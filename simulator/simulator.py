"""
Stock Trading Strategy Simulator - With Universe Management and System Benchmarking
Main entry point for backtesting trading strategies with automatic position liquidation

KEY CHANGES FROM ORIGINAL:
1. max_positions increased from 5 to 10 (line ~735)
2. End-of-simulation liquidation added (line ~900)
3. force_liquidate_all() method support added
4. Optional liquidation and universe checking flags added
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import importlib.util
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import sqlite3

from data_manager import DataManager
from stock_universe import UniverseManager
from strategy_tracker import StrategyTracker, INITIAL_CASH
from strategy_analysis import show_strategy_analysis
from system_benchmark import SystemBenchmark
import time

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Get recommended workers from benchmark if available
default_download_workers = SystemBenchmark.get_recommended_workers()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Stock Strategy Simulator')

# Data management arguments
parser.add_argument('--cache-status', action='store_true', help='Show offline cache status')
parser.add_argument('--download', action='store_true', help='Download data for symbols')
parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers to download')
parser.add_argument('--offline', action='store_true', help='Run in offline mode')
parser.add_argument('--workers', type=int, default=default_download_workers,
                   help=f'Number of workers for API downloads (default: {default_download_workers} from benchmark)')

# Universe management arguments
parser.add_argument('--update-universe', type=str, help='Update universe: sp500, nasdaq100, russell3000, or all')
parser.add_argument('--universe', type=str, help='Run simulation with specific universe')
parser.add_argument('--universe-status', action='store_true', help='Show universe status')
parser.add_argument('--check-ticker', type=str, help='Check if a ticker is in any universe')
parser.add_argument('--clear-universe', type=str, help='Clear universe data')

# Diagnostic arguments
parser.add_argument('--diagnose', type=str, help='Diagnose mismatch for universe')
parser.add_argument('--check-quality', type=str, help='Check data quality for universe')
parser.add_argument('--find-duplicates', type=str, help='Find duplicate ticker issues')
parser.add_argument('--compare', nargs=2, help='Compare two universes')

# Validation arguments
parser.add_argument('--validate', type=str, help='Validate tickers for universe')
parser.add_argument('--cleanup-db', action='store_true', help='Clean up database')

# Benchmark arguments
parser.add_argument('--benchmark', action='store_true', help='Run network benchmark')
parser.add_argument('--show-benchmark', action='store_true', help='Show saved benchmark results')

# Strategy testing arguments
parser.add_argument('--force-liquidate', action='store_true', 
                   help='Force liquidation of all positions at end of simulation')
parser.add_argument('--no-universe-check', action='store_true',
                   help='Disable universe checking during simulation')

args = parser.parse_args()

# Configuration
HISTORY = 180  # 6 months of data
TOTAL_DURATION = 3.0  # seconds for visualization
strategy_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# ============================================================
# BENCHMARK COMMANDS (Before creating data manager)
# ============================================================

if args.benchmark:
    print("\n" + "="*70)
    print("SYSTEM BENCHMARK MODE")
    print("="*70)
    
    # Initialize managers for benchmarking
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

# Initialize managers
data_manager = DataManager(api_key, secret_key, offline_mode=args.offline)
universe_manager = UniverseManager(api_key, secret_key)

# ============================================================
# UNIVERSE MANAGEMENT COMMANDS
# ============================================================

if args.update_universe:
    print("\n" + "="*70)
    print("UNIVERSE UPDATE MODE")
    print("="*70)
    universe_manager.update_universe(args.update_universe)
    sys.exit(0)

if args.universe_status:
    universe_manager.print_status()
    sys.exit(0)

if args.check_ticker:
    universe_manager.print_ticker_info(args.check_ticker)
    sys.exit(0)

if args.clear_universe:
    universe_manager.clear_universe(args.clear_universe)
    sys.exit(0)

# ============================================================
# DIAGNOSTIC COMMANDS
# ============================================================

if args.diagnose:
    print("\n" + "="*70)
    print("UNIVERSE DIAGNOSTICS MODE")
    print("="*70)
    universe_manager.diagnose_mismatch(args.diagnose)
    sys.exit(0)

if args.check_quality:
    print("\n" + "="*70)
    print("DATA QUALITY CHECK MODE")
    print("="*70)
    if hasattr(universe_manager, 'diagnostics'):
        universe_manager.diagnostics.check_data_quality(args.check_quality)
    else:
        print("ERROR: diagnostics module not available")
    sys.exit(0)

if args.find_duplicates:
    print("\n" + "="*70)
    print("DUPLICATE ANALYSIS MODE")
    print("="*70)
    if hasattr(universe_manager, 'diagnostics'):
        universe_manager.diagnostics.find_duplicate_issues(args.find_duplicates)
    else:
        print("ERROR: diagnostics module not available")
    sys.exit(0)

if args.compare:
    print("\n" + "="*70)
    print("UNIVERSE COMPARISON MODE")
    print("="*70)
    if hasattr(universe_manager, 'diagnostics'):
        universe_manager.diagnostics.compare_universes(args.compare[0], args.compare[1])
    else:
        print("ERROR: diagnostics module not available")
    sys.exit(0)

# ============================================================
# VALIDATION COMMANDS
# ============================================================

if args.validate:
    print("\n" + "="*70)
    print("TICKER VALIDATION MODE")
    print("="*70)
    
    # Get tickers from universe
    tickers = universe_manager.get_approved_tickers(args.validate)
    
    if not tickers:
        print(f"No tickers found for {args.validate}")
        sys.exit(1)
    
    # Validate them
    from ticker_validation import TickerValidator
    valid, invalid, stats = TickerValidator.print_validation_report(tickers)
    
    if invalid:
        print(f"\n💡 TIP: Run --cleanup-db to remove invalid tickers from database")
    
    sys.exit(0)

if args.cleanup_db:
    print("\n" + "="*70)
    print("DATABASE CLEANUP MODE")
    print("="*70)
    
    from ticker_validation import TickerValidator
    import sqlite3
    
    conn = sqlite3.connect(universe_manager.db_path)
    cursor = conn.cursor()
    
    # Get all symbols from database
    cursor.execute('''
        SELECT DISTINCT symbol, universe_name
        FROM universe_constituents
        WHERE date_removed IS NULL
    ''')
    
    all_entries = cursor.fetchall()
    total_entries = len(all_entries)
    
    print(f"\n📊 Found {total_entries} active entries in database")
    print(f"🔍 Checking for invalid tickers...\n")
    
    invalid_count = 0
    for symbol, universe_name in all_entries:
        if not TickerValidator.is_valid(symbol):
            print(f"  ❌ Removing invalid ticker: '{symbol}' from {universe_name}")
            
            # Mark as removed
            cursor.execute('''
                UPDATE universe_constituents
                SET date_removed = ?
                WHERE symbol = ? AND universe_name = ? AND date_removed IS NULL
            ''', (date.today(), symbol, universe_name))
            
            invalid_count += 1
    
    if invalid_count > 0:
        conn.commit()
        print(f"\n✅ Removed {invalid_count} invalid tickers from database")
        print(f"📊 Remaining active entries: {total_entries - invalid_count}")
    else:
        print(f"✅ No invalid tickers found - database is clean!")
    
    conn.close()
    print(f"\n{'='*70}\n")
    sys.exit(0)

# ============================================================
# CACHE STATUS COMMAND
# ============================================================

if args.cache_status:
    data_manager.print_cache_status()
    sys.exit(0)

# ============================================================
# DOWNLOAD COMMAND - THREAD-SAFE VERSION
# ============================================================

if args.download:
    print(f"\n{'='*70}")
    print(f"DOWNLOADING DATA")
    print(f"{'='*70}\n")
    
    # Determine which symbols to download
    if args.tickers:
        symbols_to_download = [t.strip().upper() for t in args.tickers.split(',')]
        print(f"📦 Downloading specific tickers: {', '.join(symbols_to_download)}")
        
    elif args.universe:
        if args.universe == 'all':
            print("📦 Downloading data for ALL universes...")
            
            all_symbols = set()
            for universe_name in ['sp500', 'nasdaq100', 'russell3000']:
                symbols = universe_manager.get_approved_tickers(universe_name)
                print(f"  ✅ {universe_name}: {len(symbols)} stocks")
                all_symbols.update(symbols)
            
            symbols_to_download = sorted(list(all_symbols)) + ['SPY']
            print(f"\n📊 Total unique stocks: {len(all_symbols)}")
            
        else:
            symbols_to_download = universe_manager.get_approved_tickers(args.universe)
            if not symbols_to_download:
                print(f"❌ No symbols found for universe: {args.universe}")
                print(f"   Run: python simulator.py --update-universe {args.universe}")
                sys.exit(1)
            
            symbols_to_download = symbols_to_download + ['SPY']
            print(f"📦 Downloading data for {args.universe}: {len(symbols_to_download)-1} stocks")
    else:
        symbols_to_download = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META', 'SPY']
        print(f"📦 Downloading data for default stocks")
    
    print(f"🔧 Using {args.workers} parallel workers\n")
    
    # THREAD-SAFE DOWNLOAD FUNCTION
    def download_symbol_threadsafe(symbol):
        """Thread-safe version that creates its own DataManager instance"""
        try:
            # Create a NEW DataManager instance for this thread
            # This avoids SQLite threading issues
            thread_data_manager = DataManager(api_key, secret_key, offline_mode=False, quiet=True)
            df = thread_data_manager.get_stock_data(symbol, days=HISTORY)
            
            # Clean up
            del thread_data_manager
            
            return (symbol, df, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    # ALTERNATIVE: Sequential download for reliability
    def download_symbol_sequential(symbol, data_mgr, pbar=None):
        """Sequential download that uses the main DataManager instance"""
        try:
            df = data_mgr.get_stock_data(symbol, days=HISTORY)
            
            if pbar:
                pbar.update(1)
                if df is not None:
                    pbar.write(f"✅ {symbol}: {len(df)} bars")
                else:
                    pbar.write(f"⚠️  {symbol}: No data available")
            
            return (symbol, df, None)
        except Exception as e:
            if pbar:
                pbar.write(f"❌ {symbol}: {e}")
            return (symbol, None, str(e))
    
    print("🚀 OPTION: Starting RELIABLE sequential download...")
    print("💡 TIP: For large universes, sequential is more reliable than parallel")
    print("       due to SQLite threading limitations\n")
    
    # Ask user which method to use
    choice = input("Choose download method:\n"
                   "1. Sequential (Recommended - most reliable)\n"
                   "2. Parallel (Faster but may have errors)\n"
                   "Enter choice (1 or 2): ").strip()
    
    results = {}
    successful = 0
    failed = 0
    
    if choice == "2":
        # Parallel download with thread-safe function
        print(f"\nStarting parallel download with thread-safe workers...")
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(download_symbol_threadsafe, sym): sym for sym in symbols_to_download}
            
            for future in as_completed(futures):
                symbol, df, error = future.result()
                
                if error or df is None:
                    error_msg = error if error else "No data returned"
                    print(f"❌ {symbol}: Error - {error_msg}")
                    results[symbol] = None
                    failed += 1
                else:
                    print(f"✅ {symbol}: {len(df)} bars downloaded")
                    results[symbol] = df
                    successful += 1
    else:
        # Sequential download (default - most reliable)
        print(f"\nStarting reliable sequential download...")
        print("This may take a while for large universes...\n")
        
        # Check how many symbols already have data
        conn = sqlite3.connect(data_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT symbol FROM stock_bars')
        existing_symbols = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        missing_symbols = [s for s in symbols_to_download if s not in existing_symbols]
        
        print(f"📊 Download status:")
        print(f"   Total symbols: {len(symbols_to_download)}")
        print(f"   Already cached: {len(existing_symbols)}")
        print(f"   Need to download: {len(missing_symbols)}")
        
        if missing_symbols:
            print(f"\n📥 Downloading {len(missing_symbols)} symbols...")
            
            from tqdm import tqdm
            
            with tqdm(total=len(missing_symbols), desc="Downloading", unit="stock") as pbar:
                for symbol in missing_symbols:
                    symbol_result, df, error = download_symbol_sequential(symbol, data_manager, pbar)
                    
                    if error or df is None:
                        results[symbol] = None
                        failed += 1
                    else:
                        results[symbol] = df
                        successful += 1
        else:
            print(f"\n✅ All symbols already downloaded!")
            successful = len(symbols_to_download)
    
    # Check which symbols failed
    failed_symbols = [s for s in symbols_to_download if results.get(s) is None]
    
    print(f"\n{'='*70}")
    print(f"DOWNLOAD COMPLETE")
    print(f"Total: {len(symbols_to_download)} symbols")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed_symbols:
        print(f"\n❌ Failed symbols ({len(failed_symbols)}):")
        for i in range(0, len(failed_symbols), 10):
            print(f"   {', '.join(failed_symbols[i:i+10])}")
    
    print(f"\n💡 Next steps:")
    print(f"   - Run again to retry failed downloads")
    print(f"   - Try with --universe sp500 for a smaller test")
    print(f"   - Check your API key limits if many failures")
    print(f"{'='*70}\n")
    
    sys.exit(0)

# ============================================================
# SYMBOL SELECTION
# ============================================================

if args.universe:
    print(f"\n{'='*70}")
    print(f"LOADING SYMBOLS FROM {args.universe.upper()} UNIVERSE")
    print(f"{'='*70}")
    
    SYMBOLS = universe_manager.get_approved_tickers(args.universe)
    
    if not SYMBOLS:
        print(f"❌ No symbols found for universe: {args.universe}")
        print(f"   Run: python simulator.py --update-universe {args.universe}")
        sys.exit(1)
    
    print(f"✅ Loaded {len(SYMBOLS)} symbols from {args.universe}")
    print(f"   Sample: {SYMBOLS[:10]}")
    print(f"{'='*70}\n")
else:
    SYMBOLS = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META']
    print(f"\nUsing default symbols: {SYMBOLS}")

if args.offline:
    print("\n" + "="*70)
    print("RUNNING IN OFFLINE MODE")
    print("="*70)
    print("Using cached data only. Will fail if data is missing.")
    print("="*70 + "\n")

# ============================================================
# STRATEGY LOADING
# ============================================================

strategies = []
print_lock = threading.Lock()

def load_strategies():
    """Load all strategy files from strategies/ directory"""
    global strategies
    strategies = []
    
    strategies_dir = Path('strategies')
    if not strategies_dir.exists():
        print("Create 'strategies/' directory and add strategy files.")
        return
    
    strategy_files = sorted(list(strategies_dir.glob('strategy_*.py')))
    
    for idx, strategy_file in enumerate(strategy_files):
        try:
            module_name = f"strategy_module_{idx}_{strategy_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            if hasattr(module, 'Strategy'):
                color = strategy_colors[idx % len(strategy_colors)]
                strategy_instance = module.Strategy(color=color)
                
                filename_name = strategy_file.stem.replace('strategy_', '').replace('_', ' ').title()
                if not hasattr(strategy_instance, 'name') or strategy_instance.name == "Strategy":
                    strategy_instance.name = filename_name
                
                strategies.append(strategy_instance)
                print(f"Loaded: {strategy_instance.name} (color: {color})")
        except Exception as e:
            print(f"Error loading {strategy_file}: {e}")

# ============================================================
# DATA FETCHING
# ============================================================

def fetch_stock_data(symbol, days=HISTORY):
    """Fetch stock data using DataManager"""
    return data_manager.get_stock_data(symbol, days=days)

def fetch_stock_data_parallel(symbols, days=HISTORY):
    """
    🚀 OPTIMIZED: Fetch multiple stocks using batch loading
    This is 10-50x faster than loading symbols individually
    No workers needed - batch loading uses a single optimized query
    """
    
    print(f"\n📊 Loading {len(symbols)} symbols from database...")
    print(f"⚡ Using BATCH LOADING for maximum speed\n")
    
    start_time = time.time()
    
    # Calculate date range
    end_date = datetime.now().replace(tzinfo=None)
    start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
    
    # 🚀 OPTION 1: Load ALL symbols in ONE query (fastest for < 1000 symbols)
    if len(symbols) <= 1000:
        print(f"⚡ Loading all {len(symbols)} symbols in a single batch query...")
        stock_data_dict = data_manager.load_multiple_symbols_batch(
            symbols, 
            start_date, 
            end_date
        )
        
        loaded = len(stock_data_dict)
        missing = len(symbols) - loaded
        
        elapsed = time.time() - start_time
        print(f"\n✅ Loaded {loaded}/{len(symbols)} symbols in {elapsed:.2f}s")
        print(f"   Speed: {loaded/elapsed:.1f} symbols/second")
        
        if missing > 0:
            print(f"⚠️  {missing} symbols not found in cache")
        
        return stock_data_dict
    
    # 🚀 OPTION 2: Load in chunks (for > 1000 symbols)
    else:
        print(f"⚡ Loading {len(symbols)} symbols in chunks...")
        chunk_size = 250  # Load 250 symbols per query
        stock_data_dict = {}
        
        from tqdm import tqdm
        
        with tqdm(total=len(symbols), desc="Loading data", unit="stock") as pbar:
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i+chunk_size]
                
                # Load this chunk
                chunk_data = data_manager.load_multiple_symbols_batch(
                    chunk,
                    start_date,
                    end_date
                )
                
                stock_data_dict.update(chunk_data)
                pbar.update(len(chunk))
        
        loaded = len(stock_data_dict)
        missing = len(symbols) - loaded
        
        elapsed = time.time() - start_time
        print(f"\n✅ Loaded {loaded}/{len(symbols)} symbols in {elapsed:.2f}s")
        print(f"   Speed: {loaded/elapsed:.1f} symbols/second")
        
        if missing > 0:
            print(f"⚠️  {missing} symbols not found in cache")
        
        return stock_data_dict

# ============================================================
# FORCED LIQUIDATION FUNCTION
# ============================================================

def check_and_liquidate_invalid_positions(current_date, strategy_trackers, approved_tickers, current_prices):
    """Check and force liquidate positions not in approved universe"""
    forced_exits = []
    
    for strategy_name, tracker in strategy_trackers.items():
        for symbol in list(tracker.positions.keys()):
            shares = tracker.positions.get(symbol, 0)
            
            if shares > 0 and symbol not in approved_tickers:
                print(f"\n⚠️  OVERRIDE: {symbol} not in approved universe")
                print(f"   → Forcing liquidation for {strategy_name}")
                
                if symbol in current_prices:
                    price = current_prices[symbol]
                    tracker.execute_trade(
                        symbol=symbol,
                        signal='SELL',
                        price=price,
                        date=current_date
                    )
                    
                    if tracker.trades:
                        tracker.trades[-1]['forced_exit'] = True
                        tracker.trades[-1]['reason'] = 'DELISTED_FROM_UNIVERSE'
                    
                    forced_exits.append({
                        'date': current_date,
                        'strategy': strategy_name,
                        'symbol': symbol,
                        'shares': shares,
                        'price': price,
                        'reason': 'DELISTED_FROM_UNIVERSE'
                    })
                    
                    print(f"   → Sold {shares:.2f} shares @ ${price:.2f}")
                else:
                    print(f"   ⚠️  WARNING: No price data for {symbol}, marking as liquidated")
                    tracker.positions[symbol] = 0
    
    return forced_exits

# ============================================================
# MAIN SIMULATION FUNCTION
# ============================================================

def run_simulation():
    """Main simulation loop with universe checking and forced liquidation"""
    global results, is_running
    is_running = True
    results = {}
    
    # Load SPY first
    print("Loading data...")
    try:
        spy_data = fetch_stock_data("SPY")
    except Exception as e:
        print(f"Error loading SPY: {e}")
        is_running = False
        return
    
    # Check if SPY has data
    if spy_data is None or spy_data.empty:
        print("❌ ERROR: No data for SPY. Please run download first.")
        print("   Try: python simulator.py --download --tickers SPY")
        is_running = False
        return
    
    # Load all other stocks in parallel
    stock_data_dict = fetch_stock_data_parallel(SYMBOLS, days=HISTORY)
    
    if not stock_data_dict:
        print("Error: No stock data loaded")
        is_running = False
        return
    
    # Filter out symbols with no data
    symbols_with_data = [symbol for symbol in stock_data_dict if not stock_data_dict[symbol].empty]
    print(f"\n📊 Found data for {len(symbols_with_data)} out of {len(SYMBOLS)} symbols")
    
    if len(symbols_with_data) == 0:
        print("❌ No symbols have data. Please run with --download first.")
        is_running = False
        return
    
    # Update stock_data_dict to only include symbols with data
    stock_data_dict = {symbol: stock_data_dict[symbol] for symbol in symbols_with_data}
    
    # Check which symbols have enough data (at least 100 bars)
    symbols_enough_data = [s for s in symbols_with_data if len(stock_data_dict[s]) >= 100]
    print(f"📊 Symbols with sufficient data (≥100 bars): {len(symbols_enough_data)}")
    
    # If we have a lot of symbols, we might want to limit for performance
    MAX_SYMBOLS = 500  # Limit for reasonable performance
    if len(symbols_enough_data) > MAX_SYMBOLS:
        print(f"⚠️  Limiting to first {MAX_SYMBOLS} symbols for performance")
        symbols_enough_data = symbols_enough_data[:MAX_SYMBOLS]
        stock_data_dict = {s: stock_data_dict[s] for s in symbols_enough_data}
    
    # Align all data to common dates
    common_dates = spy_data.index
    for symbol in list(stock_data_dict.keys()):
        common_dates = common_dates.intersection(stock_data_dict[symbol].index)
    
    # Check if we have any common dates
    if len(common_dates) == 0:
        print("\n❌ ERROR: No overlapping time periods between SPY and the selected stocks")
        print("This can happen if:")
        print("  1. Some stocks have no data for the requested period")
        print("  2. Some stocks have different trading calendars")
        print("  3. The data is corrupted or incomplete")
        print("\n💡 Solutions:")
        print("  - Run with --download to refresh the data")
        print("  - Try a smaller universe (sp500 instead of russell3000)")
        print("  - Check if you're in offline mode with incomplete data")
        
        # Show which symbols have data
        print(f"\n📊 Data availability summary:")
        print(f"  SPY: {len(spy_data)} bars")
        for symbol in list(stock_data_dict.keys())[:10]:  # Show first 10
            print(f"  {symbol}: {len(stock_data_dict[symbol])} bars")
        if len(stock_data_dict) > 10:
            print(f"  ... and {len(stock_data_dict) - 10} more")
        
        is_running = False
        return
    
    spy_data = spy_data.loc[common_dates]
    for symbol in stock_data_dict:
        stock_data_dict[symbol] = stock_data_dict[symbol].loc[common_dates]
    
    print(f"\n✅ Data aligned: {len(common_dates)} common time points")
    print(f"   Date range: {common_dates[0].date()} to {common_dates[-1].date()}")
    
    total_bars = len(common_dates)
    delay = TOTAL_DURATION / total_bars if total_bars > 0 else 0.01
    
    # ============================================================
    # CHANGE 1: Increase max_positions from 5 to 10
    # ============================================================
    strategy_trackers = {}
    for strategy in strategies:
        strategy.reset()
        strategy_trackers[strategy.name] = StrategyTracker(
            strategy.name, 
            INITIAL_CASH,
            position_size_pct=0.20,
            max_positions=10  # ← INCREASED FROM 5 TO 10
        )
    
    # SPY tracker for benchmark
    spy_tracker = StrategyTracker("S&P 500", INITIAL_CASH)
    
    # Setup figure
    fig, ax = plt.subplots(figsize=(14, 8))
    plt.subplots_adjust(bottom=0.25, right=0.75)
    
    # Plot lines
    strategy_lines = {}
    for idx, strategy in enumerate(strategies):
        line, = ax.plot([], [], label=strategy.name, color=strategy.color, linewidth=2)
        strategy_lines[strategy.name] = line
    
    spy_line, = ax.plot([], [], label='S&P 500', color='black', linewidth=2, linestyle='--')
    
    ax.set_title('Portfolio Performance vs S&P 500', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Portfolio Value ($)')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # Results table on right side
    table_ax = fig.add_axes([0.77, 0.35, 0.22, 0.5])
    table_ax.axis('off')
    
    # Track forced exits
    all_forced_exits = []
    
    # Track signal statistics
    signal_stats = {strategy.name: {'attempts': 0, 'blocked': 0, 'executed': 0} for strategy in strategies}
    
    # Simulate bar by bar
    print("\nRunning simulation...")
    for i in range(total_bars):
        current_date = common_dates[i]
        
        # Get current prices
        current_prices = {symbol: stock_data_dict[symbol]['close'].iloc[i] 
                         for symbol in stock_data_dict}
        current_spy_price = spy_data['close'].iloc[i]
        
        # ============================================================
        # OPTIONAL: UNIVERSE CHECKING - FORCED LIQUIDATION
        # ============================================================
        if args.universe and not args.no_universe_check:
            # Get approved tickers for this date
            approved_tickers = universe_manager.get_approved_tickers(
                args.universe, 
                query_date=current_date.date()
            )
            
            # Check and liquidate invalid positions
            forced_exits = check_and_liquidate_invalid_positions(
                current_date=current_date,
                strategy_trackers=strategy_trackers,
                approved_tickers=approved_tickers,
                current_prices=current_prices
            )
            
            all_forced_exits.extend(forced_exits)
        
        # Update SPY tracker
        if i == 0:
            spy_shares = INITIAL_CASH / current_spy_price
            spy_tracker.positions['SPY'] = spy_shares
            spy_tracker.cash = 0
        
        spy_value = spy_tracker.update_portfolio_value(current_date, {'SPY': current_spy_price})
        
        # Run each strategy
        for strategy in strategies:
            tracker = strategy_trackers[strategy.name]
            
            # Run strategy on each stock
            for symbol in stock_data_dict:
                stock_bar = stock_data_dict[symbol].iloc[:i+1]
                spy_bar = spy_data.iloc[:i+1]
                
                # Generate signal
                signal = strategy.on_data(stock_bar, spy_bar, current_date, symbol)
                
                if signal:
                    signal_stats[strategy.name]['attempts'] += 1
                    
                    # Execute the trade
                    success = tracker.execute_trade(
                        symbol, signal, 
                        current_prices[symbol], current_date
                    )
                    
                    if success:
                        # Trade executed successfully!
                        strategy.record_execution(signal, symbol)
                        signal_stats[strategy.name]['executed'] += 1
                    else:
                        # Trade failed
                        signal_stats[strategy.name]['blocked'] += 1
            
            # Update portfolio value
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Update plot every 10 bars
        if i % 10 == 0 or i == total_bars - 1:
            # Update lines
            spy_line.set_data(spy_tracker.dates, spy_tracker.portfolio_value_history)
            
            for strategy in strategies:
                tracker = strategy_trackers[strategy.name]
                strategy_lines[strategy.name].set_data(tracker.dates, tracker.portfolio_value_history)
            
            ax.relim()
            ax.autoscale_view()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            
            # Update results table
            table_ax.clear()
            table_ax.axis('off')
            
            sorted_strategies = sorted(
                strategies,
                key=lambda s: strategy_trackers[s.name].get_return_pct(),
                reverse=True
            )
            
            table_data = [['Rank', 'Strategy', 'Profit', 'Return %', 'Win Rate']]
            for rank, strat in enumerate(sorted_strategies, 1):
                tracker = strategy_trackers[strat.name]
                profit = tracker.get_profit_dollars()
                profit_str = f"${profit:+,.0f}" if profit >= 0 else f"-${abs(profit):,.0f}"
                
                table_data.append([
                    str(rank),
                    strat.name[:10],
                    profit_str,
                    f"{tracker.get_return_pct():.1f}%",
                    f"{tracker.get_win_rate():.0f}%"
                ])
            
            # Add SPY
            spy_profit = spy_tracker.get_profit_dollars()
            spy_profit_str = f"${spy_profit:+,.0f}" if spy_profit >= 0 else f"-${abs(spy_profit):,.0f}"
            table_data.append([
                '-',
                'S&P 500',
                spy_profit_str,
                f"{spy_tracker.get_return_pct():.1f}%",
                '100%'
            ])
            
            table = table_ax.table(cellText=table_data, cellLoc='left',
                                  loc='upper left', colWidths=[0.12, 0.28, 0.20, 0.20, 0.20])
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.8)
            
            # Header styling
            for i in range(5):
                table[(0, i)].set_facecolor('#4CAF50')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            # Color code profit column
            for row in range(1, len(table_data)):
                if row <= len(sorted_strategies):
                    profit_val = strategy_trackers[sorted_strategies[row-1].name].get_profit_dollars()
                else:
                    profit_val = spy_profit
                
                if profit_val > 0:
                    table[(row, 2)].set_facecolor('#E8F5E9')
                elif profit_val < 0:
                    table[(row, 2)].set_facecolor('#FFEBEE')
            
            plt.pause(delay)
    
    # ============================================================
    # OPTIONAL: END-OF-SIMULATION LIQUIDATION
    # ============================================================
    if args.force_liquidate:
        print("\n📊 Liquidating all positions at end of simulation...")
        
        final_date = common_dates[-1]
        final_prices = {symbol: stock_data_dict[symbol]['close'].iloc[-1] 
                        for symbol in stock_data_dict}
        
        for strategy in strategies:
            tracker = strategy_trackers[strategy.name]
            positions_before = tracker.get_current_position_count()
            
            if positions_before > 0:
                liquidated = tracker.force_liquidate_all(final_date, final_prices)
                print(f"  {strategy.name}: Closed {liquidated} positions")
                
                # Update final portfolio value
                tracker.update_portfolio_value(final_date, final_prices)
        
        # Also liquidate SPY benchmark
        if spy_tracker.positions.get('SPY', 0) > 0:
            spy_tracker.force_liquidate_all(final_date, {'SPY': final_prices.get('SPY', spy_data['close'].iloc[-1])})
    else:
        print("\n📊 Simulation complete - positions remain open for continuous tracking")
        
        # Just update final values without liquidating
        final_date = common_dates[-1]
        final_prices = {symbol: stock_data_dict[symbol]['close'].iloc[-1] 
                        for symbol in stock_data_dict}
        
        for strategy in strategies:
            tracker = strategy_trackers[strategy.name]
            tracker.update_portfolio_value(final_date, final_prices)
        
        spy_tracker.update_portfolio_value(final_date, {'SPY': final_prices.get('SPY', spy_data['close'].iloc[-1])})
    
    # ============================================================
    # STORE RESULTS AND CREATE ANALYSIS BUTTONS
    # ============================================================
    
    results['strategy_trackers'] = strategy_trackers
    results['spy_tracker'] = spy_tracker
    results['stock_data'] = stock_data_dict
    results['common_dates'] = common_dates
    results['strategies'] = strategies
    results['forced_exits'] = all_forced_exits
    
    # Print final signal statistics
    print("\n" + "="*70)
    print("SIGNAL STATISTICS SUMMARY")
    print("="*70)
    for strategy_name, stats in signal_stats.items():
        print(f"\n{strategy_name}:")
        print(f"  Signal attempts: {stats['attempts']}")
        print(f"  Successfully executed: {stats['executed']}")
        print(f"  Blocked/Failed: {stats['blocked']}")
        print(f"  Execution rate: {(stats['executed']/stats['attempts']*100) if stats['attempts'] > 0 else 0:.1f}%")
    
    # Print forced exits summary only if universe checking was enabled
    if all_forced_exits and not args.no_universe_check:
        print(f"\n{'='*70}")
        print(f"FORCED LIQUIDATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total forced exits: {len(all_forced_exits)}")
        for exit in all_forced_exits:
            print(f"  • {exit['date'].date()}: {exit['strategy']} sold {exit['symbol']}")
        print(f"{'='*70}\n")
    
    # ============================================================
    # OPEN POSITIONS SUMMARY
    # ============================================================
    print(f"\n{'='*70}")
    print(f"FINAL POSITIONS SUMMARY")
    print(f"{'='*70}")
    
    for strategy in strategies:
        tracker = strategy_trackers[strategy.name]
        open_positions = tracker.get_current_position_count()
        
        if open_positions > 0:
            print(f"\n{strategy.name}:")
            print(f"  Open positions: {open_positions}")
            print(f"  Cash: ${tracker.cash:,.2f}")
            print(f"  Portfolio value: ${tracker.get_final_value():,.2f}")
            
            # List each position
            for symbol in symbols_with_data:  # Use symbols_with_data instead of SYMBOLS
                shares = tracker.positions.get(symbol, 0)
                if shares > 0:
                    current_price = stock_data_dict[symbol]['close'].iloc[-1]
                    position_value = shares * current_price
                    print(f"    {symbol}: {shares:.2f} shares @ ${current_price:.2f} = ${position_value:,.2f}")
        else:
            print(f"\n{strategy.name}: No open positions (all cash: ${tracker.cash:,.2f})")
    
    print(f"\n{'='*70}\n")
    
    # Add analysis buttons
    button_y = 0.20
    button_spacing = 0.05
    button_refs = []
    
    print(f"\nCreating analysis buttons for {len(strategies)} strategies...")
    
    for idx, strategy in enumerate(strategies):
        y_pos = button_y - (idx * button_spacing)
        
        if y_pos < 0.02:
            print(f"Warning: Too many strategies to show all buttons. Showing first {idx}.")
            break
        
        if strategy.name not in strategy_trackers:
            print(f"  ERROR: Strategy '{strategy.name}' not found in trackers!")
            continue
        
        tracker = strategy_trackers[strategy.name]
        
        ax_btn = fig.add_axes([0.77, y_pos, 0.21, 0.04])
        btn_label = f'Analyze {strategy.name}'
        
        if len(btn_label) > 22:
            btn_label = btn_label[:19] + '...'
        
        btn = Button(ax_btn, btn_label)
        button_refs.append(btn)
        
        print(f"  Button {idx+1}: '{btn_label}' -> '{strategy.name}' (trades: {len(tracker.trades)})")
        
        def make_handler(strat_obj, track_obj, stock_dict, syms):
            def handler(event):
                print(f"\n{'='*60}")
                print(f"Analyze button clicked for: {strat_obj.name}")
                print(f"{'='*60}")
                try:
                    show_strategy_analysis(strat_obj, track_obj, stock_dict, syms)
                except Exception as e:
                    print(f"ERROR in analysis window: {e}")
                    import traceback
                    traceback.print_exc()
            return handler
        
        btn.on_clicked(make_handler(strategy, tracker, stock_data_dict, symbols_with_data))
    
    results['buttons'] = button_refs
    
    is_running = False
    print("\nSimulation complete!")
    plt.show()

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == '__main__':
    load_strategies()
    
    if not strategies:
        print("\n⚠️  No strategies found in strategies/ directory")
        print("Add strategy files named strategy_*.py")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Loaded {len(strategies)} strategies")
    print(f"{'='*70}\n")
    
    run_simulation()