"""Local Catalog Backend — SQLite-based artifact catalog for local development.

Zero-config, file-based catalog that works without any server.
Uses SQLite via the standard library for maximum portability.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from flowyml.storage.catalog.backend import CatalogBackend, CatalogEntry

logger = logging.getLogger(__name__)


class LocalCatalogBackend(CatalogBackend):
    """SQLite-backed artifact catalog for local development.

    Stores artifact metadata in a local SQLite database file.
    Works standalone — no server, no external dependencies.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to `.flowyml/catalog.db`
    """

    def __init__(self, db_path: str = ".flowyml/catalog.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    content_hash TEXT,
                    source_step TEXT,
                    source_run_id TEXT,
                    source_pipeline TEXT,
                    parent_ids TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    uri TEXT,
                    created_at TEXT NOT NULL,
                    version TEXT
                )
            """,
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_content_hash
                ON artifacts(content_hash)
            """,
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_source_pipeline
                ON artifacts(source_pipeline)
            """,
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_type
                ON artifacts(artifact_type)
            """,
            )
            conn.commit()

    def _row_to_entry(self, row: tuple) -> CatalogEntry:
        """Convert a database row to a CatalogEntry."""
        return CatalogEntry(
            artifact_id=row[0],
            name=row[1],
            artifact_type=row[2],
            content_hash=row[3] or "",
            source_step=row[4] or "",
            source_run_id=row[5] or "",
            source_pipeline=row[6] or "",
            parent_ids=json.loads(row[7]) if row[7] else [],
            tags=json.loads(row[8]) if row[8] else {},
            metadata=json.loads(row[9]) if row[9] else {},
            uri=row[10] or "",
            created_at=row[11] or "",
            version=row[12],
        )

    def register(self, entry: CatalogEntry) -> str:
        """Register a new artifact in the local catalog."""
        if not entry.artifact_id:
            entry.artifact_id = str(uuid.uuid4())
        if not entry.created_at:
            entry.created_at = datetime.now().isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts
                (artifact_id, name, artifact_type, content_hash, source_step,
                 source_run_id, source_pipeline, parent_ids, tags, metadata,
                 uri, created_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.artifact_id,
                    entry.name,
                    entry.artifact_type,
                    entry.content_hash,
                    entry.source_step,
                    entry.source_run_id,
                    entry.source_pipeline,
                    json.dumps(entry.parent_ids),
                    json.dumps(entry.tags),
                    json.dumps(entry.metadata),
                    entry.uri,
                    entry.created_at,
                    entry.version,
                ),
            )
            conn.commit()

        logger.debug(f"Registered artifact '{entry.name}' ({entry.artifact_id})")
        return entry.artifact_id

    def get(self, artifact_id: str) -> CatalogEntry | None:
        """Get an artifact by ID."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None

    def list_artifacts(
        self,
        artifact_type: str | None = None,
        source_pipeline: str | None = None,
        source_step: str | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
    ) -> list[CatalogEntry]:
        """List artifacts with optional filtering."""
        query = "SELECT * FROM artifacts WHERE 1=1"
        params: list[Any] = []

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)

        if source_pipeline:
            query += " AND source_pipeline = ?"
            params.append(source_pipeline)

        if source_step:
            query += " AND source_step = ?"
            params.append(source_step)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(query, params)
            entries = [self._row_to_entry(row) for row in cursor.fetchall()]

        # Filter by tags in Python (SQLite JSON support varies)
        if tags:
            entries = [e for e in entries if all(e.tags.get(k) == v for k, v in tags.items())]

        return entries

    def list(self, **kwargs) -> list[CatalogEntry]:  # noqa: A003
        """Alias for list_artifacts() for convenience."""
        return self.list_artifacts(**kwargs)

    def tag(self, artifact_id: str, tags: dict[str, str]) -> None:
        """Add or update tags on an artifact."""
        entry = self.get(artifact_id)
        if entry is None:
            raise ValueError(f"Artifact '{artifact_id}' not found")

        entry.tags.update(tags)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE artifacts SET tags = ? WHERE artifact_id = ?",
                (json.dumps(entry.tags), artifact_id),
            )
            conn.commit()

    def search(self, query: str, limit: int = 50) -> list[CatalogEntry]:
        """Search artifacts by name, type, or tag values."""
        search_term = f"%{query}%"

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM artifacts
                WHERE name LIKE ? OR artifact_type LIKE ?
                   OR tags LIKE ? OR source_pipeline LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (search_term, search_term, search_term, search_term, limit),
            )
            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Get lineage information for an artifact."""
        entry = self.get(artifact_id)
        if entry is None:
            return {"artifact_id": artifact_id, "error": "not found"}

        # Get parents (what produced this artifact's inputs)
        parents = []
        for parent_id in entry.parent_ids:
            parent = self.get(parent_id)
            if parent:
                parents.append(parent.to_dict())

        # Get children (artifacts that consumed this artifact)
        children = []
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM artifacts WHERE parent_ids LIKE ?",
                (f"%{artifact_id}%",),
            )
            for row in cursor.fetchall():
                child = self._row_to_entry(row)
                if artifact_id in child.parent_ids:
                    children.append(child.to_dict())

        return {
            "artifact": entry.to_dict(),
            "parents": parents,
            "children": children,
        }

    def find_by_content_hash(self, content_hash: str) -> CatalogEntry | None:
        """Find an artifact by its content hash."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM artifacts WHERE content_hash = ? LIMIT 1",
                (content_hash,),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None
