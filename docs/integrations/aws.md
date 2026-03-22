# ☁️ Amazon Web Services (AWS)

!!! info "What you'll learn"
    How to use S3 for artifact storage and SageMaker for execution — FlowyML abstracts away the complexity of Boto3 and AWS SDKs.

Deploy your FlowyML pipelines to the world's leading cloud provider with zero code changes.

---

## Why AWS with FlowyML?

| Feature | Benefit |
|---|---|
| **S3 Durability** | 99.999999999% durability for model artifacts |
| **SageMaker** | Specialized ML instances (Trainium, Inferentia, GPUs) |
| **IAM Security** | Granular access control for data and resources |
| **ECR** | Private container registry for pipeline images |

---

## 🪣 S3 Artifact Store

Use Amazon S3 as the backend for all your pipeline artifacts:

```bash
# Register an AWS stack
flowyml stack register aws-prod \
    --artifact-store s3://my-bucket/flowyml-artifacts \
    --metadata-store sqlite:///flowyml.db
```

```python
from flowyml import Pipeline

# Artifacts automatically go to S3 when using the aws-prod stack
pipeline = Pipeline("training")
pipeline.run()  # All artifacts saved to s3://my-bucket/flowyml-artifacts/
```

---

## 🧠 SageMaker Execution

Run your pipelines on Amazon SageMaker Processing Jobs or Training Jobs:

```python
from flowyml import Pipeline
from flowyml.integrations.aws import SageMakerOrchestrator

pipeline = Pipeline("aws_pipeline")

pipeline.run(
    orchestrator=SageMakerOrchestrator(
        role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
        instance_type="ml.m5.xlarge",
        region_name="us-east-1",
    )
)
```

### SageMaker Configuration

| Parameter | Type | Description |
|---|---|---|
| `role_arn` | `str` | IAM role ARN for SageMaker execution |
| `instance_type` | `str` | Compute instance (e.g., `ml.m5.xlarge`, `ml.p3.2xlarge`) |
| `region_name` | `str` | AWS region |
| `instance_count` | `int` | Number of instances (default: 1) |
| `volume_size_gb` | `int` | EBS storage per instance (default: 30) |

---

## 🔐 Authentication

FlowyML uses the standard AWS credential chain:

1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. **Shared credentials file**: `~/.aws/credentials`
3. **IAM Role**: Automatic when running on EC2, Lambda, or SageMaker

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1

# Option 2: AWS CLI configured profile
aws configure --profile flowyml
```

---

## Best Practices

!!! tip "Use IAM roles in production"
    Avoid hardcoding credentials. Use IAM roles on EC2/SageMaker for secure, credential-free authentication.

!!! tip "S3 lifecycle policies"
    Set up S3 lifecycle policies to automatically archive or delete old artifacts and reduce storage costs.
