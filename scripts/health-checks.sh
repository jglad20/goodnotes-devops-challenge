#!/bin/bash
set -euo pipefail

echo "================================================"
echo "Running Health Checks..."
echo "================================================"

FAILED=0

# Function to check deployment health
check_deployment() {
  local deployment=$1
  local desired=$(kubectl get deployment "$deployment" -o jsonpath='{.spec.replicas}')
  local ready=$(kubectl get deployment "$deployment" -o jsonpath='{.status.readyReplicas}')

  if [ "$desired" == "$ready" ]; then
    echo "✅ Deployment $deployment: $ready/$desired replicas ready"
    return 0
  else
    echo "❌ Deployment $deployment: $ready/$desired replicas ready"
    return 1
  fi
}

# Function to check service
check_service() {
  local service=$1

  if kubectl get service "$service" &> /dev/null; then
    local endpoints=$(kubectl get endpoints "$service" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
    if [ "$endpoints" -gt 0 ]; then
      echo "✅ Service $service: $endpoints endpoints available"
      return 0
    else
      echo "❌ Service $service: No endpoints available"
      return 1
    fi
  else
    echo "❌ Service $service: Not found"
    return 1
  fi
}

# Function to test ingress routing
test_ingress() {
  local host=$1
  local expected_text=$2

  echo ""
  echo "Testing ingress route: $host"

  # Test with curl
  response=$(curl -s -H "Host: $host" http://localhost --max-time 5 || echo "FAILED")

  if [[ "$response" == *"$expected_text"* ]]; then
    echo "✅ $host → Response: $response"
    return 0
  else
    echo "❌ $host → Expected '$expected_text', got: $response"
    return 1
  fi
}

echo ""
echo "1. Checking Deployments..."
echo "----------------------------"
check_deployment "foo-echo" || FAILED=1
check_deployment "bar-echo" || FAILED=1

echo ""
echo "2. Checking Services..."
echo "----------------------------"
check_service "foo-echo-service" || FAILED=1
check_service "bar-echo-service" || FAILED=1

echo ""
echo "3. Checking Ingress..."
echo "----------------------------"
if kubectl get ingress http-echo-ingress &> /dev/null; then
  echo "✅ Ingress http-echo-ingress: Found"
  kubectl get ingress http-echo-ingress
else
  echo "❌ Ingress http-echo-ingress: Not found"
  FAILED=1
fi

echo ""
echo "4. Testing Ingress Routing..."
echo "----------------------------"
# Give ingress a moment to fully propagate
sleep 5

test_ingress "foo.localhost" "foo" || FAILED=1
test_ingress "bar.localhost" "bar" || FAILED=1

echo ""
echo "================================================"
if [ $FAILED -eq 0 ]; then
  echo "✅ ALL HEALTH CHECKS PASSED"
  echo "================================================"
  exit 0
else
  echo "❌ SOME HEALTH CHECKS FAILED"
  echo "================================================"
  echo ""
  echo "Debugging information:"
  echo "----------------------------"
  kubectl get all -A
  exit 1
fi
