---
title: "Storage API — FlowyML"
description: "API reference for FlowyML's storage backends: local filesystem, GCS, S3, and Azure Blob Storage."
---

# Storage API Reference

FlowyML uses a pluggable storage layer that separates **artifact storage** (binary outputs of each step) from **metadata storage** (run history, step status, and lineage graphs). Every backend implements a common interface, so you can swap providers — local disk during development, cloud object stores in production — without changing pipeline code.

Storage backends for flowyml:

- [Artifact Stores](artifact_stores.md): Storage for step outputs (GCS, Local, etc.)
- [Metadata Stores](metadata_stores.md): Storage for run metadata and lineage (SQLite, etc.)

---

## See Also

- [Artifact Stores API](artifact_stores.md) — detailed reference for every artifact-store backend
- [Plugins Overview](../plugins/overview.md) — how storage backends are registered as plugins
