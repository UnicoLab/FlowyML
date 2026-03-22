# 🏟️ Judge Arena — A/B Testing Evaluators

!!! info "What you'll learn"
    How to pit multiple LLM judges against each other — and against human labels — to find the most reliable and cost-effective evaluator for your use case.

The Judge Arena is FlowyML's **evaluator benchmarking system**. It runs every judge on the same data, computes Elo-style rankings, and tells you which judge best correlates with human labels.

---

## Why Judge Arena? 🤔

| Problem | Arena Solution |
|---|---|
| "Which LLM judge should I use?" | Elo rankings by accuracy |
| "Is my custom judge reliable?" | Compare against human baselines |
| "GPT-4o is expensive for evals" | Cost analysis per evaluation |
| "Do different judges agree?" | Inter-judge correlation matrix |

---

## Quick Start 🚀

```python
from flowyml.evals import JudgeArena, EvalDataset, Relevance, Faithfulness, make_judge

# 1. Prepare evaluation data with human scores
data = EvalDataset.create_genai("golden_set", examples=[
    {"inputs": {"query": "What is ML?"}, "expected": "Machine learning is...",
     "context": ["ML is a subset of AI..."]},
    {"inputs": {"query": "Explain RAG"}, "expected": "RAG combines retrieval...",
     "context": ["Retrieval-Augmented Generation..."]},
])

human_labels = [0.9, 0.8]  # Human quality scores for each example

# 2. Create arena with judges to compare
arena = JudgeArena(
    judges=[
        Relevance(model="openai:/gpt-4o-mini"),
        Faithfulness(model="openai:/gpt-4o-mini"),
        make_judge("custom_quality", "Rate the quality and helpfulness of the response."),
    ],
)

# 3. Run the arena
result = arena.evaluate(data=data, human_labels=human_labels)
```

---

## Arena Results API 📊

The `JudgeArenaResult` object provides rich analysis:

```python
# Best performing judge
best = result.best_judge()
print(f"Winner: {best}")

# Full rankings (Elo-style)
for rank in result.rankings:
    print(f"  #{rank['rank']} {rank['judge']}: Elo={rank['elo']:.0f}")

# How well judges agree with humans
for judge, score in result.agreement_scores().items():
    print(f"  {judge}: {score:.2%} agreement")

# How well judges agree with each other
matrix = result.correlation_matrix()
print(matrix)

# Cost comparison
for judge, cost in result.cost_analysis().items():
    print(f"  {judge}: ${cost:.4f}/eval")
```

### Available Methods

| Method | Returns | Description |
|---|---|---|
| `best_judge()` | `str` | Name of the top-performing judge |
| `rankings` | `list[dict]` | Elo-style rankings with scores |
| `correlation_matrix()` | `dict` | Inter-judge agreement matrix |
| `agreement_scores()` | `dict[str, float]` | Human-agreement score per judge |
| `cost_analysis()` | `dict[str, float]` | USD cost per evaluation per judge |

---

## Real-World Examples 🌍

### Choosing Between LLM Providers

```python
arena = JudgeArena(
    judges=[
        Relevance(model="openai:/gpt-4o"),
        Relevance(model="openai:/gpt-4o-mini"),
        Relevance(model="anthropic:/claude-3-haiku"),
    ],
)
result = arena.evaluate(data=golden_set, human_labels=human_scores)

# Find the cheapest judge with >90% human agreement
for judge, agreement in result.agreement_scores().items():
    cost = result.cost_analysis()[judge]
    if agreement > 0.9:
        print(f"✅ {judge}: {agreement:.1%} agreement, ${cost:.4f}/eval")
```

### Validating a Custom Judge

```python
custom = make_judge(
    "domain_expert",
    "You are a medical AI evaluator. Score the clinical accuracy of the response.",
    model="openai:/gpt-4o",
)

arena = JudgeArena(
    judges=[custom, Relevance(), Faithfulness()],
)
result = arena.evaluate(data=medical_data, human_labels=doctor_scores)

# Check if custom judge outperforms generic ones
print(result.rankings)
```

---

## Best Practices 💡

!!! tip "Always include human labels"
    Without human labels, the arena can only measure inter-judge agreement — not actual accuracy. Even 50 human-labeled examples make a big difference.

!!! tip "Mix general and specialized judges"
    Include at least one general-purpose judge (Relevance) and one domain-specific judge to see if specialization helps.

!!! warning "Cost awareness"
    Running N judges on M examples costs N × M LLM calls. Start with a small golden set (50–100 examples).
