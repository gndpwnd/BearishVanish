"""
Stock Trading Strategy Simulator - Parallel Data Loading
Main entry point for backtesting trading strategies with concurrent data fetching


THIS IS THE OLD SIMULATION SCRIPT

"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
import importlib.util
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from data_manager import DataManager
from strategy_tracker import StrategyTracker, INITIAL_CASH
from strategy_analysis import show_strategy_analysis

# Parse command line arguments first
parser = argparse.ArgumentParser(description='Stock Strategy Simulator')
parser.add_argument('--cache-status', action='store_true', help='Show offline cache status')
parser.add_argument('--download', action='store_true', help='Download data for all symbols')
parser.add_argument('--offline', action='store_true', help='Run in offline mode')
parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers for data loading')
args = parser.parse_args()

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Configuration
HISTORY = 180  # 6 months (approximately 180 days)
TOTAL_DURATION = 3.0  # seconds
SYMBOLS = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'META']
strategy_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

# Initialize DataManager
data_manager = DataManager(api_key, secret_key, offline_mode=args.offline)

# Handle command line options
if args.cache_status:
    data_manager.print_cache_status()
    sys.exit(0)

if args.download:
    print(f"Downloading data for all symbols using {args.workers} workers...")
    symbols_to_download = SYMBOLS + ['SPY']
    
    # Parallel download
    def download_symbol(symbol):
        try:
            df = data_manager.get_stock_data(symbol, days=HISTORY)
            return (symbol, df, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_symbol, sym): sym for sym in symbols_to_download}
        
        for future in as_completed(futures):
            symbol, df, error = future.result()
            if error:
                print(f"✗ {symbol}: Error - {error}")
                results[symbol] = None
            else:
                print(f"✓ {symbol}: {len(df)} bars downloaded")
                results[symbol] = df
    
    print(f"\n{'='*60}")
    print(f"DOWNLOAD COMPLETE")
    print(f"Successful: {sum(1 for v in results.values() if v is not None)}/{len(symbols_to_download)}")
    print(f"{'='*60}\n")
    sys.exit(0)

if args.offline:
    print("\n" + "="*60)
    print("RUNNING IN OFFLINE MODE")
    print("="*60)
    print("Using cached data only. Will fail if data is missing.")
    print("="*60 + "\n")

# Global state
strategies = []
results = {}
is_running = False
print_lock = threading.Lock()  # For thread-safe printing

def fetch_stock_data(symbol, days=HISTORY):
    """Fetch stock data using DataManager (handles offline/online automatically)"""
    return data_manager.get_stock_data(symbol, days=days)

def fetch_stock_data_parallel(symbols, days=HISTORY, max_workers=None):
    """
    Fetch multiple stocks in parallel using thread pool
    SQLite handles concurrent reads efficiently
    
    Args:
        symbols: List of stock symbols
        days: Number of days of history
        max_workers: Number of parallel threads (default: min(10, len(symbols)))
    
    Returns:
        Dictionary of {symbol: dataframe}
    """
    if max_workers is None:
        max_workers = min(args.workers, len(symbols))
    
    print(f"Loading {len(symbols)} symbols using {max_workers} parallel workers...")
    
    stock_data_dict = {}
    errors = []
    
    def load_symbol(symbol):
        try:
            with print_lock:
                print(f"  [{threading.current_thread().name}] Loading {symbol}...")
            df = fetch_stock_data(symbol, days)
            return (symbol, df, None)
        except Exception as e:
            return (symbol, None, str(e))
    
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='DataLoader') as executor:
        # Submit all tasks
        futures = {executor.submit(load_symbol, sym): sym for sym in symbols}
        
        # Collect results as they complete
        for future in as_completed(futures):
            symbol, df, error = future.result()
            if error:
                errors.append((symbol, error))
                with print_lock:
                    print(f"  ✗ {symbol}: {error}")
            else:
                stock_data_dict[symbol] = df
                with print_lock:
                    print(f"  ✓ {symbol}: {len(df)} bars loaded")
    
    if errors:
        print(f"\n⚠ Warning: {len(errors)} symbols failed to load")
        for symbol, error in errors:
            print(f"  - {symbol}: {error}")
    
    print(f"✓ Successfully loaded {len(stock_data_dict)}/{len(symbols)} symbols\n")
    return stock_data_dict

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
            # Use unique module name to avoid conflicts
            module_name = f"strategy_module_{idx}_{strategy_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            if hasattr(module, 'Strategy'):
                color = strategy_colors[idx % len(strategy_colors)]
                strategy_instance = module.Strategy(color=color)
                
                # Override name with filename if not custom set or if name is default
                filename_name = strategy_file.stem.replace('strategy_', '').replace('_', ' ').title()
                if not hasattr(strategy_instance, 'name') or strategy_instance.name == "Strategy":
                    strategy_instance.name = filename_name
                
                strategies.append(strategy_instance)
                print(f"Loaded: {strategy_instance.name} (color: {color})")
        except Exception as e:
            print(f"Error loading {strategy_file}: {e}")

def run_simulation():
    """Main simulation loop with parallel data loading"""
    global results, is_running
    is_running = True
    results = {}
    
    # Load all stock data IN PARALLEL
    print("Loading data...")
    
    # Load SPY first (needed for alignment)
    try:
        spy_data = fetch_stock_data("SPY")
    except Exception as e:
        print(f"Error loading SPY: {e}")
        is_running = False
        return
    
    # Load all other stocks in parallel
    stock_data_dict = fetch_stock_data_parallel(SYMBOLS, days=HISTORY)
    
    if not stock_data_dict:
        print("Error: No stock data loaded")
        is_running = False
        return
    
    # Align all data to common dates
    common_dates = spy_data.index
    for symbol in list(stock_data_dict.keys()):
        common_dates = common_dates.intersection(stock_data_dict[symbol].index)
    
    spy_data = spy_data.loc[common_dates]
    for symbol in stock_data_dict:
        stock_data_dict[symbol] = stock_data_dict[symbol].loc[common_dates]
    
    print(f"\n✓ Data aligned: {len(common_dates)} common time points")
    
    total_bars = len(common_dates)
    delay = TOTAL_DURATION / total_bars if total_bars > 0 else 0.01
    
    # Initialize trackers for each strategy
    strategy_trackers = {}
    for strategy in strategies:
        strategy.reset()
        strategy_trackers[strategy.name] = StrategyTracker(strategy.name, INITIAL_CASH)
    
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
    
    # Simulate bar by bar
    print("Running simulation...")
    for i in range(total_bars):
        current_date = common_dates[i]
        
        # Get current prices for all stocks
        current_prices = {symbol: stock_data_dict[symbol]['close'].iloc[i] 
                         for symbol in stock_data_dict}
        current_spy_price = spy_data['close'].iloc[i]
        
        # Update SPY tracker (buy and hold)
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
                
                signal = strategy.on_data(stock_bar, spy_bar, current_date, symbol)
                
                if signal:
                    tracker.execute_trade(symbol, signal, current_prices[symbol], current_date)
            
            # Update portfolio value
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Update plot every 10 bars for performance
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
            
            # Sort strategies by return
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
                profit_val = tracker.get_profit_dollars() if row <= len(sorted_strategies) else spy_profit
                if profit_val > 0:
                    table[(row, 2)].set_facecolor('#E8F5E9')  # Light green
                elif profit_val < 0:
                    table[(row, 2)].set_facecolor('#FFEBEE')  # Light red
            
            plt.pause(delay)
    
    # Store final results
    results['strategy_trackers'] = strategy_trackers
    results['spy_tracker'] = spy_tracker
    results['stock_data'] = stock_data_dict
    results['common_dates'] = common_dates
    results['strategies'] = strategies
    
    # Add analysis buttons dynamically - MUST be after results are stored
    button_y = 0.20
    button_spacing = 0.05
    
    print(f"\nCreating analysis buttons for {len(strategies)} strategies...")
    print(f"Available strategies in results: {list(strategy_trackers.keys())}")
    
    # Create list to store button references (prevents garbage collection)
    button_refs = []
    
    for idx, strategy in enumerate(strategies):
        y_pos = button_y - (idx * button_spacing)
        
        # Stop if we run out of space
        if y_pos < 0.02:
            print(f"Warning: Too many strategies to show all buttons. Showing first {idx} strategies.")
            break
        
        # Verify this strategy exists in trackers
        if strategy.name not in strategy_trackers:
            print(f"  ERROR: Strategy '{strategy.name}' not found in trackers!")
            continue
        
        tracker = strategy_trackers[strategy.name]
        
        ax_btn = fig.add_axes([0.77, y_pos, 0.21, 0.04])
        btn_label = f'Analyze {strategy.name}'
        
        # Truncate label if too long
        if len(btn_label) > 22:
            btn_label = btn_label[:19] + '...'
        
        btn = Button(ax_btn, btn_label)
        button_refs.append(btn)  # Keep reference to prevent garbage collection
        
        print(f"  Button {idx+1}: '{btn_label}' -> '{strategy.name}' (trades: {len(tracker.trades)})")
        
        # Create closure that captures everything needed
        def make_handler(strat_obj, track_obj, stock_dict, syms):
            def handler(event):
                print(f"\n{'='*60}")
                print(f"Analyze button clicked for: {strat_obj.name}")
                print(f"Tracker has {len(track_obj.trades)} trades")
                print(f"{'='*60}")
                try:
                    show_strategy_analysis(strat_obj, track_obj, stock_dict, syms)
                except Exception as e:
                    print(f"ERROR in analysis window: {e}")
                    import traceback
                    traceback.print_exc()
            return handler
        
        btn.on_clicked(make_handler(strategy, tracker, stock_data_dict, SYMBOLS))
    
    # Store button references in results to prevent garbage collection
    results['buttons'] = button_refs
    
    is_running = False
    print("Simulation complete!")
    plt.show()

# Main execution
if __name__ == '__main__':
    load_strategies()
    if strategies:
        run_simulation()
    else:
        print("No strategies loaded. Add strategy files to strategies/ directory.")