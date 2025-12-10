#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "================================================"
echo "Deploying http-echo applications via Kustomize..."
echo "================================================"

echo ""
echo "Deploying foo-echo..."
kubectl apply -k kubernetes/overlays/foo

echo "Deploying bar-echo..."
kubectl apply -k kubernetes/overlays/bar

echo ""
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=Available deployment/foo-echo --timeout=300s
kubectl wait --for=condition=Available deployment/bar-echo --timeout=300s

echo ""
echo "Deploying ingress..."
kubectl apply -f kubernetes/ingress/ingress.yaml

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
