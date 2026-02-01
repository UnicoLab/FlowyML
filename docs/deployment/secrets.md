# Secret Management for FlowyML

FlowyML uses cloud-native secret management services (GCP Secret Manager, AWS Secrets Manager) to securely handle sensitive information like database passwords, authentication secrets, and API tokens.

## Overview

Infrastructure is provisioned using Terraform, which creates:
1.  **Secret Store**: A centralized secret in the cloud provider.
2.  **Secret Version**: The actual value of the secret.
3.  **IAM Binding**: Permissions for the compute service (Cloud Run / App Runner) to access the secret.
4.  **Injection**: Secrets are mounted as environment variables at runtime.

## Usage

### 1. Define Secrets Locally

**DO NOT** commit secrets to version control. Instead, use a local variable definition file (e.g., `prod.secrets.tfvars`).

Create a file named `prod.secrets.tfvars`:

```hcl
db_password = "super_secure_db_password"
auth_secret = "your_jwt_signing_secret_key"
api_token   = "your_static_api_token"
```

**Note**: Ensure `*.tfvars` is in your `.gitignore` (except for example files).

### 2. Deploy with Secrets

When running Terraform commands, pass the secrets file using the `-var-file` flag.

#### GCP
```bash
cd infra/gcp
terraform init
terraform apply -var-file="prod.secrets.tfvars"
```

#### AWS
```bash
cd infra/aws
terraform init
terraform apply -var-file="prod.secrets.tfvars"
```

## Secret Rotation

To rotate a secret:
1.  Update the value in your `prod.secrets.tfvars` file.
2.  Run `terraform apply -var-file="prod.secrets.tfvars"`.
3.  Terraform will add a new version to the Secret Manager.
4.  **Important**: You must redeploy the application (Cloud Run / App Runner) to pick up the new "latest" version of the secret. Infrastructure changes alone usually won't trigger a container restart unless the service revision template changes.

## Troubleshooting

- **Permission Denied**: Ensure the Service Account (GCP) or Instance Role (AWS) has the correct IAM role (`roles/secretmanager.secretAccessor` or `secretsmanager:GetSecretValue`).
- **Empty Secret**: GCP Secret Manager does not allow empty payloads. Ensure your variables are not empty strings.
