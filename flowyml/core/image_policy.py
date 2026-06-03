"""Enterprise Docker image governance for FlowyML.

Provides policy validation for Docker images used in pipeline execution.
Platform teams define which base images are approved, what labels are
required, and whether scanning/signing is mandatory.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

__all__ = [
    "ImagePolicy",
    "ImagePolicyResult",
    "ImagePolicyValidator",
]


# ---------------------------------------------------------------------------
# Policy configuration
# ---------------------------------------------------------------------------


class ImagePolicy(BaseModel):
    """Policy configuration for Docker images.

    Platform teams create instances of this model (typically loaded from YAML)
    to describe which base images are approved, what security requirements
    apply, and which registries are allowed.

    Attributes:
        approved_base_images: Allowlist of approved base images.  Empty means
            all base images are allowed.
        denied_base_images: Blocklist of denied base images.  Denied list
            takes precedence over the approved list.
        require_non_root: When ``True``, the final image must contain a
            non-root ``USER`` directive.
        max_image_size_mb: Maximum allowed image size in megabytes.
        require_labels: Required OCI labels (e.g.
            ``org.opencontainers.image.source``).
        scan_on_build: Run a vulnerability scan before pushing.
        scan_severity_threshold: Minimum severity that causes a build to
            fail: ``LOW``, ``MEDIUM``, ``HIGH``, or ``CRITICAL``.
        sign_on_push: Sign the image with cosign after pushing.
        allowed_registries: Allowed container registries.
        require_pinned_base_image: Require base images to be pinned by
            digest (``sha256:…``).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # Base image controls
    approved_base_images: list[str] = Field(
        default_factory=list,
        alias="approvedBaseImages",
        description="Allowlist of approved base images. Empty = all allowed.",
    )
    denied_base_images: list[str] = Field(
        default_factory=list,
        alias="deniedBaseImages",
        description="Blocklist of denied base images.",
    )

    # Security requirements
    require_non_root: bool = Field(
        alias="requireNonRoot",
        default=True,
        description="Require non-root USER in final image.",
    )
    max_image_size_mb: int | None = Field(
        alias="maxImageSizeMb",
        default=None,
        description="Maximum allowed image size in MB.",
    )

    # Labels & metadata
    require_labels: list[str] = Field(
        default_factory=list,
        alias="requireLabels",
        description="Required OCI labels (e.g., org.opencontainers.image.source).",
    )

    # Scanning & signing
    scan_on_build: bool = Field(
        alias="scanOnBuild",
        default=False,
        description="Run vulnerability scan before pushing.",
    )
    scan_severity_threshold: str = Field(
        alias="scanSeverityThreshold",
        default="HIGH",
        description="Minimum severity to block: LOW, MEDIUM, HIGH, CRITICAL.",
    )
    sign_on_push: bool = Field(
        alias="signOnPush",
        default=False,
        description="Sign image with cosign after push.",
    )

    # Registry controls
    allowed_registries: list[str] = Field(
        default_factory=list,
        alias="allowedRegistries",
        description="Allowed container registries.",
    )

    # Pinning
    require_pinned_base_image: bool = Field(
        alias="requirePinnedBaseImage",
        default=False,
        description="Require base images to be pinned by digest (sha256:...).",
    )


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


class ImagePolicyResult(BaseModel):
    """Result of a single policy check.

    Attributes:
        rule_name: Machine-readable identifier for the rule.
        status: One of ``passed``, ``failed``, or ``warning``.
        message: Human-readable explanation of the outcome.
        suggestion: Optional actionable fix when the rule fails.
    """

    rule_name: str
    status: str  # 'passed', 'failed', 'warning'
    message: str
    suggestion: str | None = None


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ImagePolicyValidator:
    """Validates Docker images and Dockerfiles against enterprise policies.

    The validator runs a series of checks against an ``ImagePolicy`` and
    returns a list of ``ImagePolicyResult`` objects.  The high-level
    :meth:`check` method raises ``ValueError`` when any rule fails.

    Args:
        policy: The ``ImagePolicy`` to enforce.

    Example::

        from flowyml.core.image_policy import ImagePolicy, ImagePolicyValidator

        policy = ImagePolicy(
            approvedBaseImages=["python:3.11-slim"],
            requireNonRoot=True,
        )
        validator = ImagePolicyValidator(policy)
        validator.check(dockerfile_content=open("Dockerfile").read())
    """

    def __init__(self, policy: ImagePolicy) -> None:
        self._policy = policy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_config(self, docker_config: Any) -> list[ImagePolicyResult]:
        """Validate a ``DockerConfig`` against the image policy.

        The *docker_config* object is expected to have ``base_image`` and
        ``image`` string attributes (duck-typed to avoid circular imports).

        Args:
            docker_config: An object with ``base_image`` and optionally
                ``image`` attributes.

        Returns:
            List of policy check results.
        """
        results: list[ImagePolicyResult] = []

        # Check base image approval
        if docker_config.base_image:
            results.append(self._check_base_image(docker_config.base_image))

        # Check pinning
        if self._policy.require_pinned_base_image:
            results.append(self._check_pinned_image(docker_config.base_image))

        # Check registry
        if docker_config.image and self._policy.allowed_registries:
            results.append(self._check_registry(docker_config.image))

        # Check required labels
        if self._policy.require_labels and hasattr(docker_config, "labels"):
            missing_labels = [
                label for label in self._policy.require_labels if label not in (docker_config.labels or {})
            ]
            if missing_labels:
                results.append(
                    ImagePolicyResult(
                        rule_name="require_labels",
                        status="failed",
                        message=f"Missing required labels: {', '.join(missing_labels)}",
                        suggestion=f"Add these labels to DockerConfig.labels: {missing_labels}",
                    ),
                )
            else:
                results.append(
                    ImagePolicyResult(
                        rule_name="require_labels",
                        status="passed",
                        message="All required labels present.",
                    ),
                )

        return results

    def validate_dockerfile(
        self,
        dockerfile_content: str,
    ) -> list[ImagePolicyResult]:
        """Validate a raw Dockerfile string against the image policy.

        Parses ``FROM`` and ``USER`` directives from the Dockerfile to
        verify base image and non-root-user compliance.

        Args:
            dockerfile_content: Full content of a Dockerfile.

        Returns:
            List of policy check results.
        """
        results: list[ImagePolicyResult] = []
        lines = dockerfile_content.strip().split("\n")

        # ----------------------------------------------------------
        # Check FROM images
        # ----------------------------------------------------------
        from_lines = [line.strip() for line in lines if line.strip().upper().startswith("FROM")]
        for from_line in from_lines:
            parts = from_line.split()
            if len(parts) >= 2:
                image = parts[1]
                results.append(self._check_base_image(image))
                if self._policy.require_pinned_base_image:
                    results.append(self._check_pinned_image(image))

        # ----------------------------------------------------------
        # Check for non-root USER
        # ----------------------------------------------------------
        if self._policy.require_non_root:
            user_lines = [line for line in lines if line.strip().upper().startswith("USER")]
            non_root_found = any(
                line.strip().split()[-1].lower() not in ("root", "0")
                for line in user_lines
                if len(line.strip().split()) >= 2
            )
            if not non_root_found:
                results.append(
                    ImagePolicyResult(
                        rule_name="non_root_user",
                        status="warning",
                        message=("No non-root USER directive found in Dockerfile."),
                        suggestion=('Add "USER nonroot" or "USER 1000" for ' "production security."),
                    ),
                )
            else:
                results.append(
                    ImagePolicyResult(
                        rule_name="non_root_user",
                        status="passed",
                        message="Non-root USER directive found.",
                    ),
                )

        return results

    def check(
        self,
        docker_config: Any = None,
        dockerfile_content: str | None = None,
    ) -> None:
        """Run all checks and raise ``ValueError`` if any fail.

        This is a convenience wrapper around :meth:`validate_config` and
        :meth:`validate_dockerfile` that raises on the first set of
        failures.

        Args:
            docker_config: Optional ``DockerConfig`` to validate.
            dockerfile_content: Optional raw Dockerfile string.

        Raises:
            ValueError: If one or more policy rules fail.
        """
        results: list[ImagePolicyResult] = []
        if docker_config:
            results.extend(self.validate_config(docker_config))
        if dockerfile_content:
            results.extend(self.validate_dockerfile(dockerfile_content))

        failures = [r for r in results if r.status == "failed"]
        if failures:
            messages = "\n".join(f"  - {r.rule_name}: {r.message}" for r in failures)
            raise ValueError(
                f"Docker image policy validation failed:\n{messages}\n\n"
                "Fix the issues above or contact the platform team for "
                "exceptions.",
            )

    # ------------------------------------------------------------------
    # Private rule implementations
    # ------------------------------------------------------------------

    def _check_base_image(self, image: str) -> ImagePolicyResult:
        """Check if a base image is approved.

        The denied list takes precedence: if the image matches any denied
        pattern, it fails immediately even if it also matches an approved
        pattern.

        Args:
            image: Docker image reference (e.g. ``python:3.11-slim``).

        Returns:
            Policy result for the base-image rule.
        """
        # Denied list takes precedence
        for denied in self._policy.denied_base_images:
            if denied in image:
                return ImagePolicyResult(
                    rule_name="base_image_denied",
                    status="failed",
                    message=(f'Base image "{image}" matches denied pattern ' f'"{denied}".'),
                    suggestion=("Use one of the approved base images from the " "platform team."),
                )

        # Check approved list (if non-empty)
        if self._policy.approved_base_images:
            if not any(approved in image for approved in self._policy.approved_base_images):
                return ImagePolicyResult(
                    rule_name="base_image_not_approved",
                    status="failed",
                    message=(f'Base image "{image}" is not in the approved list.'),
                    suggestion=(f"Approved images: {self._policy.approved_base_images}"),
                )

        return ImagePolicyResult(
            rule_name="base_image_approved",
            status="passed",
            message=f'Base image "{image}" is approved.',
        )

    def _check_pinned_image(self, image: str) -> ImagePolicyResult:
        """Check if the image is pinned by digest.

        Args:
            image: Docker image reference.

        Returns:
            Policy result for the pinning rule.
        """
        if "@sha256:" in image:
            return ImagePolicyResult(
                rule_name="image_pinned",
                status="passed",
                message=f'Image "{image}" is pinned by digest.',
            )
        return ImagePolicyResult(
            rule_name="image_not_pinned",
            status="failed",
            message=f'Image "{image}" is not pinned by digest.',
            suggestion="Use image@sha256:... for reproducibility.",
        )

    def _check_registry(self, image_uri: str) -> ImagePolicyResult:
        """Check if the image URI uses an allowed registry.

        Args:
            image_uri: Full image URI (e.g.
                ``myregistry.azurecr.io/flowyml/train:latest``).

        Returns:
            Policy result for the registry rule.
        """
        for reg in self._policy.allowed_registries:
            if image_uri.startswith(reg):
                return ImagePolicyResult(
                    rule_name="registry_allowed",
                    status="passed",
                    message=f"Image registry is allowed: {reg}.",
                )
        return ImagePolicyResult(
            rule_name="registry_not_allowed",
            status="failed",
            message=f'Image "{image_uri}" uses a disallowed registry.',
            suggestion=(f"Allowed registries: {self._policy.allowed_registries}"),
        )
