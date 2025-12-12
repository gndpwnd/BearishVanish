# ============================================================
# SIMULATOR.PY PATCHES - Add these changes
# ============================================================

# CHANGE 1: Update tracker initialization (around line 610)
# OLD CODE:
# strategy_trackers[strategy.name] = StrategyTracker(strategy.name, INITIAL_CASH)

# NEW CODE:
strategy_trackers[strategy.name] = StrategyTracker(
    strategy.name, 
    INITIAL_CASH,
    position_size_pct=0.20,
    max_positions=10  # â† INCREASED from 5 to 10
)

# ============================================================

# CHANGE 2: Add liquidation at end of simulation (after main loop, before storing results)
# INSERT THIS CODE after the main simulation loop ends:

# ============================================================
# END-OF-SIMULATION LIQUIDATION
# ============================================================
print("\nðŸ"Š Liquidating all positions at end of simulation...")

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

# ============================================================

# CHANGE 3: Add progress indicators (optional but helpful)
# INSERT THIS in the main simulation loop (around line 750):

# Show progress every 20 bars
if i % 20 == 0 and i > 0:
    print(f"  Progress: {i}/{total_bars} bars ({i/total_bars*100:.1f}%)")
    
    # Show current state
    for strategy in strategies:
        tracker = strategy_trackers[strategy.name]
        positions = tracker.get_current_position_count()
        if positions > 0:
            print(f"    {strategy.name}: {positions}/{tracker.max_positions} positions, "
                  f"${tracker.cash:,.0f} cash, "
                  f"${tracker.get_current_portfolio_value(current_prices):,.0f} portfolio")

# ============================================================

# CHANGE 4: Fix signal checking logic (around line 720)
# This ensures signals can alternate properly

# OLD CODE:
# if signal:
#     signal_stats[strategy.name]['attempts'] += 1
#     
#     # Check if we can actually execute
#     can_execute = True
#     # ...

# NEW CODE:
if signal:
    signal_stats[strategy.name]['attempts'] += 1
    
    # Execute the trade (let execute_trade handle all checks)
    success = tracker.execute_trade(
        symbol, signal, 
        current_prices[symbol], current_date
    )
    
    if success:
        # Trade executed successfully!
        strategy.record_execution(signal, symbol)
        signal_stats[strategy.name]['executed'] += 1
    else:
        # Trade failed - this is normal and expected
        signal_stats[strategy.name]['blocked'] += 1

# ============================================================

# COMPLETE MODIFIED SECTION FOR MAIN SIMULATION LOOP:

    # Simulate bar by bar
    print("Running simulation...")
    for i in range(total_bars):
        current_date = common_dates[i]
        
        # Get current prices for all stocks
        current_prices = {symbol: stock_data_dict[symbol]['close'].iloc[i] 
                         for symbol in stock_data_dict}
        current_spy_price = spy_data['close'].iloc[i]
        
        # ============================================================
        # DAILY UNIVERSE CHECK - FORCED LIQUIDATION
        # ============================================================
        if args.universe:
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
        
        # ============================================================
        # REGULAR SIMULATION LOGIC
        # ============================================================
        
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
                        # Trade failed (insufficient cash or other issue)
                        signal_stats[strategy.name]['blocked'] += 1
            
            # Update portfolio value
            tracker.update_portfolio_value(current_date, current_prices)
        
        # Show progress every 20 bars
        if i % 20 == 0 and i > 0:
            print(f"  Progress: {i}/{total_bars} bars ({i/total_bars*100:.1f}%)")
            
            # Show current state for each strategy
            for strategy in strategies:
                tracker = strategy_trackers[strategy.name]
                positions = tracker.get_current_position_count()
                if positions > 0:
                    portfolio_val = tracker.get_current_portfolio_value(current_prices)
                    print(f"    {strategy.name}: {positions}/{tracker.max_positions} positions, "
                          f"${tracker.cash:,.0f} cash, ${portfolio_val:,.0f} total")
        
        # Update plot every 10 bars for performance
        if i % 10 == 0 or i == total_bars - 1:
            # ... existing plot update code ...
            pass
    
    # ============================================================
    # END-OF-SIMULATION LIQUIDATION
    # ============================================================
    print("\nðŸ"Š Liquidating all positions at end of simulation...")
    
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
    
    # ============================================================
    # STORE RESULTS AND CREATE ANALYSIS BUTTONS
    # ============================================================
    
    # Store final results
    results['strategy_trackers'] = strategy_trackers
    results['spy_tracker'] = spy_tracker
    results['stock_data'] = stock_data_dict
    results['common_dates'] = common_dates
    results['strategies'] = strategies
    results['forced_exits'] = all_forced_exits
    
    # ... rest of existing code ...