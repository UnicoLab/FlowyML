"""Docker Image Builder v2 – Production-grade image builder for FlowyML.

This module provides :class:`DockerImageBuilder`, the authoritative entry-point
for generating optimised Dockerfiles and building container images used by
FlowyML pipelines.  The builder supports multi-stage builds, GPU-aware base
image selection, five dependency managers, BuildKit cache mounts, platform
cross-compilation, and deterministic content-hash tagging.

Example::

    from flowyml.stacks.components import DockerConfig
    from flowyml.core.image_builder import DockerImageBuilder

    cfg = DockerConfig(
        requirements=["numpy", "pandas"],
        gpu_enabled=True,
        cuda_version="12.4",
    )
    builder = DockerImageBuilder()
    tag = builder.generate_tag(cfg, base_name="my-pipeline")
    image = builder.build_image(cfg, tag=tag)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from flowyml.stacks.components import DockerConfig

__all__ = ["DockerImageBuilder"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CUDA_VERSION = "12.4"

_DEFAULT_DOCKERIGNORE_PATTERNS: list[str] = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".gitignore",
    ".dockerignore",
    ".env",
    ".venv",
    "venv",
    "*.egg-info",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "*.so",
    "*.o",
    ".DS_Store",
    "Thumbs.db",
    "node_modules",
]


class DockerImageBuilder:
    """Production-grade Docker image builder for FlowyML pipelines.

    Generates optimised multi-stage Dockerfiles with:

    * **BuildKit cache mounts** for pip / uv / conda
    * **GPU-aware base image auto-selection** via CUDA version mapping
    * **Smart dependency manager detection** (conda → uv → poetry → pip)
    * **Platform targeting** for cross-compilation (``linux/amd64``, etc.)
    * **Content-hash image tagging** for deterministic builds
    * **Build log streaming** for real-time feedback
    * **Security hardening** (non-root user, minimal layers)
    """

    # ── CUDA base image catalogue ─────────────────────────────────────
    CUDA_BASE_IMAGES: dict[str, str] = {
        "12.4": "nvidia/cuda:12.4.1-runtime-ubuntu22.04",
        "12.1": "nvidia/cuda:12.1.1-runtime-ubuntu22.04",
        "11.8": "nvidia/cuda:11.8.0-runtime-ubuntu22.04",
    }

    # ── Public API ────────────────────────────────────────────────────

    def build_image(
        self,
        docker_config: DockerConfig,
        tag: str,
        stream_logs: bool = True,
    ) -> str:
        """Build a Docker image from *docker_config*.

        The method resolves (or generates) a Dockerfile, writes a
        ``.dockerignore`` alongside it, and invokes ``docker build``
        with BuildKit enabled.

        Args:
            docker_config: Fully-populated Docker configuration.
            tag: Image tag to apply (e.g. ``myimg:abc123``).
            stream_logs: When ``True``, stream ``docker build`` output
                line-by-line to *stdout*.

        Returns:
            The full image tag that was successfully built.

        Raises:
            FileNotFoundError: If the build context does not exist.
            RuntimeError: If ``docker build`` exits with a non-zero code.
        """
        build_context = Path(docker_config.build_context).resolve()
        if not build_context.exists():
            raise FileNotFoundError(f"Build context not found: {build_context}")

        # Ensure Dockerfile exists (generate when needed)
        dockerfile_path = self._ensure_dockerfile(docker_config, build_context)

        # Write .dockerignore next to the Dockerfile
        ignore_path = build_context / ".dockerignore"
        ignore_path.write_text(self.generate_dockerignore(docker_config))
        logger.debug("Wrote .dockerignore to %s", ignore_path)

        # Assemble docker build command
        cmd: list[str] = [
            "docker",
            "build",
            "--platform",
            docker_config.platform,
            "-t",
            tag,
            "-f",
            str(dockerfile_path),
        ]

        # Build arguments
        for key, value in docker_config.build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.append(str(build_context))

        # Enable BuildKit
        env = {**os.environ, "DOCKER_BUILDKIT": "1"}

        print(f"🐳 Building image: {tag}")
        print(f"   Platform : {docker_config.platform}")
        print(f"   Context  : {build_context}")
        logger.info("Running: %s", " ".join(cmd))

        try:
            if stream_logs:
                self._run_streaming(cmd, env=env)
            else:
                subprocess.run(cmd, check=True, env=env, capture_output=True)
            print("✅ Build successful!")
            return tag
        except subprocess.CalledProcessError as exc:
            logger.error("Docker build failed (exit %d)", exc.returncode)
            raise RuntimeError(
                f"Docker build failed with exit code {exc.returncode}",
            ) from exc

    # ------------------------------------------------------------------

    def generate_dockerfile(self, config: DockerConfig) -> str:
        """Generate a production-quality Dockerfile as a string.

        Depending on ``config.multi_stage``, the result is either a
        two-stage (builder → runtime) Dockerfile or a simpler single-
        stage variant.

        Args:
            config: Docker configuration describing the desired image.

        Returns:
            The full Dockerfile content as a single string.
        """
        if config.multi_stage:
            builder_base = self._resolve_base_image(config)
            lines = self._generate_builder_stage(config)
            lines.extend(self._generate_runtime_stage(config, builder_base))
        else:
            lines = self._generate_single_stage(config)

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------

    def compute_content_hash(self, config: DockerConfig) -> str:
        """Compute a deterministic SHA-256 content hash.

        The hash is derived from the serialised configuration dict plus
        the contents of any referenced requirements files.  This allows
        cache-friendly tagging – an image only needs to be rebuilt when
        its inputs actually change.

        Args:
            config: Docker configuration.

        Returns:
            A 12-character hexadecimal digest string.
        """
        hasher = hashlib.sha256()

        # 1. Config dict (sorted keys for determinism)
        config_bytes = json.dumps(config.to_dict(), sort_keys=True).encode()
        hasher.update(config_bytes)

        # 2. Requirements file content (if any)
        context = Path(config.build_context)
        for candidate in (
            config.requirements_file,
            "requirements.txt",
            "pyproject.toml",
            "uv.lock",
            "poetry.lock",
        ):
            if candidate is None:
                continue
            path = context / candidate
            if path.is_file():
                hasher.update(path.read_bytes())

        # 3. Conda file content
        if config.conda_file:
            conda_path = context / config.conda_file
            if conda_path.is_file():
                hasher.update(conda_path.read_bytes())

        return hasher.hexdigest()[:12]

    # ------------------------------------------------------------------

    def generate_tag(self, config: DockerConfig, base_name: str) -> str:
        """Generate an image tag based on the configured tagging strategy.

        Supported strategies:

        * ``content-hash`` – deterministic SHA-256 of config + deps.
        * ``git-sha`` – current ``HEAD`` short SHA from *git*.
        * ``latest`` – always ``latest``.
        * ``semver`` – placeholder; falls back to ``content-hash``.

        Args:
            config: Docker configuration.
            base_name: Repository / image base name
                (e.g. ``"my-pipeline"``).

        Returns:
            A full ``<base_name>:<tag>`` string.
        """
        strategy = config.tag_strategy

        if strategy == "content-hash":
            digest = self.compute_content_hash(config)
            return f"{base_name}:{digest}"

        if strategy == "git-sha":
            try:
                sha = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=config.build_context,
                    text=True,
                ).strip()
                return f"{base_name}:{sha}"
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning(
                    "git-sha strategy failed; falling back to content-hash",
                )
                digest = self.compute_content_hash(config)
                return f"{base_name}:{digest}"

        if strategy == "latest":
            return f"{base_name}:latest"

        if strategy == "semver":
            logger.info(
                "semver strategy not yet implemented; using content-hash",
            )
            digest = self.compute_content_hash(config)
            return f"{base_name}:{digest}"

        logger.warning("Unknown tag strategy %r; using content-hash", strategy)
        digest = self.compute_content_hash(config)
        return f"{base_name}:{digest}"

    # ------------------------------------------------------------------

    def generate_dockerignore(self, config: DockerConfig) -> str:
        """Generate ``.dockerignore`` content.

        Combines a sensible set of default exclusion patterns with any
        user-supplied ``config.exclude_patterns``.

        Args:
            config: Docker configuration.

        Returns:
            Content suitable for writing to a ``.dockerignore`` file.
        """
        patterns = list(_DEFAULT_DOCKERIGNORE_PATTERNS)
        if config.exclude_patterns:
            patterns.extend(config.exclude_patterns)

        # De-duplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                unique.append(p)

        return "\n".join(unique) + "\n"

    # ── Private helpers ───────────────────────────────────────────────

    def _resolve_base_image(self, config: DockerConfig) -> str:
        """Select the base Docker image.

        When ``config.gpu_enabled`` is ``True`` the method returns the
        matching NVIDIA CUDA runtime image.  Otherwise it falls back to
        ``config.base_image``.

        Args:
            config: Docker configuration.

        Returns:
            A Docker image reference string.
        """
        if config.gpu_enabled:
            cuda_ver = config.cuda_version or _DEFAULT_CUDA_VERSION
            base = self.CUDA_BASE_IMAGES.get(cuda_ver)
            if base is None:
                supported = ", ".join(sorted(self.CUDA_BASE_IMAGES))
                logger.warning(
                    "Unsupported CUDA version %r (supported: %s); " "falling back to %s",
                    cuda_ver,
                    supported,
                    config.base_image,
                )
                return config.base_image
            logger.info("GPU enabled – using CUDA base image: %s", base)
            return base

        return config.base_image

    # ------------------------------------------------------------------

    def _generate_builder_stage(self, config: DockerConfig) -> list[str]:
        """Generate the *builder* stage of a multi-stage Dockerfile.

        This stage installs build tooling, creates a virtual-environment,
        and compiles / downloads all dependencies.  Only the resulting
        ``/app/.venv`` directory is carried forward to the runtime stage.

        Args:
            config: Docker configuration.

        Returns:
            A list of Dockerfile instruction lines.
        """
        base = self._resolve_base_image(config)
        lines: list[str] = [
            "# ── builder stage ─────────────────────────────────────",
            f"FROM {base} AS builder",
            "",
            "ENV PYTHONDONTWRITEBYTECODE=1 \\",
            "    PYTHONUNBUFFERED=1",
            "",
            "WORKDIR /app",
            "",
        ]

        # System packages (builder may need compilers, dev headers)
        if config.apt_packages:
            lines.append(self._generate_apt_install(config.apt_packages))
            lines.append("")

        # Install the chosen dependency manager and deps
        manager = self._detect_dependency_manager(config)
        logger.info("Dependency manager: %s", manager)
        lines.extend(self._generate_dep_install_lines(config, manager, stage="builder"))
        lines.append("")

        return lines

    # ------------------------------------------------------------------

    def _generate_runtime_stage(
        self,
        config: DockerConfig,
        builder_image: str,
    ) -> list[str]:
        """Generate the *runtime* stage of a multi-stage Dockerfile.

        Copies the virtual-environment from the builder stage, sets
        ``PATH``, applies env-vars, creates a non-root user, and
        configures the entrypoint.

        Args:
            config: Docker configuration.
            builder_image: The base image reference (used for a clean
                ``FROM`` in the runtime stage).

        Returns:
            A list of Dockerfile instruction lines.
        """
        base = self._resolve_base_image(config)
        lines: list[str] = [
            "# ── runtime stage ─────────────────────────────────────",
            f"FROM {base} AS runtime",
            "",
            "ENV PYTHONDONTWRITEBYTECODE=1 \\",
            "    PYTHONUNBUFFERED=1",
            "",
            "WORKDIR /app",
            "",
        ]

        # Minimal runtime system packages (no compilers)
        runtime_apt = self._runtime_apt_packages(config)
        if runtime_apt:
            lines.append(self._generate_apt_install(runtime_apt))
            lines.append("")

        # Copy virtual-env from builder
        lines.append("# Copy virtual environment from builder")
        lines.append("COPY --from=builder /app/.venv /app/.venv")
        lines.append('ENV PATH="/app/.venv/bin:$PATH"')
        lines.append("")

        # Copy source code
        lines.append("# Copy application source")
        lines.append("COPY . .")
        lines.append("")

        # User-defined environment variables
        if config.env_vars:
            for key, value in config.env_vars.items():
                lines.append(f"ENV {key}={value}")
            lines.append("")

        # Non-root user for security
        lines.extend(
            [
                "# Run as non-root for security",
                "RUN groupadd --gid 1000 appuser \\",
                "    && useradd --uid 1000 --gid appuser --shell /bin/bash " "--create-home appuser \\",
                "    && chown -R appuser:appuser /app",
                "USER appuser",
                "",
            ],
        )

        # Command / Entrypoint
        lines.extend(self._generate_entrypoint_lines(config))

        return lines

    # ------------------------------------------------------------------

    def _generate_single_stage(self, config: DockerConfig) -> list[str]:
        """Generate a single-stage Dockerfile.

        Used when ``config.multi_stage`` is ``False``.  The resulting
        image is larger but simpler and sometimes easier to debug.

        Args:
            config: Docker configuration.

        Returns:
            A list of Dockerfile instruction lines.
        """
        base = self._resolve_base_image(config)
        lines: list[str] = [
            f"FROM {base}",
            "",
            "ENV PYTHONDONTWRITEBYTECODE=1 \\",
            "    PYTHONUNBUFFERED=1",
            "",
            "WORKDIR /app",
            "",
        ]

        # System packages
        if config.apt_packages:
            lines.append(self._generate_apt_install(config.apt_packages))
            lines.append("")

        # Dependencies
        manager = self._detect_dependency_manager(config)
        logger.info("Dependency manager (single-stage): %s", manager)
        lines.extend(self._generate_dep_install_lines(config, manager, stage="single"))
        lines.append("")

        # Copy source
        lines.append("COPY . .")
        lines.append("")

        # Env vars
        if config.env_vars:
            for key, value in config.env_vars.items():
                lines.append(f"ENV {key}={value}")
            lines.append("")

        # Entrypoint
        lines.extend(self._generate_entrypoint_lines(config))

        return lines

    # ------------------------------------------------------------------

    def _detect_dependency_manager(self, config: DockerConfig) -> str:
        """Detect which dependency manager to use.

        Resolution order (first match wins):

        1. ``config.use_conda`` → ``"conda"``
        2. ``config.use_uv`` **and** ``uv.lock`` exists → ``"uv-lock"``
        3. ``config.use_poetry`` **and** ``poetry.lock`` exists → ``"poetry"``
        4. ``config.requirements_file`` set → ``"requirements-file"``
        5. ``requirements.txt`` exists in context → ``"requirements-txt"``
        6. ``config.requirements`` list provided → ``"inline"``
        7. ``config.replicate_local_env`` → ``"freeze"``
        8. Fallback → ``"none"``

        Args:
            config: Docker configuration.

        Returns:
            A short string identifier for the chosen manager.
        """
        context = Path(config.build_context)

        if config.use_conda:
            return "conda"

        if config.use_uv and (context / "uv.lock").is_file():
            return "uv-lock"

        if config.use_poetry and (context / "poetry.lock").is_file():
            return "poetry"

        if config.requirements_file:
            return "requirements-file"

        if (context / "requirements.txt").is_file():
            return "requirements-txt"

        if config.requirements:
            return "inline"

        if config.replicate_local_env:
            return "freeze"

        return "none"

    # ------------------------------------------------------------------

    def _generate_dep_install_lines(
        self,
        config: DockerConfig,
        manager: str,
        stage: str = "builder",
    ) -> list[str]:
        """Generate dependency installation Dockerfile lines.

        Each manager produces appropriate ``COPY`` and ``RUN`` lines.
        When ``config.cache_pip`` is enabled the ``RUN`` directives
        include BuildKit ``--mount=type=cache`` for faster rebuilds.

        Args:
            config: Docker configuration.
            manager: Manager identifier returned by
                :meth:`_detect_dependency_manager`.
            stage: Either ``"builder"`` or ``"single"`` – controls
                whether a virtual-env is explicitly created.

        Returns:
            A list of Dockerfile lines.
        """
        lines: list[str] = []
        cache_uv = "--mount=type=cache,target=/root/.cache/uv " if config.cache_pip else ""
        cache_pip = "--mount=type=cache,target=/root/.cache/pip " if config.cache_pip else ""
        cache_conda = "--mount=type=cache,target=/opt/conda/pkgs " if config.cache_pip else ""

        # ── Conda / Mamba ─────────────────────────────────────────────
        if manager == "conda":
            conda_file = config.conda_file or "environment.yml"
            lines.append("# Install conda / mamba")
            lines.append(
                "RUN apt-get update && apt-get install -y --no-install-recommends "
                "wget && rm -rf /var/lib/apt/lists/*",
            )
            lines.append(
                "RUN wget -qO /tmp/mambaforge.sh "
                "https://github.com/conda-forge/miniforge/releases/latest/"
                "download/Mambaforge-Linux-x86_64.sh "
                "&& bash /tmp/mambaforge.sh -b -p /opt/conda "
                "&& rm /tmp/mambaforge.sh",
            )
            lines.append('ENV PATH="/opt/conda/bin:$PATH"')
            lines.append(f"COPY {conda_file} .")
            lines.append(
                f"RUN {cache_conda}mamba env update -n base -f {conda_file} " f"&& conda clean -afy",
            )
            return lines

        # Every non-conda path starts by installing uv
        lines.append("# Install uv (fast Python package manager)")
        lines.append(
            f"RUN {cache_pip}pip install --no-cache-dir uv",
        )
        lines.append("ENV VIRTUAL_ENV=/app/.venv")
        lines.append('ENV PATH="$VIRTUAL_ENV/bin:$PATH"')
        lines.append("RUN uv venv $VIRTUAL_ENV")
        lines.append("")

        # ── uv lock ───────────────────────────────────────────────────
        if manager == "uv-lock":
            lines.append("# Sync from uv.lock (frozen)")
            lines.append("COPY pyproject.toml uv.lock ./")
            lines.append(
                f"RUN {cache_uv}uv sync --frozen --no-install-project",
            )

        # ── Poetry ────────────────────────────────────────────────────
        elif manager == "poetry":
            lines.append("# Install dependencies via Poetry")
            lines.append(
                f"RUN {cache_pip}pip install --no-cache-dir poetry",
            )
            lines.append("COPY pyproject.toml poetry.lock ./")
            lines.append("RUN poetry config virtualenvs.create false")
            lines.append(
                f"RUN {cache_pip}poetry install " f"--no-interaction --no-ansi --no-root --only main",
            )

        # ── Explicit requirements file ────────────────────────────────
        elif manager == "requirements-file":
            req = config.requirements_file
            lines.append(f"# Install from {req}")
            lines.append(f"COPY {req} .")
            basename = Path(req).name  # type: ignore[arg-type]
            lines.append(
                f"RUN {cache_uv}uv pip install -r {basename}",
            )

        # ── requirements.txt in context ───────────────────────────────
        elif manager == "requirements-txt":
            lines.append("# Install from requirements.txt")
            lines.append("COPY requirements.txt .")
            lines.append(
                f"RUN {cache_uv}uv pip install -r requirements.txt",
            )

        # ── Inline requirements list ──────────────────────────────────
        elif manager == "inline":
            pkgs = " ".join(f'"{p}"' for p in (config.requirements or []))
            lines.append("# Install inline requirements")
            lines.append(
                f"RUN {cache_uv}uv pip install {pkgs}",
            )

        # ── Freeze local env ──────────────────────────────────────────
        elif manager == "freeze":
            frozen = self._freeze_local_env()
            if frozen:
                # We write a temp requirements block directly
                reqs = " ".join(f'"{p}"' for p in frozen)
                lines.append("# Replicate local environment (pip freeze)")
                lines.append(
                    f"RUN {cache_uv}uv pip install {reqs}",
                )

        # ── none ──────────────────────────────────────────────────────
        else:
            lines.append("# No dependency manager detected")

        return lines

    # ------------------------------------------------------------------

    def _generate_apt_install(self, packages: list[str]) -> str:
        """Generate an ``apt-get install`` Dockerfile line.

        Packages are installed with ``--no-install-recommends`` and the
        apt cache is cleaned in the same layer to keep the image small.

        Args:
            packages: List of Debian package names to install.

        Returns:
            A single ``RUN`` instruction string.
        """
        pkg_str = " \\\n    ".join(sorted(packages))
        return (
            "RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            f"    {pkg_str} \\\n"
            "    && rm -rf /var/lib/apt/lists/*"
        )

    # ------------------------------------------------------------------

    def _freeze_local_env(self) -> list[str]:
        """Freeze the local Python environment packages.

        Invokes ``pip freeze`` in the current interpreter and returns
        the resulting package specifiers.

        Returns:
            A list of ``package==version`` strings.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                check=True,
            )
            packages = [
                line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith("#")
            ]
            logger.info("Froze %d packages from local environment", len(packages))
            return packages
        except subprocess.CalledProcessError:
            logger.warning("pip freeze failed; returning empty list")
            return []

    # ------------------------------------------------------------------

    def _ensure_dockerfile(
        self,
        config: DockerConfig,
        context: Path,
    ) -> Path:
        """Resolve an existing Dockerfile or generate one.

        If ``config.dockerfile`` is set, the method locates it relative
        to *context* (falling back to an absolute path).  Otherwise a
        temporary ``.flowyml.Dockerfile`` is generated inside *context*.

        Args:
            config: Docker configuration.
            context: Resolved build-context path.

        Returns:
            The :class:`~pathlib.Path` to the Dockerfile.

        Raises:
            FileNotFoundError: If the specified Dockerfile cannot be
                found.
        """
        if config.dockerfile:
            path = context / config.dockerfile
            if not path.exists():
                path = Path(config.dockerfile)
                if not path.exists():
                    raise FileNotFoundError(
                        f"Dockerfile not found: {config.dockerfile}",
                    )
            logger.info("Using existing Dockerfile: %s", path)
            return path

        generated_path = context / ".flowyml.Dockerfile"
        content = self.generate_dockerfile(config)
        generated_path.write_text(content)
        logger.info("Generated Dockerfile at %s", generated_path)
        return generated_path

    # ── Internal utilities ────────────────────────────────────────────

    @staticmethod
    def _runtime_apt_packages(config: DockerConfig) -> list[str]:
        """Return a minimal set of runtime-only system packages.

        Compiler / header packages listed in ``config.apt_packages``
        that are only needed at build time are *excluded* from the
        runtime stage.  Currently we carry all user-specified packages
        through because we cannot reliably classify them.

        Args:
            config: Docker configuration.

        Returns:
            Filtered list of packages for the runtime stage.
        """
        if not config.apt_packages:
            return []
        # Future: filter out *-dev, gcc, g++, make, etc.
        build_only = {
            "build-essential",
            "gcc",
            "g++",
            "make",
            "cmake",
            "pkg-config",
        }
        return [p for p in config.apt_packages if p not in build_only]

    # ------------------------------------------------------------------

    @staticmethod
    def _generate_entrypoint_lines(config: DockerConfig) -> list[str]:
        """Generate ``ENTRYPOINT`` / ``CMD`` Dockerfile lines.

        If ``config.entrypoint`` is set it is split on whitespace and
        used as the ``ENTRYPOINT`` exec-form array.  Otherwise a
        default ``["python"]`` entrypoint is used.

        ``config.command`` is rendered as a ``CMD`` directive and
        ``config.args`` is *not* emitted separately (it is typically
        consumed by orchestrators, not baked into the image).

        Args:
            config: Docker configuration.

        Returns:
            A list of Dockerfile lines.
        """
        lines: list[str] = []

        if config.entrypoint:
            parts = config.entrypoint.split()
            entry_json = json.dumps(parts)
            lines.append(f"ENTRYPOINT {entry_json}")
        else:
            lines.append('ENTRYPOINT ["python"]')

        if config.command:
            cmd_json = json.dumps(config.command)
            lines.append(f"CMD {cmd_json}")

        if not lines:
            lines.append('ENTRYPOINT ["python"]')

        lines.append("")
        return lines

    # ------------------------------------------------------------------

    @staticmethod
    def _run_streaming(
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
    ) -> None:
        """Execute *cmd* and stream stdout/stderr line-by-line.

        Args:
            cmd: Command list passed to :class:`subprocess.Popen`.
            env: Optional environment mapping.

        Raises:
            subprocess.CalledProcessError: When the command exits with
                a non-zero return code.
        """
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        ) as proc:
            assert proc.stdout is not None  # noqa: S101
            for line in proc.stdout:
                print(line, end="")
            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)
