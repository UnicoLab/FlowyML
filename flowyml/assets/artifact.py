"""Artifact Asset - Represents generic artifacts (configs, checkpoints, etc)."""

from typing import Any
from flowyml.assets.base import Asset


class Artifact(Asset):
    """Generic artifact asset for configs, checkpoints, reports, etc.

    Example:
        >>> config = Artifact(name="training_config", artifact_type="config", data={"lr": 0.001, "epochs": 10})
    """

    def __init__(
        self,
        name: str,
        artifact_type: str = "generic",
        version: str | None = None,
        data: Any = None,
        file_path: str | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=properties,
        )

        self.artifact_type = artifact_type
        self.file_path = file_path

        # Add artifact-specific properties
        self.metadata.properties["artifact_type"] = artifact_type
        if file_path:
            self.metadata.properties["file_path"] = file_path
