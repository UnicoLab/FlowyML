"""Resource specification for pipeline steps.

This module provides orchestrator-agnostic resource specification for flowyml pipeline steps,
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
        return bool(re.match(r"^\d+(\.\d+)?(Ki|Mi|Gi|Ti|KB|MB|GB|TB|K|M|G|T)$", memory))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.gpu_type,
            "count": self.count,
            "memory": self.memory,
        }

    def merge_with(self, other: "GPUConfig") -> "GPUConfig":
        """Merge with another GPU config, taking max count and best GPU type.

        Args:
            other: Another GPUConfig to merge with

        Returns:
            New GPUConfig with merged specifications
        """
        # Prefer A100 > V100 > T4 > other, or just take first if unknown
        gpu_hierarchy = ["nvidia-a100", "nvidia-tesla-a100", "nvidia-tesla-v100", "nvidia-v100", "nvidia-t4"]

        best_type = self.gpu_type
        for gpu_type in gpu_hierarchy:
            if gpu_type in self.gpu_type.lower():
                self_rank = gpu_hierarchy.index(gpu_type)
                break
        else:
            self_rank = 999

        for gpu_type in gpu_hierarchy:
            if gpu_type in other.gpu_type.lower():
                other_rank = gpu_hierarchy.index(gpu_type)
                break
        else:
            other_rank = 999

        if other_rank < self_rank:
            best_type = other.gpu_type

        # Take max count
        max_count = max(self.count, other.count)

        # Take max memory if both specified
        max_memory = None
        if self.memory and other.memory:
            max_memory = self._compare_memory(self.memory, other.memory)
        elif self.memory:
            max_memory = self.memory
        elif other.memory:
            max_memory = other.memory

        return GPUConfig(
            gpu_type=best_type,
            count=max_count,
            memory=max_memory,
        )

    @staticmethod
    def _compare_memory(mem1: str, mem2: str) -> str:
        """Return the larger memory specification."""

        # Simple comparison - convert to bytes and compare
        def to_bytes(mem: str) -> int:
            import re

            match = re.match(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|KB|MB|GB|TB|K|M|G|T)?$", mem)
            if not match:
                return 0
            value, unit = float(match.group(1)), match.group(2) or ""
            multipliers = {
                "Ki": 1024,
                "Mi": 1024**2,
                "Gi": 1024**3,
                "Ti": 1024**4,
                "KB": 1000,
                "MB": 1000**2,
                "GB": 1000**3,
                "TB": 1000**4,
                "K": 1000,
                "M": 1000**2,
                "G": 1000**3,
                "T": 1000**4,
                "": 1,
            }
            return int(value * multipliers.get(unit, 1))

        return mem1 if to_bytes(mem1) >= to_bytes(mem2) else mem2


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

    def merge_with(self, other: "NodeAffinity") -> "NodeAffinity":
        """Merge with another node affinity, combining constraints.

        Args:
            other: Another NodeAffinity to merge with

        Returns:
            New NodeAffinity with merged constraints
        """
        # Merge required labels (intersection - both must be satisfied)
        merged_required = {**self.required, **other.required}

        # Merge preferred labels (union - prefer either)
        merged_preferred = {**self.preferred, **other.preferred}

        # Merge tolerations (union - tolerate all)
        merged_tolerations = list(self.tolerations)
        for tol in other.tolerations:
            if tol not in merged_tolerations:
                merged_tolerations.append(tol)

        return NodeAffinity(
            required=merged_required,
            preferred=merged_preferred,
            tolerations=merged_tolerations,
        )


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
        """Check if memory string is valid (e.g., '16Gi', '32768Mi', '4GB')."""
        return bool(re.match(r"^\d+(\.\d+)?(Ki|Mi|Gi|Ti|KB|MB|GB|TB|K|M|G|T|B)?$", memory))

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

    def __getitem__(self, key: str) -> Any:
        """Provide dict-style access for backwards compatibility."""
        if not hasattr(self, key):
            raise KeyError(key)
        value = getattr(self, key)
        if key == "gpu" and isinstance(value, GPUConfig):
            return value.count
        return value

    def get_gpu_count(self) -> int:
        """Get total number of GPUs requested."""
        return self.gpu.count if self.gpu else 0

    @staticmethod
    def _compare_cpu(cpu1: str, cpu2: str) -> str:
        """Return the larger CPU requirement.

        Args:
            cpu1: First CPU specification (e.g., "2", "500m")
            cpu2: Second CPU specification

        Returns:
            The larger CPU specification
        """

        def to_millicores(cpu: str) -> int:
            if cpu.endswith("m"):
                return int(cpu[:-1])
            return int(float(cpu) * 1000)

        return cpu1 if to_millicores(cpu1) >= to_millicores(cpu2) else cpu2

    @staticmethod
    def _compare_memory(mem1: str, mem2: str) -> str:
        """Return the larger memory requirement.

        Args:
            mem1: First memory specification (e.g., "4Gi", "8192Mi")
            mem2: Second memory specification

        Returns:
            The larger memory specification (in original format)
        """
        import re

        def to_bytes(mem: str) -> int:
            match = re.match(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|KB|MB|GB|TB|K|M|G|T|B)?$", mem)
            if not match:
                return 0
            value, unit = float(match.group(1)), match.group(2) or "B"
            multipliers = {
                "Ki": 1024,
                "Mi": 1024**2,
                "Gi": 1024**3,
                "Ti": 1024**4,
                "KB": 1000,
                "MB": 1000**2,
                "GB": 1000**3,
                "TB": 1000**4,
                "K": 1000,
                "M": 1000**2,
                "G": 1000**3,
                "T": 1000**4,
                "B": 1,
                "": 1,
            }
            return int(value * multipliers.get(unit, 1))

        bytes1 = to_bytes(mem1)
        bytes2 = to_bytes(mem2)

        # Return whichever is larger, but keep original format
        return mem1 if bytes1 >= bytes2 else mem2

    def merge_with(self, other: "ResourceRequirements") -> "ResourceRequirements":
        """Merge with another ResourceRequirements, taking maximum of each.

        This is used when grouping steps to aggregate their resource needs.
        Strategy:
        - CPU: Take maximum
        - Memory: Take maximum
        - Storage: Take maximum
        - GPU: Merge configs (max count, best type)
        - Node affinity: Merge constraints

        Args:
            other: Another ResourceRequirements to merge with

        Returns:
            New ResourceRequirements with merged specifications
        """
        # Merge CPU
        merged_cpu = None
        if self.cpu and other.cpu:
            merged_cpu = self._compare_cpu(self.cpu, other.cpu)
        elif self.cpu:
            merged_cpu = self.cpu
        elif other.cpu:
            merged_cpu = other.cpu

        # Merge memory
        merged_memory = None
        if self.memory and other.memory:
            merged_memory = self._compare_memory(self.memory, other.memory)
        elif self.memory:
            merged_memory = self.memory
        elif other.memory:
            merged_memory = other.memory

        # Merge storage
        merged_storage = None
        if self.storage and other.storage:
            merged_storage = self._compare_memory(self.storage, other.storage)
        elif self.storage:
            merged_storage = self.storage
        elif other.storage:
            merged_storage = other.storage

        # Merge GPU
        merged_gpu = None
        if self.gpu and other.gpu:
            merged_gpu = self.gpu.merge_with(other.gpu)
        elif self.gpu:
            merged_gpu = self.gpu
        elif other.gpu:
            merged_gpu = other.gpu

        # Merge node affinity
        merged_affinity = None
        if self.node_affinity and other.node_affinity:
            merged_affinity = self.node_affinity.merge_with(other.node_affinity)
        elif self.node_affinity:
            merged_affinity = self.node_affinity
        elif other.node_affinity:
            merged_affinity = other.node_affinity

        return ResourceRequirements(
            cpu=merged_cpu,
            memory=merged_memory,
            storage=merged_storage,
            gpu=merged_gpu,
            node_affinity=merged_affinity,
        )


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
