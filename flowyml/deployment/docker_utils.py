"""Thin, testable wrappers around the ``docker`` CLI used by deployment targets.

All functions shell out to ``docker`` (or a configured equivalent) and raise
:class:`DockerError` on failure.  They are deliberately small so they can be
mocked in unit tests.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class DockerError(RuntimeError):
    """Raised when a docker CLI invocation fails."""


def docker_available(binary: str = "docker") -> bool:
    """Return True if the ``docker`` CLI is present on PATH.

    Note: this only checks the CLI. Use :func:`daemon_running` to verify the
    Docker daemon is actually reachable before running containers.
    """
    return shutil.which(binary) is not None


def daemon_running(binary: str = "docker") -> bool:
    """Return True if the Docker daemon is reachable, not just the CLI present.

    ``docker`` can be installed while the daemon (Docker Desktop / dockerd) is
    stopped. ``docker info`` returns a non-zero exit code in that case, which we
    translate into a clean boolean so callers can emit a friendly message.
    """
    if not docker_available(binary):
        return False
    try:
        subprocess.run(
            [binary, "info"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _run(cmd: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    logger.debug("exec: %s", " ".join(cmd))
    try:
        return subprocess.run(cmd, capture_output=capture, text=True, check=check)
    except FileNotFoundError as exc:
        raise DockerError(f"'{cmd[0]}' not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise DockerError(
            f"Command failed ({exc.returncode}): {' '.join(cmd)}\n{exc.stderr or exc.stdout}",
        ) from exc


def build_image(
    build_dir: str,
    image_tag: str,
    *,
    dockerfile: str | None = None,
    platform: str | None = "linux/amd64",
    build_args: dict[str, str] | None = None,
    binary: str = "docker",
) -> str:
    """Build a docker image from ``build_dir``. Returns the image tag."""
    cmd = [binary, "build", "-t", image_tag]
    if dockerfile:
        cmd += ["-f", dockerfile]
    if platform:
        cmd += ["--platform", platform]
    for key, value in (build_args or {}).items():
        cmd += ["--build-arg", f"{key}={value}"]
    cmd.append(build_dir)
    _run(cmd, capture=False)
    logger.info("Built image %s", image_tag)
    return image_tag


def push_image(image_tag: str, *, binary: str = "docker") -> str:
    _run([binary, "push", image_tag], capture=False)
    logger.info("Pushed image %s", image_tag)
    return image_tag


def tag_image(source: str, target: str, *, binary: str = "docker") -> str:
    _run([binary, "tag", source, target])
    return target


def run_container(
    image: str,
    name: str,
    *,
    ports: dict[int, int] | None = None,
    env: dict[str, str] | None = None,
    detach: bool = True,
    binary: str = "docker",
) -> str:
    """Run a container. Returns the container id/name."""
    cmd = [binary, "run", "--name", name]
    if detach:
        cmd.append("-d")
    cmd += ["--rm"]
    for host, container in (ports or {}).items():
        cmd += ["-p", f"{host}:{container}"]
    for key, value in (env or {}).items():
        cmd += ["-e", f"{key}={value}"]
    cmd.append(image)
    result = _run(cmd)
    return (result.stdout or name).strip()


def stop_container(name: str, *, binary: str = "docker") -> bool:
    try:
        _run([binary, "rm", "-f", name])
        return True
    except DockerError:
        return False


def container_status(name: str, *, binary: str = "docker") -> dict[str, Any] | None:
    """Return docker inspect state for ``name`` or ``None`` if absent."""
    inspect = _inspect(name, binary=binary)
    if inspect is None:
        return None
    return inspect.get("State", {})


def _inspect(name: str, *, binary: str = "docker") -> dict[str, Any] | None:
    try:
        result = _run([binary, "inspect", name])
    except DockerError:
        return None
    data = json.loads(result.stdout)
    return data[0] if data else None


def container_published_ports(name: str, *, binary: str = "docker") -> dict[int, int]:
    """Return a mapping of ``container_port -> host_port`` for a running container."""
    inspect = _inspect(name, binary=binary)
    if inspect is None:
        return {}
    ports = (inspect.get("NetworkSettings", {}) or {}).get("Ports", {}) or {}
    mapping: dict[int, int] = {}
    for spec, bindings in ports.items():
        if not bindings:
            continue
        container_port = int(str(spec).split("/")[0])
        try:
            mapping[container_port] = int(bindings[0]["HostPort"])
        except (KeyError, IndexError, ValueError):
            continue
    return mapping
