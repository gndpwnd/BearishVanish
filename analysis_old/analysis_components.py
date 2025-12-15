"""
Analysis Components - REFACTORED FOR DATABASE-ONLY
NO dependencies on simulator code - all data from SQLite
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
import pytz


def create_portfolio_equity_chart(fig, gs_spec, reader, strategy_name, spy_name='SPY', color='blue'):
    """
    Create portfolio equity curve - reads from database
    
    Args:
        fig: Matplotlib figure
        gs_spec: Grid spec for subplot
        reader: SimulationReader instance
        strategy_name: Strategy to plot
        spy_name: Benchmark strategy name
        color: Line color
    """
    ax = fig.add_subplot(gs_spec)
    
    # Get portfolio history from database
    portfolio = reader.get_portfolio_history(strategy_name)
    
    if portfolio.empty:
        ax.text(0.5, 0.5, 'No portfolio data', 
                ha='center', va='center', transform=ax.transAxes)
        return
    
    # Get initial cash from database
    initial_cash = reader.get_initial_cash()
    
    # Plot strategy
    ax.plot(portfolio['date'], portfolio['portfolio_value'], 
            color=color, linewidth=2.5, label='Strategy', zorder=3)
    
    # Plot SPY if available
    spy_portfolio = reader.get_portfolio_history(spy_name)
    if not spy_portfolio.empty:
        ax.plot(spy_portfolio['date'], spy_portfolio['portfolio_value'],
                color='black', linewidth=2, linestyle='--', alpha=0.7, 
                label='S&P 500', zorder=2)
    
    # Initial capital line
    ax.axhline(initial_cash, color='gray', linestyle=':', alpha=0.5, 
               linewidth=1, label='Initial Capital')
    
    # Fill areas
    ax.fill_between(portfolio['date'], initial_cash, portfolio['portfolio_value'],
                    where=(portfolio['portfolio_value'].values > initial_cash),
                    color='green', alpha=0.15, zorder=1)
    ax.fill_between(portfolio['date'], initial_cash, portfolio['portfolio_value'],
                    where=(portfolio['portfolio_value'].values <= initial_cash),
                    color='red', alpha=0.15, zorder=1)
    
    # Drawdown overlay
    values = portfolio['portfolio_value'].values
    running_max = np.maximum.accumulate(values)
    drawdown_pct = ((values - running_max) / running_max) * 100
    
    ax2 = ax.twinx()
    ax2.fill_between(portfolio['date'], 0, drawdown_pct, 
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


def create_performance_metrics_table(fig, gs_spec, reader, strategy_name, spy_name='SPY'):
    """
    Create performance metrics table - reads from database
    """
    ax = fig.add_subplot(gs_spec)
    ax.axis('off')
    
    # Get all metrics from database
    stats = reader.get_summary_stats(strategy_name)
    
    if not stats:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Get SPY comparison
    spy_stats = reader.get_summary_stats(spy_name)
    spy_return = spy_stats['total_return_pct'] if spy_stats else 0
    
    # Format metrics
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Return', f"{stats['total_return_pct']:+.2f}%"],
        ['Total Profit', f"${stats['total_profit_dollars']:+,.0f}"],
        ['vs S&P 500', f"{stats['total_return_pct'] - spy_return:+.2f}%" if spy_stats else 'N/A'],
        ['', ''],
        ['Sharpe Ratio', f"{stats['sharpe_ratio']:.3f}"],
        ['Sortino Ratio', f"{stats['sortino_ratio']:.3f}"],
        ['Calmar Ratio', f"{stats['calmar_ratio']:.3f}"],
        ['', ''],
        ['Win Rate (Closed)', f"{stats['win_rate_pct']:.1f}%"],
        ['Completed Trades', f"{stats['completed_trades']}"],
        ['Avg Win', f"${stats['avg_win_dollars']:,.0f}"],
        ['Avg Loss', f"${stats['avg_loss_dollars']:,.0f}"],
        ['Risk/Reward', f"{abs(stats['avg_win_dollars']/stats['avg_loss_dollars']):.2f}:1" if stats['avg_loss_dollars'] != 0 else 'N/A'],
        ['', ''],
        ['Beta', f"{stats['beta']:.3f}" if stats['beta'] is not None else 'N/A'],
        ['Alpha', f"{stats['alpha_pct']:.2f}%" if stats['alpha_pct'] is not None else 'N/A'],
        ['Info Ratio', f"{stats['information_ratio']:.3f}" if stats['information_ratio'] is not None else 'N/A'],
        ['', ''],
        ['Max Drawdown', f"{stats['max_drawdown_pct']:.2f}%"],
        ['Max DD $', f"${stats['max_drawdown_pct'] * stats['initial_cash'] / 100:,.0f}"],
    ]
    
    create_metrics_table(ax, metrics_data)


def create_metrics_table(ax, metrics_data):
    """Helper to create styled metrics table"""
    table = ax.table(cellText=metrics_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(7)
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
    profit_str = metrics_data[2][1].replace('$', '').replace(',', '').replace('+', '')
    profit_val = float(profit_str)
    if profit_val > 0:
        table[(2, 1)].set_facecolor('#C8E6C9')
    else:
        table[(2, 1)].set_facecolor('#FFCDD2')
    
    # Highlight win rate row
    table[(9, 0)].set_text_props(weight='bold')
    table[(9, 1)].set_text_props(weight='bold')
    
    return table


def create_trading_stats_table(fig, gs_spec, reader, strategy_name):
    """Create trading statistics table - reads from database"""
    ax = fig.add_subplot(gs_spec)
    ax.axis('off')
    
    stats = reader.get_summary_stats(strategy_name)
    
    if not stats:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        return
    
    stats_data = [
        ['Trading Statistics', ''],
        ['Total Executions', f"{stats['total_trades']}"],
        ['Completed Trades', f"{stats['completed_trades']}"],
        ['Open Positions', f"{stats['open_positions']}"],
        ['', ''],
        ['Win Rate (Closed)', f"{stats['win_rate_pct']:.1f}%"],
        ['Winning Trades', f"{stats['winning_trades']}"],
        ['Losing Trades', f"{stats['losing_trades']}"],
        ['', ''],
        ['Profit Factor', f"{stats['profit_factor']:.2f}"],
        ['Expectancy', f"${stats['expectancy_dollars']:,.0f}"],
    ]
    
    create_stats_table(ax, stats_data)


def create_stats_table(ax, stats_data):
    """Helper to create styled stats table"""
    table = ax.table(cellText=stats_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(7)
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


def create_returns_distribution(fig, gs_spec, reader, strategy_name):
    """Create returns distribution histogram - reads from database"""
    ax = fig.add_subplot(gs_spec)
    
    # Get closed trades
    closed = reader.get_closed_trades(strategy_name)
    
    if closed.empty:
        ax.text(0.5, 0.5, 'No completed trades', 
                ha='center', va='center', transform=ax.transAxes)
        return
    
    returns = closed['profit_loss_pct'].values
    
    # Create histogram
    n, bins, patches = ax.hist(returns, bins=20, edgecolor='black', alpha=0.7)
    
    # Color bars
    for i, patch in enumerate(patches):
        if bins[i] < 0:
            patch.set_facecolor('#F44336')
        else:
            patch.set_facecolor('#4CAF50')
    
    ax.axvline(0, color='black', linestyle='--', linewidth=2, label='Breakeven', zorder=3)
    
    # Add mean and median
    mean_return = returns.mean()
    median_return = np.median(returns)
    
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


def create_monthly_returns_chart(fig, gs_spec, reader, strategy_name):
    """Create monthly returns bar chart - reads from database"""
    ax = fig.add_subplot(gs_spec)
    
    portfolio = reader.get_portfolio_history(strategy_name)
    
    if portfolio.empty or len(portfolio) < 2:
        ax.text(0.5, 0.5, 'Insufficient data', 
                ha='center', va='center', transform=ax.transAxes)
        return
    
    # Calculate daily returns
    portfolio = portfolio.set_index('date')
    returns_series = portfolio['portfolio_value'].pct_change()
    
    # Monthly returns
    monthly_returns = returns_series.groupby(pd.Grouper(freq='ME')).apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    
    monthly_returns = monthly_returns.dropna()
    
    if len(monthly_returns) == 0:
        ax.text(0.5, 0.5, 'No monthly data', 
                ha='center', va='center', transform=ax.transAxes)
        return
    
    # Format labels
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


def generate_markdown_report(reader, strategy_name):
    """
    Generate comprehensive markdown report - reads from database
    
    Args:
        reader: SimulationReader instance
        strategy_name: Strategy to report on
    
    Returns:
        str: Markdown formatted report
    """
    timestamp = datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    stats = reader.get_summary_stats(strategy_name)
    
    if not stats:
        return "# Error: No data found for strategy"
    
    # Get benchmark comparison
    benchmark = reader.get_benchmark_comparison(strategy_name)
    spy_return = benchmark['benchmark']['return'] if benchmark else 0
    spy_sharpe = benchmark['benchmark']['sharpe'] if benchmark else 0
    
    md = f"""# Strategy Analysis Report: {strategy_name}

**Generated**: {timestamp}  
**Simulation ID**: {reader.get_simulation_id()}  
**Period**: {stats['start_date']} to {stats['end_date']}  
**Initial Capital**: ${stats['initial_cash']:,.0f}  

## 📊 Performance Summary

| Metric | Strategy | S&P 500 | Difference |
|--------|----------|---------|------------|
| **Total Return** | {stats['total_return_pct']:+.2f}% | {spy_return:+.2f}% | {stats['total_return_pct'] - spy_return:+.2f}% |
| **Profit/Loss** | ${stats['total_profit_dollars']:+,.0f} | - | - |
| **Sharpe Ratio** | {stats['sharpe_ratio']:.3f} | {spy_sharpe:.3f} | - |
| **Max Drawdown** | {stats['max_drawdown_pct']:.2f}% | - | - |
| **Win Rate** | {stats['win_rate_pct']:.1f}% ({stats['completed_trades']} trades) | - | - |
| **Profit Factor** | {stats['profit_factor']:.2f} | - | - |

## ⚠️ RISK ASSESSMENT

**Risk Score**: {calculate_risk_score(stats):.0f}/100

"""
    
    # Add risk warnings
    if stats['win_rate_pct'] > 70 and stats['total_return_pct'] < 5:
        md += f"- ❌ **HIGH WIN RATE, LOW RETURN**: {stats['win_rate_pct']:.1f}% win rate but only {stats['total_return_pct']:+.2f}% return\n"
    
    if stats['max_drawdown_pct'] > 10:
        md += f"- ❌ **EXCESSIVE DRAWDOWN**: {stats['max_drawdown_pct']:.2f}% maximum drawdown\n"
    
    risk_reward = abs(stats['avg_win_dollars'] / stats['avg_loss_dollars']) if stats['avg_loss_dollars'] != 0 else 0
    if risk_reward < 1.0:
        md += f"- ❌ **POOR RISK/REWARD**: {risk_reward:.2f}:1\n"
    
    if stats['profit_factor'] < 1.5:
        md += f"- ⚠️ **LOW PROFIT FACTOR**: {stats['profit_factor']:.2f}\n"
    
    md += f"""
## 💼 Portfolio Summary

- **Total Executions**: {stats['total_trades']}
- **Completed Trades**: {stats['completed_trades']}
- **Open Positions**: {stats['open_positions']}
- **Final Value**: ${stats['final_value']:,.0f}

## 📈 Detailed Metrics

### Trade Statistics
- **Win Rate**: {stats['win_rate_pct']:.1f}%
- **Winning Trades**: {stats['winning_trades']}
- **Losing Trades**: {stats['losing_trades']}
- **Average Win**: ${stats['avg_win_dollars']:,.0f}
- **Average Loss**: ${stats['avg_loss_dollars']:,.0f}
- **Risk/Reward Ratio**: {risk_reward:.2f}:1
- **Expectancy**: ${stats['expectancy_dollars']:,.0f}

### Risk Metrics
- **Sharpe Ratio**: {stats['sharpe_ratio']:.3f}
- **Sortino Ratio**: {stats['sortino_ratio']:.3f}
- **Calmar Ratio**: {stats['calmar_ratio']:.3f}
- **Max Drawdown**: {stats['max_drawdown_pct']:.2f}%

### Market Exposure
- **Beta**: {stats['beta']:.3f if stats['beta'] is not None else 'N/A'}
- **Alpha**: {stats['alpha_pct']:.2f if stats['alpha_pct'] is not None else 'N/A'}%
- **Information Ratio**: {stats['information_ratio']:.3f if stats['information_ratio'] is not None else 'N/A'}

## ⚠️ Important Notes

- **Database Source**: {reader.db_path.name}
- Win rate based on {stats['completed_trades']} completed trades
- Open positions ({stats['open_positions']}) NOT included in win rate
- All metrics calculated from simulation telemetry database
"""
    
    return md


def calculate_risk_score(stats):
    """Calculate overall risk score (0-100, higher = riskier)"""
    score = 0
    
    # Drawdown component
    score += min(stats['max_drawdown_pct'] * 2, 40)
    
    # Return/Risk component
    if stats['total_return_pct'] < 0:
        score += 30
    elif stats['total_return_pct'] < 5:
        score += 20
    
    # Win rate mismatch
    if stats['win_rate_pct'] > 70 and stats['total_return_pct'] < 10:
        score += 30
    
    return min(score, 100)