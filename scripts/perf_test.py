#!/usr/bin/env python3
"""
Performance Testing Script for RepoDiscoverAI
Usage: python scripts/perf_test.py [options]

Tests:
- Load testing with increasing concurrency
- Endpoint response times
- Database query performance
- Cache effectiveness
"""

import asyncio
import time
import statistics
import aiohttp
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class TestResult:
    """Store test results for a single request"""
    endpoint: str
    status_code: int
    response_time_ms: float
    timestamp: float
    error: Optional[str] = None


@dataclass
class TestSummary:
    """Aggregate test results"""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    min_response_ms: float
    max_response_ms: float
    avg_response_ms: float
    p50_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    requests_per_second: float


class PerformanceTester:
    """Performance testing suite for RepoDiscoverAI"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def setup(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def teardown(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, endpoint: str, method: str = "GET") -> TestResult:
        """Make a single request and record results"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url) as response:
                response_time = (time.time() - start_time) * 1000
                return TestResult(
                    endpoint=endpoint,
                    status_code=response.status,
                    response_time_ms=response_time,
                    timestamp=time.time()
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=response_time,
                timestamp=time.time(),
                error=str(e)
            )
    
    async def load_test(
        self,
        endpoint: str,
        concurrency: int = 10,
        requests_per_client: int = 100
    ) -> List[TestResult]:
        """Run load test with specified concurrency"""
        print(f"🚀 Load testing {endpoint} with {concurrency} concurrent clients, {requests_per_client} requests each")
        
        tasks = []
        for _ in range(concurrency):
            for _ in range(requests_per_client):
                tasks.append(self.make_request(endpoint))
        
        results = await asyncio.gather(*tasks)
        self.results.extend(results)
        return results
    
    async def stress_test(self, endpoint: str, duration_seconds: int = 60) -> List[TestResult]:
        """Run stress test for specified duration"""
        print(f"💥 Stress testing {endpoint} for {duration_seconds} seconds")
        
        start_time = time.time()
        results = []
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            tasks = [self.make_request(endpoint) for _ in range(10)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            request_count += len(batch_results)
            
            # Report progress every 10 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 10 == 0:
                rps = request_count / elapsed if elapsed > 0 else 0
                print(f"   Progress: {int(elapsed)}s - {request_count} requests - {rps:.1f} req/s")
        
        self.results.extend(results)
        return results
    
    def calculate_summary(self, endpoint: str) -> TestSummary:
        """Calculate summary statistics for an endpoint"""
        endpoint_results = [r for r in self.results if r.endpoint == endpoint]
        
        if not endpoint_results:
            return None
        
        successful = [r for r in endpoint_results if r.status_code < 400]
        failed = [r for r in endpoint_results if r.status_code >= 400 or r.error]
        
        response_times = [r.response_time_ms for r in successful]
        
        if not response_times:
            return TestSummary(
                endpoint=endpoint,
                total_requests=len(endpoint_results),
                successful_requests=0,
                failed_requests=len(endpoint_results),
                success_rate=0,
                min_response_ms=0,
                max_response_ms=0,
                avg_response_ms=0,
                p50_response_ms=0,
                p95_response_ms=0,
                p99_response_ms=0,
                requests_per_second=0
            )
        
        total_time = max(r.timestamp for r in endpoint_results) - min(r.timestamp for r in endpoint_results)
        rps = len(endpoint_results) / total_time if total_time > 0 else 0
        
        return TestSummary(
            endpoint=endpoint,
            total_requests=len(endpoint_results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            success_rate=len(successful) / len(endpoint_results) * 100,
            min_response_ms=min(response_times),
            max_response_ms=max(response_times),
            avg_response_ms=statistics.mean(response_times),
            p50_response_ms=statistics.quantiles(response_times, n=100)[49],
            p95_response_ms=statistics.quantiles(response_times, n=100)[94],
            p99_response_ms=statistics.quantiles(response_times, n=100)[98],
            requests_per_second=rps
        )
    
    def print_report(self):
        """Print performance test report"""
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE TEST REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().isoformat()}")
        print(f"Base URL: {self.base_url}")
        print(f"Total Requests: {len(self.results)}")
        print()
        
        # Group by endpoint
        endpoints = set(r.endpoint for r in self.results)
        
        for endpoint in sorted(endpoints):
            summary = self.calculate_summary(endpoint)
            if summary:
                print(f"\n📍 Endpoint: {endpoint}")
                print("-" * 60)
                print(f"  Total Requests:     {summary.total_requests:,}")
                print(f"  Successful:         {summary.successful_requests:,} ({summary.success_rate:.1f}%)")
                print(f"  Failed:             {summary.failed_requests:,}")
                print(f"  Throughput:         {summary.requests_per_second:.1f} req/s")
                print(f"  Response Times:")
                print(f"    Min:              {summary.min_response_ms:.2f} ms")
                print(f"    Avg:              {summary.avg_response_ms:.2f} ms")
                print(f"    P50:              {summary.p50_response_ms:.2f} ms")
                print(f"    P95:              {summary.p95_response_ms:.2f} ms")
                print(f"    P99:              {summary.p99_response_ms:.2f} ms")
                print(f"    Max:              {summary.max_response_ms:.2f} ms")
        
        print("\n" + "=" * 80)
    
    def save_report(self, filename: str = "perf_report.json"):
        """Save report to JSON file"""
        endpoints = set(r.endpoint for r in self.results)
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "base_url": self.base_url,
            "total_requests": len(self.results),
            "endpoints": {}
        }
        
        for endpoint in sorted(endpoints):
            summary = self.calculate_summary(endpoint)
            if summary:
                report["endpoints"][endpoint] = {
                    "total_requests": summary.total_requests,
                    "successful_requests": summary.successful_requests,
                    "failed_requests": summary.failed_requests,
                    "success_rate": summary.success_rate,
                    "requests_per_second": summary.requests_per_second,
                    "response_times": {
                        "min": summary.min_response_ms,
                        "avg": summary.avg_response_ms,
                        "p50": summary.p50_response_ms,
                        "p95": summary.p95_response_ms,
                        "p99": summary.p99_response_ms,
                        "max": summary.max_response_ms
                    }
                }
        
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Report saved to {filename}")


async def main():
    """Run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RepoDiscoverAI Performance Testing")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent clients")
    parser.add_argument("--requests", type=int, default=100, help="Requests per client")
    parser.add_argument("--endpoint", default="/api/trending", help="Endpoint to test")
    parser.add_argument("--output", default="perf_report.json", help="Output file")
    args = parser.parse_args()
    
    tester = PerformanceTester(args.url)
    
    try:
        await tester.setup()
        
        # Run load test
        endpoints_to_test = [
            "/health",
            "/api/trending",
            "/api/search?q=machine+learning",
            "/api/repositories/1"
        ]
        
        for endpoint in endpoints_to_test:
            await tester.load_test(endpoint, args.concurrency, args.requests)
        
        # Print and save report
        tester.print_report()
        tester.save_report(args.output)
        
    finally:
        await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
