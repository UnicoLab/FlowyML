# Human-in-the-Loop & Approvals ✋

Inject human intelligence into automated workflows. Pause pipelines for manual review, safety checks, or compliance approvals.

> [!NOTE]
> **What you'll learn**: How to stop automation when a human decision is required
>
> **Key insight**: Not everything should be automated. Deployment to production often needs a human "thumbs up."

## Why Human Review Matters

**Use cases**:
- **Safety**: "Does this model output look safe?"
- **Compliance**: "Has Legal approved this dataset?"
- **Quality Assurance**: "Is the generated image high quality?"
- **Cost Control**: "Approve spending $500 on this training run?"

## ✋ Approval Steps

You can insert an `approval` step anywhere in your pipeline.

### Real-World Pattern: The Deployment Gate

The classic MLOps pattern: Train automatically, deploy manually.

```python
from flowyml import Pipeline, step, approval

pipeline = Pipeline("deployment_pipeline")

@step
def train():
    return model

# Pause here!
approve_deploy = approval(
    name="approve_deploy",
    approver="lead-data-scientist",
    timeout_seconds=86400  # 24 hours to approve
)

@step
def deploy(model):
    # Only runs if approved
    production.deploy(model)

pipeline.add_step(train)
pipeline.add_step(approve_deploy)
pipeline.add_step(deploy)
```

### Interactive Approval

When running locally (CLI), the pipeline will pause and prompt the user:

```bash
$ flowyml run deployment_pipeline

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
