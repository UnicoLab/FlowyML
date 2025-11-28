"""Tests for resource specification."""

import pytest
from uniflow.core.resources import ResourceRequirements, GPUConfig, NodeAffinity, resources


class TestResourceRequirements:
    """Test ResourceRequirements validation and creation."""

    def test_simple_cpu_memory(self):
        """Test simple CPU and memory specification."""
        req = ResourceRequirements(cpu="2", memory="4Gi")
        assert req.cpu == "2"
        assert req.memory == "4Gi"
        assert req.gpu is None

    def test_with_gpu(self):
        """Test with GPU configuration."""
        gpu = GPUConfig(gpu_type="nvidia-tesla-v100", count=2, memory="16Gi")
        req = ResourceRequirements(cpu="4", memory="16Gi", gpu=gpu)

        assert req.has_gpu()
        assert req.get_gpu_count() == 2

    def test_cpu_formats(self):
        """Test various CPU format validations."""
        # Valid formats
        ResourceRequirements(cpu="1")
        ResourceRequirements(cpu="2.5")
        ResourceRequirements(cpu="500m")
        ResourceRequirements(cpu="1000m")

    def test_memory_formats(self):
        """Test various memory format validations."""
        # Valid formats
        ResourceRequirements(memory="1Gi")
        ResourceRequirements(memory="1024Mi")
        ResourceRequirements(memory="1G")
        ResourceRequirements(memory="1024M")
        ResourceRequirements(memory="1073741824")  # Bytes

    def test_invalid_cpu_format(self):
        """Test that invalid CPU format raises error."""
        with pytest.raises(ValueError, match="Invalid CPU format"):
            ResourceRequirements(cpu="invalid")

        with pytest.raises(ValueError, match="Invalid CPU format"):
            ResourceRequirements(cpu="2.5.5")

    def test_invalid_memory_format(self):
        """Test that invalid memory format raises error."""
        with pytest.raises(ValueError, match="Invalid memory format"):
            ResourceRequirements(memory="invalid")

        with pytest.raises(ValueError, match="Invalid memory format"):
            ResourceRequirements(memory="16Zb")  # Invalid unit

    def test_to_dict(self):
        """Test dictionary conversion."""
        gpu = GPUConfig(gpu_type="nvidia-v100", count=1)
        req = ResourceRequirements(
            cpu="2",
            memory="4Gi",
            storage="100Gi",
            gpu=gpu,
        )

        result = req.to_dict()
        assert result["cpu"] == "2"
        assert result["memory"] == "4Gi"
        assert result["storage"] == "100Gi"
        assert result["gpu"]["type"] == "nvidia-v100"
        assert result["gpu"]["count"] == 1


class TestGPUConfig:
    """Test GPU configuration."""

    def test_basic_gpu(self):
        """Test basic GPU configuration."""
        gpu = GPUConfig(gpu_type="nvidia-tesla-t4", count=1)
        assert gpu.gpu_type == "nvidia-tesla-t4"
        assert gpu.count == 1
        assert gpu.memory is None

    def test_gpu_with_memory(self):
        """Test GPU with memory specification."""
        gpu = GPUConfig(gpu_type="nvidia-a100", count=4, memory="80Gi")
        assert gpu.count == 4
        assert gpu.memory == "80Gi"

    def test_invalid_gpu_count(self):
        """Test that invalid GPU count raises error."""
        with pytest.raises(ValueError, match="GPU count must be >= 1"):
            GPUConfig(gpu_type="nvidia-v100", count=0)

        with pytest.raises(ValueError, match="GPU count must be >= 1"):
            GPUConfig(gpu_type="nvidia-v100", count=-1)

    def test_invalid_gpu_memory(self):
        """Test that invalid GPU memory format raises error."""
        with pytest.raises(ValueError, match="Invalid GPU memory format"):
            GPUConfig(gpu_type="nvidia-v100", count=1, memory="invalid")


class TestNodeAffinity:
    """Test node affinity specification."""

    def test_basic_affinity(self):
        """Test basic node affinity."""
        affinity = NodeAffinity(
            required={"gpu": "true"},
            preferred={"zone": "us-central1-a"},
        )
        assert affinity.required["gpu"] == "true"
        assert affinity.preferred["zone"] == "us-central1-a"

    def test_with_tolerations(self):
        """Test affinity with tolerations."""
        affinity = NodeAffinity(
            required={"gpu": "true"},
            tolerations=[
                {"key": "nvidia.com/gpu", "operator": "Exists"},
                {"key": "dedicated", "value": "gpu", "effect": "NoSchedule"},
            ],
        )
        assert len(affinity.tolerations) == 2
        assert affinity.tolerations[0]["key"] == "nvidia.com/gpu"


class TestResourcesHelper:
    """Test resources() helper function."""

    def test_resources_helper(self):
        """Test that resources() helper creates ResourceRequirements."""
        req = resources(cpu="2", memory="4Gi")
        assert isinstance(req, ResourceRequirements)
        assert req.cpu == "2"
        assert req.memory == "4Gi"

    def test_resources_with_all_params(self):
        """Test resources() with all parameters."""
        gpu = GPUConfig(gpu_type="nvidia-v100", count=2)
        affinity = NodeAffinity(required={"gpu": "true"})

        req = resources(
            cpu="4",
            memory="16Gi",
            storage="100Gi",
            gpu=gpu,
            node_affinity=affinity,
        )

        assert req.cpu == "4"
        assert req.has_gpu()
        assert req.node_affinity is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
