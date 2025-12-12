"""
Strategy Analysis Module with Scrollable Interface
Displays detailed institutional-grade analysis windows for strategies
with markdown export capability and scrollable layout
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import filedialog
import pandas as pd
from datetime import datetime
import pytz
import pyperclip  # For clipboard functionality
import os
import sys
from strategy_tracker import INITIAL_CASH

def show_strategy_analysis(strategy, tracker, stock_data, symbols):
    """Show detailed analysis window for a strategy with scrollable interface"""
    
    # Create Tkinter window for scrollable interface
    root = tk.Tk()
    root.title(f"{strategy.name} - Institutional Analysis Dashboard")
    root.geometry("1600x1000")
    
    # Create main frame
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create canvas and scrollbar
    canvas = tk.Canvas(main_frame)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    # Configure scroll region
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Pack everything
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Bind mouse wheel for scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # Create matplotlib figure inside scrollable frame
    fig_width = 18
    fig_height = 25  # Much taller for all content
    
    fig = plt.figure(figsize=(fig_width, fig_height))
    fig.suptitle(f'{strategy.name} - Institutional Analysis Dashboard', 
                 fontsize=18, fontweight='bold')
    
    # Create grid: 8 rows, 4 columns for more space
    gs = fig.add_gridspec(8, 4, hspace=0.6, wspace=0.4, top=0.97, bottom=0.02)
    
    # ============================================================
    # 1. Portfolio value over time (row 0, spans 3 cols)
    # ============================================================
    ax1 = fig.add_subplot(gs[0, :3])
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
    
    # ============================================================
    # 2. Performance Metrics Table (row 0, col 3)
    # ============================================================
    ax2 = fig.add_subplot(gs[0, 3])
    ax2.axis('off')
    
    # Calculate metrics
    total_return_pct = tracker.get_return_pct()
    total_profit = tracker.get_profit_dollars()
    sharpe = tracker.get_sharpe_ratio()
    sortino = tracker.get_sortino_ratio()
    calmar = tracker.get_calmar_ratio()
    max_dd = tracker.get_max_drawdown()
    avg_dd = tracker.get_avg_drawdown()
    ulcer = tracker.get_ulcer_index()
    recovery = tracker.get_recovery_factor()
    
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Return', f'{total_return_pct:.2f}%'],
        ['Total Profit', f'${total_profit:+,.0f}'],
        ['CAGR (Annual)', f'{total_return_pct * 2:.2f}%'],
        ['', ''],
        ['Sharpe Ratio', f'{sharpe:.3f}'],
        ['Sortino Ratio', f'{sortino:.3f}'],
        ['Calmar Ratio', f'{calmar:.3f}'],
        ['', ''],
        ['Max Drawdown', f'{max_dd:.2f}%'],
        ['Avg Drawdown', f'{avg_dd:.2f}%'],
        ['Ulcer Index', f'{ulcer:.2f}'],
        ['Recovery Factor', f'{recovery:.2f}'],
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
    if total_profit > 0:
        table[(2, 1)].set_facecolor('#C8E6C9')
    else:
        table[(2, 1)].set_facecolor('#FFCDD2')
    
    # ============================================================
    # 3. Trading Statistics Table (row 1, cols 0-1)
    # ============================================================
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.axis('off')
    
    # Calculate trading stats
    win_rate = tracker.get_win_rate()
    winning_trades = tracker.get_winning_trades()
    losing_trades = tracker.get_losing_trades()
    total_trades = tracker.get_num_trades()
    profit_factor = tracker.get_profit_factor()
    payoff_ratio = tracker.get_payoff_ratio()
    expectancy = tracker.get_expectancy()
    avg_duration = tracker.get_avg_trade_duration()
    exposure_time = tracker.get_exposure_time()
    avg_win = tracker.get_avg_win()
    avg_loss = tracker.get_avg_loss()
    largest_win = tracker.get_largest_win()
    largest_loss = tracker.get_largest_loss()
    cons_wins = tracker.get_consecutive_wins()
    cons_losses = tracker.get_consecutive_losses()
    
    trade_stats = [
        ['Trading Statistics', '', 'Win/Loss Analysis', ''],
        ['Total Trades', f'{total_trades}', 'Win Rate', f'{win_rate:.1f}%'],
        ['Winning Trades', f'{len(winning_trades)}', 'Avg Win', f'${avg_win:,.0f}'],
        ['Losing Trades', f'{len(losing_trades)}', 'Avg Loss', f'${avg_loss:,.0f}'],
        ['', '', 'Largest Win', f'${largest_win:,.0f}'],
        ['Profit Factor', f'{profit_factor:.2f}', 'Largest Loss', f'${largest_loss:,.0f}'],
        ['Payoff Ratio', f'{payoff_ratio:.2f}', 'Expectancy', f'${expectancy:,.0f}'],
        ['Avg Duration', f'{avg_duration:.1f} days', '', ''],
        ['', '', 'Max Consecutive Wins', f'{cons_wins}'],
        ['Exposure Time', f'{exposure_time:.1f}%', 'Max Consecutive Losses', f'{cons_losses}'],
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
    
    # ============================================================
    # 4. Position Analysis (row 1, cols 2-3)
    # ============================================================
    ax4 = fig.add_subplot(gs[1, 2:])
    ax4.axis('off')
    
    position_data = [['Current Positions', 'Shares', 'Value', 'P&L']]
    position_details = []  # Store for markdown report
    
    for symbol in symbols:
        shares = tracker.positions.get(symbol, 0)
        if shares > 0:
            current_price = stock_data[symbol]['close'].iloc[-1]
            position_value = shares * current_price
            
            # Calculate P&L for this position
            symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol and t['action'] == 'BUY']
            if symbol_trades:
                total_shares = sum(t['shares'] for t in symbol_trades)
                total_cost = sum(t['price'] * t['shares'] for t in symbol_trades)
                avg_buy_price = total_cost / total_shares
            else:
                avg_buy_price = current_price
            
            pl = (current_price - avg_buy_price) * shares
            pl_pct = (current_price - avg_buy_price) / avg_buy_price * 100 if avg_buy_price > 0 else 0
            
            position_data.append([
                symbol,
                f'{shares:.2f}',
                f'${position_value:,.0f}',
                f'${pl:+,.0f} ({pl_pct:+.1f}%)'
            ])
            
            # Store for markdown
            position_details.append({
                'symbol': symbol,
                'shares': shares,
                'price': current_price,
                'value': position_value,
                'avg_buy': avg_buy_price,
                'pl': pl,
                'pl_pct': pl_pct
            })
    
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
    
    # ============================================================
    # 5. Per-stock performance (row 2, cols 0-1)
    # ============================================================
    ax5 = fig.add_subplot(gs[2, :2])
    stock_returns = {}
    stock_performance = []  # Store for markdown
    
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
            
            profit_loss = total_returned - total_invested if total_invested > 0 else 0
            stock_returns[symbol] = profit_loss
            
            stock_performance.append({
                'symbol': symbol,
                'profit_loss': profit_loss,
                'num_trades': len(stock_trades)
            })
    
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
    
    # ============================================================
    # 6. Returns distribution histogram (row 2, cols 2-3)
    # ============================================================
    ax6 = fig.add_subplot(gs[2, 2:])
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
    
    # ============================================================
    # 7. Trade timeline (row 3, spans all columns)
    # ============================================================
    ax7 = fig.add_subplot(gs[3, :])
    trade_events = []  # Store for markdown
    
    for symbol in symbols:
        symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol]
        buys = [(t['date'], t['price']) for t in symbol_trades if t['action'] == 'BUY']
        sells = [(t['date'], t['price']) for t in symbol_trades if t['action'] == 'SELL']
        
        # Store trade events for markdown
        for trade in symbol_trades:
            trade_events.append({
                'date': trade['date'],
                'symbol': symbol,
                'action': trade['action'],
                'price': trade['price'],
                'shares': trade['shares']
            })
        
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
    
    # ============================================================
    # 8. Monthly Returns Heatmap (row 4-5, spans all columns)
    # ============================================================
    if len(tracker.dates) > 0:
        ax8 = fig.add_subplot(gs[4:6, :])
        
        # Convert dates to monthly returns
        monthly_returns = {}
        for i in range(1, len(tracker.portfolio_value_history)):
            current_val = tracker.portfolio_value_history[i]
            prev_val = tracker.portfolio_value_history[i-1]
            current_date = tracker.dates[i]
            
            month_key = current_date.strftime('%Y-%m')
            daily_return = (current_val - prev_val) / prev_val * 100
            
            if month_key not in monthly_returns:
                monthly_returns[month_key] = []
            monthly_returns[month_key].append(daily_return)
        
        # Calculate average monthly returns
        months = sorted(monthly_returns.keys())
        avg_returns = [sum(monthly_returns[m])/len(monthly_returns[m]) for m in months]
        
        # Create heatmap-like bar chart
        colors = ['#F44336' if r < 0 else '#4CAF50' for r in avg_returns]
        bars = ax8.bar(months, avg_returns, color=colors, edgecolor='black')
        ax8.set_title('Average Monthly Returns (%)', fontweight='bold', fontsize=11)
        ax8.set_xlabel('Month')
        ax8.set_ylabel('Avg Daily Return (%)')
        ax8.grid(True, alpha=0.3, axis='y')
        ax8.axhline(0, color='black', linewidth=1)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax8.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:+.1f}%',
                    ha='center', va='bottom' if height > 0 else 'top', 
                    fontsize=8, fontweight='bold')
        
        plt.setp(ax8.get_xticklabels(), rotation=45, ha='right')
    
    # ============================================================
    # 9. Trade List (last 2 rows, spans all columns)
    # ============================================================
    ax9 = fig.add_subplot(gs[6:, :])
    ax9.axis('off')
    
    # Prepare trade list table
    trade_list_data = [['Date', 'Symbol', 'Action', 'Price', 'Shares', 'Amount', 'Return %']]
    
    # Sort trades by date (most recent first)
    sorted_trades = sorted(trade_events, key=lambda x: x['date'], reverse=True)
    
    # Take top 30 trades for display
    for trade in sorted_trades[:30]:
        amount = trade['price'] * trade['shares']
        
        # Find if there's a return percentage for this trade
        return_pct = 'N/A'
        for t in tracker.trades:
            if (t['date'] == trade['date'] and t['symbol'] == trade['symbol'] and 
                t['action'] == trade['action'] and abs(t['price'] - trade['price']) < 0.01):
                if 'return_pct' in t:
                    return_pct = f"{t['return_pct']:+.1f}%"
                break
        
        trade_list_data.append([
            trade['date'].strftime('%m-%d'),
            trade['symbol'],
            trade['action'],
            f"${trade['price']:.2f}",
            f"{trade['shares']:.2f}",
            f"${amount:,.0f}",
            return_pct
        ])
    
    # Add a summary row
    trade_list_data.append([''] * 7)
    trade_list_data.append([
        f'Total Trades: {len(sorted_trades)}',
        '',
        f'Wins: {len(winning_trades)}',
        f'Losses: {len(losing_trades)}',
        f'Win Rate: {win_rate:.1f}%',
        f'Profit: ${total_profit:+,.0f}',
        f'Return: {total_return_pct:+.1f}%'
    ])
    
    table4 = ax9.table(cellText=trade_list_data, cellLoc='center',
                      loc='center', colWidths=[0.12, 0.12, 0.10, 0.12, 0.12, 0.12, 0.12])
    table4.auto_set_font_size(False)
    table4.set_fontsize(7)
    table4.scale(1, 1.5)
    
    # Header styling
    for i in range(7):
        table4[(0, i)].set_facecolor('#1565C0')
        table4[(0, i)].set_text_props(weight='bold', color='white', fontsize=8)
    
    # Color code actions
    for row in range(1, len(trade_list_data) - 2):
        action = trade_list_data[row][2]
        if action == 'BUY':
            table4[(row, 2)].set_facecolor('#C8E6C9')
        elif action == 'SELL':
            table4[(row, 2)].set_facecolor('#FFCDD2')
    
    # ============================================================
    # MARKDOWN REPORT FUNCTIONS
    # ============================================================
    
    def generate_markdown_report():
        """Generate markdown report for the strategy"""
        
        # Get current timestamp
        current_time = datetime.now(pytz.timezone('America/New_York'))
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Create markdown content
        md_content = f"""# Strategy Analysis Report: {strategy.name}

**Generated**: {timestamp}  
**Simulation Period**: {tracker.dates[0].strftime('%Y-%m-%d') if tracker.dates else 'N/A'} to {tracker.dates[-1].strftime('%Y-%m-%d') if tracker.dates else 'N/A'}  
**Initial Capital**: ${INITIAL_CASH:,.0f}  
**Final Portfolio Value**: ${tracker.get_final_value():,.0f}

## 📊 Performance Summary

| Metric | Value |
|--------|-------|
| **Total Return** | {total_return_pct:+.2f}% |
| **Total Profit** | ${total_profit:+,.0f} |
| **Annualized CAGR** | {total_return_pct * 2:+.2f}% |
| **Sharpe Ratio** | {sharpe:.3f} |
| **Sortino Ratio** | {sortino:.3f} |
| **Calmar Ratio** | {calmar:.3f} |
| **Max Drawdown** | {max_dd:.2f}% |
| **Average Drawdown** | {avg_dd:.2f}% |
| **Ulcer Index** | {ulcer:.2f} |
| **Recovery Factor** | {recovery:.2f} |

## 📈 Trading Statistics

| Metric | Value | Metric | Value |
|--------|-------|--------|-------|
| **Total Trades** | {total_trades} | **Win Rate** | {win_rate:.1f}% |
| **Winning Trades** | {len(winning_trades)} | **Average Win** | ${avg_win:,.0f} |
| **Losing Trades** | {len(losing_trades)} | **Average Loss** | ${avg_loss:,.0f} |
| **Profit Factor** | {profit_factor:.2f} | **Largest Win** | ${largest_win:,.0f} |
| **Payoff Ratio** | {payoff_ratio:.2f} | **Largest Loss** | ${largest_loss:,.0f} |
| **Expectancy** | ${expectancy:,.0f} | **Max Consecutive Wins** | {cons_wins} |
| **Avg Trade Duration** | {avg_duration:.1f} days | **Max Consecutive Losses** | {cons_losses} |
| **Exposure Time** | {exposure_time:.1f}% |  |  |

## 💼 Current Portfolio Positions

| Symbol | Shares | Current Price | Position Value | P&L | P&L % |
|--------|--------|---------------|----------------|-----|-------|
"""
        
        # Add position rows
        for pos in position_details:
            md_content += f"| {pos['symbol']} | {pos['shares']:.2f} | ${pos['price']:.2f} | ${pos['value']:,.0f} | ${pos['pl']:+,.0f} | {pos['pl_pct']:+.1f}% |\n"
        
        md_content += f"""
| **Cash** | - | - | **${tracker.cash:,.0f}** | - | - |
| **Total Portfolio** | - | - | **${tracker.get_final_value():,.0f}** | - | - |

## 📊 Stock-by-Stock Performance

| Symbol | Profit/Loss | Number of Trades |
|--------|-------------|------------------|
"""
        
        # Add stock performance rows
        for perf in stock_performance:
            md_content += f"| {perf['symbol']} | ${perf['profit_loss']:+,.0f} | {perf['num_trades']} |\n"
        
        # Add trade history section
        md_content += f"""
## 📝 Recent Trade History (Last 30 Trades)

| Date | Symbol | Action | Price | Shares | Amount | Return % |
|------|--------|--------|-------|--------|--------|----------|
"""
        
        # Take last 30 trades
        for trade in sorted_trades[:30]:
            amount = trade['price'] * trade['shares']
            
            # Find return percentage
            return_pct = 'N/A'
            for t in tracker.trades:
                if (t['date'] == trade['date'] and t['symbol'] == trade['symbol'] and 
                    t['action'] == trade['action'] and abs(t['price'] - trade['price']) < 0.01):
                    if 'return_pct' in t:
                        return_pct = f"{t['return_pct']:+.1f}%"
                    break
            
            action_emoji = "🟢 BUY" if trade['action'] == 'BUY' else "🔴 SELL"
            md_content += f"| {trade['date'].strftime('%Y-%m-%d')} | {trade['symbol']} | {action_emoji} | ${trade['price']:.2f} | {trade['shares']:.2f} | ${amount:,.0f} | {return_pct} |\n"
        
        # Add summary statistics
        md_content += f"""
## 📈 Performance Statistics

- **Best Performing Stock**: {max(stock_performance, key=lambda x: x['profit_loss'])['symbol'] if stock_performance else 'N/A'} (${max([p['profit_loss'] for p in stock_performance]) if stock_performance else 0:+,.0f})
- **Worst Performing Stock**: {min(stock_performance, key=lambda x: x['profit_loss'])['symbol'] if stock_performance else 'N/A'} (${min([p['profit_loss'] for p in stock_performance]) if stock_performance else 0:+,.0f})
- **Most Traded Stock**: {max(stock_performance, key=lambda x: x['num_trades'])['symbol'] if stock_performance else 'N/A'} ({max([p['num_trades'] for p in stock_performance]) if stock_performance else 0} trades)
- **Portfolio Beta**: {tracker.get_portfolio_beta():.3f} (vs S&P 500)
- **Information Ratio**: {tracker.get_information_ratio():.3f}
- **Alpha**: {tracker.get_alpha():.3f}%

## 🔧 Strategy Details

**Strategy Name**: {strategy.name}
**Strategy Class**: {strategy.__class__.__name__}
**Position Sizing**: {tracker.position_size_pct*100:.0f}% per position
**Max Positions**: {tracker.max_positions}
**Trade Execution**: Fractional shares with position limits

## 📋 Notes
- Report generated automatically by Stock Trading Strategy Simulator
- All values in USD
- Calculations based on historical data with look-ahead protection
- Performance shown is simulated and not indicative of future results
"""
        
        return md_content
    
    def copy_markdown_to_clipboard():
        """Copy markdown report to clipboard"""
        try:
            md_content = generate_markdown_report()
            try:
                import pyperclip
                pyperclip.copy(md_content)
                print(f"\n✅ Markdown report copied to clipboard! ({len(md_content)} characters)")
                print("   You can now paste it into any markdown editor.")
            except ImportError:
                # Fallback: save to file and show message
                filename = f"report_{strategy.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                with open(filename, 'w') as f:
                    f.write(md_content)
                print(f"\n⚠️  pyperclip not installed. Report saved to: {filename}")
                print("   Install with: pip install pyperclip")
        except Exception as e:
            print(f"\n❌ Error generating markdown: {e}")
    
    def save_markdown_to_file():
        """Save markdown report to file with dialog"""
        try:
            md_content = generate_markdown_report()
            
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            strategy_safe = "".join(c for c in strategy.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            strategy_safe = strategy_safe.replace(' ', '_')
            default_filename = f"report_{strategy_safe}_{timestamp}.md"
            
            # Ask user where to save
            filename = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=default_filename,
                title="Save Markdown Report"
            )
            
            if filename:  # User didn't cancel
                with open(filename, 'w') as f:
                    f.write(md_content)
                
                print(f"\n✅ Report saved to: {filename}")
                print(f"   File size: {len(md_content)} characters")
                print(f"   Full path: {os.path.abspath(filename)}")
                
                # Show preview
                print(f"\n📄 Report preview (first 5 lines):")
                print("-" * 60)
                for i, line in enumerate(md_content.split('\n')[:5]):
                    print(f"  {line}")
                print("-" * 60)
            
        except Exception as e:
            print(f"\n❌ Error saving report: {e}")
    
    # ============================================================
    # CREATE BUTTONS AT THE TOP OF THE WINDOW
    # ============================================================
    
    # Create a frame for buttons at the top of the Tkinter window
    button_frame = tk.Frame(root, height=50, bg='#f0f0f0')
    button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
    
    # Copy to Clipboard button
    copy_button = tk.Button(
        button_frame, 
        text="📋 Copy Report to Clipboard", 
        command=copy_markdown_to_clipboard,
        bg='#90CAF9',
        fg='black',
        font=('Arial', 10, 'bold'),
        padx=15,
        pady=8,
        relief=tk.RAISED,
        borderwidth=2
    )
    copy_button.pack(side=tk.LEFT, padx=5)
    
    # Save to File button
    save_button = tk.Button(
        button_frame, 
        text="💾 Save Report to File...", 
        command=save_markdown_to_file,
        bg='#A5D6A7',
        fg='black',
        font=('Arial', 10, 'bold'),
        padx=15,
        pady=8,
        relief=tk.RAISED,
        borderwidth=2
    )
    save_button.pack(side=tk.LEFT, padx=5)
    
    # Close button
    close_button = tk.Button(
        button_frame, 
        text="❌ Close Window", 
        command=root.destroy,
        bg='#FFCDD2',
        fg='black',
        font=('Arial', 10, 'bold'),
        padx=15,
        pady=8,
        relief=tk.RAISED,
        borderwidth=2
    )
    close_button.pack(side=tk.RIGHT, padx=5)
    
    # Add instructions label
    instructions = tk.Label(
        button_frame,
        text="📝 Export strategy analysis as markdown | Scroll with mouse wheel",
        bg='#f0f0f0',
        font=('Arial', 9, 'italic')
    )
    instructions.pack(side=tk.LEFT, padx=20)
    
    # ============================================================
    # EMBED MATPLOTLIB FIGURE IN TKINTER WINDOW
    # ============================================================
    
    # Embed the matplotlib figure in Tkinter
    canvas_widget = FigureCanvasTkAgg(fig, master=scrollable_frame)
    canvas_widget.draw()
    canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # Add some padding at the bottom
    padding_label = tk.Label(scrollable_frame, text="", height=2)
    padding_label.pack()
    
    print(f"\n📊 Analysis window opened for: {strategy.name}")
    print("   Use mouse wheel to scroll through all charts")
    print("   Buttons at top: 📋 Copy to Clipboard | 💾 Save to File")
    
    # Start the Tkinter event loop
    root.mainloop()