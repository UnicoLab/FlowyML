# 👋 START HERE - Flowy UI Documentation

## Your Question Answered ✅

**Q: How do I use `flowy ui start` in development mode?**

**A: Install the package in editable mode first:**

```bash
cd /Users/piotrlaczkowski/Desktop/PROJECT/UnicoLab/Repositories/Flowy
pip install -e ".[ui]"
```

Now the `flowy` command will work!

**Alternative (no installation):**
```bash
python -m flowy.cli.main ui start
```

---

## 📖 Complete Documentation Available

I've created comprehensive documentation for the Flowy UI system:

### 🎯 Quick Links

1. **[SUMMARY.md](SUMMARY.md)** ⭐ **START HERE** - Overview of everything
2. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Solves your `command not found` issue
3. **[CHEATSHEET.md](CHEATSHEET.md)** - Quick reference for common commands
4. **[UI_GUIDE.md](UI_GUIDE.md)** - Complete UI usage guide
5. **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - All CLI commands
6. **[UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)** - Architecture diagrams

---

## 🚀 Quick Start

### Step 1: Install in Development Mode
```bash
pip install -e ".[ui]"
```

### Step 2: Build Frontend (One-Time)
```bash
cd flowy/ui/frontend
npm install && npm run build
cd ../../..
```

### Step 3: Start UI Server
```bash
flowy ui start --open-browser
```

### Step 4: Run a Pipeline
```bash
python examples/ui_integration_example.py
```

---

## 📚 Documentation Structure

```
Documentation Files:
├── SUMMARY.md                     ⭐ Read this first - complete overview
├── DEVELOPMENT.md                 ⭐ Your issue solution + dev guide
├── CHEATSHEET.md                  → Quick command reference
├── UI_GUIDE.md                    → Complete UI usage guide
├── CLI_REFERENCE.md               → All CLI commands
├── UI_ARCHITECTURE.md             → System architecture
├── UI_INTEGRATION_SUMMARY.md      → Integration details
├── README.md                      → Main project README (updated)
└── QUICKSTART.md                  → Quick start guide (updated)
```

---

## 💡 Key Points

### Problem: `zsh: command not found: flowy`

**Cause**: The package isn't installed, so the CLI command isn't available.

**Solution 1 (Recommended):**
```bash
pip install -e ".[ui]"  # Editable install
flowy ui start          # Now works!
```

**Solution 2 (Alternative):**
```bash
python -m flowy.cli.main ui start  # No install needed
```

### How the UI Works

1. **Backend**: FastAPI server serves API and static files
2. **Frontend**: React app built with Vite
3. **Connection**: Frontend calls backend API endpoints
4. **Integration**: Pipelines automatically connect when backend is running

### Usage Modes

- **Manual**: `flowy ui start` (run when needed)
- **Background**: `nohup flowy ui start &` (always available)
- **Auto-start**: Coming soon (like ZenML)

---

## 🎯 What I Created

### New Files
- `flowy/ui/utils.py` - UI utility functions
- `examples/ui_integration_example.py` - Working example
- 7 comprehensive documentation files

### Updated Files
- `flowy/ui/__init__.py` - Exports utilities
- `flowy/cli/main.py` - Enhanced UI commands
- `README.md` - Added UI section and troubleshooting
- `QUICKSTART.md` - Added UI setup
- `flowy/ui/frontend/README.md` - Detailed frontend guide

### New CLI Commands
- `flowy ui status` - Check if running
- `flowy ui start --open-browser` - Auto-open browser

---

## ✅ Everything You Need

### For Development
→ Read [DEVELOPMENT.md](DEVELOPMENT.md)

### For Using the UI
→ Read [UI_GUIDE.md](UI_GUIDE.md)

### For Quick Reference
→ Read [CHEATSHEET.md](CHEATSHEET.md)

### For Understanding the System
→ Read [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)

### For a Complete Overview
→ Read [SUMMARY.md](SUMMARY.md)

---

## 🔗 Quick Commands Reference

```bash
# Installation
pip install -e ".[ui]"

# UI Server
flowy ui start              # Start server
flowy ui start --dev        # Dev mode (auto-reload)
flowy ui start -o           # Start and open browser
flowy ui status             # Check status

# Alternative (no install)
python -m flowy.cli.main ui start
```

---

## 📞 Need Help?

All common issues are documented in:
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development issues
- [UI_GUIDE.md#troubleshooting](UI_GUIDE.md#troubleshooting) - UI issues
- [README.md#troubleshooting](README.md#troubleshooting) - General issues

---

**Next Step: Read [SUMMARY.md](SUMMARY.md) for the complete overview!** 🚀
