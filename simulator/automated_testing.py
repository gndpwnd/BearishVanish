"""
Automated Strategy Testing Framework
Run multiple simulations with different configurations and compare results
Auto-benchmarks system if no config exists, uses optimal worker counts
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd

BENCHMARK_CONFIG = Path('./benchmark_config.json')

class AutomatedTesting:
    def __init__(self):
        self.results_dir = Path('./test_results')
        self.results_dir.mkdir(exist_ok=True)
        self.test_configs = []
        self.results = []
        self.download_workers = 10
        self.db_workers = 10
        
        # Check if benchmark exists, if not run it
        self._ensure_benchmark()
        
    def _ensure_benchmark(self):
        """Ensure system is benchmarked before running tests"""
        if not BENCHMARK_CONFIG.exists():
            print("\n" + "="*70)
            print("NO BENCHMARK FOUND - RUNNING SYSTEM BENCHMARK")
            print("="*70)
            print("This will take 1-2 minutes but only needs to run once...")
            
            # Run benchmark
            result = subprocess.run(
                ['python', 'simulator.py', '--benchmark'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("⚠️  Benchmark failed, using default worker counts (10 each)")
                self.download_workers = 10
                self.db_workers = 10
                return
        
        # Load benchmark results
        try:
            with open(BENCHMARK_CONFIG, 'r') as f:
                config = json.load(f)
                
            if 'recommendations' in config:
                self.download_workers = config['recommendations']['download_workers']
                self.db_workers = config['recommendations']['db_workers']
                
                print(f"\n✅ Using benchmarked worker counts:")
                print(f"   Download workers: {self.download_workers}")
                print(f"   Database workers: {self.db_workers}")
            else:
                print("⚠️  Invalid benchmark config, using defaults")
                self.download_workers = 10
                self.db_workers = 10
                
        except Exception as e:
            print(f"⚠️  Could not load benchmark: {e}")
            self.download_workers = 10
            self.db_workers = 10
    
    def add_test_config(self, name, universe=None, tickers=None, description=""):
        """
        Add a test configuration
        
        Args:
            name: Test name (e.g., "sp500_test")
            universe: Universe to test (e.g., "sp500")
            tickers: List of tickers to test (e.g., ["AAPL", "MSFT"])
            description: Test description
        """
        config = {
            'name': name,
            'universe': universe,
            'tickers': tickers,
            'description': description,
            'timestamp': None,
            'status': 'pending'
        }
        self.test_configs.append(config)
        return config
    
    def download_data_for_tests(self):
        """Download data needed for all test configurations"""
        print("\n" + "="*70)
        print("DOWNLOADING DATA FOR ALL TESTS")
        print("="*70)
        
        # Collect all unique symbols needed
        all_universes = set()
        all_tickers = set()
        
        for config in self.test_configs:
            if config['universe']:
                all_universes.add(config['universe'])
            if config['tickers']:
                all_tickers.update(config['tickers'])
        
        # Download by universe (more efficient)
        for universe in all_universes:
            print(f"\n📦 Downloading {universe} universe data...")
            cmd = [
                'python', 'simulator.py', 
                '--download', 
                '--universe', universe,
                '--download-workers', str(self.download_workers)
            ]
            
            print(f"   Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Downloaded {universe} data")
            else:
                print(f"  ❌ Failed to download {universe} data")
                print(result.stderr)
        
        # Download individual tickers if specified
        if all_tickers:
            print(f"\n📦 Downloading specific tickers: {', '.join(all_tickers)}")
            ticker_str = ','.join(all_tickers)
            cmd = [
                'python', 'simulator.py', 
                '--download', 
                '--tickers', ticker_str,
                '--download-workers', str(self.download_workers)
            ]
            
            print(f"   Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Downloaded ticker data")
            else:
                print(f"  ❌ Failed to download ticker data")
                print(result.stderr)
        
        print("\n" + "="*70)
        print("DATA DOWNLOAD COMPLETE")
        print("="*70)
    
    def run_test(self, config):
        """
        Run a single test configuration
        
        Args:
            config: Test configuration dictionary
            
        Returns:
            dict with test results
        """
        print(f"\n{'='*70}")
        print(f"RUNNING TEST: {config['name']}")
        print(f"{'='*70}")
        print(f"Description: {config['description']}")
        
        # Build command
        cmd = [
            'python', 'simulator.py',
            '--db-workers', str(self.db_workers)
        ]
        
        if config['universe']:
            cmd.extend(['--universe', config['universe']])
        
        config['timestamp'] = datetime.now().isoformat()
        
        try:
            # Run simulation
            print(f"Starting simulation...")
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                config['status'] = 'completed'
                print(f"✅ Test completed successfully")
            else:
                config['status'] = 'failed'
                print(f"❌ Test failed")
                print(result.stderr)
            
            # Store output
            config['stdout'] = result.stdout
            config['stderr'] = result.stderr
            config['returncode'] = result.returncode
            
        except subprocess.TimeoutExpired:
            config['status'] = 'timeout'
            print(f"❌ Test timed out after 10 minutes")
        except Exception as e:
            config['status'] = 'error'
            config['error'] = str(e)
            print(f"❌ Test error: {e}")
        
        return config
    
    def run_all_tests(self, download_first=True):
        """
        Run all configured tests
        
        Args:
            download_first: Whether to download data before testing
            
        Returns:
            list of test results
        """
        print("\n" + "="*70)
        print("AUTOMATED TESTING SUITE")
        print("="*70)
        print(f"Total tests: {len(self.test_configs)}")
        print(f"Worker configuration:")
        print(f"  Download workers: {self.download_workers}")
        print(f"  Database workers: {self.db_workers}")
        
        # Download data if requested
        if download_first:
            self.download_data_for_tests()
        
        # Run each test
        self.results = []
        for i, config in enumerate(self.test_configs, 1):
            print(f"\n[{i}/{len(self.test_configs)}] Running: {config['name']}")
            result = self.run_test(config)
            self.results.append(result)
        
        # Generate summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        return self.results
    
    def print_summary(self):
        """Print summary of test results"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        completed = sum(1 for r in self.results if r['status'] == 'completed')
        failed = sum(1 for r in self.results if r['status'] == 'failed')
        timeout = sum(1 for r in self.results if r['status'] == 'timeout')
        error = sum(1 for r in self.results if r['status'] == 'error')
        
        print(f"\nTotal tests: {len(self.results)}")
        print(f"  ✅ Completed: {completed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⏱️  Timeout: {timeout}")
        print(f"  🔥 Error: {error}")
        
        print(f"\nDetailed Results:")
        for result in self.results:
            status_emoji = {
                'completed': '✅',
                'failed': '❌',
                'timeout': '⏱️',
                'error': '🔥'
            }.get(result['status'], '❓')
            
            print(f"  {status_emoji} {result['name']}: {result['status']}")
        
        print("="*70)
    
    def save_results(self):
        """Save test results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.results_dir / f'test_results_{timestamp}.json'
        
        # Clean results for JSON serialization
        clean_results = []
        for result in self.results:
            clean_result = {
                'name': result['name'],
                'universe': result.get('universe'),
                'tickers': result.get('tickers'),
                'description': result['description'],
                'status': result['status'],
                'timestamp': result['timestamp'],
                'returncode': result.get('returncode')
            }
            clean_results.append(clean_result)
        
        # Add system info
        summary = {
            'test_suite_timestamp': timestamp,
            'total_tests': len(self.results),
            'completed': sum(1 for r in self.results if r['status'] == 'completed'),
            'failed': sum(1 for r in self.results if r['status'] != 'completed'),
            'worker_config': {
                'download_workers': self.download_workers,
                'db_workers': self.db_workers
            },
            'results': clean_results
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        return output_file
    
    def compare_strategies(self):
        """
        Compare strategy performance across different universes
        This would parse simulation output and create comparison tables
        """
        print("\n" + "="*70)
        print("STRATEGY COMPARISON")
        print("="*70)
        print("(Feature coming soon - requires strategy result parsing)")
        print("="*70)


def create_standard_test_suite():
    """
    Create a standard test suite for common scenarios
    
    Returns:
        AutomatedTesting instance with configured tests
    """
    testing = AutomatedTesting()
    
    # Test 1: S&P 500
    testing.add_test_config(
        name="sp500_full",
        universe="sp500",
        description="Full S&P 500 universe test (502 stocks)"
    )
    
    # Test 2: NASDAQ 100
    testing.add_test_config(
        name="nasdaq100_full",
        universe="nasdaq100",
        description="Full NASDAQ 100 universe test (101 stocks)"
    )
    
    # Test 3: Russell 3000
    testing.add_test_config(
        name="russell3000_full",
        universe="russell3000",
        description="Full Russell 3000 universe test (2500+ stocks)"
    )
    
    return testing


def create_quick_test_suite():
    """
    Create a quick test suite for rapid testing
    
    Returns:
        AutomatedTesting instance with quick tests
    """
    testing = AutomatedTesting()
    
    # Quick test: Just S&P 500
    testing.add_test_config(
        name="quick_sp500",
        universe="sp500",
        description="Quick test with S&P 500 (502 stocks)"
    )
    
    return testing


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Strategy Testing')
    parser.add_argument('--suite', type=str, choices=['standard', 'quick', 'custom'],
                       default='standard', help='Test suite to run')
    parser.add_argument('--no-download', action='store_true',
                       help='Skip data download (assumes data exists)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare strategy results')
    parser.add_argument('--force-benchmark', action='store_true',
                       help='Force re-run of system benchmark')
    
    args = parser.parse_args()
    
    # Force benchmark if requested
    if args.force_benchmark:
        print("\n" + "="*70)
        print("FORCING SYSTEM BENCHMARK")
        print("="*70)
        
        result = subprocess.run(
            ['python', 'simulator.py', '--benchmark'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Benchmark completed successfully")
        else:
            print("❌ Benchmark failed")
            print(result.stderr)
    
    # Create test suite
    if args.suite == 'standard':
        print("\n" + "="*70)
        print("STANDARD TEST SUITE")
        print("="*70)
        print("Running 3 universe tests (S&P 500, NASDAQ 100, Russell 3000)")
        print("Estimated time: 20-30 minutes")
        testing = create_standard_test_suite()
    elif args.suite == 'quick':
        print("\n" + "="*70)
        print("QUICK TEST SUITE")
        print("="*70)
        print("Running 1 universe test (S&P 500)")
        print("Estimated time: 5-10 minutes")
        testing = create_quick_test_suite()
    else:
        print("\n" + "="*70)
        print("CUSTOM TEST SUITE")
        print("="*70)
        testing = AutomatedTesting()
        # Add custom tests here
        testing.add_test_config(
            name="custom_test",
            universe="sp500",
            description="Custom test configuration"
        )
    
    # Run tests
    results = testing.run_all_tests(download_first=not args.no_download)
    
    # Compare if requested
    if args.compare:
        testing.compare_strategies()
    
    print("\n✅ Automated testing complete!")
    print(f"\n📊 Results summary:")
    print(f"   Total: {len(results)}")
    print(f"   Completed: {sum(1 for r in results if r['status'] == 'completed')}")
    print(f"   Failed: {sum(1 for r in results if r['status'] != 'completed')}")