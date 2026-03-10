"""Tests for build-time type validation."""

import unittest
from flowyml.core.type_validator import TypeValidator, TypeIssue, validate_pipeline
from flowyml.core.graph import DAG, Node
from tests.base import BaseTestCase


class MockStep:
    """Mock step for type validation tests."""

    def __init__(self, name, func=None, inputs=None, outputs=None):
        self.name = name
        self.func = func
        self.inputs = inputs or []
        self.outputs = outputs or []


class TestTypeValidator(BaseTestCase):
    """Test suite for TypeValidator."""

    def setUp(self):
        super().setUp()
        self.validator = TypeValidator()

    def test_compatible_types(self):
        """Compatible types produce no issues."""

        def producer() -> int:
            return 1

        def consumer(x: int) -> None:
            pass

        p = MockStep("producer", func=producer, outputs=["x"])
        c = MockStep("consumer", func=consumer, inputs=["x"])

        issues = self.validator.validate_connection(p, c, "x")
        errors = [i for i in issues if i.level == "error"]
        self.assertEqual(len(errors), 0)

    def test_incompatible_types(self):
        """Incompatible types produce an error."""

        def producer() -> str:
            return "hello"

        def consumer(x: int) -> None:
            pass

        p = MockStep("producer", func=producer, outputs=["x"])
        c = MockStep("consumer", func=consumer, inputs=["x"])

        issues = self.validator.validate_connection(p, c, "x")
        errors = [i for i in issues if i.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("mismatch", errors[0].message.lower())

    def test_subclass_compatible(self):
        """Subclasses are compatible."""

        class Animal:
            pass

        class Dog(Animal):
            pass

        def producer() -> Dog:
            return Dog()

        def consumer(x: Animal) -> None:
            pass

        p = MockStep("producer", func=producer, outputs=["x"])
        c = MockStep("consumer", func=consumer, inputs=["x"])

        issues = self.validator.validate_connection(p, c, "x")
        errors = [i for i in issues if i.level == "error"]
        self.assertEqual(len(errors), 0)

    def test_untyped_no_errors(self):
        """Functions without annotations produce no errors."""

        def producer():
            return 1

        def consumer(x):
            pass

        p = MockStep("producer", func=producer, outputs=["x"])
        c = MockStep("consumer", func=consumer, inputs=["x"])

        issues = self.validator.validate_connection(p, c, "x")
        errors = [i for i in issues if i.level == "error"]
        self.assertEqual(len(errors), 0)

    def test_type_issue_str(self):
        """TypeIssue has a readable string representation."""
        issue = TypeIssue(
            level="error",
            producer_step="train",
            consumer_step="evaluate",
            asset_name="model",
            message="Type mismatch",
            producer_type="Model",
            consumer_type="Dataset",
        )
        text = str(issue)
        self.assertIn("train", text)
        self.assertIn("evaluate", text)
        self.assertIn("model", text)

    def test_validate_pipeline_function(self):
        """validate_pipeline works with DAG and steps."""
        dag = DAG()
        n1 = Node("step1", None, [], ["data"])
        n2 = Node("step2", None, ["data"], ["result"])
        dag.add_node(n1)
        dag.add_node(n2)
        dag.build_edges()

        def s1_func() -> int:
            return 1

        def s2_func(data: int) -> str:
            return str(data)

        steps = [
            MockStep("step1", func=s1_func, outputs=["data"]),
            MockStep("step2", func=s2_func, inputs=["data"]),
        ]

        errors, warnings = validate_pipeline(dag, steps)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
