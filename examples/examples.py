"""Flowy Examples - Comprehensive examples of using the framework."""

# ============================================================================
# Example 1: Basic Pipeline with Context Injection
# ============================================================================


def example_basic_pipeline():
    """Simple pipeline with automatic context injection."""
    from flowyml import Pipeline, step, context

    # Define context
    ctx = context(
        learning_rate=0.001,
        epochs=10,
        batch_size=32,
    )

    # Steps automatically get parameters from context
    @step(outputs=["model/trained"])
    def train_model(learning_rate: float, epochs: int, batch_size: int):
        print(f"Training with lr={learning_rate}, epochs={epochs}, batch={batch_size}")
        # Simulate training
        model = {"weights": "trained", "accuracy": 0.95}
        return model

    @step(inputs=["model/trained"], outputs=["metrics/evaluation"])
    def evaluate_model(trained_model):
        print(f"Evaluating model: {trained_model}")
        metrics = {"accuracy": 0.95, "loss": 0.05}
        return metrics

    # Create and run pipeline
    pipeline = Pipeline("basic_pipeline", context=ctx)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)

    result = pipeline.run(debug=True)
    print("\n" + "=" * 60)
    print(result.summary())
    print("=" * 60)

    return result


# ============================================================================
# Example 2: Asset-Centric Pipeline with Lineage Tracking
# ============================================================================


def example_asset_pipeline():
    """Pipeline demonstrating asset-centric design."""
    from flowyml import Pipeline, step, context
    from flowyml.assets import Dataset, Model, Metrics

    ctx = context(
        data_path="./data/train.csv",
        model_type="neural_network",
        learning_rate=0.001,
    )

    @step(outputs=["data/raw"])
    def load_data(data_path: str):
        print(f"Loading data from {data_path}")
        # Simulate data loading
        raw_data = {"samples": 1000, "features": 50}

        return Dataset.create(
            data=raw_data,
            name="raw_dataset",
            properties={"samples": 1000, "source": data_path},
        )

    @step(inputs=["data/raw"], outputs=["data/processed"])
    def preprocess(raw_dataset: Dataset):
        print(f"Preprocessing {raw_dataset.name}")
        processed_data = {"samples": 1000, "features": 40}

        return Dataset.create(
            data=processed_data,
            name="processed_dataset",
            parent=raw_dataset,  # Lineage tracking!
            properties={"transformations": ["normalize", "pca"]},
        )

    @step(inputs=["data/processed"], outputs=["model/trained", "metrics/training"])
    def train(processed_dataset: Dataset, learning_rate: float, model_type: str):
        print(f"Training {model_type} model")

        # Simulate training
        trained_model = {"type": model_type, "weights": [1, 2, 3]}

        model = Model.create(
            data=trained_model,
            name="trained_model",
            architecture=model_type,
            framework="custom",
            trained_on=processed_dataset,  # Link to training data
        )

        metrics = Metrics.create(
            accuracy=0.95,
            loss=0.05,
            training_time="2m 30s",
        )

        return model, metrics

    # Create and run
    pipeline_instance = Pipeline("asset_pipeline", context=ctx)
    pipeline_instance.add_step(load_data)
    pipeline_instance.add_step(preprocess)
    pipeline_instance.add_step(train)

    result = pipeline_instance.run(debug=True)

    # Access outputs
    model = result["model/trained"]
    metrics = result["metrics/training"]

    print("\n" + "=" * 60)
    print("Model:", model)
    print("Metrics:", metrics)
    print("=" * 60)

    return result


# ============================================================================
# Example 3: Caching Demonstration
# ============================================================================


def example_caching():
    """Demonstrate intelligent caching."""
    from flowyml import Pipeline, step, context
    import time

    ctx = context(data_size=1000, threshold=0.5)

    @step(outputs=["data/loaded"], cache="code_hash")
    def load_data(data_size: int):
        print("Loading data (expensive operation)...")
        time.sleep(1)  # Simulate expensive operation
        return {"size": data_size, "data": list(range(data_size))}

    @step(inputs=["data/loaded"], outputs=["data/filtered"], cache="input_hash")
    def filter_data(loaded_data, threshold: float):
        print("Filtering data...")
        filtered = [x for x in loaded_data["data"] if x > threshold]
        return {"filtered": filtered}

    pipeline = Pipeline("caching_pipeline", context=ctx, enable_cache=True)
    pipeline.add_step(load_data)
    pipeline.add_step(filter_data)

    print("\n" + "=" * 60)
    print("First run (no cache):")
    print("=" * 60)
    result1 = pipeline.run(debug=True)

    print("\n" + "=" * 60)
    print("Second run (should use cache):")
    print("=" * 60)
    result2 = pipeline.run(debug=True)

    # Check cache stats
    print("\n" + "=" * 60)
    print("Cache Statistics:")
    print(pipeline.cache_stats())
    print("=" * 60)

    return result2


# ============================================================================
# Example 4: Experiment Tracking
# ============================================================================


def example_experiment_tracking():
    """Demonstrate experiment tracking."""
    from flowyml import Pipeline, step, context, Experiment

    # Run multiple experiments with different parameters
    experiments_data = []

    for lr in [0.001, 0.01, 0.1]:
        ctx = context(learning_rate=lr, epochs=10)

        @step(outputs=["metrics"])
        def train_and_evaluate(learning_rate: float, epochs: int):
            # Simulate training with different learning rates
            accuracy = 0.8 + (learning_rate * 10)  # Fake relationship
            loss = 0.3 - (learning_rate * 2)

            return {
                "accuracy": min(accuracy, 0.99),
                "loss": max(loss, 0.01),
            }

        pipeline = Pipeline(f"exp_lr_{lr}", context=ctx)
        pipeline.add_step(train_and_evaluate)

        result = pipeline.run()
        experiments_data.append(
            {
                "run_id": result.run_id,
                "lr": lr,
                "metrics": result["metrics"],
            },
        )

    # Create experiment and log runs
    exp = Experiment(
        name="learning_rate_tuning",
        description="Testing different learning rates",
    )

    for data in experiments_data:
        exp.log_run(
            run_id=data["run_id"],
            metrics=data["metrics"],
            parameters={"learning_rate": data["lr"]},
        )

    # Compare runs
    print("\n" + "=" * 60)
    print("Experiment Comparison:")
    comparison = exp.compare_runs()
    for run_id, metrics in comparison["runs"].items():
        print(f"\nRun: {run_id}")
        print(f"  Metrics: {metrics}")

    # Get best run
    best_run = exp.get_best_run(metric="accuracy", maximize=True)
    print(f"\nBest run (by accuracy): {best_run}")
    print("=" * 60)

    return exp


# ============================================================================
# Example 5: Complex Multi-Step Pipeline
# ============================================================================


def example_complex_pipeline():
    """Complex pipeline with multiple branches and assets."""
    from flowyml import Pipeline, step, context, Dataset, Model

    ctx = context(
        data_path="./data",
        train_split=0.8,
        model_architecture="resnet50",
        learning_rate=0.001,
        epochs=20,
    )

    @step(outputs=["data/raw"])
    def load_raw_data(data_path: str):
        print(f"Loading from {data_path}")
        return Dataset.create(
            data={"total_samples": 10000},
            name="raw_data",
        )

    @step(inputs=["data/raw"], outputs=["data/train", "data/test"])
    def split_data(raw_data: Dataset, train_split: float):
        print(f"Splitting data: {train_split} train, {1-train_split} test")

        train_data = Dataset.create(
            data={"samples": 8000},
            name="train_split",
            parent=raw_data,
        )

        test_data = Dataset.create(
            data={"samples": 2000},
            name="test_split",
            parent=raw_data,
        )

        return train_data, test_data

    @step(inputs=["data/train"], outputs=["features/train"])
    def extract_features_train(train_data: Dataset):
        print("Extracting training features")
        return {"features": [1, 2, 3], "labels": [0, 1, 0]}

    @step(inputs=["data/test"], outputs=["features/test"])
    def extract_features_test(test_data: Dataset):
        print("Extracting test features")
        return {"features": [4, 5, 6], "labels": [1, 0, 1]}

    @step(
        inputs=["features/train"],
        outputs=["model/trained"],
        cache="code_hash",
    )
    def train_model(train_features, learning_rate: float, epochs: int, model_architecture: str):
        print(f"Training {model_architecture} for {epochs} epochs")

        return Model.create(
            data={"weights": "trained"},
            name="trained_model",
            architecture=model_architecture,
        )

    @step(inputs=["model/trained", "features/test"], outputs=["metrics/final"])
    def evaluate_final(trained_model: Model, test_features):
        print("Final evaluation")
        return {
            "accuracy": 0.95,
            "precision": 0.93,
            "recall": 0.94,
        }

    # Build pipeline
    pipeline = Pipeline("complex_pipeline", context=ctx)
    pipeline.add_step(load_raw_data)
    pipeline.add_step(split_data)
    pipeline.add_step(extract_features_train)
    pipeline.add_step(extract_features_test)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_final)

    # Visualize before running
    print("\n" + "=" * 60)
    print("Pipeline Structure:")
    print(pipeline.visualize())
    print("=" * 60)

    # Run
    result = pipeline.run(debug=True)

    print("\n" + "=" * 60)
    print(result.summary())
    print("=" * 60)

    return result


# ============================================================================
# Run all examples
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🌊 " * 30)
    print("FLOWY EXAMPLES")
    print("🌊 " * 30 + "\n")

    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Pipeline with Context Injection")
    print("=" * 60)
    example_basic_pipeline()

    print("\n\n" + "=" * 60)
    print("EXAMPLE 2: Asset-Centric Pipeline with Lineage")
    print("=" * 60)
    example_asset_pipeline()

    print("\n\n" + "=" * 60)
    print("EXAMPLE 3: Caching Demonstration")
    print("=" * 60)
    example_caching()

    print("\n\n" + "=" * 60)
    print("EXAMPLE 4: Experiment Tracking")
    print("=" * 60)
    example_experiment_tracking()

    print("\n\n" + "=" * 60)
    print("EXAMPLE 5: Complex Multi-Step Pipeline")
    print("=" * 60)
    example_complex_pipeline()

    print("\n\n" + "🌊 " * 30)
    print("ALL EXAMPLES COMPLETED!")
    print("🌊 " * 30 + "\n")
