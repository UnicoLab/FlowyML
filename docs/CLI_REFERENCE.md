# 🎯 Flowy CLI Quick Reference

Quick reference guide for common Flowy CLI commands.

## 📦 Installation

```bash
# Basic installation
pip install flowy

# With UI support (recommended)
pip install "flowy[ui]"

# Everything
pip install "flowy[all]"
```

### Development Mode

If you're developing Flowy and get `zsh: command not found: flowy`:

```bash
# Install in editable mode (from repo root)
pip install -e ".[ui]"

# Now 'flowy' command works
flowy ui start

# Or run without installing:
python -m flowy.cli.main ui start
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for more details.


---

## 🚀 Getting Started

### Initialize a New Project

```bash
# Interactive project creation
flowy init

# With options
flowy init --name my_project --template pytorch --dir ./projects
```

**Templates:**
- `basic` - Basic pipeline template
- `pytorch` - PyTorch ML pipeline
- `tensorflow` - TensorFlow ML pipeline
- `sklearn` - scikit-learn pipeline

---

## 🖥️ UI Server Commands

### Start UI Server

```bash
# Default (localhost:8080)
flowy ui start

# Custom port
flowy ui start --port 3000

# Custom host (for remote access)
flowy ui start --host 0.0.0.0 --port 8080

# Development mode (auto-reload)
flowy ui start --dev

# Start and open browser
flowy ui start --open-browser
flowy ui start -o  # Short form
```

### Check UI Status

```bash
# Check if running
flowy ui status

# Check specific host/port
flowy ui status --host localhost --port 3000
```

### Stop UI Server

```bash
flowy ui stop
# This will show instructions for stopping the server
```

---

## 🏃 Running Pipelines

### Run a Pipeline

```bash
# Run pipeline from Python file
flowy run my_pipeline

# With custom stack
flowy run my_pipeline --stack aws

# With context parameters
flowy run my_pipeline --context learning_rate=0.01 --context epochs=20
flowy run my_pipeline -c lr=0.01 -c epochs=20  # Short form

# Debug mode
flowy run my_pipeline --debug
```

---

## 🧪 Experiment Tracking

### List Experiments

```bash
# List recent experiments
flowy experiment list

# Limit results
flowy experiment list --limit 20

# Filter by pipeline
flowy experiment list --pipeline training_pipeline
```

### Compare Runs

```bash
# Compare multiple runs
flowy experiment compare run_abc123 run_def456 run_ghi789
```

---

## 📚 Stack Management

### List Stacks

```bash
flowy stack list
```

**Available stacks:**
- `local` - Local execution (default)
- `aws` - AWS (SageMaker, S3, Step Functions)
- `gcp` - Google Cloud (Vertex AI, GCS)
- `azure` - Azure (ML, Blob Storage)

### Switch Stack

```bash
flowy stack switch production
flowy stack switch local
```

---

## 💾 Cache Management

### View Cache Statistics

```bash
flowy cache stats
```

### Clear Cache

```bash
# Clear all cache (with confirmation)
flowy cache clear

# Force clear without confirmation
flowy cache clear --yes
```

---

## ⚙️ Configuration

### View Configuration

```bash
flowy config
```

This shows:
- Flowy home directory
- Artifacts directory
- Metadata database path
- Default stack
- Caching settings
- Log level
- UI port
- Debug mode

---

## 📝 Logs

### View Pipeline Logs

```bash
# View logs for a run
flowy logs run_abc123

# Filter by step
flowy logs run_abc123 --step train_model

# Tail last N lines
flowy logs run_abc123 --tail 50
```

---

## 🔧 Troubleshooting Commands

### Check UI is Running

```bash
flowy ui status
```

### Verify Installation

```bash
flowy --version
```

### View Configuration

```bash
flowy config
```

### Check Health

```bash
# If UI is running, check health endpoint
curl http://localhost:8080/api/health
```

---

## 💡 Common Workflows

### Development Workflow

```bash
# 1. Start UI server in background
nohup flowy ui start > flowy_ui.log 2>&1 &

# 2. Check it's running
flowy ui status

# 3. Run your pipeline
python my_pipeline.py

# 4. View in browser at http://localhost:8080

# 5. View logs if needed
tail -f flowy_ui.log
```

### Production Deployment

```bash
# 1. Switch to production stack
flowy stack switch production

# 2. Run pipeline
flowy run training_pipeline --stack production

# 3. Monitor via UI
flowy ui start --host 0.0.0.0 --port 80
```

### Experiment Comparison

```bash
# 1. Run multiple experiments
flowy run my_pipeline -c lr=0.001
flowy run my_pipeline -c lr=0.01
flowy run my_pipeline -c lr=0.1

# 2. List experiments
flowy experiment list

# 3. Compare runs
flowy experiment compare <run_id_1> <run_id_2> <run_id_3>
```

---

## 🆘 Getting Help

### General Help

```bash
flowy --help
```

### Command-Specific Help

```bash
flowy ui --help
flowy ui start --help
flowy run --help
flowy experiment --help
```

---

## 📖 Documentation Links

- **Full UI Guide**: [UI_GUIDE.md](UI_GUIDE.md)
- **Main README**: [README.md](README.md)
- **Design Document**: [DESIGN.md](DESIGN.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Frontend Docs**: [flowy/ui/frontend/README.md](flowy/ui/frontend/README.md)

---

## 🎨 Advanced Usage

### Background UI Server

```bash
# Start in background
nohup flowy ui start --port 8080 > flowy_ui.log 2>&1 &

# Check process
ps aux | grep "flowy ui"

# View logs
tail -f flowy_ui.log

# Stop background server
pkill -f "flowy ui start"
```

### Environment Variables

```bash
# Set custom UI port
export FLOWY_UI_PORT=3000

# Set UI host
export FLOWY_UI_HOST=0.0.0.0

# Enable debug mode
export FLOWY_DEBUG=true

# Then start
flowy ui start
```

### Multiple Environments

```bash
# Development
flowy ui start --port 8080 --dev

# Staging  
flowy ui start --port 8081 --host 0.0.0.0

# Production
flowy ui start --port 80 --host 0.0.0.0
```

---

## ✅ Checklist: First Time Setup

- [ ] Install Flowy: `pip install "flowy[ui]"`
- [ ] Install Node.js (for UI frontend)
- [ ] Build frontend: `cd flowy/ui/frontend && npm install && npm run build`
- [ ] Start UI: `flowy ui start`
- [ ] Check status: `flowy ui status`
- [ ] Visit: http://localhost:8080
- [ ] Run test pipeline: `python examples/basic_pipeline.py`
- [ ] View in UI

---

## 🎯 Quick Tips

1. **Always check UI status** before running pipelines:
   ```bash
   flowy ui status
   ```

2. **Use `--open-browser` flag** to auto-open UI:
   ```bash
   flowy ui start -o
   ```

3. **Run UI in background** for long sessions:
   ```bash
   nohup flowy ui start > flowy_ui.log 2>&1 &
   ```

4. **Use context parameters** for experiments:
   ```bash
   flowy run my_pipeline -c param1=value1 -c param2=value2
   ```

5. **Check configuration** when troubleshooting:
   ```bash
   flowy config
   ```

---

For more detailed information, see the [Full UI Guide](UI_GUIDE.md).
