"""
Strategy Analysis Module
Displays detailed institutional-grade analysis windows for strategies
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from strategy_tracker import INITIAL_CASH

def show_strategy_analysis(strategy, tracker, stock_data, symbols):
    """Show detailed analysis window for a strategy with institutional-grade metrics"""
    
    # Create new window with more space
    analysis_fig = plt.figure(figsize=(18, 12))
    analysis_fig.suptitle(f'{strategy.name} - Institutional Analysis Dashboard', 
                         fontsize=18, fontweight='bold')
    
    # Create grid: 4 rows, 4 columns
    gs = analysis_fig.add_gridspec(4, 4, hspace=0.4, wspace=0.4)
    
    # 1. Portfolio value over time (top, spans 3 cols)
    ax1 = analysis_fig.add_subplot(gs[0, :3])
    ax1.plot(tracker.dates, tracker.portfolio_value_history, color=strategy.color, 
             linewidth=2.5, label='Portfolio Value')
    ax1.axhline(INITIAL_CASH, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.fill_between(tracker.dates, INITIAL_CASH, tracker.portfolio_value_history, 
                     where=(np.array(tracker.portfolio_value_history) > INITIAL_CASH),
                     color='green', alpha=0.2)
    ax1.fill_between(tracker.dates, INITIAL_CASH, tracker.portfolio_value_history,
                     where=(np.array(tracker.portfolio_value_history) <= INITIAL_CASH),
                     color='red', alpha=0.2)
    
    # Add drawdown overlay
    values = np.array(tracker.portfolio_value_history)
    running_max = np.maximum.accumulate(values)
    drawdown_pct = ((values - running_max) / running_max) * 100
    
    ax1_dd = ax1.twinx()
    ax1_dd.fill_between(tracker.dates, 0, drawdown_pct, color='red', alpha=0.2, label='Drawdown')
    ax1_dd.set_ylabel('Drawdown (%)', color='red')
    ax1_dd.tick_params(axis='y', labelcolor='red')
    ax1_dd.set_ylim([min(drawdown_pct) * 1.2, 5])
    
    ax1.set_title('Portfolio Equity Curve with Drawdown', fontweight='bold', fontsize=12)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 2. Performance Metrics Table (top right)
    ax2 = analysis_fig.add_subplot(gs[0, 3])
    ax2.axis('off')
    
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Return', f'{tracker.get_return_pct():.2f}%'],
        ['Total Profit', f'${tracker.get_profit_dollars():+,.0f}'],
        ['CAGR (Annual)', f'{tracker.get_return_pct() * 2:.2f}%'],
        ['', ''],
        ['Sharpe Ratio', f'{tracker.get_sharpe_ratio():.3f}'],
        ['Sortino Ratio', f'{tracker.get_sortino_ratio():.3f}'],
        ['Calmar Ratio', f'{tracker.get_calmar_ratio():.3f}'],
        ['', ''],
        ['Max Drawdown', f'{tracker.get_max_drawdown():.2f}%'],
        ['Avg Drawdown', f'{tracker.get_avg_drawdown():.2f}%'],
        ['Ulcer Index', f'{tracker.get_ulcer_index():.2f}'],
        ['Recovery Factor', f'{tracker.get_recovery_factor():.2f}'],
    ]
    
    table = ax2.table(cellText=metrics_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)
    
    # Styling
    table[(0, 0)].set_facecolor('#1565C0')
    table[(0, 0)].set_text_props(weight='bold', color='white', fontsize=9)
    table[(0, 1)].set_facecolor('#1565C0')
    
    # Separators
    for row in [4, 8]:
        table[(row, 0)].set_facecolor('#E3F2FD')
        table[(row, 1)].set_facecolor('#E3F2FD')
    
    # Color code returns
    profit = tracker.get_profit_dollars()
    if profit > 0:
        table[(2, 1)].set_facecolor('#C8E6C9')
    else:
        table[(2, 1)].set_facecolor('#FFCDD2')
    
    # 3. Trading Statistics Table (second row, left)
    ax3 = analysis_fig.add_subplot(gs[1, :2])
    ax3.axis('off')
    
    win_rate = tracker.get_win_rate()
    winning_trades = tracker.get_winning_trades()
    losing_trades = tracker.get_losing_trades()
    
    trade_stats = [
        ['Trading Statistics', '', 'Win/Loss Analysis', ''],
        ['Total Trades', f'{tracker.get_num_trades()}', 'Win Rate', f'{win_rate:.1f}%'],
        ['Winning Trades', f'{len(winning_trades)}', 'Avg Win', f'${tracker.get_avg_win():,.0f}'],
        ['Losing Trades', f'{len(losing_trades)}', 'Avg Loss', f'${tracker.get_avg_loss():,.0f}'],
        ['', '', 'Largest Win', f'${tracker.get_largest_win():,.0f}'],
        ['Profit Factor', f'{tracker.get_profit_factor():.2f}', 'Largest Loss', f'${tracker.get_largest_loss():,.0f}'],
        ['Payoff Ratio', f'{tracker.get_payoff_ratio():.2f}', 'Expectancy', f'${tracker.get_expectancy():,.0f}'],
        ['Avg Duration', f'{tracker.get_avg_trade_duration():.1f} days', '', ''],
        ['', '', 'Max Consecutive Wins', f'{tracker.get_consecutive_wins()}'],
        ['Exposure Time', f'{tracker.get_exposure_time():.1f}%', 'Max Consecutive Losses', f'{tracker.get_consecutive_losses()}'],
    ]
    
    table2 = ax3.table(cellText=trade_stats, cellLoc='left',
                      loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
    table2.auto_set_font_size(False)
    table2.set_fontsize(8)
    table2.scale(1, 2)
    
    # Header styling
    for i in range(4):
        table2[(0, i)].set_facecolor('#1565C0')
        table2[(0, i)].set_text_props(weight='bold', color='white', fontsize=9)
    
    # 4. Position Analysis (second row, right 2 cols)
    ax4 = analysis_fig.add_subplot(gs[1, 2:])
    ax4.axis('off')
    
    position_data = [['Current Positions', 'Shares', 'Value', 'P&L']]
    total_position_value = 0
    
    for symbol in symbols:
        shares = tracker.positions.get(symbol, 0)
        if shares > 0:
            current_price = stock_data[symbol]['close'].iloc[-1]
            position_value = shares * current_price
            total_position_value += position_value
            
            # Calculate P&L for this position
            symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol and t['action'] == 'BUY']
            avg_buy_price = sum(t['price'] * t['shares'] for t in symbol_trades) / sum(t['shares'] for t in symbol_trades) if symbol_trades else current_price
            pl = (current_price - avg_buy_price) * shares
            pl_pct = (current_price - avg_buy_price) / avg_buy_price * 100 if avg_buy_price > 0 else 0
            
            position_data.append([
                symbol,
                f'{shares:.2f}',
                f'${position_value:,.0f}',
                f'${pl:+,.0f} ({pl_pct:+.1f}%)'
            ])
    
    position_data.append(['', '', '', ''])
    position_data.append(['Cash', '-', f'${tracker.cash:,.0f}', '-'])
    position_data.append(['Total Portfolio', '-', f'${tracker.get_final_value():,.0f}', '-'])
    
    table3 = ax4.table(cellText=position_data, cellLoc='left',
                      loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
    table3.auto_set_font_size(False)
    table3.set_fontsize(8)
    table3.scale(1, 2)
    
    # Header
    for i in range(4):
        table3[(0, i)].set_facecolor('#1565C0')
        table3[(0, i)].set_text_props(weight='bold', color='white', fontsize=9)
    
    # 5. Per-stock performance (third row, left 2 cols)
    ax5 = analysis_fig.add_subplot(gs[2, :2])
    stock_returns = {}
    for symbol in symbols:
        stock_trades = [t for t in tracker.trades if t['symbol'] == symbol]
        if stock_trades:
            buys = [t for t in stock_trades if t['action'] == 'BUY']
            sells = [t for t in stock_trades if t['action'] == 'SELL']
            
            total_invested = sum(t['shares'] * t['price'] for t in buys)
            total_returned = sum(t.get('proceeds', 0) for t in sells)
            
            if tracker.positions.get(symbol, 0) > 0:
                final_price = stock_data[symbol]['close'].iloc[-1]
                total_returned += tracker.positions[symbol] * final_price
            
            stock_returns[symbol] = total_returned - total_invested if total_invested > 0 else 0
    
    if stock_returns:
        colors = ['#4CAF50' if v > 0 else '#F44336' for v in stock_returns.values()]
        bars = ax5.bar(stock_returns.keys(), stock_returns.values(), color=colors, 
                      edgecolor='black', linewidth=1.5)
        ax5.set_title('Profit/Loss by Stock', fontweight='bold', fontsize=11)
        ax5.set_ylabel('$ Profit/Loss')
        ax5.axhline(0, color='black', linewidth=2)
        ax5.grid(True, alpha=0.3, axis='y')
        
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:,.0f}',
                    ha='center', va='bottom' if height > 0 else 'top', 
                    fontsize=9, fontweight='bold')
    
    # 6. Returns distribution histogram (third row, right 2 cols)
    ax6 = analysis_fig.add_subplot(gs[2, 2:])
    all_returns = []
    for w in winning_trades:
        all_returns.append(w['return_pct'])
    for l in losing_trades:
        all_returns.append(l['return_pct'])
    
    if all_returns:
        ax6.hist(all_returns, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
        ax6.axvline(0, color='red', linestyle='--', linewidth=2, label='Breakeven')
        ax6.set_title('Trade Returns Distribution', fontweight='bold', fontsize=11)
        ax6.set_xlabel('Return per Trade (%)')
        ax6.set_ylabel('Frequency')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
    
    # 7. Trade timeline (bottom, spans all columns)
    ax7 = analysis_fig.add_subplot(gs[3, :])
    for symbol in symbols:
        symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol]
        buys = [(t['date'], t['price']) for t in symbol_trades if t['action'] == 'BUY']
        sells = [(t['date'], t['price']) for t in symbol_trades if t['action'] == 'SELL']
        
        if buys:
            dates, prices = zip(*buys)
            ax7.scatter(dates, prices, marker='o', s=100, label=f'{symbol} BUY', alpha=0.7)
        if sells:
            dates, prices = zip(*sells)
            ax7.scatter(dates, prices, marker='x', s=100, linewidths=2.5, label=f'{symbol} SELL', alpha=0.7)
    
    ax7.set_title('Trade Execution Timeline - All Stocks', fontweight='bold', fontsize=11)
    ax7.set_xlabel('Date')
    ax7.set_ylabel('Execution Price ($)')
    ax7.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=8, ncol=2)
    ax7.grid(True, alpha=0.3)
    ax7.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # Adjust layout to prevent overlap
    plt.subplots_adjust(right=0.88)
    plt.show()