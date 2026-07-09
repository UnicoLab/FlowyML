"""Tests for the FlowyML deployment layer.

Covers models, packaging (bundle), serving app, runtime image builders,
Kubernetes/OpenShift manifests, deployment targets (mocked CLIs), the
deployment service, champion/challenger promotion, and batch inference.
"""

from __future__ import annotations

import numpy as np
import pytest

from flowyml.deployment import (
    DeploymentSpec,
    DeploymentStatus,
    DeploymentTarget,
    ModelRef,
    ServingRuntime,
    build_bundle,
    promote_if_better,
    run_batch_inference,
)
from flowyml.deployment.runtimes.base import get_serving_builder
from flowyml.deployment.serving_app import load_bundle_model, predict_with_model
from flowyml.deployment.targets import get_deployer
from flowyml.deployment.targets import manifests as mf
from flowyml.registry.model_registry import ModelRegistry, ModelStage


# --------------------------------------------------------------------------- #
# A picklable rule-based model usable by the registry/serving path.            #
# (Not named Test* so pytest does not try to collect it.)                      #
# --------------------------------------------------------------------------- #
class SumRule:
    def __init__(self, threshold: float = 1.5) -> None:
        self.threshold = threshold

    def predict(self, X):
        arr = np.asarray(X, dtype=float)
        return (arr.sum(axis=1) > self.threshold).astype(int).tolist()


@pytest.fixture
def registry(tmp_path):
    reg = ModelRegistry(registry_path=str(tmp_path / "reg"), db_url=f"sqlite:///{tmp_path}/reg.db")
    reg.register(SumRule(1.5), "risk", "v1", framework="rule_based", metrics={"auc": 0.80}, stage=ModelStage.PRODUCTION)
    return reg


# --------------------------------------------------------------------------- #
# models                                                                       #
# --------------------------------------------------------------------------- #
def test_deployment_spec_dns_name_sanitized():
    spec = DeploymentSpec(name="Churn API v2!", model=ModelRef("churn"))
    assert spec.dns_name == "churn-api-v2"


def test_deployment_spec_roundtrip():
    spec = DeploymentSpec(
        name="churn",
        model=ModelRef("churn", stage="production"),
        runtime="triton",
        target="openshift",
        namespace="ml",
        replicas=3,
    )
    restored = DeploymentSpec.from_dict(spec.to_dict())
    assert restored.name == "churn"
    assert restored.runtime == ServingRuntime.TRITON
    assert restored.target == DeploymentTarget.OPENSHIFT
    assert restored.model.stage == "production"
    assert restored.replicas == 3


def test_model_ref_from_string():
    spec = DeploymentSpec(name="x", model="mymodel")
    assert isinstance(spec.model, ModelRef)
    assert spec.model.name == "mymodel"


# --------------------------------------------------------------------------- #
# packaging + serving                                                          #
# --------------------------------------------------------------------------- #
def test_build_bundle_and_predict(registry):
    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    assert bundle.name == "risk"
    assert bundle.framework == "rule_based"
    assert "cloudpickle" in bundle.requirements
    assert bundle.path + "/metadata.json"

    model, meta = load_bundle_model(bundle.path)
    out = predict_with_model(model, {"inputs": [[2, 2], [0, 0]]}, meta["framework"])
    assert out["prediction"] == [1, 0]


def test_resolve_missing_model_raises(registry):
    with pytest.raises(ValueError):
        build_bundle(ModelRef("does-not-exist"), registry=registry)


def test_serving_app_endpoints(registry):
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from flowyml.deployment.serving_app import create_app

    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    client = TestClient(create_app(bundle.path))

    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/metadata").json()["name"] == "risk"
    body = client.post("/predict", json={"inputs": [[2, 2], [0, 0]]}).json()
    assert body["prediction"] == [1, 0]


# --------------------------------------------------------------------------- #
# runtime builders                                                             #
# --------------------------------------------------------------------------- #
def test_fastapi_builder_creates_context(registry, tmp_path):
    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(name="risk", model=ModelRef("risk"), runtime="fastapi")
    ctx = get_serving_builder("fastapi").prepare(spec, bundle, str(tmp_path / "build"))
    import os

    files = set(os.listdir(ctx.build_dir))
    assert {"Dockerfile", "serve.py", "requirements.txt", "model_bundle"} <= files
    assert ctx.port == 8080


def test_triton_python_backend_for_rule_based(registry, tmp_path):
    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(name="risk", model=ModelRef("risk"), runtime="triton")
    ctx = get_serving_builder("triton").prepare(spec, bundle, str(tmp_path / "b"))
    from pathlib import Path

    config = Path(ctx.build_dir) / "model_repository" / "risk" / "config.pbtxt"
    assert config.exists()
    assert 'backend: "python"' in config.read_text()
    assert (Path(ctx.build_dir) / "model_repository" / "risk" / "1" / "model.py").exists()


def test_tfserving_rejects_non_tensorflow(registry, tmp_path):
    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(name="risk", model=ModelRef("risk"), runtime="tensorflow_serving")
    with pytest.raises(ValueError):
        get_serving_builder("tensorflow_serving").prepare(spec, bundle, str(tmp_path / "b"))


# --------------------------------------------------------------------------- #
# manifests                                                                    #
# --------------------------------------------------------------------------- #
def test_render_manifests_openshift():
    spec = DeploymentSpec(
        name="churn",
        model=ModelRef("churn"),
        target="openshift",
        namespace="ml-prod",
        route_host="churn.example.com",
        replicas=2,
    )
    manifests = mf.render_manifests(spec, "reg/img:1", 8080, "/health", openshift=True)
    kinds = [m["kind"] for m in manifests]
    assert kinds == ["Deployment", "Service", "Route"]
    dep = manifests[0]
    assert dep["spec"]["replicas"] == 2
    assert dep["metadata"]["namespace"] == "ml-prod"
    assert dep["spec"]["template"]["spec"]["containers"][0]["image"] == "reg/img:1"
    assert manifests[2]["spec"]["host"] == "churn.example.com"


def test_render_manifests_with_hpa_and_gpu():
    from flowyml.deployment.models import Autoscaling, ResourceRequests

    spec = DeploymentSpec(
        name="fraud",
        model=ModelRef("fraud"),
        target="kubernetes",
        autoscaling=Autoscaling(enabled=True, min_replicas=2, max_replicas=8),
        resources=ResourceRequests(cpu="1", memory="2Gi", gpu=1),
    )
    manifests = mf.render_manifests(spec, "img:1", 8000, "/v2/health", openshift=False)
    kinds = [m["kind"] for m in manifests]
    assert "HorizontalPodAutoscaler" in kinds
    assert "Ingress" in kinds
    dep = manifests[0]
    limits = dep["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]
    assert limits["nvidia.com/gpu"] == "1"


# --------------------------------------------------------------------------- #
# targets                                                                      #
# --------------------------------------------------------------------------- #
def test_get_deployer_types():
    from flowyml.deployment.targets import KubernetesDeployer, LocalDockerDeployer, OpenShiftDeployer

    assert isinstance(get_deployer("local_docker"), LocalDockerDeployer)
    assert isinstance(get_deployer("kubernetes"), KubernetesDeployer)
    assert isinstance(get_deployer("openshift"), OpenShiftDeployer)


def test_local_docker_deploy_mocked(registry, mocker):
    from flowyml.deployment import docker_utils

    mocker.patch.object(docker_utils, "docker_available", return_value=True)
    mocker.patch.object(docker_utils, "daemon_running", return_value=True)
    mocker.patch.object(docker_utils, "build_image", return_value="flowyml-serve-risk:v1")
    mocker.patch.object(docker_utils, "stop_container", return_value=True)
    run = mocker.patch.object(docker_utils, "run_container", return_value="cid")

    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(
        name="risk-api",
        model=ModelRef("risk", version="v1"),
        runtime="fastapi",
        target="local_docker",
        port=9000,
    )
    deployer = get_deployer("local_docker")
    result = deployer.deploy(spec, bundle)

    assert result.status == DeploymentStatus.RUNNING
    assert result.endpoint_url == "http://localhost:9000"
    run.assert_called_once()


def test_local_docker_deploy_dead_daemon_friendly_error(registry, mocker):
    from flowyml.deployment import docker_utils
    from flowyml.deployment.targets import get_deployer

    # CLI present but daemon down.
    mocker.patch.object(docker_utils, "docker_available", return_value=True)
    mocker.patch.object(docker_utils, "daemon_running", return_value=False)

    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(
        name="risk-api",
        model=ModelRef("risk", version="v1"),
        runtime="fastapi",
        target="local_docker",
    )
    deployer = get_deployer("local_docker")
    with pytest.raises(RuntimeError, match="daemon is not running"):
        deployer.deploy(spec, bundle)


def test_kubernetes_deploy_dry_run(registry):
    bundle = build_bundle(ModelRef("risk", version="v1"), registry=registry)
    spec = DeploymentSpec(
        name="risk",
        model=ModelRef("risk", version="v1"),
        runtime="fastapi",
        target="kubernetes",
        image="prebuilt:1",
        namespace="ml",
        extra={"dry_run": True},
    )
    deployer = get_deployer("kubernetes")
    result = deployer.deploy(spec, bundle)
    assert result.status == DeploymentStatus.PENDING
    assert "Deployment" in result.details["manifests"]


# --------------------------------------------------------------------------- #
# promotion                                                                    #
# --------------------------------------------------------------------------- #
def test_promote_first_version(tmp_path):
    reg = ModelRegistry(registry_path=str(tmp_path / "r"), db_url=f"sqlite:///{tmp_path}/r.db")
    reg.register(SumRule(), "m", "v1", framework="rule_based", metrics={"auc": 0.7})
    decision = promote_if_better("m", "v1", metric="auc", registry=reg)
    assert decision.promoted
    assert reg.get_latest_version("m", stage=ModelStage.PRODUCTION).version == "v1"


def test_promote_if_better_wins_and_loses(registry):
    registry.register(SumRule(), "risk", "v2", framework="rule_based", metrics={"auc": 0.9})
    win = promote_if_better("risk", "v2", metric="auc", registry=registry)
    assert win.promoted
    assert win.improvement == pytest.approx(0.1)
    assert registry.get_latest_version("risk", stage=ModelStage.PRODUCTION).version == "v2"

    registry.register(SumRule(), "risk", "v3", framework="rule_based", metrics={"auc": 0.85})
    lose = promote_if_better("risk", "v3", metric="auc", registry=registry)
    assert not lose.promoted


def test_promote_respects_min_improvement(registry):
    registry.register(SumRule(), "risk", "v2", framework="rule_based", metrics={"auc": 0.81})
    decision = promote_if_better("risk", "v2", metric="auc", registry=registry, min_improvement=0.05)
    assert not decision.promoted


def test_promote_missing_metric_raises(registry):
    registry.register(SumRule(), "risk", "v2", framework="rule_based", metrics={"f1": 0.9})
    with pytest.raises(ValueError):
        promote_if_better("risk", "v2", metric="auc", registry=registry)


def test_promote_when_champion_missing_metric(tmp_path):
    """Champion lacking the comparison metric must not crash; challenger wins."""
    reg = ModelRegistry(registry_path=str(tmp_path / "r"), db_url=f"sqlite:///{tmp_path}/r.db")
    # Champion in production WITHOUT the 'auc' metric.
    reg.register(SumRule(), "m", "v1", framework="rule_based", metrics={"f1": 0.5}, stage=ModelStage.PRODUCTION)
    # Challenger WITH the 'auc' metric.
    reg.register(SumRule(), "m", "v2", framework="rule_based", metrics={"auc": 0.9})

    decision = promote_if_better("m", "v2", metric="auc", registry=reg)

    assert decision.promoted
    assert decision.champion_score is None
    assert decision.challenger_score == pytest.approx(0.9)
    assert reg.get_latest_version("m", stage=ModelStage.PRODUCTION).version == "v2"


# --------------------------------------------------------------------------- #
# batch                                                                        #
# --------------------------------------------------------------------------- #
def test_batch_inference_list(registry):
    result = run_batch_inference("risk", [[2, 2], [0, 0], [1, 1]], registry=registry, version="v1", batch_size=2)
    assert result.num_rows == 3
    assert result.predictions == [1, 0, 1]


def test_batch_inference_writes_output(registry, tmp_path):
    out = tmp_path / "preds.json"
    result = run_batch_inference("risk", [[3, 3]], registry=registry, version="v1", output_path=str(out))
    assert out.exists()
    assert result.output_path == str(out)
