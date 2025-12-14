"""
Analysis Button Functions
All the individual analysis window functions
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')  # CRITICAL: Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import os
import io
import sys

from analysis_components import generate_markdown_report
from mock_trackers import MockTracker, MockStrategy


def export_report(reader, strategy_name, dashboard):
    """Export markdown report using your existing function"""
    try:
        import pyperclip
        md_content = generate_markdown_report(reader, strategy_name)
        pyperclip.copy(md_content)
        messagebox.showinfo("Success", f"Report copied to clipboard!\n({len(md_content)} characters)")
    except ImportError:
        try:
            filename = f"report_{strategy_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w') as f:
                md_content = generate_markdown_report(reader, strategy_name)
                f.write(md_content)
            messagebox.showinfo("Success", f"Report saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export: {e}")


def show_risk_analysis(reader, strategy_name, dashboard):
    """Open comprehensive risk analysis using your risk_analysis.py"""
    try:
        # Create risk window
        risk_window = tk.Toplevel(dashboard)
        risk_window.title(f"🚨 Risk Analysis - {strategy_name}")
        risk_window.geometry("1200x800")
        
        # Create main frame
        main_frame = tk.Frame(risk_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Get trade history for risk analysis
        trades = reader.get_trade_history(strategy_name)
        
        if trades.empty:
            tk.Label(main_frame, text="No trade data for risk analysis", 
                    font=('Arial', 12)).pack(expand=True)
            return
        
        # Get portfolio history
        portfolio = reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            tk.Label(main_frame, text="No portfolio data for risk analysis", 
                    font=('Arial', 12)).pack(expand=True)
            return
        
        # Create mock tracker
        mock_tracker = MockTracker(strategy_name, trades, portfolio)
        
        # Get SPY tracker if available
        spy_tracker = None
        spy_portfolio = reader.get_portfolio_history('SPY')
        if not spy_portfolio.empty:
            spy_trades = reader.get_trade_history('SPY')
            spy_tracker = MockTracker('SPY', spy_trades, spy_portfolio)
        
        # Create RiskAnalyzer
        from risk_analysis import RiskAnalyzer
        analyzer = RiskAnalyzer(mock_tracker, spy_tracker)
        
        # Get complete report
        report = analyzer.generate_report()
        
        # Create text widget for report
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 9))
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Format report for display
        report_text = f"{'='*70}\n"
        report_text += f"COMPREHENSIVE RISK ANALYSIS: {strategy_name}\n"
        report_text += f"{'='*70}\n\n"
        
        # Add risk assessment
        assessment = report.get('risk_assessment', {})
        report_text += f"📊 RISK ASSESSMENT:\n"
        report_text += f"  Severity: {assessment.get('severity', 'N/A')}\n"
        report_text += f"  Risk Score: {assessment.get('risk_score', 0)}/100\n"
        report_text += f"  Summary: {assessment.get('summary', 'N/A')}\n\n"
        
        # Add warnings
        warnings = assessment.get('warnings', [])
        if warnings:
            report_text += f"⚠️  WARNINGS ({len(warnings)}):\n"
            for warning in warnings:
                report_text += f"\n  {warning.get('message', 'N/A')}\n"
                report_text += f"    Explanation: {warning.get('explanation', 'N/A')}\n"
                report_text += f"    Recommendation: {warning.get('recommendation', 'N/A')}\n"
            report_text += "\n"
        
        # Add key metrics
        report_text += f"📈 PERFORMANCE METRICS:\n"
        report_text += f"  Total Return: {report.get('total_return_pct', 0):+.2f}%\n"
        report_text += f"  Total Profit: ${report.get('total_profit_dollars', 0):+,.0f}\n"
        report_text += f"  Volatility: {report.get('volatility_annual_pct', 0):.2f}%\n"
        report_text += f"  Max Drawdown: {report.get('drawdown_analysis', {}).get('max_drawdown_pct', 0):.2f}%\n\n"
        
        # Add performance ratios
        report_text += f"📊 PERFORMANCE RATIOS:\n"
        report_text += f"  Sharpe Ratio: {report.get('sharpe_ratio', 0):.3f}\n"
        report_text += f"  Sortino Ratio: {report.get('sortino_ratio', 0):.3f}\n"
        report_text += f"  Calmar Ratio: {report.get('calmar_ratio', 0):.3f}\n"
        report_text += f"  Omega Ratio: {report.get('omega_ratio', 0):.3f}\n\n"
        
        # Add trade metrics
        trade_metrics = report.get('trade_metrics', {})
        if trade_metrics:
            report_text += f"💼 TRADE STATISTICS:\n"
            report_text += f"  Total Trades: {trade_metrics.get('total_trades', 0)}\n"
            report_text += f"  Win Rate: {trade_metrics.get('win_rate_pct', 0):.1f}%\n"
            report_text += f"  Profit Factor: {trade_metrics.get('profit_factor', 0):.2f}\n"
            report_text += f"  Risk/Reward: {trade_metrics.get('risk_reward_ratio', 0):.2f}:1\n"
            report_text += f"  Expectancy: ${trade_metrics.get('expectancy_dollars', 0):+,.0f}\n\n"
        
        text_widget.insert(1.0, report_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=risk_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Risk analysis window opened")
        
    except Exception as e:
        print(f"❌ Risk analysis error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open risk analysis:\n{e}")


def show_stock_details(reader, strategy_name, dashboard):
    """Open stock detail viewer using your existing module"""
    try:
        # Get stock performance data
        stock_perf = reader.get_stock_performance(strategy_name)
        
        if stock_perf.empty:
            messagebox.showinfo("No Data", "No stock performance data available")
            return
        
        # Create stock detail window
        stock_window = tk.Toplevel(dashboard)
        stock_window.title(f"📊 Stock Performance - {strategy_name}")
        stock_window.geometry("1400x800")
        
        # Create main frame
        main_frame = tk.Frame(stock_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, text=f"📊 Stock Performance - {strategy_name}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create treeview
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(tree_frame)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create tree
        columns = ('Symbol', 'Trades', 'Total P&L', 'Avg P&L', 'Avg P&L %', 'Win Rate')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                          yscrollcommand=v_scrollbar.set,
                          xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.config(command=tree.yview)
        h_scrollbar.config(command=tree.xview)
        
        # Configure columns
        tree.heading('Symbol', text='Symbol')
        tree.heading('Trades', text='# Trades')
        tree.heading('Total P&L', text='Total P&L')
        tree.heading('Avg P&L', text='Avg P&L')
        tree.heading('Avg P&L %', text='Avg P&L %')
        tree.heading('Win Rate', text='Win Rate')
        
        tree.column('Symbol', width=100, anchor='center')
        tree.column('Trades', width=80, anchor='center')
        tree.column('Total P&L', width=120, anchor='e')
        tree.column('Avg P&L', width=120, anchor='e')
        tree.column('Avg P&L %', width=100, anchor='center')
        tree.column('Win Rate', width=100, anchor='center')
        
        # Populate with data
        for _, row in stock_perf.iterrows():
            values = (
                row['symbol'],
                int(row['num_trades']),
                f"${row['total_pnl']:+,.0f}",
                f"${row['avg_pnl']:+,.0f}" if not pd.isna(row['avg_pnl']) else '-',
                f"{row['avg_pnl_pct']:+.1f}%" if not pd.isna(row['avg_pnl_pct']) else '-',
                f"{row.get('win_rate', 0):.1f}%" if 'win_rate' in row and not pd.isna(row['win_rate']) else 'N/A'
            )
            
            # Color code
            if row['total_pnl'] > 0:
                tree.insert('', tk.END, values=values, tags=('profit',))
            else:
                tree.insert('', tk.END, values=values, tags=('loss',))
        
        tree.tag_configure('profit', background='#C8E6C9')
        tree.tag_configure('loss', background='#FFCDD2')
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Summary stats
        summary_frame = tk.Frame(main_frame, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=2)
        summary_frame.pack(fill=tk.X, pady=10)
        
        total_stocks = len(stock_perf)
        profitable = len(stock_perf[stock_perf['total_pnl'] > 0])
        total_pnl = stock_perf['total_pnl'].sum()
        
        tk.Label(summary_frame, 
                text=f"Total Stocks: {total_stocks} | Profitable: {profitable} ({profitable/total_stocks*100:.1f}%) | Total P&L: ${total_pnl:+,.0f}",
                bg='#e0e0e0',
                font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=stock_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=5)
        
        print(f"✅ Stock details window opened")
        
    except Exception as e:
        print(f"❌ Stock details error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open stock details:\n{e}")


def show_trade_history(reader, strategy_name, dashboard):
    """Open trade history viewer using your existing module"""
    try:
        # Import your trade history viewer
        from trade_history_viewer import show_trade_history_window
        
        # Create mock tracker for compatibility
        trades = reader.get_trade_history(strategy_name)
        
        class MockTracker:
            def __init__(self, trades_df):
                self.trades = trades_df.to_dict('records')
            
            def get_trade_history_dataframe(self):
                return trades
        
        mock_tracker = MockTracker(trades)
        
        # Get simulation ID
        sim_id = reader.get_simulation_id()
        
        # Create mock strategy for compatibility
        mock_strategy = MockStrategy(strategy_name)
        
        # Open the window
        show_trade_history_window(mock_strategy, mock_tracker, sim_id)
        
    except Exception as e:
        print(f"❌ Trade history error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open trade history:\n{e}")


def show_portfolio_risk(reader, strategy_name, dashboard):
    """Open portfolio-level risk analysis"""
    try:
        from portfolio_risk_analyzer import analyze_portfolio_risk
        
        # Create mock tracker for the current strategy
        trades = reader.get_trade_history(strategy_name)
        portfolio = reader.get_portfolio_history(strategy_name)
        
        # Create mock tracker
        tracker = MockTracker(strategy_name, trades, portfolio)
        
        # Get SPY tracker if available
        spy_tracker = None
        spy_portfolio = reader.get_portfolio_history('SPY')
        if not spy_portfolio.empty:
            spy_trades = reader.get_trade_history('SPY')
            spy_tracker = MockTracker('SPY', spy_trades, spy_portfolio)
        
        # Create portfolio risk window
        risk_window = tk.Toplevel(dashboard)
        risk_window.title(f"📈 Portfolio Risk Analysis - {strategy_name}")
        risk_window.geometry("1000x700")
        
        # Create main frame
        main_frame = tk.Frame(risk_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, text=f"📈 Portfolio Risk Analysis - {strategy_name}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create text widget
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 9))
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Generate portfolio risk report
        report = f"{'='*70}\n"
        report += f"PORTFOLIO RISK ANALYSIS: {strategy_name}\n"
        report += f"{'='*70}\n\n"
        
        # Get stats from database
        stats = reader.get_summary_stats(strategy_name)
        
        if stats:
            report += f"📊 PORTFOLIO SUMMARY:\n"
            report += f"  Total Return: {stats.get('total_return_pct', 0):+.2f}%\n"
            report += f"  Total Profit: ${stats.get('total_profit_dollars', 0):+,.0f}\n"
            report += f"  Initial Capital: ${stats.get('initial_cash', 0):,.0f}\n"
            report += f"  Final Value: ${stats.get('final_value', 0):,.0f}\n"
            report += f"  Completed Trades: {stats.get('completed_trades', 0)}\n"
            report += f"  Open Positions: {stats.get('open_positions', 0)}\n\n"
            
            report += f"📉 RISK METRICS:\n"
            report += f"  Max Drawdown: {stats.get('max_drawdown_pct', 0):.2f}%\n"
            report += f"  Sharpe Ratio: {stats.get('sharpe_ratio', 0):.3f}\n"
            report += f"  Sortino Ratio: {stats.get('sortino_ratio', 0):.3f}\n"
            report += f"  Calmar Ratio: {stats.get('calmar_ratio', 0):.3f}\n\n"
            
            report += f"📈 TRADE PERFORMANCE:\n"
            report += f"  Win Rate: {stats.get('win_rate_pct', 0):.1f}%\n"
            report += f"  Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            report += f"  Avg Win: ${stats.get('avg_win_dollars', 0):,.0f}\n"
            report += f"  Avg Loss: ${stats.get('avg_loss_dollars', 0):,.0f}\n\n"
            
            # Risk assessment
            max_dd = stats.get('max_drawdown_pct', 0)
            if max_dd > 20:
                report += f"🚨 RISK ASSESSMENT: CRITICAL\n"
                report += f"  Excessive drawdown ({max_dd:.1f}%)\n"
            elif max_dd > 10:
                report += f"⚠️  RISK ASSESSMENT: HIGH\n"
                report += f"  High drawdown ({max_dd:.1f}%)\n"
            else:
                report += f"✅ RISK ASSESSMENT: ACCEPTABLE\n"
                report += f"  Drawdown within limits ({max_dd:.1f}%)\n"
        
        text_widget.insert(1.0, report)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=risk_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Portfolio risk analysis opened")
        
    except Exception as e:
        print(f"❌ Portfolio risk error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open portfolio risk:\n{e}")


def show_performance_timeline(reader, strategy_name, dashboard):
    """Open performance timeline analysis"""
    try:
        from performance_timeline import PerformanceTimeline
        
        # Create mock trackers
        portfolio = reader.get_portfolio_history(strategy_name)
        spy_portfolio = reader.get_portfolio_history('SPY')
        
        tracker = MockTracker(strategy_name, portfolio, portfolio)  # Need both trades and portfolio
        spy_tracker = MockTracker('SPY', spy_portfolio, spy_portfolio) if not spy_portfolio.empty else None
        
        # Create timeline window
        timeline_window = tk.Toplevel(dashboard)
        timeline_window.title(f"📅 Performance Timeline - {strategy_name}")
        timeline_window.geometry("1400x900")
        
        # Create matplotlib figure
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle(f'{strategy_name} - Performance Timeline', fontsize=14, fontweight='bold')
        
        # Calculate returns
        if not portfolio.empty:
            # Plot 1: Cumulative returns
            returns = portfolio['portfolio_value'].pct_change().fillna(0)
            cum_returns = (1 + returns).cumprod() * 100
            axes[0].plot(portfolio['date'], cum_returns, label='Strategy', linewidth=2)
            
            if not spy_portfolio.empty:
                spy_returns = spy_portfolio['portfolio_value'].pct_change().fillna(0)
                spy_cum_returns = (1 + spy_returns).cumprod() * 100
                axes[0].plot(spy_portfolio['date'], spy_cum_returns, 
                           label='S&P 500', linestyle='--', alpha=0.7)
            
            axes[0].set_title('Cumulative Returns')
            axes[0].set_ylabel('Return (%)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # Plot 2: Daily returns
            axes[1].bar(portfolio['date'], returns * 100, 
                      color=['g' if x > 0 else 'r' for x in returns],
                      alpha=0.6)
            axes[1].axhline(0, color='black', linewidth=0.5)
            axes[1].set_title('Daily Returns')
            axes[1].set_ylabel('Return (%)')
            axes[1].grid(True, alpha=0.3, axis='y')
            
            # Plot 3: Drawdown
            cummax = portfolio['portfolio_value'].cummax()
            drawdown = (portfolio['portfolio_value'] - cummax) / cummax * 100
            axes[2].fill_between(portfolio['date'], drawdown, color='red', alpha=0.3)
            axes[2].set_title('Drawdown')
            axes[2].set_ylabel('Drawdown (%)')
            axes[2].set_xlabel('Date')
            axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=timeline_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Close button
        tk.Button(timeline_window, text="❌ Close", command=timeline_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Performance timeline opened")
        
    except Exception as e:
        print(f"❌ Timeline error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open timeline:\n{e}")


