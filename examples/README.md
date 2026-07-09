# FlowyML Examples

Runnable examples for every major FlowyML feature — from a 20-line pipeline to a
complete **train → register → promote → serve → batch** production loop.

Unless noted otherwise, every example runs with just the core install and no
configuration:

```bash
pip install flowyml
python examples/simple_pipeline.py
```

> **Tip:** run examples from the repository root (as shown). Examples that read
> `data.csv` resolve it relative to the repo, so they also work from any
> directory.

## Start here (concrete, end-to-end projects)

If you want a *real project* to copy, start with these:

| Project | What you get | Extra deps |
|---------|--------------|------------|
| [`production_serving/`](production_serving/) | **Flagship.** Train two model flavors, register with lineage, champion/challenger promotion, serve online (FastAPI) and score in batch. Switches from laptop → Azure ML + OpenShift by changing one stack. | none (Docker only for the local container serve) |
| [`training_pipeline.py`](training_pipeline.py) | A Keras regression pipeline: load CSV → build model → train (auto-tracked) → evaluate → conditional deploy. | `flowyml[tensorflow]` |
| [`enterprise_stack_registry/`](enterprise_stack_registry/) | The *same* pipeline code running on different stacks selected by environment. | none |

## All examples

### Core pipelines (run out-of-the-box)

| Example | Demonstrates | Run |
|---------|--------------|-----|
| [`simple_pipeline.py`](simple_pipeline.py) | The smallest possible pipeline: `@step`, context injection, execution. | `python examples/simple_pipeline.py` |
| [`clean_pipeline.py`](clean_pipeline.py) | An infrastructure-agnostic pipeline written in idiomatic style. | `python examples/clean_pipeline.py` |
| [`conditional_pipeline.py`](conditional_pipeline.py) | Conditional step execution based on params and data values. | `python examples/conditional_pipeline.py` |
| [`caching_pipeline.py`](caching_pipeline.py) | Caching strategies (`code_hash`, `input_hash`, disabled) + cache stats. | `python examples/caching_pipeline.py` |
| [`step_grouping_example.py`](step_grouping_example.py) | Grouping steps to cut overhead and aggregate resource requests. | `python examples/step_grouping_example.py` |
| [`resources_example.py`](resources_example.py) | Declaring CPU / memory / GPU resource requirements per step. | `python examples/resources_example.py` |
| [`advanced_orchestration.py`](advanced_orchestration.py) | Lifecycle hooks (`@on_pipeline_start`/`end`) and retry policies. | `python examples/advanced_orchestration.py` |
| [`pipeline_showcase.py`](pipeline_showcase.py) | Complex DAG branching, multi-asset outputs, deep dependencies. | `python examples/pipeline_showcase.py` |
| [`demo_pipeline.py`](demo_pipeline.py) | Assets (Dataset/Model/Metrics/FeatureSet), caching, monitoring, UI links. | `python examples/demo_pipeline.py` |
| [`complete_demo.py`](complete_demo.py) | Feature tour: versioning, projects, notifications, leaderboards, templates, drift, scheduling. | `python examples/complete_demo.py` |
| [`examples.py`](examples.py) | Five bite-size examples (basic, assets/lineage, caching, experiments, complex DAG). | `python examples/examples.py` |

### UI integration (run out-of-the-box)

| Example | Demonstrates | Run |
|---------|--------------|-----|
| [`simple_pipeline_ui.py`](simple_pipeline_ui.py) | A simple pipeline that emits clickable run URLs for the dashboard. | `python examples/simple_pipeline_ui.py` |
| [`ui_integration_example.py`](ui_integration_example.py) | Real-time logging, progress and live metric updates to the UI. | `python examples/ui_integration_example.py` |

Start the dashboard in another terminal to follow runs live:

```bash
flowyml ui start        # then open the printed http://localhost:8080/runs/<id>
```

### GenAI observability

| Example | Demonstrates | Extra deps |
|---------|--------------|------------|
| [`generic_observability.py`](generic_observability.py) | Framework-agnostic tracing (`span`, `trace`, `log_llm_call`) for any stack. | none |
| [`chatbot_session.py`](chatbot_session.py) | Multi-turn session tracking with token/cost/latency aggregation + event streaming. | none |
| [`session_eval.py`](session_eval.py) | Auto-evaluating each chat turn with scorers (uses a mock scorer, no API key). | none |
| [`openai_observability.py`](openai_observability.py) | Tracing the OpenAI SDK directly (client, patch, streaming, decorator). | `flowyml[openai]` + `OPENAI_API_KEY` |
| [`langchain_observability.py`](langchain_observability.py) | Tracing LangChain chains/runnables. | `flowyml[langchain] langchain-openai` + `OPENAI_API_KEY` |
| [`langgraph_observability.py`](langgraph_observability.py) | Tracing LangGraph agents (callback, context manager, decorator, instrument). | `flowyml[langgraph] langchain-openai` + `OPENAI_API_KEY` |

Examples needing an optional package or an API key **exit cleanly with install
instructions** when those are missing — they never crash.

### Evaluation framework — [`evaluations/`](evaluations/)

| Example | Demonstrates | Extra deps |
|---------|--------------|------------|
| [`classical_ml_eval.py`](evaluations/classical_ml_eval.py) | Accuracy/F1/precision scorers on classical predictions. | none |
| [`genai_eval.py`](evaluations/genai_eval.py) | GenAI scorers over traces/datasets. | none |
| [`custom_judge.py`](evaluations/custom_judge.py) | Writing a custom `Scorer`. | none |
| [`pipeline_eval.py`](evaluations/pipeline_eval.py) | Embedding evaluation as a pipeline step. | none |
| [`ci_assertions.py`](evaluations/ci_assertions.py) | `EvalAssert` quality gates for CI/CD. | none |
| [`adapter_example.py`](evaluations/adapter_example.py) | Third-party scorer adapters (Ragas/Phoenix/DeepEval). | requires those SDKs |

### Model training with deep-learning frameworks

| Example | Demonstrates | Extra deps |
|---------|--------------|------------|
| [`training_pipeline.py`](training_pipeline.py) | Keras regression pipeline with auto-tracked training + conditional deploy. | `flowyml[tensorflow]` |
| [`training_pipeline_dataset.py`](training_pipeline_dataset.py) | Same, loading data via `tf.data.Dataset`. | `flowyml[tensorflow]` |

### Stacks, deployment & plugins

| Example | Demonstrates | Extra deps |
|---------|--------------|------------|
| [`production_serving/`](production_serving/) | Full production loop (see **Start here**). | none (+ Docker for local serve) |
| [`enterprise_stack_registry/`](enterprise_stack_registry/) | One pipeline, many stacks selected by environment. | none |
| [`custom_components/`](custom_components/) | Registering custom orchestrator/registry components + packaging template. | none |
| [`plugins/`](plugins/) | Verifying an Airflow integration via the generic bridge. | none |
| [`fastapi_remote_logging/`](fastapi_remote_logging/) | Streaming pipeline logs to a remote FastAPI collector. | `fastapi uvicorn` |
| [`gcp_stack/`](gcp_stack/) | Running training on a GCP (Vertex AI) stack + local↔GCP switching. | `flowyml[gcp]` + GCP credentials |

## Viewing results in the UI

1. Start the dashboard: `flowyml ui start`
2. Run any example.
3. Click the `http://localhost:8080/runs/<run_id>` URL printed in the console.
4. Explore run status, step details, assets, metrics, and lineage.

## Need help?

- 📖 [Documentation](../docs/)
- 💬 [GitHub Discussions](https://github.com/UnicoLab/FlowyML/discussions)
- 🐛 [Report issues](https://github.com/UnicoLab/FlowyML/issues)
