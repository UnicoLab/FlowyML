# 🧪 Model Flavors: Rule-Based & PyMC / Bayesian

FlowyML routes and serves models by a **`framework`** string. Deep-learning and
scikit-learn models are auto-detected, but two common families need a small,
portable, picklable wrapper so they package, register, and serve **exactly like
any other model**:

- **Rule-based** models — hand-written business rules and heuristics.
- **Bayesian / PyMC** models — a fitted posterior plus a pure prediction
  function.

Both live in `flowyml.models` and expose a scikit-learn-style `predict(X)`.

```python
from flowyml.models import RuleBasedModel, BayesianPredictor
```

!!! tip "Why a wrapper?"
    A servable model must survive a round-trip through the registry and reload
    **inside a container**. These base classes guarantee picklability and a
    uniform `.predict()` interface, and they set a `framework` attribute
    (`"rule_based"` / `"bayesian"`) so the registry and deployment layer treat
    them as first-class artifacts.

---

## Rule-Based Models

Subclass `RuleBasedModel` and implement `predict`. Constructor keyword arguments
are stored on `self.params`, so rules stay configurable and picklable.

```python title="models.py"
from __future__ import annotations

import numpy as np
from flowyml.models import RuleBasedModel


class RiskRules(RuleBasedModel):
    """An explainable hand-written baseline."""

    def predict(self, X):
        arr = np.asarray(X, dtype=float)
        cutoff = self.params.get("cutoff", 0.5)   # from RiskRules(cutoff=...)
        return [(1 if (row[0] > 0.8 and row[1] > cutoff) else 0) for row in arr]


model = RiskRules(cutoff=0.6)
model.predict([[0.9, 0.7, 0.1]])   # → [1]
model.get_params()                 # → {"cutoff": 0.6}
```

Rule-based models are perfect as an **explainable champion** to benchmark ML
models against — and because they serve through the same path, you can deploy one
as a real endpoint or promote an ML challenger to replace it.

---

## Bayesian / PyMC Models

`BayesianPredictor` wraps a fitted posterior (`idata`) and a **module-level**
prediction function into a servable object.

```python title="models.py"
from __future__ import annotations

import numpy as np
from flowyml.models import BayesianPredictor


def posterior_mean_predict(idata, X):
    """Module-level predict fn so the model unpickles in a container."""
    X = np.asarray(X, dtype=float)
    beta = np.asarray(idata["beta"], dtype=float)
    logits = X @ beta + float(idata["intercept"])
    return (1.0 / (1.0 + np.exp(-logits)) > 0.5).astype(int)


def make_bayesian_model(beta, intercept) -> BayesianPredictor:
    return BayesianPredictor(
        idata={"beta": list(beta), "intercept": float(intercept)},
        predict_fn=posterior_mean_predict,
        metadata={"kind": "bayesian-logistic"},
    )
```

!!! warning "`predict_fn` must be importable"
    Pass a **module-level** function, never a lambda or closure — otherwise the
    model cannot be unpickled in a fresh process or container. Keep both the
    predict function and any custom classes in an importable module (not a
    notebook or `__main__`).

### Real PyMC + ArviZ

For a real model, `idata` is an ArviZ `InferenceData` object and `predict_fn`
reads the posterior directly:

```python
import pymc as pm

with pm.Model() as model:
    # ... define priors + likelihood ...
    idata = pm.sample()


def predict_mean(idata, X):
    beta = idata.posterior["beta"].mean(("chain", "draw")).values
    return (X @ beta > 0).astype(int)


servable = BayesianPredictor(idata, predict_mean)
```

FlowyML's [`PyMCMaterializer`](../advanced/materializers.md) serializes
`InferenceData` to NetCDF automatically when you register it or store it as an
asset, so the posterior is versioned alongside the model.

---

## Register & Serve

Both flavors register with the model registry like any other model — pass the
matching `framework` string:

```python
from flowyml.registry.model_registry import ModelRegistry, ModelStage

registry = ModelRegistry()
registry.register(RiskRules(cutoff=0.5), name="risk-rules",
                  version="v1", framework="rule_based",
                  metrics={"accuracy": 0.81}, stage=ModelStage.DEVELOPMENT)
registry.register(make_bayesian_model([1.0, 1.5, -1.0], -1.0), name="risk-bayesian",
                  version="v1", framework="bayesian",
                  metrics={"accuracy": 0.88}, stage=ModelStage.DEVELOPMENT)
```

Then deploy or serve them exactly like a built-in framework — remembering to bake
your model module into the image via `code_paths`:

```python
from flowyml.deployment import DeploymentSpec, ModelRef, DeploymentService

spec = DeploymentSpec(
    name="risk-api",
    model=ModelRef("risk-bayesian", stage="production"),
    runtime="fastapi",
    target="openshift",
    code_paths=["models.py"],   # your RuleBasedModel / BayesianPredictor classes
)
DeploymentService().deploy(spec)
```

```bash
# or serve locally, no Docker
flowyml serve risk-bayesian --stage production
```

!!! note "Custom code must ride along"
    Because these are *your* classes/functions, `code_paths` copies the module(s)
    onto the serving image's `PYTHONPATH` so the pickle re-loads at serve time.
    Built-in frameworks (sklearn/PyTorch/ONNX/TF) need nothing extra. See the
    [Model Serving & Deployment guide](model-serving-deployment.md).

---

## Related

- **[Model Serving & Deployment](model-serving-deployment.md)** — runtimes,
  targets, promotion, and batch inference.
- **[Serve on OpenShift (E2E)](../tutorials/production-serving-openshift.md)** —
  a full working example that trains and serves both flavors.
- **[Materializers](../advanced/materializers.md)** — the PyMC materializer and
  custom serialization.
- **[Model Registry](../user-guide/model-registry.md)** — versioning and staging.
