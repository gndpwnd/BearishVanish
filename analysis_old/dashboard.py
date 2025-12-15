# File: dashboard.py

"""
Main Strategy Dashboard
All UI and button functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')  # CRITICAL: Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from datetime import datetime

from analysis_components import (
    create_portfolio_equity_chart,
    create_performance_metrics_table,
    create_trading_stats_table,
    create_returns_distribution,
    create_monthly_returns_chart,
    generate_markdown_report
)
from analysis_functions import (
    export_report,
    show_risk_analysis,
    show_stock_details,
    show_trade_history,
    show_portfolio_risk,
    show_performance_timeline
)
# REMOVED: from mock_trackers import MockTracker, MockStrategy  # This no longer exists


def show_strategy_dashboard(reader, strategy_name, all_strategies=None):
    """
    Show detailed strategy analysis dashboard with ALL buttons
    Properly integrates all analysis modules
    """
    try:
        # Create new window
        dashboard = tk.Tk()
        dashboard.title(f"{strategy_name} - Complete Performance Dashboard")
        dashboard.geometry("1800x1200")
        
        # Prevent window from closing immediately
        def on_closing():
            """Handle window close"""
            try:
                plt.close('all')
            except:
                pass
            dashboard.destroy()
        
        dashboard.protocol("WM_DELETE_WINDOW", on_closing)
        
        # ============================================================
        # STRATEGY SELECTOR
        # ============================================================
        if all_strategies and len(all_strategies) > 1:
            selector_frame = tk.Frame(dashboard, bg='#e3f2fd', height=60)
            selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
            
            tk.Label(
                selector_frame,
                text="📊 Select Strategy:",
                font=('Arial', 12, 'bold'),
                bg='#e3f2fd'
            ).pack(side=tk.LEFT, padx=10, pady=10)
            
            def switch_strategy(new_strategy):
                """Switch to different strategy"""
                dashboard.destroy()
                show_strategy_dashboard(reader, new_strategy, all_strategies)
            
            for strat in all_strategies:
                is_current = (strat == strategy_name)
                btn = tk.Button(
                    selector_frame,
                    text=strat,
                    font=('Arial', 10, 'bold' if is_current else 'normal'),
                    bg='#4CAF50' if is_current else '#90CAF9',
                    fg='white',
                    padx=15,
                    pady=8,
                    relief=tk.SUNKEN if is_current else tk.RAISED,
                    command=lambda s=strat: switch_strategy(s)
                )
                btn.pack(side=tk.LEFT, padx=3)
        
        # ============================================================
        # TOP BUTTON BAR - ALL ANALYSIS FEATURES (2 ROWS)
        # ============================================================
        button_frame = tk.Frame(dashboard, bg='#f0f0f0', height=120)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Title
        title_label = tk.Label(
            button_frame,
            text=f"📊 {strategy_name} - Complete Analysis Dashboard",
            font=('Arial', 14, 'bold'),
            bg='#f0f0f0'
        )
        title_label.pack(pady=5)
        
        # Create two rows of buttons
        button_row1 = tk.Frame(button_frame, bg='#f0f0f0')
        button_row1.pack(fill=tk.X, pady=2)
        
        button_row2 = tk.Frame(button_frame, bg='#f0f0f0')
        button_row2.pack(fill=tk.X, pady=2)
        
        # ============================================================
        # CREATE ALL BUTTONS (TWO ROWS)
        # ============================================================
        
        # ROW 1 BUTTONS
        tk.Button(
            button_row1,
            text="📋 Copy Report",
            command=lambda: export_report(reader, strategy_name, dashboard),
            bg='#90CAF9',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_row1,
            text="⚠️ Risk Analysis",
            command=lambda: show_risk_analysis(reader, strategy_name, dashboard),
            bg='#FFAB91',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_row1,
            text="📊 Stock Details",
            command=lambda: show_stock_details(reader, strategy_name, dashboard),
            bg='#FFE082',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_row1,
            text="📜 Trade History",
            command=lambda: show_trade_history(reader, strategy_name, dashboard),
            bg='#CE93D8',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        # ROW 2 BUTTONS
        tk.Button(
            button_row2,
            text="📈 Portfolio Risk",
            command=lambda: show_portfolio_risk(reader, strategy_name, dashboard),
            bg='#80DEEA',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_row2,
            text="📅 Timeline",
            command=lambda: show_performance_timeline(reader, strategy_name, dashboard),
            bg='#FFCC80',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_row2,
            text="❌ Close Dashboard",
            command=on_closing,
            bg='#FFCDD2',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.RIGHT, padx=3)
        
        # ============================================================
        # MAIN MATPLOTLIB FIGURE
        # ============================================================
        
        # Create matplotlib figure
        fig = plt.figure(figsize=(18, 14))
        fig.suptitle(f'{strategy_name} - Performance Analysis', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # Create grid
        gs = GridSpec(4, 4, figure=fig, hspace=0.4, wspace=0.4, 
                      top=0.95, bottom=0.03)
        
        print(f"Creating charts for {strategy_name}...")
        
        # DEBUG: Check if we have data
        portfolio = reader.get_portfolio_history(strategy_name)
        stats = reader.get_summary_stats(strategy_name)
        print(f"\n📊 DATA CHECK:")
        print(f"   Portfolio history rows: {len(portfolio)}")
        print(f"   Stats available: {bool(stats)}")
        if stats:
            print(f"   Total return: {stats['total_return_pct']:.2f}%")
            print(f"   Total trades: {stats['total_trades']}")
        
        if portfolio.empty:
            print("\n❌ NO PORTFOLIO DATA - Cannot create charts!")
            print("   This usually means the simulation didn't record daily snapshots")
            dashboard.destroy()
            return
        
        # Row 0: Portfolio equity + metrics
        try:
            create_portfolio_equity_chart(fig, gs[0, :3], reader, strategy_name, color='blue')
            print("  ✅ Portfolio chart created")
        except Exception as e:
            print(f"  ❌ Portfolio chart error: {e}")
        
        try:
            create_performance_metrics_table(fig, gs[0, 3], reader, strategy_name)
            print("  ✅ Metrics table created")
        except Exception as e:
            print(f"  ❌ Metrics table error: {e}")
        
        # Row 1: Trading stats + returns distribution
        try:
            create_trading_stats_table(fig, gs[1, :2], reader, strategy_name)
            print("  ✅ Trading stats created")
        except Exception as e:
            print(f"  ❌ Trading stats error: {e}")
        
        try:
            create_returns_distribution(fig, gs[1, 2:], reader, strategy_name)
            print("  ✅ Returns distribution created")
        except Exception as e:
            print(f"  ❌ Returns distribution error: {e}")
        
        # Row 2: Monthly returns (full width)
        try:
            create_monthly_returns_chart(fig, gs[2, :], reader, strategy_name)
            print("  ✅ Monthly returns created")
        except Exception as e:
            print(f"  ❌ Monthly returns error: {e}")
        
        # Row 3: Stock performance table
        ax_stocks = fig.add_subplot(gs[3, :])
        ax_stocks.axis('off')
        
        try:
            # Use the new direct database method for stock performance
            stock_perf = reader.get_stock_performance(strategy_name)
            
            if not stock_perf.empty:
                # Show top 10 stocks
                top_stocks = stock_perf.head(10)
                
                # Check what columns are available in the database
                columns_available = list(stock_perf.columns)
                print(f"  Available stock performance columns: {columns_available}")
                
                # Use available columns - adapt to what's in the database
                if 'symbol' in stock_perf.columns:
                    stock_data = [['Symbol', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate']]
                    for _, row in top_stocks.iterrows():
                        # Extract values with fallbacks if columns don't exist
                        symbol = row['symbol'] if 'symbol' in row else 'N/A'
                        num_trades = row.get('num_trades', row.get('total_trades', 'N/A'))
                        total_pnl = row.get('total_pnl', row.get('net_profit_loss', 0))
                        avg_pnl = row.get('avg_pnl', row.get('average_profit_loss', 0))
                        win_rate = row.get('win_rate', row.get('win_rate_pct', 'N/A'))
                        
                        stock_data.append([
                            symbol,
                            f"{int(num_trades)}" if isinstance(num_trades, (int, float)) else str(num_trades),
                            f"${total_pnl:+,.0f}" if isinstance(total_pnl, (int, float)) else str(total_pnl),
                            f"${avg_pnl:+,.0f}" if isinstance(avg_pnl, (int, float)) else str(avg_pnl),
                            f"{win_rate:.0f}%" if isinstance(win_rate, (int, float)) else str(win_rate)
                        ])
                    
                    table = ax_stocks.table(cellText=stock_data, cellLoc='center',
                                           loc='center', colWidths=[0.2, 0.2, 0.2, 0.2, 0.2])
                    table.auto_set_font_size(False)
                    table.set_fontsize(8)
                    table.scale(1, 2)
                    
                    # Header styling
                    for i in range(5):
                        table[(0, i)].set_facecolor('#1565C0')
                        table[(0, i)].set_text_props(weight='bold', color='white')
                    
                    ax_stocks.set_title('Top 10 Stock Performance', fontweight='bold', pad=15)
                    print("  ✅ Stock performance table created")
                else:
                    # If we don't have the expected columns, show a simplified view
                    ax_stocks.text(0.5, 0.5, f'Stock performance data available ({len(stock_perf)} stocks)', 
                                 ha='center', va='center', transform=ax_stocks.transAxes)
            else:
                ax_stocks.text(0.5, 0.5, 'No stock performance data', 
                             ha='center', va='center', transform=ax_stocks.transAxes)
        except Exception as e:
            print(f"  ❌ Stock performance error: {e}")
            import traceback
            traceback.print_exc()
            ax_stocks.text(0.5, 0.5, f'Error: {e}', 
                         ha='center', va='center', transform=ax_stocks.transAxes)
        
        # Embed matplotlib in tkinter
        canvas_frame = tk.Frame(dashboard)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        print(f"\n✅ Dashboard opened for: {strategy_name}")
        print("   Keep this terminal open - closing it will close the dashboard")
        
        # Start the GUI event loop
        dashboard.mainloop()
        
    except Exception as e:
        print(f"\n❌ Error creating dashboard: {e}")
        import traceback
        traceback.print_exc()