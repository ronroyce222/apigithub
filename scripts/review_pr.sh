#!/bin/bash
# Script to trigger a PR code review via the github/review endpoint.
#
# Usage:
#   ./review_pr.sh <owner> <repo> <pr_number> [post_comment]
#
# Examples:
#   ./review_pr.sh org my-repo 123
#   ./review_pr.sh org my-repo 123 true

set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8080}"
ENDPOINT="${BASE_URL}/webhooks/github/review"

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <owner> <repo> <pr_number> [post_comment]"
    echo ""
    echo "Arguments:"
    echo "  owner          GitHub repository owner"
    echo "  repo           Repository name"
    echo "  pr_number      Pull request number"
    echo "  post_comment   Optional: true/false (default: false)"
    echo ""
    echo "Environment variables:"
    echo "  API_BASE_URL   Base URL of the API (default: http://localhost:8080)"
    exit 1
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
POST_COMMENT="${4:-false}"

JSON_PAYLOAD=$(cat <<EOF
{
    "owner": "${OWNER}",
    "repo": "${REPO}",
    "pr_number": ${PR_NUMBER},
    "post_comment": ${POST_COMMENT}
}
EOF
)

echo "Sending review request to: ${ENDPOINT}"
echo "Payload: ${JSON_PAYLOAD}"
echo ""

curl -s -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "${JSON_PAYLOAD}" | python3 -m json.tool

echo ""
