# FlowyML Evaluation Examples

This directory contains example scripts demonstrating the FlowyML evaluation framework.

## Examples

| Script | Description |
|---|---|
| `classical_ml_eval.py` | Classification and regression evaluation with built-in scorers |
| `genai_eval.py` | LLM-as-a-judge evaluation with Relevance, Coherence, Toxicity, Faithfulness |
| `custom_judge.py` | Custom scorers via `make_judge()` (LLM) and `make_scorer()` (function) |
| `pipeline_eval.py` | Evaluation-as-a-pipeline-step with `EvalStep` |
| `ci_assertions.py` | CI/CD quality gates with `EvalAssert` |

## Quick Start

```bash
# Classical ML evaluation
python examples/evaluations/classical_ml_eval.py

# GenAI evaluation (requires OpenAI API key)
export OPENAI_API_KEY="sk-..."
python examples/evaluations/genai_eval.py

# Custom scorers
python examples/evaluations/custom_judge.py

# CI/CD assertions
python examples/evaluations/ci_assertions.py
```

## Full Documentation

See [docs/evaluations.md](../../docs/evaluations.md) for the comprehensive guide.
