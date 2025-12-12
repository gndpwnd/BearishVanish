"""
System Benchmark Module
Benchmarks network, database, and CPU performance to recommend optimal worker counts
"""

import os
import time
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil  # For system info - install with: pip install psutil

BENCHMARK_CONFIG = Path('./benchmark_config.json')

class SystemBenchmark:
    def __init__(self, data_manager, universe_manager):
        """
        Initialize benchmark with data manager and universe manager
        
        Args:
            data_manager: DataManager instance for testing downloads
            universe_manager: UniverseManager instance for getting symbols
        """
        self.data_manager = data_manager
        self.universe_manager = universe_manager
        self.results = {}
        
    def benchmark_network(self, test_symbols=None, num_tests=10):
        """
        Benchmark network speed by downloading test stocks
        
        Args:
            test_symbols: List of symbols to test (default: uses S&P 500 sample)
            num_tests: Number of stocks to download for testing
            
        Returns:
            dict with network benchmark results
        """
        print("\n" + "="*70)
        print("BENCHMARKING NETWORK SPEED")
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
        for symbol in test_symbols[:5]:  # Test with 5 stocks
            try:
                self.data_manager.fetch_from_api(symbol, start_date, end_date)
                successful += 1
            except Exception as e:
                print(f"  ⚠️  {symbol} failed: {e}")
        
        single_thread_time = time.time() - start_time
        avg_time_per_stock = single_thread_time / successful if successful > 0 else 0
        
        print(f"  ✅ Downloaded {successful}/5 stocks in {single_thread_time:.2f}s")
        print(f"  📊 Average: {avg_time_per_stock:.2f}s per stock")
        
        # Test 2: Multi-threaded download (5 workers)
        print("\n2️⃣ Testing multi-threaded downloads (5 workers)...")
        start_time = time.time()
        
        def download_test(symbol):
            try:
                self.data_manager.fetch_from_api(symbol, start_date, end_date)
                return True
            except:
                return False
        
        successful = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(download_test, sym): sym for sym in test_symbols[5:10]}
            for future in as_completed(futures):
                if future.result():
                    successful += 1
        
        multi_thread_time = time.time() - start_time
        speedup = single_thread_time / multi_thread_time if multi_thread_time > 0 else 1
        
        print(f"  ✅ Downloaded {successful}/5 stocks in {multi_thread_time:.2f}s")
        print(f"  📊 Speedup: {speedup:.2f}x faster than single-threaded")
        
        # Calculate optimal workers for network
        # Network I/O bound: more workers = better, but limited by API rate limits
        cpu_count = os.cpu_count() or 4
        estimated_optimal = int(min(cpu_count * 2, 50))  # Max 50 workers for API
        
        results = {
            'single_thread_time': single_thread_time,
            'multi_thread_time': multi_thread_time,
            'avg_time_per_stock': avg_time_per_stock,
            'speedup': speedup,
            'recommended_download_workers': estimated_optimal,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📊 NETWORK BENCHMARK RESULTS:")
        print(f"  Average time per stock: {avg_time_per_stock:.2f}s")
        print(f"  Multi-threading speedup: {speedup:.2f}x")
        print(f"  Recommended download workers: {estimated_optimal}")
        
        return results
    
    def benchmark_database(self, test_symbols=None, num_tests=100):
        """
        Benchmark database read speed
        
        Args:
            test_symbols: List of symbols to test (default: uses cached symbols)
            num_tests: Number of reads to perform
            
        Returns:
            dict with database benchmark results
        """
        print("\n" + "="*70)
        print("BENCHMARKING DATABASE READ SPEED")
        print("="*70)
        
        # Get test symbols from cached data
        if test_symbols is None:
            cached = self.data_manager.list_cached_symbols()
            if not cached:
                print("❌ No cached data available for database test")
                return None
            test_symbols = [s['symbol'] for s in cached[:num_tests]]
        
        if not test_symbols:
            print("❌ No symbols available for database test")
            return None
        
        print(f"Testing database read speed with {len(test_symbols)} stocks...")
        
        end_date = datetime.now().replace(tzinfo=None)
        start_date = (end_date - timedelta(days=30)).replace(tzinfo=None)
        
        # Test 1: Single-threaded reads
        print("\n1️⃣ Testing single-threaded database reads...")
        start_time = time.time()
        
        successful = 0
        for symbol in test_symbols[:20]:  # Test with 20 stocks
            try:
                df = self.data_manager.load_offline_data(symbol, start_date, end_date)
                if df is not None:
                    successful += 1
            except:
                pass
        
        single_thread_time = time.time() - start_time
        avg_time_per_read = single_thread_time / successful if successful > 0 else 0
        
        print(f"  ✅ Read {successful}/20 stocks in {single_thread_time:.2f}s")
        print(f"  📊 Average: {avg_time_per_read:.3f}s per stock")
        
        # Test 2: Multi-threaded reads (10 workers)
        print("\n2️⃣ Testing multi-threaded database reads (10 workers)...")
        start_time = time.time()
        
        def read_test(symbol):
            try:
                df = self.data_manager.load_offline_data(symbol, start_date, end_date)
                return df is not None
            except:
                return False
        
        successful = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(read_test, sym): sym for sym in test_symbols[20:40]}
            for future in as_completed(futures):
                if future.result():
                    successful += 1
        
        multi_thread_time = time.time() - start_time
        speedup = single_thread_time / multi_thread_time if multi_thread_time > 0 else 1
        
        print(f"  ✅ Read {successful}/20 stocks in {multi_thread_time:.2f}s")
        print(f"  📊 Speedup: {speedup:.2f}x faster than single-threaded")
        
        # Calculate optimal workers for database
        # Database reads are CPU + I/O bound: benefit from parallelism but have limits
        cpu_count = os.cpu_count() or 4
        estimated_optimal = int(min(cpu_count * 3, 30))  # Max 30 workers for DB
        
        results = {
            'single_thread_time': single_thread_time,
            'multi_thread_time': multi_thread_time,
            'avg_time_per_read': avg_time_per_read,
            'speedup': speedup,
            'recommended_db_workers': estimated_optimal,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\n📊 DATABASE BENCHMARK RESULTS:")
        print(f"  Average time per read: {avg_time_per_read:.3f}s")
        print(f"  Multi-threading speedup: {speedup:.2f}x")
        print(f"  Recommended database workers: {estimated_optimal}")
        
        return results
    
    def benchmark_cpu(self):
        """
        Get CPU information and capacity
        
        Returns:
            dict with CPU info
        """
        print("\n" + "="*70)
        print("SYSTEM CPU INFORMATION")
        print("="*70)
        
        cpu_count = os.cpu_count() or 4
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            
            print(f"  CPU Cores: {cpu_count}")
            print(f"  CPU Usage: {cpu_percent}%")
            if cpu_freq:
                print(f"  CPU Frequency: {cpu_freq.current:.0f} MHz")
            print(f"  Memory Total: {memory.total / (1024**3):.1f} GB")
            print(f"  Memory Available: {memory.available / (1024**3):.1f} GB")
            print(f"  Memory Usage: {memory.percent}%")
            
            results = {
                'cpu_count': cpu_count,
                'cpu_percent': cpu_percent,
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else None,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'memory_percent': memory.percent,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"  ℹ️  Limited system info available: {e}")
            results = {
                'cpu_count': cpu_count,
                'timestamp': datetime.now().isoformat()
            }
        
        return results
    
    def run_full_benchmark(self):
        """
        Run complete benchmark suite
        
        Returns:
            dict with all benchmark results and recommendations
        """
        print("\n" + "="*70)
        print("RUNNING FULL SYSTEM BENCHMARK")
        print("="*70)
        print("This will take 1-2 minutes...")
        
        # 1. CPU info
        cpu_results = self.benchmark_cpu()
        
        # 2. Network speed
        network_results = self.benchmark_network()
        
        # 3. Database speed
        db_results = self.benchmark_database()
        
        # Calculate final recommendations (70% of capacity)
        cpu_count = cpu_results.get('cpu_count', 4)
        
        if network_results:
            recommended_download = int(network_results['recommended_download_workers'] * 0.7)
        else:
            recommended_download = int(cpu_count * 1.4)  # Fallback: 70% of 2x cores
        
        if db_results:
            recommended_db = int(db_results['recommended_db_workers'] * 0.7)
        else:
            recommended_db = int(cpu_count * 2.1)  # Fallback: 70% of 3x cores
        
        # Ensure minimum of 2 workers
        recommended_download = max(2, recommended_download)
        recommended_db = max(2, recommended_db)
        
        results = {
            'cpu': cpu_results,
            'network': network_results,
            'database': db_results,
            'recommendations': {
                'download_workers': recommended_download,
                'db_workers': recommended_db,
                'notes': 'Set to 70% of measured capacity for system stability'
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
        print(f"  CPU Cores: {cpu_count}")
        if network_results:
            print(f"  Network: {network_results['avg_time_per_stock']:.2f}s per stock")
        if db_results:
            print(f"  Database: {db_results['avg_time_per_read']:.3f}s per read")
        
        print(f"\n🎯 RECOMMENDATIONS (70% of capacity):")
        print(f"  Download workers: {recommended_download}")
        print(f"  Database workers: {recommended_db}")
        
        print(f"\n📝 USAGE:")
        print(f"  python simulator.py --download --universe all --workers {recommended_download}")
        print(f"  python simulator.py --universe sp500 --workers {recommended_db}")
        
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
            tuple: (download_workers, db_workers) or (10, 10) if no benchmark
        """
        results = SystemBenchmark.load_benchmark()
        
        if results and 'recommendations' in results:
            return (
                results['recommendations']['download_workers'],
                results['recommendations']['db_workers']
            )
        
        # Default values if no benchmark
        cpu_count = os.cpu_count() or 4
        return (max(2, cpu_count), max(2, cpu_count))