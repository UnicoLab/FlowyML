"""DockerHub Container Registry component for FlowyML.

Provides a :class:`DockerHubContainerRegistry` that wraps the public
Docker Hub registry (``docker.io``) and exposes ``push``, ``pull``, and
``login`` operations via the local Docker CLI.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

from flowyml.stacks.components import ContainerRegistry
from flowyml.stacks.plugins import register_component

logger = logging.getLogger(__name__)


@register_component(name="dockerhub")
class DockerHubContainerRegistry(ContainerRegistry):
    """Container registry implementation backed by Docker Hub.

    This component delegates to the local ``docker`` CLI for all image
    operations (tag, push, pull, login).  It targets the public Docker Hub
    registry at ``docker.io``.

    Args:
        name: Logical component name within a FlowyML stack.
        username: Docker Hub username (required).
        repository: Docker Hub repository namespace.  Defaults to
            *username* when not provided.
        password: Docker Hub password used for ``docker login``.  Mutually
            exclusive with *token* – if both are supplied *token* takes
            precedence.
        token: Docker Hub personal-access token (PAT) used for
            ``docker login``.  Preferred over *password*.

    Example::

        registry = DockerHubContainerRegistry(
            username="myuser",
            token="dckr_pat_xxxx",
        )
        registry.login()
        uri = registry.push_image("my-model-server", tag="v1.0.0")
        print(uri)  # docker.io/myuser/my-model-server:v1.0.0
    """

    # The canonical Docker Hub registry host used in image URIs.
    _REGISTRY_HOST: str = "docker.io"

    def __init__(
        self,
        name: str = "dockerhub",
        username: str | None = None,
        repository: str | None = None,
        password: str | None = None,
        token: str | None = None,
    ) -> None:
        super().__init__(name)
        self.username = username
        self.repository = repository or username
        self.password = password
        self.token = token

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> bool:
        """Validate the registry configuration.

        Ensures a *username* is set and that the ``docker`` CLI is
        available on ``$PATH``.

        Returns:
            ``True`` when the configuration is valid.

        Raises:
            ValueError: If required configuration is missing or the
                ``docker`` binary cannot be found.
        """
        if not self.username:
            raise ValueError(
                "username is required for DockerHubContainerRegistry",
            )

        if shutil.which("docker") is None:
            raise ValueError(
                "The 'docker' CLI is not installed or not on PATH. "
                "DockerHubContainerRegistry requires a working Docker "
                "installation.",
            )

        logger.debug(
            "DockerHubContainerRegistry '%s' configuration is valid.",
            self.name,
        )
        return True

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Authenticate to Docker Hub via ``docker login``.

        Uses *token* if available, otherwise falls back to *password*.
        If neither credential is provided the method is a no-op (the
        user is expected to have already authenticated via another
        mechanism, e.g. a Docker credential helper).

        Raises:
            subprocess.CalledProcessError: If ``docker login`` exits
                with a non-zero status.
        """
        credential = self.token or self.password
        if not credential:
            logger.info(
                "No password or token provided – skipping docker login. "
                "Ensure you are already authenticated to Docker Hub.",
            )
            return

        logger.info("Logging in to Docker Hub as '%s' …", self.username)
        subprocess.run(
            [
                "docker",
                "login",
                "--username",
                self.username,
                "--password-stdin",
            ],
            input=credential.encode(),
            check=True,
            capture_output=True,
        )
        logger.info("Successfully logged in to Docker Hub.")

    # ------------------------------------------------------------------
    # Image operations
    # ------------------------------------------------------------------

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        """Tag and push a local Docker image to Docker Hub.

        The method performs three steps:

        1. Authenticate via :meth:`login` (no-op when credentials are
           absent).
        2. ``docker tag <image_name>:<tag> <full_uri>``
        3. ``docker push <full_uri>``

        Args:
            image_name: Local image name (e.g. ``"my-app"``).
            tag: Image tag.  Defaults to ``"latest"``.

        Returns:
            The full image URI that was pushed, e.g.
            ``"docker.io/myuser/my-app:latest"``.

        Raises:
            subprocess.CalledProcessError: If any Docker CLI command
                fails.
        """
        full_uri = self.get_image_uri(image_name, tag)
        self.login()

        logger.info(
            "Tagging image '%s:%s' → '%s' …",
            image_name,
            tag,
            full_uri,
        )
        subprocess.run(
            ["docker", "tag", f"{image_name}:{tag}", full_uri],
            check=True,
        )

        logger.info("Pushing '%s' to Docker Hub …", full_uri)
        subprocess.run(["docker", "push", full_uri], check=True)

        logger.info("Successfully pushed '%s'.", full_uri)
        return full_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull a Docker image from Docker Hub.

        Args:
            image_name: Image name within the repository namespace
                (e.g. ``"my-app"``).
            tag: Image tag.  Defaults to ``"latest"``.

        Raises:
            subprocess.CalledProcessError: If ``docker pull`` fails.
        """
        full_uri = self.get_image_uri(image_name, tag)
        self.login()

        logger.info("Pulling '%s' from Docker Hub …", full_uri)
        subprocess.run(["docker", "pull", full_uri], check=True)
        logger.info("Successfully pulled '%s'.", full_uri)

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Build the fully-qualified image URI for Docker Hub.

        Args:
            image_name: Image name (e.g. ``"my-app"``).
            tag: Image tag.  Defaults to ``"latest"``.

        Returns:
            A URI of the form ``docker.io/<repository>/<image_name>:<tag>``.
        """
        return f"{self._REGISTRY_HOST}/{self.repository}/{image_name}:{tag}"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry_uri(self) -> str:
        """Return the base registry URI for this Docker Hub account.

        Returns:
            A string of the form ``docker.io/<username>``.
        """
        return f"{self._REGISTRY_HOST}/{self.username}"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the component to a plain dictionary.

        Sensitive fields (*password*, *token*) are deliberately excluded
        to avoid leaking secrets into stack configuration files.

        Returns:
            A JSON/YAML-safe dictionary representation of this
            component.
        """
        return {
            "name": self.name,
            "type": "dockerhub",
            "username": self.username,
            "repository": self.repository,
            "registry_uri": self.registry_uri,
        }
