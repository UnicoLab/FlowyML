"""Backend dependencies."""

import os

from loguru import logger
from flowyml.storage.sql import SQLMetadataStore
from flowyml.utils.config import get_config

_store = None


def get_store() -> SQLMetadataStore:
    """Get the metadata store instance.

    Uses FLOWYML_DATABASE_URL if set, otherwise defaults to local SQLite.
    """
    global _store
    if _store is None:
        config = get_config()
        db_url = os.environ.get("FLOWYML_DATABASE_URL")

        # If no explicit URL, use the config's metadata_db path
        if not db_url:
            db_path = config.metadata_db
            # Ensure it's a string path for SQLMetadataStore
            _store = SQLMetadataStore(db_path=str(db_path))
        else:
            _store = SQLMetadataStore(db_url=db_url)

    return _store


def iter_metadata_stores() -> list[tuple[str | None, SQLMetadataStore]]:
    """Yield ``(project_name, store)`` for the global store and every project store.

    A run, asset or experiment can live either in the globally configured store
    or in a project's own store, so any lookup by id has to consult both. Three
    routers each kept their own copy of this loop and they drifted: the AI
    context endpoint checked only the global store and answered 404 for runs
    the run-detail page displayed perfectly well.

    Project discovery failures are non-fatal: the global store is always usable
    on its own.
    """
    from flowyml.core.project import ProjectManager

    stores: list[tuple[str | None, SQLMetadataStore]] = [(None, get_store())]

    try:
        manager = ProjectManager()
        for project_meta in manager.list_projects():
            name = project_meta.get("name")
            if not name:
                continue
            project = manager.get_project(name)
            if project:
                stores.append((name, project.metadata_store))
    except Exception as exc:  # pragma: no cover - project layout is optional
        logger.debug(f"Could not enumerate project metadata stores: {exc}")

    return stores


def find_run_across_stores(run_id: str) -> tuple[dict | None, SQLMetadataStore | None]:
    """Locate a run in any known store, returning ``(run, store)``.

    The run is annotated with its owning project when the store knows one and
    the record does not already carry it.
    """
    for project_name, store in iter_metadata_stores():
        run = store.load_run(run_id)
        if run:
            if project_name and not run.get("project"):
                run["project"] = project_name
            return run, store
    return None, None
