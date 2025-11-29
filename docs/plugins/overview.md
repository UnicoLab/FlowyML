# flowyml Plugin System

flowyml features a robust, ecosystem-agnostic plugin system designed to seamlessly integrate components from various ML and data frameworks, including ZenML, Airflow, and Prefect.

## Key Features

- **Generic Integration Bridge**: A universal wrapper system that adapts external components (like ZenML orchestrators or Airflow operators) to flowyml's interface using rule-based configuration. No hardcoded dependencies!
- **Zero-Code Integration**: Use components from other frameworks just by defining a simple YAML configuration.
- **Unified Management**: Discover, install, and manage plugins via a consistent CLI.
- **Stack Migration**: Automatically migrate existing stacks (e.g., from ZenML) to flowyml.

## Architecture

The plugin system is built on three core pillars:

1.  **Component Registry**: The central hub that manages all available components, including built-ins, plugins, and bridged components.
2.  **Generic Bridge (`GenericBridge`)**: A smart adapter that uses introspection and configuration rules to "teach" flowyml how to talk to external components.
3.  **Plugin Configuration**: YAML-based definitions that map external classes and methods to flowyml's expected behavior.

## Quick Start

### Listing Plugins

View all installed and available plugins:

```bash
flowyml plugin list
```

### Searching for Plugins

Find plugins for specific tools or categories:

```bash
flowyml plugin search kubernetes
flowyml plugin search airflow
```

### Installing Plugins

Install a plugin directly from PyPI:

```bash
flowyml plugin install zenml-kubernetes
```

### Importing External Stacks

Migrate an existing ZenML stack to flowyml:

```bash
flowyml plugin import-zenml-stack my-zenml-stack
```

This will generate a `flowyml.yaml` configuration file with all the necessary plugin mappings, ready to run!
