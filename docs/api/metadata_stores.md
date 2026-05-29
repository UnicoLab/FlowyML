---
title: "Metadata Stores — FlowyML"
description: "API reference for FlowyML metadata store backends: SQLite, PostgreSQL, and cloud-managed stores."
---

# Metadata Stores API 🗄️

Metadata stores are the **lineage backbone** of FlowyML. They record every pipeline run, the status of each step, input/output artifact references, and timing information. FlowyML ships with a lightweight SQLite backend for local development and supports PostgreSQL and cloud-managed alternatives for production deployments. All backends implement the `MetadataStore` interface documented below.

Metadata Stores track pipeline runs, step status, and artifact lineage.

## Base Metadata Store

::: flowyml.storage.metadata.MetadataStore
    options:
        show_root_heading: false

## SQLite Metadata Store

::: flowyml.storage.metadata.SQLiteMetadataStore
    options:
        show_root_heading: false

---

## See Also

- [Artifact Stores API](artifact_stores.md) — the companion storage layer for binary step outputs
- [Plugins Overview](../plugins/overview.md) — how metadata-store backends are registered as plugins
