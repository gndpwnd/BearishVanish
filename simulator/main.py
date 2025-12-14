"""
Stock Trading Strategy Simulator - Main Entry Point
Pure simulation engine - NO analysis, NO GUI
ENHANCED: Volume tracking and indicator system integration
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
import importlib.util

from data_manager import DataManager
from stock_universe import UniverseManager
from system_benchmark import SystemBenchmark
from simulator import run_simulation

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Strategy colors (for future use in analysis)
STRATEGY_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Stock Strategy Simulator')
    
    # Data management
    parser.add_argument('--cache-status', action='store_true', help='Show cache status')
    parser.add_argument('--download', action='store_true', help='Download data')
    parser.add_argument('--tickers', type=str, help='Comma-separated tickers')
    parser.add_argument('--offline', action='store_true', help='Offline mode')
    parser.add_argument('--workers', type=int, default=10, help='Download workers')
    
    # Universe management
    parser.add_argument('--update-universe', type=str, help='Update universe')
    parser.add_argument('--universe', type=str, help='Universe to simulate')
    parser.add_argument('--universe-status', action='store_true', help='Universe status')
    parser.add_argument('--check-ticker', type=str, help='Check ticker')
    
    # Simulation options
    parser.add_argument('--force-liquidate', action='store_true', 
                       help='Force liquidate at end')
    parser.add_argument('--no-universe-check', action='store_true',
                       help='Disable universe checking')
    
    # Benchmark
    parser.add_argument('--benchmark', action='store_true', help='Run benchmark')
    
    return parser.parse_args()


def load_strategies(indicator_library=None):
    """Load all strategy files from strategies/ directory with configurable parameters"""
    strategies = []
    
    strategies_dir = Path('strategies')
    if not strategies_dir.exists():
        print("❌ Create 'strategies/' directory and add strategy files")
        return strategies
    
    strategy_files = sorted(list(strategies_dir.glob('strategy_*.py')))
    
    print(f"\n{'='*70}")
    print(f"LOADING STRATEGIES")
    print(f"{'='*70}\n")
    
    # Strategy configuration (could be loaded from a config file)
    strategy_configs = {
        'Weekly Threshold': {
            'color': '#1f77b4',
            'initial_capital': 100000,
            'position_size_pct': 0.10,
            'max_positions': 10,
            'buy_threshold': -0.05,
            'sell_threshold': 0.10
        },
        '500 Intersection': {
            'color': '#ff7f0e',
            'initial_capital': 100000,
            'position_size_pct': 0.10,
            'max_positions': 10
        },
        'Volume Indicator Strategy': {  # NEW: Example volume strategy
            'color': '#2ca02c',
            'initial_capital': 100000,
            'position_size_pct': 0.10,
            'max_positions': 10
        }
    }
    
    for idx, strategy_file in enumerate(strategy_files):
        try:
            module_name = f"strategy_module_{idx}"
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            if hasattr(module, 'Strategy'):
                # Get strategy name from filename
                filename_name = strategy_file.stem.replace('strategy_', '').replace('_', ' ').title()
                
                # Get configuration for this strategy
                config = strategy_configs.get(filename_name, {})
                color = config.get('color', STRATEGY_COLORS[idx % len(STRATEGY_COLORS)])
                
                # Create strategy instance with configuration
                strategy_instance = module.Strategy(
                    color=color,
                    initial_capital=config.get('initial_capital', 100000),
                    position_size_pct=config.get('position_size_pct', 0.10),
                    max_positions=config.get('max_positions', 10),
                    **{k: v for k, v in config.items() if k not in ['color', 'initial_capital', 'position_size_pct', 'max_positions']}
                )
                
                # Set name from filename if not set
                if not hasattr(strategy_instance, 'name') or strategy_instance.name == "Strategy":
                    strategy_instance.name = filename_name
                
                # Attach indicator library if available
                if indicator_library is not None:
                    strategy_instance.indicator_library = indicator_library
                
                strategies.append(strategy_instance)
                
                # Print configuration
                print(f"✅ Loaded: {strategy_instance.name}")
                print(f"   Config: Capital=${strategy_instance.initial_capital:,}, "
                      f"Pos Size={strategy_instance.position_size_pct*100:.1f}%, "
                      f"Max Pos={strategy_instance.max_positions}")
                if hasattr(strategy_instance, 'indicator_library') and strategy_instance.indicator_library:
                    print(f"   Indicators: Available")
        except Exception as e:
            print(f"❌ Error loading {strategy_file}: {e}")
    
    print(f"\n{'='*70}\n")
    
    return strategies   

def handle_download(args, data_manager, universe_manager):
    """Handle download command"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm
    
    print(f"\n{'='*70}")
    print("DOWNLOADING DATA")
    print(f"{'='*70}\n")
    
    # Determine symbols
    if args.tickers:
        symbols = [t.strip().upper() for t in args.tickers.split(',')]
    elif args.universe:
        symbols = universe_manager.get_approved_tickers(args.universe)
        if not symbols:
            print(f"❌ No symbols for universe: {args.universe}")
            return
        symbols = symbols + ['SPY']
    else:
        symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META', 'SPY']
    
    print(f"📦 Downloading {len(symbols)} symbols with {args.workers} workers\n")
    
    def download_symbol(symbol):
        try:
            thread_dm = DataManager(api_key, secret_key, offline_mode=False, quiet=True)
            df = thread_dm.get_stock_data(symbol)
            del thread_dm
            return (symbol, df, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    successful = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_symbol, sym): sym for sym in symbols}
        
        with tqdm(total=len(symbols), desc="Downloading", unit="stock") as pbar:
            for future in as_completed(futures):
                symbol, df, error = future.result()
                
                if error or df is None:
                    failed += 1
                else:
                    successful += 1
                
                pbar.update(1)
    
    print(f"\n✅ Downloaded {successful}/{len(symbols)} symbols")
    if failed > 0:
        print(f"❌ Failed: {failed} symbols")
    
    print(f"\n{'='*70}\n")


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Initialize managers
    data_manager = DataManager(api_key, secret_key, offline_mode=args.offline)
    universe_manager = UniverseManager(api_key, secret_key)
    
    # Handle special commands
    if args.benchmark:
        benchmark = SystemBenchmark(data_manager, universe_manager)
        benchmark.run_benchmark()
        sys.exit(0)
    
    if args.universe_status:
        universe_manager.print_status()
        sys.exit(0)
    
    if args.update_universe:
        universe_manager.update_universe(args.update_universe)
        sys.exit(0)
    
    if args.check_ticker:
        universe_manager.print_ticker_info(args.check_ticker)
        sys.exit(0)
    
    if args.cache_status:
        data_manager.print_cache_status()
        sys.exit(0)
    
    if args.download:
        handle_download(args, data_manager, universe_manager)
        sys.exit(0)
    
    # Offline mode notice
    if args.offline:
        print("\n⚠️  OFFLINE MODE - Using cached data only")
    
    # Initialize indicator system (must be done BEFORE loading strategies)
    print("\n📊 Initializing indicator system...")
    try:
        from indicator_loader import get_indicator_library
        
        # Create indicators directory if it doesn't exist
        indicators_dir = Path('./indicators')
        indicators_dir.mkdir(exist_ok=True)
        
        # Get indicator library
        indicator_library = get_indicator_library()
        
        # Create example indicator file if none exist
        if not list(indicators_dir.glob("indicator_*.py")):
            print("📝 Creating example indicator files...")
            indicator_library.create_example_indicator('function')
            indicator_library.create_example_indicator('class')
        
        print(f"✅ Indicator system ready")
        print(f"   Available indicators: {len(indicator_library._functions)} functions, {len(indicator_library._classes)} classes")
        
        # List available indicators
        indicator_list = indicator_library.list_indicators()
        if indicator_list['functions']:
            print(f"   Functions: {', '.join(indicator_list['functions'][:5])}{'...' if len(indicator_list['functions']) > 5 else ''}")
        if indicator_list['classes']:
            print(f"   Classes: {', '.join(indicator_list['classes'])}")
        
    except ImportError as e:
        print(f"⚠️  Could not import indicator system: {e}")
        print(f"   Make sure indicator_base.py and indicator_loader.py are in your project directory")
        indicator_library = None
    except Exception as e:
        print(f"⚠️  Error initializing indicator system: {e}")
        indicator_library = None
    
    # Load strategies WITH indicator library
    strategies = load_strategies(indicator_library=indicator_library)
    
    if not strategies:
        print("❌ No strategies found")
        sys.exit(1)
    
    # Select symbols
    if args.universe:
        print(f"\n📋 Loading {args.universe.upper()} universe...")
        symbols = universe_manager.get_approved_tickers(args.universe)
        
        if not symbols:
            print(f"❌ No symbols for universe: {args.universe}")
            print(f"   Run: python main.py --update-universe {args.universe}")
            sys.exit(1)
        
        print(f"✅ Loaded {len(symbols)} symbols\n")
    else:
        symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META']
        print(f"\n📋 Using default symbols: {symbols}\n")
    
    # Run simulation
    print(f"\n{'='*70}")
    print("STARTING SIMULATION")
    print(f"{'='*70}\n")
    print(f"Strategies: {len(strategies)}")
    print(f"Symbols: {len(symbols)}")
    print(f"Universe: {args.universe or 'custom'}")
    print(f"Force Liquidate: {args.force_liquidate}")
    print(f"No Universe Check: {args.no_universe_check}")
    print(f"Indicator System: {indicator_library is not None}")
    print(f"\n{'='*70}\n")
    
    db_path = run_simulation(
        strategies=strategies,
        symbols=symbols,
        data_manager=data_manager,
        universe_manager=universe_manager,
        args=args
    )
    
    if db_path:
        print(f"\n{'='*70}")
        print("✅ SIMULATION COMPLETE")
        print(f"{'='*70}")
        print(f"\n📊 Results saved to: {db_path}")
        print(f"\n💡 To analyze results:")
        print(f"   cd ../analysis")
        print(f"   python main.py --sim {db_path}")
        print(f"\n📈 Volume metrics are now tracked in the database!")
        print(f"   Query example: SELECT entry_relative_volume, profit_loss_pct FROM trade_history")
        print(f"\n📊 Indicators used: {indicator_library is not None}")
        if indicator_library:
            print(f"   Total indicators: {len(indicator_library._functions)} functions, {len(indicator_library._classes)} classes")
        print(f"\n{'='*70}\n")
    else:
        print("\n❌ Simulation failed")
        sys.exit(1)

if __name__ == '__main__':
    main()