# Flowy Examples

This directory contains example pipelines demonstrating various Flowy features.

## Quick Start

### 1. Simple Pipeline
The most basic Flowy pipeline to get started:

```bash
python examples/simple_pipeline.py
```

**Features demonstrated:**
- Basic pipeline creation
- Step definition with `@step` decorator
- Automatic context injection
- Pipeline execution

### 2. Demo Pipeline (Comprehensive)
A complete ML pipeline showcasing all major features:

```bash
# Start the UI first (optional but recommended)
flowy ui start

# Run the demo pipeline
python examples/demo_pipeline.py
```

**Features demonstrated:**
- Asset management (Dataset, Model, Metrics, FeatureSet)
- Multiple steps with dependencies
- Caching strategies
- Conditional execution
- Monitoring and alerts
- UI integration with clickable run URLs

### 3. Conditional Execution
Learn how to use conditional steps:

```bash
python examples/conditional_pipeline.py
```

**Features demonstrated:**
- Conditional step execution based on context parameters
- Conditional step execution based on data values
- Skipped step tracking

### 4. Caching Strategies
Explore different caching approaches:

```bash
python examples/caching_pipeline.py
```

**Features demonstrated:**
- Code hash caching (default)
- Input hash caching
- Disabling cache for specific steps
- Cache statistics and monitoring

## Viewing Results in the UI

1. **Start the UI server:**
   ```bash
   flowy ui start
   ```

2. **Run any example pipeline**

3. **Click the URL printed in the console** (e.g., `http://localhost:8080/runs/<run_id>`)

4. **Explore:**
   - Real-time run status
   - Step execution details
   - Artifacts and assets
   - Metrics and performance

## Next Steps

- Check out the [documentation](../docs/) for more details
- Explore the [tutorials](../docs/tutorials/) for advanced use cases
- Read the [API reference](../docs/api/) for complete API documentation

## Need Help?

- 📖 [Documentation](../README.md)
- 💬 [GitHub Discussions](https://github.com/flowy/flowy/discussions)
- 🐛 [Report Issues](https://github.com/flowy/flowy/issues)
