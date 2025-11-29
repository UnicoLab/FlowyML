# CLI Reference 💻

Command-line interface for flowyml.

## Usage

```bash
flowyml [COMMAND] [OPTIONS]
```

## Commands

### `init`

Initialize a new flowyml project.

```bash
flowyml init [PROJECT_NAME]
```

### `run`

Run a pipeline.

```bash
flowyml run [PIPELINE_FILE]
```

### `stack`

Manage infrastructure stacks.

```bash
flowyml stack list
flowyml stack register [NAME]
flowyml stack set [NAME]
```

### `ui`

Start the dashboard.

```bash
flowyml ui --port 8080
```
