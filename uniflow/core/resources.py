"""Resource specification for pipeline steps.

This module provides orchestrator-agnostic resource specification for UniFlow pipeline steps,
including CPU, memory, GPU, storage, and node affinity requirements.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import re


@dataclass
class GPUConfig:
    """GPU configuration specification.

    Args:
        gpu_type: GPU type/model (e.g., 'nvidia-tesla-v100', 'nvidia-a100')
        count: Number of GPUs required
        memory: GPU memory per device (e.g., '16Gi', '32Gi')

    Examples:
        >>> gpu = GPUConfig(gpu_type="nvidia-tesla-v100", count=2, memory="16Gi")
        >>> gpu = GPUConfig(gpu_type="nvidia-a100", count=4)
    """

    gpu_type: str
    count: int = 1
    memory: Optional[str] = None

    def __post_init__(self):
        """Validate GPU configuration."""
        if self.count < 1:
            msg = f"GPU count must be >= 1, got {self.count}"
            raise ValueError(msg)
        if self.memory and not self._is_valid_memory(self.memory):
            msg = f"Invalid GPU memory format: {self.memory}"
            raise ValueError(msg)

    @staticmethod
    def _is_valid_memory(memory: str) -> bool:
        """Check if memory string is valid (e.g., '16Gi', '32768Mi')."""
        return bool(re.match(r"^\d+(\.\d+)?(Ki|Mi|Gi|Ti|K|M|G|T)$", memory))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.gpu_type,
            "count": self.count,
            "memory": self.memory,
        }


@dataclass
class NodeAffinity:
    """Node affinity and anti-affinity rules.

    Args:
        required: Required node labels (hard constraints)
        preferred: Preferred node labels (soft constraints)
        tolerations: Tolerations for node taints

    Examples:
        >>> affinity = NodeAffinity(
        ...     required={"cloud.google.com/gke-nodepool": "gpu-pool"}, preferred={"instance-type": "n1-standard-8"}
        ... )
    """

    required: dict[str, str] = field(default_factory=dict)
    preferred: dict[str, str] = field(default_factory=dict)
    tolerations: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "required": self.required,
            "preferred": self.preferred,
            "tolerations": self.tolerations,
        }


@dataclass
class ResourceRequirements:
    """Resource requirements for a pipeline step.

    Orchestrator-agnostic resource specification that can be translated to
    platform-specific formats (Kubernetes, Vertex AI, SageMaker, etc.).

    Args:
        cpu: CPU cores (e.g., "2", "500m", "2.5")
        memory: RAM amount (e.g., "4Gi", "8192Mi", "16G")
        storage: Ephemeral storage (e.g., "100Gi", "50G")
        gpu: GPU configuration
        node_affinity: Node selection rules

    Examples:
        >>> # Simple CPU/memory
        >>> resources = ResourceRequirements(cpu="2", memory="4Gi")

        >>> # With GPU
        >>> resources = ResourceRequirements(cpu="4", memory="16Gi", gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=2))

        >>> # With node affinity
        >>> resources = ResourceRequirements(
        ...     cpu="8",
        ...     memory="32Gi",
        ...     node_affinity=NodeAffinity(
        ...         required={"gpu": "true"}, tolerations=[{"key": "nvidia.com/gpu", "operator": "Exists"}]
        ...     ),
        ... )
    """

    cpu: Optional[str] = None
    memory: Optional[str] = None
    storage: Optional[str] = None
    gpu: Optional[GPUConfig] = None
    node_affinity: Optional[NodeAffinity] = None

    def __post_init__(self):
        """Validate resource specifications."""
        if self.cpu and not self._is_valid_cpu(self.cpu):
            msg = f"Invalid CPU format: {self.cpu}"
            raise ValueError(msg)
        if self.memory and not self._is_valid_memory(self.memory):
            msg = f"Invalid memory format: {self.memory}"
            raise ValueError(msg)
        if self.storage and not self._is_valid_memory(self.storage):
            msg = f"Invalid storage format: {self.storage}"
            raise ValueError(msg)

    @staticmethod
    def _is_valid_cpu(cpu: str) -> bool:
        """Check if CPU string is valid (e.g., '2', '500m', '2.5')."""
        return bool(re.match(r"^\d+(\.\d+)?m?$", cpu))

    @staticmethod
    def _is_valid_memory(memory: str) -> bool:
        """Check if memory string is valid (e.g., '16Gi', '32768Mi')."""
        return bool(re.match(r"^\d+(\.\d+)?(Ki|Mi|Gi|Ti|K|M|G|T|B)?$", memory))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.cpu:
            result["cpu"] = self.cpu
        if self.memory:
            result["memory"] = self.memory
        if self.storage:
            result["storage"] = self.storage
        if self.gpu:
            result["gpu"] = self.gpu.to_dict()
        if self.node_affinity:
            result["node_affinity"] = self.node_affinity.to_dict()
        return result

    def has_gpu(self) -> bool:
        """Check if GPU resources are requested."""
        return self.gpu is not None

    def get_gpu_count(self) -> int:
        """Get total number of GPUs requested."""
        return self.gpu.count if self.gpu else 0


def resources(
    cpu: Optional[str] = None,
    memory: Optional[str] = None,
    storage: Optional[str] = None,
    gpu: Optional[GPUConfig] = None,
    node_affinity: Optional[NodeAffinity] = None,
) -> ResourceRequirements:
    """Create a ResourceRequirements object with validation.

    Convenience function for creating resource specifications with cleaner syntax.

    Args:
        cpu: CPU cores (e.g., "2", "500m")
        memory: RAM amount (e.g., "4Gi", "8192Mi")
        storage: Ephemeral storage (e.g., "100Gi")
        gpu: GPU configuration
        node_affinity: Node selection rules

    Returns:
        Validated ResourceRequirements object

    Examples:
        >>> req = resources(cpu="2", memory="4Gi")
        >>> req = resources(cpu="4", memory="16Gi", gpu=GPUConfig(gpu_type="nvidia-v100", count=2))
    """
    return ResourceRequirements(
        cpu=cpu,
        memory=memory,
        storage=storage,
        gpu=gpu,
        node_affinity=node_affinity,
    )
