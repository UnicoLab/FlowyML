# Production Serving Example

A complete, working loop: **train → register → compare → promote → deploy →
serve/batch**, with custom model flavors (rule-based + Bayesian). Runs entirely
on a laptop, and switches to Azure ML + OpenShift by changing one stack.

Full walkthrough: **[docs → Train on Azure ML, Serve on OpenShift](../../docs/tutorials/production-serving-openshift.md)**.

## Layout

| File | What it does |
|------|--------------|
| `models.py` | `RiskRules` (rule-based) + `make_bayesian_model` (Bayesian). Importable so pickles reload in a container. |
| `pipelines/training.py` | Trains both models, registers them with metrics + lineage. Prints each candidate's version. |
| `deploy.py` | Champion/challenger gate (`promote_if_better`) + deploy the winner. |
| `batch.py` | Offline/batch inference (`run_batch_inference`) — score rows with no server. |
| `flowyml.yaml` | Three stacks: `local`, `azureml-openshift`, `azureml-mlflow`. |

## Quickstart (local)

```bash
pip install flowyml fastapi uvicorn prometheus-client

cd examples/production_serving

# 1) train + register (prints each candidate's version, e.g. v1783596659)
python pipelines/training.py

# 2) promote if better than the current production champion, then deploy locally
#    (the local_docker target needs a running Docker daemon)
python deploy.py risk-bayesian <version>

# 3) online prediction against the served container
curl -X POST http://localhost:8080/predict \
     -H 'content-type: application/json' \
     -d '{"inputs": [[0.9, 1.0, 0.1], [0.1, 0.1, 0.9]]}'
# → {"prediction": [1, 0], ...}
```

### Batch inference (no server, no Docker)

Score a dataset offline with the same packaging path used for online serving:

```bash
# score the current production champion (after step 2 above)
python batch.py risk-bayesian

# ...or score a specific version directly (no promotion/Docker needed)
python batch.py risk-bayesian <version>
# → writes predictions to ./.flowyml/batch_predictions.json
```

## Go to production

```bash
export AZURE_SUBSCRIPTION_ID=... AZURE_RESOURCE_GROUP=... AZURE_WORKSPACE=...
export AZURE_BLOB_ACCOUNT_URL=... OPENSHIFT_REGISTRY=...
export FLOWYML_STACK=azureml-openshift

python pipelines/training.py          # trains on Azure ML compute
python deploy.py risk-bayesian <version>   # deploys to OpenShift
```

Everything else — packaging, fetching, versioning, image build, model mounting,
health probes, Prometheus scrape annotations — is handled by FlowyML.
