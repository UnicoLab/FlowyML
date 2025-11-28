# Debugging Tools 🐛

UniFlow provides interactive debugging tools that let you pause pipelines, inspect state, and fix issues without restarting from scratch.

> [!NOTE]
> **What you'll learn**: How to debug pipelines like standard Python code
>
> **Key insight**: Distributed pipelines are notoriously hard to debug. UniFlow brings the "IDE experience" to pipelines.

## Why Interactive Debugging Matters

**The old way (Airflow/Kubeflow)**:
1. Push code
2. Wait 10 mins for container build
3. Wait 20 mins for pipeline to fail
4. Read logs: `KeyError: 'x'`
5. Add print statement, repeat

**The UniFlow way**:
1. Set a breakpoint: `debugger.add_breakpoint(...)`
2. Run pipeline locally
3. Execution pauses at the error
4. Inspect variables, fix code, resume

## Debugging Strategies

| Strategy | Tool | Use When |
|----------|------|----------|
| **Interactive** | `StepDebugger` | You need to inspect variables mid-execution |
| **Tracing** | `PipelineDebugger` | You need to see the sequence of events and timing |
| **Post-Mortem** | `analyze_errors` | A run already failed and you want to know why |

## Overview ℹ️

UniFlow provides comprehensive debugging tools:
- **StepDebugger**: Debug individual steps with breakpoints and inspection
- **PipelineDebugger**: Debug entire pipelines with execution tracing
- **Utility Functions**: Quick debugging helpers

## Step Debugging 🐞

### Basic Usage

```python
from uniflow import StepDebugger, step

@step(outputs=["result"])
def process_data(data):
    return [x * 2 for x in data]

# Create debugger
debugger = StepDebugger(process_data)

# Set breakpoint
debugger.add_breakpoint(
    condition=lambda inputs: len(inputs['data']) > 100,
    action=lambda step, inputs: print(f"Large dataset: {len(inputs['data'])} items")
)

### Real-World Pattern: Conditional Breakpoint

Stop execution only when data looks weird.

```python
from uniflow import StepDebugger, step

@step
def process_data(batch):
    # ... complex logic ...
    return result

# Debug specific edge case
debugger = StepDebugger(process_data)

# "Stop if we get an empty batch"
debugger.add_breakpoint(
    condition=lambda inputs: len(inputs['batch']) == 0,
    action=lambda step, inputs: print(f"⚠️ Empty batch detected in {step.name}!")
)

# Run pipeline - it will pause ONLY if the condition is met
pipeline.run(debugger=debugger)
```

### Inspecting Inputs and Outputs

```python
# Inspect inputs before execution
debugger.inspect_inputs(data=[1, 2, 3])
# Output: {'data': [1, 2, 3]}

# Execute and inspect output
result = debugger.debug_execute(data=[1, 2, 3])
debugger.inspect_output()
# Output: [2, 4, 6]
```

### Breakpoints

```python
# Conditional breakpoint
debugger.add_breakpoint(
    condition=lambda inputs: inputs.get('threshold', 0) > 10,
    action=lambda step, inputs: print(f"⚠️ High threshold: {inputs['threshold']}")
)

# Always-trigger breakpoint
debugger.add_breakpoint(
    action=lambda step, inputs: print(f"Executing {step.name}")
)

# Remove breakpoints
debugger.clear_breakpoints()
```

### Exception Debugging

```python
@step(outputs=["result"])
def failing_step(data):
    if len(data) == 0:
        raise ValueError("Empty data")
    return data[0]

debugger = StepDebugger(failing_step)

try:
    result = debugger.debug_execute(data=[])
except Exception as e:
    # Get detailed traceback
    debugger.debug_exception(e)
    # Shows: exception type, message, inputs that caused it
```

## Pipeline Debugging 🕸️

### Tracing Execution

```python
from uniflow import PipelineDebugger, Pipeline

pipeline = Pipeline("my_pipeline")
pipeline.add_step(load)
pipeline.add_step(transform)
pipeline.add_step(save)

# Create debugger
debugger = PipelineDebugger(pipeline)

# Enable tracing
debugger.enable_tracing()

# Run with tracing
result = pipeline.run()

# View execution trace
trace = debugger.get_trace()
for entry in trace:
    print(f"{entry['timestamp']}: {entry['step_name']} - {entry['event']}")
```

### Profiling

```python
# Profile pipeline execution
debugger.enable_profiling()
result = pipeline.run()

# Get profile report
profile = debugger.get_profile()
for step_name, metrics in profile.items():
    print(f"{step_name}:")
    print(f"  Duration: {metrics['duration_seconds']:.2f}s")
    print(f"  Memory: {metrics['memory_mb']:.1f}MB")
    print(f"  CPU: {metrics['cpu_percent']:.1f}%")
```

### DAG Visualization

```python
# Visualize pipeline structure
debugger.visualize_dag(output_path="pipeline_dag.png")

# Or get DOT format
dot = debugger.get_dag_dot()
print(dot)
```

### Error Analysis

```python
# After failed run
if not result.success:
    analysis = debugger.analyze_errors(result)

    print(f"Failed steps: {analysis['failed_steps']}")
    print(f"Error types: {analysis['error_types']}")
    print(f"Common patterns: {analysis['patterns']}")
```

### Execution Replay

```python
# Replay a previous run
debugger.replay_execution(run_id="abc123")

# Replay with modifications
debugger.replay_execution(
    run_id="abc123",
    override_inputs={"step1": {"new_param": "value"}}
)
```

## Quick Debugging Utilities 🛠️

### debug_step

```python
from uniflow.utils.debug import debug_step

@step(outputs=["result"])
def my_step(data):
    return process(data)

# Quick debug - prints inputs/outputs
result = debug_step(my_step, data=[1, 2, 3])
# Output:
# 🔍 Debugging: my_step
# 📥 Inputs: {'data': [1, 2, 3]}
# 📤 Output: [2, 4, 6]
# ⏱️ Duration: 0.001s
```

### trace_step

```python
from uniflow.utils.debug import trace_step

# Trace step execution
@trace_step
@step(outputs=["result"])
def traced_step(data):
    return process(data)

# Automatically prints:
# → Entering traced_step
# ← Exiting traced_step (0.001s)
```

### profile_step

```python
from uniflow.utils.debug import profile_step

# Profile step performance
stats = profile_step(my_step, data=[1, 2, 3])
print(f"Execution time: {stats['time']:.3f}s")
print(f"Memory used: {stats['memory_mb']:.1f}MB")
```

## Best Practices 💡

### 1. Use Conditional Breakpoints

```python
# Only break on interesting cases
debugger.add_breakpoint(
    condition=lambda inputs: inputs['value'] < 0,
    action=lambda step, inputs: print(f"⚠️ Negative value: {inputs['value']}")
)
```

### 2. Enable Tracing for Production Issues

```python
# Enable tracing when issues occur
if environment == "production":
    if detect_anomaly():
        debugger.enable_tracing()
        result = pipeline.run()
        trace = debugger.get_trace()
        send_to_monitoring(trace)
```

### 3. Profile Before Optimization

```python
# Identify bottlenecks
debugger.enable_profiling()
result = pipeline.run()

profile = debugger.get_profile()
slowest = max(profile.items(), key=lambda x: x[1]['duration_seconds'])
print(f"Bottleneck: {slowest[0]} ({slowest[1]['duration_seconds']:.2f}s)")
```

### 4. Combine with Logging

```python
import logging

logger = logging.getLogger(__name__)

debugger.add_breakpoint(
    action=lambda step, inputs: logger.info(
        f"Executing {step.name} with {len(inputs)} inputs"
    )
)
```

## Advanced Usage ⚡

### Custom Breakpoint Actions

```python
def save_snapshot(step, inputs):
    """Save inputs to file for later analysis"""
    import pickle
    with open(f"snapshot_{step.name}.pkl", "wb") as f:
        pickle.dump(inputs, f)
    print(f"💾 Saved snapshot for {step.name}")

debugger.add_breakpoint(
    condition=lambda inputs: should_save(inputs),
    action=save_snapshot
)
```

### Programmatic Error Handling

```python
class DebugHandler:
    def __init__(self):
        self.errors = []

    def handle_error(self, step, inputs, exception):
        self.errors.append({
            'step': step.name,
            'inputs': inputs,
            'error': str(exception)
        })
        # Send alert
        alert_team(f"Error in {step.name}: {exception}")

handler = DebugHandler()

debugger.add_breakpoint(
    action=lambda step, inputs: handler.handle_error(step, inputs, None)
)
```

## API Reference 📚

### StepDebugger

```python
StepDebugger(step: Step)
```

**Methods**:
- `debug_execute(**inputs) -> Any` - Execute with debugging
- `inspect_inputs(**inputs) -> Dict` - Inspect inputs
- `inspect_output() -> Any` - Inspect last output
- `add_breakpoint(action, condition=None)` - Add breakpoint
- `clear_breakpoints()` - Remove all breakpoints
- `debug_exception(exception)` - Analyze exception

### PipelineDebugger

```python
PipelineDebugger(pipeline: Pipeline)
```

**Methods**:
- `enable_tracing()` - Enable execution tracing
- `enable_profiling()` - Enable performance profiling
- `get_trace() -> List[Dict]` - Get execution trace
- `get_profile() -> Dict` - Get performance profile
- `visualize_dag(output_path: str)` - Visualize pipeline
- `analyze_errors(result) -> Dict` - Analyze failed run
- `replay_execution(run_id, override_inputs=None)` - Replay run

### Utility Functions

**debug_step(step, **inputs)**:
- Executes step with detailed logging
- Returns: step output

**trace_step(func)**:
- Decorator for automatic tracing
- Prints entry/exit with timing

**profile_step(step, **inputs)**:
- Profiles step execution
- Returns: Dict with timing and memory stats
