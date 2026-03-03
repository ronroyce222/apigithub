#!/bin/bash
set +x
# Start minikube and wait for cluster readiness.
# Runs as user via LaunchAgent at login.

LOG="/tmp/minikube-startup.log"
MINIKUBE="/opt/homebrew/bin/minikube"
KUBECTL="/opt/homebrew/bin/kubectl"
PROFILE="minikube-local"
MAX_WAIT=300
INTERVAL=5

echo "Starting..."

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $1" >> "$LOG"
}

echo "INFO: Waiting for Docker to be ready"
elapsed=0
while ! docker info >/dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Docker not ready after ${MAX_WAIT}s"
        exit 1
    fi
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done
echo "INFO: Docker is ready"

echo "INFO: Starting minikube profile=${PROFILE}"
"$MINIKUBE" start --driver=docker --profile="$PROFILE" >> "$LOG" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "ERROR: minikube start failed rc=${rc}"
    exit 1
fi
echo "INFO: minikube started successfully"

echo "INFO: Waiting for cluster nodes to be ready"
elapsed=0
while ! "$KUBECTL" get nodes --context="$PROFILE" 2>/dev/null \
        | grep -q " Ready"; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Cluster not ready after ${MAX_WAIT}s"
        exit 1
    fi
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done
echo "INFO: Cluster is ready"
