# flowyml Examples

This directory contains example pipelines demonstrating various flowyml features.

## Quick Start

### 1. Simple Pipeline
The most basic flowyml pipeline to get started:

```bash
# Recommendation: use poetry to ensure all dependencies are available
poetry run python examples/simple_pipeline.py
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
# Recommend using poetry run for the CLI as well
poetry run flowyml ui start

# Run the demo pipeline
poetry run python examples/demo_pipeline.py
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
poetry run python examples/conditional_pipeline.py
```

**Features demonstrated:**
- Conditional step execution based on context parameters
- Conditional step execution based on data values
- Skipped step tracking

### 4. Pipeline Showcase (Complex)
A sophisticated pipeline with branching and multi-asset handling:

```bash
python examples/pipeline_showcase.py
```

**Features demonstrated:**
- Complex DAG branching
- Multi-asset outputs (tuple and dict)
- Advanced condition logic
- Deep dependency management

### 5. UI Integration
How to monitor your pipelines in real-time:

```bash
python examples/ui_integration_example.py
```

**Features demonstrated:**
- Real-time logging to the UI
- Progress tracking
- Live metric updates
- Interactive dashboard integration

### 6. Step Grouping (Optimization)
Optimize your resources by grouping steps together:

```bash
python examples/step_grouping_example.py
```

**Features demonstrated:**
- Reduced overhead for small steps
- Subgrouping of non-consecutive steps
- Aggregated resource requirements (CPU, Memory)

### 7. Advanced Orchestration
Lifecycle hooks and error handling:

```bash
python examples/advanced_orchestration.py
```

**Features demonstrated:**
- `@on_pipeline_start` and `@on_pipeline_end` hooks
- `OrchestratorRetryPolicy` for robust runs
### 8. Caching Strategies
Explore different caching approaches:

```bash
python examples/caching_pipeline.py
```

**Features demonstrated:**
- Code hash caching (default)
- Input hash caching
- Disabling cache for specific steps
- Cache statistics and monitoring

### 9. Complete Demo (Giant)
The ultimate tour of FlowyML features:

```bash
python examples/complete_demo.py
```

**Features demonstrated:**
- Project management & Multi-tenancy
- Pipeline versioning
- Model Leaderboards
- Data Drift Detection
- Notifications (Slack/Console)
- Scheduling (demo only)

## Viewing Results in the UI

1. **Start the UI server:**
   ```bash
   flowyml ui start
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
- 💬 [GitHub Discussions](https://github.com/UnicoLab/FlowyML/discussions)
- 🐛 [Report Issues](https://github.com/UnicoLab/FlowyML/issues)
