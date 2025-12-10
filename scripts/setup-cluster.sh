#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Creating multi-node KinD cluster..."
kind create cluster --config kubernetes/kind-config.yaml

echo "Waiting for cluster nodes to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

echo ""
echo "Cluster Info:"
kubectl cluster-info
kubectl get nodes -o wide

echo ""
echo "✅ Multi-node KinD cluster created (1 control-plane + 2 workers)"
