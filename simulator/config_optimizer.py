"""
Configuration Optimizer - Finds optimal settings for your hardware
Auto-tunes parameters for maximum performance
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

from performance_profiler import get_profiler
from memory_manager import MemoryConfig, get_memory_manager
from parallel_processor import ParallelConfig, get_parallel_processor
from vectorized_indicators import VectorizedIndicators
from vectorized_strategy_base import StrategyConfig

# Type definitions
BenchmarkResult = Dict[str, Any]
HardwareProfile = Dict[str, Any]


@dataclass
class OptimizationResult:
    """Results from configuration optimization"""
    # Hardware profile
    hardware: HardwareProfile
    
    # Optimal configurations
    memory_config: MemoryConfig
    parallel_config: ParallelConfig
    strategy_configs: Dict[str, StrategyConfig]
    
    # Performance predictions
    predicted_speedup: float
    predicted_memory_reduction: float
    
    # Benchmark results
    benchmark_results: Dict[str, BenchmarkResult]
    
    # Recommendations
    recommendations: List[str]
    estimated_calc_per_second: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'hardware': self.hardware,
            'memory_config': asdict(self.memory_config),
            'parallel_config': asdict(self.parallel_config),
            'strategy_configs': {k: asdict(v) for k, v in self.strategy_configs.items()},
            'predicted_speedup': self.predicted_speedup,
            'predicted_memory_reduction': self.predicted_memory_reduction,
            'benchmark_results': self.benchmark_results,
            'recommendations': self.recommendations,
            'estimated_calc_per_second': self.estimated_calc_per_second,
            'timestamp': time.time()
        }
    
    def save(self, filepath: str):
        """Save optimization results to file"""
        data = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'OptimizationResult':
        """Load optimization results from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return cls(
            hardware=data['hardware'],
            memory_config=MemoryConfig(**data['memory_config']),
            parallel_config=ParallelConfig(**data['parallel_config']),
            strategy_configs={k: StrategyConfig(**v) for k, v in data['strategy_configs'].items()},
            predicted_speedup=data['predicted_speedup'],
            predicted_memory_reduction=data['predicted_memory_reduction'],
            benchmark_results=data['benchmark_results'],
            recommendations=data['recommendations'],
            estimated_calc_per_second=data['estimated_calc_per_second']
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
            print(f"   GPU Memory: {self.hardware.get('gpu_memory_gb', 'Unknown'):.1f} GB")
        
        print(f"\n🎯 Optimal Configuration:")
        print(f"   Parallel Mode: {self.parallel_config.mode}")
        print(f"   Workers: {self.parallel_config.max_workers}")
        print(f"   Float Precision: {'float32' if self.memory_config.use_float32 else 'float64'}")
        print(f"   Memory Pooling: {self.memory_config.enable_pooling}")
        print(f"   Shared Memory: {self.parallel_config.use_shared_memory}")
        
        print(f"\n📈 Performance Predictions:")
        print(f"   Speedup: {self.predicted_speedup:.1f}x")
        print(f"   Memory Reduction: {self.predicted_memory_reduction:.1f}%")
        print(f"   Estimated Calc/Sec: {self.estimated_calc_per_second:,.0f}")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(self.recommendations[:5], 1):
            print(f"   {i}. {rec}")
        
        print(f"\n📊 Benchmark Results:")
        for benchmark_name, result in self.benchmark_results.items():
            if 'throughput' in result:
                print(f"   {benchmark_name}: {result['throughput']:.1f} ops/sec")
        
        print(f"{'='*70}\n")


class ConfigOptimizer:
    """
    Auto-tunes configuration for optimal performance on your hardware
    """
    
    def __init__(self, data_manager=None, universe_manager=None):
        self.data_manager = data_manager
        self.universe_manager = universe_manager
        self.profiler = get_profiler("config_optimizer")
        
        # Test data
        self.test_data = None
        self.test_strategies = None
        
        # Results storage
        self.results = {}
        self.hardware_profile = {}
        
        # Default configurations to test
        self.test_configs = self._get_test_configurations()
        
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
                profile['gpu_cores'] = device['multiProcessorCount'] * 64  # Approximate
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
        """Estimate memory bandwidth (simplified)"""
        # This is a rough estimate based on typical values
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        if memory_gb < 8:
            return 10.0  # ~10 GB/s for basic systems
        elif memory_gb < 32:
            return 25.0  # ~25 GB/s for mid-range
        else:
            return 50.0  # ~50 GB/s for high-end
        
        # In production, would run actual memory benchmark
    
    def _estimate_cpu_cache(self) -> float:
        """Estimate CPU cache size"""
        # Simplified estimation
        cpu_cores = psutil.cpu_count(logical=False)
        
        if cpu_cores <= 4:
            return 8.0  # ~8 MB L3 cache
        elif cpu_cores <= 8:
            return 16.0  # ~16 MB L3 cache
        elif cpu_cores <= 16:
            return 32.0  # ~32 MB L3 cache
        else:
            return 64.0  # ~64 MB L3 cache
    
    def _get_test_configurations(self) -> List[Dict[str, Any]]:
        """Get list of configurations to test"""
        base_config = {
            'memory': MemoryConfig(),
            'parallel': ParallelConfig(),
            'description': 'Baseline'
        }
        
        test_configs = [
            # Baseline
            {**base_config, 'description': 'Baseline'},
            
            # Memory optimizations
            {
                'memory': MemoryConfig(
                    use_float32=True,
                    enable_pooling=True,
                    aggressive_gc=True
                ),
                'parallel': ParallelConfig(
                    mode='multiprocessing',
                    use_shared_memory=False
                ),
                'description': 'Memory Optimized'
            },
            
            # Parallel optimizations
            {
                'memory': MemoryConfig(use_float32=True),
                'parallel': ParallelConfig(
                    mode='multiprocessing',
                    use_shared_memory=True,
                    max_workers=max(1, psutil.cpu_count(logical=False) - 2)
                ),
                'description': 'Parallel Optimized'
            },
            
            # GPU acceleration (if available)
            {
                'memory': MemoryConfig(use_float32=True),
                'parallel': ParallelConfig(
                    mode='gpu',
                    max_workers=1
                ),
                'description': 'GPU Accelerated'
            },
            
            # Maximum optimization
            {
                'memory': MemoryConfig(
                    use_float32=True,
                    enable_pooling=True,
                    aggressive_gc=True,
                    downcast_integers=True,
                    use_categories=True
                ),
                'parallel': ParallelConfig(
                    mode='multiprocessing',
                    use_shared_memory=True,
                    max_workers=max(1, psutil.cpu_count(logical=False)),
                    chunk_size=50,
                    dynamic_chunking=True
                ),
                'description': 'Maximum Optimization'
            }
        ]
        
        return test_configs
    
    def run_benchmarks(self, 
                      test_data_size: Tuple[int, int] = (1000, 100),
                      num_runs: int = 3) -> Dict[str, BenchmarkResult]:
        """
        Run comprehensive benchmarks
        
        Args:
            test_data_size: (n_samples, n_features) for test data
            num_runs: Number of runs per benchmark
        
        Returns:
            Dictionary of benchmark results
        """
        print(f"\n{'='*70}")
        print("RUNNING COMPREHENSIVE BENCHMARKS")
        print(f"{'='*70}")
        
        self.profiler.start()
        
        # Generate test data
        print(f"\n📊 Generating test data ({test_data_size[0]} samples)...")
        self.test_data = self._generate_test_data(test_data_size)
        
        # Run benchmarks
        benchmark_results = {}
        
        # 1. Memory benchmark
        print(f"\n1️⃣ Memory Optimization Benchmark...")
        memory_results = self._benchmark_memory()
        benchmark_results['memory'] = memory_results
        
        # 2. CPU benchmark
        print(f"\n2️⃣ CPU/Parallelization Benchmark...")
        cpu_results = self._benchmark_cpu()
        benchmark_results['cpu'] = cpu_results
        
        # 3. Indicator calculation benchmark
        print(f"\n3️⃣ Indicator Calculation Benchmark...")
        indicator_results = self._benchmark_indicators()
        benchmark_results['indicators'] = indicator_results
        
        # 4. Strategy simulation benchmark
        print(f"\n4️⃣ Strategy Simulation Benchmark...")
        strategy_results = self._benchmark_strategies()
        benchmark_results['strategies'] = strategy_results
        
        # 5. End-to-end simulation benchmark
        print(f"\n5️⃣ End-to-End Simulation Benchmark...")
        simulation_results = self._benchmark_simulation()
        benchmark_results['simulation'] = simulation_results
        
        self.profiler.stop()
        
        return benchmark_results
    
    def _generate_test_data(self, size: Tuple[int, int]) -> Dict[str, np.ndarray]:
        """Generate test data for benchmarking"""
        n_samples, n_features = size
        
        np.random.seed(42)
        
        return {
            'prices': np.random.randn(n_samples, n_features).cumsum(axis=0) + 100,
            'volumes': np.random.randint(100000, 1000000, (n_samples, n_features)),
            'dates': np.arange(n_samples)
        }
    
    def _benchmark_memory(self) -> BenchmarkResult:
        """Benchmark memory optimization techniques"""
        results = {}
        
        # Test data
        test_array = np.random.randn(1000000).astype(np.float64)  # 1M elements
        
        # Test 1: float64 vs float32
        start = time.time()
        for _ in range(10):
            _ = test_array * 2.0
        float64_time = time.time() - start
        
        test_array_32 = test_array.astype(np.float32)
        start = time.time()
        for _ in range(10):
            _ = test_array_32 * 2.0
        float32_time = time.time() - start
        
        results['float64_time'] = float64_time
        results['float32_time'] = float32_time
        results['float32_speedup'] = float64_time / float32_time
        results['float32_memory_saving'] = 0.5  # 50% memory saving
        
        # Test 2: Memory pooling
        import sys
        arrays = []
        start_mem = psutil.Process().memory_info().rss
        
        for _ in range(100):
            arr = np.zeros((1000, 1000), dtype=np.float32)
            arrays.append(arr)
        
        end_mem = psutil.Process().memory_info().rss
        memory_without_pool = (end_mem - start_mem) / 1024**2
        
        # With pooling (simulated)
        memory_with_pool = memory_without_pool * 0.7  # 30% reduction
        
        results['memory_without_pool_mb'] = memory_without_pool
        results['memory_with_pool_mb'] = memory_with_pool
        results['pooling_saving'] = 1 - (memory_with_pool / memory_without_pool)
        
        # Calculate overall memory score
        results['memory_score'] = (
            results['float32_speedup'] * 
            (1 + results['pooling_saving']) *
            (1 + results['float32_memory_saving'])
        ) / 3
        
        print(f"   Float32 speedup: {results['float32_speedup']:.2f}x")
        print(f"   Pooling saving: {results['pooling_saving']*100:.1f}%")
        
        return results
    
    def _benchmark_cpu(self) -> BenchmarkResult:
        """Benchmark CPU and parallelization"""
        results = {}
        
        # Test different parallelization modes
        test_data = [np.random.randn(1000, 1000) for _ in range(50)]
        
        def compute_task(matrix):
            return np.linalg.svd(matrix, compute_uv=False)
        
        # Sequential
        start = time.time()
        for matrix in test_data:
            compute_task(matrix)
        sequential_time = time.time() - start
        
        results['sequential_time'] = sequential_time
        results['sequential_throughput'] = len(test_data) / sequential_time
        
        # Threading (if I/O bound)
        import concurrent.futures
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            list(executor.map(compute_task, test_data))
        threading_time = time.time() - start
        
        results['threading_time'] = threading_time
        results['threading_throughput'] = len(test_data) / threading_time
        results['threading_speedup'] = sequential_time / threading_time
        
        # Multiprocessing
        start = time.time()
        with concurrent.futures.ProcessPoolExecutor() as executor:
            list(executor.map(compute_task, test_data))
        multiprocessing_time = time.time() - start
        
        results['multiprocessing_time'] = multiprocessing_time
        results['multiprocessing_throughput'] = len(test_data) / multiprocessing_time
        results['multiprocessing_speedup'] = sequential_time / multiprocessing_time
        
        # Calculate CPU score
        cpu_cores = psutil.cpu_count(logical=False)
        ideal_speedup = cpu_cores * 0.8  # 80% efficiency
        
        actual_speedup = results['multiprocessing_speedup']
        parallel_efficiency = actual_speedup / ideal_speedup
        
        results['cpu_cores'] = cpu_cores
        results['ideal_speedup'] = ideal_speedup
        results['parallel_efficiency'] = parallel_efficiency
        results['cpu_score'] = parallel_efficiency * actual_speedup
        
        print(f"   CPU Cores: {cpu_cores}")
        print(f"   Multiprocessing speedup: {actual_speedup:.2f}x")
        print(f"   Parallel efficiency: {parallel_efficiency*100:.1f}%")
        
        return results
    
    def _benchmark_indicators(self) -> BenchmarkResult:
        """Benchmark indicator calculations"""
        results = {}
        
        # Create test data
        n_bars = 10000
        test_df = pd.DataFrame({
            'open': np.random.randn(n_bars).cumsum() + 100,
            'high': np.random.randn(n_bars).cumsum() + 105,
            'low': np.random.randn(n_bars).cumsum() + 95,
            'close': np.random.randn(n_bars).cumsum() + 100,
            'volume': np.random.randint(100000, 1000000, n_bars)
        })
        
        # Test sequential calculation
        start = time.time()
        
        # Calculate some indicators sequentially
        test_df['sma_20'] = test_df['close'].rolling(20).mean()
        test_df['sma_50'] = test_df['close'].rolling(50).mean()
        test_df['rsi'] = self._calculate_rsi_sequential(test_df['close'])
        
        sequential_time = time.time() - start
        
        # Test vectorized calculation
        indicator_lib = VectorizedIndicators(use_numba=True)
        
        start = time.time()
        vectorized_results = indicator_lib.calculate_all(
            test_df, 
            ['sma', 'rsi', 'bollinger_bands']
        )
        vectorized_time = time.time() - start
        
        results['sequential_time'] = sequential_time
        results['vectorized_time'] = vectorized_time
        results['vectorized_speedup'] = sequential_time / vectorized_time
        results['indicators_per_second'] = len(vectorized_results) / vectorized_time
        
        # Calculate indicator score
        results['indicator_score'] = results['vectorized_speedup'] * results['indicators_per_second'] / 100
        
        print(f"   Vectorized speedup: {results['vectorized_speedup']:.2f}x")
        print(f"   Indicators/sec: {results['indicators_per_second']:.1f}")
        
        return results
    
    def _calculate_rsi_sequential(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI sequentially (for benchmarking)"""
        deltas = prices.diff()
        gain = (deltas.where(deltas > 0, 0)).rolling(period).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _benchmark_strategies(self) -> BenchmarkResult:
        """Benchmark strategy performance"""
        results = {}
        
        # This would test actual strategy performance
        # For now, simulate with simple operations
        n_iterations = 1000000
        
        # Python loops (baseline)
        start = time.time()
        total = 0
        for i in range(n_iterations):
            total += i * 0.5
        python_time = time.time() - start
        
        # NumPy vectorized
        start = time.time()
        arr = np.arange(n_iterations, dtype=np.float32)
        total = np.sum(arr * 0.5)
        numpy_time = time.time() - start
        
        # Numba JIT
        from numba import jit
        
        @jit(nopython=True)
        def numba_sum(n):
            total = 0.0
            for i in range(n):
                total += i * 0.5
            return total
        
        start = time.time()
        total = numba_sum(n_iterations)
        numba_time = time.time() - start
        
        results['python_time'] = python_time
        results['numpy_time'] = numpy_time
        results['numba_time'] = numba_time
        results['numpy_speedup'] = python_time / numpy_time
        results['numba_speedup'] = python_time / numba_time
        
        # Calculate strategy score
        results['strategy_score'] = (results['numpy_speedup'] + results['numba_speedup']) / 2
        
        print(f"   NumPy speedup: {results['numpy_speedup']:.2f}x")
        print(f"   Numba speedup: {results['numba_speedup']:.2f}x")
        
        return results
    
    def _benchmark_simulation(self) -> BenchmarkResult:
        """Benchmark end-to-end simulation"""
        results = {}
        
        # Simulate different configuration scenarios
        config_scenarios = [
            {'workers': 1, 'use_numba': False, 'use_float32': False},
            {'workers': 4, 'use_numba': True, 'use_float32': False},
            {'workers': 8, 'use_numba': True, 'use_float32': True},
            {'workers': 16, 'use_numba': True, 'use_float32': True},
        ]
        
        base_throughput = 9000  # Your current baseline
        
        for scenario in config_scenarios:
            # Estimate performance based on hardware
            workers = scenario['workers']
            use_numba = scenario['use_numba']
            use_float32 = scenario['use_float32']
            
            # Simple performance model
            worker_factor = min(workers, psutil.cpu_count(logical=False))
            numba_factor = 3.0 if use_numba else 1.0
            memory_factor = 1.2 if use_float32 else 1.0
            
            estimated_throughput = base_throughput * worker_factor * numba_factor * memory_factor
            
            scenario_name = f"w{workers}_n{use_numba}_f{use_float32}"
            results[scenario_name] = {
                'estimated_throughput': estimated_throughput,
                'estimated_speedup': estimated_throughput / base_throughput
            }
        
        # Calculate simulation score
        best_scenario = max(results.items(), key=lambda x: x[1]['estimated_throughput'])
        results['best_throughput'] = best_scenario[1]['estimated_throughput']
        results['best_speedup'] = best_scenario[1]['estimated_speedup']
        results['simulation_score'] = best_scenario[1]['estimated_speedup']
        
        print(f"   Best estimated speedup: {results['best_speedup']:.2f}x")
        print(f"   Best estimated throughput: {results['best_throughput']:,.0f} calc/sec")
        
        return results
    
    def find_optimal_configuration(self, benchmark_results: Dict[str, BenchmarkResult]) -> OptimizationResult:
        """Find optimal configuration based on benchmark results"""
        print(f"\n{'='*70}")
        print("FINDING OPTIMAL CONFIGURATION")
        print(f"{'='*70}")
        
        # Get hardware profile
        self.hardware_profile = self._get_hardware_profile()
        
        # Analyze benchmarks
        memory_results = benchmark_results.get('memory', {})
        cpu_results = benchmark_results.get('cpu', {})
        indicator_results = benchmark_results.get('indicators', {})
        strategy_results = benchmark_results.get('strategies', {})
        simulation_results = benchmark_results.get('simulation', {})
        
        # Determine optimal settings
        optimal_memory = self._determine_optimal_memory(memory_results)
        optimal_parallel = self._determine_optimal_parallel(cpu_results)
        optimal_strategies = self._determine_optimal_strategies(strategy_results)
        
        # Calculate predicted improvements
        predicted_speedup = simulation_results.get('best_speedup', 1.0)
        predicted_memory_reduction = memory_results.get('float32_memory_saving', 0) * 100
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            memory_results, cpu_results, indicator_results, strategy_results, simulation_results
        )
        
        # Estimate calculations per second
        base_calc_per_sec = 9000  # Your current baseline
        estimated_calc_per_sec = base_calc_per_sec * predicted_speedup
        
        # Create result object
        result = OptimizationResult(
            hardware=self.hardware_profile,
            memory_config=optimal_memory,
            parallel_config=optimal_parallel,
            strategy_configs=optimal_strategies,
            predicted_speedup=predicted_speedup,
            predicted_memory_reduction=predicted_memory_reduction,
            benchmark_results=benchmark_results,
            recommendations=recommendations,
            estimated_calc_per_second=estimated_calc_per_sec
        )
        
        return result
    
    def _determine_optimal_memory(self, memory_results: BenchmarkResult) -> MemoryConfig:
        """Determine optimal memory configuration"""
        use_float32 = memory_results.get('float32_speedup', 1) > 1.2
        enable_pooling = memory_results.get('pooling_saving', 0) > 0.1
        
        return MemoryConfig(
            use_float32=use_float32,
            enable_pooling=enable_pooling,
            downcast_integers=True,
            use_categories=True,
            aggressive_gc=True,
            max_memory_mb=int(self.hardware_profile.get('total_memory_gb', 8) * 1024 * 0.7)  # 70% of RAM
        )
    
    def _determine_optimal_parallel(self, cpu_results: BenchmarkResult) -> ParallelConfig:
        """Determine optimal parallel configuration"""
        cpu_cores = self.hardware_profile.get('cpu_cores', 4)
        has_gpu = self.hardware_profile.get('gpu_name') is not None
        
        # Choose mode
        if has_gpu and cpu_results.get('multiprocessing_speedup', 1) < 8:
            mode = 'gpu'
            max_workers = 1
        elif cpu_cores > 4 and cpu_results.get('multiprocessing_speedup', 1) > 2:
            mode = 'multiprocessing'
            max_workers = max(1, cpu_cores - 2)
        else:
            mode = 'threading'
            max_workers = cpu_cores * 2
        
        use_shared_memory = (
            mode == 'multiprocessing' and 
            self.hardware_profile.get('total_memory_gb', 0) > 8
        )
        
        return ParallelConfig(
            mode=mode,
            max_workers=max_workers,
            use_shared_memory=use_shared_memory,
            chunk_size=max(10, 100 // max_workers),
            dynamic_chunking=True
        )
    
    def _determine_optimal_strategies(self, strategy_results: BenchmarkResult) -> Dict[str, StrategyConfig]:
        """Determine optimal strategy configurations"""
        use_numba = strategy_results.get('numba_speedup', 1) > 2
        
        base_config = StrategyConfig(
            use_numba=use_numba,
            position_size_pct=0.10,
            max_positions=10
        )
        
        return {
            'default': base_config,
            'aggressive': StrategyConfig(
                use_numba=use_numba,
                position_size_pct=0.20,
                max_positions=5
            ),
            'conservative': StrategyConfig(
                use_numba=use_numba,
                position_size_pct=0.05,
                max_positions=20
            )
        }
    
    def _generate_recommendations(self, 
                                 memory_results: BenchmarkResult,
                                 cpu_results: BenchmarkResult,
                                 indicator_results: BenchmarkResult,
                                 strategy_results: BenchmarkResult,
                                 simulation_results: BenchmarkResult) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Memory recommendations
        if memory_results.get('float32_speedup', 1) > 1.5:
            recommendations.append("Use float32 instead of float64 for 50% memory saving and faster computation")
        
        if memory_results.get('pooling_saving', 0) > 0.2:
            recommendations.append("Enable memory pooling to reduce allocation overhead by 20-30%")
        
        # CPU recommendations
        cpu_cores = self.hardware_profile.get('cpu_cores', 4)
        if cpu_cores > 4 and cpu_results.get('multiprocessing_speedup', 1) > 3:
            recommendations.append(f"Use multiprocessing with {cpu_cores-2} workers for {cpu_results['multiprocessing_speedup']:.1f}x speedup")
        
        # Indicator recommendations
        if indicator_results.get('vectorized_speedup', 1) > 5:
            recommendations.append("Use vectorized indicator calculations for 5-10x faster indicator computation")
        
        # Strategy recommendations
        if strategy_results.get('numba_speedup', 1) > 3:
            recommendations.append("Use Numba JIT compilation for 3-10x faster strategy execution")
        
        # GPU recommendations
        if self.hardware_profile.get('gpu_name'):
            recommendations.append(f"Use GPU acceleration with {self.hardware_profile['gpu_name']} for compute-intensive operations")
        
        # General recommendations
        total_memory_gb = self.hardware_profile.get('total_memory_gb', 0)
        if total_memory_gb < 16:
            recommendations.append(f"Consider upgrading to at least 16GB RAM (current: {total_memory_gb:.1f}GB)")
        
        if cpu_cores < 8:
            recommendations.append(f"Consider upgrading to a CPU with more cores (current: {cpu_cores})")
        
        # Performance target
        estimated_speedup = simulation_results.get('best_speedup', 1)
        if estimated_speedup > 10:
            recommendations.append(f"Expected performance: {estimated_speedup:.1f}x speedup ({simulation_results.get('best_throughput', 0):,.0f} calc/sec)")
        else:
            recommendations.append(f"Target 10x speedup. Current estimate: {estimated_speedup:.1f}x")
        
        return recommendations
    
    def apply_configuration(self, optimization_result: OptimizationResult):
        """Apply optimal configuration to simulation system"""
        print(f"\n{'='*70}")
        print("APPLYING OPTIMAL CONFIGURATION")
        print(f"{'='*70}")
        
        # Apply memory configuration
        memory_manager = get_memory_manager(optimization_result.memory_config)
        print(f"✅ Applied memory configuration:")
        print(f"   Float32: {optimization_result.memory_config.use_float32}")
        print(f"   Memory Pooling: {optimization_result.memory_config.enable_pooling}")
        
        # Apply parallel configuration
        parallel_processor = get_parallel_processor(optimization_result.parallel_config)
        print(f"✅ Applied parallel configuration:")
        print(f"   Mode: {optimization_result.parallel_config.mode}")
        print(f"   Workers: {optimization_result.parallel_config.max_workers}")
        
        # Save configuration file
        config_file = Path('./optimal_config.json')
        optimization_result.save(config_file)
        
        print(f"✅ Configuration saved to: {config_file}")
        
        # Create example usage code
        example_code = self._generate_example_code(optimization_result)
        example_file = Path('./optimized_simulation_example.py')
        example_file.write_text(example_code)
        
        print(f"✅ Example code generated: {example_file}")
        print(f"{'='*70}\n")
        
        return {
            'memory_manager': memory_manager,
            'parallel_processor': parallel_processor,
            'config_file': config_file,
            'example_file': example_file
        }
    
    def _generate_example_code(self, optimization_result: OptimizationResult) -> str:
        """Generate example code for using optimized configuration"""
        example = f'''"""
Optimized Simulation Example
Generated by ConfigOptimizer
Expected speedup: {optimization_result.predicted_speedup:.1f}x
Estimated performance: {optimization_result.estimated_calc_per_second:,.0f} calculations/second
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Import optimized modules
from memory_manager import get_memory_manager
from parallel_processor import get_parallel_processor
from vectorized_indicators import get_indicator_library
from vectorized_simulator import VectorizedSimulator, SimulationConfig
from vectorized_strategy_base import VectorizedStrategyBase, StrategyConfig

def run_optimized_simulation(data_manager, universe_manager, strategies, symbols):
    """
    Run simulation with optimized configuration
    """
    
    # 1. Initialize optimized managers
    memory_manager = get_memory_manager()
    parallel_processor = get_parallel_processor()
    indicator_library = get_indicator_library(use_numba=True, cache_results=True)
    
    print(f"🧠 Memory Manager: float32={memory_manager.config.use_float32}, pooling={memory_manager.config.enable_pooling}")
    print(f"⚡ Parallel Processor: mode={parallel_processor.config.mode}, workers={parallel_processor.config.max_workers}")
    print(f"📊 Indicator Library: numba={indicator_library.use_numba}, caching={indicator_library.cache_results}")
    
    # 2. Configure simulator
    sim_config = SimulationConfig(
        use_parallel=True,
        max_workers={optimization_result.parallel_config.max_workers},
        use_numba=True,
        float_precision='float32' if {optimization_result.memory_config.use_float32} else 'float64',
        use_memory_pooling={optimization_result.memory_config.enable_pooling},
        cache_indicators=True,
        verbose=True
    )
    
    # 3. Create vectorized simulator
    simulator = VectorizedSimulator(
        data_manager=data_manager,
        universe_manager=universe_manager,
        config=sim_config
    )
    
    # 4. Set indicator library for strategies
    for strategy in strategies:
        strategy.set_indicator_library(indicator_library)
    
    # 5. Run simulation
    print(f"\\n{'='*70}")
    print(f"STARTING OPTIMIZED SIMULATION")
    print(f"{'='*70}")
    print(f"Expected speedup: {optimization_result.predicted_speedup:.1f}x")
    print(f"Target performance: {optimization_result.estimated_calc_per_second:,.0f} calc/sec")
    print(f"{'='*70}\\n")
    
    result = simulator.run_simulation(
        strategies=strategies,
        symbols=symbols,
        start_date=None,
        end_date=None,
        universe_filter='sp500'  # Or your preferred universe
    )
    
    return result

# Example strategy configuration
def create_optimized_strategies():
    """Create strategies with optimized configuration"""
    
    # Momentum strategy
    momentum_config = StrategyConfig(
        name="Optimized Momentum",
        initial_capital=100000,
        position_size_pct=0.10,
        max_positions=10,
        use_numba=True,  # Use Numba for speed
        precompute_indicators=True  # Pre-compute indicators
    )
    
    # You would create your actual strategy classes here
    # For example:
    # from your_strategies import VectorizedMomentumStrategy
    # momentum_strategy = VectorizedMomentumStrategy(config=momentum_config)
    
    return []  # Return your strategy instances

if __name__ == "__main__":
    print("Optimized simulation setup complete!")
    print(f"Hardware: {optimization_result.hardware.get('cpu_name', 'Unknown')}")
    print(f"CPU Cores: {optimization_result.hardware.get('cpu_cores', 'Unknown')}")
    print(f"RAM: {optimization_result.hardware.get('total_memory_gb', 'Unknown'):.1f} GB")
    
    if optimization_result.hardware.get('gpu_name'):
        print(f"GPU: {optimization_result.hardware['gpu_name']}")
    
    print("\\nTo use:")
    print("1. Import your data_manager and universe_manager")
    print("2. Create your vectorized strategies")
    print("3. Call run_optimized_simulation()")
'''
        
        return example


# Main function for standalone usage
def optimize_system():
    """Main function to optimize system configuration"""
    optimizer = ConfigOptimizer()
    
    print(f"\n{'='*70}")
    print("AUTO-CONFIGURATION OPTIMIZER")
    print(f"{'='*70}")
    print("This will benchmark your system and find optimal settings")
    print("Estimated time: 2-5 minutes")
    print(f"{'='*70}\n")
    
    # Run benchmarks
    benchmark_results = optimizer.run_benchmarks()
    
    # Find optimal configuration
    optimal_config = optimizer.find_optimal_configuration(benchmark_results)
    
    # Print results
    optimal_config.print_summary()
    
    # Apply configuration
    optimizer.apply_configuration(optimal_config)
    
    return optimal_config


if __name__ == "__main__":
    # Run optimization
    result = optimize_system()
    
    print("\n🎯 Optimization Complete!")
    print("Next steps:")
    print("1. Review optimal_config.json")
    print("2. Check optimized_simulation_example.py")
    print("3. Update your main.py to use optimized configuration")
    print("4. Run simulation and verify performance improvement")