from flowyml.stacks.local import LocalStack
from tests.base import BaseTestCase


class TestStacks(BaseTestCase):
    """Test suite for stack functionality."""

    def test_local_stack_creation(self):
        """Test creating a local stack."""
        stack = LocalStack(
            name="test_stack",
            artifact_path=f"{self.test_dir}/artifacts",
            metadata_path=f"{self.test_dir}/metadata.db",
        )
        self.assertEqual(stack.name, "test_stack")

    def test_stack_has_name(self):
        """Test that stack has a name attribute."""
        stack = LocalStack(
            name="my_stack",
            artifact_path=f"{self.test_dir}/artifacts2",
            metadata_path=f"{self.test_dir}/metadata2.db",
        )
        self.assertTrue(hasattr(stack, "name"))
        self.assertEqual(stack.name, "my_stack")


if __name__ == "__main__":
    unittest.main()
