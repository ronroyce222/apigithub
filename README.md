# apigithub

Version 2

FastAPI server that receives webhook events from GitHub,
validates their signatures, and publishes them to AWS SNS topics for
downstream processing by
[svc-pr-code-reviewer](../svc-pr-code-reviewer/).

## Architecture Role

This service is the **ingress point** in the PR Code Review system.
It exposes HTTPS endpoints that Git hosting platforms call when pull
request events occur.

```
GitHub ──HTTPS──▶ api-webhook ──SNS──▶ Event SQS Queue
                   /webhook/pr
```

See the [system architecture](../docs/pr-code-reviewer.png) for the
full data flow.

## Features

- FastAPI-based async webhook receiver
- HMAC-SHA256 signature verification for GitHub webhooks
- Async SNS publishing with exponential backoff retry using `aioboto3`
- AI-powered PR code review via Claude Code CLI
- GitHub API integration for fetching diffs and posting comments
- Health check endpoints for Kubernetes liveness/readiness probes
- LocalStack support for local AWS testing
- Configurable via environment variables with Pydantic settings

## Requirements

- Python 3.12+
- AWS IAM role with SNS publish permissions
- GitHub webhook secret for signature verification

## Installation

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure environment variables
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8080` | Server bind port |
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `GITHUB_SNS_TOPIC_ARN` | Yes | - | SNS topic for GitHub events |
| `GITHUB_WEBHOOK_SECRET` | Yes | - | GitHub signature secret |
| `GITHUB_BASE_URL` | No | `https://api.github.com` | GitHub API URL |
| `GITHUB_TOKEN` | No | - | GitHub personal access token |
| `GITHUB_API_TIMEOUT` | No | `30.0` | GitHub API timeout |
| `CLAUDE_CODE_PATH` | No | - | Path to Claude Code CLI |
| `CLAUDE_CODE_MODEL` | No | - | Claude model for reviews |
| `CODE_REVIEW_ENABLED` | No | `true` | Enable code review feature |
| `USE_LOCALSTACK` | No | `false` | Use LocalStack for testing |
| `LOCALSTACK_ENDPOINT` | No | - | LocalStack endpoint URL |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Home/info endpoint |
| `GET` | `/health` | Full health check with version |
| `GET` | `/health/live` | Kubernetes liveness probe |
| `GET` | `/health/ready` | Kubernetes readiness probe |
| `GET` | `/health/startup` | Kubernetes startup probe |
| `POST` | `/webhooks/github` | Receive GitHub webhook, publish to SNS |
| `POST` | `/webhooks/github/review` | Trigger AI code review on a PR |

## Usage

### Running Locally

```bash
cd src
python main.py
```

### Running with Docker

```bash
docker build -t api-webhook .
docker run -p 8080:8080 --env-file .env api-webhook
```

### Running with LocalStack

```bash
docker-compose up -d   # Starts LocalStack
cd src && python main.py
```

## Development

### Running Tests

```bash
pytest
pytest --cov=src --cov-report=term-missing
pytest tests/test_health.py -v
```

### Code Quality

```bash
black src tests
ruff check src tests
```

## Project Structure

```
api-webhook/
├── src/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings
│   ├── logging_config.py        # Enhanced syslog logging
│   ├── version.py               # Application version
│   ├── models/                  # Pydantic data models
│   │   ├── github_event.py      # GitHub webhook models
│   │   ├── github_pull_request.py
│   │   ├── github_user.py
│   │   ├── github_repository.py
│   │   ├── github_ref.py
│   │   └── pr_review.py         # Code review models
│   ├── routers/                 # FastAPI route handlers
│   │   ├── home.py              # Root endpoint
│   │   ├── health.py            # Health check endpoints
│   │   └── github.py            # GitHub webhook handlers
│   ├── services/                # Business logic
│   │   ├── sns_publisher.py     # AWS SNS publishing
│   │   ├── github_signature.py  # HMAC-SHA256 verification
│   │   ├── github_api.py        # GitHub REST API client
│   │   └── claude_code_reviewer.py  # Claude Code CLI
│   └── exceptions/              # Custom exceptions
├── tests/                       # Test suite
├── docs/                        # Documentation
│   ├── api.md                   # API reference
│   └── architecture.md          # Architecture details
├── localstack/                  # LocalStack initialization
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

## Documentation

- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)

## License

Proprietary
