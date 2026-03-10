"""Test suite for Step auto-registration and Pipeline auto-discovery."""

import unittest

from flowyml.core.step import (
    Step,
    StepRegistry,
    clear_step_registry,
    get_registered_steps,
    step,
)
from flowyml.core.pipeline import Pipeline
from tests.base import BaseTestCase


class TestStepRegistry(unittest.TestCase):
    """Tests for the StepRegistry class itself."""

    def setUp(self):
        self.registry = StepRegistry()

    def test_register_and_get_all(self):
        """Registered steps appear in get_all()."""
        s1 = Step(func=lambda: 1, name="s1", outputs=["a"])
        s2 = Step(func=lambda: 2, name="s2", inputs=["a"], outputs=["b"])
        self.registry.register(s1)
        self.registry.register(s2)

        self.assertEqual(len(self.registry), 2)
        self.assertEqual(len(self.registry.get_all()), 2)

    def test_get_by_name(self):
        """Can look up a step by its name."""
        s = Step(func=lambda: 1, name="lookup_me", outputs=["x"])
        self.registry.register(s)
        self.assertIs(self.registry.get_by_name("lookup_me"), s)
        self.assertIsNone(self.registry.get_by_name("nonexistent"))

    def test_clear(self):
        """clear() removes all registered steps."""
        self.registry.register(Step(func=lambda: 1, name="temp", outputs=["x"]))
        self.assertEqual(len(self.registry), 1)
        self.registry.clear()
        self.assertEqual(len(self.registry), 0)

    def test_duplicate_name_raises(self):
        """Registering two different steps with the same name raises ValueError."""
        s1 = Step(func=lambda: 1, name="dup", outputs=["a"])
        s2 = Step(func=lambda: 2, name="dup", outputs=["b"])
        self.registry.register(s1)
        with self.assertRaises(ValueError):
            self.registry.register(s2)

    def test_same_object_reregister_ok(self):
        """Re-registering the exact same Step instance is idempotent."""
        s = Step(func=lambda: 1, name="same", outputs=["a"])
        self.registry.register(s)
        self.registry.register(s)  # Should not raise
        self.assertEqual(len(self.registry), 1)

    def test_pipeline_scoped_filtering(self):
        """Steps can be filtered by pipeline tag."""
        s1 = Step(func=lambda: 1, name="train", outputs=["a"], tags={"pipeline": "training"})
        s2 = Step(func=lambda: 2, name="serve", outputs=["b"], tags={"pipeline": "serving"})
        s3 = Step(func=lambda: 3, name="util", outputs=["c"])  # No pipeline tag
        self.registry.register(s1)
        self.registry.register(s2)
        self.registry.register(s3)

        training_steps = self.registry.get_all(pipeline="training")
        self.assertEqual(len(training_steps), 2)  # s1 + s3 (unscoped)
        names = {s.name for s in training_steps}
        self.assertIn("train", names)
        self.assertIn("util", names)
        self.assertNotIn("serve", names)

    def test_contains(self):
        """__contains__ works as expected."""
        s = Step(func=lambda: 1, name="check", outputs=["x"])
        self.registry.register(s)
        self.assertIn("check", self.registry)
        self.assertNotIn("missing", self.registry)


class TestStepDecoratorAutoRegistration(unittest.TestCase):
    """Tests for the @step decorator's auto-registration feature."""

    def setUp(self):
        clear_step_registry()

    def tearDown(self):
        clear_step_registry()

    def test_decorator_auto_registers(self):
        """@step automatically registers the function."""

        @step(outputs=["data"])
        def load():
            return [1, 2, 3]

        steps = get_registered_steps()
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].name, "load")

    def test_decorator_register_false(self):
        """@step(register=False) does NOT register the function."""

        @step(outputs=["x"], register=False)
        def helper():
            return 42

        self.assertEqual(len(get_registered_steps()), 0)

    def test_decorator_pipeline_tag(self):
        """@step(pipeline='name') sets the pipeline tag."""

        @step(pipeline="training", outputs=["model"])
        def train():
            return {}

        steps = get_registered_steps()
        self.assertEqual(steps[0].tags.get("pipeline"), "training")

    def test_decorator_pipeline_scoped_query(self):
        """get_registered_steps(pipeline=...) respects scoping."""

        @step(pipeline="training", outputs=["model"])
        def train():
            return {}

        @step(pipeline="serving", outputs=["prediction"])
        def serve():
            return {}

        @step(outputs=["data"])
        def load():
            return []

        training_steps = get_registered_steps(pipeline="training")
        self.assertEqual(len(training_steps), 2)  # train + load (unscoped)

        serving_steps = get_registered_steps(pipeline="serving")
        self.assertEqual(len(serving_steps), 2)  # serve + load (unscoped)

        all_steps = get_registered_steps()
        self.assertEqual(len(all_steps), 3)

    def test_bare_decorator(self):
        """@step without parentheses auto-registers."""

        @step
        def simple():
            return 1

        self.assertEqual(len(get_registered_steps()), 1)

    def test_tags_preserved_with_pipeline(self):
        """Custom tags are preserved when pipeline is also set."""

        @step(pipeline="training", tags={"team": "ml"}, outputs=["x"])
        def tagged_step():
            return 1

        s = get_registered_steps()[0]
        self.assertEqual(s.tags.get("team"), "ml")
        self.assertEqual(s.tags.get("pipeline"), "training")


class TestPipelineAutoDiscover(BaseTestCase):
    """Tests for Pipeline auto_discover, from_steps, and add_steps."""

    def setUp(self):
        super().setUp()
        clear_step_registry()

    def tearDown(self):
        clear_step_registry()
        super().tearDown()

    def test_auto_discover_builds_dag(self):
        """Pipeline(auto_discover=True) discovers steps and builds DAG."""

        @step(outputs=["data"])
        def load():
            return [1, 2, 3]

        @step(inputs=["data"], outputs=["model"])
        def train(data):
            return {"weights": data}

        pipeline = Pipeline("test_auto", auto_discover=True, enable_cache=False)
        pipeline.build()

        self.assertEqual(len(pipeline.steps), 2)
        sorted_names = [n.name for n in pipeline.dag.topological_sort()]
        self.assertEqual(sorted_names.index("load"), 0)
        self.assertEqual(sorted_names.index("train"), 1)

    def test_auto_discover_runs_successfully(self):
        """Pipeline(auto_discover=True) executes the full pipeline."""

        @step(outputs=["data"])
        def load():
            return [10, 20]

        @step(inputs=["data"], outputs=["result"])
        def process(data):
            return sum(data)

        pipeline = Pipeline("test_run_auto", auto_discover=True, enable_cache=False)
        result = pipeline.run()
        self.assertTrue(result.success)

    def test_auto_discover_respects_pipeline_tag(self):
        """auto_discover prefers steps tagged with the pipeline name."""

        @step(pipeline="my_pipeline", outputs=["data"])
        def load():
            return [1, 2, 3]

        @step(pipeline="other_pipeline", outputs=["other"])
        def other_load():
            return [4, 5, 6]

        pipeline = Pipeline("my_pipeline", auto_discover=True, enable_cache=False)
        pipeline.build()

        step_names = {s.name for s in pipeline.steps}
        self.assertIn("load", step_names)
        self.assertNotIn("other_load", step_names)

    def test_manual_add_step_overrides_auto_discover(self):
        """Manually added steps prevent auto-discover from running."""

        @step(outputs=["data"])
        def load():
            return [1]

        @step(inputs=["data"], outputs=["model"])
        def train(data):
            return {"w": data}

        # Only add one step manually
        pipeline = Pipeline("test_override", auto_discover=True, enable_cache=False)
        pipeline.add_step(load)
        pipeline.build()

        # Should only have the manually added step
        self.assertEqual(len(pipeline.steps), 1)
        self.assertEqual(pipeline.steps[0].name, "load")

    def test_from_steps_constructor(self):
        """Pipeline.from_steps() creates a pipeline with provided steps."""

        @step(outputs=["data"], register=False)
        def load():
            return [1, 2]

        @step(inputs=["data"], outputs=["result"], register=False)
        def process(data):
            return sum(data)

        pipeline = Pipeline.from_steps(
            load,
            process,
            name="from_steps_test",
            enable_cache=False,
        )

        self.assertEqual(len(pipeline.steps), 2)
        result = pipeline.run()
        self.assertTrue(result.success)

    def test_add_steps_batch(self):
        """pipeline.add_steps([...]) adds multiple steps at once."""

        @step(outputs=["data"], register=False)
        def load():
            return [1]

        @step(inputs=["data"], outputs=["model"], register=False)
        def train(data):
            return {"ok": True}

        pipeline = Pipeline("batch_test", enable_cache=False)
        pipeline.add_steps([load, train])

        self.assertEqual(len(pipeline.steps), 2)
        result = pipeline.run()
        self.assertTrue(result.success)

    def test_add_steps_chaining(self):
        """add_steps() returns self for chaining."""

        @step(outputs=["x"], register=False)
        def s1():
            return 1

        pipeline = Pipeline("chain_test", enable_cache=False)
        returned = pipeline.add_steps([s1])
        self.assertIs(returned, pipeline)

    def test_from_steps_chaining_with_run(self):
        """from_steps -> run works end-to-end."""

        @step(outputs=["value"], register=False)
        def produce():
            return 42

        result = Pipeline.from_steps(
            produce,
            name="chain_run",
            enable_cache=False,
        ).run()
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
