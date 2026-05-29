---
title: "Artifact Stores — FlowyML"
description: "API reference for FlowyML artifact store backends: local filesystem, GCS, S3, and Azure Blob Storage."
---

# Artifact Stores API 📦

Artifact stores handle the **persistence and retrieval** of step outputs — serialized DataFrames, trained models, evaluation reports, and any other binary or structured data produced during a pipeline run. FlowyML provides a local-filesystem backend for development and cloud backends (GCS, S3, Azure Blob Storage) for production. All implementations share the `ArtifactStore` base interface documented below, so you can swap providers with a single configuration change.

Artifact Stores manage the storage and retrieval of step outputs.

## Base Artifact Store

::: flowyml.storage.artifacts.ArtifactStore
    options:
        show_root_heading: false

## Local Artifact Store

::: flowyml.storage.artifacts.LocalArtifactStore
    options:
        show_root_heading: false

## GCS Artifact Store

::: flowyml.stacks.gcp.GCSArtifactStore
    options:
        show_root_heading: false

---

## See Also

- [Storage API](storage.md) — high-level overview of FlowyML's storage layer
- [Plugins Overview](../plugins/overview.md) — how artifact-store backends are registered as plugins
- [Stack Configuration](../plugins/stack-configuration.md) — configuring storage backends in your stack
