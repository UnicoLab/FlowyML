"""Champion/challenger gate + deployment for the production serving tutorial.

Usage:
    python deploy.py risk-bayesian vXXXX`     # promote if better, then deploy

Locally it deploys with the local_docker target; set FLOWYML_STACK to a prod
stack (e.g. azureml-openshift) to deploy to OpenShift instead.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from flowyml.deployment import DeploymentSpec, ModelRef, promote_if_better

# The custom model classes (RiskRules / BayesianPredictor) live in models.py.
# They must be baked into the serving image so the pickled model re-loads inside
# the container — pass the module via ``code_paths``.
_MODELS_PY = str(Path(__file__).resolve().parent / "models.py")


def main(model_name: str, candidate_version: str) -> None:
    target = "openshift" if os.environ.get("FLOWYML_STACK", "").endswith("openshift") else "local_docker"

    spec = DeploymentSpec(
        name=f"{model_name}-api",
        model=ModelRef(model_name),  # version filled in on promotion
        runtime="fastapi",  # any framework → FastAPI works everywhere
        target=target,
        namespace="ml-prod",
        route_host=f"{model_name}.apps.example.com",
        registry_uri=os.environ.get("OPENSHIFT_REGISTRY"),
        code_paths=[_MODELS_PY],  # bake custom model code into the image
        port=8080,
    )

    decision = promote_if_better(
        model_name,
        candidate_version,
        metric="accuracy",
        higher_is_better=True,
        min_improvement=0.0,
        to_stage="production",
        auto_deploy=True,
        deployment_spec=spec,
    )

    print("Promoted:", decision.promoted, "-", decision.reason)
    if decision.deployment:
        print("Endpoint:", decision.deployment.endpoint_url or decision.deployment.message)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python deploy.py <model_name> <candidate_version>")
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2])
