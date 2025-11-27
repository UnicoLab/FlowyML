"""Model Asset - Represents ML models with metadata and lineage."""

from typing import Any
from uniflow.assets.base import Asset


class Model(Asset):
    """Model asset with training metadata and lineage.

    Example:
        >>> model = Model(
        ...     name="resnet50_v1",
        ...     version="v1.0.0",
        ...     data=trained_model,
        ...     architecture="resnet50",
        ...     framework="pytorch",
        ...     properties={"params": 25_557_032},
        ... )
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: Any = None,
        architecture: str | None = None,
        framework: str | None = None,
        input_shape: tuple | None = None,
        output_shape: tuple | None = None,
        trained_on: Asset | None = None,
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

        self.architecture = architecture
        self.framework = framework
        self.input_shape = input_shape
        self.output_shape = output_shape

        # Track training dataset
        if trained_on:
            self.parents.append(trained_on)
            trained_on.children.append(self)

        # Add model-specific properties
        if architecture:
            self.metadata.properties["architecture"] = architecture
        if framework:
            self.metadata.properties["framework"] = framework
        if input_shape:
            self.metadata.properties["input_shape"] = input_shape
        if output_shape:
            self.metadata.properties["output_shape"] = output_shape

    def get_training_datasets(self):
        """Get all datasets this model was trained on."""
        from uniflow.assets.dataset import Dataset

        return [p for p in self.parents if isinstance(p, Dataset)]

    def get_parameters_count(self) -> int | None:
        """Get number of model parameters if available."""
        return self.metadata.properties.get("params") or self.metadata.properties.get("parameters")

    def get_architecture_info(self) -> dict[str, Any]:
        """Get architecture information."""
        return {
            "architecture": self.architecture,
            "framework": self.framework,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "parameters": self.get_parameters_count(),
        }
