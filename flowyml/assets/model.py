"""Model Asset - Represents ML models with metadata and lineage."""

from typing import Any
from flowyml.assets.base import Asset


class Model(Asset):
    """Model asset with training metadata and lineage.

    Supports storing training history for visualization in the FlowyML dashboard.
    When `training_history` is provided, the UI will display interactive charts
    showing loss, accuracy, and other metrics over training epochs.

    Example:
        >>> model = Model(
        ...     name="resnet50_v1",
        ...     version="v1.0.0",
        ...     data=trained_model,
        ...     architecture="resnet50",
        ...     framework="pytorch",
        ...     properties={"params": 25_557_032},
        ...     training_history={
        ...         "epochs": [1, 2, 3],
        ...         "train_loss": [0.5, 0.3, 0.1],
        ...         "val_loss": [0.6, 0.4, 0.2],
        ...     },
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
        training_history: dict[str, list] | None = None,
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

        # Store training history for UI visualization
        # This will be displayed as interactive charts in the dashboard
        self.training_history = training_history

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
        from flowyml.assets.dataset import Dataset

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

    @classmethod
    def create(
        cls,
        data: Any,
        name: str | None = None,
        version: str | None = None,
        parent: "Asset | None" = None,
        **kwargs: Any,
    ) -> "Model":
        """Factory method to create a Model asset.

        This method properly handles Model-specific parameters like
        `training_history`, `architecture`, and `framework`.

        Args:
            data: The model object (Keras model, PyTorch model, etc.)
            name: Asset name
            version: Asset version
            parent: Parent asset for lineage
            **kwargs: Additional parameters including:
                - training_history: Dict of training metrics per epoch
                - architecture: Model architecture name
                - framework: ML framework (keras, pytorch, etc.)
                - properties: Additional properties
                - tags: Metadata tags

        Returns:
            New Model instance

        Example:
            >>> model_asset = Model.create(
            ...     data=trained_model,
            ...     name="my_model",
            ...     framework="keras",
            ...     training_history=callback.get_training_history(),
            ... )
        """
        from datetime import datetime

        asset_name = name or f"Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Extract Model-specific parameters
        training_history = kwargs.pop("training_history", None)
        architecture = kwargs.pop("architecture", None)
        framework = kwargs.pop("framework", None)
        input_shape = kwargs.pop("input_shape", None)
        output_shape = kwargs.pop("output_shape", None)
        trained_on = kwargs.pop("trained_on", None)

        # Extract tags and properties
        tags = kwargs.pop("tags", {})
        props = kwargs.pop("properties", {})
        # Merge remaining kwargs into properties
        props.update(kwargs)

        return cls(
            name=asset_name,
            version=version,
            data=data,
            architecture=architecture,
            framework=framework,
            input_shape=input_shape,
            output_shape=output_shape,
            trained_on=trained_on,
            parent=parent,
            tags=tags,
            properties=props,
            training_history=training_history,
        )
