"""Confine artifact file access to the configured artifacts directory.

Artifact metadata records a ``path`` telling the API where the bytes live. That
value reaches the filesystem through download, inline-content, delete and
upload handlers, so anything able to influence it can steer those operations at
an arbitrary location:

* ``POST /api/assets/`` accepts a free-form ``metadata`` dict that is persisted
  verbatim, so a client could store ``{"path": "/etc/hostname"}`` and then read
  that file back through ``GET /api/assets/{id}/download``.
* The upload handler builds its destination from ``project``, ``run_id``,
  ``artifact_id`` and the uploaded ``filename`` — all client-supplied — so a
  ``..`` component escaped the artifacts directory, and an absolute component
  discarded it entirely (``Path("/base") / "/etc/passwd"`` is ``/etc/passwd``).

Every filesystem access therefore goes through :func:`resolve_within_root`,
which resolves symlinks and refuses any result outside the root.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

#: Metadata keys the API computes itself. A client that supplies them is
#: overriding server state, so they are dropped from user-provided metadata.
RESERVED_METADATA_KEYS: frozenset[str] = frozenset({"path"})

#: Characters that are unsafe in a single path segment. The path separators are
#: excluded so a segment can never introduce directory structure.
_UNSAFE_SEGMENT_CHARS = re.compile(r"[^A-Za-z0-9._\-]")


class ArtifactPathError(ValueError):
    """Raised when a path would escape the artifacts root."""


def sanitize_path_segment(segment: str, *, fallback: str = "unnamed") -> str:
    """Reduce *segment* to a single, safe path component.

    Strips directory separators, ``..`` and other unsafe characters so the
    result can never introduce nesting or traversal when joined into a path.
    """
    if not segment:
        return fallback

    # Take only the final component: callers sometimes pass a browser-supplied
    # filename, which on Windows clients can arrive as "C:\\path\\to\\file".
    segment = segment.replace("\\", "/").rsplit("/", 1)[-1]

    cleaned = _UNSAFE_SEGMENT_CHARS.sub("_", segment).strip("._")
    return cleaned or fallback


def resolve_within_root(candidate: str | os.PathLike[str], root: str | os.PathLike[str]) -> Path:
    """Resolve *candidate* against *root* and guarantee it stays inside.

    A relative candidate is joined to the root; an absolute one must already be
    inside it. Symlinks are resolved before the check so a link planted inside
    the root cannot point out of it.

    Raises:
        ArtifactPathError: if the resolved path escapes *root*.
    """
    root_path = Path(root).expanduser().resolve()
    candidate_path = Path(candidate).expanduser()

    combined = candidate_path if candidate_path.is_absolute() else root_path / candidate_path

    # ``strict=False`` so a not-yet-created upload destination still resolves;
    # existence is the caller's concern, containment is ours.
    resolved = combined.resolve(strict=False)

    if resolved != root_path and root_path not in resolved.parents:
        raise ArtifactPathError(
            f"Refusing to access '{candidate}': resolved path {resolved} is outside "
            f"the artifacts directory {root_path}",
        )

    return resolved


def strip_reserved_metadata(metadata: dict) -> dict:
    """Return *metadata* without keys the server owns."""
    return {key: value for key, value in metadata.items() if key not in RESERVED_METADATA_KEYS}
