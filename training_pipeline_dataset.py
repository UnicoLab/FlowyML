"""Example training pipeline with TensorFlow Dataset and Keras integration.

This demonstrates a complete ML pipeline using FlowyML with:
- SIMPLIFIED Dataset API with automatic statistics extraction
- TensorFlow tf.data.Dataset for data loading
- Model initialization and training with Keras
- Evaluation and metrics tracking
- Conditional deployment based on model performance
"""

import numpy as np
import tensorflow as tf
import keras
from flowyml import Pipeline, step, context, PipelineScheduler
from flowyml import Dataset, Model, Metrics
from flowyml import If
from flowyml.integrations.keras import FlowymlKerasCallback

# Define context with training hyperparameters
ctx = context(
    learning_rate=0.01,
    batch_size=8,
    epochs=100,
    min_mae_threshold=0.2,
    data_path="data.csv",
)


@step(outputs=["data/train", "data/val"])
def load_data(data_path: str):
    """Load data using tf.data.experimental.make_csv_dataset.

    Note how minimal the code is - Dataset.create() automatically extracts:
    - Number of samples
    - Number of features
    - Feature columns
    - Column statistics (mean, std, min, max, etc.)
    - Framework detection
    """
    print("📂 Loading data using tf.data.experimental.make_csv_dataset...")

    # Define column names
    feature_columns = ["feature_1", "feature_2", "feature_3"]
    label_column = "target"

    # Create TensorFlow dataset from CSV
    full_dataset = tf.data.experimental.make_csv_dataset(
        data_path,
        batch_size=1,
        column_names=["feature_1", "feature_2", "feature_3", "target"],
        label_name=label_column,
        header=True,
        shuffle=True,
        shuffle_seed=42,
        num_epochs=1,
    )

    # Convert to list for splitting
    all_data = list(full_dataset)
    total_samples = len(all_data)

    # Split 80/20
    train_size = int(total_samples * 0.8)
    train_data_list = all_data[:train_size]
    val_data_list = all_data[train_size:]

    print(f"   Loaded {total_samples} samples using tf.data.Dataset")
    print(f"   Train samples: {len(train_data_list)}, Val samples: {len(val_data_list)}")

    # Convert to dict format for training
    def list_to_dict_dataset(data_list):
        features = {col: [] for col in feature_columns}
        targets = []

        for features_batch, label_batch in data_list:
            for col in feature_columns:
                features[col].append(float(features_batch[col].numpy()[0]))
            targets.append(float(label_batch.numpy()[0]))

        return {"features": features, "target": targets}

    train_dict = list_to_dict_dataset(train_data_list)
    val_dict = list_to_dict_dataset(val_data_list)

    # 🎯 SIMPLIFIED API: Just pass the data - stats are extracted automatically!
    # No need to manually specify samples, num_features, feature_columns, etc.
    train_dataset = Dataset.create(
        data=train_dict,
        name="train_tf_dataset",
        source=data_path,  # Additional properties as kwargs
        split="train",
        loader="tf.data.experimental.make_csv_dataset",
    )

    val_dataset = Dataset.create(
        data=val_dict,
        name="val_tf_dataset",
        source=data_path,
        split="validation",
        loader="tf.data.experimental.make_csv_dataset",
    )

    # You can still access auto-extracted stats:
    print(f"   Auto-extracted: {train_dataset.num_samples} samples, {train_dataset.num_features} features")
    print(f"   Feature columns: {train_dataset.feature_columns}")

    return train_dataset, val_dataset


@step(outputs=["model/initialized"])
def init_model():
    """Initialize the Keras model architecture.

    Note how minimal the code is - Model.create() automatically extracts:
    - Framework detection (keras)
    - Parameter count
    - Layer info
    - Architecture name
    """
    print("🏗️  Initializing model architecture...")

    inputs = {
        "feature_1": keras.Input(shape=(1,), name="feature_1"),
        "feature_2": keras.Input(shape=(1,), name="feature_2"),
        "feature_3": keras.Input(shape=(1,), name="feature_3"),
    }

    concatenated = keras.layers.Concatenate()(list(inputs.values()))
    x = keras.layers.Dense(32, activation="relu")(concatenated)
    x = keras.layers.Dense(16, activation="relu")(x)
    x = keras.layers.Dense(8, activation="relu")(x)
    outputs = keras.layers.Dense(1, name="prediction")(x)

    model = keras.Model(inputs=inputs, outputs=outputs)

    # 🎯 CONVENIENCE METHOD: Model.from_keras() for Keras-specific extraction
    # Auto-extracts: framework, parameters, layers, architecture, shapes
    model_asset = Model.from_keras(model, name="initialized_model")

    # Access auto-extracted properties
    print(f"   Auto-extracted: {model_asset.parameters:,} parameters")
    print(f"   Framework: {model_asset.framework}")
    print(f"   Layers: {model_asset.num_layers}, Types: {model_asset.layer_types}")

    return model_asset


@step(
    inputs=["data/train", "data/val", "model/initialized"],
    outputs=["model/trained"],
    execution_group="training",
)
def train_model(train_data, val_data, model_asset, learning_rate, epochs, batch_size):
    """Train the model with FlowyML callback for automatic tracking.

    Note how minimal the code is - Model.create() automatically:
    - Extracts training history from the FlowyML callback
    - Captures optimizer, learning rate, loss function from the compiled model
    - Tracks final metrics from training history
    """
    print(f"🎯 Training model: lr={learning_rate}, epochs={epochs}, batch_size={batch_size}")

    model = model_asset.data

    # Prepare training data
    train_x = {k: np.array(v).reshape(-1, 1) for k, v in train_data.data["features"].items()}
    train_y = np.array(train_data.data["target"])

    val_x = {k: np.array(v).reshape(-1, 1) for k, v in val_data.data["features"].items()}
    val_y = np.array(val_data.data["target"])

    # Set up callbacks
    flowyml_callback = FlowymlKerasCallback(
        experiment_name="tf-dataset-demo",
        project="keras_demo",
    )

    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
        verbose=1,
    )

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae", "mape"],
    )

    model.fit(
        train_x,
        train_y,
        validation_data=(val_x, val_y),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[flowyml_callback, early_stop],
        verbose=0,
    )

    # 🎯 CONVENIENCE METHOD: Model.from_keras() with callback for full extraction
    # Auto-extracts: optimizer, learning_rate, loss, metrics, training_history
    trained_model = Model.from_keras(
        model,
        name="trained_model",
        callback=flowyml_callback,  # Auto-extracts training_history!
        # Additional metadata (auto-merged with extracted properties)
        epochs_requested=epochs,
        batch_size=batch_size,
        data_loader="tf.data.Dataset",
    )

    # Access auto-extracted training info
    training_info = trained_model.get_training_info()
    print(f"   ✅ Training complete after {training_info.get('epochs_trained', '?')} epochs")
    print(f"   📊 Optimizer: {trained_model.optimizer}, LR: {trained_model.learning_rate}")
    print(f"   📊 Final train_loss: {training_info.get('final_train_loss', 0):.4f}")
    print(f"   📊 Final val_loss: {training_info.get('final_val_loss', 0):.4f}")

    return trained_model


@step(
    inputs=["model/trained", "data/val"],
    outputs=["metrics/evaluation"],
    cache=False,
    execution_group="training",
)
def evaluate_model(model_asset, val_data):
    """Evaluate the trained model on validation data."""
    print("📈 Evaluating model on validation set...")

    model = model_asset.data

    val_x = {k: np.array(v).reshape(-1, 1) for k, v in val_data.data["features"].items()}
    val_y = np.array(val_data.data["target"])

    results = model.evaluate(val_x, val_y, return_dict=True, verbose=0)
    predictions = model.predict(val_x, verbose=0).flatten()

    # Compute R² and MAPE
    ss_res = np.sum((val_y - predictions) ** 2)
    ss_tot = np.sum((val_y - np.mean(val_y)) ** 2)
    r2_score = 1 - (ss_res / ss_tot)
    mape = np.mean(np.abs((val_y - predictions) / val_y)) * 100

    metrics = {
        "mse": float(results["loss"]),
        "mae": float(results["mae"]),
        "r2_score": float(r2_score),
        "mape": float(mape),
    }

    print(f"   📊 MSE: {metrics['mse']:.4f}")
    print(f"   📊 MAE: {metrics['mae']:.4f}")
    print(f"   📊 R² Score: {metrics['r2_score']:.4f}")
    print(f"   📊 MAPE: {metrics['mape']:.2f}%")

    return Metrics.create(
        data=metrics,
        name="evaluation_metrics",
        tags={"source": "validation_set"},
        properties={"samples": len(val_y), **metrics},
    )


@step(inputs=["model/trained"], outputs=["deploy/status"])
def deploy_model(trained_model):
    """Deploy the trained model (placeholder)."""
    print("🚀 Deploying model to production...")
    print(f"   Model: {trained_model.name}")
    print(f"   Framework: {trained_model.framework}")

    return {"status": "deployed", "model_name": trained_model.name}


# Create pipeline
def create_pipeline():
    """Create the training pipeline with conditional deployment."""
    pipeline = Pipeline(
        "tf_dataset_pipeline",
        context=ctx,
        enable_cache=False,
        project_name="keras_demo",
        version="v1.0.0",
    )

    pipeline.add_step(load_data)
    pipeline.add_step(init_model)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)

    def check_mae_threshold(ctx):
        metrics_asset = ctx.steps["evaluate_model"].outputs["metrics/evaluation"]
        mae = metrics_asset.properties.get("mae", 1.0)
        threshold = ctx.params.get("min_mae_threshold", 0.2)
        return mae < threshold

    pipeline.add_control_flow(
        If(
            condition=check_mae_threshold,
            then_step=deploy_model,
            else_step=None,
        ),
    )

    return pipeline


# Only run scheduler if explicitly enabled
ENABLE_SCHEDULER = False

if ENABLE_SCHEDULER:
    scheduler = PipelineScheduler()
    scheduler.schedule_daily(
        name="daily_tf_dataset_training",
        pipeline_func=lambda: create_pipeline().run(),
        hour=2,
        minute=0,
        timezone="America/New_York",
    )
    scheduler.start()


if __name__ == "__main__":
    print("=" * 70)
    print("🌊 FlowyML TensorFlow Dataset Training Pipeline")
    print("=" * 70)
    print("📦 Using SIMPLIFIED Dataset API with automatic stats extraction")
    print("=" * 70)

    pipeline = create_pipeline()
    result = pipeline.run()

    print("\n" + "=" * 70)
    if result.success:
        print("✅ Pipeline completed successfully!")

        deploy_ran = "deploy_model" in result.step_results
        if deploy_ran:
            print("🚀 Model was deployed to production!")
        else:
            print("ℹ️  Model was not deployed (MAE above threshold)")
    else:
        print("❌ Pipeline failed!")
    print("=" * 70)
