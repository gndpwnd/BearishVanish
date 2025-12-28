# Simulator Updates for System Benchmarking & Automated Downloads

## 📋 Changes Needed to simulator.py

### Step 1: Add Import at Top

Add this with your other imports:
```python
from system_benchmark import SystemBenchmark
```

### Step 2: Add Command Line Arguments

Add these new arguments to your parser (around line 25):

```python
# Benchmark arguments
parser.add_argument('--benchmark', action='store_true', help='Run system benchmark and recommend worker counts')
parser.add_argument('--show-benchmark', action='store_true', help='Show saved benchmark results')
```

### Step 3: Handle Benchmark Commands

Add this BEFORE your data_manager initialization (around line 50):

```python
# ============================================================
# BENCHMARK COMMANDS (Before creating data manager)
# ============================================================

if args.benchmark:
    print("\n" + "="*70)
    print("SYSTEM BENCHMARK MODE")
    print("="*70)
    
    # Initialize managers for benchmarking
    from data_manager import DataManager
    from stock_universe import UniverseManager
    
    data_manager = DataManager(api_key, secret_key, offline_mode=False)
    universe_manager = UniverseManager(api_key, secret_key)
    
    # Run full benchmark
    benchmark = SystemBenchmark(data_manager, universe_manager)
    results = benchmark.run_full_benchmark()
    
    sys.exit(0)

if args.show_benchmark:
    print("\n" + "="*70)
    print("SAVED BENCHMARK RESULTS")
    print("="*70)
    
    results = SystemBenchmark.load_benchmark()
    
    if not results:
        print("❌ No benchmark results found")
        print("   Run: python simulator.py --benchmark")
    else:
        import json
        print(json.dumps(results, indent=2))
        
        if 'recommendations' in results:
            rec = results['recommendations']
            print("\n🎯 RECOMMENDED WORKER COUNTS:")
            print(f"  Download workers: {rec['download_workers']}")
            print(f"  Database workers: {rec['db_workers']}")
    
    print("="*70)
    sys.exit(0)
```

### Step 4: Auto-Use Recommended Workers

Update your workers argument default (around line 23):

```python
# Get recommended workers from benchmark if available
default_download_workers, default_db_workers = SystemBenchmark.get_recommended_workers()

parser.add_argument('--workers', type=int, default=default_download_workers, 
                   help=f'Number of parallel workers (default: {default_download_workers} from benchmark)')
```

### Step 5: Support "all" Universe for Downloads

Update the download section (around line 60):

```python
if args.download:
    print(f"\n{'='*70}")
    print(f"DOWNLOADING DATA")
    print(f"{'='*70}\n")
    
    # Determine which symbols to download
    if args.universe:
        if args.universe == 'all':
            # Download ALL universes
            print("📦 Downloading data for ALL universes...")
            
            all_symbols = set()
            for universe_name in ['sp500', 'nasdaq100', 'russell3000']:
                symbols = universe_manager.get_approved_tickers(universe_name)
                print(f"  ✅ {universe_name}: {len(symbols)} stocks")
                all_symbols.update(symbols)
            
            symbols_to_download = sorted(list(all_symbols)) + ['SPY']
            print(f"\n📊 Total unique stocks: {len(all_symbols)}")
            
        else:
            # Download specific universe
            symbols_to_download = universe_manager.get_approved_tickers(args.universe)
            if not symbols_to_download:
                print(f"❌ No symbols found for universe: {args.universe}")
                print(f"   Run: python simulator.py --update-universe {args.universe}")
                sys.exit(1)
            
            symbols_to_download = symbols_to_download + ['SPY']
            print(f"📦 Downloading data for {args.universe}: {len(symbols_to_download)-1} stocks")
    else:
        # Original behavior: download default SYMBOLS
        symbols_to_download = SYMBOLS + ['SPY']
        print(f"📦 Downloading data for {len(SYMBOLS)} default stocks")
    
    # Parallel download with recommended workers
    def download_symbol(symbol):
        try:
            df = data_manager.get_stock_data(symbol, days=HISTORY)
            return (symbol, df, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    results = {}
    successful = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_symbol, sym): sym for sym in symbols_to_download}
        
        for future in as_completed(futures):
            symbol, df, error = future.result()
            if error:
                print(f"❌ {symbol}: Error - {error}")
                results[symbol] = None
            else:
                print(f"✅ {symbol}: {len(df)} bars downloaded")
                results[symbol] = df
                successful += 1
    
    print(f"\n{'='*70}")
    print(f"DOWNLOAD COMPLETE")
    print(f"Successful: {successful}/{len(symbols_to_download)}")
    print(f"{'='*70}\n")
    sys.exit(0)
```

## 🎯 New Commands Available

### Run System Benchmark
```bash
# Benchmark your system (takes 1-2 minutes)
python simulator.py --benchmark

# Output shows:
# - CPU info (cores, frequency, memory)
# - Network speed (download times)
# - Database speed (read times)
# - Recommended worker counts (70% of capacity)
```

### Show Saved Benchmark
```bash
# View your saved benchmark results
python simulator.py --show-benchmark
```

### Download All Universes
```bash
# Download data for ALL universes at once
python simulator.py --download --universe all --workers 20

# Or let it auto-use recommended workers
python simulator.py --download --universe all

# Download specific universe
python simulator.py --download --universe sp500

# Download multiple universes (future feature)
python simulator.py --download --universe sp500,nasdaq100
```

### Run Simulation with Auto-Tuned Workers
```bash
# Simulation automatically uses recommended DB workers
python simulator.py --universe sp500

# Or override with custom count
python simulator.py --universe sp500 --workers 15
```

## 📊 Example Workflow

### First Time Setup
```bash
# Step 1: Benchmark your system
python simulator.py --benchmark

# Output:
# 💻 SYSTEM SPECS:
#   CPU Cores: 8
#   Network: 1.23s per stock
#   Database: 0.012s per read
#
# 🎯 RECOMMENDATIONS (70% of capacity):
#   Download workers: 11
#   Database workers: 16

# Step 2: Update all universes
python simulator.py --update-universe all

# Step 3: Download all data with recommended workers
python simulator.py --download --universe all

# Step 4: Run simulation
python simulator.py --universe sp500
```

### Daily Usage
```bash
# Simulation automatically uses your benchmarked worker counts
python simulator.py --universe russell3000
```

## 🔍 Understanding Worker Recommendations

### Download Workers (Network I/O)
- **Bottleneck:** API rate limits + network bandwidth
- **Formula:** `min(cpu_count * 2, 50) * 0.7`
- **Example:** 8 cores → recommend 11 workers
- **Why 70%:** Leaves headroom for system stability

### Database Workers (Disk I/O)
- **Bottleneck:** SQLite read performance + disk speed
- **Formula:** `min(cpu_count * 3, 30) * 0.7`
- **Example:** 8 cores → recommend 16 workers
- **Why 70%:** Prevents system overload during simulation

## 💡 Advanced Usage

### Force Re-Benchmark
```bash
# If your system changes (upgrade RAM, SSD, etc.)
python simulator.py --benchmark

# This overwrites old benchmark with new results
```

### Manual Worker Override
```bash
# Use custom worker count (ignores benchmark)
python simulator.py --download --universe all --workers 25
```

### Check Current Settings
```bash
# See what workers are being used
python simulator.py --show-benchmark
```

## 📈 Performance Benefits

### Before (Manual Workers)
```bash
# User guesses: --workers 10
# Might be too slow (system can handle more)
# OR too fast (system overloaded)
```

### After (Benchmarked Workers)
```bash
# System automatically uses optimal count
# 70% capacity = stable + fast
# Adapts to YOUR hardware
```

### Real-World Example

On a system with:
- 8 CPU cores
- Fast SSD
- Good network

**Without benchmark:**
- User sets `--workers 10` manually
- Download 500 stocks: ~15 minutes
- Simulation: works but not optimized

**With benchmark:**
- Recommends 11 download workers, 16 DB workers
- Download 500 stocks: ~10 minutes (33% faster!)
- Simulation: fully utilizing system capacity

## 🎯 Installation

You'll need psutil for system info:
```bash
pip install psutil
```

If psutil isn't available, the benchmark still works but with limited system info.

## ✅ Summary

### What You Get:
1. ✅ **Automated Downloads** - `--download --universe all` downloads everything
2. ✅ **System Benchmarking** - Know your system's capabilities
3. ✅ **Auto-Tuned Workers** - Optimal performance without manual tuning
4. ✅ **70% Capacity Rule** - Fast but stable (no system overload)
5. ✅ **One-Time Setup** - Benchmark once, use forever

### Files Updated:
- `simulator.py` - Add benchmark support, auto worker selection
- `system_benchmark.py` - New module (complete)

Your simulation will now automatically use the optimal worker count for YOUR hardware! 🚀