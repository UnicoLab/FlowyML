import pytest
from unittest.mock import MagicMock
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
    with pytest.raises(ValueError, match="Remote execution requires a specific 'image'"):
        basic_stack.prepare_docker_image(config, pipeline_name="test")


def test_prepare_image_no_registry_explicit_image(basic_stack):
    """Test that explicit image is returned even without registry."""
    config = DockerConfig(image="python:3.9")
    result = basic_stack.prepare_docker_image(config, pipeline_name="test")
    assert result == "python:3.9"


def test_prepare_image_with_registry_no_image(remote_stack, mocker):
    """Test that image URI is constructed when registry allows building."""
    # Mock builder to avoid actual build in unit test
    mock_builder = mocker.patch("flowyml.core.image_builder.DockerImageBuilder")
    mock_instance = mock_builder.return_value
    # When build_image is called, it should just return the tag passed to it
    mock_instance.build_image.side_effect = lambda config, tag: tag

    # Mock registry push to verify it's called
    remote_stack.container_registry.push_image = mocker.Mock(return_value="pushed_uri")

    config = DockerConfig(image=None)
    # This should trigger the 'build' logic (mocked)
    # With project_name
    result = remote_stack.prepare_docker_image(config, pipeline_name="mypipe", project_name="myproj")

    # Expect: registry_uri/project-pipeline:latest
    # safe_name of myproj-mypipe is myproj-mypipe
    expected = "gcr.io/my-project/myproj-mypipe:latest"

    # BUT wait, the function returns the RESULT of push_image, not the built tag
    # In our mock above, push_image returns "pushed_uri"
    assert result == "pushed_uri"

    # Verify build and push were called with expected tag
    mock_instance.build_image.assert_called_once()
    built_tag = mock_instance.build_image.call_args[0][1]
    assert built_tag == expected

    remote_stack.container_registry.push_image.assert_called_once_with(expected)


def test_prepare_image_with_registry_explicit_image(remote_stack, mocker):
    """Test that explicit image takes precedence over registry build."""
    # Mock builder to ensure it is NOT called
    mock_builder = mocker.patch("flowyml.core.image_builder.DockerImageBuilder")

    config = DockerConfig(image="my-custom-image:v1")
    result = remote_stack.prepare_docker_image(config, pipeline_name="test")
    assert result == "my-custom-image:v1"

    # Builder should not be called
    mock_builder.assert_not_called()
