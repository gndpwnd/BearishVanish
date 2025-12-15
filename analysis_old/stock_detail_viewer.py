"""
Stock Detail Viewer - REFACTORED FOR DATABASE
NO MockTracker dependency - works directly with SimulationReader

Shows detailed metrics and trade history for each stock
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import numpy as np


def show_stock_detail_window(reader, strategy_name):
    """
    Show window with detailed performance for each stock
    
    Args:
        reader: SimulationReader instance
        strategy_name: Strategy to analyze
    """
    
    # Get stock performance directly from database
    stock_performance = reader.get_stock_performance(strategy_name)
    
    if stock_performance.empty:
        print("⚠️  No stock trades to display")
        return
    
    # Create new window
    detail_window = tk.Tk()
    detail_window.title(f"{strategy_name} - Stock Performance Details")
    detail_window.geometry("1400x900")
    
    # Create main container
    main_container = tk.Frame(detail_window)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # Left panel: Stock list
    left_panel = tk.Frame(main_container, width=300, bg='#f0f0f0')
    left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
    
    tk.Label(left_panel, text="📊 Stocks Traded", 
             font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(pady=10)
    
    # Right panel: Detail view
    right_panel = tk.Frame(main_container)
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Create scrollable stock list
    list_frame = tk.Frame(left_panel, bg='white')
    list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Variable to track selected stock
    selected_stock = tk.StringVar()
    
    # Create radio buttons for each stock
    for _, row in stock_performance.iterrows():
        symbol = row['symbol']
        pnl = row['net_profit_loss']
        win_rate = row.get('win_rate_pct', 0)
        
        pnl_text = f"${pnl:+,.0f}"
        wr_text = f"{win_rate:.0f}%"
        
        # Color code based on performance
        bg_color = '#C8E6C9' if pnl > 0 else '#FFCDD2'
        
        radio_frame = tk.Frame(list_frame, bg=bg_color, relief=tk.RAISED, borderwidth=1)
        radio_frame.pack(fill=tk.X, padx=2, pady=1)
        
        radio = tk.Radiobutton(
            radio_frame,
            text=f"{symbol:6s} {pnl_text:>12s} WR:{wr_text:>5s}",
            variable=selected_stock,
            value=symbol,
            font=('Courier', 9),
            bg=bg_color,
            anchor='w',
            command=lambda s=symbol: show_stock_details(reader, strategy_name, s, right_panel)
        )
        radio.pack(fill=tk.X, padx=5, pady=2)
    
    # Select first stock by default
    if not stock_performance.empty:
        first_symbol = stock_performance.iloc[0]['symbol']
        selected_stock.set(first_symbol)
        show_stock_details(reader, strategy_name, first_symbol, right_panel)
    
    # Summary stats at bottom
    summary_frame = tk.Frame(left_panel, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=2)
    summary_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)
    
    total_stocks = len(stock_performance)
    profitable = len(stock_performance[stock_performance['net_profit_loss'] > 0])
    total_pnl = stock_performance['net_profit_loss'].sum()
    
    tk.Label(summary_frame, text=f"Total Stocks: {total_stocks}", 
             bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(pady=2)
    tk.Label(summary_frame, text=f"Profitable: {profitable} ({profitable/total_stocks*100:.0f}%)", 
             bg='#e0e0e0', font=('Arial', 9)).pack(pady=2)
    tk.Label(summary_frame, text=f"Total P&L: ${total_pnl:+,.0f}", 
             bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(pady=2)
    
    detail_window.mainloop()


def show_stock_details(reader, strategy_name, symbol, parent_frame):
    """
    Display detailed analysis for a specific stock
    
    Args:
        reader: SimulationReader instance
        strategy_name: Strategy name
        symbol: Stock symbol to analyze
        parent_frame: Tkinter frame to display in
    """
    
    # Clear previous content
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Get stock performance from database
    stock_perf = reader.get_stock_performance(strategy_name)
    stock_data = stock_perf[stock_perf['symbol'] == symbol]
    
    if stock_data.empty:
        tk.Label(parent_frame, text=f"No data for {symbol}",
                font=('Arial', 12)).pack(expand=True)
        return
    
    stats = stock_data.iloc[0]
    
    # Get trades for this stock
    symbol_trades = reader.get_trades_by_symbol(strategy_name, symbol)
    
    # Create matplotlib figure
    fig = plt.figure(figsize=(12, 8))
    fig.suptitle(f'{symbol} - Detailed Performance', fontsize=14, fontweight='bold')
    
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3, top=0.93, bottom=0.05)
    
    # 1. Trade timeline
    ax1 = fig.add_subplot(gs[0, :])
    
    if not symbol_trades.empty:
        # Plot entry/exit prices over time
        entries = symbol_trades[symbol_trades['entry_date'].notna()]
        exits = symbol_trades[symbol_trades['exit_date'].notna()]
        
        if not entries.empty:
            ax1.scatter(entries['entry_date'], entries['entry_price'], 
                       marker='^', s=100, color='green', label='Entry', zorder=5)
        
        if not exits.empty:
            ax1.scatter(exits['exit_date'], exits['exit_price'],
                       marker='v', s=100, color='red', label='Exit', zorder=5)
        
        # Connect entry/exit with lines
        for _, trade in symbol_trades.iterrows():
            if pd.notna(trade['exit_date']):
                ax1.plot([trade['entry_date'], trade['exit_date']],
                        [trade['entry_price'], trade['exit_price']],
                        'b--', alpha=0.3, linewidth=1)
        
        ax1.set_title(f'Trade Timeline', fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Price ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 2. Performance metrics table
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.axis('off')
    
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Trades', f"{stats['total_trades']}"],
        ['Winning Trades', f"{stats['winning_trades']}"],
        ['Losing Trades', f"{stats['losing_trades']}"],
        ['', ''],
        ['Net P&L', f"${stats['net_profit_loss']:+,.0f}"],
        ['Win Rate', f"{stats.get('win_rate_pct', 0):.1f}%"],
    ]
    
    table = ax2.table(cellText=metrics_data, cellLoc='left',
                     loc='center', colWidths=[0.60, 0.40])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    # Style header
    table[(0, 0)].set_facecolor('#1565C0')
    table[(0, 0)].set_text_props(weight='bold', color='white')
    table[(0, 1)].set_facecolor('#1565C0')
    
    # Color P&L
    if stats['net_profit_loss'] > 0:
        table[(5, 1)].set_facecolor('#C8E6C9')
    else:
        table[(5, 1)].set_facecolor('#FFCDD2')
    
    # 3. Trade history table
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis('off')
    
    trade_data = [['Date', 'Entry', 'Exit', 'P&L %']]
    
    # Show last 10 closed trades
    closed_trades = symbol_trades[symbol_trades['trade_status'] == 'CLOSED'].tail(10)
    
    for _, trade in closed_trades.iterrows():
        trade_data.append([
            trade['entry_date'].strftime('%m-%d') if pd.notna(trade['entry_date']) else '-',
            f"${trade['entry_price']:.2f}",
            f"${trade['exit_price']:.2f}" if pd.notna(trade['exit_price']) else '-',
            f"{trade.get('profit_loss_pct', 0):+.1f}%" if pd.notna(trade.get('profit_loss_pct')) else '-'
        ])
    
    if len(trade_data) > 1:
        table2 = ax3.table(cellText=trade_data, cellLoc='center',
                          loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
        table2.auto_set_font_size(False)
        table2.set_fontsize(8)
        table2.scale(1, 1.8)
        
        # Header
        for i in range(4):
            table2[(0, i)].set_facecolor('#1565C0')
            table2[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color P&L
        for row in range(1, len(trade_data)):
            pnl_str = trade_data[row][3]
            if '+' in pnl_str:
                table2[(row, 3)].set_facecolor('#C8E6C9')
            elif '-' in pnl_str:
                table2[(row, 3)].set_facecolor('#FFCDD2')
    
    ax3.set_title('Recent Closed Trades (Last 10)', fontweight='bold', fontsize=10)
    
    # 4. Trade returns distribution (bottom row)
    ax4 = fig.add_subplot(gs[2, :])
    
    # Calculate returns for closed trades
    closed = symbol_trades[symbol_trades['trade_status'] == 'CLOSED']
    
    if not closed.empty and 'profit_loss_pct' in closed.columns:
        returns = closed['profit_loss_pct'].dropna()
        
        if len(returns) > 0:
            colors = ['#4CAF50' if r > 0 else '#F44336' for r in returns]
            bars = ax4.bar(range(len(returns)), returns, color=colors, 
                          edgecolor='black', linewidth=1)
            
            ax4.axhline(0, color='black', linewidth=1.5)
            ax4.set_title(f'Trade Returns - {symbol}', fontweight='bold')
            ax4.set_xlabel('Trade Number')
            ax4.set_ylabel('Return (%)')
            ax4.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for i, (bar, val) in enumerate(zip(bars, returns)):
                height = bar.get_height()
                ax4.text(i, height + (1 if height > 0 else -1),
                        f'{val:+.1f}%',
                        ha='center', va='bottom' if height > 0 else 'top',
                        fontsize=8, fontweight='bold')
        else:
            ax4.text(0.5, 0.5, 'No completed trades',
                    ha='center', va='center', transform=ax4.transAxes)
    else:
        ax4.text(0.5, 0.5, 'No completed trades',
                ha='center', va='center', transform=ax4.transAxes)
    
    # Embed in tkinter
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_stock_performance(reader, strategy_name):
    """
    Convenience function to open stock detail viewer
    
    Usage:
        analyze_stock_performance(reader, 'My Strategy')
    """
    show_stock_detail_window(reader, strategy_name)