"""
Analysis Button Functions - FULLY REFACTORED FOR DATABASE
All functions now use SimulationReader directly - NO MockTracker dependencies

Each function opens a specific analysis window with database-driven insights
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime

from analysis_components import generate_markdown_report


# ============================================================
# EXPORT & REPORTING
# ============================================================

def export_report(reader, strategy_name, dashboard):
    """
    Export markdown report to clipboard or file
    
    Args:
        reader: SimulationReader instance
        strategy_name: Strategy to report on
        dashboard: Parent window (not used but kept for compatibility)
    """
    try:
        import pyperclip
        md_content = generate_markdown_report(reader, strategy_name)
        pyperclip.copy(md_content)
        messagebox.showinfo("Success", 
                          f"Report copied to clipboard!\n({len(md_content)} characters)")
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


# ============================================================
# RISK ANALYSIS
# ============================================================

def show_risk_analysis(reader, strategy_name, dashboard):
    """
    Open comprehensive risk analysis window
    
    Uses RiskAnalyzerDB - NO MockTracker needed!
    """
    try:
        from risk_analysis import RiskAnalyzerDB
        
        # Create risk analyzer directly with reader
        analyzer = RiskAnalyzerDB(reader, strategy_name, benchmark='SPY')
        
        # Generate complete report
        report = analyzer.generate_report()
        
        # Create risk window
        risk_window = tk.Toplevel(dashboard)
        risk_window.title(f"🚨 Risk Analysis - {strategy_name}")
        risk_window.geometry("1200x800")
        
        # Create main frame
        main_frame = tk.Frame(risk_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, 
                text=f"🚨 Comprehensive Risk Analysis - {strategy_name}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
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
        
        # Risk assessment
        assessment = report.get('risk_assessment', {})
        report_text += f"📊 RISK ASSESSMENT:\n"
        report_text += f"  Severity: {assessment.get('severity', 'N/A')}\n"
        report_text += f"  Risk Score: {assessment.get('risk_score', 0)}/100\n"
        report_text += f"  Summary: {assessment.get('summary', 'N/A')}\n\n"
        
        # Warnings
        warnings = assessment.get('warnings', [])
        if warnings:
            report_text += f"⚠️  WARNINGS ({len(warnings)}):\n"
            for warning in warnings:
                report_text += f"\n  {warning.get('message', 'N/A')}\n"
                report_text += f"    Explanation: {warning.get('explanation', 'N/A')}\n"
                report_text += f"    Recommendation: {warning.get('recommendation', 'N/A')}\n"
            report_text += "\n"
        
        # Performance metrics
        report_text += f"📈 PERFORMANCE METRICS:\n"
        report_text += f"  Total Return: {report.get('total_return_pct', 0):+.2f}%\n"
        report_text += f"  Total Profit: ${report.get('total_profit_dollars', 0):+,.0f}\n"
        report_text += f"  Volatility: {report.get('volatility_annual_pct', 0):.2f}%\n"
        report_text += f"  Max Drawdown: {report.get('drawdown_analysis', {}).get('max_drawdown_pct', 0):.2f}%\n\n"
        
        # Performance ratios
        report_text += f"📊 PERFORMANCE RATIOS:\n"
        report_text += f"  Sharpe Ratio: {report.get('sharpe_ratio', 0):.3f}\n"
        report_text += f"  Sortino Ratio: {report.get('sortino_ratio', 0):.3f}\n"
        report_text += f"  Calmar Ratio: {report.get('calmar_ratio', 0):.3f}\n"
        report_text += f"  Omega Ratio: {report.get('omega_ratio', 0):.3f}\n\n"
        
        # Risk metrics
        report_text += f"📉 RISK METRICS:\n"
        report_text += f"  VaR (95%): {report.get('value_at_risk_95_pct', 0):.2f}%\n"
        report_text += f"  CVaR (95%): {report.get('conditional_var_95_pct', 0):.2f}%\n"
        report_text += f"  Downside Deviation: {report.get('downside_deviation_pct', 0):.2f}%\n\n"
        
        # Market exposure
        if report.get('beta') is not None:
            report_text += f"🎯 MARKET EXPOSURE:\n"
            report_text += f"  Beta: {report.get('beta', 0):.3f}\n"
            report_text += f"  Alpha: {report.get('alpha_pct', 0):+.2f}%\n"
            report_text += f"  Correlation: {report.get('correlation', 0):.3f}\n"
            report_text += f"  Information Ratio: {report.get('information_ratio', 0):.3f}\n\n"
        
        # Trade metrics
        trade_metrics = report.get('trade_metrics', {})
        if trade_metrics:
            report_text += f"💼 TRADE STATISTICS:\n"
            report_text += f"  Total Trades: {trade_metrics.get('total_trades', 0)}\n"
            report_text += f"  Win Rate: {trade_metrics.get('win_rate_pct', 0):.1f}%\n"
            report_text += f"  Profit Factor: {trade_metrics.get('profit_factor', 0):.2f}\n"
            report_text += f"  Risk/Reward: {trade_metrics.get('risk_reward_ratio', 0):.2f}:1\n"
            report_text += f"  Expectancy: ${trade_metrics.get('expectancy_dollars', 0):+,.0f}\n"
            report_text += f"  Max Win Streak: {trade_metrics.get('max_consecutive_wins', 0)}\n"
            report_text += f"  Max Loss Streak: {trade_metrics.get('max_consecutive_losses', 0)}\n\n"
        
        # Drawdown analysis
        dd = report.get('drawdown_analysis', {})
        if dd:
            report_text += f"📉 DRAWDOWN ANALYSIS:\n"
            report_text += f"  Max Drawdown: {dd.get('max_drawdown_pct', 0):.2f}%\n"
            report_text += f"  Max DD ($): ${dd.get('max_drawdown_dollars', 0):,.0f}\n"
            report_text += f"  Peak Date: {dd.get('peak_date', 'N/A')}\n"
            report_text += f"  Trough Date: {dd.get('trough_date', 'N/A')}\n"
            if dd.get('recovery_date'):
                report_text += f"  Recovery Date: {dd.get('recovery_date', 'N/A')}\n"
                report_text += f"  Recovery Days: {dd.get('recovery_days', 0)}\n"
            else:
                report_text += f"  Recovery: Not yet recovered\n"
            report_text += f"  Avg Drawdown: {dd.get('avg_drawdown_pct', 0):.2f}%\n"
            report_text += f"  # Drawdown Periods: {dd.get('num_drawdown_periods', 0)}\n\n"
        
        text_widget.insert(1.0, report_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=risk_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Risk analysis window opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Risk analysis error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open risk analysis:\n{e}")


# ============================================================
# STOCK DETAILS
# ============================================================

def show_stock_details(reader, strategy_name, dashboard):
    """
    Open stock detail viewer - shows per-symbol performance
    
    Uses database directly - NO MockTracker needed!
    """
    try:
        from stock_detail_viewer import show_stock_detail_window
        
        # Open stock detail window with reader
        show_stock_detail_window(reader, strategy_name)
        
        print(f"✅ Stock details window opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Stock details error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open stock details:\n{e}")


# ============================================================
# TRADE HISTORY
# ============================================================

def show_trade_history(reader, strategy_name, dashboard):
    """
    Open trade history viewer - complete trade table
    
    Uses database directly - NO MockTracker needed!
    """
    try:
        from trade_history_viewer import show_trade_history_window
        
        # Open trade history window with reader
        show_trade_history_window(reader, strategy_name)
        
        print(f"✅ Trade history window opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Trade history error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open trade history:\n{e}")


# ============================================================
# PORTFOLIO RISK
# ============================================================

def show_portfolio_risk(reader, strategy_name, dashboard):
    """
    Open portfolio-level risk analysis
    
    Uses PortfolioRiskAnalyzerDB - NO MockTracker needed!
    """
    try:
        from portfolio_risk_analyzer import PortfolioRiskAnalyzerDB
        
        # Get all strategies for portfolio analysis
        all_strategies = reader.list_strategies()
        
        if len(all_strategies) < 2:
            messagebox.showinfo("Portfolio Analysis", 
                              "Portfolio analysis requires at least 2 strategies.\n"
                              "Showing single-strategy analysis instead.")
            show_risk_analysis(reader, strategy_name, dashboard)
            return
        
        # Create portfolio analyzer
        analyzer = PortfolioRiskAnalyzerDB(reader, all_strategies, benchmark='SPY')
        
        # Generate report
        report = analyzer.generate_report()
        
        # Create portfolio risk window
        risk_window = tk.Toplevel(dashboard)
        risk_window.title(f"📈 Portfolio Risk Analysis")
        risk_window.geometry("1000x700")
        
        # Create main frame
        main_frame = tk.Frame(risk_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, text=f"📈 Portfolio Risk Analysis", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create text widget
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 9))
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Format report
        report_text = f"{'='*70}\n"
        report_text += f"PORTFOLIO RISK ANALYSIS\n"
        report_text += f"{'='*70}\n\n"
        
        # Portfolio metrics
        portfolio = report['portfolio_metrics']
        report_text += f"📊 PORTFOLIO PERFORMANCE:\n"
        report_text += f"  Total Return: {portfolio['return_pct']:+.2f}%\n"
        report_text += f"  Volatility: {portfolio['volatility_pct']:.2f}%\n"
        report_text += f"  Sharpe Ratio: {portfolio['sharpe_ratio']:.3f}\n"
        report_text += f"  Max Drawdown: {portfolio['max_drawdown_pct']:.2f}%\n"
        report_text += f"  Diversification Benefit: {portfolio['diversification_benefit_pct']:.2f}%\n\n"
        
        # Strategy weights
        report_text += f"⚖️ STRATEGY WEIGHTS:\n"
        for name, weight in report['strategy_weights'].items():
            report_text += f"  {name}: {weight*100:.1f}%\n"
        report_text += "\n"
        
        # Risk contributions
        report_text += f"🎯 RISK CONTRIBUTIONS:\n"
        for name, contrib in sorted(report['risk_contributions'].items(), 
                                   key=lambda x: x[1], reverse=True):
            report_text += f"  {name}: {contrib:.1f}%\n"
        report_text += "\n"
        
        # Correlation analysis
        corr = report['correlation_analysis']
        report_text += f"🔗 CORRELATION ANALYSIS:\n"
        report_text += f"  Average Correlation: {corr['average_correlation']:.3f}\n"
        report_text += f"  Diversification Score: {corr['diversification_score']:.1f}/100\n"
        
        if corr['high_correlation_pairs']:
            report_text += f"\n  ⚠️ HIGH CORRELATION PAIRS:\n"
            for pair in corr['high_correlation_pairs']:
                report_text += f"    {pair['strategy1']} ↔ {pair['strategy2']}: {pair['correlation']:.3f}\n"
        report_text += "\n"
        
        # Individual strategies
        report_text += f"📈 INDIVIDUAL STRATEGY PERFORMANCE:\n"
        report_text += f"  {'Strategy':<25} {'Return %':<12} {'Sharpe':<10} {'Max DD %':<12}\n"
        report_text += f"  {'-'*65}\n"
        
        individual = report['individual_strategy_metrics']
        for name, metrics in sorted(individual.items(), 
                                   key=lambda x: x[1]['return_pct'], 
                                   reverse=True):
            report_text += f"  {name:<25} "
            report_text += f"{metrics['return_pct']:>10.2f}% "
            report_text += f"{metrics['sharpe_ratio']:>10.3f} "
            report_text += f"{metrics['max_drawdown_pct']:>10.2f}%\n"
        
        text_widget.insert(1.0, report_text)
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


# ============================================================
# PERFORMANCE TIMELINE
# ============================================================

def show_performance_timeline(reader, strategy_name, dashboard):
    """
    Open performance timeline analysis
    
    Uses PerformanceTimelineDB - NO MockTracker needed!
    """
    try:
        from performance_timeline import PerformanceTimelineDB
        
        # Create timeline analyzer
        analyzer = PerformanceTimelineDB(reader, strategy_name, benchmark='SPY')
        
        # Get summary
        summary = analyzer.get_performance_summary()
        
        if not summary:
            messagebox.showwarning("No Data", "No timeline data available for this strategy")
            return
        
        # Create timeline window
        timeline_window = tk.Toplevel(dashboard)
        timeline_window.title(f"📅 Performance Timeline - {strategy_name}")
        timeline_window.geometry("1400x900")
        
        # Create matplotlib figure
        fig, axes = analyzer.create_timeline_chart()
        
        if fig is None:
            messagebox.showwarning("No Data", "Unable to create timeline chart")
            timeline_window.destroy()
            return
        
        # Embed in tkinter
        canvas_frame = tk.Frame(timeline_window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Summary stats panel
        stats_frame = tk.Frame(timeline_window, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=2)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        stats_text = (f"Total Return: {summary['total_return_strategy']:+.2f}% | "
                     f"Excess Return: {summary['excess_return']:+.2f}% | "
                     f"Days Outperformed: {summary['outperformance_pct']:.1f}% | "
                     f"Max Win Streak: {summary['max_win_streak_days']} days | "
                     f"Sudden Drops: {summary['sudden_drops']}")
        
        tk.Label(stats_frame, text=stats_text, bg='#e0e0e0', 
                font=('Arial', 9, 'bold')).pack(pady=5)
        
        # Close button
        tk.Button(timeline_window, text="❌ Close", command=timeline_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Performance timeline opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Timeline error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open timeline:\n{e}")


# ============================================================
# NEW ANALYSIS FUNCTIONS (USING NEW DATABASE FEATURES)
# ============================================================

def show_rejection_analysis(reader, strategy_name, dashboard):
    """
    Open rejection analysis window - shows why trades were rejected
    
    NEW FEATURE using trade_attempts table!
    """
    try:
        # Get rejection analysis from database
        rejection_stats = reader.get_rejection_analysis(strategy_name)
        
        if not rejection_stats:
            messagebox.showinfo("No Data", 
                              "No trade attempt data available.\n"
                              "This feature requires trade_attempts table.")
            return
        
        # Create rejection window
        rejection_window = tk.Toplevel(dashboard)
        rejection_window.title(f"🚫 Rejection Analysis - {strategy_name}")
        rejection_window.geometry("800x600")
        
        # Create main frame
        main_frame = tk.Frame(rejection_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, 
                text=f"🚫 Trade Rejection Analysis - {strategy_name}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create text widget
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10))
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Format report
        report_text = f"{'='*70}\n"
        report_text += f"TRADE REJECTION ANALYSIS\n"
        report_text += f"{'='*70}\n\n"
        
        report_text += f"📊 SUMMARY:\n"
        report_text += f"  Total Attempts: {rejection_stats['total_attempts']}\n"
        report_text += f"  Successful: {rejection_stats['successful']}\n"
        report_text += f"  Rejected: {rejection_stats['rejected']}\n"
        report_text += f"  Rejection Rate: {rejection_stats['rejection_rate_pct']:.1f}%\n\n"
        
        report_text += f"🚫 REJECTION REASONS:\n"
        reasons = rejection_stats['rejection_reasons']
        for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            report_text += f"  {reason}: {count} ({count/rejection_stats['rejected']*100:.1f}%)\n"
        
        report_text += f"\n💡 INTERPRETATION:\n"
        if rejection_stats['rejection_rate_pct'] > 50:
            report_text += f"  ⚠️ HIGH REJECTION RATE: Over half of trade signals are rejected.\n"
            report_text += f"  Consider adjusting strategy parameters or risk controls.\n"
        elif rejection_stats['rejection_rate_pct'] > 20:
            report_text += f"  ⚠️ MODERATE REJECTION RATE: Significant signals are being filtered.\n"
        else:
            report_text += f"  ✅ LOW REJECTION RATE: Most signals are being executed.\n"
        
        if rejection_stats['most_common_rejection']:
            report_text += f"\n  Most Common Rejection: {rejection_stats['most_common_rejection']}\n"
        
        text_widget.insert(1.0, report_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=rejection_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Rejection analysis opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Rejection analysis error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open rejection analysis:\n{e}")


def show_volume_analysis(reader, strategy_name, dashboard):
    """
    Open volume analysis window - shows impact of volume on performance
    
    NEW FEATURE using volume fields in trade_history!
    """
    try:
        # Get volume analysis from database
        volume_stats = reader.get_volume_analysis(strategy_name)
        
        if not volume_stats or volume_stats.get('trades_with_volume_data', 0) == 0:
            messagebox.showinfo("No Data", 
                              "No volume data available.\n"
                              "This feature requires volume fields in trade_history.")
            return
        
        # Create volume window
        volume_window = tk.Toplevel(dashboard)
        volume_window.title(f"📊 Volume Analysis - {strategy_name}")
        volume_window.geometry("800x600")
        
        # Create main frame
        main_frame = tk.Frame(volume_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        tk.Label(main_frame, 
                text=f"📊 Volume Impact Analysis - {strategy_name}", 
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Create text widget
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10))
        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Format report
        report_text = f"{'='*70}\n"
        report_text += f"VOLUME IMPACT ANALYSIS\n"
        report_text += f"{'='*70}\n\n"
        
        report_text += f"📊 VOLUME STATISTICS:\n"
        report_text += f"  Trades with Volume Data: {volume_stats['trades_with_volume_data']}\n"
        report_text += f"  Avg Entry Relative Volume: {volume_stats['avg_entry_volume']:.2f}x\n"
        
        if volume_stats['avg_exit_volume']:
            report_text += f"  Avg Exit Relative Volume: {volume_stats['avg_exit_volume']:.2f}x\n"
        
        report_text += f"  High Volume Trades (>2x): {volume_stats['high_volume_trades']}\n"
        report_text += f"  Low Volume Trades (<1x): {volume_stats['low_volume_trades']}\n\n"
        
        report_text += f"📈 PERFORMANCE BY VOLUME:\n"
        # Note: performance_by_volume structure depends on implementation
        report_text += f"  (See detailed breakdown in database query)\n\n"
        
        report_text += f"💡 INTERPRETATION:\n"
        if volume_stats['avg_entry_volume'] > 2.0:
            report_text += f"  ✅ HIGH ENTRY VOLUME: Strategy tends to enter on high volume.\n"
        elif volume_stats['avg_entry_volume'] < 0.8:
            report_text += f"  ⚠️ LOW ENTRY VOLUME: Strategy enters on low volume - may affect fills.\n"
        else:
            report_text += f"  ✅ NORMAL ENTRY VOLUME: Strategy enters on typical volume.\n"
        
        text_widget.insert(1.0, report_text)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(main_frame, text="❌ Close", command=volume_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=8).pack(pady=10)
        
        print(f"✅ Volume analysis opened for {strategy_name}")
        
    except Exception as e:
        print(f"❌ Volume analysis error: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Error", f"Failed to open volume analysis:\n{e}")