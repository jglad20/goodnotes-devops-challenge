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

  local response=""

  # Method 1: Try hostPort (works on Docker Desktop / local KinD)
  response=$(curl -s -H "Host: $host" http://localhost:80 --max-time 3 2>/dev/null || echo "")

  # Method 2: If hostPort failed, try NodePort (GitHub Actions)
  if [ -z "$response" ] || [[ "$response" == *"Connection refused"* ]]; then
    local nodeport=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')
    if [ -n "$nodeport" ]; then
      echo "  → Trying NodePort :$nodeport"
      response=$(curl -s -H "Host: $host" http://localhost:$nodeport --max-time 3 2>/dev/null || echo "")
    fi
  fi

  # Method 3: Try via Docker network (KinD specific)
  if [ -z "$response" ] || [[ "$response" == *"Connection refused"* ]]; then
    # Use Go template index to get only the first network's IP (avoids concatenation issue)
    local control_plane_ip=$(docker inspect -f '{{(index .NetworkSettings.Networks (index (keys .NetworkSettings.Networks) 0)).IPAddress}}' devops-challenge-control-plane 2>/dev/null || echo "")
    if [ -n "$control_plane_ip" ]; then
      echo "  → Trying control plane IP: $control_plane_ip"
      response=$(curl -s -H "Host: $host" http://$control_plane_ip:80 --max-time 3 2>/dev/null || echo "")
    fi
  fi

  # Method 4: As last resort, test from inside the cluster using a test pod
  if [ -z "$response" ] || [[ "$response" == *"Connection refused"* ]] || [[ "$response" == "FAILED" ]]; then
    echo "  → Trying from inside cluster (test pod)"
    # Create a temporary test pod with unique name to avoid conflicts
    local pod_name="curl-test-${host//./-}-$$"
    # Note: kubectl run --rm outputs "pod deleted" message, so we filter it out with grep -v
    kubectl run "$pod_name" --image=curlimages/curl:latest --rm -i --restart=Never --pod-running-timeout=30s -- \
      curl -s -H "Host: $host" http://ingress-nginx-controller.ingress-nginx.svc.cluster.local --max-time 5 2>/dev/null \
      | grep -v "^pod.*deleted" > /tmp/ingress-test-$host.txt || true
    response=$(cat /tmp/ingress-test-$host.txt 2>/dev/null || echo "FAILED")
    rm -f /tmp/ingress-test-$host.txt
  fi

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
# Give ingress more time to fully propagate (especially in CI environments)
echo "Waiting 10 seconds for ingress rules to propagate..."
sleep 10

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
