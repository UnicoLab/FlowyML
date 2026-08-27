"""Tests for artifact identity in the store and model availability reporting.

Two defects that made assets look broken in the UI:

*Missing identity.* ``SQLMetadataStore`` keeps ``artifact_id`` in its own
column but ``list_assets``/``load_artifact`` returned only the metadata JSON.
Records whose metadata did not happen to repeat the id — everything created
through ``POST /api/assets/`` — came back without one, and the UI builds
download and content URLs from that field. ``query()`` had always projected
``run_id`` the same way for runs; artifacts simply never got the same
treatment.

*Wrong artifact root.* ``/api/deployments/available-models`` probed for model
files under a hard-coded ``/app/artifacts``, the path inside the project's
Docker image. Anyone running ``flowyml ui`` from a pip install keeps artifacts
under the configured artifacts directory, so the probe always failed and the
deployments page labelled every model "Missing".
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.storage.sql import SQLMetadataStore  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return SQLMetadataStore(db_path=str(tmp_path / "meta.db"))


class TestArtifactIdentity:
    def test_list_assets_includes_the_id_when_metadata_omits_it(self, store):
        store.save_artifact("no-id-in-metadata", {"name": "m", "type": "model"})

        [asset] = store.list_assets()
        assert asset["artifact_id"] == "no-id-in-metadata"

    def test_load_artifact_includes_the_id_when_metadata_omits_it(self, store):
        store.save_artifact("no-id-in-metadata", {"name": "m", "type": "model"})

        loaded = store.load_artifact("no-id-in-metadata")
        assert loaded["artifact_id"] == "no-id-in-metadata"

    def test_metadata_id_is_not_overwritten(self, store):
        """A metadata-supplied id wins, so existing records keep their value."""
        store.save_artifact("column-id", {"artifact_id": "metadata-id", "name": "m"})

        assert store.load_artifact("column-id")["artifact_id"] == "metadata-id"
        assert store.list_assets()[0]["artifact_id"] == "metadata-id"

    def test_every_listed_asset_is_addressable(self, store):
        for index in range(5):
            store.save_artifact(f"asset-{index}", {"name": f"m{index}", "type": "model"})

        assets = store.list_assets()
        assert len(assets) == 5
        assert all(asset.get("artifact_id") for asset in assets)

    def test_load_artifact_still_returns_none_for_unknown_id(self, store):
        assert store.load_artifact("nope") is None


@pytest.fixture
def client(monkeypatch, tmp_path):
    """API client with isolated artifact and metadata storage."""
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

    from flowyml.ui.backend import dependencies

    monkeypatch.setattr(
        dependencies,
        "_store",
        SQLMetadataStore(db_path=str(tmp_path / "meta.db")),
    )

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        yield test_client


class TestRestCreatedAssetsAreUsable:
    """The full path the UI takes: create, upload, list, download."""

    def test_asset_created_via_api_is_listed_with_an_id(self, client):
        client.post(
            "/api/assets/",
            json={
                "artifact_id": "rest-made",
                "name": "my_model",
                "type": "model",
                "run_id": "run-1",
                "step": "train",
            },
        )

        listed = client.get("/api/assets/?limit=100").json()["assets"]
        assert any(asset.get("artifact_id") == "rest-made" for asset in listed)

    def test_asset_created_via_api_can_be_downloaded(self, client):
        client.post(
            "/api/assets/",
            json={
                "artifact_id": "rest-made",
                "name": "my_model",
                "type": "model",
                "run_id": "run-1",
                "step": "train",
            },
        )
        client.post(
            "/api/assets/rest-made/upload",
            files={"file": ("model.pkl", b"MODELBYTES")},
        )

        response = client.get("/api/assets/rest-made/download")
        assert response.status_code == 200
        assert response.content == b"MODELBYTES"


class TestModelAvailability:
    def _create_model_with_file(self, client, artifact_id="deployable"):
        client.post(
            "/api/assets/",
            json={
                "artifact_id": artifact_id,
                "name": "my_model",
                "type": "model",
                "run_id": "run-1",
                "step": "train",
            },
        )
        client.post(
            f"/api/assets/{artifact_id}/upload",
            files={"file": ("model.pkl", b"MODELBYTES")},
        )

    def test_model_with_a_file_reports_file_exists(self, client):
        """Previously always False outside Docker, showing "Missing" for every model."""
        self._create_model_with_file(client)

        models = client.get("/api/deployments/available-models").json()
        found = [m for m in models if m["artifact_id"] == "deployable"]

        assert found, "model should be offered for deployment"
        assert found[0]["has_file"] is True
        assert found[0]["file_exists"] is True

    def test_model_without_a_file_reports_file_missing(self, client):
        client.post(
            "/api/assets/",
            json={
                "artifact_id": "no-file",
                "name": "my_model",
                "type": "model",
                "run_id": "run-1",
                "step": "train",
            },
        )

        models = client.get("/api/deployments/available-models").json()
        found = [m for m in models if m["artifact_id"] == "no-file"]

        assert found
        assert found[0]["has_file"] is False
        assert found[0]["file_exists"] is False

    def test_path_outside_the_artifacts_root_is_not_probed(self, client, tmp_path):
        """A path escaping the root reports False rather than probing the host."""
        from flowyml.ui.backend.routers.deployments import _artifact_file_exists

        outside = tmp_path / "outside.txt"
        outside.write_text("data")

        assert _artifact_file_exists(str(outside)) is False
        assert _artifact_file_exists("../../../etc/hostname") is False

    def test_missing_path_reports_false(self, client):
        from flowyml.ui.backend.routers.deployments import _artifact_file_exists

        assert _artifact_file_exists(None) is False
        assert _artifact_file_exists("") is False
