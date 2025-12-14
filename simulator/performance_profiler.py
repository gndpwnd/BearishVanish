"""
Performance Profiler - Identifies exact bottlenecks in simulation
Line-by-line profiling, memory tracking, and query timing
"""

import time
import cProfile
import pstats
import io
import tracemalloc
import psutil
import line_profiler
from functools import wraps
from datetime import datetime
from pathlib import Path
import json

PROFILE_DIR = Path('./profiling')
PROFILE_DIR.mkdir(exist_ok=True)

class PerformanceProfiler:
    """Comprehensive performance profiling for simulation engine"""
    
    def __init__(self, name="simulation"):
        self.name = name
        self.profiler = cProfile.Profile()
        self.start_time = None
        self.memory_snapshots = []
        self.timestamps = []
        self.metrics = {}
        self.line_profiler = line_profiler.LineProfiler()
        
    def start(self):
        """Start profiling session"""
        self.start_time = time.time()
        tracemalloc.start()
        self.profiler.enable()
        
        # Record initial memory
        process = psutil.Process()
        self.memory_snapshots.append({
            'timestamp': time.time(),
            'rss_mb': process.memory_info().rss / 1024**2,
            'vms_mb': process.memory_info().vms / 1024**2,
            'cpu_percent': process.cpu_percent()
        })
        
        print(f"🔍 Starting performance profiling: {self.name}")
        return self
    
    def checkpoint(self, label):
        """Record a checkpoint with current metrics"""
        process = psutil.Process()
        elapsed = time.time() - self.start_time
        
        snapshot = {
            'label': label,
            'elapsed_seconds': elapsed,
            'timestamp': time.time(),
            'rss_mb': process.memory_info().rss / 1024**2,
            'vms_mb': process.memory_info().vms / 1024**2,
            'cpu_percent': process.cpu_percent(),
            'threads': process.num_threads(),
            'context_switches': process.num_ctx_switches()
        }
        
        self.memory_snapshots.append(snapshot)
        print(f"📊 {label}: {elapsed:.2f}s, {snapshot['rss_mb']:.1f}MB RAM")
        
    def profile_function(self, func):
        """Decorator to profile a specific function"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start line profiler for this function
            profiler = line_profiler.LineProfiler()
            profiler.add_function(func)
            profiler.enable_by_count()
            
            result = func(*args, **kwargs)
            
            profiler.disable_by_count()
            
            # Save line profile
            output = io.StringIO()
            profiler.print_stats(stream=output, output_unit=1e-3)  # milliseconds
            stats_str = output.getvalue()
            
            # Save to file
            profile_file = PROFILE_DIR / f"line_profile_{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            profile_file.write_text(stats_str)
            print(f"📈 Line profile saved for {func.__name__}: {profile_file}")
            
            return result
        return wrapper
    
    def profile_method(self, method):
        """Decorator for profiling class methods"""
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            func_name = f"{self.__class__.__name__}.{method.__name__}"
            start = time.time()
            
            result = method(self, *args, **kwargs)
            
            elapsed = time.time() - start
            if elapsed > 0.1:  # Only log if significant
                print(f"⏱️  {func_name}: {elapsed:.3f}s")
                
            return result
        return wrapper
    
    def stop(self):
        """Stop profiling and generate reports"""
        self.profiler.disable()
        
        # Generate cProfile stats
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions
        stats_output = s.getvalue()
        
        # Save all reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. cProfile report
        cprofile_file = PROFILE_DIR / f"cprofile_{self.name}_{timestamp}.txt"
        cprofile_file.write_text(stats_output)
        
        # 2. Memory timeline report
        memory_data = {
            'name': self.name,
            'start_time': self.start_time,
            'end_time': time.time(),
            'total_duration': time.time() - self.start_time,
            'snapshots': self.memory_snapshots,
            'metrics': self.metrics
        }
        
        memory_file = PROFILE_DIR / f"memory_{self.name}_{timestamp}.json"
        memory_file.write_text(json.dumps(memory_data, indent=2, default=str))
        
        # 3. HTML report for visualization
        self._generate_html_report(memory_data, timestamp)
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"PERFORMANCE PROFILE COMPLETE: {self.name}")
        print(f"{'='*70}")
        print(f"📊 Total time: {time.time() - self.start_time:.2f}s")
        print(f"📈 Peak memory: {max(s['rss_mb'] for s in self.memory_snapshots):.1f} MB")
        print(f"📁 Reports saved to: {PROFILE_DIR}")
        print(f"   • {cprofile_file.name} - Function timing")
        print(f"   • {memory_file.name} - Memory timeline")
        print(f"   • profile_{self.name}_{timestamp}.html - Visual report")
        print(f"{'='*70}\n")
        
        return {
            'cprofile_file': cprofile_file,
            'memory_file': memory_file,
            'total_time': time.time() - self.start_time
        }
    
    def _generate_html_report(self, memory_data, timestamp):
        """Generate HTML visualization of performance data"""
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Profile: {self.name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .chart-container {{ margin: 20px 0; height: 400px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <h1>Performance Profile: {self.name}</h1>
    <div class="summary">
        <p><strong>Total Duration:</strong> {memory_data['total_duration']:.2f} seconds</p>
        <p><strong>Number of Snapshots:</strong> {len(memory_data['snapshots'])}</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="grid">
        <div class="chart-container">
            <canvas id="memoryChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="cpuChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="timelineChart"></canvas>
        </div>
    </div>
    
    <script>
        // Prepare data
        const snapshots = {json.dumps(memory_data['snapshots'])};
        
        const labels = snapshots.map(s => s.label || 'Checkpoint');
        const memoryData = snapshots.map(s => s.rss_mb);
        const cpuData = snapshots.map(s => s.cpu_percent);
        const elapsedData = snapshots.map(s => s.elapsed_seconds);
        
        // Memory Chart
        new Chart(document.getElementById('memoryChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'RSS Memory (MB)',
                    data: memoryData,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    fill: true,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Memory Usage Over Time'
                    }}
                }}
            }}
        }});
        
        // CPU Chart
        new Chart(document.getElementById('cpuChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'CPU Usage (%)',
                    data: cpuData,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'CPU Usage Per Checkpoint'
                    }}
                }}
            }}
        }});
        
        // Timeline Chart
        new Chart(document.getElementById('timelineChart'), {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Execution Timeline',
                    data: snapshots.map((s, i) => ({{
                        x: s.elapsed_seconds,
                        y: i,
                        r: Math.sqrt(s.rss_mb) / 10
                    }})),
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgb(75, 192, 192)'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Elapsed Time (seconds)'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Checkpoint Index'
                        }},
                        ticks: {{
                            callback: function(value, index, values) {{
                                return snapshots[value]?.label || value;
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Execution Timeline with Memory Size'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const snapshot = snapshots[context.dataIndex];
                                return [
                                    `Checkpoint: ${{snapshot.label}}`,
                                    `Time: ${{snapshot.elapsed_seconds.toFixed(2)}}s`,
                                    `Memory: ${{snapshot.rss_mb.toFixed(1)}} MB`,
                                    `CPU: ${{snapshot.cpu_percent}}%`
                                ];
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        html_file = PROFILE_DIR / f"profile_{self.name}_{timestamp}.html"
        html_file.write_text(html_template)
    
    def benchmark_operation(self, operation_name, operation, *args, **kwargs):
        """Benchmark a specific operation with detailed timing"""
        import timeit
        
        # Warm up
        for _ in range(3):
            operation(*args, **kwargs)
        
        # Time it
        timer = timeit.Timer(lambda: operation(*args, **kwargs))
        
        # Run multiple times for accuracy
        n_runs = 10
        total_time = timer.timeit(number=n_runs)
        avg_time = total_time / n_runs
        
        # Memory before/after
        process = psutil.Process()
        mem_before = process.memory_info().rss
        
        result = operation(*args, **kwargs)
        
        mem_after = process.memory_info().rss
        mem_diff = (mem_after - mem_before) / 1024**2  # MB
        
        self.metrics[operation_name] = {
            'avg_time_seconds': avg_time,
            'total_time_seconds': total_time,
            'n_runs': n_runs,
            'memory_change_mb': mem_diff,
            'operations_per_second': 1 / avg_time if avg_time > 0 else float('inf')
        }
        
        print(f"⚡ {operation_name}:")
        print(f"   Time: {avg_time*1000:.2f}ms per run ({total_time:.3f}s total)")
        print(f"   Speed: {1/avg_time:.0f} ops/sec")
        print(f"   Memory: {mem_diff:+.1f} MB")
        
        return result
    
    def track_query_performance(self, db_path):
        """Track SQLite query performance"""
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA temp_store = MEMORY')
        conn.execute('PRAGMA journal_mode = WAL')
        
        # Enable query logging
        conn.set_trace_callback(lambda query: self._log_query(query))
        
        return conn
    
    def _log_query(self, query):
        """Log SQL query for performance analysis"""
        query = query.strip()
        if query.startswith('SELECT') or query.startswith('INSERT'):
            start = time.time()
            # We can't time it here, but we can log it
            self.timestamps.append({
                'query': query[:100] + ('...' if len(query) > 100 else ''),
                'timestamp': time.time(),
                'length': len(query)
            })


# Singleton instance for easy access
_profiler = None

def get_profiler(name="simulation"):
    """Get or create global profiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler(name)
    return _profiler


def profile(func):
    """Decorator for profiling functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = get_profiler()
        return profiler.profile_function(func)(*args, **kwargs)
    return wrapper


def profile_class_methods(cls):
    """Class decorator to profile all methods"""
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            setattr(cls, attr_name, profile(attr))
    return cls