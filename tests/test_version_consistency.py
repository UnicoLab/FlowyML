"""Every surface that reports a version must report the real one.

Version strings were duplicated as literals in places the release automation
does not update. ``[tool.semantic_release].version_variables`` covers
``flowyml/__init__.py`` and the sidebar component, but nothing else - so
``flowyml --version`` answered "0.1.0" for release 2.2.0, the FastAPI app
advertised "0.1.0" in its OpenAPI document, and ``/api/health`` returned the
same. Anyone diagnosing a deployment from those outputs was reading a number
that had been wrong for every release since the first.

Each surface now derives its value from ``flowyml.__version__``; these tests
fail if a literal creeps back in.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

import flowyml

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def declared_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["tool"]["poetry"]["version"]


def test_package_version_matches_pyproject(declared_version):
    assert flowyml.__version__ == declared_version


def test_cli_reports_the_package_version():
    from click.testing import CliRunner

    from flowyml.cli.main import cli

    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert flowyml.__version__ in result.output, (
        f"`flowyml --version` printed {result.output.strip()!r}, "
        f"expected it to contain {flowyml.__version__!r}"
    )


def test_cli_does_not_hardcode_a_version():
    """A literal here cannot be updated by the release automation."""
    source = (REPO_ROOT / "flowyml" / "cli" / "main.py").read_text(encoding="utf-8")

    match = re.search(r"@click\.version_option\(\s*version\s*=\s*([^,)]+)", source)
    assert match, "version_option not found"
    assert "__version__" in match.group(1), (
        f"CLI version is hardcoded as {match.group(1).strip()}; derive it from __version__"
    )


class TestApiSurfaces:
    @pytest.fixture
    def client(self, monkeypatch):
        pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        monkeypatch.delenv("FLOWYML_ENV", raising=False)
        monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

        from flowyml.ui.backend.main import app

        with TestClient(app) as test_client:
            yield test_client

    def test_health_endpoint_reports_the_package_version(self, client):
        assert client.get("/api/health").json()["version"] == flowyml.__version__

    def test_openapi_document_reports_the_package_version(self, client):
        assert client.get("/openapi.json").json()["info"]["version"] == flowyml.__version__

    def test_server_info_reports_the_package_version(self, client):
        assert client.get("/api/execution/info").json()["version"] == flowyml.__version__


def test_the_frontend_sidebar_shows_the_current_version(declared_version):
    """The sidebar literal is updated by semantic-release; verify it kept up."""
    sidebar = REPO_ROOT / "flowyml" / "ui" / "frontend" / "src" / "components" / "sidebar"
    sidebar_file = sidebar / "Sidebar.jsx"
    if not sidebar_file.exists():
        pytest.skip("frontend sources not present")

    text = sidebar_file.read_text(encoding="utf-8")
    versions = re.findall(r"FlowyML v(\d+\.\d+\.\d+)", text)

    assert versions, "no 'FlowyML v<version>' string found in the sidebar"
    assert all(v == declared_version for v in versions), (
        f"sidebar shows {versions}, expected {declared_version}"
    )
