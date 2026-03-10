"""Checkpoint Asset - Represents training checkpoints with resumability metadata."""

from datetime import datetime
from pathlib import Path
from typing import Any

from flowyml.assets.base import Asset


class Checkpoint(Asset):
    """Checkpoint asset for training resumability and model snapshots.

    Tracks serialised training state (weights, optimiser, epoch) so that
    interrupted runs can be resumed exactly where they left off.

    Example:
        >>> checkpoint = Checkpoint.create(
        ...     data=model.state_dict(),  # or keras model
        ...     name="resnet50_epoch_10",
        ...     epoch=10,
        ...     step=5000,
        ...     metrics={"loss": 0.23, "accuracy": 0.91},
        ...     file_path="checkpoints/epoch_10.pt",
        ... )

        >>> # Quick check
        >>> print(checkpoint.epoch)  # 10
        >>> print(checkpoint.is_best)  # False (set explicitly)
        >>> print(checkpoint.file_path)  # checkpoints/epoch_10.pt
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: Any = None,
        epoch: int | None = None,
        step: int | None = None,
        metrics: dict[str, float] | None = None,
        file_path: str | None = None,
        is_best: bool = False,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
    ):
        """Initialise Checkpoint.

        Args:
            name: Checkpoint name / identifier.
            version: Version string.
            data: Serialised state (state_dict, weights array, etc.).
            epoch: Training epoch number.
            step: Global training step.
            metrics: Metrics at checkpoint time (loss, accuracy, …).
            file_path: Path where the checkpoint file is stored.
            is_best: Whether this is the best checkpoint so far.
            parent: Parent asset for lineage tracking.
            tags: Key-value tags.
            properties: Additional metadata properties.
        """
        final_properties = properties.copy() if properties else {}

        if epoch is not None:
            final_properties["epoch"] = epoch
        if step is not None:
            final_properties["step"] = step
        if metrics:
            final_properties["checkpoint_metrics"] = metrics
        if file_path:
            final_properties["file_path"] = file_path
        final_properties["is_best"] = is_best

        # Detect data size if possible
        if data is not None:
            if hasattr(data, "__len__"):
                final_properties["num_tensors"] = len(data)
            if isinstance(data, dict):
                final_properties["state_keys"] = list(data.keys())[:20]

        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=final_properties,
        )

        self._epoch = epoch
        self._step = step
        self._metrics = metrics or {}
        self.file_path = file_path
        self.is_best = is_best

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def epoch(self) -> int | None:
        """Training epoch at checkpoint time."""
        return self._epoch

    @property
    def step(self) -> int | None:
        """Global training step at checkpoint time."""
        return self._step

    @property
    def checkpoint_metrics(self) -> dict[str, float]:
        """Metrics captured at checkpoint time."""
        return self._metrics

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        data: Any,
        name: str | None = None,
        version: str | None = None,
        epoch: int | None = None,
        step: int | None = None,
        metrics: dict[str, float] | None = None,
        file_path: str | None = None,
        is_best: bool = False,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "Checkpoint":
        """Factory method to create a Checkpoint.

        Args:
            data: Serialised model state.
            name: Checkpoint name (auto-generated if omitted).
            version: Version string.
            epoch: Training epoch.
            step: Global step.
            metrics: Metrics dict (e.g. ``{"loss": 0.23}``).
            file_path: Path to checkpoint file on disk.
            is_best: Whether this is the best checkpoint.
            parent: Parent asset for lineage.
            tags: Tags dict.
            **kwargs: Extra properties.

        Returns:
            New ``Checkpoint`` instance.
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = f"_epoch{epoch}" if epoch is not None else ""
            name = f"checkpoint{suffix}_{timestamp}"

        return cls(
            name=name,
            version=version,
            data=data,
            epoch=epoch,
            step=step,
            metrics=metrics,
            file_path=file_path,
            is_best=is_best,
            parent=parent,
            tags=tags,
            properties=kwargs if kwargs else None,
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save(self, path: str | Path | None = None) -> Path:
        """Save checkpoint data to disk.

        Uses ``torch.save`` if data looks like a PyTorch state_dict,
        otherwise falls back to ``pickle``.

        Args:
            path: Target file path. Defaults to ``self.file_path``.

        Returns:
            Path where the checkpoint was saved.
        """
        target = Path(path or self.file_path or f".flowyml/checkpoints/{self.name}.ckpt")
        target.parent.mkdir(parents=True, exist_ok=True)

        # Try torch.save first
        try:
            import torch

            torch.save(self.data, str(target))
        except (ImportError, Exception):
            import pickle

            with open(target, "wb") as f:
                pickle.dump(self.data, f)

        self.file_path = str(target)
        self.metadata.properties["file_path"] = str(target)
        return target

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        parts = [f"Checkpoint(name='{self.name}'"]
        if self._epoch is not None:
            parts.append(f"epoch={self._epoch}")
        if self._step is not None:
            parts.append(f"step={self._step}")
        if self.is_best:
            parts.append("best=True")
        return ", ".join(parts) + ")"
