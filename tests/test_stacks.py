"""Test suite for stack functionality."""

import unittest
from flowyml.stacks.base import Stack
from flowyml.stacks.local import LocalStack


class TestStacks(unittest.TestCase):
    """Test suite for stack functionality."""

    def test_local_stack_creation(self):
        """Test creating a local stack."""
        stack = LocalStack(name="test_stack")
        self.assertEqual(stack.name, "test_stack")

    def test_stack_has_name(self):
        """Test that stack has a name attribute."""
        stack = LocalStack(name="my_stack")
        self.assertTrue(hasattr(stack, "name"))
        self.assertEqual(stack.name, "my_stack")


if __name__ == "__main__":
    unittest.main()
