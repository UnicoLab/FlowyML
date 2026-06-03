"""Stack management REST API for the FlowyML UI.

Provides endpoints for listing, inspecting, and governing enterprise stacks.
All enterprise module imports are lazy so the router still loads when the
full ``flowyml.stacks.enterprise`` package is not installed.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class StackSummary(BaseModel):
    """Lightweight representation returned by ``GET /``."""

    name: str
    version: str | None = None
    backend: str | None = None
    owner: str | None = None
    tags: list[str] = []
    source: str | None = None


class PolicyCheckResult(BaseModel):
    """Single policy-check outcome returned by ``POST /{name}/policy-check``."""

    rule_name: str
    status: str
    message: str


class LockEntry(BaseModel):
    """Lock status entry returned by ``GET /lock-status``."""

    name: str
    digest: str | None = None
    status: str


class ImportRequest(BaseModel):
    """Request body for ``POST /import``."""

    uri: str


# ---------------------------------------------------------------------------
# Helpers — lazy enterprise registry access
# ---------------------------------------------------------------------------


def _get_resolver() -> Any | None:
    """Return a ``StackResolver`` with auto-bootstrap or ``None``.

    Uses lazy importing so the router can be mounted even when the
    enterprise extras are not installed.
    """
    try:
        from flowyml.stacks.enterprise.resolver import StackResolver

        return StackResolver()
    except Exception:
        logger.debug(
            "Enterprise stack resolver not available — falling back to legacy.",
        )
        return None


def _get_legacy_registry() -> Any | None:
    """Return the legacy ``StackRegistry`` singleton or ``None``."""
    try:
        from flowyml.stacks.registry import get_registry

        return get_registry()
    except Exception:
        logger.debug("Legacy stack registry not available.")
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/")
async def list_stacks() -> dict[str, list[dict[str, Any]]]:
    """List all available stacks.

    Tries the enterprise resolver first (with auto-bootstrap); falls back
    to the legacy ``StackRegistry`` when unavailable.

    Returns:
        ``{"stacks": [...]}``, where each item contains *name*, *version*,
        *backend*, *owner*, *tags*, and *source*.
    """
    try:
        # 1. Try enterprise resolver
        resolver = _get_resolver()
        if resolver is not None:
            try:
                refs = resolver.list_stacks()
                if refs:
                    stacks = [
                        StackSummary(
                            name=ref.name,
                            version=getattr(ref, "version", None),
                            source=getattr(ref, "source", None),
                        ).model_dump()
                        for ref in refs
                    ]
                    return {"stacks": stacks}
            except Exception as exc:
                logger.warning(
                    "Enterprise resolver listing failed: %s — falling back.",
                    exc,
                )

        # 2. Fall back to legacy registry
        legacy = _get_legacy_registry()
        if legacy is not None:
            names = legacy.list_stacks()
            stacks = []
            for name in names:
                stack = legacy.get_stack(name)
                stacks.append(
                    StackSummary(
                        name=name,
                        backend=getattr(
                            getattr(stack, "config", None),
                            "backend",
                            None,
                        )
                        if stack
                        else None,
                        source="legacy",
                    ).model_dump(),
                )
            return {"stacks": stacks}

        return {"stacks": []}

    except Exception as exc:
        logger.exception("Failed to list stacks.")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list stacks: {exc}",
        ) from exc


@router.get("/lock-status")
async def get_lock_status() -> dict[str, list[dict[str, Any]]]:
    """Return the lock status for all stacks in the current lock file.

    Reads ``flowyml.lock`` from the working directory and returns a list
    of locked stacks with their digests and verification status.

    Note:
        This endpoint is defined BEFORE ``/{name}`` to prevent FastAPI
        from matching ``lock-status`` as a stack name.

    Returns:
        ``{"locked_stacks": [{"name": ..., "digest": ..., "status": ...}]}``.
    """
    try:
        from flowyml.stacks.enterprise.lock import StackLockManager

        mgr = StackLockManager()
        lock = mgr.load()
        if lock is None:
            return {"locked_stacks": []}

        results = mgr.verify()
        locked_stacks = [
            LockEntry(
                name=r.stack_name,
                digest=r.expected_digest,
                status=r.status,
            ).model_dump()
            for r in results
        ]
        return {"locked_stacks": locked_stacks}

    except Exception as exc:
        logger.exception("Failed to get lock status.")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get lock status: {exc}",
        ) from exc


@router.get("/{name}")
async def get_stack(name: str) -> dict[str, Any]:
    """Get the full stack definition as a dictionary.

    Resolves the stack through the enterprise resolver (preferred) or the
    legacy registry and returns the YAML-like structure.

    Args:
        name: Stack name to look up.

    Returns:
        The full stack definition as a JSON-serialisable dict.

    Raises:
        HTTPException 404: Stack not found.
        HTTPException 500: Internal error during resolution.
    """
    try:
        # 1. Enterprise resolver
        resolver = _get_resolver()
        if resolver is not None:
            try:
                stack_def = resolver.resolve(stack=name)
                return {
                    "stack": stack_def.model_dump(
                        mode="json",
                        by_alias=True,
                    ),
                }
            except Exception:
                pass  # fall through to legacy

        # 2. Legacy registry
        legacy = _get_legacy_registry()
        if legacy is not None:
            stack = legacy.get_stack(name)
            if stack is not None:
                return {
                    "stack": {
                        "name": stack.name,
                        "config": (stack.config.to_dict() if hasattr(stack.config, "to_dict") else {}),
                    },
                }

        raise HTTPException(
            status_code=404,
            detail=f"Stack '{name}' not found.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get stack '%s'.", name)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stack '{name}': {exc}",
        ) from exc


@router.post("/{name}/policy-check")
async def run_policy_check(
    name: str,
) -> dict[str, list[dict[str, str]]]:
    """Run the enterprise policy engine against a stack.

    Resolves the stack by *name* and evaluates all registered policy rules,
    returning per-rule results.

    Args:
        name: Stack name to validate.

    Returns:
        ``{"results": [{"rule_name": ..., "status": ..., "message": ...}]}``.

    Raises:
        HTTPException 500: When the enterprise policy engine is unavailable
            or the stack cannot be resolved.
    """
    try:
        from flowyml.stacks.enterprise.resolver import StackResolver
        from flowyml.stacks.enterprise.policy import PolicyEngine, PolicyContext

        resolver = StackResolver()
        stack_def = resolver.resolve(stack=name)

        ctx = PolicyContext(stack=stack_def)
        engine = PolicyEngine()
        results = engine.validate(ctx)

        return {
            "results": [
                PolicyCheckResult(
                    rule_name=r.rule_name,
                    status=r.status,
                    message=r.message,
                ).model_dump()
                for r in results
            ],
        }

    except Exception as exc:
        logger.exception("Policy check failed for stack '%s'.", name)
        raise HTTPException(
            status_code=500,
            detail=f"Policy check failed for stack '{name}': {exc}",
        ) from exc


@router.post("/import")
async def import_from_uri(
    body: ImportRequest,
) -> dict[str, list[str]]:
    """Import stack definitions from a remote source URI.

    Uses ``StackResolver`` to get the auto-bootstrapped registry and
    imports stacks from the given URI.

    Args:
        body: Request body containing the source URI.

    Returns:
        ``{"imported": ["stack_a", "stack_b", ...]}``.

    Raises:
        HTTPException 500: When the import fails.
    """
    try:
        from flowyml.stacks.enterprise.resolver import StackResolver

        resolver = StackResolver()
        stack_def = resolver.resolve_from_uri(body.uri)
        return {"imported": [stack_def.name]}

    except Exception as exc:
        logger.exception("Failed to import stacks from '%s'.", body.uri)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import stacks from '{body.uri}': {exc}",
        ) from exc
