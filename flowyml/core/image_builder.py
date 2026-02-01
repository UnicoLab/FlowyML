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
        """Generate Dockerfile content based on requirements."""
        lines = [f"FROM {config.base_image}", "WORKDIR /app"]

        # Copy requirements first for cache
        if config.requirements or (Path(config.build_context) / "requirements.txt").exists():
            lines.append("COPY requirements.txt .")
            lines.append("RUN pip install -r requirements.txt")
        elif (Path(config.build_context) / "pyproject.toml").exists():
            lines.append("RUN pip install poetry")
            lines.append("COPY pyproject.toml poetry.lock* .")
            lines.append("RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi")

        # Copy source code
        lines.append("COPY . .")

        # Env vars
        for k, v in config.env_vars.items():
            lines.append(f"ENV {k}={v}")

        return "\n".join(lines)
