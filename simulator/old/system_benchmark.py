"""
Simplified System Benchmark
Only benchmarks what actually matters: Network download speeds
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BENCHMARK_CONFIG = Path('./benchmark_config.json')

class SystemBenchmark:
    def __init__(self, data_manager, universe_manager):
        """Initialize benchmark with data manager and universe manager"""
        self.data_manager = data_manager
        self.universe_manager = universe_manager
        self.results = {}
        
    def benchmark_network(self, test_symbols=None, num_tests=10):
        """
        Benchmark network speed by downloading test stocks
        This determines optimal worker count for API downloads
        """
        print("\n" + "="*70)
        print("BENCHMARKING NETWORK DOWNLOAD SPEED")
        print("="*70)
        
        # Get test symbols
        if test_symbols is None:
            all_symbols = self.universe_manager.get_approved_tickers('sp500')
            if not all_symbols:
                print("❌ No symbols available for network test")
                return None
            test_symbols = all_symbols[:num_tests]
        
        print(f"Testing download speed with {len(test_symbols)} stocks...")
        
        end_date = datetime.now().replace(tzinfo=None)
        start_date = (end_date - timedelta(days=30)).replace(tzinfo=None)
        
        # Test 1: Single-threaded download
        print("\n1️⃣ Testing single-threaded downloads...")
        start_time = time.time()
        
        successful = 0
        for symbol in test_symbols[:5]:
            try:
                self.data_manager.fetch_from_api(symbol, start_date, end_date)
                successful += 1
            except Exception as e:
                print(f"  ⚠️  {symbol} failed: {e}")
        
        single_thread_time = time.time() - start_time
        avg_time_per_stock = single_thread_time / successful if successful > 0 else 0
        
        print(f"  ✅ Downloaded {successful}/5 stocks in {single_thread_time:.2f}s")
        print(f"  📊 Average: {avg_time_per_stock:.2f}s per stock")
        
        # Test 2: Multi-threaded download (test different worker counts)
        print("\n2️⃣ Testing multi-threaded downloads...")
        
        def download_test(symbol):
            try:
                self.data_manager.fetch_from_api(symbol, start_date, end_date)
                return True
            except:
                return False
        
        best_workers = 10
        best_time = float('inf')
        
        for workers in [5, 10, 15, 20]:
            print(f"\n   Testing {workers} workers...")
            start_time = time.time()
            
            successful = 0
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(download_test, sym): sym 
                          for sym in test_symbols[5:5+min(workers, len(test_symbols)-5)]}
                for future in as_completed(futures):
                    if future.result():
                        successful += 1
            
            elapsed = time.time() - start_time
            if successful > 0 and elapsed < best_time:
                best_time = elapsed
                best_workers = workers
            
            print(f"   ✅ {successful} stocks in {elapsed:.2f}s")
        
        speedup = single_thread_time / best_time if best_time > 0 else 1
        
        # Calculate recommended workers
        cpu_count = os.cpu_count() or 4
        recommended_workers = min(best_workers, cpu_count * 4, 50)
        
        results = {
            'single_thread_time': single_thread_time,
            'best_parallel_time': best_time,
            'best_workers': best_workers,
            'avg_time_per_stock': avg_time_per_stock,
            'speedup': speedup,
            'recommended_download_workers': recommended_workers,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📊 NETWORK BENCHMARK RESULTS:")
        print(f"  Average time per stock: {avg_time_per_stock:.2f}s")
        print(f"  Best parallel speedup: {speedup:.2f}x (with {best_workers} workers)")
        print(f"  Recommended download workers: {recommended_workers}")
        
        return results
    
    def get_system_info(self):
        """Get basic system info (no benchmarking)"""
        cpu_count = os.cpu_count() or 4
        
        info = {
            'cpu_count': cpu_count,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            info.update({
                'cpu_percent': cpu_percent,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'memory_percent': memory.percent
            })
        except ImportError:
            print("  ℹ️  Install 'psutil' for detailed system info: pip install psutil")
        
        return info
    
    def run_benchmark(self):
        """
        Run simplified benchmark (network only)
        """
        print("\n" + "="*70)
        print("RUNNING SYSTEM BENCHMARK")
        print("="*70)
        print("This will take about 30-60 seconds...")
        
        # 1. System info
        print("\n" + "="*70)
        print("SYSTEM INFORMATION")
        print("="*70)
        
        system_info = self.get_system_info()
        
        print(f"  CPU Cores: {system_info['cpu_count']}")
        if 'cpu_percent' in system_info:
            print(f"  CPU Usage: {system_info['cpu_percent']}%")
            print(f"  Memory Total: {system_info['memory_total_gb']:.1f} GB")
            print(f"  Memory Available: {system_info['memory_available_gb']:.1f} GB")
        
        # 2. Network speed
        network_results = self.benchmark_network()
        
        if not network_results:
            print("❌ Network benchmark failed")
            return None
        
        # Final recommendations
        recommended_download = network_results['recommended_download_workers']
        
        results = {
            'system': system_info,
            'network': network_results,
            'recommendations': {
                'download_workers': recommended_download,
                'notes': 'Network workers for API downloads. Database uses batch loading (no workers needed).'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Save results
        self.save_benchmark(results)
        
        # Print summary
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        print(f"\n💻 SYSTEM SPECS:")
        print(f"  CPU Cores: {system_info['cpu_count']}")
        print(f"  Network: {network_results['avg_time_per_stock']:.2f}s per stock")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        print(f"  Download workers: {recommended_download}")
        print(f"  Database workers: NOT NEEDED (uses batch loading)")
        
        print(f"\n📝 USAGE:")
        print(f"  python simulator.py --download --universe sp500 --workers {recommended_download}")
        print(f"  python simulator.py --universe sp500  # batch loading is automatic")
        
        print(f"\n💾 Results saved to: {BENCHMARK_CONFIG}")
        print("="*70)
        
        return results
    
    def save_benchmark(self, results):
        """Save benchmark results to config file"""
        try:
            with open(BENCHMARK_CONFIG, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save benchmark config: {e}")
    
    @staticmethod
    def load_benchmark():
        """Load saved benchmark results"""
        if not BENCHMARK_CONFIG.exists():
            return None
        
        try:
            with open(BENCHMARK_CONFIG, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Could not load benchmark config: {e}")
            return None
    
    @staticmethod
    def get_recommended_workers():
        """
        Get recommended worker counts from saved benchmark
        
        Returns:
            int: download_workers (or default 10)
        """
        results = SystemBenchmark.load_benchmark()
        
        if results and 'recommendations' in results:
            return results['recommendations']['download_workers']
        
        # Default: 2x CPU cores for downloads
        cpu_count = os.cpu_count() or 4
        return min(cpu_count * 2, 20)