"""Example training pipeline with Keras integration.

This demonstrates a complete ML pipeline using FlowyML with:
- Data loading and preprocessing
- Model initialization and training with Keras
- Evaluation and metrics tracking
- Conditional deployment based on model performance
"""

import numpy as np
import pandas as pd
import keras
from flowyml import Pipeline, step, context, PipelineScheduler
from flowyml import Dataset, Model, Metrics
from flowyml import If
from flowyml.integrations.keras import FlowymlKerasCallback

# Define context with training hyperparameters
ctx = context(
    learning_rate=0.01,  # Increased for faster convergence
    batch_size=8,  # Smaller batch for small dataset
    epochs=100,  # More epochs for better convergence
    min_mae_threshold=0.2,  # Deployment threshold
    data_path="data.csv",
)


@step(outputs=["data/train", "data/val"])
def load_data(data_path: str):
    """Load and preprocess data from CSV."""
    print("📂 Loading data from CSV...")

    # Load CSV data
    df = pd.read_csv("data.csv")
    print(f"   Loaded {len(df)} samples with columns: {list(df.columns)}")

    # Split features and target
    feature_cols = ["feature_1", "feature_2", "feature_3"]
    target_col = "target"

    # Shuffle the data
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # Split into train/val (80/20)
    train_size = int(len(df) * 0.8)
    train_df = df[:train_size]
    val_df = df[train_size:]

    print(f"   Train samples: {len(train_df)}, Val samples: {len(val_df)}")

    # Create datasets
    train_data = Dataset.create(
        data={
            "features": train_df[feature_cols].to_dict("list"),
            "target": train_df[target_col].tolist(),
        },
        name="train_dataset",
        properties={
            "source": "data.csv",
            "split": "train",
            "samples": len(train_df),
            "feature_columns": feature_cols,
        },
    )

    val_data = Dataset.create(
        data={
            "features": val_df[feature_cols].to_dict("list"),
            "target": val_df[target_col].tolist(),
        },
        name="val_dataset",
        properties={
            "source": "data.csv",
            "split": "val",
            "samples": len(val_df),
            "feature_columns": feature_cols,
        },
    )

    return train_data, val_data


@step(outputs=["model/initialized"])
def init_model():
    """Initialize the Keras model architecture."""
    print("🏗️  Initializing model architecture...")

    # Create a simple regression model for predicting target from features
    inputs = {
        "feature_1": keras.Input(shape=(1,), name="feature_1"),
        "feature_2": keras.Input(shape=(1,), name="feature_2"),
        "feature_3": keras.Input(shape=(1,), name="feature_3"),
    }

    # Concatenate inputs
    concatenated = keras.layers.Concatenate()(list(inputs.values()))

    # Hidden layers
    x = keras.layers.Dense(32, activation="relu")(concatenated)
    x = keras.layers.Dense(16, activation="relu")(x)
    x = keras.layers.Dense(8, activation="relu")(x)

    # Output layer
    outputs = keras.layers.Dense(1, name="prediction")(x)

    model = keras.Model(inputs=inputs, outputs=outputs)
    print(f"   Model created with {model.count_params():,} parameters")

    return Model.create(
        data=model,
        name="initialized_model",
        architecture="mlp",
        framework="keras",
        properties={"parameters": model.count_params()},
    )


@step(
    inputs=["data/train", "data/val", "model/initialized"],
    outputs=["model/trained"],
    execution_group="training",
)
def train_model(train_data, val_data, model_asset, learning_rate, epochs, batch_size):
    """Train the model with FlowyML callback for automatic tracking.

    The FlowymlKerasCallback automatically captures ALL metrics from your
    model.compile() call - no configuration needed! The training history
    is displayed as interactive charts in the FlowyML dashboard.
    """
    print(f"🎯 Training model: lr={learning_rate}, epochs={epochs}, batch_size={batch_size}")

    # Extract the keras model from the asset
    model = model_asset.data

    # Prepare training data as numpy arrays for Keras
    train_x = {k: np.array(v).reshape(-1, 1) for k, v in train_data.data["features"].items()}
    train_y = np.array(train_data.data["target"])

    val_x = {k: np.array(v).reshape(-1, 1) for k, v in val_data.data["features"].items()}
    val_y = np.array(val_data.data["target"])

    # Set up the FlowyML callback - automatically captures ALL compiled metrics!
    flowyml_callback = FlowymlKerasCallback(
        experiment_name="keras-regression-demo",
        project="keras_demo",
    )

    # Early stopping to prevent overfitting
    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
        verbose=1,
    )

    # Compile model with your metrics - ALL will be automatically tracked!
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae", "mape"],  # Add any metrics you want - they're all captured!
    )

    # Train with callbacks
    model.fit(
        train_x,
        train_y,
        validation_data=(val_x, val_y),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[flowyml_callback, early_stop],
        verbose=0,  # Suppress per-epoch output
    )

    # Get training history automatically from callback (fully dynamic!)
    training_history = flowyml_callback.get_training_history()
    actual_epochs = len(training_history.get("epochs", []))

    # Extract final metrics from the training history
    final_loss = training_history.get("train_loss", [0])[-1]
    final_val_loss = training_history.get("val_loss", [0])[-1]
    final_mae = training_history.get("train_mae", [0])[-1]
    final_val_mae = training_history.get("val_mae", [0])[-1]

    print(f"   ✅ Training complete after {actual_epochs} epochs")
    print(f"   📊 Train - Loss: {final_loss:.4f}, MAE: {final_mae:.4f}")
    print(f"   📊 Val   - Loss: {final_val_loss:.4f}, MAE: {final_val_mae:.4f}")

    return Model.create(
        data=model,
        name="trained_model",
        framework="keras",
        properties={
            "learning_rate": learning_rate,
            "epochs_trained": actual_epochs,
            "epochs_requested": epochs,
            "batch_size": batch_size,
            "final_loss": float(final_loss),
            "final_val_loss": float(final_val_loss),
            "final_mae": float(final_mae),
            "final_val_mae": float(final_val_mae),
        },
        # Training history is automatically captured and passed to UI!
        training_history=training_history,
    )


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

    # Prepare validation data
    val_x = {k: np.array(v).reshape(-1, 1) for k, v in val_data.data["features"].items()}
    val_y = np.array(val_data.data["target"])

    # Evaluate
    results = model.evaluate(val_x, val_y, return_dict=True, verbose=0)

    # Make predictions and compute additional metrics
    predictions = model.predict(val_x, verbose=0).flatten()

    # R-squared score
    ss_res = np.sum((val_y - predictions) ** 2)
    ss_tot = np.sum((val_y - np.mean(val_y)) ** 2)
    r2_score = 1 - (ss_res / ss_tot)

    # MAPE (Mean Absolute Percentage Error)
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

    # Pass metrics as keyword arguments so they're stored directly
    return Metrics.create(
        data=metrics,  # This becomes .data attribute
        name="evaluation_metrics",
        tags={"source": "validation_set"},
        properties={"samples": len(val_y), **metrics},  # Also store in properties
    )


@step(inputs=["model/trained"], outputs=["deploy/status"])
def deploy_model(trained_model):
    """Deploy the trained model (placeholder)."""
    print("🚀 Deploying model to production...")
    print(f"   Model: {trained_model.name}")
    print(f"   Framework: {trained_model.framework}")

    # In a real scenario, you would:
    # - Save model to a registry (MLflow, Weights & Biases, etc.)
    # - Deploy to a serving endpoint (TensorFlow Serving, TorchServe, etc.)
    # - Update DNS/routing for the new model version

    return {"status": "deployed", "model_name": trained_model.name}


# Create pipeline
def create_pipeline():
    """Create the training pipeline with conditional deployment."""
    pipeline = Pipeline(
        "keras_training_pipeline",
        context=ctx,
        enable_cache=False,
        project_name="keras_demo",
        version="v1.0.0",
    )

    # Add steps in order
    pipeline.add_step(load_data)
    pipeline.add_step(init_model)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)

    # Add conditional deployment based on MAE threshold
    # Deploy only if MAE is below threshold (good model)
    def check_mae_threshold(ctx):
        """Check if MAE is below threshold."""
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
        name="daily_keras_training",
        pipeline_func=lambda: create_pipeline().run(),
        hour=2,
        minute=0,
        timezone="America/New_York",
    )
    scheduler.start()


if __name__ == "__main__":
    print("=" * 70)
    print("🌊 FlowyML Keras Training Pipeline")
    print("=" * 70)

    pipeline = create_pipeline()
    result = pipeline.run()

    # Print final summary
    print("\n" + "=" * 70)
    if result.success:
        print("✅ Pipeline completed successfully!")

        # Check if model was deployed (look for deploy_model step in results)
        deploy_ran = "deploy_model" in result.step_results
        if deploy_ran:
            print("🚀 Model was deployed to production!")
        else:
            print("ℹ️  Model was not deployed (MAE above threshold)")
    else:
        print("❌ Pipeline failed!")
    print("=" * 70)
