# Amazon Web Services (AWS) ☁️

Deploy your UniFlow pipelines to the world's leading cloud provider.

> [!NOTE]
> **What you'll learn**: How to use S3 for storage and SageMaker for execution
>
> **Key insight**: UniFlow abstracts away the complexity of Boto3 and AWS SDKs.

## Why Use AWS with UniFlow?

- **S3 Durability**: 99.999999999% durability for your model artifacts.
- **SageMaker Power**: Access specialized ML instances (Trainium, Inferentia).
- **IAM Security**: Granular access control for your data.

## 🪣 S3 Artifact Store

Use Amazon S3 as the backend for all your pipeline artifacts.

### Configuration

```bash
# Register an AWS stack
uniflow stack register aws-prod \
    --artifact-store s3://my-bucket/uniflow-artifacts \
    --metadata-store sqlite:///uniflow.db
```

## 🧠 SageMaker Execution

Run your pipelines on Amazon SageMaker Processing Jobs or Training Jobs.

### Real-World Pattern: Scale to Cloud

```python
from uniflow import Pipeline
from uniflow.integrations.aws import SageMakerOrchestrator

pipeline = Pipeline("aws_pipeline")

# Run on SageMaker
pipeline.run(
    orchestrator=SageMakerOrchestrator(
        role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
        instance_type="ml.m5.xlarge",
        region_name="us-east-1"
    )
)
```

## 🔐 Authentication

UniFlow uses the standard AWS credential chain.
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file
3. IAM Role (if running on EC2/Lambda)
