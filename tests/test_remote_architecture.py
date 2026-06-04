import pytest
from flowyml.stacks.base import Stack
from flowyml.stacks.components import DockerConfig, ContainerRegistry


class MockExecutor:
    pass


class MockArtifactStore:
    pass


class MockMetadataStore:
    pass


class MockRegistry(ContainerRegistry):
    def __init__(self, uri):
        self.uri = uri
        self.registry_uri = uri  # Add alias for compatibility with GCR-style access
        super().__init__("mock_registry")

    @property
    def component_type(self):
        from flowyml.stacks.components import ComponentType

        return ComponentType.CONTAINER_REGISTRY

    def validate(self):
        return True

    def to_dict(self):
        return {"name": self.name, "uri": self.uri}

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        return f"{self.uri}/{image_name}:{tag}"

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        pass

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        # Simplified for testing logic in base.py which assumes a certain format or uses base logic
        return f"{self.uri}/{image_name}:{tag}"


@pytest.fixture
def basic_stack():
    return Stack(
        name="local_stack",
        executor=MockExecutor(),
        artifact_store=MockArtifactStore(),
        metadata_store=MockMetadataStore(),
    )


@pytest.fixture
def remote_stack():
    return Stack(
        name="remote_stack",
        executor=MockExecutor(),
        artifact_store=MockArtifactStore(),
        metadata_store=MockMetadataStore(),
        container_registry=MockRegistry("gcr.io/my-project"),
    )


def test_prepare_image_no_registry_no_image(basic_stack):
    """Test that error is raised if no registry and no image provided."""
    config = DockerConfig(image=None)
    with pytest.raises(ValueError, match="Remote execution requires a container registry"):
        basic_stack.prepare_docker_image(config, pipeline_name="test")


def test_prepare_image_no_registry_explicit_image(basic_stack):
    """Test that explicit image is returned even without registry."""
    config = DockerConfig(image="python:3.9")
    result = basic_stack.prepare_docker_image(config, pipeline_name="test")
    assert result == "python:3.9"


def test_prepare_image_with_registry_no_image(remote_stack):
    """Test that image URI is constructed when registry allows building."""
    from unittest.mock import patch, MagicMock

    with patch("flowyml.core.image_builder.DockerImageBuilder") as mock_builder:
        mock_instance = mock_builder.return_value

        # generate_tag returns a predictable tag
        expected_tag = "gcr.io/my-project/myproj-mypipe:latest"
        mock_instance.generate_tag.return_value = expected_tag

        # build_image returns the tag it was given
        mock_instance.build_image.return_value = expected_tag

        # push_image returns a pushed URI
        mock_instance.push_image.return_value = "pushed_uri"

        config = DockerConfig(image=None)
        result = remote_stack.prepare_docker_image(
            config,
            pipeline_name="mypipe",
            project_name="myproj",
        )

        # The function returns the result of builder.push_image()
        assert result == "pushed_uri"

        # Verify build and push were called
        mock_instance.generate_tag.assert_called_once()
        mock_instance.build_image.assert_called_once()
        mock_instance.push_image.assert_called_once()


def test_prepare_image_with_registry_explicit_image(remote_stack):
    """Test that explicit image takes precedence over registry build."""
    from unittest.mock import patch

    with patch("flowyml.core.image_builder.DockerImageBuilder") as mock_builder:
        config = DockerConfig(image="my-custom-image:v1")
        result = remote_stack.prepare_docker_image(config, pipeline_name="test")
        assert result == "my-custom-image:v1"

        # Builder should not be instantiated at all (early return before import)
        mock_builder.assert_not_called()
