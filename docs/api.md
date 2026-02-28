# Webhook Server API Documentation

## Overview

FastAPI server that receives webhook events from GitHub, then publishes them to SNS topics for downstream processing.

## Endpoints

### Health Check

**GET /health**

Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-01T00:00:00.000000+00:00"
}
```

### GitHub Webhook

**POST /webhooks/github**

Receives GitHub webhook events and publishes to SNS.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| X-Hub-Signature-256 | Yes | HMAC-SHA256 signature (sha256=...) |
| X-GitHub-Event | No | GitHub event type |
| Content-Type | Yes | application/json |

**Response:**
```json
{
  "status": "accepted",
  "message_id": "sns-message-id-123"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing signature
- `422 Unprocessable Entity`: Invalid pull request payload
- `500 Internal Server Error`: Failed to publish to SNS

### GitHub PR Review

**POST /webhooks/github/review**

Triggers an AI-powered code review for a GitHub pull request.

**Request Body:**
```json
{
  "owner": "org",
  "repo": "my-repo",
  "pr_number": 123,
  "post_comment": true,
  "custom_prompt": "Focus on security issues"
}
```

**Response:**
```json
{
  "status": "completed",
  "pr_number": 123,
  "repository": "my-repo",
  "owner": "org",
  "summary": "Code looks good overall.",
  "files_reviewed": 5,
  "approval_recommendation": true,
  "comment_count": 3,
  "comment_posted": true,
  "review_markdown": "## Code Review\n..."
}
```

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| HOST | No | 0.0.0.0 | Server bind host |
| PORT | No | 8080 | Server bind port |
| DEBUG | No | false | Enable debug mode |
| LOG_LEVEL | No | INFO | Logging level |
| AWS_REGION | No | us-east-1 | AWS region |
| GITHUB_SNS_TOPIC_ARN | Yes | - | SNS topic for GitHub |
| GITHUB_WEBHOOK_SECRET | Yes | - | GitHub signature secret |
| GITHUB_BASE_URL | No | https://api.github.com | GitHub API URL |
| GITHUB_TOKEN | No | - | GitHub personal access token |
| GITHUB_API_TIMEOUT | No | 30.0 | GitHub API timeout |
| USE_LOCALSTACK | No | false | Use LocalStack for testing |
| LOCALSTACK_ENDPOINT | No | - | LocalStack endpoint URL |

## Running the Server

```bash
# Create virtual environment (Python 3.12+)
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the server
cd src
python main.py
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_health.py
```

## SNS Message Format

Messages published to SNS include attributes for filtering:

```json
{
  "MessageAttributes": {
    "event_type": {
      "DataType": "String",
      "StringValue": "pull_request"
    },
    "source": {
      "DataType": "String",
      "StringValue": "github"
    }
  }
}
```
