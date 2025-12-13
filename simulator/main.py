"""
Stock Trading Strategy Simulator - Main Entry Point
Handles argument parsing, data loading, and command execution
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import date
from dotenv import load_dotenv
import importlib.util
import sqlite3

from data_manager import DataManager
from stock_universe import UniverseManager
from system_benchmark import SystemBenchmark
from simulator import run_simulation, HISTORY

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Get recommended workers from benchmark if available
default_download_workers = SystemBenchmark.get_recommended_workers()

# Configuration
strategy_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# ============================================================
# ARGUMENT PARSING
# ============================================================

def parse_arguments():
    """Parse command line arguments"""
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
    
    return parser.parse_args()

# ============================================================
# STRATEGY LOADING
# ============================================================

def load_strategies():
    """Load all strategy files from strategies/ directory"""
    strategies = []
    
    strategies_dir = Path('strategies')
    if not strategies_dir.exists():
        print("Create 'strategies/' directory and add strategy files.")
        return strategies
    
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
    
    return strategies

# ============================================================
# DOWNLOAD FUNCTIONS
# ============================================================

def download_symbol_threadsafe(symbol, api_key, secret_key):
    """Thread-safe version that creates its own DataManager instance"""
    try:
        thread_data_manager = DataManager(api_key, secret_key, offline_mode=False, quiet=True)
        df = thread_data_manager.get_stock_data(symbol, days=HISTORY)
        del thread_data_manager
        return (symbol, df, None)
    except Exception as e:
        return (symbol, None, str(e))

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

def handle_download_command(args, data_manager, universe_manager):
    """Handle the download command"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm
    
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
                print(f"   Run: python main.py --update-universe {args.universe}")
                return
            
            symbols_to_download = symbols_to_download + ['SPY']
            print(f"📦 Downloading data for {args.universe}: {len(symbols_to_download)-1} stocks")
    else:
        symbols_to_download = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META', 'SPY']
        print(f"📦 Downloading data for default stocks")
    
    print(f"🔧 Using {args.workers} parallel workers\n")
    
    # Check existing data
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
    
    if not missing_symbols:
        print(f"\n✅ All symbols already downloaded!")
        return
    
    # Ask user which method to use
    choice = input("\nChoose download method:\n"
                   "1. Sequential (Recommended - most reliable)\n"
                   "2. Parallel (Faster but may have errors)\n"
                   "Enter choice (1 or 2): ").strip()
    
    results = {}
    successful = 0
    failed = 0
    
    if choice == "2":
        # Parallel download
        print(f"\nStarting parallel download with thread-safe workers...")
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(download_symbol_threadsafe, sym, api_key, secret_key): sym 
                      for sym in missing_symbols}
            
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
        # Sequential download
        print(f"\nStarting reliable sequential download...")
        print("This may take a while for large universes...\n")
        
        with tqdm(total=len(missing_symbols), desc="Downloading", unit="stock") as pbar:
            for symbol in missing_symbols:
                symbol_result, df, error = download_symbol_sequential(symbol, data_manager, pbar)
                
                if error or df is None:
                    results[symbol] = None
                    failed += 1
                else:
                    results[symbol] = df
                    successful += 1
    
    # Print summary
    failed_symbols = [s for s in missing_symbols if results.get(s) is None]
    
    print(f"\n{'='*70}")
    print(f"DOWNLOAD COMPLETE")
    print(f"Total: {len(missing_symbols)} symbols")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed_symbols:
        print(f"\n❌ Failed symbols ({len(failed_symbols)}):")
        for i in range(0, len(failed_symbols), 10):
            print(f"   {', '.join(failed_symbols[i:i+10])}")
    
    print(f"{'='*70}\n")

# ============================================================
# COMMAND HANDLERS
# ============================================================

def handle_benchmark_command(args, data_manager, universe_manager):
    """Handle benchmark commands"""
    if args.benchmark:
        print("\n" + "="*70)
        print("SYSTEM BENCHMARK MODE")
        print("="*70)
        
        benchmark = SystemBenchmark(data_manager, universe_manager)
        results = benchmark.run_full_benchmark()
        return True
    
    if args.show_benchmark:
        print("\n" + "="*70)
        print("SAVED BENCHMARK RESULTS")
        print("="*70)
        
        results = SystemBenchmark.load_benchmark()
        
        if not results:
            print("❌ No benchmark results found")
            print("   Run: python main.py --benchmark")
        else:
            import json
            print(json.dumps(results, indent=2))
            
            if 'recommendations' in results:
                rec = results['recommendations']
                print("\n🎯 RECOMMENDED WORKER COUNTS:")
                print(f"  Download workers: {rec['download_workers']}")
                print(f"  Database workers: {rec['db_workers']}")
        
        print("="*70)
        return True
    
    return False

def handle_universe_commands(args, universe_manager):
    """Handle universe management commands"""
    if args.update_universe:
        print("\n" + "="*70)
        print("UNIVERSE UPDATE MODE")
        print("="*70)
        universe_manager.update_universe(args.update_universe)
        return True
    
    if args.universe_status:
        universe_manager.print_status()
        return True
    
    if args.check_ticker:
        universe_manager.print_ticker_info(args.check_ticker)
        return True
    
    if args.clear_universe:
        universe_manager.clear_universe(args.clear_universe)
        return True
    
    return False

def handle_diagnostic_commands(args, universe_manager):
    """Handle diagnostic commands"""
    if args.diagnose:
        print("\n" + "="*70)
        print("UNIVERSE DIAGNOSTICS MODE")
        print("="*70)
        universe_manager.diagnose_mismatch(args.diagnose)
        return True
    
    if args.check_quality:
        print("\n" + "="*70)
        print("DATA QUALITY CHECK MODE")
        print("="*70)
        if hasattr(universe_manager, 'diagnostics'):
            universe_manager.diagnostics.check_data_quality(args.check_quality)
        else:
            print("ERROR: diagnostics module not available")
        return True
    
    if args.find_duplicates:
        print("\n" + "="*70)
        print("DUPLICATE ANALYSIS MODE")
        print("="*70)
        if hasattr(universe_manager, 'diagnostics'):
            universe_manager.diagnostics.find_duplicate_issues(args.find_duplicates)
        else:
            print("ERROR: diagnostics module not available")
        return True
    
    if args.compare:
        print("\n" + "="*70)
        print("UNIVERSE COMPARISON MODE")
        print("="*70)
        if hasattr(universe_manager, 'diagnostics'):
            universe_manager.diagnostics.compare_universes(args.compare[0], args.compare[1])
        else:
            print("ERROR: diagnostics module not available")
        return True
    
    return False

def handle_validation_commands(args, universe_manager):
    """Handle validation commands"""
    if args.validate:
        print("\n" + "="*70)
        print("TICKER VALIDATION MODE")
        print("="*70)
        
        tickers = universe_manager.get_approved_tickers(args.validate)
        
        if not tickers:
            print(f"No tickers found for {args.validate}")
            return True
        
        from ticker_validation import TickerValidator
        valid, invalid, stats = TickerValidator.print_validation_report(tickers)
        
        if invalid:
            print(f"\n💡 TIP: Run --cleanup-db to remove invalid tickers from database")
        
        return True
    
    if args.cleanup_db:
        print("\n" + "="*70)
        print("DATABASE CLEANUP MODE")
        print("="*70)
        
        from ticker_validation import TickerValidator
        
        conn = sqlite3.connect(universe_manager.db_path)
        cursor = conn.cursor()
        
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
        return True
    
    return False

# ============================================================
# SYMBOL SELECTION
# ============================================================

def select_symbols(args, universe_manager):
    """Select symbols based on arguments"""
    if args.universe:
        print(f"\n{'='*70}")
        print(f"LOADING SYMBOLS FROM {args.universe.upper()} UNIVERSE")
        print(f"{'='*70}")
        
        symbols = universe_manager.get_approved_tickers(args.universe)
        
        if not symbols:
            print(f"❌ No symbols found for universe: {args.universe}")
            print(f"   Run: python main.py --update-universe {args.universe}")
            sys.exit(1)
        
        print(f"✅ Loaded {len(symbols)} symbols from {args.universe}")
        print(f"   Sample: {symbols[:10]}")
        print(f"{'='*70}\n")
        return symbols
    else:
        symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META']
        print(f"\nUsing default symbols: {symbols}")
        return symbols

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Initialize managers (needed for most commands)
    data_manager = DataManager(api_key, secret_key, offline_mode=args.offline)
    universe_manager = UniverseManager(api_key, secret_key)
    
    # Handle benchmark commands first (before other initialization)
    if handle_benchmark_command(args, data_manager, universe_manager):
        sys.exit(0)
    
    # Handle universe management commands
    if handle_universe_commands(args, universe_manager):
        sys.exit(0)
    
    # Handle diagnostic commands
    if handle_diagnostic_commands(args, universe_manager):
        sys.exit(0)
    
    # Handle validation commands
    if handle_validation_commands(args, universe_manager):
        sys.exit(0)
    
    # Handle cache status
    if args.cache_status:
        data_manager.print_cache_status()
        sys.exit(0)
    
    # Handle download command
    if args.download:
        handle_download_command(args, data_manager, universe_manager)
        sys.exit(0)
    
    # If offline mode, print notice
    if args.offline:
        print("\n" + "="*70)
        print("RUNNING IN OFFLINE MODE")
        print("="*70)
        print("Using cached data only. Will fail if data is missing.")
        print("="*70 + "\n")
    
    # Load strategies
    strategies = load_strategies()
    
    if not strategies:
        print("\n⚠️  No strategies found in strategies/ directory")
        print("Add strategy files named strategy_*.py")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Loaded {len(strategies)} strategies")
    print(f"{'='*70}\n")
    
    # Select symbols
    symbols = select_symbols(args, universe_manager)
    
    # Run simulation
    run_simulation(
        strategies=strategies,
        symbols=symbols,
        data_manager=data_manager,
        universe_manager=universe_manager,
        args=args
    )

if __name__ == '__main__':
    main()