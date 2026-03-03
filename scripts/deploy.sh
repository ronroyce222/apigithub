#!/bin/bash
set -x
# Build, push, and redeploy the apigithub container.

IMAGE="ronroyce222/ronroyce-repo:apigithub"
DEPLOYMENT="apigithub"
KUBECTL="/opt/homebrew/bin/kubectl"
PROFILE="minikube-local"
NAMESPACE="default"

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $1"
}

die() {
    log "ERROR: $1"
    exit 1
}

# --- Build ---
log "INFO: Building Docker image ${IMAGE}"
docker build --no-cache -t "$IMAGE" . || die "Docker build failed"

# --- Push ---
log "INFO: Pushing image to Docker Hub"
docker push "$IMAGE" || die "Docker push failed"

# --- Redeploy ---
log "INFO: Deleting deployment ${DEPLOYMENT}"
"$KUBECTL" delete deployment "$DEPLOYMENT" \
    --context="$PROFILE" \
    --namespace="$NAMESPACE" \
    --ignore-not-found || die "Failed to delete deployment"

log "INFO: Applying deployment from k8s/"
"$KUBECTL" apply -f k8s/ \
    --context="$PROFILE" \
    --namespace="$NAMESPACE" || die "Failed to apply k8s manifests"

log "INFO: Waiting for rollout to complete"
"$KUBECTL" rollout status deployment/"$DEPLOYMENT" \
    --context="$PROFILE" \
    --namespace="$NAMESPACE" \
    --timeout=120s || die "Rollout did not complete in time"

log "INFO: Deployment complete"
