"""
Configuration Optimizer with Integrated Benchmarking
Auto-tunes parameters for maximum performance based on hardware benchmarking
"""

import numpy as np
import pandas as pd
import json
import time
import psutil
import platform
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Type definitions
BenchmarkResult = Dict[str, Any]
HardwareProfile = Dict[str, Any]

# Configurable paths
BENCHMARK_CONFIG = Path('./benchmark_config.json')
OPTIMIZATION_CONFIG = Path('./optimization_config.json')

@dataclass
class OptimizationResult:
    """Results from configuration optimization"""
    # Hardware profile
    hardware: HardwareProfile
    
    # Performance predictions
    predicted_speedup: float
    predicted_memory_reduction: float
    recommended_download_workers: int
    recommended_simulation_workers: int
    
    # Benchmark results
    benchmark_results: Dict[str, BenchmarkResult]
    
    # Recommendations
    recommendations: List[str]
    estimated_calc_per_second: float
    
    # Timestamp
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'hardware': self.hardware,
            'predicted_speedup': self.predicted_speedup,
            'predicted_memory_reduction': self.predicted_memory_reduction,
            'recommended_download_workers': self.recommended_download_workers,
            'recommended_simulation_workers': self.recommended_simulation_workers,
            'benchmark_results': self.benchmark_results,
            'recommendations': self.recommendations,
            'estimated_calc_per_second': self.estimated_calc_per_second,
            'timestamp': self.timestamp
        }
    
    def save(self, filepath: str = None):
        """Save optimization results to file"""
        if filepath is None:
            filepath = BENCHMARK_CONFIG
        
        data = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Optimization results saved to: {filepath}")
    
    @classmethod
    def load(cls, filepath: str = None) -> 'OptimizationResult':
        """Load optimization results from file"""
        if filepath is None:
            filepath = BENCHMARK_CONFIG
        
        if not Path(filepath).exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls(
            hardware=data['hardware'],
            predicted_speedup=data['predicted_speedup'],
            predicted_memory_reduction=data['predicted_memory_reduction'],
            recommended_download_workers=data['recommended_download_workers'],
            recommended_simulation_workers=data['recommended_simulation_workers'],
            benchmark_results=data['benchmark_results'],
            recommendations=data['recommendations'],
            estimated_calc_per_second=data['estimated_calc_per_second'],
            timestamp=data.get('timestamp')
        )
    
    def print_summary(self):
        """Print optimization summary"""
        print(f"\n{'='*70}")
        print("CONFIGURATION OPTIMIZATION RESULTS")
        print(f"{'='*70}")
        
        print(f"\n💻 Hardware Profile:")
        print(f"   CPU: {self.hardware.get('cpu_name', 'Unknown')}")
        print(f"   Cores: {self.hardware.get('cpu_cores', 'Unknown')}")
        print(f"   RAM: {self.hardware.get('total_memory_gb', 'Unknown'):.1f} GB")
        print(f"   OS: {self.hardware.get('os', 'Unknown')}")
        
        if 'gpu_name' in self.hardware and self.hardware['gpu_name']:
            print(f"   GPU: {self.hardware['gpu_name']}")
        
        print(f"\n🎯 Performance Predictions:")
        print(f"   Speedup: {self.predicted_speedup:.1f}x")
        print(f"   Memory Reduction: {self.predicted_memory_reduction:.1f}%")
        print(f"   Estimated Calc/Sec: {self.estimated_calc_per_second:,.0f}")
        
        print(f"\n⚡ Recommended Settings:")
        print(f"   Download Workers: {self.recommended_download_workers}")
        print(f"   Simulation Workers: {self.recommended_simulation_workers}")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(self.recommendations[:5], 1):
            print(f"   {i}. {rec}")
        
        print(f"{'='*70}\n")


class ConfigOptimizer:
    """
    Auto-tunes configuration for optimal performance on your hardware
    Combines system benchmarking with optimization recommendations
    """
    
    def __init__(self, data_manager=None, universe_manager=None):
        self.data_manager = data_manager
        self.universe_manager = universe_manager
        
        # Test data
        self.test_data = None
        
        # Results storage
        self.results = {}
        self.hardware_profile = {}
        
        print(f"🔧 Configuration Optimizer Initialized")
    
    def _get_hardware_profile(self) -> HardwareProfile:
        """Profile the current hardware"""
        profile = {}
        
        # CPU information
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            profile['cpu_name'] = cpu_info.get('brand_raw', 'Unknown')
            profile['cpu_cores'] = psutil.cpu_count(logical=False)
            profile['cpu_threads'] = psutil.cpu_count(logical=True)
            profile['cpu_frequency'] = psutil.cpu_freq().max if psutil.cpu_freq() else None
        except ImportError:
            profile['cpu_name'] = platform.processor()
            profile['cpu_cores'] = psutil.cpu_count(logical=False)
            profile['cpu_threads'] = psutil.cpu_count(logical=True)
        
        # Memory information
        memory = psutil.virtual_memory()
        profile['total_memory_gb'] = memory.total / (1024**3)
        profile['available_memory_gb'] = memory.available / (1024**3)
        
        # Disk information
        try:
            disk = psutil.disk_usage('/')
            profile['disk_total_gb'] = disk.total / (1024**3)
            profile['disk_free_gb'] = disk.free / (1024**3)
        except Exception:
            pass
        
        # GPU information
        profile['gpu_name'] = None
        profile['gpu_memory_gb'] = 0
        
        try:
            import cupy as cp
            if cp.cuda.is_available():
                device = cp.cuda.runtime.getDeviceProperties(0)
                profile['gpu_name'] = device['name'].decode('utf-8')
                profile['gpu_memory_gb'] = device['totalGlobalMem'] / (1024**3)
                profile['gpu_cores'] = device['multiProcessorCount'] * 64
        except ImportError:
            pass
        
        # OS information
        profile['os'] = platform.system()
        profile['os_version'] = platform.version()
        profile['python_version'] = platform.python_version()
        
        # Performance characteristics
        profile['memory_bandwidth_gb_s'] = self._estimate_memory_bandwidth()
        profile['cpu_cache_mb'] = self._estimate_cpu_cache()
        
        return profile
    
    def _estimate_memory_bandwidth(self) -> float:
        """Estimate memory bandwidth"""
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        if memory_gb < 8:
            return 10.0
        elif memory_gb < 32:
            return 25.0
        else:
            return 50.0
    
    def _estimate_cpu_cache(self) -> float:
        """Estimate CPU cache size"""
        cpu_cores = psutil.cpu_count(logical=False)
        
        if cpu_cores <= 4:
            return 8.0
        elif cpu_cores <= 8:
            return 16.0
        elif cpu_cores <= 16:
            return 32.0
        else:
            return 64.0
    
    def benchmark_network(self, test_symbols=None, num_tests=10):
        """
        Benchmark network speed by downloading test stocks
        This determines optimal worker count for API downloads
        """
        if self.data_manager is None:
            print("❌ Data manager not provided for network benchmark")
            return None
        
        print("\n" + "="*70)
        print("BENCHMARKING NETWORK DOWNLOAD SPEED")
        print("="*70)
        
        # Get test symbols
        if test_symbols is None:
            if self.universe_manager:
                all_symbols = self.universe_manager.get_approved_tickers('sp500')
                if not all_symbols:
                    print("❌ No symbols available for network test")
                    return None
                test_symbols = all_symbols[:num_tests]
            else:
                test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'][:num_tests]
        
        print(f"Testing download speed with {len(test_symbols)} stocks...")
        
        end_date = datetime.now().replace(tzinfo=None)
        start_date = (end_date - timedelta(days=30)).replace(tzinfo=None)
        
        # Test 1: Single-threaded download
        print("\n1️⃣ Testing single-threaded downloads...")
        start_time = time.time()
        
        successful = 0
        for symbol in test_symbols[:min(5, len(test_symbols))]:
            try:
                self.data_manager.fetch_from_api(symbol, start_date, end_date)
                successful += 1
            except Exception as e:
                print(f"  ⚠️  {symbol} failed: {e}")
        
        single_thread_time = time.time() - start_time
        avg_time_per_stock = single_thread_time / successful if successful > 0 else 0
        
        print(f"  ✅ Downloaded {successful}/5 stocks in {single_thread_time:.2f}s")
        print(f"  📊 Average: {avg_time_per_stock:.2f}s per stock")
        
        # Test 2: Multi-threaded download
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
        cpu_count = psutil.cpu_count(logical=False) or 4
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
    
    def benchmark_computation(self, data_size: Tuple[int, int] = (10000, 10)):
        """
        Benchmark computational performance
        """
        print(f"\n{'='*70}")
        print("BENCHMARKING COMPUTATIONAL PERFORMANCE")
        print(f"{'='*70}")
        
        results = {}
        
        # Test NumPy performance
        print(f"\n🧮 NumPy Performance Test...")
        np.random.seed(42)
        
        # Large array operations
        arr = np.random.randn(1000000)
        
        start = time.time()
        for _ in range(100):
            _ = arr * 2.0 + 1.0
        numpy_time = time.time() - start
        
        results['numpy_ops_per_sec'] = 100 / numpy_time
        print(f"  NumPy operations: {results['numpy_ops_per_sec']:.0f} ops/sec")
        
        # Test Numba if available
        try:
            from numba import jit
            
            @jit(nopython=True)
            def numba_loop(arr):
                result = np.empty_like(arr)
                for i in range(len(arr)):
                    result[i] = arr[i] * 2.0 + 1.0
                return result
            
            # First run includes compilation
            _ = numba_loop(arr)
            
            start = time.time()
            for _ in range(100):
                _ = numba_loop(arr)
            numba_time = time.time() - start
            
            results['numba_ops_per_sec'] = 100 / numba_time
            results['numba_speedup'] = numpy_time / numba_time
            print(f"  Numba operations: {results['numba_ops_per_sec']:.0f} ops/sec ({results['numba_speedup']:.1f}x)")
        except ImportError:
            print("  ℹ️  Numba not installed - install for 3-10x speedup")
            results['numba_available'] = False
        except Exception as e:
            print(f"  ⚠️  Numba test failed: {e}")
            results['numba_available'] = False
        
        return results
    
    def benchmark_memory(self):
        """
        Benchmark memory performance
        """
        print(f"\n{'='*70}")
        print("BENCHMARKING MEMORY PERFORMANCE")
        print(f"{'='*70}")
        
        results = {}
        
        # Test memory allocation speed
        import sys
        
        start = time.time()
        arrays = []
        for i in range(1000):
            arrays.append(np.zeros((1000, 10), dtype=np.float64))
        allocation_time = time.time() - start
        
        results['allocation_speed'] = len(arrays) / allocation_time
        results['float64_memory_mb'] = sys.getsizeof(arrays[0]) / 1024**2
        
        # Test float32 vs float64
        arr64 = np.random.randn(1000000).astype(np.float64)
        arr32 = arr64.astype(np.float32)
        
        start = time.time()
        for _ in range(100):
            _ = arr64 * 2.0
        float64_time = time.time() - start
        
        start = time.time()
        for _ in range(100):
            _ = arr32 * 2.0
        float32_time = time.time() - start
        
        results['float64_time'] = float64_time
        results['float32_time'] = float32_time
        results['float32_speedup'] = float64_time / float32_time
        results['float32_memory_saving'] = 0.5
        
        print(f"  Float64: {float64_time:.3f}s")
        print(f"  Float32: {float32_time:.3f}s ({results['float32_speedup']:.1f}x)")
        print(f"  Memory saving with float32: {results['float32_memory_saving']*100:.0f}%")
        
        return results
    
    def run_comprehensive_benchmark(self):
        """
        Run comprehensive system benchmark
        """
        print(f"\n{'='*70}")
        print("RUNNING COMPREHENSIVE SYSTEM BENCHMARK")
        print(f"{'='*70}")
        print("This will take about 30-60 seconds...")
        
        # 1. Hardware profile
        print(f"\n{'='*70}")
        print("SYSTEM INFORMATION")
        print(f"{'='*70}")
        
        hardware_profile = self._get_hardware_profile()
        self.hardware_profile = hardware_profile
        
        print(f"  CPU: {hardware_profile['cpu_name']}")
        print(f"  Cores: {hardware_profile['cpu_cores']}")
        print(f"  RAM: {hardware_profile['total_memory_gb']:.1f} GB")
        print(f"  OS: {hardware_profile['os']}")
        
        if hardware_profile.get('gpu_name'):
            print(f"  GPU: {hardware_profile['gpu_name']}")
        
        # 2. Network benchmark
        network_results = self.benchmark_network()
        
        # 3. Computation benchmark
        compute_results = self.benchmark_computation()
        
        # 4. Memory benchmark
        memory_results = self.benchmark_memory()
        
        # Compile results
        benchmark_results = {
            'hardware': hardware_profile,
            'network': network_results,
            'computation': compute_results,
            'memory': memory_results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate recommendations
        optimization_result = self._generate_recommendations(benchmark_results)
        
        # Save results
        optimization_result.save()
        
        # Print summary
        optimization_result.print_summary()
        
        # Also save optimization config
        self._save_optimization_config(optimization_result)
        
        return optimization_result
    
    def _generate_recommendations(self, benchmark_results: Dict) -> OptimizationResult:
        """Generate optimization recommendations based on benchmark results"""
        hardware = benchmark_results['hardware']
        network = benchmark_results.get('network', {})
        compute = benchmark_results.get('computation', {})
        memory = benchmark_results.get('memory', {})
        
        # Calculate recommendations
        cpu_cores = hardware.get('cpu_cores', 4)
        total_ram_gb = hardware.get('total_memory_gb', 8)
        
        # Network workers
        recommended_download = network.get('recommended_download_workers', min(cpu_cores * 2, 20))
        
        # Simulation workers (different from download workers)
        recommended_simulation = max(1, cpu_cores - 2)
        
        # Performance predictions
        predicted_speedup = 1.0
        
        if compute.get('numba_available', False) and compute.get('numba_speedup', 1) > 2:
            predicted_speedup *= compute['numba_speedup']
        
        if memory.get('float32_speedup', 1) > 1.2:
            predicted_speedup *= 1.2
        
        predicted_speedup *= (recommended_simulation * 0.8)  # 80% parallel efficiency
        
        predicted_memory_reduction = memory.get('float32_memory_saving', 0) * 100
        
        # Estimate calculations per second
        base_calc_per_sec = 9000
        estimated_calc_per_sec = base_calc_per_sec * predicted_speedup
        
        # Generate recommendations
        recommendations = []
        
        # Network recommendations
        recommendations.append(f"Use {recommended_download} workers for data downloads")
        
        # Computation recommendations
        if compute.get('numba_available', False):
            recommendations.append("Enable Numba JIT compilation for 3-10x speedup")
        else:
            recommendations.append("Install Numba: pip install numba")
        
        # Memory recommendations
        if memory.get('float32_speedup', 1) > 1.2:
            recommendations.append("Use float32 data types for 50% memory reduction")
        
        if total_ram_gb < 16:
            recommendations.append(f"Consider upgrading to 16GB+ RAM (current: {total_ram_gb:.1f}GB)")
        
        # General performance
        recommendations.append(f"Expected speedup: {predicted_speedup:.1f}x ({estimated_calc_per_sec:,.0f} calc/sec)")
        
        return OptimizationResult(
            hardware=hardware,
            predicted_speedup=predicted_speedup,
            predicted_memory_reduction=predicted_memory_reduction,
            recommended_download_workers=recommended_download,
            recommended_simulation_workers=recommended_simulation,
            benchmark_results=benchmark_results,
            recommendations=recommendations,
            estimated_calc_per_second=estimated_calc_per_sec
        )
    
    def _save_optimization_config(self, optimization_result: OptimizationResult):
        """Save optimization configuration file"""
        config = {
            'use_numba': True,
            'use_float32': optimization_result.predicted_memory_reduction > 20,
            'parallel_workers': {
                'download': optimization_result.recommended_download_workers,
                'simulation': optimization_result.recommended_simulation_workers
            },
            'precompute_indicators': True,
            'batch_database_operations': True,
            'memory_optimization': {
                'aggressive_gc': optimization_result.hardware.get('total_memory_gb', 0) < 8
            },
            'profiling': {
                'enabled': False,
                'output_dir': './profiling'
            },
            'benchmark_timestamp': optimization_result.timestamp
        }
        
        with open(OPTIMIZATION_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Optimization configuration saved to: {OPTIMIZATION_CONFIG}")
    
    def get_recommended_settings(self):
        """Get recommended settings from saved benchmark"""
        result = OptimizationResult.load()
        if result is None:
            # Return defaults
            cpu_cores = psutil.cpu_count(logical=False) or 4
            return {
                'download_workers': min(cpu_cores * 2, 20),
                'simulation_workers': max(1, cpu_cores - 2),
                'use_numba': True,
                'use_float32': False
            }
        
        return {
            'download_workers': result.recommended_download_workers,
            'simulation_workers': result.recommended_simulation_workers,
            'use_numba': True,
            'use_float32': result.predicted_memory_reduction > 20
        }
    
    @staticmethod
    def load_config():
        """Load optimization configuration"""
        if not OPTIMIZATION_CONFIG.exists():
            # Return default config
            cpu_cores = psutil.cpu_count(logical=False) or 4
            return {
                'use_numba': True,
                'use_float32': False,
                'parallel_workers': {
                    'download': min(cpu_cores * 2, 20),
                    'simulation': max(1, cpu_cores - 2)
                },
                'precompute_indicators': True,
                'batch_database_operations': True,
                'memory_optimization': {'aggressive_gc': False},
                'profiling': {'enabled': False, 'output_dir': './profiling'}
            }
        
        with open(OPTIMIZATION_CONFIG, 'r') as f:
            return json.load(f)


# Convenience functions
def optimize_system(data_manager=None, universe_manager=None):
    """Main function to optimize system configuration"""
    optimizer = ConfigOptimizer(data_manager, universe_manager)
    return optimizer.run_comprehensive_benchmark()

def get_optimized_settings():
    """Get optimized settings for simulation"""
    optimizer = ConfigOptimizer()
    return optimizer.get_recommended_settings()

def load_optimization_config():
    """Load optimization configuration"""
    return ConfigOptimizer.load_config()


if __name__ == "__main__":
    # Run optimization standalone
    print(f"\n{'='*70}")
    print("AUTO-CONFIGURATION OPTIMIZER")
    print(f"{'='*70}")
    print("This will benchmark your system and find optimal settings")
    print("Estimated time: 2-5 minutes")
    print(f"{'='*70}\n")
    
    result = optimize_system()
    
    if result:
        print("\n🎯 Optimization Complete!")
        print("Next steps:")
        print("1. Review benchmark_config.json for detailed results")
        print("2. Review optimization_config.json for settings")
        print("3. Update your simulation to use optimized settings")
        print("4. Run simulation and verify performance improvement")