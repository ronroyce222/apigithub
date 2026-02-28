#!/bin/bash
# LocalStack initialization script for AWS resources
# This script runs automatically when LocalStack starts

set -e

REGION="us-east-1"
ENDPOINT="http://localhost:4566"

echo "Initializing LocalStack AWS resources..."

# Create SNS topics
echo "Creating SNS topics..."
awslocal sns create-topic --name github-events --region $REGION

# Create SQS queues
echo "Creating SQS queues..."
awslocal sqs create-queue --queue-name github-events-queue --region $REGION

# Create dead letter queues for retry handling
echo "Creating dead letter queues..."
awslocal sqs create-queue --queue-name github-events-dlq --region $REGION

# Get queue ARNs for subscriptions
GITHUB_QUEUE_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url http://localhost:4566/000000000000/github-events-queue \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text \
    --region $REGION)

# Subscribe SQS queues to SNS topics
echo "Subscribing SQS queues to SNS topics..."
awslocal sns subscribe \
    --topic-arn arn:aws:sns:us-east-1:000000000000:github-events \
    --protocol sqs \
    --notification-endpoint $GITHUB_QUEUE_ARN \
    --region $REGION

# List created resources
echo ""
echo "=== LocalStack Resources Created ==="
echo ""
echo "SNS Topics:"
awslocal sns list-topics --region $REGION

echo ""
echo "SQS Queues:"
awslocal sqs list-queues --region $REGION

echo ""
echo "SNS Subscriptions:"
awslocal sns list-subscriptions --region $REGION

echo ""
echo "LocalStack initialization complete!"
