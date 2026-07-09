"""CLI commands for model deployment and serving.

Adds ``flowyml deploy``, ``flowyml serve`` and the ``flowyml deployment`` group.
Registered onto the main CLI via :func:`register_deployment_commands`.
"""

from __future__ import annotations

import json
from typing import Any

import rich_click as click

from flowyml.cli.rich_utils import recho


def _parse_env(pairs: tuple[str, ...]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in pairs or ():
        if "=" not in item:
            raise click.BadParameter(f"--env must be KEY=VALUE, got '{item}'")
        key, value = item.split("=", 1)
        env[key] = value
    return env


def _build_spec(
    model: str,
    *,
    name: str | None,
    version: str | None,
    stage: str | None,
    runtime: str,
    target: str,
    namespace: str | None,
    route_host: str | None,
    registry_uri: str | None,
    replicas: int,
    port: int,
    cpu: str,
    memory: str,
    gpu: int,
    env: dict[str, str],
    dry_run: bool,
):
    from flowyml.deployment.models import DeploymentSpec, ModelRef, ResourceRequests

    return DeploymentSpec(
        name=name or f"{model}-endpoint",
        model=ModelRef(name=model, version=version, stage=stage),
        runtime=runtime,
        target=target,
        namespace=namespace,
        route_host=route_host,
        registry_uri=registry_uri,
        replicas=replicas,
        port=port,
        resources=ResourceRequests(cpu=cpu, memory=memory, gpu=gpu),
        env=env,
        extra={"dry_run": dry_run} if dry_run else {},
    )


def register_deployment_commands(cli: Any) -> None:
    """Attach deployment commands to the root ``cli`` group."""

    @cli.command()
    @click.argument("model")
    @click.option("--name", default=None, help="Deployment name (default: <model>-endpoint).")
    @click.option("--version", default=None, help="Explicit model version to deploy.")
    @click.option("--stage", default=None, help="Resolve version from a registry stage (e.g. production).")
    @click.option(
        "--runtime",
        type=click.Choice(["fastapi", "triton", "tensorflow_serving", "torchserve"]),
        default="fastapi",
        help="Serving runtime.",
    )
    @click.option(
        "--target",
        type=click.Choice(["local_docker", "kubernetes", "openshift"]),
        default="local_docker",
        help="Deployment target.",
    )
    @click.option("--namespace", default=None, help="Kubernetes/OpenShift namespace.")
    @click.option("--route-host", default=None, help="External host for the Route/Ingress.")
    @click.option("--registry", "registry_uri", default=None, help="Container registry to push the serving image to.")
    @click.option("--replicas", default=1, type=int, help="Number of replicas.")
    @click.option("--port", default=8080, type=int, help="Service port.")
    @click.option("--cpu", default="500m", help="CPU request.")
    @click.option("--memory", default="1Gi", help="Memory request.")
    @click.option("--gpu", default=0, type=int, help="Number of GPUs.")
    @click.option("--env", multiple=True, help="Environment variable KEY=VALUE (repeatable).")
    @click.option("--spec", "spec_file", default=None, help="Load a DeploymentSpec from a YAML file.")
    @click.option("--dry-run", is_flag=True, help="Render manifests without applying (k8s/openshift).")
    def deploy(
        model,
        name,
        version,
        stage,
        runtime,
        target,
        namespace,
        route_host,
        registry_uri,
        replicas,
        port,
        cpu,
        memory,
        gpu,
        env,
        spec_file,
        dry_run,
    ) -> None:
        r"""Package a registered MODEL and deploy it to a target.

        Examples:
          flowyml deploy churn --stage production --runtime fastapi --target openshift \
              --namespace ml-prod --route-host churn.apps.example.com --registry my-registry.io/ml

          flowyml deploy fraud --runtime triton --target local_docker
        """
        from flowyml.deployment.models import DeploymentSpec
        from flowyml.deployment.service import DeploymentService

        if spec_file:
            spec = DeploymentSpec.from_yaml(spec_file)
        else:
            spec = _build_spec(
                model,
                name=name,
                version=version,
                stage=stage,
                runtime=runtime,
                target=target,
                namespace=namespace,
                route_host=route_host,
                registry_uri=registry_uri,
                replicas=replicas,
                port=port,
                cpu=cpu,
                memory=memory,
                gpu=gpu,
                env=_parse_env(env),
                dry_run=dry_run,
            )

        recho(f"[cyan]Deploying[/] {spec.model.name} → runtime={spec.runtime.value} target={spec.target.value}")
        try:
            result = DeploymentService().deploy(spec)
        except Exception as exc:  # noqa: BLE001
            recho(f"[red]✗ Deployment failed: {exc}", err=True)
            raise click.Abort() from exc

        if dry_run and result.details.get("manifests"):
            recho("[yellow]Dry run — generated manifests:[/]")
            click.echo(result.details["manifests"])
            return

        recho(f"[green]✓ {result.status.value}[/] — {result.message}")
        if result.endpoint_url:
            recho(f"  Endpoint: [bold]{result.endpoint_url}[/]")
        if result.predict_url:
            recho(f"  Predict:  [bold]{result.predict_url}[/]")
        if result.image:
            recho(f"  Image:    {result.image}")

    @cli.command()
    @click.argument("model")
    @click.option("--version", default=None, help="Explicit model version.")
    @click.option("--stage", default=None, help="Resolve version from a registry stage.")
    @click.option("--port", default=8080, type=int, help="Local port to bind.")
    @click.option("--host", default="127.0.0.1", help="Host to bind.")
    def serve(model, version, stage, port, host) -> None:
        """Serve a registered MODEL locally (in-process FastAPI), no Docker required."""
        import uvicorn

        from flowyml.deployment.bundle import build_bundle
        from flowyml.deployment.models import ModelRef
        from flowyml.deployment.serving_app import create_app

        recho(f"[cyan]Packaging[/] {model} (version={version}, stage={stage})...")
        bundle = build_bundle(ModelRef(name=model, version=version, stage=stage))
        recho(f"[green]✓[/] Serving {bundle.name}:{bundle.version} on http://{host}:{port}")
        recho(f"  Try: [bold]curl -X POST http://{host}:{port}/predict -d '{{\"inputs\": [[...]]}}'[/]")
        uvicorn.run(create_app(bundle.path), host=host, port=port)

    @cli.group()
    def deployment() -> None:
        """Manage running deployments (list, status, predict, delete)."""

    @deployment.command("list")
    def _list() -> None:
        """List recorded deployments."""
        from flowyml.deployment.service import DeploymentService

        records = DeploymentService().list()
        if not records:
            recho("[dim]No deployments recorded.[/]")
            return
        for rec in records:
            recho(
                f"[bold]{rec['name']}[/] — {rec.get('status')} "
                f"({rec.get('runtime')}/{rec.get('target')}) "
                f"{rec.get('endpoint_url') or ''}",
            )

    @deployment.command()
    @click.argument("name")
    def status(name) -> None:
        """Show live status of a deployment."""
        from flowyml.deployment.service import DeploymentService

        result = DeploymentService().status(name)
        recho(json.dumps(result.to_dict(), indent=2, default=str))

    @deployment.command()
    @click.argument("name")
    @click.option("--json", "json_input", required=True, help="JSON prediction payload.")
    def predict(name, json_input) -> None:
        """Send a prediction request to a deployment."""
        from flowyml.deployment.service import DeploymentService

        payload = json.loads(json_input)
        result = DeploymentService().predict(name, payload)
        recho(json.dumps(result, indent=2, default=str))

    @deployment.command()
    @click.argument("name")
    def delete(name) -> None:
        """Tear down a deployment."""
        from flowyml.deployment.service import DeploymentService

        ok = DeploymentService().undeploy(name)
        recho(f"[green]✓ Removed {name}[/]" if ok else f"[red]✗ Failed to remove {name}[/]")
