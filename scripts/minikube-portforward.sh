#!/bin/bash
# Port-forward ingress controller on privileged ports 80/443.
# Runs as root via LaunchDaemon at boot.
set -x

LOG="/tmp/minikube-portforward.log"
KUBECTL="/opt/homebrew/bin/kubectl"
KUBECONFIG="/Users/rroyce/.kube/config"
export KUBECONFIG
MAX_WAIT=600
INTERVAL=10

log() {
    echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $1" >> "$LOG"
}

log "INFO: Waiting for ingress controller to be ready"
elapsed=0
while true; do
    ready=$("$KUBECTL" get pods -n ingress-nginx \
        -l app.kubernetes.io/name=ingress-nginx \
        -l app.kubernetes.io/component=controller \
        --context=minikube-local \
        -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$ready" = "Running" ]; then
        break
    fi
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "ERROR: Ingress controller not ready after ${MAX_WAIT}s"
        exit 1
    fi
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done
log "INFO: Ingress controller is ready"

log "INFO: Starting port-forward 80:80 443:443"
"$KUBECTL" port-forward \
    -n ingress-nginx \
    svc/ingress-nginx-controller \
    80:80 443:443 \
    --address 0.0.0.0 \
    --context=minikube-local \
    >> "$LOG" 2>&1
