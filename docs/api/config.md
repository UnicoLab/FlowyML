---
title: "Configuration — FlowyML"
description: "API reference for FlowyML configuration classes and settings."
---

# Configuration API ⚙️

FlowyML pipelines are configured through a combination of a `flowyml.yaml` file, environment variables, and Python configuration classes. The configuration system validates settings at startup, resolves environment-variable overrides, and exposes typed accessors so that every component — orchestrator, storage backend, monitoring — receives its parameters in a consistent, type-safe way.

Reference for `flowyml.yaml` and environment variables.

## Stack Configuration

::: flowyml.utils.validation.StackConfig
    options:
        show_root_heading: false

## General Configuration

::: flowyml.utils.config
    options:
        show_root_heading: false

---

## See Also

- [Configuration Guide](../user-guide/configuration.md) — step-by-step walkthrough of `flowyml.yaml` options and environment variables
