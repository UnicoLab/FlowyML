# Human-in-the-Loop & Approvals ✋

UniFlow supports "Human-in-the-Loop" workflows, allowing pipelines to pause and wait for manual approval before proceeding. This is essential for deployment pipelines or critical decision points.

## ✋ Approval Steps

You can insert an `approval` step anywhere in your pipeline.

### Basic Usage

```python
from uniflow import Pipeline, step, approval

pipeline = Pipeline("deployment_pipeline")

@step
def train():
    # ... training logic ...
    return model

# Create an approval step
approve_deploy = approval(
    name="approve_deploy",
    approver="ml-team",
    timeout_seconds=3600  # Wait up to 1 hour
)

@step
def deploy(model):
    # ... deployment logic ...
    pass

pipeline.add_step(train)
pipeline.add_step(approve_deploy)
pipeline.add_step(deploy)

# Link dependencies
# deploy depends on approve_deploy, which depends on train
```

### Interactive Approval

When running locally (CLI), the pipeline will pause and prompt the user:

```bash
$ uniflow run deployment_pipeline

...
[INFO] Step 'train' completed.
[WARN] ✋ Step 'approve_deploy' requires approval.
       Waiting for approval from: ml-team
       Timeout: 3600s
       Approve execution? [y/N]:
```

### Auto-Approval Logic

You can define conditions for automatic approval, useful for CI/CD environments.

```python
approve_deploy = approval(
    name="approve_deploy",
    approver="ml-team",
    auto_approve_if=lambda: os.getenv("ENVIRONMENT") == "staging"
)
```

## 📧 Notifications

Approvers can be notified via configured channels (Email, Slack) when their attention is required. See [Notifications](notifications.md) for setup.
