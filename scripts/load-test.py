#!/usr/bin/env python3
"""
Enhanced Load Testing Script for Kubernetes HTTP Echo Services

Features:
- Concurrent request execution with ThreadPoolExecutor
- Real-time progress updates
- Comprehensive statistical analysis (mean, median, percentiles)
- Per-host metrics breakdown
- Failure categorization (timeout vs connection errors)
- CSV output for detailed analysis
- Resource utilization correlation (optional)
"""

import time
import random
import statistics
import csv
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
HOSTS = ["foo.localhost", "bar.localhost"]

# Dynamically detect the ingress access method (hostPort vs NodePort vs env var)
import os

def get_base_url():
    """
    Detect the correct URL to access the ingress controller.
    Priority: LOAD_TEST_URL env var > hostPort > NodePort > Docker network > cluster service
    """
    # Method 0: Use environment variable if provided (set by CI port-forward)
    env_url = os.environ.get("LOAD_TEST_URL")
    if env_url:
        print(f"  → Using LOAD_TEST_URL from environment: {env_url}", file=sys.stderr)
        return env_url

    # Method 1: Try hostPort on localhost:80 (Docker Desktop / local KinD)
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-H", "Host: foo.localhost", "http://localhost:80", "--max-time", "2"],
            capture_output=True, text=True, timeout=3
        )
        if result.stdout.strip() in ["200", "404"]:
            return "http://localhost:80"
    except:
        pass

    # Method 2: Try NodePort (GitHub Actions without port-forward)
    try:
        result = subprocess.run(
            ["kubectl", "get", "svc", "-n", "ingress-nginx", "ingress-nginx-controller",
             "-o", "jsonpath={.spec.ports[?(@.name==\"http\")].nodePort}"],
            capture_output=True, text=True, timeout=5
        )
        nodeport = result.stdout.strip()
        if nodeport and nodeport.isdigit():
            test_url = f"http://localhost:{nodeport}"
            test_result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "-H", "Host: foo.localhost", test_url, "--max-time", "2"],
                capture_output=True, text=True, timeout=3
            )
            if test_result.stdout.strip() in ["200", "404"]:
                return test_url
    except:
        pass

    # Method 3: Try via Docker network (KinD specific)
    try:
        # Use index 0 to get only the first network's IP (avoids concatenation issue)
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{(index .NetworkSettings.Networks (index (keys .NetworkSettings.Networks) 0)).IPAddress}}",
             "devops-challenge-control-plane"],
            capture_output=True, text=True, timeout=5
        )
        raw_ip = result.stdout.strip()
        import re
        # Validate it's a proper IP (each octet 0-255)
        ip_match = re.match(r'^((?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d))$', raw_ip)
        if ip_match:
            control_plane_ip = ip_match.group(1)
            # Validate connectivity before returning
            test_url = f"http://{control_plane_ip}:80"
            test_result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "-H", "Host: foo.localhost", test_url, "--max-time", "2"],
                capture_output=True, text=True, timeout=3
            )
            if test_result.stdout.strip() in ["200", "404"]:
                return test_url
    except:
        pass

    # Method 4: Cluster-internal service (last resort)
    return "http://ingress-nginx-controller.ingress-nginx.svc.cluster.local"

BASE_URL = get_base_url()
print(f"🌐 Using ingress URL: {BASE_URL}")

DURATION_SECONDS = 60   # Long enough for patterns, short enough for CI feedback loops
CONCURRENT_USERS = 10   # Simulates typical small-team concurrent access

CSV_OUTPUT_FILE = "load-test-metrics.csv"  # CSV for easy Excel analysis of artifacts

# ============================================
# DATA STRUCTURES
# ============================================
@dataclass
class LoadTestMetrics:
    """Container for all load test metrics with thread-safe operations"""
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    connection_error_count: int = 0
    other_error_count: int = 0
    response_times: List[float] = field(default_factory=list)
    host_metrics: Dict[str, Dict] = field(default_factory=lambda: {
        "foo.localhost": {
            "success": 0,
            "failure": 0,
            "timeout": 0,
            "connection_error": 0,
            "times": []
        },
        "bar.localhost": {
            "success": 0,
            "failure": 0,
            "timeout": 0,
            "connection_error": 0,
            "times": []
        }
    })
    csv_rows: List[Dict] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def add_result(self, host: str, success: bool, response_time: float, error_type: str = None):
        """Record a single request result (thread-safe)"""
        timestamp = datetime.now().isoformat()

        with self._lock:
            self.request_count += 1

            if success:
                self.success_count += 1
                self.response_times.append(response_time)
                self.host_metrics[host]["success"] += 1
                self.host_metrics[host]["times"].append(response_time)
                status = "success"
            else:
                self.failure_count += 1
                self.host_metrics[host]["failure"] += 1

                # Categorize failure type
                if error_type == "timeout":
                    self.timeout_count += 1
                    self.host_metrics[host]["timeout"] += 1
                    status = "timeout"
                elif error_type == "connection":
                    self.connection_error_count += 1
                    self.host_metrics[host]["connection_error"] += 1
                    status = "connection_error"
                else:
                    self.other_error_count += 1
                    status = "other_error"

            # Record for CSV export
            self.csv_rows.append({
                "timestamp": timestamp,
                "host": host,
                "status": status,
                "response_time_ms": round(response_time * 1000, 2) if success else None,
                "error_type": error_type if not success else None
            })

    def calculate_percentile(self, percentile: float, data: List[float]) -> float:
        """Calculate percentile value from sorted data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_summary(self) -> str:
        """Generate comprehensive summary report"""
        if not self.response_times:
            return "⚠️  No successful requests to analyze"

        avg_time = statistics.mean(self.response_times)
        median_time = statistics.median(self.response_times)
        min_time = min(self.response_times)
        max_time = max(self.response_times)
        p50 = self.calculate_percentile(50, self.response_times)
        p90 = self.calculate_percentile(90, self.response_times)
        p95 = self.calculate_percentile(95, self.response_times)
        p99 = self.calculate_percentile(99, self.response_times)

        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        requests_per_sec = self.request_count / DURATION_SECONDS

        report = f"""
{'='*60}
KUBERNETES LOAD TESTING RESULTS
{'='*60}

📊 OVERALL STATISTICS
{'─'*60}
  Total Requests:          {self.request_count:,}
  Successful:              {self.success_count:,} ({success_rate:.2f}%)
  Failed:                  {self.failure_count:,}
  Requests/sec:            {requests_per_sec:.2f}
  Test Duration:           {DURATION_SECONDS}s
  Concurrent Users:        {CONCURRENT_USERS}

⏱️  RESPONSE TIME METRICS
{'─'*60}
  Average:                 {avg_time*1000:.2f} ms
  Median (p50):            {median_time*1000:.2f} ms
  90th percentile (p90):   {p90*1000:.2f} ms
  95th percentile (p95):   {p95*1000:.2f} ms
  99th percentile (p99):   {p99*1000:.2f} ms
  Min:                     {min_time*1000:.2f} ms
  Max:                     {max_time*1000:.2f} ms
"""

        # Add failure breakdown if there were failures
        if self.failure_count > 0:
            report += f"""
❌ FAILURE BREAKDOWN
{'─'*60}
  Timeouts:                {self.timeout_count:,}
  Connection Errors:       {self.connection_error_count:,}
  Other Errors:            {self.other_error_count:,}
"""

        # Per-host breakdown
        report += f"""
🎯 PER-HOST BREAKDOWN
{'─'*60}
"""
        for host, metrics in self.host_metrics.items():
            total_host_requests = metrics["success"] + metrics["failure"]
            if total_host_requests == 0:
                continue

            host_success_rate = (metrics["success"] / total_host_requests * 100)
            host_avg_time = statistics.mean(metrics["times"]) if metrics["times"] else 0

            report += f"""
  {host}:
    Requests:              {total_host_requests:,}
    Success:               {metrics["success"]:,} ({host_success_rate:.2f}%)
    Failures:              {metrics["failure"]:,}
      - Timeouts:          {metrics["timeout"]:,}
      - Connection Errors: {metrics["connection_error"]:,}
    Avg Response Time:     {host_avg_time*1000:.2f} ms
"""

        report += f"""
{'='*60}
✅ Load testing completed successfully!
📁 CSV metrics saved to: {CSV_OUTPUT_FILE}
{'='*60}
"""
        return report

    def export_csv(self, filename: str):
        """Export detailed metrics to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'host', 'status', 'response_time_ms', 'error_type']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_rows)
        print(f"📊 Exported {len(self.csv_rows)} metrics to {filename}")


# ============================================
# REQUEST EXECUTION
# ============================================
_debug_lock = Lock()
_debug_printed = False

def make_request(host: str) -> Tuple[bool, float, str]:
    """
    Execute a single HTTP request using curl (matches health-checks.sh approach).
    This ensures consistent behavior between health checks and load testing.
    """
    global _debug_printed
    start_time = time.time()

    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-H", f"Host: {host}", BASE_URL, "--max-time", "5"],
            capture_output=True, text=True, timeout=6
        )
        elapsed_time = time.time() - start_time
        http_code = result.stdout.strip()

        # Debug: print first response code to stderr (thread-safe)
        with _debug_lock:
            if not _debug_printed:
                print(f"  → First curl response: http_code='{http_code}', stderr='{result.stderr.strip()[:100]}'", file=sys.stderr)
                _debug_printed = True

        # Accept any 2xx or 3xx response as success
        if http_code.startswith("2") or http_code.startswith("3"):
            return (True, elapsed_time, None)
        # Handle curl connection failures (http_code "000" or empty means network/DNS failure)
        elif http_code == "000" or http_code == "":
            return (False, elapsed_time, "connection")
        else:
            return (False, elapsed_time, f"http_{http_code}")

    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        return (False, elapsed_time, "timeout")

    except Exception:
        elapsed_time = time.time() - start_time
        return (False, elapsed_time, "connection")


def worker(worker_id: int, stop_time: float, metrics: LoadTestMetrics, progress_tracker: dict):
    """
    Worker thread that continuously makes requests until stop_time

    Args:
        worker_id: Unique identifier for this worker
        stop_time: Unix timestamp when to stop making requests
        metrics: Shared metrics object
        progress_tracker: Shared dict for progress updates
    """
    local_requests = 0

    while time.time() < stop_time:
        # Randomly select host
        host = random.choice(HOSTS)

        # Make request
        success, response_time, error_type = make_request(host)

        # Record result
        metrics.add_result(host, success, response_time, error_type)
        local_requests += 1

        # Update progress tracker
        progress_tracker[worker_id] = local_requests

        # Realistic user think time (50-200ms between requests)
        time.sleep(random.uniform(0.05, 0.2))


def print_progress(progress_tracker: dict, start_time: float, duration: int):
    """Print real-time progress updates"""
    while time.time() - start_time < duration:
        time.sleep(5)  # Update every 5 seconds
        elapsed = int(time.time() - start_time)
        total_requests = sum(progress_tracker.values())
        req_per_sec = total_requests / elapsed if elapsed > 0 else 0
        remaining = duration - elapsed

        print(f"⏳ Progress: {elapsed}s / {duration}s | "
              f"Requests: {total_requests:,} | "
              f"Rate: {req_per_sec:.2f} req/s | "
              f"Remaining: {remaining}s",
              file=sys.stderr)


# ============================================
# RESOURCE UTILIZATION
# ============================================
def get_resource_utilization() -> Dict[str, Dict]:
    """
    Capture pod resource utilization using kubectl top.
    Returns CPU and memory usage for foo-echo and bar-echo pods.
    """
    resource_data = {
        "foo-echo": {"cpu": "N/A", "memory": "N/A", "pods": []},
        "bar-echo": {"cpu": "N/A", "memory": "N/A", "pods": []}
    }

    try:
        # Get pod metrics using kubectl top
        result = subprocess.run(
            ["kubectl", "top", "pods", "-l", "component=http-echo", "--no-headers"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            foo_cpu_total, foo_mem_total, foo_count = 0, 0, 0
            bar_cpu_total, bar_mem_total, bar_count = 0, 0, 0

            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    pod_name = parts[0]
                    cpu = parts[1]  # e.g., "45m"
                    memory = parts[2]  # e.g., "52Mi"

                    # Parse CPU (convert to millicores)
                    cpu_value = int(cpu.replace('m', '')) if 'm' in cpu else int(cpu) * 1000

                    # Parse memory (convert to Mi)
                    if 'Mi' in memory:
                        mem_value = int(memory.replace('Mi', ''))
                    elif 'Gi' in memory:
                        mem_value = int(memory.replace('Gi', '')) * 1024
                    elif 'Ki' in memory:
                        mem_value = int(memory.replace('Ki', '')) // 1024
                    else:
                        mem_value = 0

                    if 'foo-echo' in pod_name:
                        foo_cpu_total += cpu_value
                        foo_mem_total += mem_value
                        foo_count += 1
                        resource_data["foo-echo"]["pods"].append({
                            "name": pod_name, "cpu": cpu, "memory": memory
                        })
                    elif 'bar-echo' in pod_name:
                        bar_cpu_total += cpu_value
                        bar_mem_total += mem_value
                        bar_count += 1
                        resource_data["bar-echo"]["pods"].append({
                            "name": pod_name, "cpu": cpu, "memory": memory
                        })

            # Calculate averages
            if foo_count > 0:
                resource_data["foo-echo"]["cpu"] = f"{foo_cpu_total // foo_count}m"
                resource_data["foo-echo"]["memory"] = f"{foo_mem_total // foo_count}Mi"
            if bar_count > 0:
                resource_data["bar-echo"]["cpu"] = f"{bar_cpu_total // bar_count}m"
                resource_data["bar-echo"]["memory"] = f"{bar_mem_total // bar_count}Mi"

    except subprocess.TimeoutExpired:
        print("  ⚠️ kubectl top timed out (metrics-server may not be ready)", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️ Could not get resource metrics: {e}", file=sys.stderr)

    return resource_data


def get_resource_limits() -> Dict[str, Dict]:
    """Get configured resource limits for pods."""
    limits = {
        "foo-echo": {"cpu_limit": "200m", "memory_limit": "128Mi"},
        "bar-echo": {"cpu_limit": "200m", "memory_limit": "128Mi"}
    }

    try:
        for deployment in ["foo-echo", "bar-echo"]:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment, "-o",
                 "jsonpath={.spec.template.spec.containers[0].resources.limits.cpu},{.spec.template.spec.containers[0].resources.limits.memory}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) == 2:
                    limits[deployment]["cpu_limit"] = parts[0]
                    limits[deployment]["memory_limit"] = parts[1]
    except Exception:
        pass  # Use defaults

    return limits


def format_resource_report(resources: Dict, limits: Dict) -> str:
    """Format resource utilization as part of the report."""
    report = f"""
📈 RESOURCE UTILIZATION (during load test)
{'─'*60}
"""
    for deployment in ["foo-echo", "bar-echo"]:
        cpu_usage = resources[deployment]["cpu"]
        mem_usage = resources[deployment]["memory"]
        cpu_limit = limits[deployment]["cpu_limit"]
        mem_limit = limits[deployment]["memory_limit"]

        # Calculate percentages if we have valid data
        cpu_pct = "N/A"
        mem_pct = "N/A"

        if cpu_usage != "N/A" and 'm' in cpu_usage and 'm' in cpu_limit:
            try:
                cpu_val = int(cpu_usage.replace('m', ''))
                cpu_lim = int(cpu_limit.replace('m', ''))
                if cpu_lim > 0:
                    cpu_pct = f"{(cpu_val / cpu_lim * 100):.1f}%"
            except ValueError:
                pass

        if mem_usage != "N/A" and 'Mi' in mem_usage and 'Mi' in mem_limit:
            try:
                mem_val = int(mem_usage.replace('Mi', ''))
                mem_lim = int(mem_limit.replace('Mi', ''))
                if mem_lim > 0:
                    mem_pct = f"{(mem_val / mem_lim * 100):.1f}%"
            except ValueError:
                pass

        report += f"""
  {deployment}:
    CPU:     {cpu_usage} / {cpu_limit} ({cpu_pct})
    Memory:  {mem_usage} / {mem_limit} ({mem_pct})
"""
        # Show per-pod breakdown if available
        if resources[deployment]["pods"]:
            report += "    Pods:\n"
            for pod in resources[deployment]["pods"]:
                report += f"      - {pod['name']}: CPU={pod['cpu']}, Mem={pod['memory']}\n"

    return report


# ============================================
# MAIN EXECUTION
# ============================================
def main():
    """Main load testing execution"""
    print(f"""
{'='*60}
STARTING LOAD TEST
{'='*60}
Configuration:
  Hosts:              {', '.join(HOSTS)}
  Duration:           {DURATION_SECONDS} seconds
  Concurrent Users:   {CONCURRENT_USERS}
  Target URL:         {BASE_URL}
{'='*60}
""", file=sys.stderr)

    metrics = LoadTestMetrics()
    progress_tracker = {i: 0 for i in range(CONCURRENT_USERS)}
    start_time = time.time()
    stop_time = start_time + DURATION_SECONDS

    # Start progress monitoring thread
    from threading import Thread
    progress_thread = Thread(target=print_progress, args=(progress_tracker, start_time, DURATION_SECONDS))
    progress_thread.daemon = True
    progress_thread.start()

    # Execute load test with thread pool
    print(f"🚀 Starting {CONCURRENT_USERS} concurrent workers...\n", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [
            executor.submit(worker, i, stop_time, metrics, progress_tracker)
            for i in range(CONCURRENT_USERS)
        ]

        # Wait for all workers to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ Worker error: {e}", file=sys.stderr)

    # Wait for progress thread to finish
    progress_thread.join(timeout=1)

    print(f"\n{'='*60}", file=sys.stderr)
    print("🏁 Load testing completed!", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Capture resource utilization (stretch goal)
    print("📊 Capturing resource utilization metrics...", file=sys.stderr)
    resources = get_resource_utilization()
    limits = get_resource_limits()
    resource_report = format_resource_report(resources, limits)

    # Export CSV
    metrics.export_csv(CSV_OUTPUT_FILE)

    # Print summary to stdout (includes resource utilization)
    print(metrics.get_summary())
    print(resource_report)


if __name__ == "__main__":
    main()
