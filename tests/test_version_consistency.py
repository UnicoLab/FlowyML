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

# `tomllib` is stdlib only from Python 3.11; this project supports 3.10,
# and `toml` is already a core dependency.
import toml
from pathlib import Path

import pytest

import flowyml

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def declared_version() -> str:
    return toml.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["poetry"]["version"]


def test_package_version_matches_pyproject(declared_version):
    assert flowyml.__version__ == declared_version


def test_cli_reports_the_package_version():
    from click.testing import CliRunner

    from flowyml.cli.main import cli

    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert flowyml.__version__ in result.output, (
        f"`flowyml --version` printed {result.output.strip()!r}, " f"expected it to contain {flowyml.__version__!r}"
    )


def test_cli_does_not_hardcode_a_version():
    """A literal here cannot be updated by the release automation."""
    source = (REPO_ROOT / "flowyml" / "cli" / "main.py").read_text(encoding="utf-8")

    match = re.search(r"@click\.version_option\(\s*version\s*=\s*([^,)]+)", source)
    assert match, "version_option not found"
    assert "__version__" in match.group(
        1,
    ), f"CLI version is hardcoded as {match.group(1).strip()}; derive it from __version__"


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


SIDEBAR = REPO_ROOT / "flowyml" / "ui" / "frontend" / "src" / "components" / "sidebar" / "Sidebar.jsx"


def test_the_frontend_sidebar_shows_the_current_version(declared_version):
    """The sidebar constant is bumped by semantic-release; verify it kept up."""
    if not SIDEBAR.exists():
        pytest.skip("frontend sources not present")

    versions = re.findall(r'^const VERSION = "(\d+\.\d+\.\d+)";', SIDEBAR.read_text(encoding="utf-8"), re.M)

    assert versions, 'no `const VERSION = "x.y.z";` found in the sidebar'
    assert all(v == declared_version for v in versions), f"sidebar shows {versions}, expected {declared_version}"


def test_the_sidebar_does_not_print_a_version_inline():
    """An inline literal is invisible to the release automation.

    ``version_variables`` rewrites assignments; it cannot touch a number
    sitting in JSX text. While the version was written straight into the
    markup, every release bumped ``pyproject.toml`` and ``__init__.py`` and
    left the sidebar advertising the previous version.
    """
    if not SIDEBAR.exists():
        pytest.skip("frontend sources not present")

    inline = re.findall(r">FlowyML v\d+\.\d+\.\d+<", SIDEBAR.read_text(encoding="utf-8"))

    assert not inline, f"the sidebar prints a hardcoded version in its markup: {inline}; render {{VERSION}} instead"


def test_every_release_version_variable_can_actually_be_rewritten(declared_version):
    """A ``version_variables`` entry that matches nothing fails silently.

    semantic-release looks for ``<variable> = "<current version>"``. If the
    entry names something that is not assigned that way it updates nothing,
    reports success, and the surface keeps showing the old version - which is
    exactly what happened to the sidebar.
    """
    config = toml.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entries = config["tool"]["semantic_release"]["version_variables"]

    unmatched = []
    for entry in entries:
        path_part, _, variable = entry.rpartition(":")
        target = REPO_ROOT / path_part
        if not target.exists():
            continue  # frontend sources may be absent in a packaged checkout
        pattern = rf'{re.escape(variable)}\s*[:=]\s*["\']{re.escape(declared_version)}["\']'
        if not re.search(pattern, target.read_text(encoding="utf-8")):
            unmatched.append(entry)

    assert not unmatched, (
        "these version_variables entries match nothing, so semantic-release " f"will silently skip them: {unmatched}"
    )
