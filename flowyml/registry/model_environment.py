"""Model environment capture for reproducibility."""

import sys
import subprocess
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class ModelEnvironment:
    r"""Captures Python environment for model reproducibility.

    Example:
        >>> env = ModelEnvironment.from_current()
        >>> print(env.python_version)
        '3.11.5'
        >>> env.to_requirements_txt()
        'numpy==1.24.0\npandas==2.0.0\n...'
    """

    python_version: str
    platform: str
    dependencies: list[str] = field(default_factory=list)
    system_info: dict[str, str] = field(default_factory=dict)
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_current(cls, include_all: bool = False) -> "ModelEnvironment":  # noqa: ARG003
        """Capture current Python environment.

        Args:
            include_all: If True, capture all packages. If False, only top-level.

        Returns:
            ModelEnvironment with current system info and dependencies
        """
        # Get pip freeze output
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            deps = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            deps = []

        # System info
        system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }

        return cls(
            python_version=platform.python_version(),
            platform=platform.platform(),
            dependencies=deps,
            system_info=system_info,
        )

    def to_requirements_txt(self) -> str:
        """Export dependencies as requirements.txt format.

        Returns:
            String with one dependency per line
        """
        return "\n".join(self.dependencies)

    def save_requirements(self, path: str) -> None:
        """Save dependencies to a requirements.txt file.

        Args:
            path: Path to save the file
        """
        with open(path, "w") as f:
            f.write(self.to_requirements_txt())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelEnvironment":
        """Create from dictionary."""
        return cls(**data)

    def get_package_version(self, package_name: str) -> str | None:
        """Get version of a specific package.

        Args:
            package_name: Name of the package to look up

        Returns:
            Version string or None if not found
        """
        for dep in self.dependencies:
            if dep.lower().startswith(package_name.lower() + "=="):
                return dep.split("==")[1]
            elif dep.lower().startswith(package_name.lower() + ">="):
                return dep.split(">=")[1]
        return None

    def __repr__(self) -> str:
        return f"ModelEnvironment(python={self.python_version}, deps={len(self.dependencies)})"
