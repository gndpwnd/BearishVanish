"""
Optimized Simulator with Pre-computation and Parallel Processing
Maintains bar-by-bar simulation (no look-ahead bias) while optimizing hot paths
ALWAYS records telemetry - fixed version
"""

import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any
import time
from tqdm import tqdm
import multiprocessing as mp
from pathlib import Path
import json
import importlib.util
import sys
import sqlite3
import logging

from strategy_tracker import StrategyTracker
from simulation_telemetry import SimulationTelemetry, BatchBuffer

# Configure logging
logging.basicConfig(
    filename='simulation_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_simulation_progress(completed, total, current_strategy=None, current_symbol=None):
    """Print clean progress updates"""
    progress_pct = (completed / total * 100) if total > 0 else 0
    print(f"\r📊 Progress: {completed}/{total} ({progress_pct:.1f}%)", end="")
    if current_strategy and current_symbol:
        print(f" | Current: {current_strategy} on {current_symbol}", end="")
    sys.stdout.flush()

# ============================================================
# INDICATOR PRE-COMPUTATION
# ============================================================

def precompute_indicators_for_symbol(symbol: str, 
                                     data: pd.DataFrame,
                                     required_indicators: List[str]) -> pd.DataFrame:
    """
    Pre-compute all indicators for a symbol ONCE
    This is the key optimization - calculate before simulation loop
    COMPLETELY SILENT - no print statements
    """
    if not required_indicators:
        return data
    
    # COMPLETELY SILENT - no timing or print statements
    try:
        from indicator_base import precompute_all_indicators
        enriched_data = precompute_all_indicators(data, required_indicators, use_numba=True)
        return enriched_data
    except ImportError:
        # Silent fallback
        return data

# ============================================================
# STRATEGY LOADER (FIXED for multiprocessing)
# ============================================================

def load_strategy_by_name(strategy_name: str, strategy_config: Dict, quiet: bool = True) -> Any:
    """
    Load a strategy by name - creates fresh instance for each process
    This avoids pickle issues with multiprocessing
    QUIET MODE: No printing for parallel processing
    """
    # Map strategy names to files (FIXED MAPPING)
    # Strategy names from load_strategies in main.py convert filenames like:
    # "strategy_wam.py" -> "Wam" (title case)
    # "strategy_500_intersection.py" -> "500 Intersection"
    
    # Create mapping based on actual filenames
    strategy_map = {}
    strategy_dir = Path('./strategies')
    
    for strategy_file in strategy_dir.glob("strategy_*.py"):
        # Convert filename to strategy name (same logic as load_strategies)
        filename_name = strategy_file.stem.replace('strategy_', '').replace('_', ' ').title()
        strategy_map[filename_name] = strategy_file.name
    
    # Add fallback mappings for common variations
    if strategy_name not in strategy_map:
        # Try variations
        variations = {
            'Wam': 'strategy_wam.py',
            'Weekly Threshold': 'strategy_wam.py',  # Common alternative name
            '500 Intersection': 'strategy_500_intersection.py',
            'Momentum Example': 'strategy_momentum_example.py',
        }
        
        if strategy_name in variations:
            strategy_map[strategy_name] = variations[strategy_name]
        else:
            # Try to find by partial match
            for key, filename in variations.items():
                if strategy_name.lower() in key.lower():
                    strategy_map[strategy_name] = filename
                    break
    
    if strategy_name not in strategy_map:
        if not quiet:
            print(f"⚠️  Strategy not found: {strategy_name}")
            print(f"   Available: {list(strategy_map.keys())}")
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_file = Path(f"./strategies/{strategy_map[strategy_name]}")
    
    try:
        # Load strategy module
        spec = importlib.util.spec_from_file_location(
            f"strategy_{strategy_name.lower().replace(' ', '_')}",
            strategy_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, 'Strategy'):
            raise ValueError(f"No Strategy class in {strategy_file}")
        
        # Create new instance with config (QUIET MODE)
        from strategy_base import StrategyConfig
        config = StrategyConfig(
            name=strategy_name,
            initial_capital=strategy_config.get('initial_capital', 100000),
            position_size_pct=strategy_config.get('position_size_pct', 0.10),
            max_positions=strategy_config.get('max_positions', 10),
            verbose=False  # QUIET MODE FOR PARALLEL
        )
        
        return module.Strategy(config=config)
        
    except Exception as e:
        if not quiet:
            print(f"❌ Error loading strategy {strategy_name}: {e}")
        raise

# ============================================================
# BATCH STRATEGY LOADING (Optimization)
# ============================================================

def create_strategy_instances(strategies):
    '''
    Create strategy instances ONCE, not per simulation
    Store as serializable configs
    '''
    strategy_configs = {}
    
    for strategy in strategies:
        config = strategy.get_config()
        # Store the class and config, not the instance
        strategy_configs[strategy.name] = {
            'config': config,
            'required_indicators': list(strategy.required_indicators),
            'class_name': strategy.__class__.__name__
        }
    
    return strategy_configs

# ============================================================
# DATA COLLECTION FOR TELEMETRY
# ============================================================

def create_trade_attempt_tuple(timestamp, date_str, strategy_name, symbol, signal, 
                               price, volume, avg_volume_20d, relative_volume,
                               portfolio_value, cash, num_positions, max_positions,
                               success, rejection_reason):
    """Create a tuple for trade attempt data"""
    return (
        timestamp,
        date_str,
        strategy_name,
        symbol,
        signal,
        price,
        volume,
        avg_volume_20d,
        relative_volume,
        portfolio_value,
        cash,
        num_positions,
        max_positions,
        1 if success else 0,  # success as integer
        rejection_reason
    )

def create_trade_entry_tuple(strategy_name, symbol, entry_date, entry_price, 
                             shares, portfolio_value, cash, num_positions,
                             entry_reason, volume, avg_volume_20d, relative_volume):
    """Create a tuple for trade entry data - MUST HAVE 14 VALUES"""
    # Get timestamp from entry_date
    if isinstance(entry_date, str):
        entry_date_obj = pd.to_datetime(entry_date)
    else:
        entry_date_obj = entry_date
    
    timestamp = int(entry_date_obj.timestamp()) if hasattr(entry_date_obj, 'timestamp') else int(time.time())
    
    return (
        strategy_name,                    # 1
        symbol,                           # 2
        timestamp,                        # 3 - entry_timestamp
        str(entry_date),                  # 4 - entry_date
        entry_price,                      # 5 - entry_price
        shares,                           # 6 - shares
        volume,                           # 7 - entry_volume
        avg_volume_20d,                   # 8 - entry_avg_volume_20d
        relative_volume,                  # 9 - entry_relative_volume
        portfolio_value,                  # 10 - entry_portfolio_value
        cash,                             # 11 - entry_cash
        num_positions,                    # 12 - entry_num_positions
        entry_reason                      # 13 - entry_reason
    )

def create_trade_exit_tuple(exit_timestamp, exit_date, exit_price, volume,
                            avg_volume_20d, relative_volume, portfolio_value,
                            cash, profit_loss, profit_loss_pct, holding_days,
                            holding_bars, forced, exit_reason, strategy_name, symbol):
    """Create a tuple for trade exit data"""
    return (
        exit_timestamp,
        str(exit_date),
        exit_price,
        volume,
        avg_volume_20d,
        relative_volume,
        portfolio_value,
        cash,
        profit_loss,
        profit_loss_pct,
        holding_days,
        holding_bars,
        1 if forced else 0,  # forced as integer
        exit_reason,
        strategy_name,
        symbol
    )

def create_portfolio_snapshot_tuple(timestamp, strategy_name, date_str,
                                    portfolio_value, cash, equity_in_positions,
                                    num_positions, daily_return):
    """Create a tuple for portfolio snapshot data"""
    return (
        timestamp,
        strategy_name,
        date_str,
        portfolio_value,
        cash,
        equity_in_positions,
        num_positions,
        daily_return
    )

# ============================================================
# OPTIMIZED SIMULATION FUNCTIONS (WITH TELEMETRY)
# ============================================================

def run_single_strategy_on_symbol(strategy_name: str,
                                 strategy_config: Dict,
                                 symbol: str,
                                 stock_data: pd.DataFrame,
                                 spy_data: pd.DataFrame,
                                 args) -> Dict:
    """
    Run a single strategy on a single symbol
    This function is parallelized across all strategy/symbol combinations
    
    Returns ONLY SERIALIZABLE data - no strategy or tracker objects
    """
    try:
        # Load strategy fresh for this process (QUIET MODE)
        strategy = load_strategy_by_name(strategy_name, strategy_config, quiet=True)
        
        # Create strategy tracker
        tracker = StrategyTracker(
            strategy.name,
            initial_cash=strategy.initial_capital,
            position_size_pct=strategy.position_size_pct,
            max_positions=strategy.max_positions,
            verbose=False  # QUIET
        )
        
        # Initialize data collection lists (ALWAYS COLLECT)
        trade_attempts = []
        trade_entries = []
        trade_exits = []
        portfolio_snapshots = []
        
        # Track entry dates for holding period calculation
        entry_dates = {}
        
        # Bar-by-bar iteration (maintains no look-ahead bias)
        rejected_trades = 0
        
        for i in range(len(stock_data)):
            current_date = stock_data.index[i]
            current_price = stock_data['close'].iloc[i]
            
            # Get historical data up to current bar (no future data!)
            historical_data = stock_data.iloc[:i+1]
            historical_spy = spy_data.iloc[:i+1] if i < len(spy_data) else spy_data
            
            # Strategy generates signal (with pre-computed indicators)
            signal = strategy.generate_signal(
                symbol=symbol,
                data=historical_data,
                spy_data=historical_spy,
                bar_index=i
            )
            
            # Get volume metrics if available
            volume_metrics = {}
            if 'volume' in stock_data.columns:
                current_volume = stock_data['volume'].iloc[i]
                volume_metrics['volume'] = current_volume
                
                # Calculate average volume (if enough data)
                if i >= 19:
                    avg_volume = stock_data['volume'].iloc[i-19:i+1].mean()
                    relative_volume = current_volume / avg_volume if avg_volume > 0 else 1.0
                    volume_metrics['avg_volume_20d'] = avg_volume
                    volume_metrics['relative_volume'] = relative_volume
            
            # Check if trade would succeed
            portfolio_value = tracker.get_current_portfolio_value({symbol: current_price})
            cash = tracker.cash
            num_positions = tracker.get_current_position_count()
            max_positions = tracker.max_positions
            
            # Determine if trade would be accepted
            success = False
            rejection_reason = None
            
            if signal == 'BUY':
                if num_positions >= max_positions and symbol not in tracker.positions:
                    rejection_reason = f"Max positions reached ({num_positions}/{max_positions})"
                elif cash < 100:  # Minimum trade size
                    rejection_reason = f"Insufficient cash (${cash:.2f} < $100)"
                else:
                    success = True
            elif signal == 'SELL':
                if tracker.positions.get(symbol, 0) <= 0:
                    rejection_reason = "No position to sell"
                else:
                    success = True
            
            # ALWAYS RECORD trade attempt
            timestamp = time.time()
            trade_attempts.append(
                create_trade_attempt_tuple(
                    timestamp, str(current_date), strategy.name, symbol, signal,
                    current_price, volume_metrics.get('volume', 0),
                    volume_metrics.get('avg_volume_20d', 0),
                    volume_metrics.get('relative_volume', 1.0),
                    portfolio_value, cash, num_positions, max_positions,
                    success, rejection_reason
                )
            )
            
            if not success and rejection_reason:
                rejected_trades += 1
            
            # Execute trade
            if signal in ['BUY', 'SELL']:
                volume = stock_data['volume'].iloc[i] if 'volume' in stock_data.columns else 0
                
                # Execute trade in tracker
                trade_success = tracker.execute_trade(
                    symbol, signal, current_price, current_date,
                    volume=volume
                )
                
                # Record successful trade (ALWAYS RECORD)
                if trade_success:
                    if signal == 'BUY':
                        # Record trade entry
                        portfolio_value = tracker.get_current_portfolio_value({symbol: current_price})
                        cash = tracker.cash
                        num_positions = tracker.get_current_position_count()
                        
                        # Store entry date for holding period calculation
                        entry_dates[symbol] = current_date
                        
                        trade_entries.append(
                            create_trade_entry_tuple(
                                strategy.name, symbol, current_date, current_price,
                                tracker.positions.get(symbol, 0), portfolio_value,
                                cash, num_positions, "Strategy signal",
                                volume, volume_metrics.get('avg_volume_20d', 0),
                                volume_metrics.get('relative_volume', 1.0)
                            )
                        )
                        
                    elif signal == 'SELL':
                        # Record trade exit
                        portfolio_value = tracker.get_current_portfolio_value({symbol: current_price})
                        cash = tracker.cash
                        
                        # Calculate holding period
                        entry_date = entry_dates.get(symbol)
                        holding_days = 0
                        holding_bars = 0
                        if entry_date:
                            # Convert to pandas Timestamp if needed
                            if isinstance(entry_date, str):
                                entry_date = pd.Timestamp(entry_date)
                            if isinstance(current_date, str):
                                current_date = pd.Timestamp(current_date)
                            
                            holding_days = (current_date - entry_date).days
                            # Count bars between entry and exit (simplified)
                            holding_bars = sum(1 for idx in stock_data.index 
                                             if entry_date <= idx <= current_date)
                        
                        # Get trade from tracker's trades (not trade_history)
                        profit_loss = None
                        profit_loss_pct = None
                        
                        # Look for the SELL trade in tracker.trades
                        for trade in tracker.trades:
                            if (trade['symbol'] == symbol and 
                                trade['action'] == 'SELL' and 
                                trade['date'] == current_date):
                                
                                # Calculate P&L
                                if 'proceeds' in trade and 'cost' in trade:
                                    profit_loss = trade['proceeds'] - trade['cost']
                                    profit_loss_pct = (profit_loss / trade['cost']) * 100 if trade['cost'] > 0 else 0
                                break
                        
                        trade_exits.append(
                            create_trade_exit_tuple(
                                timestamp, current_date, current_price, volume,
                                volume_metrics.get('avg_volume_20d', 0),
                                volume_metrics.get('relative_volume', 1.0),
                                portfolio_value, cash, profit_loss,
                                profit_loss_pct, holding_days, holding_bars,
                                False, "Strategy signal", strategy.name, symbol
                            )
                        )
            
            # Record daily snapshot (every 5 bars to reduce data volume)
            if i == len(stock_data) - 1 or i % 5 == 0:
                portfolio_value = tracker.get_current_portfolio_value({symbol: current_price})
                cash = tracker.cash
                num_positions = tracker.get_current_position_count()
                
                # Calculate daily return (simplified)
                daily_return = 0.0
                if i > 0:
                    prev_price = stock_data['close'].iloc[i-1] if i > 0 else current_price
                    if tracker.positions.get(symbol, 0) > 0:
                        # Position return
                        position_return = (current_price - prev_price) / prev_price
                        position_pct = tracker.positions.get(symbol, 0) * prev_price / (
                            tracker.get_current_portfolio_value({symbol: prev_price}) if tracker.get_current_portfolio_value({symbol: prev_price}) > 0 else 1
                        )
                        daily_return = position_return * position_pct
                
                portfolio_snapshots.append(
                    create_portfolio_snapshot_tuple(
                        timestamp, strategy.name, str(current_date),
                        portfolio_value, cash, portfolio_value - cash,
                        num_positions, daily_return
                    )
                )
            
            # Update portfolio value
            current_prices = {symbol: current_price}
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Force liquidation if configured
        if args.force_liquidate:
            final_prices = {symbol: stock_data['close'].iloc[-1]}
            positions_liquidated = tracker.force_liquidate_all(stock_data.index[-1], final_prices)
            
            # Record forced exits if any
            if positions_liquidated > 0:
                portfolio_value = tracker.get_current_portfolio_value({symbol: final_prices[symbol]})
                cash = tracker.cash
                # Use tracker.trades instead of tracker.trade_history
                for trade in tracker.trades[-positions_liquidated:]:
                    if trade['symbol'] == symbol and trade.get('forced', False):
                        # Calculate P&L for forced liquidation
                        profit_loss = None
                        profit_loss_pct = None
                        if 'proceeds' in trade and 'cost' in trade:
                            profit_loss = trade['proceeds'] - trade['cost']
                            profit_loss_pct = (profit_loss / trade['cost']) * 100 if trade['cost'] > 0 else 0
                        
                        trade_exits.append(
                            create_trade_exit_tuple(
                                time.time(), trade['date'], trade['price'], 0,
                                0, 1.0, portfolio_value, cash, profit_loss,
                                profit_loss_pct, 0, 0, True, "Forced liquidation",
                                strategy.name, symbol
                            )
                        )
        
        # Get per-stock performance summary
        stock_performance = tracker.get_stock_performance_summary()
        
        # Return ONLY SERIALIZABLE data (no tracker objects)
        return {
            'strategy': strategy.name,
            'symbol': symbol,
            'strategy_config': strategy_config,  # Add config for later
            'initial_cash': tracker.initial_cash,
            'final_cash': tracker.cash,
            'portfolio_value_history': tracker.portfolio_value_history,
            'portfolio_dates': [str(d) for d in tracker.dates],
            'positions': tracker.positions.copy(),
            'trades_summary': {
                'total_trades': len(tracker.trades),
                'buy_trades': tracker.get_num_buys(),
                'sell_trades': tracker.get_num_sells(),
                'winning_trades': len(tracker.get_winning_trades()),
                'losing_trades': len(tracker.get_losing_trades())
            },
            'rejected_trades': rejected_trades,
            'trade_attempts': trade_attempts,
            'trade_entries': trade_entries,
            'trade_exits': trade_exits,
            'portfolio_snapshots': portfolio_snapshots,
            'stock_performance': stock_performance,  # Add per-stock metrics
            'success': True
        }
        
    except Exception as e:
        # Log error to file AND print to console
        error_msg = f"Error in {strategy_name} on {symbol}: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"âŒ {error_msg}")
        
        import traceback
        traceback.print_exc()
        
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'error': str(e),
            'success': False
        }

# ============================================================
# MAIN SIMULATION FUNCTION (WITH TELEMETRY)
# ============================================================

def run_simulation(strategies, symbols, data_manager, universe_manager, args):
    """
    Main simulation with pre-computation and parallel processing
    ALWAYS records telemetry - parallel workers collect data, main process writes it
    """
    # Initialize telemetry system
    telemetry = SimulationTelemetry()
    
    # Load optimization configuration
    try:
        from config_optimizer import load_optimization_config
        opt_config = load_optimization_config()
        use_numba = opt_config.get('use_numba', True)
        parallel_workers = opt_config.get('parallel_workers', {}).get('simulation', max(1, mp.cpu_count() - 2))
    except ImportError:
        # Default settings
        use_numba = True
        parallel_workers = max(1, mp.cpu_count() - 2)
    
    print(f"\n{'='*70}")
    print("OPTIMIZED SIMULATION ENGINE WITH TELEMETRY")
    print(f"{'='*70}")
    print(f"⚡ Strategies: {len(strategies)}")
    print(f"📈 Symbols: {len(symbols)}")
    print(f"🔧 Workers: {parallel_workers} CPU cores")
    print(f"💾 Telemetry: ALWAYS ENABLED")
    print(f"{'='*70}\n")
    
    # STEP 1: Load all data in batch (optimized)
    print("📥 Loading market data...")
    start_time = time.time()
    
    # Determine date range
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.Timedelta(days=180)
    
    # Load symbols in batch with progress bar
    with tqdm(total=len(symbols), desc="Loading data", unit="stock", 
              bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}',
              ncols=80) as pbar:
        
        # Load all symbols in batch
        data_dict = data_manager.load_multiple_symbols_batch(
            symbols, start_date, end_date
        )
        
        # Update progress bar to show completion
        pbar.update(len(symbols))
    
    # Load SPY data separately
    spy_data = data_manager.get_stock_data('SPY', days=180)
    
    # Filter out None data
    data_dict = {k: v for k, v in data_dict.items() if v is not None and not v.empty}
    
    print(f"✅ Loaded {len(data_dict)} symbols in {(time.time() - start_time):.1f}s\n")
    
    if not data_dict:
        print("❌ No data loaded for simulation")
        return None
    
    # STEP 2: Collect all required indicators
    all_required_indicators = set()
    for strategy in strategies:
        all_required_indicators.update(strategy.required_indicators)
    
    # STEP 3: Pre-compute indicators for all symbols
    print(f"⚡ Pre-computing {len(all_required_indicators)} indicators...")
    
    # Set indicator library for strategies if available
    try:
        from indicator_loader import get_indicator_library
        indicator_library = get_indicator_library()
        for strategy in strategies:
            strategy.set_indicator_library(indicator_library)
    except ImportError:
        indicator_library = None
    
    enriched_data_dict = {}
    
    # Pre-compute indicators for each symbol with clean progress bar
    for symbol in tqdm(list(data_dict.keys()), desc="Indicators", unit="stock", 
                      bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}',
                      ncols=80):
        if symbol in data_dict:
            enriched_data = precompute_indicators_for_symbol(
                symbol,
                data_dict[symbol],
                list(all_required_indicators)
            )
            enriched_data_dict[symbol] = enriched_data
    
    print(f"✅ Indicators ready\n")
    
    # STEP 4: Record simulation start in telemetry
    telemetry.record_simulation_start(
        universe_name=args.universe or 'custom',
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=strategies[0].initial_capital if strategies else 100000,
        config={'optimized': True, 'use_numba': use_numba, 'parallel_workers': parallel_workers}
    )
    
    # STEP 5: Run simulations in parallel and COLLECT ALL DATA
    print("🚀 Running parallel simulations...")
    
    # Create tasks with strategy CONFIGS instead of instances
    tasks = []
    for strategy in strategies:
        strategy_config = strategy.get_config()  # Get serializable config
        for symbol in symbols:
            if symbol in enriched_data_dict:
                tasks.append((strategy.name, strategy_config, symbol))
    
    print(f"  Total simulations: {len(tasks)}")
    
    # Initialize data collection lists
    all_trade_attempts = []
    all_trade_entries = []
    all_trade_exits = []
    all_portfolio_snapshots = []
    all_stock_performance = []  # Collect per-stock performance
    
    # Store strategy performance data (serializable only)
    strategy_performances = {}
    
    start_time = time.time()
    
    # ALWAYS USE PARALLEL PROCESSING
    with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                run_single_strategy_on_symbol,
                strategy_name, strategy_config, symbol, 
                enriched_data_dict[symbol], spy_data, args
            ): (strategy_name, symbol)
            for strategy_name, strategy_config, symbol in tasks
        }
        
        # Process results as they complete
        with tqdm(total=len(futures), 
                 desc="Simulating", 
                 unit="sim",
                 bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
                 ncols=100) as pbar:
            
            for future in as_completed(futures):
                strategy_name, symbol = futures[future]
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        # Store performance data (serializable only)
                        if strategy_name not in strategy_performances:
                            strategy_performances[strategy_name] = {
                                'config': result.get('strategy_config', {}),
                                'symbols': [],
                                'rejected_trades': 0,
                            }
                        
                        # Update performance data
                        perf = strategy_performances[strategy_name]
                        perf['symbols'].append(symbol)
                        perf['rejected_trades'] += result.get('rejected_trades', 0)
                        
                        # COLLECT ALL TELEMETRY DATA
                        all_trade_attempts.extend(result.get('trade_attempts', []))
                        all_trade_entries.extend(result.get('trade_entries', []))
                        all_trade_exits.extend(result.get('trade_exits', []))
                        all_portfolio_snapshots.extend(result.get('portfolio_snapshots', []))
                        
                        # COLLECT STOCK PERFORMANCE DATA
                        stock_perf = result.get('stock_performance', {})
                        for stock_symbol, metrics in stock_perf.items():
                            all_stock_performance.append({
                                'strategy_name': strategy_name,
                                'symbol': stock_symbol,
                                'num_trades': metrics.get('num_trades', 0),
                                'num_buys': metrics.get('num_buys', 0),
                                'num_sells': metrics.get('num_sells', 0),
                                'total_invested': metrics.get('total_invested', 0),
                                'total_returned': metrics.get('total_returned', 0),
                                'pnl': metrics.get('pnl', 0),
                                'pnl_pct': metrics.get('pnl_pct', 0),
                                'win_rate': metrics.get('win_rate', 0),
                                'wins': metrics.get('wins', 0),
                                'losses': metrics.get('losses', 0),
                                'current_shares': metrics.get('current_shares', 0),
                            })
                    
                except Exception as e:
                    # Log and display errors
                    error_msg = f"Error processing {strategy_name} on {symbol}: {e}"
                    logger.error(error_msg, exc_info=True)
                    print(f"\nâŒ {error_msg}")
                    
                    import traceback
                    traceback.print_exc()
                
                pbar.update(1)
    
    simulation_time = time.time() - start_time
    
    # STEP 6: WRITE ALL COLLECTED DATA TO DATABASE
    print(f"\n💾 Recording telemetry data...")
    
    # DEBUG: Check what data we collected
    print(f"  📊 Collected data counts:")
    print(f"    Trade attempts: {len(all_trade_attempts):,}")
    print(f"    Trade entries: {len(all_trade_entries):,}")
    print(f"    Trade exits: {len(all_trade_exits):,}")
    print(f"    Portfolio snapshots: {len(all_portfolio_snapshots):,}")
    
    # Write trade attempts
    if all_trade_attempts:
        print(f"  📝 Writing {len(all_trade_attempts)} trade attempts...")
        try:
            telemetry.batch_insert_trade_attempts(all_trade_attempts)
            print(f"    ✅ Trade attempts written successfully")
        except Exception as e:
            print(f"    ❌ Error writing trade attempts: {e}")

    # Write trade entries
    if all_trade_entries:
        print(f"  📈 Writing {len(all_trade_entries)} trade entries...")
        try:
            telemetry.batch_insert_trade_entries(all_trade_entries)
            print(f"    ✅ Trade entries written successfully")
        except Exception as e:
            print(f"    ❌ Error writing trade entries: {e}")
    
    # Write trade exits
    if all_trade_exits:
        print(f"  📉 Writing {len(all_trade_exits)} trade exits...")
        try:
            telemetry.batch_update_trade_exits(all_trade_exits)
            print(f"    ✅ Trade exits written successfully")
        except Exception as e:
            print(f"    ❌ Error writing trade exits: {e}")
    
    # Write portfolio snapshots
    if all_portfolio_snapshots:
        print(f"  📊 Writing {len(all_portfolio_snapshots)} portfolio snapshots...")
        try:
            telemetry.batch_insert_portfolio_snapshots(all_portfolio_snapshots)
            print(f"    ✅ Portfolio snapshots written successfully")
        except Exception as e:
            print(f"    ❌ Error writing portfolio snapshots: {e}")
    
    # Write stock performance (per-symbol metrics)
    if all_stock_performance:
        print(f"  📈 Writing {len(all_stock_performance)} stock performance records...")
        try:
            conn = sqlite3.connect(telemetry.db_path)
            conn.text_factory = str
            cursor = conn.cursor()
            
            for perf in all_stock_performance:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_performance
                    (strategy_name, symbol, num_trades, num_buys, num_sells,
                     total_invested, total_returned, pnl, pnl_pct, win_rate,
                     winning_trades, losing_trades, current_shares, created_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    perf['strategy_name'],
                    perf['symbol'],
                    perf['num_trades'],
                    perf['num_buys'],
                    perf['num_sells'],
                    perf['total_invested'],
                    perf['total_returned'],
                    perf['pnl'],
                    perf['pnl_pct'],
                    perf['win_rate'],
                    perf['wins'],
                    perf['losses'],
                    perf['current_shares'],
                    int(time.time())
                ))
            
            conn.commit()
            conn.close()
            print(f"    ✅ Stock performance written successfully")
        except Exception as e:
            print(f"    ❌ Error writing stock performance: {e}")
            import traceback
            traceback.print_exc()
    
    # STEP 7: Finalize strategy performance (database version)
    print(f"\n📊 Finalizing strategy performance...")
    
    # Store strategy configurations
    for strategy in strategies:
        strategy_config = strategy.get_config()
        
        # Store config in database
        conn = sqlite3.connect(telemetry.db_path)
        conn.text_factory = str  # Ensure UTF-8 compatibility
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_configs
            (strategy_name, initial_capital, position_size_pct, max_positions, 
            color, parameters_json, created_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy.name,
            strategy.initial_capital,
            strategy.position_size_pct,
            strategy.max_positions,
            strategy.color,
            json.dumps(strategy_config),
            int(time.time())
        ))
        
        conn.commit()
        conn.close()
    
    # Finalize each strategy using database queries
    for strategy_name in strategy_performances.keys():
        telemetry.finalize_strategy(
            strategy_name=strategy_name,
            rejected_count=strategy_performances[strategy_name].get('rejected_trades', 0)
        )
        print(f"  ✅ {strategy_name}: Finalized with database queries")
    
    # Record simulation end
    telemetry.record_simulation_end()
    
    # Print summary
    total_sims = len(tasks)
    if simulation_time > 0:
        calc_per_second = total_sims * 180 / simulation_time  # 180 bars per symbol
    else:
        calc_per_second = 0
    
    print(f"\n{'='*70}")
    print("✅ SIMULATION COMPLETE WITH TELEMETRY")
    print(f"{'='*70}")
    print(f"📊 Completed: {total_sims} simulations")
    print(f"⏱️  Time: {simulation_time:.1f}s ({simulation_time/total_sims:.2f}s per sim)")
    print(f"⚡ Speed: {calc_per_second:,.0f} calculations/sec")
    print(f"💾 Database: {telemetry.db_path}")
    
    # Data recording summary
    print(f"\n📈 TELEMETRY RECORDED:")
    print(f"   Trade attempts: {len(all_trade_attempts):,}")
    print(f"   Trade entries: {len(all_trade_entries):,}")
    print(f"   Trade exits: {len(all_trade_exits):,}")
    print(f"   Portfolio snapshots: {len(all_portfolio_snapshots):,}")
    print(f"   Stock performance records: {len(all_stock_performance):,}")
    print(f"   Strategies finalized: {len(strategy_performances):,}")
    
    # Print performance improvement estimate
    if total_sims > 0 and simulation_time > 0:
        estimated_baseline_time = total_sims * 0.5  # Estimated 0.5s per task baseline
        speedup = estimated_baseline_time / simulation_time
        print(f"🎯 Estimated speedup: {speedup:.1f}x")
    
    # Quick verification
    try:
        conn = sqlite3.connect(telemetry.db_path)
        conn.text_factory = str  # Ensure UTF-8 compatibility
        cursor = conn.cursor()
        
        print(f"\n📊 QUICK VERIFICATION:")
        cursor.execute("SELECT COUNT(*) FROM trade_history")
        trade_count = cursor.fetchone()[0]
        print(f"   Trade history rows: {trade_count:,}")
        
        cursor.execute("SELECT strategy_name, total_trades FROM strategy_performance")
        strategies_check = cursor.fetchall()
        for strat_name, total_trades in strategies_check:
            print(f"   {strat_name}: {total_trades} trades in performance table")
        
        conn.close()
    except Exception as e:
        print(f"   ⚠️  Verification failed: {e}")
    
    print(f"{'='*70}\n")
    
    return telemetry.db_path

# ============================================================
# PERFORMANCE TESTING (UPDATED)
# ============================================================

def test_performance_improvement(strategies, symbols, data_manager, universe_manager, args):
    """
    Test performance improvement with optimizations and telemetry
    """
    print(f"\n{'='*70}")
    print("PERFORMANCE TEST WITH TELEMETRY")
    print(f"{'='*70}")
    
    # Test with a subset
    test_symbols = symbols[:5] if len(symbols) > 5 else symbols
    test_strategies = strategies[:2] if len(strategies) > 2 else strategies
    
    print(f"Testing with {len(test_strategies)} strategies and {len(test_symbols)} symbols")
    print(f"Expected improvement: 5-15x speedup with telemetry")
    print(f"{'='*70}\n")
    
    # Time the simulation
    start_time = time.time()
    db_path = run_simulation(test_strategies, test_symbols, data_manager, universe_manager, args)
    elapsed = time.time() - start_time
    
    print(f"✅ Performance test completed in {elapsed:.2f}s")
    
    # Estimate baseline (assuming 0.5s per strategy-symbol without optimization)
    estimated_baseline = len(test_strategies) * len(test_symbols) * 0.5
    speedup = estimated_baseline / elapsed if elapsed > 0 else 1
    
    print(f"📈 Estimated speedup: {speedup:.1f}x")
    print(f"   Baseline estimate: {estimated_baseline:.1f}s")
    print(f"   Actual: {elapsed:.2f}s")
    
    # Verify data was written
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.text_factory = str  # Ensure UTF-8 compatibility
    cursor = conn.cursor()
    
    tables = ['trade_attempts', 'trade_history', 'portfolio_history', 'strategy_performance']
    print(f"\n📊 Database verification:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {table}: {count} rows")
    
    conn.close()
    
    if speedup > 3:
        print(f"🎉 Great! Optimizations are working well with telemetry")
    else:
        print(f"⚠️  Speedup less than expected. Check configuration.")
    
    return db_path, speedup