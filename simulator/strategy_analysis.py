"""
Refactored Strategy Analysis Module - Main Dashboard
Cleaner, more focused main view with modular components
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import filedialog
import pandas as pd
from datetime import datetime
import pytz

from strategy_tracker import INITIAL_CASH
from analysis_components import (
    create_performance_metrics_table,
    create_trading_stats_table,
    create_portfolio_equity_chart,
    create_returns_distribution,
    create_monthly_returns_chart,
    generate_markdown_report
)
from stock_detail_viewer import show_stock_detail_window
from trade_history_viewer import show_trade_history_window
from risk_analysis import RiskAnalyzer  # ADDED: Risk analysis import


def show_strategy_analysis(strategy, tracker, stock_data, symbols, spy_tracker=None, sim_id=None):
    """
    Show main strategy analysis dashboard
    Simplified view with buttons to drill into details
    
    Args:
        strategy: Strategy instance
        tracker: StrategyTracker instance
        stock_data: Dict of stock DataFrames
        symbols: List of symbols
        spy_tracker: Optional SPY benchmark tracker
        sim_id: Optional simulation ID for telemetry
    """
    
    # Create Tkinter window with larger size to prevent overlaps
    root = tk.Tk()
    root.title(f"{strategy.name} - Strategy Dashboard")
    root.geometry("1800x1100")  # Increased size for better layout
    
    # Create main frame with scrolling
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    canvas = tk.Canvas(main_frame)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # ============================================================
    # TOP BUTTON BAR - WITH RISK ANALYSIS BUTTON
    # ============================================================
    button_frame = tk.Frame(root, height=70, bg='#f0f0f0')  # Increased height
    button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
    
    # Export buttons
    def copy_to_clipboard():
        try:
            md_content = generate_markdown_report(strategy, tracker, stock_data, symbols, spy_tracker, sim_id)
            import pyperclip
            pyperclip.copy(md_content)
            print(f"\n✅ Report copied to clipboard! ({len(md_content)} characters)")
        except ImportError:
            print("\n⚠️  pyperclip not installed. Install with: pip install pyperclip")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    def save_to_file():
        try:
            md_content = generate_markdown_report(strategy, tracker, stock_data, symbols, spy_tracker, sim_id)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"report_{strategy.name.replace(' ', '_')}_{timestamp}.md"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All", "*.*")],
                initialfile=default_name
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(md_content)
                print(f"\n✅ Report saved to: {filename}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    def show_stock_details():
        """Open stock performance detail window"""
        show_stock_detail_window(strategy, tracker, stock_data, symbols)
    
    def show_trade_history():
        """Open trade history window"""
        show_trade_history_window(strategy, tracker, sim_id)
    
    def show_risk_analysis():
        """Open risk analysis report"""
        print(f"\n{'='*70}")
        print(f"RISK ANALYSIS: {strategy.name}")
        print(f"{'='*70}")
        
        try:
            analyzer = RiskAnalyzer(tracker, spy_tracker)
            analyzer.print_report()
            
            # Create a new window for risk analysis
            risk_window = tk.Toplevel(root)
            risk_window.title(f"Risk Analysis - {strategy.name}")
            risk_window.geometry("1200x800")
            
            # Create text widget to show risk report
            text_widget = tk.Text(risk_window, wrap=tk.WORD, font=('Courier', 9))
            text_scroll = tk.Scrollbar(risk_window, command=text_widget.yview)
            text_widget.config(yscrollcommand=text_scroll.set)
            
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Get risk report and display
            report = analyzer.generate_report()
            
            risk_text = f"{'='*70}\n"
            risk_text += f"RISK ANALYSIS REPORT: {strategy.name}\n"
            risk_text += f"{'='*70}\n\n"
            
            # Risk assessment summary
            assessment = report['risk_assessment']
            risk_text += f"{assessment['summary']}\n\n"
            
            # Warnings
            if assessment['warnings']:
                risk_text += f"⚠️ WARNINGS ({len(assessment['warnings'])}):\n"
                for warning in assessment['warnings']:
                    risk_text += f"\n{warning['message']}\n"
                    risk_text += f"  Explanation: {warning['explanation']}\n"
                    risk_text += f"  Recommendation: {warning['recommendation']}\n"
                risk_text += "\n"
            
            # Performance metrics
            risk_text += f"📊 PERFORMANCE:\n"
            risk_text += f"  Total Return: {report['total_return_pct']:+.2f}%\n"
            risk_text += f"  Total Profit: ${report['total_profit_dollars']:+,.0f}\n"
            
            # Risk metrics
            risk_text += f"\n📉 RISK METRICS:\n"
            risk_text += f"  Volatility (Annual): {report['volatility_annual_pct']:.2f}%\n"
            risk_text += f"  Max Drawdown: {report['drawdown_analysis']['max_drawdown_pct']:.2f}%\n"
            risk_text += f"  VaR (95%): {report['value_at_risk_95_pct']:.2f}%\n"
            risk_text += f"  CVaR (95%): {report['conditional_var_95_pct']:.2f}%\n"
            
            # Performance ratios
            risk_text += f"\n📈 PERFORMANCE RATIOS:\n"
            risk_text += f"  Sharpe Ratio: {report['sharpe_ratio']:.3f}\n"
            risk_text += f"  Sortino Ratio: {report['sortino_ratio']:.3f}\n"
            risk_text += f"  Calmar Ratio: {report['calmar_ratio']:.3f}\n"
            
            # Trade statistics
            trade_metrics = report['trade_metrics']
            if trade_metrics:
                risk_text += f"\n💼 TRADE STATISTICS:\n"
                risk_text += f"  Total Trades: {trade_metrics['total_trades']}\n"
                risk_text += f"  Win Rate: {trade_metrics['win_rate_pct']:.1f}%\n"
                risk_text += f"  Avg Win: ${trade_metrics['avg_win_dollars']:,.0f}\n"
                risk_text += f"  Avg Loss: ${trade_metrics['avg_loss_dollars']:,.0f}\n"
                risk_text += f"  Risk/Reward: {trade_metrics['risk_reward_ratio']:.2f}:1\n"
                risk_text += f"  Profit Factor: {trade_metrics['profit_factor']:.2f}\n"
            
            text_widget.insert(1.0, risk_text)
            text_widget.config(state=tk.DISABLED)  # Make read-only
            
            print(f"✅ Risk analysis window opened")
            
        except Exception as e:
            print(f"❌ Error in risk analysis: {e}")
            import traceback
            traceback.print_exc()
    
    def show_portfolio_risk():
        """Show portfolio-level risk analysis"""
        try:
            from portfolio_risk_analyzer import analyze_portfolio_risk
            
            # Get all strategy trackers from results
            if 'results' in globals():
                results = globals()['results']
                if 'strategy_trackers' in results:
                    strategy_trackers = results['strategy_trackers']
                    if len(strategy_trackers) > 1:
                        analyze_portfolio_risk(strategy_trackers, spy_tracker)
                        return
            
            print("\n⚠️  Portfolio analysis requires multiple strategies")
            print("   Run a simulation with at least 2 strategies first")
            
        except Exception as e:
            print(f"❌ Portfolio risk error: {e}")
    
    # Create buttons (arranged to prevent overlap)
    button_row1 = tk.Frame(button_frame, bg='#f0f0f0')
    button_row1.pack(side=tk.TOP, fill=tk.X, pady=2)
    
    button_row2 = tk.Frame(button_frame, bg='#f0f0f0')
    button_row2.pack(side=tk.TOP, fill=tk.X, pady=2)
    
    # Row 1 buttons
    tk.Button(button_row1, text="📋 Copy Report", command=copy_to_clipboard,
              bg='#90CAF9', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_row1, text="💾 Save Report", command=save_to_file,
              bg='#A5D6A7', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_row1, text="⚠️  Risk Analysis", command=show_risk_analysis,
              bg='#FFAB91', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_row1, text="📊 Stock Details", command=show_stock_details,
              bg='#FFE082', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    # Row 2 buttons
    tk.Button(button_row2, text="📜 Trade History", command=show_trade_history,
              bg='#CE93D8', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_row2, text="📈 Portfolio Risk", command=show_portfolio_risk,
              bg='#80DEEA', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_row2, text="❌ Close Dashboard", command=root.destroy,
              bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(side=tk.RIGHT, padx=5)
    
    tk.Label(button_frame, text="📈 Strategy Analysis Dashboard",
             bg='#f0f0f0', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=20)
    
    # ============================================================
    # MAIN MATPLOTLIB FIGURE (Improved layout to prevent overlap)
    # ============================================================
    fig = plt.figure(figsize=(20, 18))  # Larger figure to prevent overlap
    fig.suptitle(f'{strategy.name} - Performance Dashboard', 
                 fontsize=16, fontweight='bold', y=0.98)  # Adjust title position
    
    # Create flexible grid with more space between components
    gs = fig.add_gridspec(5, 4, hspace=0.6, wspace=0.5, top=0.96, bottom=0.02)
    
    # Row 0: Portfolio equity curve with SPY overlay + metrics
    create_portfolio_equity_chart(fig, gs[0, :3], tracker, spy_tracker, strategy.color)
    create_performance_metrics_table(fig, gs[0, 3], tracker, spy_tracker, sim_id)
    
    # Row 1: Trading statistics + current positions
    create_trading_stats_table(fig, gs[1, :2], tracker, sim_id)
    create_current_positions_table(fig, gs[1, 2:], tracker, stock_data, symbols)
    
    # Row 2: Returns distribution + profit/loss heatmap
    create_returns_distribution(fig, gs[2, :2], tracker)
    create_pnl_heatmap(fig, gs[2, 2:], tracker, stock_data, symbols)
    
    # Row 3: Monthly returns chart (full width)
    create_monthly_returns_chart(fig, gs[3, :], tracker)
    
    # Row 4: Trade volume over time (full width)
    create_trade_volume_chart(fig, gs[4, :], tracker)
    
    # Embed matplotlib in Tkinter
    canvas_widget = FigureCanvasTkAgg(fig, master=scrollable_frame)
    canvas_widget.draw()
    canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=20)  # Add padding
    
    # Add some vertical space at bottom
    tk.Label(scrollable_frame, text="", height=2).pack()
    
    print(f"\n📊 Analysis dashboard opened for: {strategy.name}")
    print(f"   Simulation ID: {sim_id}")
    
    root.mainloop()


def create_current_positions_table(fig, gs_spec, tracker, stock_data, symbols):
    """Create current positions table with improved layout"""
    ax = fig.add_subplot(gs_spec)
    ax.axis('off')
    
    position_data = [['Symbol', 'Shares', 'Value', 'P&L %']]
    
    total_position_value = 0
    
    for symbol in symbols:
        shares = tracker.positions.get(symbol, 0)
        if shares > 0:
            current_price = stock_data[symbol]['close'].iloc[-1]
            position_value = shares * current_price
            total_position_value += position_value
            
            # Calculate P&L
            symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol and t['action'] == 'BUY']
            if symbol_trades:
                total_cost = sum(t['price'] * t['shares'] for t in symbol_trades)
                total_shares = sum(t['shares'] for t in symbol_trades)
                avg_buy = total_cost / total_shares if total_shares > 0 else current_price
                pl_pct = (current_price - avg_buy) / avg_buy * 100 if avg_buy > 0 else 0
            else:
                pl_pct = 0
            
            position_data.append([
                symbol,
                f'{shares:.2f}',
                f'${position_value:,.0f}',
                f'{pl_pct:+.1f}%'
            ])
    
    position_data.append(['', '', '', ''])
    position_data.append(['Cash', '-', f'${tracker.cash:,.0f}', '-'])
    position_data.append(['Total', '-', f'${tracker.get_final_value():,.0f}', '-'])
    
    table = ax.table(cellText=position_data, cellLoc='left',
                     loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
    table.auto_set_font_size(False)
    table.set_fontsize(7)  # Smaller font to prevent overlap
    table.scale(1, 1.8)
    
    # Header
    for i in range(4):
        table[(0, i)].set_facecolor('#1565C0')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Current Portfolio', fontweight='bold', pad=15, fontsize=10)  # Added padding


def create_pnl_heatmap(fig, gs_spec, tracker, stock_data, symbols):
    """Create P&L heatmap showing win/loss distribution"""
    ax = fig.add_subplot(gs_spec)
    
    stock_summary = tracker.get_stock_performance_summary()
    
    if not stock_summary:
        ax.text(0.5, 0.5, 'No completed trades', 
                ha='center', va='center', transform=ax.transAxes, fontsize=10)
        ax.set_title('Profit/Loss by Stock', fontweight='bold', fontsize=10)
        return
    
    # Sort by P&L
    sorted_stocks = sorted(stock_summary.items(), key=lambda x: x[1]['pnl'], reverse=True)
    
    # Take top 20 for visibility
    display_stocks = sorted_stocks[:20]
    
    symbols_list = [s[0] for s in display_stocks]
    pnl_values = [s[1]['pnl'] for s in display_stocks]
    win_rates = [s[1]['win_rate'] for s in display_stocks]
    
    # Create color map based on P&L and win rate
    colors = []
    for pnl, wr in zip(pnl_values, win_rates):
        if pnl > 0:
            # Green intensity based on win rate
            intensity = min(wr / 100, 1.0)
            colors.append((0, intensity * 0.8, 0))
        else:
            # Red intensity based on loss rate
            intensity = min((100 - wr) / 100, 1.0)
            colors.append((intensity * 0.8, 0, 0))
    
    bars = ax.barh(symbols_list, pnl_values, color=colors, edgecolor='black', linewidth=1)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, pnl_values)):
        label = f'${val:,.0f}'
        x_pos = val + (max(pnl_values) - min(pnl_values)) * 0.02
        if val < 0:
            x_pos = val - (max(pnl_values) - min(pnl_values)) * 0.02
        
        ax.text(x_pos, i, label, va='center', 
                ha='left' if val > 0 else 'right', fontsize=7, fontweight='bold')
    
    ax.axvline(0, color='black', linewidth=2)
    ax.set_title('Profit/Loss by Stock (Top 20)', fontweight='bold', fontsize=10)
    ax.set_xlabel('$ Profit/Loss', fontsize=9)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3, axis='x')


def create_trade_volume_chart(fig, gs_spec, tracker):
    """Create chart showing trade volume over time"""
    ax = fig.add_subplot(gs_spec)
    
    if not tracker.trades:
        ax.text(0.5, 0.5, 'No trades executed', 
                ha='center', va='center', transform=ax.transAxes, fontsize=10)
        ax.set_title('Trade Volume Over Time', fontweight='bold', fontsize=10)
        return
    
    # Convert trades to DataFrame
    df = pd.DataFrame(tracker.trades)
    df['amount'] = df['price'] * df['shares']
    
    # Group by date and action
    df_grouped = df.groupby(['date', 'action'])['amount'].sum().unstack(fill_value=0)
    
    # Plot stacked bar chart
    if 'BUY' in df_grouped.columns:
        ax.bar(df_grouped.index, df_grouped['BUY'], label='BUY', color='#4CAF50', alpha=0.7)
    
    if 'SELL' in df_grouped.columns:
        ax.bar(df_grouped.index, -df_grouped['SELL'], label='SELL', color='#F44336', alpha=0.7)
    
    ax.axhline(0, color='black', linewidth=1)
    ax.set_title('Trade Volume Over Time', fontweight='bold', fontsize=10)
    ax.set_xlabel('Date', fontsize=9)
    ax.set_ylabel('Trade Amount ($)', fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.tick_params(labelsize=7)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')