"""
Stock Trading Strategy Simulator - Simulation Engine
Contains the core simulation logic and supporting functions
"""

import signal
import sys
import time
import threading
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button

from strategy_tracker import StrategyTracker, INITIAL_CASH
from strategy_analysis import show_strategy_analysis
from simulation_telemetry import telemetry  # ADDED: Telemetry import
import pandas as pd

# ============================================================
# CTRL+C GRACEFUL SHUTDOWN HANDLER
# ============================================================

# Global flag for clean shutdown
_shutdown_requested = False

def signal_handler(sig, frame):
    """Handle CTRL+C gracefully"""
    global _shutdown_requested
    
    print("\n\n⚠️  CTRL+C detected - Shutting down gracefully...")
    print("⏳ Closing matplotlib windows...")
    
    _shutdown_requested = True
    
    # Close all matplotlib windows
    plt.close('all')
    
    print("✅ Shutdown complete")
    sys.exit(0)

# Register the signal handler at module load
signal.signal(signal.SIGINT, signal_handler)

# ============================================================
# CONFIGURATION AND GLOBAL STATE
# ============================================================

# Configuration
HISTORY = 180  # 6 months of data
TOTAL_DURATION = 3.0  # seconds for visualization

# Global state
results = {}
is_running = False
print_lock = threading.Lock()

# ============================================================
# DATA FETCHING FUNCTIONS
# ============================================================

def fetch_stock_data(data_manager, symbol, days=HISTORY):
    """Fetch stock data using DataManager"""
    return data_manager.get_stock_data(symbol, days=days)

def fetch_stock_data_parallel(data_manager, symbols, days=HISTORY):
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

def run_simulation(strategies, symbols, data_manager, universe_manager, args):
    """
    Main simulation loop with universe checking and forced liquidation
    
    Parameters:
    -----------
    strategies : list
        List of strategy instances to test
    symbols : list
        List of stock symbols to trade (pre-filtered by universe)
    data_manager : DataManager
        Data manager instance for fetching stock data
    universe_manager : UniverseManager
        Universe manager for checking approved tickers
    args : argparse.Namespace
        Command line arguments with force_liquidate and no_universe_check flags
    """
    global results, is_running, _shutdown_requested
    
    is_running = True
    results = {}
    _shutdown_requested = False  # Reset at start of simulation
    
    # ============================================================
    # PRE-FILTER: Get approved universe ONCE at start
    # ============================================================
    if args.universe and not args.no_universe_check:
        approved_universe = set(universe_manager.get_approved_tickers(args.universe))
        print(f"\n📋 Universe filter: {len(approved_universe)} approved stocks")
        
        # Filter symbols to only those in approved universe
        symbols_before = len(symbols)
        symbols = [s for s in symbols if s in approved_universe]
        symbols_filtered = symbols_before - len(symbols)
        
        if symbols_filtered > 0:
            print(f"   ✂️  Filtered out {symbols_filtered} stocks not in universe")
        print(f"   ✅ Simulating {len(symbols)} approved stocks\n")
    else:
        approved_universe = None
        print(f"\n📋 No universe filtering - simulating all {len(symbols)} stocks\n")
    
    # Load SPY first
    print("Loading data...")
    try:
        spy_data = fetch_stock_data(data_manager, "SPY")
    except Exception as e:
        print(f"Error loading SPY: {e}")
        is_running = False
        return
    
    # Check if SPY has data
    if spy_data is None or spy_data.empty:
        print("❌ ERROR: No data for SPY. Please run download first.")
        print("   Try: python main.py --download --tickers SPY")
        is_running = False
        return
    
    # Load all other stocks in parallel
    stock_data_dict = fetch_stock_data_parallel(data_manager, symbols, days=HISTORY)
    
    if not stock_data_dict:
        print("Error: No stock data loaded")
        is_running = False
        return
    
    # Filter out symbols with no data
    symbols_with_data = [symbol for symbol in stock_data_dict if not stock_data_dict[symbol].empty]
    print(f"\n📊 Found data for {len(symbols_with_data)} out of {len(symbols)} symbols")
    
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
    # TELEMETRY: Start recording this simulation
    # ============================================================
    sim_id = telemetry.start_simulation(
        universe_name=args.universe or 'custom',
        symbols=symbols_with_data,
        start_date=common_dates[0],
        end_date=common_dates[-1],
        initial_capital=INITIAL_CASH,
        config={
            'force_liquidate': args.force_liquidate,
            'max_positions': 10,
            'no_universe_check': args.no_universe_check
        }
    )
    
    print(f"\n📊 Telemetry Recording Started")
    print(f"   Simulation ID: {sim_id}")
    print(f"   Database: ./telemetry/simulations.db\n")
    
    # Initialize strategy trackers
    strategy_trackers = {}
    for strategy in strategies:
        strategy.reset()
        strategy_trackers[strategy.name] = StrategyTracker(
            strategy.name, 
            INITIAL_CASH,
            position_size_pct=0.20,
            max_positions=10  # INCREASED FROM 5 TO 10
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
    print("ℹ️  Iteration pattern: For each time step → For each strategy → For each stock")
    print("   This ensures no look-ahead bias and fair turn-taking\n")
    
    for i in range(total_bars):
        # Check for shutdown request
        if _shutdown_requested:
            print("\n⚠️  Simulation interrupted by user")
            is_running = False
            plt.close('all')
            return
        
        current_date = common_dates[i]
        
        # Get current prices
        current_prices = {symbol: stock_data_dict[symbol]['close'].iloc[i] 
                         for symbol in stock_data_dict}
        current_spy_price = spy_data['close'].iloc[i]
        
        # OPTIONAL: UNIVERSE CHECKING - Disabled during simulation
        # We pre-filtered stocks at start, so no need to re-check every iteration
        # Stocks are locked in for the entire simulation period
        # (In production, you'd need a separate delisting feed/API)
        
        # Update SPY tracker
        if i == 0:
            spy_shares = INITIAL_CASH / current_spy_price
            spy_tracker.positions['SPY'] = spy_shares
            spy_tracker.cash = 0
        
        spy_value = spy_tracker.update_portfolio_value(current_date, {'SPY': current_spy_price})
        
        # Record daily snapshot for SPY
        telemetry.record_daily_snapshot(
            sim_id, 'S&P 500', current_date, spy_value,
            spy_tracker.cash, spy_value - spy_tracker.cash,
            1 if spy_tracker.positions.get('SPY', 0) > 0 else 0
        )
        
        # ============================================================
        # STRATEGY ITERATION: Each strategy analyzes all stocks
        # Pattern: strategy1→all stocks, strategy2→all stocks, etc.
        # This is SEQUENTIAL (no parallelization needed) because:
        # 1. Prevents race conditions on shared data
        # 2. Maintains temporal order (no look-ahead bias)
        # 3. Ensures each strategy "gets a turn" before moving to next time step
        # ============================================================
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
                        
                        # ============================================================
                        # TELEMETRY: Record the trade
                        # ============================================================
                        if signal == 'BUY':
                            telemetry.record_trade_entry(
                                sim_id, strategy.name, symbol,
                                current_date, current_prices[symbol],
                                tracker.positions[symbol]
                            )
                        elif signal == 'SELL':
                            telemetry.record_trade_exit(
                                sim_id, strategy.name, symbol,
                                current_date, current_prices[symbol],
                                forced=False, reason='STRATEGY_SIGNAL'
                            )
                        
                    else:
                        # Trade failed
                        signal_stats[strategy.name]['blocked'] += 1
            
            # Update portfolio value
            current_value = tracker.update_portfolio_value(current_date, current_prices)
            
            # Record daily snapshot for this strategy
            positions_value = sum(shares * current_prices.get(symbol, 0) 
                                for symbol, shares in tracker.positions.items())
            
            telemetry.record_daily_snapshot(
                sim_id, strategy.name, current_date, current_value,
                tracker.cash, positions_value,
                tracker.get_current_position_count()
            )
        
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
            
            # Check again after GUI update
            if _shutdown_requested:
                print("\n⚠️  Simulation interrupted by user")
                is_running = False
                plt.close('all')
                return
    
    # OPTIONAL: END-OF-SIMULATION LIQUIDATION
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
                
                # Record forced exits in telemetry
                for symbol in list(tracker.positions.keys()):
                    if tracker.positions.get(symbol, 0) > 0:
                        telemetry.record_trade_exit(
                            sim_id, strategy.name, symbol,
                            final_date, final_prices[symbol],
                            forced=True, reason='FORCE_LIQUIDATION_END_OF_SIM'
                        )
                
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
    # TELEMETRY: Finalize all strategy metrics
    # ============================================================
    spy_returns = pd.Series(spy_tracker.portfolio_value_history).pct_change().dropna()
    
    print("\n" + "="*70)
    print("FINALIZING TELEMETRY RECORDS")
    print("="*70)
    
    for strategy in strategies:
        tracker = strategy_trackers[strategy.name]
        telemetry.finalize_strategy(sim_id, strategy.name, tracker, spy_returns)
        print(f"✅ Recorded: {strategy.name}")
    
    # STORE RESULTS AND CREATE ANALYSIS BUTTONS
    results['strategy_trackers'] = strategy_trackers
    results['spy_tracker'] = spy_tracker
    results['stock_data'] = stock_data_dict
    results['common_dates'] = common_dates
    results['strategies'] = strategies
    results['forced_exits'] = all_forced_exits
    results['sim_id'] = sim_id  # ADDED: Store simulation ID
    
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
    
    # OPEN POSITIONS SUMMARY
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
            for symbol in symbols_with_data:
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
        
        def make_handler(strat_obj, track_obj, stock_dict, syms, spy_track, s_id):
            def handler(event):
                print(f"\n{'='*60}")
                print(f"Analyze button clicked for: {strat_obj.name}")
                print(f"{'='*60}")
                try:
                    # PASS SIM_ID and SPY_TRACKER to analysis!
                    show_strategy_analysis(
                        strat_obj, track_obj, stock_dict, syms,
                        spy_tracker=spy_track,
                        sim_id=s_id
                    )
                except Exception as e:
                    print(f"ERROR in analysis window: {e}")
                    import traceback
                    traceback.print_exc()
            return handler
        
        btn.on_clicked(make_handler(strategy, tracker, stock_data_dict, symbols_with_data, spy_tracker, sim_id))
    
    results['buttons'] = button_refs
    
    is_running = False
    
    # Print telemetry summary
    print("\n" + "="*70)
    print("TELEMETRY SUMMARY")
    print("="*70)
    telemetry.print_simulation_summary(sim_id)
    
    print("\nSimulation complete!")
    print("💡 Press CTRL+C to close all windows and exit")
    print(f"📊 Telemetry saved to: ./telemetry/simulations.db (Simulation ID: {sim_id})")
    
    try:
        plt.show(block=True)
    except KeyboardInterrupt:
        print("\n✅ Exiting...")
        plt.close('all')
        sys.exit(0)