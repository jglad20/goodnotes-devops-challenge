# Complete Setup Guide - Goodnotes DevOps Challenge

**Step-by-step instructions from zero to submission**

This guide walks you through the entire process, from setting up prerequisites to submitting your solution to Goodnotes.

---

## 📋 Table of Contents

1. [Prerequisites Installation](#1-prerequisites-installation)
2. [Local Testing (Optional)](#2-local-testing-optional)
3. [GitHub Repository Setup](#3-github-repository-setup)
4. [Create Pull Request](#4-create-pull-request)
5. [Verify Workflow Execution](#5-verify-workflow-execution)
6. [Submit to Goodnotes](#6-submit-to-goodnotes)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites Installation

### Option A: GitHub Actions Only (Recommended for Submission)

**Minimal Requirements:**
- Git installed locally
- GitHub account with Actions enabled
- GitHub CLI (optional, but recommended)

**Install Git:**
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Windows
# Download from https://git-scm.com/download/win
```

**Install GitHub CLI (optional):**
```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt-get install gh

# Windows
winget install GitHub.cli
```

**Authenticate GitHub CLI:**
```bash
gh auth login
# Follow prompts to authenticate
```

### Option B: Local Testing Setup (Optional)

If you want to test locally before submitting, install these additional tools:

**Install Docker Desktop:**
- macOS: https://docs.docker.com/desktop/install/mac-install/
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

**Install kubectl:**
```bash
# macOS
brew install kubectl

# Ubuntu/Debian
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Windows
winget install Kubernetes.kubectl
```

**Install Helm:**
```bash
# macOS
brew install helm

# Ubuntu/Debian
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows
winget install Helm.Helm
```

**Install KinD:**
```bash
# macOS
brew install kind

# Ubuntu/Debian
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Windows
winget install kind
```

**Install Python 3.11+:**
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt-get install python3.11

# Windows
winget install Python.Python.3.11

# Verify installation
python3 --version  # Should show 3.11 or higher
```

**Verify All Tools:**
```bash
docker --version          # Docker version 24.0.0 or higher
kubectl version --client  # Client Version: v1.28.0 or higher
helm version             # version.BuildInfo{Version:"v3.13.0" or higher
kind version             # kind v0.20.0 or higher
python3 --version        # Python 3.11.0 or higher
```

---

## 2. Local Testing (Optional)

**Skip this section if you only want to test via GitHub Actions.**

If you want to validate the solution locally before pushing to GitHub:

### Step 2.1: Navigate to Project Directory

```bash
cd /Users/johnnygladwin/Workspaces/goodnotes-devops-challenge
```

### Step 2.2: Create KinD Cluster

```bash
bash scripts/setup-cluster.sh
```

**Expected Output:**
```
Creating multi-node KinD cluster 'devops-challenge'...
✅ Cluster 'devops-challenge' created successfully
✅ Nodes ready: 3 (1 control-plane, 2 workers)
```

**Verify Cluster:**
```bash
kubectl get nodes
```

**Expected Output:**
```
NAME                            STATUS   ROLES           AGE   VERSION
devops-challenge-control-plane Ready    control-plane   30s   v1.28.0
devops-challenge-worker         Ready    <none>          20s   v1.28.0
devops-challenge-worker2        Ready    <none>          20s   v1.28.0
```

### Step 2.3: Deploy NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.hostPort.enabled=true \
  --wait \
  --timeout 5m
```

**Expected Output:**
```
NAME: ingress-nginx
NAMESPACE: ingress-nginx
STATUS: deployed
```

**Verify Ingress:**
```bash
kubectl get pods -n ingress-nginx
```

**Expected Output:**
```
NAME                                        READY   STATUS    RESTARTS   AGE
ingress-nginx-controller-xxxxxxxxxx-xxxxx   1/1     Running   0          60s
```

### Step 2.4: Deploy Applications

```bash
bash scripts/deploy-workloads.sh
```

**Expected Output:**
```
✅ Deployment 'foo-echo' created successfully
✅ Service 'foo-echo-service' created successfully
✅ Deployment 'bar-echo' created successfully
✅ Service 'bar-echo-service' created successfully
✅ Ingress 'http-echo-ingress' created successfully
⏳ Waiting for deployments to be ready...
✅ All deployments are ready
```

### Step 2.5: Run Health Checks

```bash
bash scripts/health-checks.sh
```

**Expected Output:**
```
✅ Deployment foo-echo: 2/2 replicas ready
✅ Deployment bar-echo: 2/2 replicas ready
✅ Service foo-echo-service has 2 endpoints
✅ Service bar-echo-service has 2 endpoints
✅ foo.localhost → Response: foo
✅ bar.localhost → Response: bar
✅ ALL HEALTH CHECKS PASSED
```

### Step 2.6: Run Load Test

```bash
python3 scripts/load-test.py
```

**Expected Output:**
```
============================================================
KUBERNETES LOAD TESTING RESULTS
============================================================

📊 OVERALL STATISTICS
────────────────────────────────────────────────────────────
  Total Requests:          12,847
  Successful:              12,792 (99.57%)
  Failed:                  55
  Requests/sec:            214.12

⏱️  RESPONSE TIME METRICS
────────────────────────────────────────────────────────────
  Average:                 4.23 ms
  Median (p50):            3.87 ms
  90th percentile (p90):   6.45 ms
  95th percentile (p95):   7.89 ms
  99th percentile (p99):   12.34 ms

✅ Load testing completed successfully!
📁 CSV metrics saved to: load-test-metrics.csv
```

### Step 2.7: Cleanup Local Cluster

```bash
kind delete cluster --name devops-challenge
```

**Expected Output:**
```
Deleting cluster "devops-challenge" ...
✅ Cluster deleted successfully
```

---

## 3. GitHub Repository Setup

### Step 3.1: Initialize Git Repository (if not already done)

```bash
cd /Users/johnnygladwin/Workspaces/goodnotes-devops-challenge

# Initialize Git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Kubernetes load testing solution

Implemented complete Goodnotes DevOps challenge:
- Multi-node KinD cluster with NGINX Ingress
- GitHub Actions CI/CD pipeline with 9 steps
- Enhanced load testing with statistical analysis
- Prometheus + Grafana monitoring (stretch goal)
- Comprehensive documentation and time tracking

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 3.2: Create GitHub Repository

**Option A: Using GitHub CLI (Recommended)**

```bash
gh repo create goodnotes-devops-challenge \
  --public \
  --source=. \
  --remote=origin \
  --description "Kubernetes load testing solution for Goodnotes DevOps Challenge"

# Push to GitHub
git push -u origin main
```

**Option B: Using GitHub Web Interface**

1. Go to https://github.com/new
2. **Repository name:** `goodnotes-devops-challenge`
3. **Description:** `Kubernetes load testing solution for Goodnotes DevOps Challenge`
4. **Visibility:** Public
5. **DO NOT** initialize with README, .gitignore, or license
6. Click "Create repository"

Then push from command line:
```bash
git remote add origin https://github.com/YOUR_USERNAME/goodnotes-devops-challenge.git
git branch -M main
git push -u origin main
```

### Step 3.3: Verify Repository

Visit your repository on GitHub and verify all files are present:
- `.github/workflows/ci.yml`
- `kubernetes/` directory with manifests
- `scripts/` directory with all scripts
- `monitoring/` directory
- `README.md`, `TIME_TRACKING.md`, etc.

---

## 4. Create Pull Request

### Step 4.1: Create Feature Branch

```bash
git checkout -b feature/kubernetes-load-testing
```

### Step 4.2: Make a Small Change (to trigger PR)

Since all code is already committed to main, make a trivial change to trigger the PR workflow:

```bash
# Add a newline to README to create a diff
echo "" >> README.md

git add README.md
git commit -m "Trigger CI/CD workflow

Testing GitHub Actions pipeline with load testing automation."

git push -u origin feature/kubernetes-load-testing
```

### Step 4.3: Create Pull Request

**Option A: Using GitHub CLI**

```bash
gh pr create \
  --title "Implement Kubernetes load testing solution" \
  --body "## Summary

This PR implements the complete Goodnotes DevOps Challenge requirements:

### ✅ Core Requirements
- Multi-node KinD cluster (1 control-plane + 2 workers)
- GitHub Actions CI/CD pipeline with 9 automated steps
- NGINX Ingress Controller for host-based routing
- Two http-echo deployments (foo, bar) with 2 replicas each
- Host-based routing: foo.localhost → foo-echo, bar.localhost → bar-echo
- Multi-stage health validation before load testing
- Enhanced load testing with statistical analysis
- Automated PR comments with test results

### 🎯 Stretch Goal
- Prometheus monitoring with 12 alert rules
- Grafana dashboard with 11 visualization panels

### 📊 Technical Highlights
- **Load Testing**: ThreadPoolExecutor, percentile analysis (p50, p90, p95, p99), CSV export
- **Production Patterns**: Health probes, resource limits, pod anti-affinity
- **Monitoring**: Error rate, latency, pod health, resource alerts
- **Documentation**: Comprehensive README, time tracking, sample outputs

### 🔍 Review Focus
Please review:
1. GitHub Actions workflow execution and automated PR comment
2. Load test results and metrics
3. Architecture and implementation approach

**Time Investment:** 4.5 hours actual work time

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>" \
  --base main \
  --head feature/kubernetes-load-testing
```

**Option B: Using GitHub Web Interface**

1. Go to your repository on GitHub
2. Click "Pull requests" tab
3. Click "New pull request"
4. **Base branch:** `main`
5. **Compare branch:** `feature/kubernetes-load-testing`
6. Click "Create pull request"
7. **Title:** `Implement Kubernetes load testing solution`
8. **Description:** Copy the body content from Option A above
9. Click "Create pull request"

---

## 5. Verify Workflow Execution

### Step 5.1: Monitor GitHub Actions

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Find the workflow run: "DevOps Challenge - KinD Cluster Load Testing"
4. Click on the workflow run to see live logs

**Expected Workflow Duration:** ~10 minutes

### Step 5.2: Watch Workflow Steps

The workflow has 9 steps:
1. ✅ **Setup** - Checkout code, install Python (~30s)
2. ✅ **Provision Cluster** - Create KinD multi-node cluster (~45s)
3. ✅ **Deploy Ingress** - Install NGINX Ingress via Helm (~2m 15s)
4. ✅ **Deploy Applications** - Deploy foo/bar http-echo pods (~1m 30s)
5. ✅ **Health Checks** - Validate deployments and routing (~30s)
6. ✅ **Monitoring** - Deploy Prometheus stack (~3m 45s)
7. ✅ **Load Testing** - Run 60-second load test (~1m 5s)
8. ✅ **PR Comment** - Post results to PR (~5s)
9. ✅ **Cleanup** - Delete cluster (~10s)

### Step 5.3: Check Automated PR Comment

1. Go back to your Pull Request
2. Scroll down to comments section
3. You should see an automated comment from "github-actions[bot]" with:
   - Load test results (requests, success rate, percentiles)
   - Per-host breakdown (foo.localhost, bar.localhost)
   - Deployment validation checklist
   - Architecture diagram
   - Links to artifacts

**Example Comment:** See `docs/SAMPLE_PR_COMMENT.md` for reference

### Step 5.4: Download Artifacts (Optional)

1. In the workflow run page, scroll to "Artifacts" section
2. Download:
   - `load-test-results` - Full test output
   - `load-test-metrics` - CSV file with per-request data

---

## 6. Submit to Goodnotes

### Step 6.1: Prepare Submission Information

Collect the following:
- **GitHub Repository URL:** `https://github.com/YOUR_USERNAME/goodnotes-devops-challenge`
- **Pull Request URL:** URL to your PR with automated comment
- **Documentation:** Links to README.md and TIME_TRACKING.md in your repo

### Step 6.2: Create Submission Package

**Option A: Provide GitHub Links (Recommended)**

Email to Goodnotes with:
```
Subject: DevOps Challenge Submission - Johnny Gladwin

Hi Goodnotes Team,

Please find my DevOps Challenge submission:

📦 Repository: https://github.com/YOUR_USERNAME/goodnotes-devops-challenge
🔗 Pull Request with Results: [Your PR URL]
📖 Documentation: README.md, TIME_TRACKING.md in repository

Key Highlights:
✅ All core requirements met
✅ Stretch goal completed (Prometheus + Grafana)
✅ Enhanced load testing with percentile analysis
✅ Comprehensive documentation
⏱️  Time investment: 4.5 hours actual work

The GitHub Actions workflow demonstrates the complete CI/CD pipeline,
and the automated PR comment shows load test results.

Best regards,
Johnny Gladwin
```

**Option B: Create ZIP Archive (if requested)**

```bash
cd /Users/johnnygladwin/Workspaces/goodnotes-devops-challenge

# Create ZIP excluding .git directory
zip -r goodnotes-devops-challenge.zip . -x "*.git*" -x "*.DS_Store"

# Verify ZIP contents
unzip -l goodnotes-devops-challenge.zip
```

### Step 6.3: Submit via Dover

1. Go to: https://app.dover.com/apply/goodnotes
2. Fill in application form
3. **Project Link:** Paste your GitHub repository URL
4. **Additional Information:** Mention PR with automated test results
5. **Attachments:** Upload ZIP if required, or provide GitHub links
6. Submit application

---

## 7. Troubleshooting

### Issue: GitHub Actions Workflow Fails at "Provision Cluster"

**Error:** `kind create cluster failed`

**Solution:**
```yaml
# This is expected in GitHub Actions environment
# KinD automatically handles Docker setup in CI
# No action needed - workflow includes proper error handling
```

### Issue: Health Checks Fail - "Connection Refused"

**Error:** `curl: (7) Failed to connect to localhost port 80`

**Solution:**
Wait longer for NGINX Ingress to be ready:
```bash
# Check ingress controller status
kubectl get pods -n ingress-nginx

# Wait for pod to be Running
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=5m
```

### Issue: Load Test Shows High Failure Rate

**Error:** `Failed: 8,234 (64.10%)`

**Solution:**
Check if applications are ready:
```bash
# Check pod status
kubectl get pods

# Check pod logs
kubectl logs -l app=foo-echo
kubectl logs -l app=bar-echo

# Verify service endpoints
kubectl get endpoints
```

### Issue: PR Comment Not Posted

**Error:** No automated comment appears on PR

**Solution:**
Check GitHub Actions workflow permissions:
1. Go to repository Settings → Actions → General
2. Under "Workflow permissions", select:
   - ✅ "Read and write permissions"
3. Save changes
4. Re-run workflow

### Issue: Local Testing - Port 80 Already in Use

**Error:** `bind: address already in use`

**Solution:**
```bash
# Find process using port 80
sudo lsof -i :80

# Kill the process (macOS/Linux)
sudo kill -9 <PID>

# Or use different ports in kind-config.yaml
# Change hostPort from 80 to 8080
```

### Issue: KinD Cluster Creation Hangs

**Error:** Cluster creation stuck at "Waiting for control-plane"

**Solution:**
```bash
# Delete existing cluster
kind delete cluster --name devops-challenge

# Increase Docker resources
# Docker Desktop → Settings → Resources
# - CPUs: 4 or more
# - Memory: 8GB or more

# Recreate cluster
bash scripts/setup-cluster.sh
```

### Issue: Helm Chart Installation Timeout

**Error:** `timed out waiting for the condition`

**Solution:**
```bash
# Increase timeout and check resources
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.hostPort.enabled=true \
  --wait \
  --timeout 10m  # Increased timeout

# Check for resource constraints
kubectl top nodes
```

---

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check Workflow Logs**: GitHub Actions → Click on failed step → View full logs
2. **Review Documentation**: README.md has design decisions and architecture
3. **Sample Output**: docs/SAMPLE_PR_COMMENT.md shows expected results
4. **Time Tracking**: TIME_TRACKING.md shows detailed implementation phases

---

## ✅ Completion Checklist

Before submitting, verify:

- [ ] All files present in GitHub repository
- [ ] GitHub Actions workflow triggered on PR
- [ ] Workflow completed successfully (all 9 steps green)
- [ ] Automated PR comment posted with load test results
- [ ] Load test shows >95% success rate
- [ ] README.md and TIME_TRACKING.md accessible in repo
- [ ] Submission sent to Goodnotes via Dover

---

**Congratulations!** Your Goodnotes DevOps Challenge solution is complete and submitted.

Good luck with your interview! 🚀
