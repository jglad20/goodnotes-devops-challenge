#!/bin/bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root directory
cd "$PROJECT_ROOT"

echo "================================================"
echo "Creating multi-node KinD cluster..."
echo "================================================"

# Create cluster from config
kind create cluster --config kubernetes/kind-config.yaml

echo ""
echo "Waiting for cluster nodes to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

echo ""
echo "================================================"
echo "Cluster Information"
echo "================================================"
kubectl cluster-info

echo ""
echo "================================================"
echo "Node Status"
echo "================================================"
kubectl get nodes -o wide

echo ""
echo "================================================"
echo "Pod Network Status"
echo "================================================"
kubectl get pods -A

echo ""
echo "✅ Multi-node KinD cluster created successfully!"
echo "   - 1 control-plane node"
echo "   - 2 worker nodes"
