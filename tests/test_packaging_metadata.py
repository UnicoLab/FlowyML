"""Regression tests for the distribution metadata in ``pyproject.toml``.

These guard a class of packaging bug that is invisible in a development
checkout but breaks every real installation: Poetry treats *any* dependency
named in ``[tool.poetry.extras]`` as extra-only, so listing a core dependency
there silently strips it from ``pip install flowyml``.  That shipped a package
whose entire web UI raised ``ModuleNotFoundError: No module named 'fastapi'``.

The mirror-image bug is an extra that names a package which was never declared
in ``[tool.poetry.dependencies]``: Poetry drops it without warning, so
``pip install flowyml[azure]`` installed nothing at all.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

# Dependencies that must always be installed by a bare ``pip install flowyml``.
# fastapi/uvicorn/websockets/python-multipart back the web UI; rich backs the CLI.
REQUIRED_CORE_PACKAGES = {
    "fastapi",
    "uvicorn",
    "websockets",
    "python-multipart",
    "rich",
    "click",
    "pydantic",
    "sqlalchemy",
    "pyyaml",
    "loguru",
}


def _normalize(name: str) -> str:
    """PEP 503 style normalization so ``python_multipart`` == ``python-multipart``."""
    return name.lower().replace("_", "-")


@pytest.fixture(scope="module")
def pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


@pytest.fixture(scope="module")
def declared_dependencies(pyproject: dict) -> dict[str, object]:
    return pyproject["tool"]["poetry"]["dependencies"]


@pytest.fixture(scope="module")
def extras(pyproject: dict) -> dict[str, list[str]]:
    return pyproject["tool"]["poetry"].get("extras", {})


def _is_optional(spec: object) -> bool:
    return isinstance(spec, dict) and bool(spec.get("optional", False))


def test_core_dependencies_are_not_listed_in_any_extra(declared_dependencies, extras):
    """A non-optional dependency named in an extra becomes extra-only."""
    optional_names = {_normalize(n) for n, s in declared_dependencies.items() if _is_optional(s)}
    core_names = {
        _normalize(n)
        for n, s in declared_dependencies.items()
        if n != "python" and not _is_optional(s)
    }

    offenders: dict[str, list[str]] = {}
    for extra_name, packages in extras.items():
        bad = [p for p in packages if _normalize(p) in core_names]
        if bad:
            offenders[extra_name] = bad

    assert not offenders, (
        "These extras name non-optional dependencies, which makes Poetry demote them "
        f"to extra-only and strips them from `pip install flowyml`: {offenders}. "
        f"(Optional dependencies available for extras: {sorted(optional_names)})"
    )


def test_every_package_named_in_an_extra_is_declared(declared_dependencies, extras):
    """Poetry silently drops extras entries that are not declared dependencies."""
    declared = {_normalize(n) for n in declared_dependencies}

    undeclared: dict[str, list[str]] = {}
    for extra_name, packages in extras.items():
        missing = [p for p in packages if _normalize(p) not in declared]
        if missing:
            undeclared[extra_name] = missing

    assert not undeclared, (
        "These extras reference packages that are absent from "
        f"[tool.poetry.dependencies], so the extra installs nothing: {undeclared}"
    )


def test_every_optional_dependency_is_reachable_through_an_extra(declared_dependencies, extras):
    """An optional dependency in no extra can never be installed by anyone."""
    optional_names = {_normalize(n) for n, s in declared_dependencies.items() if _is_optional(s)}
    reachable = {_normalize(p) for packages in extras.values() for p in packages}

    orphans = sorted(optional_names - reachable)
    assert not orphans, (
        f"These dependencies are declared `optional = true` but appear in no extra, "
        f"so no `pip install flowyml[...]` invocation can ever install them: {orphans}"
    )


def test_all_extra_is_a_superset_of_the_cloud_and_framework_extras(extras):
    """``flowyml[all]`` must not be missing pieces the narrower extras provide."""
    all_packages = {_normalize(p) for p in extras.get("all", [])}

    # ``all`` is deliberately a superset of every extra that pulls real
    # third-party packages. Empty back-compat extras (ui, rich) have nothing
    # to contribute and are skipped by the emptiness check itself.
    missing: dict[str, list[str]] = {}
    for extra_name, packages in extras.items():
        if extra_name == "all" or not packages:
            continue
        gap = sorted({_normalize(p) for p in packages} - all_packages)
        if gap:
            missing[extra_name] = gap

    assert not missing, f"`flowyml[all]` is missing packages provided by narrower extras: {missing}"


def test_installed_distribution_exposes_core_dependencies_unconditionally():
    """Check the *built* metadata, which is what pip actually consumes."""
    from importlib.metadata import PackageNotFoundError, requires

    try:
        requirements = requires("flowyml")
    except PackageNotFoundError:  # pragma: no cover - only when not installed
        pytest.skip("flowyml is not installed in this environment")

    assert requirements is not None

    # A requirement with no environment marker is installed unconditionally.
    unconditional = {
        _normalize(r.split(";")[0].strip().split()[0].split("[")[0])
        for r in requirements
        if ";" not in r
    }

    missing = sorted(REQUIRED_CORE_PACKAGES - unconditional)
    assert not missing, (
        f"The built distribution does not install {missing} unconditionally. "
        "`pip install flowyml` would produce a broken install. "
        "Re-run `pip install -e .` if pyproject.toml changed since the last build."
    )
