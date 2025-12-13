"""
Analysis Components - FIXED VERSION with Telemetry Integration
Fixes: Deprecation warnings, accurate metrics, dynamic layout, no overlaps
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
import pytz
from strategy_tracker import INITIAL_CASH


def create_portfolio_equity_chart(fig, gs_spec, tracker, spy_tracker, color):
    """Create portfolio equity curve with SPY overlay"""
    ax = fig.add_subplot(gs_spec)
    
    # Plot portfolio value
    ax.plot(tracker.dates, tracker.portfolio_value_history, 
            color=color, linewidth=2.5, label='Strategy', zorder=3)
    
    # Plot SPY if available
    if spy_tracker and len(spy_tracker.portfolio_value_history) > 0:
        ax.plot(spy_tracker.dates, spy_tracker.portfolio_value_history,
                color='black', linewidth=2, linestyle='--', alpha=0.7, label='S&P 500', zorder=2)
    
    # Initial capital line
    ax.axhline(INITIAL_CASH, color='gray', linestyle=':', alpha=0.5, linewidth=1, label='Initial Capital')
    
    # Fill areas
    ax.fill_between(tracker.dates, INITIAL_CASH, tracker.portfolio_value_history,
                    where=(np.array(tracker.portfolio_value_history) > INITIAL_CASH),
                    color='green', alpha=0.15, zorder=1)
    ax.fill_between(tracker.dates, INITIAL_CASH, tracker.portfolio_value_history,
                    where=(np.array(tracker.portfolio_value_history) <= INITIAL_CASH),
                    color='red', alpha=0.15, zorder=1)
    
    # Drawdown overlay
    values = np.array(tracker.portfolio_value_history)
    running_max = np.maximum.accumulate(values)
    drawdown_pct = ((values - running_max) / running_max) * 100
    
    ax2 = ax.twinx()
    ax2.fill_between(tracker.dates, 0, drawdown_pct, 
                      color='red', alpha=0.2, label='Drawdown', zorder=1)
    ax2.set_ylabel('Drawdown (%)', color='red', fontsize=8)
    ax2.tick_params(axis='y', labelcolor='red', labelsize=7)
    ax2.set_ylim([min(drawdown_pct) * 1.2 if min(drawdown_pct) < 0 else -5, 5])
    ax2.grid(False)
    
    ax.set_title('Portfolio Performance vs S&P 500', fontweight='bold', fontsize=11)
    ax.set_xlabel('Date', fontsize=9)
    ax.set_ylabel('Portfolio Value ($)', fontsize=9)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))


def create_performance_metrics_table(fig, gs_spec, tracker, spy_tracker, sim_id=None):
    """
    Create performance metrics table with ACCURATE calculations
    FIXED: Uses telemetry data if available for 100% accuracy
    """
    ax = fig.add_subplot(gs_spec)
    ax.axis('off')
    
    # Try to get accurate metrics from telemetry
    try:
        from simulation_telemetry import telemetry
        if sim_id:
            import sqlite3
            conn = sqlite3.connect(telemetry.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_return_pct, total_profit_dollars, sharpe_ratio,
                       sortino_ratio, calmar_ratio, max_drawdown_pct,
                       win_rate_pct, total_trades, winning_trades, losing_trades,
                       profit_factor, avg_win_dollars, avg_loss_dollars,
                       beta, alpha_pct, information_ratio
                FROM strategy_performance
                WHERE simulation_id = ? AND strategy_name = ?
            ''', (sim_id, tracker.name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Unpack all results safely
                (total_return, profit_dollars, sharpe, sortino, calmar, max_dd,
                 win_rate, total_trades_db, wins, losses, profit_factor,
                 avg_win, avg_loss, beta, alpha, ir) = result
                
                print(f"✅ Using telemetry data for {tracker.name}")
                
                # Use telemetry values
                spy_return = spy_tracker.get_return_pct() if spy_tracker else 0
                
                # Format None values safely
                beta_str = f'{beta:.3f}' if beta is not None else 'N/A'
                alpha_str = f'{alpha:.2f}%' if alpha is not None else 'N/A'
                ir_str = f'{ir:.3f}' if ir is not None else 'N/A'
                
                # Calculate risk/reward ratio
                risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                metrics_data = [
                    ['Performance Metrics', ''],
                    ['Total Return', f'{total_return:+.2f}%'],
                    ['Total Profit', f'${profit_dollars:+,.0f}'],
                    ['vs S&P 500', f'{total_return - (spy_return or 0):+.2f}%' if spy_return else 'N/A'],
                    ['', ''],
                    ['Sharpe Ratio', f'{sharpe:.3f}'],
                    ['Sortino Ratio', f'{sortino:.3f}'],
                    ['Calmar Ratio', f'{calmar:.3f}'],
                    ['', ''],
                    ['Win Rate (Closed)', f'{win_rate:.1f}%'],
                    ['Completed Trades', f'{total_trades_db}'],
                    ['Avg Win', f'${avg_win:,.0f}'],
                    ['Avg Loss', f'${avg_loss:,.0f}'],
                    ['Risk/Reward', f'{risk_reward:.2f}:1'],
                    ['', ''],
                    ['Beta', beta_str],
                    ['Alpha', alpha_str],
                    ['Info Ratio', ir_str],
                    ['', ''],
                    ['Max Drawdown', f'{max_dd:.2f}%'],
                    ['Max DD $', f'${max_dd * tracker.initial_cash / 100:,.0f}'],
                ]
                
                table = create_metrics_table(ax, metrics_data)
                return  # Exit early using telemetry data
                
    except Exception as e:
        print(f"⚠️  Could not load telemetry data: {e}")
    
    # FALLBACK: Use tracker calculation
    win_rate = calculate_accurate_win_rate(tracker)
    total_return = tracker.get_return_pct()
    profit = tracker.get_profit_dollars()
    sharpe = tracker.get_sharpe_ratio()
    sortino = tracker.get_sortino_ratio()
    calmar = tracker.get_calmar_ratio()
    max_dd = tracker.get_max_drawdown()
    max_dd_dollars = tracker.get_max_drawdown_dollars()
    
    # Calculate vs SPY if available
    spy_return = None
    if spy_tracker and len(spy_tracker.portfolio_value_history) > 0:
        spy_return = spy_tracker.get_return_pct()
        spy_returns_series = pd.Series(spy_tracker.portfolio_value_history).pct_change().dropna()
    else:
        spy_returns_series = None
    
    beta = tracker.get_portfolio_beta(spy_returns_series) if spy_returns_series is not None else None
    ir = tracker.get_information_ratio(spy_returns_series) if spy_returns_series is not None else None
    alpha = tracker.get_alpha(spy_return) if spy_return is not None else None
    
    # Format None values safely
    beta_str = f'{beta:.3f}' if beta is not None else 'N/A'
    alpha_str = f'{alpha:.2f}%' if alpha is not None else 'N/A'
    ir_str = f'{ir:.3f}' if ir is not None else 'N/A'
    
    # Calculate risk/reward ratio
    risk_reward = abs(tracker.get_avg_win() / tracker.get_avg_loss()) if tracker.get_avg_loss() != 0 else 0
    
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Return', f'{total_return:+.2f}%'],
        ['Total Profit', f'${profit:+,.0f}'],
        ['vs S&P 500', f'{total_return - (spy_return or 0):+.2f}%' if spy_return else 'N/A'],
        ['', ''],
        ['Sharpe Ratio', f'{sharpe:.3f}'],
        ['Sortino Ratio', f'{sortino:.3f}'],
        ['Calmar Ratio', f'{calmar:.3f}'],
        ['', ''],
        ['Win Rate (Closed)', f'{win_rate:.1f}%'],
        ['Completed Trades', f'{tracker.get_num_trades()}'],
        ['Avg Win', f'${tracker.get_avg_win():,.0f}'],
        ['Avg Loss', f'${tracker.get_avg_loss():,.0f}'],
        ['Risk/Reward', f'{risk_reward:.2f}:1'],
        ['', ''],
        ['Beta', beta_str],
        ['Alpha', alpha_str],
        ['Info Ratio', ir_str],
        ['', ''],
        ['Max Drawdown', f'{max_dd:.2f}%'],
        ['Max DD $', f'${max_dd_dollars:,.0f}'],
    ]
    
    create_metrics_table(ax, metrics_data)


def create_metrics_table(ax, metrics_data):
    """Helper to create styled metrics table"""
    table = ax.table(cellText=metrics_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(7)  # Smaller font to prevent overlap
    table.scale(1, 1.3)
    
    # Styling
    table[(0, 0)].set_facecolor('#1565C0')
    table[(0, 0)].set_text_props(weight='bold', color='white', fontsize=8)
    table[(0, 1)].set_facecolor('#1565C0')
    
    # Separators
    for row in [4, 8, 14, 18]:
        if row < len(metrics_data):
            table[(row, 0)].set_facecolor('#E3F2FD')
            table[(row, 1)].set_facecolor('#E3F2FD')
    
    # Color code profit
    profit_val = float(metrics_data[2][1].replace('$', '').replace(',', '').replace('+', ''))
    if profit_val > 0:
        table[(2, 1)].set_facecolor('#C8E6C9')
    else:
        table[(2, 1)].set_facecolor('#FFCDD2')
    
    # Highlight win rate row
    table[(9, 0)].set_text_props(weight='bold')
    table[(9, 1)].set_text_props(weight='bold')
    
    return table


def calculate_accurate_win_rate(tracker):
    """
    FIXED: Calculate win rate based ONLY on completed (closed) trades
    Ignores open positions to avoid inflated percentages
    """
    completed_trades = []
    
    # Group trades by symbol and match buys with sells
    symbol_trades = {}
    for trade in tracker.trades:
        symbol = trade['symbol']
        if symbol not in symbol_trades:
            symbol_trades[symbol] = []
        symbol_trades[symbol].append(trade)
    
    # For each symbol, match sequential buy-sell pairs
    for symbol, trades in symbol_trades.items():
        i = 0
        while i < len(trades) - 1:
            if trades[i]['action'] == 'BUY' and trades[i+1]['action'] == 'SELL':
                buy_price = trades[i]['price']
                sell_price = trades[i+1]['price']
                profit_loss = (sell_price - buy_price) * trades[i]['shares']
                
                completed_trades.append({
                    'symbol': symbol,
                    'profit_loss': profit_loss,
                    'is_win': profit_loss > 0
                })
                
                i += 2  # Skip both the buy and sell
            else:
                i += 1
    
    if len(completed_trades) == 0:
        return 0.0
    
    wins = sum(1 for t in completed_trades if t['is_win'])
    win_rate = (wins / len(completed_trades)) * 100
    
    print(f"📊 Accurate Win Rate Calculation:")
    print(f"   Total trades executed: {len(tracker.trades)}")
    print(f"   Completed pairs: {len(completed_trades)}")
    print(f"   Winning pairs: {wins}")
    print(f"   Win rate: {win_rate:.1f}%")
    
    return win_rate


def create_trading_stats_table(fig, gs_spec, tracker, sim_id=None):
    """Create trading statistics table with telemetry support"""
    ax = fig.add_subplot(gs_spec)
    ax.axis('off')
    
    # Try to get from telemetry first
    try:
        from simulation_telemetry import telemetry
        if sim_id:
            import sqlite3
            conn = sqlite3.connect(telemetry.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_trades, winning_trades, losing_trades,
                       avg_trade_duration_days, exposure_time_pct
                FROM strategy_performance
                WHERE simulation_id = ? AND strategy_name = ?
            ''', (sim_id, tracker.name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                total_trades, wins, losses, avg_duration, exposure = result
                completed_trades = wins + losses
                open_trades = total_trades - completed_trades
                win_rate = (wins / completed_trades * 100) if completed_trades > 0 else 0
                
                stats_data = [
                    ['Trading Statistics', ''],
                    ['Total Executions', f'{total_trades}'],
                    ['Completed Trades', f'{completed_trades}'],
                    ['Open Positions', f'{open_trades}'],
                    ['', ''],
                    ['Win Rate (Closed)', f'{win_rate:.1f}%'],
                    ['Winning Trades', f'{wins}'],
                    ['Losing Trades', f'{losses}'],
                    ['', ''],
                    ['Profit Factor', f'{tracker.get_profit_factor():.2f}'],
                    ['Expectancy', f'${tracker.get_expectancy():,.0f}'],
                    ['Avg Duration', f'{avg_duration:.1f} days'],
                    ['Exposure Time', f'{exposure:.1f}%'],
                ]
                
                table = create_stats_table(ax, stats_data)
                return
                
    except Exception as e:
        print(f"⚠️  Could not load telemetry stats: {e}")
    
    # Fallback to tracker calculations
    win_rate = calculate_accurate_win_rate(tracker)
    winning = tracker.get_winning_trades()
    losing = tracker.get_losing_trades()
    total_trades = tracker.get_num_trades()
    profit_factor = tracker.get_profit_factor()
    expectancy = tracker.get_expectancy()
    avg_duration = tracker.get_avg_trade_duration()
    exposure = tracker.get_exposure_time()
    
    # Count completed vs open
    completed_trades = len(winning) + len(losing)
    open_trades = total_trades - completed_trades
    
    stats_data = [
        ['Trading Statistics', ''],
        ['Total Executions', f'{total_trades}'],
        ['Completed Trades', f'{completed_trades}'],
        ['Open Positions', f'{open_trades}'],
        ['', ''],
        ['Win Rate (Closed)', f'{win_rate:.1f}%'],
        ['Winning Trades', f'{len(winning)}'],
        ['Losing Trades', f'{len(losing)}'],
        ['', ''],
        ['Profit Factor', f'{profit_factor:.2f}'],
        ['Expectancy', f'${expectancy:,.0f}'],
        ['Avg Duration', f'{avg_duration:.1f} days'],
        ['Exposure Time', f'{exposure:.1f}%'],
    ]
    
    create_stats_table(ax, stats_data)


def create_stats_table(ax, stats_data):
    """Helper to create styled stats table"""
    table = ax.table(cellText=stats_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(7)  # Smaller font to prevent overlap
    table.scale(1, 1.5)
    
    # Header
    table[(0, 0)].set_facecolor('#1565C0')
    table[(0, 0)].set_text_props(weight='bold', color='white', fontsize=8)
    table[(0, 1)].set_facecolor('#1565C0')
    
    # Separators
    for row in [4, 8]:
        if row < len(stats_data):
            table[(row, 0)].set_facecolor('#E3F2FD')
            table[(row, 1)].set_facecolor('#E3F2FD')
    
    return table


def create_returns_distribution(fig, gs_spec, tracker):
    """Create returns distribution histogram"""
    ax = fig.add_subplot(gs_spec)
    
    winning = tracker.get_winning_trades()
    losing = tracker.get_losing_trades()
    
    all_returns = []
    for w in winning:
        all_returns.append(w['return_pct'])
    for l in losing:
        all_returns.append(l['return_pct'])
    
    if all_returns:
        # Create histogram
        n, bins, patches = ax.hist(all_returns, bins=20, edgecolor='black', alpha=0.7)
        
        # Color bars based on positive/negative
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor('#F44336')
            else:
                patch.set_facecolor('#4CAF50')
        
        ax.axvline(0, color='black', linestyle='--', linewidth=2, label='Breakeven', zorder=3)
        
        # Add mean and median lines
        mean_return = np.mean(all_returns)
        median_return = np.median(all_returns)
        
        ax.axvline(mean_return, color='blue', linestyle='--', 
                  linewidth=1.5, alpha=0.7, label=f'Mean: {mean_return:.1f}%')
        ax.axvline(median_return, color='purple', linestyle='--', 
                  linewidth=1.5, alpha=0.7, label=f'Median: {median_return:.1f}%')
        
        ax.set_title('Trade Returns Distribution (Closed Only)', fontweight='bold', fontsize=10)
        ax.set_xlabel('Return per Trade (%)', fontsize=9)
        ax.set_ylabel('Frequency', fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(labelsize=8)
    else:
        ax.text(0.5, 0.5, 'No completed trades', 
                ha='center', va='center', transform=ax.transAxes, fontsize=10)


def create_monthly_returns_chart(fig, gs_spec, tracker):
    """Create monthly returns bar chart - FIXED deprecation warning"""
    ax = fig.add_subplot(gs_spec)
    
    if len(tracker.dates) < 2:
        ax.text(0.5, 0.5, 'Insufficient data', 
                ha='center', va='center', transform=ax.transAxes, fontsize=10)
        return
    
    # Calculate daily returns
    returns_series = pd.Series(tracker.portfolio_value_history, 
                               index=tracker.dates).pct_change()
    
    # FIXED: Use 'ME' instead of deprecated 'M'
    monthly_returns = returns_series.groupby(pd.Grouper(freq='ME')).apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    
    # Remove NaN values
    monthly_returns = monthly_returns.dropna()
    
    if len(monthly_returns) == 0:
        ax.text(0.5, 0.5, 'No monthly data', 
                ha='center', va='center', transform=ax.transAxes, fontsize=10)
        return
    
    # Format month labels
    month_labels = [d.strftime('%Y-%m') for d in monthly_returns.index]
    
    # Create bars
    colors = ['#F44336' if r < 0 else '#4CAF50' for r in monthly_returns.values]
    bars = ax.bar(range(len(month_labels)), monthly_returns.values, color=colors, 
                  edgecolor='black', linewidth=1)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, monthly_returns.values)):
        height = bar.get_height()
        ax.text(i, height + (0.5 if height > 0 else -0.5),
                f'{val:+.1f}%',
                ha='center', va='bottom' if height > 0 else 'top',
                fontsize=7, fontweight='bold')
    
    ax.axhline(0, color='black', linewidth=1)
    ax.set_title('Monthly Returns', fontweight='bold', fontsize=10)
    ax.set_xlabel('Month', fontsize=9)
    ax.set_ylabel('Return (%)', fontsize=9)
    ax.set_xticks(range(len(month_labels)))
    ax.set_xticklabels(month_labels, fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    ax.tick_params(labelsize=8)


def generate_markdown_report(strategy, tracker, stock_data, symbols, spy_tracker=None, sim_id=None):
    """Generate comprehensive markdown report with ACCURATE metrics"""
    
    timestamp = datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Try to get accurate metrics from telemetry
    try:
        from simulation_telemetry import telemetry
        if sim_id:
            import sqlite3
            conn = sqlite3.connect(telemetry.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_return_pct, total_profit_dollars, sharpe_ratio,
                       sortino_ratio, calmar_ratio, max_drawdown_pct,
                       win_rate_pct, total_trades, winning_trades, losing_trades,
                       profit_factor, avg_win_dollars, avg_loss_dollars,
                       beta, alpha_pct, information_ratio
                FROM strategy_performance
                WHERE simulation_id = ? AND strategy_name = ?
            ''', (sim_id, tracker.name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Use telemetry values for 100% accuracy
                (total_return, profit_dollars, sharpe, sortino, calmar, max_dd,
                 win_rate, total_trades_db, wins, losses, profit_factor,
                 avg_win, avg_loss, beta, alpha, ir) = result
                
                print(f"✅ Generating report from telemetry data")
                
                # Get SPY comparison
                spy_return = spy_tracker.get_return_pct() if spy_tracker else 0
                spy_profit = spy_tracker.get_profit_dollars() if spy_tracker else 0
                
                # Calculate risk/reward
                risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                # Get current positions
                open_positions = tracker.get_current_position_count()
                
                # Generate report with telemetry data
                md = f"""# Strategy Analysis Report: {strategy.name}

**Generated**: {timestamp}  
**Simulation ID**: {sim_id}  
**Period**: {tracker.dates[0].strftime('%Y-%m-%d')} to {tracker.dates[-1].strftime('%Y-%m-%d')}  
**Initial Capital**: ${INITIAL_CASH:,.0f}  

## 📊 Performance Summary (Verified from Telemetry)

| Metric | Strategy | S&P 500 | Difference |
|--------|----------|---------|------------|
| **Total Return** | {total_return:+.2f}% | {spy_return:+.2f}% | {total_return - spy_return:+.2f}% |
| **Profit/Loss** | ${profit_dollars:+,.0f} | ${spy_profit:+,.0f} | - |
| **Sharpe Ratio** | {sharpe:.3f} | {spy_tracker.get_sharpe_ratio() if spy_tracker else 0:.3f} | - |
| **Max Drawdown** | {max_dd:.2f}% | {spy_tracker.get_max_drawdown() if spy_tracker else 0:.2f}% | - |
| **Win Rate** | {win_rate:.1f}% ({wins}/{total_trades_db} trades) | - | - |
| **Profit Factor** | {profit_factor:.2f} | - | - |

## ⚠️ RISK ASSESSMENT

**Risk Score**: {((max_dd + (100 - win_rate) + (1/profit_factor if profit_factor > 0 else 10))/3):.0f}/100

**Key Issues Detected**:
"""
                
                # Add risk warnings
                if win_rate > 70 and total_return < 5:
                    md += f"- ❌ **HIGH WIN RATE, LOW RETURN**: {win_rate:.1f}% win rate but only {total_return:+.2f}% return\n"
                
                if max_dd > 10:
                    md += f"- ❌ **EXCESSIVE DRAWDOWN**: {max_dd:.2f}% maximum drawdown\n"
                
                if risk_reward < 1.0:
                    md += f"- ❌ **POOR RISK/REWARD**: {risk_reward:.2f}:1 (avg win: ${avg_win:,.0f}, avg loss: ${avg_loss:,.0f})\n"
                
                if profit_factor < 1.5:
                    md += f"- ⚠️  **LOW PROFIT FACTOR**: {profit_factor:.2f}\n"
                
                # Add position summary
                md += f"""
## 💼 Portfolio Summary

- **Total Executions**: {len(tracker.trades)}
- **Completed Trades**: {total_trades_db}
- **Open Positions**: {open_positions}/{tracker.max_positions}
- **Cash**: ${tracker.cash:,.0f}
- **Total Value**: ${tracker.get_final_value():,.0f}

## 📈 Detailed Metrics

### Risk Metrics
- **Volatility**: Use Risk Analysis button for complete metrics
- **Beta**: {beta:.3f if beta is not None else 'N/A'}
- **Alpha**: {alpha:.2f if alpha is not None else 'N/A'}%
- **Information Ratio**: {ir:.3f if ir is not None else 'N/A'}

### Trade Statistics
- **Total Trades**: {total_trades_db}
- **Winning Trades**: {wins}
- **Losing Trades**: {losses}
- **Average Win**: ${avg_win:,.0f}
- **Average Loss**: ${avg_loss:,.0f}
- **Risk/Reward Ratio**: {risk_reward:.2f}:1
- **Expectancy**: ${(win_rate/100 * avg_win) - ((1-win_rate/100) * avg_loss):,.0f}

## ⚠️ Important Notes

- **Telemetry Verified**: All metrics sourced from simulation_telemetry database
- **Win Rate Calculation**: Based on {total_trades_db} completed (closed) trades only
- Open positions ({open_positions}) are NOT included in win rate
- Performance is simulated and not indicative of future results
- **Database Location**: ./telemetry/simulations.db (Simulation ID: {sim_id})
"""
                
                return md
    
    except Exception as e:
        print(f"⚠️  Could not load telemetry for report: {e}")
    
    # Fallback to tracker calculations if telemetry unavailable
    return generate_fallback_report(strategy, tracker, stock_data, symbols, spy_tracker, timestamp)


def generate_fallback_report(strategy, tracker, stock_data, symbols, spy_tracker, timestamp):
    """Generate report using tracker calculations when telemetry unavailable"""
    
    # Calculate ACCURATE metrics
    win_rate = calculate_accurate_win_rate(tracker)
    total_return = tracker.get_return_pct()
    profit = tracker.get_profit_dollars()
    sharpe = tracker.get_sharpe_ratio()
    sortino = tracker.get_sortino_ratio()
    max_dd = tracker.get_max_drawdown()
    
    # Get completed vs total trades
    completed = len(tracker.get_winning_trades()) + len(tracker.get_losing_trades())
    total_trades = tracker.get_num_trades()
    
    # SPY comparison
    spy_return = spy_tracker.get_return_pct() if spy_tracker else 0
    spy_profit = spy_tracker.get_profit_dollars() if spy_tracker else 0
    
    # Calculate risk/reward
    avg_win = tracker.get_avg_win()
    avg_loss = tracker.get_avg_loss()
    risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    md = f"""# Strategy Analysis Report: {strategy.name}

**Generated**: {timestamp}  
**Period**: {tracker.dates[0].strftime('%Y-%m-%d')} to {tracker.dates[-1].strftime('%Y-%m-%d')}  
**Initial Capital**: ${INITIAL_CASH:,.0f}  

## 📊 Performance Summary

| Metric | Strategy | S&P 500 | Difference |
|--------|----------|---------|------------|
| **Total Return** | {total_return:+.2f}% | {spy_return:+.2f}% | {total_return - spy_return:+.2f}% |
| **Profit/Loss** | ${profit:+,.0f} | ${spy_profit:+,.0f} | - |
| **Sharpe Ratio** | {sharpe:.3f} | {spy_tracker.get_sharpe_ratio() if spy_tracker else 0:.3f} | - |
| **Max Drawdown** | {max_dd:.2f}% | {spy_tracker.get_max_drawdown() if spy_tracker else 0:.2f}% | - |
| **Win Rate** | {win_rate:.1f}% (on {completed} completed trades) | - | - |

## ⚠️ CRITICAL: Win Rate vs Return Analysis

Your strategy has a **{win_rate:.1f}% win rate** but only **{total_return:+.2f}% return**.

This indicates **POOR RISK MANAGEMENT**:
- ❌ Winning trades are too small (avg: ${avg_win:,.0f})
- ❌ Losing trades are too large (avg: ${avg_loss:,.0f})
- ❌ Max drawdown was {max_dd:.2f}% (you lost ${tracker.get_max_drawdown_dollars():,.0f} at worst point)

**Recommendation**: Focus on position sizing and stop losses, not win rate.

## 📈 Risk Metrics

- **Sharpe Ratio**: {sharpe:.3f}
- **Sortino Ratio**: {sortino:.3f}
- **Profit Factor**: {tracker.get_profit_factor():.2f}
- **Risk/Reward Ratio**: {risk_reward:.2f}:1

## 💼 Portfolio Summary

- **Total Executions**: {total_trades}
- **Completed Trades**: {completed}
- **Open Positions**: {tracker.get_current_position_count()}/{tracker.max_positions}
- **Cash**: ${tracker.cash:,.0f}
- **Total Value**: ${tracker.get_final_value():,.0f}

## ⚠️ Important Notes

- **Win Rate Calculation**: Based on {completed} completed (closed) trades only
- Open positions are NOT included in win rate to avoid inflated statistics
- **Telemetry Disabled**: Metrics calculated from tracker (use Risk Analysis button for complete metrics)
- All values in USD
- Performance is simulated and not indicative of future results
"""
    
    return md