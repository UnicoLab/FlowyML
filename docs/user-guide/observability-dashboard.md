# 📊 Observability Dashboard: The Nerve Center 🧠

The FlowyML Dashboard is a professional-grade, interactive command center designed to give you **X-ray vision** into your ML infrastructure. Whether you are tracking a single hyperparameter sweep or managing thousands of production pipelines, this is where you monitor the "heartbeat" of your system.

---

## 🗺️ Navigation & Layout

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🚀 Real-Time HUD
The "Heads-Up Display" (HUD) auto-refreshes every **30 seconds**. No manual reloads. See runs as they happen.
</div>

<div class="header-card" markdown>
### 🌙 Premium Dark Mode
Designed for high-contrast visibility. Our **Slate Night** theme reduces eye strain during long debugging sessions.
</div>

<div class="header-card" markdown>
### 📈 Live Visualizations
Interactive Gantt charts, Lineage Trees, and Drift Overlays are generated instantly from the metadata store.
</div>

</div>

---

## 📊 Core KPI Cards

At the top of the dashboard, you'll find the **Nerve Center Metrics**. These are your high-level health indicators:

| KPI | Technical Meaning | Metric Optimization |
|-----|-------------------|---------------------|
| **Total Runs** | Volume of pipeline executions in the current cycle. | Use for capacity planning. |
| **Success Rate** | The ratio of `success` status vs. `failed`. | **Critical**: Investigate if < 95%. |
| **Avg Duration** | Mean execution time from start to finalize. | Optimize if trending upwards. |
| **Cache Efficiency** | Percentage of steps skipped due to `content_hash` matches. | **Goal**: > 40% for faster iteration. |

---

## 🕵️ Lineage Explorer (Artifact Tracking)

Because FlowyML is **Artifact-Centric**, the dashboard allows you to click on any data asset (Dataset, Model, Metric) and see its "DNA":

1.  **Immutability Checksum**: The `SHA-256` content hash of the data.
2.  **Parentage**: A visual graph showing exactly which raw data and which code version produced this specific model.
3.  **Metadata Inspection**: View Pydantic-validated hyperparameters, training metrics, and environment tags.

---

## ⏱️ Execution Timeline (Gantt View)

Every pipeline run features a high-fidelity **Waterfall Timeline**.

- **Parallel Streams**: See which steps ran concurrently.
- **Critical Path Analysis**: FlowyML highlights the longest-running chain of dependencies so you know exactly where to optimize.
- **Cold-Start Latency**: See precisely how long container pull and environment setup took vs. actual code execution.

---

## 🤖 GenAI & LLM Traces

The traces tab provides a dedicated view for LLM observability:

- **Waterfall Traces**: Full nesting of chains, retrievers, and LLM calls.
- **Token Economy**: Individual token counts (Input/Output/Total) and calculated $USD cost per call.
- **Prompt Benchmarking**: Compare side-by-side completions for different prompt versions.

---

## 🔌 Programmatic Integration

You can extract all dashboard data into your own BI tools (Grafana, Datadog) or CI/CD pipelines.

```python linenums="1"
import requests

# Fetch the current health of the 'retraining-v2' project
resp = requests.get("http://localhost:8080/api/metrics/observability/orchestrator")
health = resp.json()

print(f"Project Health: {health['success_rate']:.0%}")
```

---

## 💡 Pro Tips

!!! tip "Performance Monitoring"
    If your **Success Rate** is high but **Avg Duration** is increasing, use the **Gantt View** to check for "Storage Bottlenecks" (slow artifact downloads).

!!! tip "Lineage as Documentation"
    Never write a "Model Card" manually again. Export the **Lineage Tree** directly from the UI as a PDF to document your model's provenance for compliance audits.
