---
title: CLI Quick Start — FlowyML
description: "5-minute guided tutorial to get started with the FlowyML CLI: init, run, visualize, and iterate."
---

<div class="hero-section" markdown>

## 🛠️ CLI Quick Start

Go from zero to a running pipeline in 5 minutes using the FlowyML command line.

<span class="feature-badge">⚡ 5 Minutes</span>
<span class="feature-badge">🌱 Init</span>
<span class="feature-badge">▶️ Run</span>
<span class="feature-badge">🖥️ Visualize</span>

</div>

!!! info "Full Reference"
    This page is a quick-start tutorial. For the complete list of every command, flag, and environment variable, see the **[CLI Reference](../reference/cli.md)**.

## Step 1 — Install FlowyML

```bash
pip install flowyml
```

Verify it worked:

```bash
flowyml --version
```

## Step 2 — Create a Project

```bash
flowyml init my-project
cd my-project
```

This scaffolds everything you need:

```
my-project/
├── flowyml.yaml         # Stack & resource config
├── requirements.txt     # Python dependencies
└── src/
    └── pipeline.py      # Your first pipeline
```

!!! tip "Templates"
    Use `--template ml` or `--template cv` for pre-built ML or Computer Vision project structures.

## Step 3 — Run Your Pipeline

```bash
flowyml run src/pipeline.py
```

You should see:

```
Fetching data...
Processing 5 items...
✓ Pipeline finished successfully!
```

!!! success "That's it!"
    Your pipeline ran locally with caching enabled by default. Run it again — cached steps are skipped automatically.

## Step 4 — Launch the UI

```bash
flowyml ui start
```

Open [http://localhost:8080](http://localhost:8080) to see the DAG visualization, run history, and artifact inspector.

Stop it when you're done:

```bash
flowyml ui stop
```

## Step 5 — Serve or Deploy a Model

Once a pipeline has registered a model, serve it locally (no Docker) or deploy it
to a target:

```bash
# In-process FastAPI server for quick checks
flowyml serve my_model --stage production

# Package + deploy to local Docker / Kubernetes / OpenShift
flowyml deploy my_model --stage production --runtime fastapi --target local_docker

# Inspect and call recorded deployments
flowyml deployment list
flowyml deployment predict my_model-endpoint --json '{"inputs": [[0.1, 0.9, 1.2]]}'
```

See the **[Model Serving & Deployment guide](../guides/model-serving-deployment.md)**
for runtimes, targets, promotion, and batch inference.

## Step 6 — Pass Parameters

Override context values from the command line without changing code:

```bash
flowyml run src/pipeline.py \
  --context dataset_size=100 \
  --context multiplier=5
```

## Step 7 — Try a Dry Run

See what *would* happen without actually executing:

```bash
flowyml run src/pipeline.py --stack production --dry-run
```

## Environment Variables

All FlowyML environment variables use the uppercase `FLOWYML_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOWYML_HOME` | `~/.flowyml` | FlowyML home directory |
| `FLOWYML_ENV` | `dev` | Environment name (`dev`, `staging`, `prod`) |
| `FLOWYML_UI_PORT` | `8080` | Default UI port |
| `FLOWYML_LOG_LEVEL` | `INFO` | Logging level |

## Handy Aliases

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias fml='flowyml'
alias fml-run='flowyml run'
alias fml-ui='flowyml ui start'
```

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 📖 Full CLI Reference
Every command, flag, and environment variable in one place.

[CLI Reference →](../reference/cli.md)

</div>

<div class="header-card" markdown>

### ⚙️ Configuration
Deep dive into flowyml.yaml, stacks, and resource presets.

[Configuration →](configuration.md)

</div>

<div class="header-card" markdown>

### 🎢 Core Concepts
Learn Pipelines, Steps, Context, and Assets in depth.

[Core Concepts →](../core/pipelines.md)

</div>

</div>
