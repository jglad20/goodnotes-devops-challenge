#!/bin/bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root directory
cd "$PROJECT_ROOT"

echo "================================================"
echo "Deploying http-echo applications..."
echo "================================================"

# Deploy foo-echo
echo ""
echo "Deploying foo-echo..."
kubectl apply -f kubernetes/deployments/foo-deployment.yaml
kubectl apply -f kubernetes/services/foo-service.yaml

# Deploy bar-echo
echo "Deploying bar-echo..."
kubectl apply -f kubernetes/deployments/bar-deployment.yaml
kubectl apply -f kubernetes/services/bar-service.yaml

# Wait for deployments to be ready
echo ""
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=Available deployment/foo-echo --timeout=300s
kubectl wait --for=condition=Available deployment/bar-echo --timeout=300s

# Deploy ingress
echo ""
echo "Deploying ingress..."
kubectl apply -f kubernetes/ingress/ingress.yaml

# Wait a bit for ingress to be processed
sleep 10

echo ""
echo "================================================"
echo "Deployment Status"
echo "================================================"
kubectl get deployments
kubectl get pods -o wide
kubectl get services
kubectl get ingress

echo ""
echo "✅ All workloads deployed successfully!"
