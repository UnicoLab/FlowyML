---
title: "Types — FlowyML"
description: "API reference for FlowyML type definitions, enums, and data classes."
---

# Types API 📝

FlowyML exposes a set of **shared type definitions** — data classes, enums, and typed configuration objects — that flow through the framework. These types enforce a consistent contract between steps, orchestrators, and storage backends, enabling static analysis, IDE auto-completion, and runtime validation. Understanding these types is key to writing well-typed pipelines and custom plugins.

Type definitions used in flowyml.

## Resource Requirements

::: flowyml.core.resources.ResourceRequirements
    options:
        show_root_heading: false

## Scheduler Config

::: flowyml.core.scheduler_config.SchedulerConfig
    options:
        show_root_heading: false

---

## See Also

- [Assets API](assets.md) — asset types and metadata classes
- [Step API](step.md) — the `Step` class and related type hierarchy
