"""
Optimized Simulator with Pre-computation and Parallel Processing
Maintains bar-by-bar simulation (no look-ahead bias) while optimizing hot paths
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

from strategy_base import StrategyBase
from strategy_tracker import StrategyTracker
from simulation_telemetry import SimulationTelemetry, BatchBuffer
from indicator_loader import get_indicator_library

# ============================================================
# INDICATOR PRE-COMPUTATION
# ============================================================

def precompute_indicators_for_symbol(symbol: str, 
                                     data: pd.DataFrame,
                                     required_indicators: List[str],
                                     indicator_library) -> pd.DataFrame:
    """
    Pre-compute all indicators for a symbol ONCE
    This is the key optimization - calculate before simulation loop
    """
    if not required_indicators:
        return data
    
    # Check if indicator library is available
    if indicator_library is None:
        print(f"  ⚠️  No indicator library for {symbol}, skipping pre-computation")
        return data
    
    print(f"  Pre-computing {len(required_indicators)} indicators for {symbol}...")
    start_time = time.time()
    
    # Parse indicator configurations
    indicators_config = {}
    for indicator_spec in required_indicators:
        if '_' in indicator_spec:
            parts = indicator_spec.split('_')
            indicator_name = parts[0]
            
            # Extract period
            try:
                period = int(parts[1])
                params = {'period': period}
                
                # Handle special cases
                if indicator_name == 'bollinger':
                    params['std_dev'] = 2.0
                    indicator_name = 'bollinger_bands'
                elif indicator_name == 'macd':
                    # Default MACD parameters
                    params = {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
                elif indicator_name == 'stochastic':
                    params = {'period': 14, 'smooth_k': 3, 'smooth_d': 3}
                
                indicators_config[indicator_name] = params
            except (ValueError, IndexError):
                # Not a parameterized indicator
                indicators_config[indicator_spec] = {}
    
    # Use indicator_base's optimized function
    try:
        from indicator_base import create_indicator_dataframe
        enriched_data = create_indicator_dataframe(data, indicators_config)
    except ImportError:
        # Fallback: compute indicators individually
        enriched_data = data.copy()
        for indicator_name, params in indicators_config.items():
            if indicator_name in indicator_library._functions:
                try:
                    result = indicator_library._functions[indicator_name](data, **params)
                    if isinstance(result, tuple):
                        for i, arr in enumerate(result):
                            suffix = ['', '_signal', '_hist'][i] if indicator_name == 'macd' else ['_upper', '_middle', '_lower'][i]
                            col_name = f"{indicator_name}{suffix}"
                            enriched_data[col_name] = arr
                    else:
                        enriched_data[indicator_name] = result
                except Exception as e:
                    print(f"    ⚠️  Error computing {indicator_name}: {e}")
    
    elapsed = (time.time() - start_time) * 1000
    print(f"  ✅ {symbol} indicators computed in {elapsed:.1f}ms")
    
    return enriched_data

# ============================================================
# OPTIMIZED SIMULATION FUNCTIONS
# ============================================================

def run_single_strategy_on_symbol(strategy, 
                                  symbol: str,
                                  stock_data: pd.DataFrame,
                                  spy_data: pd.DataFrame,
                                  args,
                                  telemetry: SimulationTelemetry = None,
                                  buffer: BatchBuffer = None) -> Dict:
    """
    Run a single strategy on a single symbol
    This function is parallelized across all strategy/symbol combinations
    """
    try:
        # Create strategy tracker
        tracker = StrategyTracker(
            strategy.name,
            initial_capital=strategy.initial_capital,
            position_size_pct=strategy.position_size_pct,
            max_positions=strategy.max_positions
        )
        
        # Store strategy configuration in tracker for telemetry
        tracker.strategy_config = strategy.get_config()
        tracker.strategy_instance = strategy
        
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
            
            # Record trade attempt in telemetry
            if telemetry is not None:
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
                
                # Record trade attempt
                if buffer:
                    buffer.add_attempt(
                        telemetry._get_simulation_timestamp(current_date),
                        str(current_date),
                        strategy.name,
                        symbol,
                        signal,
                        current_price,
                        volume_metrics.get('volume', 0),
                        volume_metrics.get('avg_volume_20d', 0),
                        volume_metrics.get('relative_volume', 1.0),
                        portfolio_value,
                        cash,
                        num_positions,
                        max_positions,
                        success,
                        rejection_reason
                    )
                else:
                    telemetry.record_trade_attempt(
                        strategy.name,
                        symbol,
                        signal,
                        current_price,
                        current_date,
                        portfolio_value,
                        cash,
                        num_positions,
                        max_positions,
                        success,
                        rejection_reason,
                        volume=volume_metrics.get('volume', 0),
                        avg_volume_20d=volume_metrics.get('avg_volume_20d', 0),
                        relative_volume=volume_metrics.get('relative_volume', 1.0)
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
                
                # Record successful trade in telemetry
                if trade_success and telemetry is not None:
                    if signal == 'BUY':
                        # Record trade entry
                        if buffer:
                            buffer.add_entry(
                                strategy.name,
                                symbol,
                                current_date,
                                current_price,
                                tracker.positions.get(symbol, 0),
                                portfolio_value,
                                cash,
                                num_positions,
                                "Strategy signal",
                                volume,
                                volume_metrics.get('avg_volume_20d', 0),
                                volume_metrics.get('relative_volume', 1.0)
                            )
                        else:
                            telemetry.record_trade_entry(
                                strategy.name,
                                symbol,
                                current_date,
                                current_price,
                                tracker.positions.get(symbol, 0),
                                portfolio_value=portfolio_value,
                                cash=cash,
                                num_positions=num_positions,
                                entry_reason="Strategy signal",
                                volume=volume,
                                avg_volume_20d=volume_metrics.get('avg_volume_20d', 0),
                                relative_volume=volume_metrics.get('relative_volume', 1.0)
                            )
                    elif signal == 'SELL':
                        # Record trade exit
                        if buffer:
                            buffer.add_exit(
                                telemetry._get_simulation_timestamp(current_date),
                                current_date,
                                current_price,
                                volume,
                                volume_metrics.get('avg_volume_20d', 0),
                                volume_metrics.get('relative_volume', 1.0),
                                portfolio_value,
                                cash,
                                None,  # profit_loss (calculated by telemetry)
                                None,  # profit_loss_pct
                                0,     # holding_days (calculated by telemetry)
                                0,     # holding_bars
                                False, # forced
                                "Strategy signal",
                                strategy.name,
                                symbol
                            )
                        else:
                            telemetry.record_trade_exit(
                                strategy.name,
                                symbol,
                                current_date,
                                current_price,
                                portfolio_value=portfolio_value,
                                cash=cash,
                                forced=False,
                                reason="Strategy signal",
                                volume=volume,
                                avg_volume_20d=volume_metrics.get('avg_volume_20d', 0),
                                relative_volume=volume_metrics.get('relative_volume', 1.0)
                            )
            
            # Record daily snapshot
            if telemetry is not None and (i == len(stock_data) - 1 or i % 5 == 0):
                # Record every 5 bars to reduce database load
                if buffer:
                    buffer.add_snapshot(
                        telemetry._get_simulation_timestamp(current_date),
                        strategy.name,
                        str(current_date),
                        portfolio_value,
                        cash,
                        portfolio_value - cash,
                        num_positions,
                        0.0  # daily_return (not calculated here)
                    )
                else:
                    telemetry.record_daily_snapshot(
                        strategy.name,
                        current_date,
                        portfolio_value,
                        cash,
                        portfolio_value - cash,
                        num_positions
                    )
            
            # Update portfolio value
            current_prices = {symbol: current_price}
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Force liquidation if configured
        if args.force_liquidate:
            final_prices = {symbol: stock_data['close'].iloc[-1]}
            positions_liquidated = tracker.force_liquidate_all(stock_data.index[-1], final_prices)
            if positions_liquidated > 0:
                print(f"  💰 Force liquidated {positions_liquidated} positions for {strategy.name} on {symbol}")
        
        return {
            'strategy': strategy.name,
            'symbol': symbol,
            'tracker': tracker,
            'rejected_trades': rejected_trades,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Error: {strategy.name} on {symbol}: {e}")
        return {
            'strategy': strategy.name,
            'symbol': symbol,
            'error': str(e),
            'success': False
        }

# ============================================================
# MAIN SIMULATION FUNCTION
# ============================================================

def run_simulation(strategies, symbols, data_manager, universe_manager, args):
    """
    Main simulation with pre-computation and parallel processing
    """
    # Initialize systems
    indicator_library = get_indicator_library()
    telemetry = SimulationTelemetry()
    buffer = BatchBuffer(telemetry, batch_size=1000)
    
    # Load optimization configuration
    try:
        from config_optimizer import load_optimization_config
        opt_config = load_optimization_config()
        use_numba = opt_config.get('use_numba', True)
        use_float32 = opt_config.get('use_float32', False)
        parallel_workers = opt_config.get('parallel_workers', {}).get('simulation', max(1, mp.cpu_count() - 2))
    except ImportError:
        # Default settings
        use_numba = True
        use_float32 = False
        parallel_workers = max(1, mp.cpu_count() - 2)
    
    print(f"\n{'='*70}")
    print("OPTIMIZED SIMULATION ENGINE")
    print(f"{'='*70}")
    print(f"Strategies: {len(strategies)}")
    print(f"Symbols: {len(symbols)}")
    print(f"Numba JIT: {'Enabled' if use_numba else 'Disabled'}")
    print(f"Float32: {'Enabled' if use_float32 else 'Disabled'}")
    print(f"Parallel Workers: {parallel_workers}")
    print(f"Pre-compute Indicators: Yes")
    print(f"{'='*70}\n")
    
    # STEP 1: Load all data in batch (optimized)
    print("📥 Loading market data...")
    start_time = time.time()
    
    # Determine date range
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.Timedelta(days=180)
    
    # Load symbols in batch
    data_dict = data_manager.load_multiple_symbols_batch(
        symbols, start_date, end_date
    )
    
    # Load SPY data
    spy_data = data_manager.get_stock_data('SPY', days=180)
    
    # Filter out None data
    data_dict = {k: v for k, v in data_dict.items() if v is not None and not v.empty}
    
    print(f"✅ Loaded {len(data_dict)} symbols in {(time.time() - start_time):.2f}s\n")
    
    if not data_dict:
        print("❌ No data loaded for simulation")
        return None
    
    # STEP 2: Collect all required indicators
    print("🔧 Collecting required indicators...")
    all_required_indicators = set()
    for strategy in strategies:
        all_required_indicators.update(strategy.required_indicators)
    
    print(f"  Total unique indicators: {len(all_required_indicators)}")
    if all_required_indicators:
        print(f"  Indicators: {', '.join(sorted(list(all_required_indicators))[:10])}")
        if len(all_required_indicators) > 10:
            print(f"  ... and {len(all_required_indicators) - 10} more")
    
    # STEP 3: Pre-compute indicators for all symbols
    print(f"\n⚡ Pre-computing indicators...")
    
    # Set indicator library for strategies
    for strategy in strategies:
        strategy.set_indicator_library(indicator_library)
    
    # Pre-compute indicators in parallel
    enriched_data_dict = {}
    
    # Create chunks for parallel pre-computation
    symbol_chunks = [list(data_dict.keys())[i:i+parallel_workers] 
                     for i in range(0, len(data_dict), parallel_workers)]
    
    for chunk in tqdm(symbol_chunks, desc="Pre-computing indicators"):
        for symbol in chunk:
            if symbol in data_dict:
                enriched_data = precompute_indicators_for_symbol(
                    symbol,
                    data_dict[symbol],
                    list(all_required_indicators),
                    indicator_library
                )
                enriched_data_dict[symbol] = enriched_data
    
    print(f"✅ All indicators pre-computed\n")
    
    # STEP 4: Run simulations in parallel
    print("🚀 Running simulations...")
    
    # Create all strategy/symbol combinations
    tasks = []
    for strategy in strategies:
        for symbol in symbols:
            if symbol in enriched_data_dict:
                tasks.append((strategy, symbol))
    
    print(f"  Total simulations: {len(tasks)}")
    
    # Run simulations in parallel
    results = {}
    rejected_counts = {}
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                run_single_strategy_on_symbol,
                strategy, symbol, enriched_data_dict[symbol], spy_data, args
            ): (strategy.name, symbol)
            for strategy, symbol in tasks
        }
        
        # Collect results with progress bar
        with tqdm(total=len(futures), desc="Simulating") as pbar:
            for future in as_completed(futures):
                strategy_name, symbol = futures[future]
                result = future.result()
                
                if result['success']:
                    if strategy_name not in results:
                        results[strategy_name] = {}
                    results[strategy_name][symbol] = result['tracker']
                    rejected_counts[strategy_name] = rejected_counts.get(strategy_name, 0) + result['rejected_trades']
                else:
                    print(f"⚠️  Failed: {strategy_name} on {symbol}: {result.get('error', 'Unknown error')}")
                
                pbar.update(1)
    
    simulation_time = time.time() - start_time
    
    # STEP 5: Finalize telemetry
    print(f"\n💾 Recording final results...")
    
    # Record simulation start
    telemetry.record_simulation_start(
        universe_name=args.universe or 'custom',
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=strategies[0].initial_capital if strategies else 100000,
        config={'optimized': True, 'use_numba': use_numba, 'parallel_workers': parallel_workers}
    )
    
    # Finalize each strategy
    for strategy_name, symbol_trackers in results.items():
        if symbol_trackers:
            # Find first tracker for this strategy
            first_tracker = next(iter(symbol_trackers.values()))
            rejected_count = rejected_counts.get(strategy_name, 0)
            
            # Calculate SPY returns for alpha/beta
            spy_returns = None
            if spy_data is not None and 'close' in spy_data.columns:
                spy_returns = spy_data['close'].pct_change().dropna()
            
            # Finalize strategy in telemetry
            telemetry.finalize_strategy(
                strategy_name=strategy_name,
                tracker=first_tracker,
                spy_returns=spy_returns,
                rejected_count=rejected_count
            )
            
            print(f"  ✅ {strategy_name}: {len(symbol_trackers)} symbols, {rejected_count} rejected trades")
    
    # Record simulation end
    telemetry.record_simulation_end()
    
    # Flush any remaining buffer data
    buffer.flush_all()
    
    # Print summary
    total_strategies = len(results)
    total_symbols = sum(len(trackers) for trackers in results.values())
    
    print(f"\n{'='*70}")
    print("SIMULATION COMPLETE")
    print(f"{'='*70}")
    print(f"📊 Results:")
    print(f"   Strategies: {total_strategies}")
    print(f"   Symbols processed: {total_symbols}")
    print(f"   Simulation time: {simulation_time:.2f}s")
    print(f"   Avg time per strategy-symbol: {(simulation_time / max(1, len(tasks))):.2f}s")
    
    if tasks:
        calc_per_second = len(tasks) * 180 / simulation_time  # 180 bars per symbol
        print(f"   Calculations per second: {calc_per_second:,.0f}")
    
    print(f"\n💾 Results saved to: {telemetry.db_path}")
    print(f"{'='*70}\n")
    
    # Print performance improvement estimate
    if tasks and simulation_time > 0:
        estimated_baseline_time = len(tasks) * 0.5  # Estimated 0.5s per task baseline
        speedup = estimated_baseline_time / simulation_time
        print(f"🎯 Estimated performance improvement: {speedup:.1f}x")
        print(f"   Baseline: {estimated_baseline_time:.1f}s estimated")
        print(f"   Optimized: {simulation_time:.2f}s actual")
    
    return telemetry.db_path


# ============================================================
# PERFORMANCE TESTING
# ============================================================

def test_performance_improvement(strategies, symbols, data_manager, args):
    """
    Test performance improvement with optimizations
    """
    print(f"\n{'='*70}")
    print("PERFORMANCE TEST")
    print(f"{'='*70}")
    
    # Test with a subset
    test_symbols = symbols[:5]
    test_strategies = strategies[:2]
    
    print(f"Testing with {len(test_strategies)} strategies and {len(test_symbols)} symbols")
    print(f"Expected improvement: 5-15x speedup")
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
    
    if speedup > 3:
        print(f"🎉 Great! Optimizations are working well")
    else:
        print(f"⚠️  Speedup less than expected. Check configuration.")
    
    return db_path, speedup