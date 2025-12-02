"""Backend dependencies."""

import os
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
