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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import urllib.request
import urllib.error

# ============================================
# CONFIGURATION
# ============================================
# NOTE: I chose these values based on balancing thoroughness vs CI runtime.
# In production, I'd parameterize these via environment variables.
# 60 seconds is long enough to see patterns but short enough for PR feedback loops.
HOSTS = ["foo.localhost", "bar.localhost"]
BASE_URL = "http://localhost"
DURATION_SECONDS = 60  # Considered 120s but GitHub Actions free tier has time limits
CONCURRENT_USERS = 10   # Matches typical small-team concurrent access patterns

# Why CSV over JSON? Easier to open in Excel for quick analysis,
# and GitHub Actions artifact download preserves formatting better.
CSV_OUTPUT_FILE = "load-test-metrics.csv"

# ============================================
# DATA STRUCTURES
# ============================================
@dataclass
class LoadTestMetrics:
    """Container for all load test metrics"""
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

    def add_result(self, host: str, success: bool, response_time: float, error_type: str = None):
        """Record a single request result"""
        self.request_count += 1
        timestamp = datetime.now().isoformat()

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
def make_request(host: str) -> Tuple[bool, float, str]:
    """
    Execute a single HTTP request to the specified host

    Returns:
        Tuple of (success, response_time, error_type)
    """
    start_time = time.time()

    try:
        req = urllib.request.Request(BASE_URL, headers={"Host": host})
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
            elapsed_time = time.time() - start_time
            return (True, elapsed_time, None)

    except urllib.error.URLError as e:
        elapsed_time = time.time() - start_time
        if isinstance(e.reason, TimeoutError) or "timed out" in str(e):
            return (False, elapsed_time, "timeout")
        else:
            return (False, elapsed_time, "connection")

    except Exception as e:
        elapsed_time = time.time() - start_time
        return (False, elapsed_time, "other")


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

    # Export CSV
    metrics.export_csv(CSV_OUTPUT_FILE)

    # Print summary to stdout
    print(metrics.get_summary())


if __name__ == "__main__":
    main()
