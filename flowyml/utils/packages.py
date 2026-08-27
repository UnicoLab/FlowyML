"""Validation for package names passed to ``pip``.

Several endpoints let an operator install or remove Python packages: plugin
management and the deployment lab's on-demand ML framework installer. The
package name arrives from an HTTP request and is placed directly in a pip
argument vector.

``subprocess`` is invoked without a shell, so there is no shell injection here,
but an argument vector still carries two hazards:

* **Option injection.** pip cannot tell a package named ``--index-url=...``
  from the flag of the same spelling, so an unvalidated name can redirect pip
  at an attacker-controlled index, install from a local path, or turn on
  ``--editable``.
* **Self-removal.** ``pip uninstall -y flowyml`` (or one of its core
  dependencies) would disable the running server.

Validating against the PEP 508 grammar closes the first; an explicit list of
protected distributions closes the second.
"""

from __future__ import annotations

import re

#: PEP 508 project name: alphanumeric, with single ``.``, ``-`` or ``_``
#: separators, and never leading or trailing punctuation.
_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"

#: Optional extras, e.g. ``uvicorn[standard]``.
_EXTRAS = rf"(?:\[{_NAME}(?:\s*,\s*{_NAME})*\])?"

#: Optional version specifiers, e.g. ``>=1.2,<2.0`` or ``==1.2.3``.
_SPECIFIER = r"(?:\s*(?:==|!=|<=|>=|<|>|~=|===)\s*[A-Za-z0-9][A-Za-z0-9._*+!-]*)"
_SPECIFIERS = rf"(?:{_SPECIFIER}(?:\s*,\s*{_SPECIFIER})*)?"

_REQUIREMENT_RE = re.compile(rf"^{_NAME}{_EXTRAS}{_SPECIFIERS}$")

#: Distributions the server must never uninstall: removing any of them stops
#: the process that is handling the request.
PROTECTED_DISTRIBUTIONS: frozenset[str] = frozenset(
    {
        "flowyml",
        "pip",
        "setuptools",
        "wheel",
        "fastapi",
        "starlette",
        "uvicorn",
        "pydantic",
        "pydantic-core",
        "sqlalchemy",
        "click",
        "loguru",
        "anyio",
    },
)


class InvalidPackageNameError(ValueError):
    """Raised when a package specifier is unsafe to hand to pip."""


def normalize_distribution_name(name: str) -> str:
    """Normalize a distribution name per PEP 503 for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_requirement(requirement: str) -> str:
    """Return *requirement* if it is a safe pip requirement, else raise.

    Accepts a bare name, extras and version specifiers - ``scikit-learn``,
    ``uvicorn[standard]``, ``torch>=2.0`` - and rejects anything that could be
    read as an option, a URL, a filesystem path, or a second argument.

    Raises:
        InvalidPackageNameError: if *requirement* is not a plain package specifier.
    """
    if not isinstance(requirement, str):
        raise InvalidPackageNameError(f"Package specifier must be a string, got {type(requirement)!r}")

    candidate = requirement.strip()
    if not candidate:
        raise InvalidPackageNameError("Package specifier must not be empty")

    if candidate.startswith("-"):
        raise InvalidPackageNameError(
            f"Refusing '{requirement}': a leading '-' would be interpreted by pip as an option, "
            "not a package name.",
        )

    if not _REQUIREMENT_RE.match(candidate):
        raise InvalidPackageNameError(
            f"Refusing '{requirement}': only plain package specifiers are accepted "
            "(name, optional [extras], optional version specifiers). URLs, paths and "
            "pip options are not permitted.",
        )

    return candidate


def validate_uninstall_target(name: str) -> str:
    """Return *name* if it is safe to uninstall, else raise.

    Beyond the checks in :func:`validate_requirement`, refuses to uninstall a
    distribution the running server depends on.

    Raises:
        InvalidPackageNameError: if *name* is malformed or protected.
    """
    candidate = validate_requirement(name)

    # A version specifier is meaningless for uninstall and would only confuse
    # the operator about what was actually removed.
    bare = re.split(r"[\[<>=!~]", candidate, maxsplit=1)[0].strip()

    if normalize_distribution_name(bare) in {
        normalize_distribution_name(p) for p in PROTECTED_DISTRIBUTIONS
    }:
        raise InvalidPackageNameError(
            f"Refusing to uninstall '{bare}': the running server depends on it.",
        )

    return bare
