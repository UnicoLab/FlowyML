"""Path-traversal regression tests for the artifact endpoints.

Artifact metadata records where an artifact's bytes live, and four handlers
turn that value into a filesystem operation. Because ``POST /api/assets/``
persisted a client's ``metadata`` dict verbatim, and the upload handler built
its destination from client-supplied name components, that value was
attacker-controlled — which made the API an arbitrary file read, write and
delete primitive:

* ``metadata={"path": "/etc/hostname"}`` then ``GET /{id}/download`` returned
  the contents of ``/etc/hostname``.
* ``metadata={"path": "/tmp/victim"}`` then ``DELETE /{id}`` removed that file.
* ``run_id="../../.."`` or ``filename="../../../etc/cron.d/x"`` escaped the
  artifacts directory on upload.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.ui.backend.artifact_paths import (  # noqa: E402
    ArtifactPathError,
    resolve_within_root,
    sanitize_path_segment,
    strip_reserved_metadata,
)


# ---------------------------------------------------------------------------
# the confinement primitives
# ---------------------------------------------------------------------------


class TestResolveWithinRoot:
    def test_relative_path_resolves_under_root(self, tmp_path):
        resolved = resolve_within_root("a/b/c.txt", tmp_path)
        assert resolved == (tmp_path / "a" / "b" / "c.txt").resolve()

    def test_parent_traversal_is_rejected(self, tmp_path):
        with pytest.raises(ArtifactPathError):
            resolve_within_root("../escape.txt", tmp_path)

    def test_deep_traversal_is_rejected(self, tmp_path):
        with pytest.raises(ArtifactPathError):
            resolve_within_root("a/../../../../etc/passwd", tmp_path)

    def test_absolute_path_outside_root_is_rejected(self, tmp_path):
        """`Path("/base") / "/etc/passwd"` silently discards the base."""
        with pytest.raises(ArtifactPathError):
            resolve_within_root("/etc/passwd", tmp_path)

    def test_absolute_path_inside_root_is_allowed(self, tmp_path):
        target = tmp_path / "nested" / "file.txt"
        assert resolve_within_root(str(target), tmp_path) == target.resolve()

    def test_symlink_escaping_root_is_rejected(self, tmp_path):
        outside = tmp_path.parent / "outside-secret.txt"
        outside.write_text("secret")
        root = tmp_path / "root"
        root.mkdir()
        (root / "link.txt").symlink_to(outside)

        with pytest.raises(ArtifactPathError):
            resolve_within_root("link.txt", root)

    def test_nonexistent_path_still_resolves(self, tmp_path):
        """Upload destinations do not exist yet; containment is the only check."""
        assert resolve_within_root("not/created/yet.bin", tmp_path)

    def test_root_itself_is_permitted(self, tmp_path):
        assert resolve_within_root(".", tmp_path) == tmp_path.resolve()


class TestSanitizePathSegment:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("normal.txt", "normal.txt"),
            ("../../etc/passwd", "passwd"),
            ("a/b/c.txt", "c.txt"),
            (r"C:\Users\me\file.txt", "file.txt"),
            ("..", "unnamed"),
            ("", "unnamed"),
            ("with space.txt", "with_space.txt"),
            ("semi;colon", "semi_colon"),
        ],
    )
    def test_reduces_to_one_safe_component(self, raw, expected):
        assert sanitize_path_segment(raw) == expected

    def test_result_never_introduces_nesting(self):
        for raw in ("../../x", "a/b", "/abs/path", "..\\..\\win"):
            assert "/" not in sanitize_path_segment(raw)
            assert "\\" not in sanitize_path_segment(raw)

    def test_custom_fallback_is_used(self):
        assert sanitize_path_segment("", fallback="default") == "default"


class TestStripReservedMetadata:
    def test_path_is_removed(self):
        assert strip_reserved_metadata({"path": "/etc/passwd", "rows": 10}) == {"rows": 10}

    def test_other_keys_survive(self):
        payload = {"rows": 10, "columns": ["a"], "nested": {"path": "kept"}}
        assert strip_reserved_metadata(payload) == payload


# ---------------------------------------------------------------------------
# end-to-end through the API
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch, tmp_path):
    """API client whose artifact and metadata storage are isolated to tmp_path."""
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    from flowyml.utils import config as config_module

    real_get_config = config_module.get_config

    def _scoped_config(*args, **kwargs):
        cfg = real_get_config(*args, **kwargs)
        cfg.artifacts_dir = artifacts_dir
        return cfg

    monkeypatch.setattr(config_module, "get_config", _scoped_config)

    from flowyml.storage.sql import SQLMetadataStore
    from flowyml.ui.backend import dependencies

    store = SQLMetadataStore(db_path=str(tmp_path / "meta.db"))
    monkeypatch.setattr(dependencies, "_store", store)

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        test_client.artifacts_dir = artifacts_dir
        test_client.outside_dir = tmp_path / "outside"
        test_client.outside_dir.mkdir()
        yield test_client


def _create_asset(client, artifact_id, **overrides):
    payload = {
        "artifact_id": artifact_id,
        "name": artifact_id,
        "type": "data",
        "run_id": "run-1",
        "step": "step-1",
    }
    payload.update(overrides)
    response = client.post("/api/assets/", json=payload)
    assert response.status_code == 200, response.text
    return response


class TestArbitraryFileRead:
    def test_client_supplied_path_is_not_persisted(self, client):
        _create_asset(client, "poc-read", metadata={"path": "/etc/hostname"})

        stored = client.get("/api/assets/poc-read").json()
        assert stored.get("path") in (None, "")

    def test_download_cannot_read_a_file_outside_the_root(self, client):
        secret = client.outside_dir / "secret.txt"
        secret.write_text("TOP SECRET")

        _create_asset(client, "poc-read", metadata={"path": str(secret)})

        response = client.get("/api/assets/poc-read/download")
        assert response.status_code == 404
        assert "TOP SECRET" not in response.text

    def test_content_cannot_read_a_file_outside_the_root(self, client):
        secret = client.outside_dir / "secret.txt"
        secret.write_text("TOP SECRET")

        _create_asset(client, "poc-read", metadata={"path": str(secret)})

        response = client.get("/api/assets/poc-read/content")
        assert response.status_code == 404
        assert "TOP SECRET" not in response.text


class TestArbitraryFileWrite:
    def test_traversal_in_filename_stays_inside_the_root(self, client):
        _create_asset(client, "poc-write")

        response = client.post(
            "/api/assets/poc-write/upload",
            files={"file": ("../../../../escaped.txt", b"OWNED")},
        )
        assert response.status_code == 200

        written = Path(client.artifacts_dir, response.json()["path"]).resolve()
        assert client.artifacts_dir.resolve() in written.parents
        assert not (client.outside_dir / "escaped.txt").exists()

    def test_traversal_in_run_id_stays_inside_the_root(self, client):
        _create_asset(client, "poc-write", run_id="../../../../tmp")

        response = client.post(
            "/api/assets/poc-write/upload",
            files={"file": ("payload.txt", b"OWNED")},
        )
        assert response.status_code == 200

        written = Path(client.artifacts_dir, response.json()["path"]).resolve()
        assert client.artifacts_dir.resolve() in written.parents

    def test_uploaded_content_round_trips(self, client):
        """Hardening must not break the legitimate upload/download path."""
        _create_asset(client, "good-asset")

        upload = client.post(
            "/api/assets/good-asset/upload",
            files={"file": ("model.txt", b"weights")},
        )
        assert upload.status_code == 200

        download = client.get("/api/assets/good-asset/download")
        assert download.status_code == 200
        assert download.content == b"weights"

        content = client.get("/api/assets/good-asset/content")
        assert content.status_code == 200
        assert content.content == b"weights"


class TestArbitraryFileDelete:
    def test_delete_leaves_files_outside_the_root_alone(self, client):
        victim = client.outside_dir / "victim.txt"
        victim.write_text("important")

        _create_asset(client, "poc-delete", metadata={"path": str(victim)})

        response = client.delete("/api/assets/poc-delete")
        assert response.status_code == 200
        assert victim.exists(), "an out-of-bounds path must never be deleted"

    def test_delete_still_removes_a_legitimate_artifact_file(self, client):
        _create_asset(client, "real-asset")
        upload = client.post(
            "/api/assets/real-asset/upload",
            files={"file": ("data.bin", b"payload")},
        )
        stored = Path(client.artifacts_dir, upload.json()["path"])
        assert stored.exists()

        assert client.delete("/api/assets/real-asset").status_code == 200
        assert not stored.exists()
