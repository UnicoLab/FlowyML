"""Pure Kubernetes/OpenShift manifest generation.

These functions have no side effects and return plain dicts, so they are fully
unit-testable and can also be rendered to YAML for GitOps workflows
(``flowyml deploy --dry-run``).
"""

from __future__ import annotations

from typing import Any

from flowyml.deployment.models import DeploymentSpec


def _labels(spec: DeploymentSpec) -> dict[str, str]:
    labels = {
        "app": spec.dns_name,
        "app.kubernetes.io/name": spec.dns_name,
        "app.kubernetes.io/managed-by": "flowyml",
        "flowyml.io/model": spec.model.name,
    }
    if spec.model.version:
        labels["flowyml.io/version"] = str(spec.model.version)
    labels.update(spec.labels)
    return labels


def _resources(spec: DeploymentSpec) -> dict[str, Any]:
    res = spec.resources
    requests: dict[str, str] = {"cpu": res.cpu, "memory": res.memory}
    limits: dict[str, str] = {
        "cpu": res.cpu_limit or res.cpu,
        "memory": res.memory_limit or res.memory,
    }
    if res.gpu:
        limits["nvidia.com/gpu"] = str(res.gpu)
    return {"requests": requests, "limits": limits}


def build_deployment(spec: DeploymentSpec, image: str, container_port: int, health_path: str) -> dict[str, Any]:
    """Build a Kubernetes Deployment manifest."""
    env = [{"name": k, "value": str(v)} for k, v in spec.env.items()]
    container: dict[str, Any] = {
        "name": spec.dns_name,
        "image": image,
        "ports": [{"containerPort": container_port, "name": "http"}],
        "resources": _resources(spec),
        "readinessProbe": {
            "httpGet": {"path": health_path, "port": container_port},
            "initialDelaySeconds": 10,
            "periodSeconds": 10,
        },
        "livenessProbe": {
            "httpGet": {"path": health_path, "port": container_port},
            "initialDelaySeconds": 30,
            "periodSeconds": 30,
        },
    }
    if env:
        container["env"] = env

    pod_spec: dict[str, Any] = {"containers": [container]}
    if spec.service_account:
        pod_spec["serviceAccountName"] = spec.service_account
    if spec.image_pull_secret:
        pod_spec["imagePullSecrets"] = [{"name": spec.image_pull_secret}]

    # Turnkey Prometheus scraping of the serving container's /metrics endpoint
    # (disable via extra={"metrics": False}).
    pod_annotations: dict[str, str] = dict(spec.annotations)
    if spec.extra.get("metrics", True):
        pod_annotations.setdefault("prometheus.io/scrape", "true")
        pod_annotations.setdefault("prometheus.io/port", str(container_port))
        pod_annotations.setdefault("prometheus.io/path", "/metrics")

    manifest: dict[str, Any] = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": spec.dns_name,
            "labels": _labels(spec),
            "annotations": spec.annotations,
        },
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": {"app": spec.dns_name}},
            "template": {
                "metadata": {"labels": _labels(spec), "annotations": pod_annotations},
                "spec": pod_spec,
            },
        },
    }
    if spec.namespace:
        manifest["metadata"]["namespace"] = spec.namespace
    return manifest


def build_service(spec: DeploymentSpec, container_port: int) -> dict[str, Any]:
    """Build a Kubernetes Service (ClusterIP) manifest."""
    manifest: dict[str, Any] = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": spec.dns_name, "labels": _labels(spec)},
        "spec": {
            "selector": {"app": spec.dns_name},
            "ports": [{"port": container_port, "targetPort": container_port, "name": "http"}],
            "type": "ClusterIP",
        },
    }
    if spec.namespace:
        manifest["metadata"]["namespace"] = spec.namespace
    return manifest


def build_route(spec: DeploymentSpec, container_port: int) -> dict[str, Any]:
    """Build an OpenShift Route manifest (edge-terminated TLS)."""
    route_spec: dict[str, Any] = {
        "to": {"kind": "Service", "name": spec.dns_name},
        "port": {"targetPort": container_port},
        "tls": {"termination": "edge", "insecureEdgeTerminationPolicy": "Redirect"},
    }
    if spec.route_host:
        route_spec["host"] = spec.route_host
    manifest: dict[str, Any] = {
        "apiVersion": "route.openshift.io/v1",
        "kind": "Route",
        "metadata": {"name": spec.dns_name, "labels": _labels(spec)},
        "spec": route_spec,
    }
    if spec.namespace:
        manifest["metadata"]["namespace"] = spec.namespace
    return manifest


def build_ingress(spec: DeploymentSpec, container_port: int) -> dict[str, Any]:
    """Build a Kubernetes Ingress manifest (requires ``route_host``)."""
    manifest: dict[str, Any] = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": spec.dns_name, "labels": _labels(spec), "annotations": spec.annotations},
        "spec": {
            "rules": [
                {
                    "host": spec.route_host,
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": spec.dns_name,
                                        "port": {"number": container_port},
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
    }
    if spec.namespace:
        manifest["metadata"]["namespace"] = spec.namespace
    return manifest


def build_hpa(spec: DeploymentSpec) -> dict[str, Any]:
    """Build a HorizontalPodAutoscaler manifest."""
    auto = spec.autoscaling
    manifest: dict[str, Any] = {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {"name": spec.dns_name, "labels": _labels(spec)},
        "spec": {
            "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": spec.dns_name},
            "minReplicas": auto.min_replicas,
            "maxReplicas": auto.max_replicas,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {"type": "Utilization", "averageUtilization": auto.target_cpu_utilization},
                    },
                },
            ],
        },
    }
    if spec.namespace:
        manifest["metadata"]["namespace"] = spec.namespace
    return manifest


def render_manifests(
    spec: DeploymentSpec,
    image: str,
    container_port: int,
    health_path: str = "/health",
    *,
    openshift: bool = False,
) -> list[dict[str, Any]]:
    """Render the full set of manifests for a deployment."""
    manifests = [
        build_deployment(spec, image, container_port, health_path),
        build_service(spec, container_port),
    ]
    if spec.expose:
        manifests.append(
            build_route(spec, container_port) if openshift else build_ingress(spec, container_port),
        )
    if spec.autoscaling.enabled:
        manifests.append(build_hpa(spec))
    return manifests


def to_yaml(manifests: list[dict[str, Any]]) -> str:
    """Serialize a list of manifests to a multi-document YAML string."""
    import yaml

    return "\n---\n".join(yaml.safe_dump(m, sort_keys=False) for m in manifests)
