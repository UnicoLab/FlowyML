# API-Based Execution & Token Management 🚀

UniFlow provides a robust REST API for executing pipelines, managing tokens, and interacting with the system programmatically. This allows you to integrate UniFlow into your existing infrastructure, such as CI/CD pipelines or custom dashboards.

## 🔑 Token Management

Secure access to the UniFlow API is managed via API tokens.

### Creating Tokens

You can generate tokens via the UI or CLI.

**Using CLI:**
```bash
# Generate a new token
uniflow token create --name "ci-cd-token" --role "admin"

# List tokens
uniflow token list

# Revoke a token
uniflow token revoke --token-id <token_id>
```

**Using UI:**
1. Navigate to **Settings** > **API Tokens**.
2. Click **Generate New Token**.
3. Copy the token immediately; it won't be shown again.

### Using Tokens

Include the token in the `Authorization` header of your HTTP requests:

```http
Authorization: Bearer <your_token>
```

## 🚀 API-Based Pipeline Execution

You can trigger pipelines remotely using the REST API.

### Trigger a Run

**Endpoint:** `POST /api/v1/runs`

**Request Body:**
```json
{
  "pipeline_name": "training_pipeline",
  "project": "default",
  "parameters": {
    "learning_rate": 0.01,
    "epochs": 20
  }
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8080/api/v1/runs \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "training_pipeline",
    "parameters": {"epochs": 50}
  }'
```

### Check Run Status

**Endpoint:** `GET /api/v1/runs/{run_id}`

**Response:**
```json
{
  "run_id": "run_12345",
  "status": "running",
  "created_at": "2023-10-27T10:00:00Z",
  "pipeline_name": "training_pipeline"
}
```

### List Runs

**Endpoint:** `GET /api/v1/runs`

**Query Parameters:**
- `pipeline_name`: Filter by pipeline.
- `status`: Filter by status (e.g., `success`, `failed`).
- `limit`: Number of results to return.

## 📚 API Reference

For a complete list of endpoints, visit the interactive API documentation (Swagger UI) at:

`http://localhost:8080/docs`
