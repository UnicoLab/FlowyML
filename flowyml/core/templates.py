"""Pre-built pipeline templates."""

from typing import Any
from flowyml.core.pipeline import Pipeline


class PipelineTemplate:
    """Base class for pipeline templates."""

    @staticmethod
    def create(name: str, **kwargs) -> Pipeline:
        """Create a pipeline from this template."""
        raise NotImplementedError()


class MLTrainingTemplate(PipelineTemplate):
    """Standard ML training pipeline template.

    Steps:
    1. Load data
    2. Preprocess
    3. Train model
    4. Evaluate
    5. Save model
    """

    @staticmethod
    def create(
        name: str = "ml_training",
        data_loader: Any | None = None,
        preprocessor: Any | None = None,
        trainer: Any | None = None,
        evaluator: Any | None = None,
        model_saver: Any | None = None,
        **ctx_params,
    ) -> Pipeline:
        """Create an ML training pipeline.

        Args:
            name: Pipeline name
            data_loader: Function to load data
            preprocessor: Function to preprocess data
            trainer: Function to train model
            evaluator: Function to evaluate model
            model_saver: Function to save model
            **ctx_params: Additional context parameters
        """
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.step import step
        from flowyml.core.context import context

        ctx = context(**ctx_params)
        pipeline = Pipeline(name, context=ctx)

        if data_loader:
            load_step = step(name="load_data", outputs=["dataset"])(data_loader)
            pipeline.add_step(load_step)

        if preprocessor:
            preprocess_step = step(
                name="preprocess",
                inputs=["dataset"],
                outputs=["processed_data"],
            )(preprocessor)
            pipeline.add_step(preprocess_step)

        if trainer:
            train_step = step(
                name="train",
                inputs=["processed_data"],
                outputs=["model"],
            )(trainer)
            pipeline.add_step(train_step)

        if evaluator:
            eval_step = step(
                name="evaluate",
                inputs=["model", "processed_data"],
                outputs=["metrics"],
            )(evaluator)
            pipeline.add_step(eval_step)

        if model_saver:
            save_step = step(
                name="save_model",
                inputs=["model"],
            )(model_saver)
            pipeline.add_step(save_step)

        return pipeline


class DataPipelineTemplate(PipelineTemplate):
    """Data processing pipeline template.

    Steps:
    1. Extract
    2. Transform
    3. Load (ETL)
    """

    @staticmethod
    def create(
        name: str = "etl_pipeline",
        extractor: Any | None = None,
        transformer: Any | None = None,
        loader: Any | None = None,
        **ctx_params,
    ) -> Pipeline:
        """Create an ETL pipeline."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.step import step
        from flowyml.core.context import context

        ctx = context(**ctx_params)
        pipeline = Pipeline(name, context=ctx)

        if extractor:
            extract_step = step(name="extract", outputs=["raw_data"])(extractor)
            pipeline.add_step(extract_step)

        if transformer:
            transform_step = step(
                name="transform",
                inputs=["raw_data"],
                outputs=["transformed_data"],
            )(transformer)
            pipeline.add_step(transform_step)

        if loader:
            load_step = step(
                name="load",
                inputs=["transformed_data"],
            )(loader)
            pipeline.add_step(load_step)

        return pipeline


class ABTestPipelineTemplate(PipelineTemplate):
    """A/B testing pipeline template.

    Runs multiple model variants and compares results.
    """

    @staticmethod
    def create(
        name: str = "ab_test",
        data_loader: Any | None = None,
        model_a_trainer: Any | None = None,
        model_b_trainer: Any | None = None,
        comparator: Any | None = None,
        **ctx_params,
    ) -> Pipeline:
        """Create an A/B test pipeline."""
        from flowyml.core.pipeline import Pipeline
        from flowyml.core.step import step
        from flowyml.core.context import context

        ctx = context(**ctx_params)
        pipeline = Pipeline(name, context=ctx)

        if data_loader:
            load_step = step(name="load_data", outputs=["dataset"])(data_loader)
            pipeline.add_step(load_step)

        if model_a_trainer:
            train_a = step(
                name="train_model_a",
                inputs=["dataset"],
                outputs=["model_a", "metrics_a"],
            )(model_a_trainer)
            pipeline.add_step(train_a)

        if model_b_trainer:
            train_b = step(
                name="train_model_b",
                inputs=["dataset"],
                outputs=["model_b", "metrics_b"],
            )(model_b_trainer)
            pipeline.add_step(train_b)

        if comparator:
            compare = step(
                name="compare",
                inputs=["metrics_a", "metrics_b"],
                outputs=["winner"],
            )(comparator)
            pipeline.add_step(compare)

        return pipeline


# Template registry
TEMPLATES = {
    "ml_training": MLTrainingTemplate,
    "etl": DataPipelineTemplate,
    "data_pipeline": DataPipelineTemplate,
    "ab_test": ABTestPipelineTemplate,
}


def create_from_template(template_name: str, **kwargs) -> Pipeline:
    """Create a pipeline from a template.

    Args:
        template_name: Name of the template
        **kwargs: Template-specific arguments

    Returns:
        Configured pipeline

    Examples:
        >>> pipeline = create_from_template("ml_training", data_loader=load_data, trainer=train_model)
    """
    if template_name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

    template_class = TEMPLATES[template_name]
    return template_class.create(**kwargs)


def list_templates() -> list[str]:
    """List available templates."""
    return list(TEMPLATES.keys())
