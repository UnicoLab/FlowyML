# CLI Reference 💻

Command-line interface for UniFlow.

## Usage

```bash
uniflow [COMMAND] [OPTIONS]
```

## Commands

### `init`

Initialize a new UniFlow project.

```bash
uniflow init [PROJECT_NAME]
```

### `run`

Run a pipeline.

```bash
uniflow run [PIPELINE_FILE]
```

### `stack`

Manage infrastructure stacks.

```bash
uniflow stack list
uniflow stack register [NAME]
uniflow stack set [NAME]
```

### `ui`

Start the dashboard.

```bash
uniflow ui --port 8080
```
