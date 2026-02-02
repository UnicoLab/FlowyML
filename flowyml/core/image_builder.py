import subprocess
from pathlib import Path
from flowyml.stacks.components import DockerConfig


class DockerImageBuilder:
    """Handles building and pushing Docker images for remote execution."""

    def build_image(self, docker_config: DockerConfig, tag: str) -> str:
        """Build a Docker image from the configuration.

        Args:
            docker_config: The Docker configuration.
            tag: The tag to apply to the built image.

        Returns:
            The full image tag that was built.
        """
        build_context = Path(docker_config.build_context)
        if not build_context.exists():
            raise FileNotFoundError(f"Build context not found: {build_context}")

        # Auto-generate Dockerfile if needed
        dockerfile_path = self._ensure_dockerfile(docker_config, build_context)

        cmd = [
            "docker",
            "build",
            "-t",
            tag,
            "-f",
            str(dockerfile_path),
            str(build_context),
        ]

        # Add build args
        for k, v in docker_config.build_args.items():
            cmd.extend(["--build-arg", f"{k}={v}"])

        print(f"🐳 Building image: {tag}")
        try:
            subprocess.run(cmd, check=True)
            print("✅ Build successful!")
            return tag
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Docker build failed: {e}")

    def _ensure_dockerfile(self, config: DockerConfig, context: Path) -> Path:
        """Get path to Dockerfile or generate one."""
        if config.dockerfile:
            path = context / config.dockerfile
            if not path.exists():
                # Try absolute path
                path = Path(config.dockerfile)
                if not path.exists():
                    raise FileNotFoundError(f"Dockerfile not found: {config.dockerfile}")
            return path

        # Generate temporary Dockerfile
        generated_path = context / ".flowyml.Dockerfile"
        content = self._generate_dockerfile_content(config)
        generated_path.write_text(content)
        return generated_path

    def _generate_dockerfile_content(self, config: DockerConfig) -> str:
        """Generate Dockerfile content based on requirements.

        Prioritizes:
        1. uv.lock -> uv sync
        2. poetry.lock -> poetry install
        3. requirements.txt -> uv pip install
        4. list -> uv pip install
        """
        lines = [f"FROM {config.base_image}", "WORKDIR /app"]

        # Install system dependencies if any
        # lines.append("RUN apt-get update && apt-get install -y ...")

        context_path = Path(config.build_context)

        # 0. Always install uv as it's our preferred installer for pip/reqs too
        # We install it via the official installer script for speed and isolation
        lines.append("RUN pip install uv")
        lines.append("ENV VIRTUAL_ENV=/app/.venv")
        lines.append('ENV PATH="$VIRTUAL_ENV/bin:$PATH"')

        # 1. Check for uv.lock
        if (context_path / "uv.lock").exists():
            print("📦 Detected uv based project")
            lines.append("COPY pyproject.toml uv.lock ./")
            # Create venv and sync
            lines.append("RUN uv venv && uv sync --frozen --no-install-project")

        # 2. Check for poetry.lock
        elif (context_path / "poetry.lock").exists() or (context_path / "pyproject.toml").exists():
            print("📦 Detected Poetry based project")
            lines.append("RUN pip install poetry")
            lines.append("COPY pyproject.toml poetry.lock* ./")
            lines.append("RUN poetry config virtualenvs.in-project true")
            lines.append("RUN poetry install --no-interaction --no-ansi --no-root")
            # Add local venv to path if poetry created one
            lines.append('ENV PATH="/app/.venv/bin:$PATH"')

        # 3. Check for requirements.txt (Use uv for speed)
        elif (context_path / "requirements.txt").exists():
            print("📦 Detected requirements.txt")
            lines.append("COPY requirements.txt .")
            lines.append("RUN uv venv && uv pip install -r requirements.txt")

        # 4. Check for dynamic requirements list (Use uv for speed)
        elif config.requirements:
            print("📦 Detected dynamic requirements list")
            reqs_str = " ".join([f'"{r}"' for r in config.requirements])
            lines.append(f"RUN uv venv && uv pip install {reqs_str}")

        # Copy source code
        lines.append("COPY . .")

        # Install project itself if needed (for uv/poetry)
        if (context_path / "uv.lock").exists():
            lines.append("RUN uv sync --frozen")
        elif (context_path / "poetry.lock").exists():
            lines.append("RUN poetry install --no-interaction --no-ansi")

        # Env vars
        for k, v in config.env_vars.items():
            lines.append(f"ENV {k}={v}")

        return "\n".join(lines)
