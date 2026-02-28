# Architecture Documentation

## Overview

The API Webhook service is a FastAPI-based application that receives webhook
events from GitHub and Jira, validates their signatures, and publishes them
to AWS SNS topics for downstream processing. It also provides AI-powered code
review capabilities using Claude Code CLI.

## System Architecture

```
+---------------------------------------------------------------------------+
|                           External Services                               |
+---------------------------------------------------------------------------+
|  GitHub                  Jira Server              Claude Code CLI          |
|  (Webhooks)              (Webhooks)               (Code Review)           |
+--------+---------------------+---------------------------+---------------+
         |                     |                           |
         v                     v                           v
+---------------------------------------------------------------------------+
|                        FastAPI Application                                 |
|                           (main.py)                                       |
+---------------------------------------------------------------------------+
|                                                                           |
|  +-------------------+  +------------------+  +-------------------------+ |
|  |  Home Router      |  |  Health Router   |  |     GitHub Router       | |
|  |  GET /            |  |  GET /health/*   |  |  POST /webhooks/github  | |
|  +-------------------+  +------------------+  |  POST /webhooks/github/ | |
|                                               |       review            | |
|  +---------------------------------------+   +-------------------------+ |
|  |         Jira Router                   |                               |
|  |    POST /webhooks/jira                |                               |
|  +---------------------------------------+                               |
|                                                                           |
+-------+-------------------------+-------------------------+--------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +---------------------------+
|    Signature      |   |   SNS Publisher   |   |   GitHub API Client       |
|    Verifiers      |   |   (aioboto3)      |   |   (httpx)                 |
|  (HMAC-SHA256)    |   |                   |   |                           |
+-------------------+   +---------+---------+   +---------------------------+
                                  |
                                  v
                        +-------------------+
                        |   AWS Services    |
                        |   - SNS Topics    |
                        |   - SQS Queues    |
                        +-------------------+
```

## Project Structure

```
api-webhook/
├── src/                           # Application source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Pydantic settings configuration
│   ├── logging_config.py         # Enhanced syslog logging setup
│   ├── version.py                # Application version
│   ├── models/                   # Pydantic data models
│   │   ├── github_event.py      # GitHub webhook models
│   │   ├── github_pull_request.py
│   │   ├── github_user.py
│   │   ├── github_repository.py
│   │   ├── github_ref.py
│   │   ├── jira_event.py        # Jira webhook models
│   │   └── pr_review.py         # Code review models
│   ├── routers/                  # FastAPI route handlers
│   │   ├── home.py              # Root endpoint
│   │   ├── health.py            # Health check endpoints
│   │   ├── github.py            # GitHub webhook handlers
│   │   └── jira.py              # Jira webhook handlers
│   ├── services/                 # Business logic services
│   │   ├── sns_publisher.py     # AWS SNS publishing
│   │   ├── github_signature.py  # GitHub signature verification
│   │   ├── jira_signature.py    # Jira signature verification
│   │   ├── github_api.py        # GitHub REST API client
│   │   └── claude_code_reviewer.py
│   └── exceptions/               # Custom exceptions
├── tests/                        # Test suite
├── docs/                         # Documentation
├── localstack/                   # LocalStack AWS emulation
│   └── init-aws.sh
├── requirements.txt
├── pyproject.toml
└── docker-compose.yml
```

## Core Components

### Application Entry Point

**File:** `src/main.py`

The application uses FastAPI's lifespan context manager for startup/shutdown:

1. **Startup Sequence:**
   - Load environment variables from `.env`
   - Configure logging with enhanced syslog format
   - Retry initialization with exponential backoff (3 attempts)
   - Include all route modules

2. **Application Factory:**
   - Creates FastAPI instance with custom lifespan
   - Registers routers: home, health, github, jira
   - Configures OpenAPI metadata

### Configuration Management

**File:** `src/config.py`

Uses Pydantic `BaseSettings` for type-safe configuration:

- Loads from environment variables and `.env` file
- Validates types and provides defaults
- Cached singleton via `@lru_cache`

Key configuration groups:
- Server settings (host, port, debug)
- AWS settings (region, SNS topic ARNs)
- Webhook secrets (GitHub, Jira)
- GitHub API credentials (token)
- Claude Code settings
- Feature flags

### Logging System

**File:** `src/logging_config.py`

Custom `SyslogFormatter` provides:
- Enhanced syslog format: `TIMESTAMP LEVEL [LOGGER] MESSAGE`
- UTC timestamps in ISO format
- Lazy logging for performance

### Route Handlers

#### Health Endpoints (`src/routers/health.py`)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Full health check with version |
| `GET /health/live` | Kubernetes liveness probe |
| `GET /health/ready` | Kubernetes readiness probe |
| `GET /health/startup` | Kubernetes startup probe |

#### GitHub Endpoints (`src/routers/github.py`)

| Endpoint | Purpose |
|----------|---------|
| `POST /webhooks/github` | Receive webhook, publish to SNS |
| `POST /webhooks/github/review` | Trigger AI code review |

#### Jira Endpoints (`src/routers/jira.py`)

| Endpoint | Purpose |
|----------|---------|
| `POST /webhooks/jira` | Receive webhook, publish to SNS |

### Services

#### SNS Publisher (`src/services/sns_publisher.py`)

- Async publishing using `aioboto3`
- Exponential backoff retry (3 attempts)
- Message attributes for filtering (source, event_type)
- LocalStack support for testing
- Uses IAM roles (no stored credentials)

#### Signature Verifiers

- `GitHubSignatureVerifier`: HMAC-SHA256 with `X-Hub-Signature-256`
- `JiraSignatureVerifier`: HMAC-SHA256 with `X-Atlassian-Webhook-Signature`

#### GitHub API Client (`src/services/github_api.py`)

- Async HTTP client using `httpx`
- Methods: `get_pr_diff()`, `get_pr_files()`, `get_pr_commits()`,
  `post_pr_comment()`
- Bearer token authentication
- Configurable timeout

#### Claude Code Reviewer (`src/services/claude_code_reviewer.py`)

- Executes Claude Code CLI via subprocess
- Parses JSON output for structured reviews
- Formats reviews as Markdown with severity grouping

## Data Flow

### Webhook Processing Flow

```
1. Webhook received (GitHub/Jira)
          |
          v
2. Extract signature from headers
          |
          v
3. Verify HMAC-SHA256 signature
          |
    +-----+-----+
    |           |
  Invalid     Valid
    |           |
    v           v
  401        4. Parse event payload
              |
              v
          5. Extract event type
              |
              v
          6. Publish to SNS with attributes
              |
              v
          7. Return message ID
```

### Code Review Flow

```
1. Review request received
          |
          v
2. Check feature flag enabled
          |
          v
3. Fetch PR diff from GitHub API
          |
          v
4. Build prompt with context
          |
          v
5. Execute Claude Code CLI
          |
          v
6. Parse JSON response
          |
          v
7. Format as Markdown
          |
          v
8. Optionally post comment to PR
          |
          v
9. Return review result
```

## Data Models

### GitHub Models (`src/models/github_event.py`)

- `GitHubEvent`: Flexible webhook payload model
- `GitHubWebhookResponse`: SNS publish response
- `PRReviewRequest`: Code review request parameters
- `PRReviewResponse`: Code review result

### Jira Models (`src/models/jira_event.py`)

- `JiraEvent`: Webhook event payload
- `JiraWebhookResponse`: SNS publish response

### PR Review Models (`src/models/pr_review.py`)

- `ReviewSeverity`: Enum (INFO, WARNING, ERROR, CRITICAL)
- `ReviewComment`: Individual review comment
- `CodeReviewResult`: Complete review result
- `PRContext`: PR metadata extraction

## External Integrations

### AWS SNS

- **Purpose:** Event distribution to downstream processors
- **Auth:** IAM roles (no stored credentials)
- **Topics:**
  - GitHub events: `GITHUB_SNS_TOPIC_ARN`
  - Jira events: `JIRA_SNS_TOPIC_ARN`
- **Message Attributes:**
  - `source`: "github" or "jira"
  - `event_type`: Event identifier (e.g., "pull_request")

### GitHub API

- **Purpose:** Fetch PR diffs, post review comments
- **Auth:** Bearer token (personal access token)
- **Endpoints Used:**
  - `GET /repos/{owner}/{repo}/pulls/{number}` (with diff Accept header)
  - `GET /repos/{owner}/{repo}/pulls/{number}/files`
  - `GET /repos/{owner}/{repo}/pulls/{number}/commits`
  - `POST /repos/{owner}/{repo}/issues/{number}/comments`

### Claude Code CLI

- **Purpose:** AI-powered code review
- **Execution:** Subprocess with timeout
- **Output:** JSON parsed to `CodeReviewResult`

## Security

### Webhook Signature Verification

All incoming webhooks require valid HMAC-SHA256 signatures:

```
signature = HMAC-SHA256(secret, request_body)
header_value = "sha256=" + hex(signature)
```

Invalid signatures result in `401 Unauthorized`.

### Credential Management

- All secrets via environment variables
- No hardcoded credentials
- AWS IAM roles for cloud authentication
- Secrets never logged

### Input Validation

- Pydantic models validate all payloads
- Type hints throughout codebase
- Request body size limits via FastAPI

## Error Handling

### Exception Hierarchy

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `AuthError` | 401 | Invalid signature |
| `GitHubAPIError` | 502 | GitHub API failure |
| `ClaudeCodeError` | 500 | Review generation failure |

### Retry Strategy

SNS publishing uses exponential backoff:
- Attempts: 3
- Base delay: 0.5 seconds
- Formula: `delay = base * (2 ** attempt)`

## Deployment

### Docker

```dockerfile
FROM python:3.12.12-alpine3.23
EXPOSE 8080
CMD ["python3.12", "main.py"]
```

### Kubernetes Probes

| Probe | Endpoint | Purpose |
|-------|----------|---------|
| Liveness | `/health/live` | Process running |
| Readiness | `/health/ready` | Accepting traffic |
| Startup | `/health/startup` | Initialization complete |

## Local Development

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (for LocalStack)

### Setup

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start LocalStack (optional, for AWS testing)
docker-compose up -d

# Run the server
cd src && python main.py
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_health.py -v
```

## Dependencies

### Core

| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | >=0.115.0 | Web framework |
| Uvicorn | 0.21.1 | ASGI server |
| aioboto3 | >=13.2.0 | Async AWS SDK |
| pydantic | >=2.10.0 | Data validation |
| httpx | >=0.28.0 | Async HTTP client |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.3.0 | Test framework |
| pytest-asyncio | >=0.24.0 | Async test support |
| localstack-client | >=2.6 | AWS emulation |
