# Tutorial: Building an Extensible ML Pipeline

This step-by-step tutorial shows you how to build a production-ready ML pipeline with custom components, from development to deployment.

## What You'll Build

- Production ML pipeline with TensorFlow
- Custom MinIO artifact store component
- Multi-environment configuration
- Automated CI/CD deployment

## Prerequisites

- Python 3.8+
- Docker installed
- (Optional) GCP account for cloud deployment
- (Optional) MinIO server for custom storage

## Step 1: Project Setup

### Install UniFlow

```bash
# Basic installation
pip install uniflow

# With ML and GCP support
pip install uniflow[tensorflow,gcp]
```

### Initialize Project

```bash
# Create project directory
mkdir ml-pipeline-tutorial
cd ml-pipeline-tutorial

# Initialize UniFlow
uniflow init

# Should create uniflow.yaml
```

## Step 2: Write Your Pipeline

Create `training_pipeline.py`:

```python
"""Clean ML training pipeline - infrastructure agnostic."""

from uniflow import Pipeline, step, Dataset, Model, Metrics
import tensorflow as tf
import pandas as pd
import numpy as np


@step
def load_data(data_path: str):
    """Load and prepare training data."""
    # In production, load from data_path
    # For tutorial, generate synthetic data
    np.random.seed(42)
    X = np.random.randn(1000, 20)
    y = (X[: 0] + X[:, 1] > 0).astype(int)
    
    df = pd.DataFrame(X)
    df['label'] = y
    
    return Dataset.create(
        data=df,
        name="training_data",
        rows=len(df),
        cols=len(df.columns),
        source=data_path
    )


@step
def split_data(dataset: Dataset):
    """Split into train and validation sets."""
    df = dataset.data
    
    # 80-20 split
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    return {
        "train": Dataset.create(
            data=train_df,
            name="train_data",
            parent=dataset,
            split="train"
        ),
        "val": Dataset.create(
            data=val_df,
            name="val_data",
            parent=dataset,
            split="validation"
        )
    }


@step
def train_model(datasets: dict, epochs: int = 10):
    """Train TensorFlow model."""
    train_data = datasets["train"].data
    
    # Prepare data
    X_train = train_data.drop('label', axis=1).values
    y_train = train_data['label'].values
    
    # Build model
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(20,)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    # Train
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=32,
        validation_split=0.2,
        verbose=1
    )
    
    return Model.create(
        data=model,
        name="binary_classifier",
        framework="tensorflow",
        parent=datasets["train"]
    )


@step
def evaluate_model(model: Model, datasets: dict):
    """Evaluate on validation set."""
    val_data = datasets["val"].data
    
    X_val = val_data.drop('label', axis=1).values
    y_val = val_data['label'].values
    
    # Evaluate
    tf_model = model.data
    loss, accuracy = tf_model.evaluate(X_val, y_val, verbose=0)
    
    return Metrics.create(
        loss=float(loss),
        accuracy=float(accuracy),
        name="validation_metrics",
        parent=model
    )


# Create pipeline - NO infrastructure code!
pipeline = Pipeline("ml_training")
pipeline.add_step(load_data)
pipeline.add_step(split_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)


if __name__ == "__main__":
    result = pipeline.run(
        context={
            "data_path": "data/train.csv",
            "epochs": 10
        }
    )
    print(f"✅ Training complete: {result}")
```

## Step 3: Test Locally

### Run with default (local) stack

```bash
uniflow run training_pipeline.py
```

Output:
```
🚀 Running pipeline: training_pipeline.py
📦 Stack: local
⚙️  Loading pipeline...
🏃 Running pipeline...

Epoch 1/10
...
✅ Pipeline completed successfully!
```

### Verify artifacts

```bash
# Check artifact storage
ls -R .uniflow/artifacts/

# Check metadata
sqlite3 .uniflow/metadata.db "SELECT * FROM runs;"
```

## Step 4: Create Custom Component

For this tutorial, we'll create a MinIO artifact store.

Create `custom_components/minio_store.py`:

```python
"""Custom MinIO artifact store for tutorial."""

from uniflow.stacks.components import ArtifactStore
from uniflow.stacks.plugins import register_component
from typing import Any
import pickle
import io


@register_component
class MinIOArtifactStore(ArtifactStore):
    """MinIO object storage integration."""
    
    def __init__(
        self,
        name: str = "minio",
        endpoint: str = "localhost:9000",
        bucket: str = "ml-artifacts",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        secure: bool = False,
    ):
        super().__init__(name)
        self.endpoint = endpoint
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from minio import Minio
            
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            
            # Create bucket if needed
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
        
        return self._client
    
    def validate(self) -> bool:
        try:
            from minio import Minio
            _ = self.client  # Test connection
            return True
        except ImportError:
            raise ImportError("pip install minio")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to MinIO: {e}")
    
    def save(self, artifact: Any, path: str) -> str:
        data = pickle.dumps(artifact)
        stream = io.BytesIO(data)
        
        self.client.put_object(
            self.bucket,
            path,
            stream,
            length=len(data)
        )
        
        return f"s3://{self.bucket}/{path}"
    
    def load(self, path: str) -> Any:
        if path.startswith("s3://"):
            path = path.replace(f"s3://{self.bucket}/", "")
        
        response = self.client.get_object(self.bucket, path)
        return pickle.loads(response.read())
    
    def exists(self, path: str) -> bool:
        try:
            self.client.stat_object(self.bucket, path)
            return True
        except:
            return False
    
    def to_dict(self):
        return {
            "type": "minio",
            "endpoint": self.endpoint,
            "bucket": self.bucket
        }
```

### Test Custom Component

```bash
# Install MinIO client
pip install minio

# Start MinIO (Docker)
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  minio/minio server /data --console-address ":9001"

# Load component
uniflow component load custom_components.minio_store

# Verify
uniflow component list
```

## Step 5: Multi-Environment Configuration

Update `uniflow.yaml`:

```yaml
# Multi-environment configuration

stacks:
  # Local development
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts
    metadata_store:
      path: .uniflow/metadata.db
  
  # Development with MinIO
  dev_minio:
    type: local
    artifact_store:
      type: minio
      endpoint: localhost:9000
      bucket: ml-dev
    metadata_store:
      path: .uniflow/metadata.db
  
  # Staging on GCP
  staging:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    region: us-central1
    artifact_store:
      type: gcs
      bucket: ${GCP_STAGING_BUCKET}
    orchestrator:
      type: vertex_ai
  
  # Production on GCP
  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    region: us-central1
    artifact_store:
      type: gcs
      bucket: ${GCP_PROD_BUCKET}
    orchestrator:
      type: vertex_ai
      service_account: ${GCP_SERVICE_ACCOUNT}

default_stack: local

resources:
  default:
    cpu: "2"
    memory: "8Gi"
  
  training:
    cpu: "8"
    memory: "32Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 2

docker:
  use_poetry: true
  base_image: python:3.11-slim

components:
  - module: custom_components.minio_store
```

### Test Different Stacks

```bash
# Local
uniflow run training_pipeline.py

# With MinIO
uniflow run training_pipeline.py --stack dev_minio

# Staging (dry run)
uniflow run training_pipeline.py --stack staging --dry-run

# Production with GPUs
uniflow run training_pipeline.py \
  --stack production \
  --resources training \
  --context epochs=50
```

##Step 6: Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY pyproject.toml* requirements.txt* ./

# Install Python dependencies
RUN if [ -f pyproject.toml ]; then \
        pip install poetry && poetry install --no-dev; \
    elif [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi

# Install UniFlow
RUN pip install uniflow[tensorflow,gcp]

# Copy code
COPY . .

# Set entrypoint
ENTRYPOINT ["python"]
CMD ["training_pipeline.py"]
```

### Build and Test

```bash
# Build image
docker build -t ml-pipeline:latest .

# Test locally
docker run ml-pipeline:latest

# Push to registry
docker tag ml-pipeline:latest gcr.io/my-project/ml-pipeline:v1
docker push gcr.io/my-project/ml-pipeline:v1
```

## Step 7: CI/CD Setup

Create `.github/workflows/ml-pipeline.yml`:

```yaml
name: ML Training Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install uniflow[tensorflow]
          pip install minio  # For custom component
      
      - name: Run tests
        run: |
          uniflow run training_pipeline.py --dry-run
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install UniFlow
        run: |
          pip install uniflow[tensorflow,gcp]
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Run pipeline on GCP
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_STAGING_BUCKET: ${{ secrets.GCP_STAGING_BUCKET }}
          GCP_PROD_BUCKET: ${{ secrets.GCP_PROD_BUCKET }}
          GCP_SERVICE_ACCOUNT: ${{ secrets.GCP_SERVICE_ACCOUNT }}
        run: |
          ENV=${{ github.event.inputs.environment || 'staging' }}
          
          uniflow run training_pipeline.py \
            --stack $ENV \
            --resources training \
            --context experiment_name=github-${{ github.run_id }}
```

## Step 8: Production Deployment

### Verify Configuration

```bash
# Check stack configuration
uniflow stack show production

# Dry run
uniflow run training_pipeline.py \
  --stack production \
  --resources training \
  --dry-run
```

### Deploy

```bash
# Run on production
uniflow run training_pipeline.py \
  --stack production \
  --resources training \
  --context epochs=100 \
  --context experiment_name=prod-v1
```

## What You've Learned

✅ **Clean pipeline code** - no infrastructure coupling  
✅ **Custom components** - MinIO artifact store  
✅ **Multi-environment setup** - dev, staging, production  
✅ **Configuration-driven** - same code, different infra  
✅ **Docker integration** - containerized execution  
✅ **CI/CD automation** - GitHub Actions deployment  

## Next Steps

1. **Add more custom components**
   - Airflow orchestrator
   - Redis cache
   - Custom metrics tracker

2. **Enhance pipeline**
   - Hyperparameter tuning
   - Model registry integration
   - A/B testing

3. **Monitor and optimize**
   - Add logging
   - Track metrics
   - Optimize resources

4. **Share components**
   - Package as pip installable
   - Publish to PyPI
   - Contribute to community

## Resources

- [Components Guide](../user-guide/components.md)
- [Configuration Guide](../user-guide/configuration.md)
- [CLI Reference](../reference/cli.md)
- [Example Code](../../examples/)

## Troubleshooting

### MinIO Connection Issues

```bash
# Check MinIO is running
docker ps | grep minio

# Test connection
python -c "from minio import Minio; Minio('localhost:9000', 'minioadmin', 'minioadmin').list_buckets()"
```

### GCP Authentication Issues

```bash
# Check authentication
gcloud auth list

# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### Component Not Loading

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Load explicitly
uniflow component load custom_components.minio_store

# Verify
uniflow component list
```

Congratulations! You've built a production-ready, extensible ML pipeline! 🎉
