"""
Stock Detail Viewer - Individual stock performance analysis
Shows detailed metrics and trade history for each stock
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import numpy as np


def show_stock_detail_window(strategy, tracker, stock_data, symbols):
    """
    Show window with detailed performance for each stock
    """
    
    # Get stock performance summary
    stock_summary = tracker.get_stock_performance_summary()
    
    if not stock_summary:
        print("⚠️  No stock trades to display")
        return
    
    # Create new window
    detail_window = tk.Tk()
    detail_window.title(f"{strategy.name} - Stock Performance Details")
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
    
    # Sort stocks by P&L
    sorted_stocks = sorted(stock_summary.items(), 
                          key=lambda x: x[1]['pnl'], 
                          reverse=True)
    
    # Variable to track selected stock
    selected_stock = tk.StringVar()
    
    # Create radio buttons for each stock
    for symbol, stats in sorted_stocks:
        pnl_text = f"${stats['pnl']:+,.0f}"
        wr_text = f"{stats['win_rate']:.0f}%"
        
        # Color code based on performance
        bg_color = '#C8E6C9' if stats['pnl'] > 0 else '#FFCDD2'
        
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
            command=lambda s=symbol: show_stock_details(s, stock_summary, tracker, 
                                                         stock_data, right_panel)
        )
        radio.pack(fill=tk.X, padx=5, pady=2)
    
    # Select first stock by default
    if sorted_stocks:
        first_symbol = sorted_stocks[0][0]
        selected_stock.set(first_symbol)
        show_stock_details(first_symbol, stock_summary, tracker, stock_data, right_panel)
    
    # Summary stats at bottom
    summary_frame = tk.Frame(left_panel, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=2)
    summary_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)
    
    total_stocks = len(stock_summary)
    profitable = sum(1 for s in stock_summary.values() if s['pnl'] > 0)
    total_pnl = sum(s['pnl'] for s in stock_summary.values())
    
    tk.Label(summary_frame, text=f"Total Stocks: {total_stocks}", 
             bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(pady=2)
    tk.Label(summary_frame, text=f"Profitable: {profitable} ({profitable/total_stocks*100:.0f}%)", 
             bg='#e0e0e0', font=('Arial', 9)).pack(pady=2)
    tk.Label(summary_frame, text=f"Total P&L: ${total_pnl:+,.0f}", 
             bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(pady=2)
    
    detail_window.mainloop()


def show_stock_details(symbol, stock_summary, tracker, stock_data, parent_frame):
    """
    Display detailed analysis for a specific stock
    """
    
    # Clear previous content
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    stats = stock_summary[symbol]
    
    # Get trades for this stock
    symbol_trades = [t for t in tracker.trades if t['symbol'] == symbol]
    
    # Create matplotlib figure
    fig = plt.figure(figsize=(12, 8))
    fig.suptitle(f'{symbol} - Detailed Performance', fontsize=14, fontweight='bold')
    
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3, top=0.93, bottom=0.05)
    
    # 1. Stock price with entry/exit markers
    ax1 = fig.add_subplot(gs[0, :])
    
    if symbol in stock_data:
        stock_df = stock_data[symbol]
        ax1.plot(stock_df.index, stock_df['close'], color='blue', 
                linewidth=1.5, label=f'{symbol} Price')
        
        # Mark buys and sells
        buys = [t for t in symbol_trades if t['action'] == 'BUY']
        sells = [t for t in symbol_trades if t['action'] == 'SELL']
        
        if buys:
            buy_dates = [t['date'] for t in buys]
            buy_prices = [t['price'] for t in buys]
            ax1.scatter(buy_dates, buy_prices, marker='^', s=100, 
                       color='green', label='BUY', zorder=5)
        
        if sells:
            sell_dates = [t['date'] for t in sells]
            sell_prices = [t['price'] for t in sells]
            ax1.scatter(sell_dates, sell_prices, marker='v', s=100, 
                       color='red', label='SELL', zorder=5)
        
        ax1.set_title(f'Price Chart with Trade Markers', fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Price ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # 2. Performance metrics table
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.axis('off')
    
    metrics_data = [
        ['Performance Metrics', ''],
        ['Total Trades', f"{stats['num_trades']}"],
        ['Buys', f"{stats['num_buys']}"],
        ['Sells', f"{stats['num_sells']}"],
        ['', ''],
        ['Total Invested', f"${stats['total_invested']:,.0f}"],
        ['Total Returned', f"${stats['total_returned']:,.0f}"],
        ['Net P&L', f"${stats['pnl']:+,.0f}"],
        ['P&L %', f"{stats['pnl_pct']:+.1f}%"],
        ['', ''],
        ['Win Rate', f"{stats['win_rate']:.1f}%"],
        ['Wins', f"{stats['wins']}"],
        ['Losses', f"{stats['losses']}"],
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
    if stats['pnl'] > 0:
        table[(7, 1)].set_facecolor('#C8E6C9')
        table[(8, 1)].set_facecolor('#C8E6C9')
    else:
        table[(7, 1)].set_facecolor('#FFCDD2')
        table[(8, 1)].set_facecolor('#FFCDD2')
    
    # 3. Trade history table
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis('off')
    
    trade_data = [['Date', 'Action', 'Price', 'Shares']]
    
    for trade in symbol_trades[-10:]:  # Last 10 trades
        trade_data.append([
            trade['date'].strftime('%m-%d'),
            trade['action'],
            f"${trade['price']:.2f}",
            f"{trade['shares']:.2f}"
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
        
        # Color actions
        for row in range(1, len(trade_data)):
            if trade_data[row][1] == 'BUY':
                table2[(row, 1)].set_facecolor('#C8E6C9')
            else:
                table2[(row, 1)].set_facecolor('#FFCDD2')
    
    ax3.set_title('Recent Trades (Last 10)', fontweight='bold', fontsize=10)
    
    # 4. Trade returns distribution (bottom row)
    ax4 = fig.add_subplot(gs[2, :])
    
    # Calculate returns for each buy-sell pair
    trade_returns = []
    i = 0
    while i < len(symbol_trades) - 1:
        if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
            buy_price = symbol_trades[i]['price']
            sell_price = symbol_trades[i+1]['price']
            ret = (sell_price - buy_price) / buy_price * 100
            trade_returns.append(ret)
            i += 2
        else:
            i += 1
    
    if trade_returns:
        colors = ['#4CAF50' if r > 0 else '#F44336' for r in trade_returns]
        bars = ax4.bar(range(len(trade_returns)), trade_returns, color=colors, 
                      edgecolor='black', linewidth=1)
        
        ax4.axhline(0, color='black', linewidth=1.5)
        ax4.set_title(f'Trade Returns - {symbol}', fontweight='bold')
        ax4.set_xlabel('Trade Number')
        ax4.set_ylabel('Return (%)')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, trade_returns)):
            ax4.text(i, val, f'{val:+.1f}%',
                    ha='center', va='bottom' if val > 0 else 'top',
                    fontsize=8, fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'No completed trade pairs',
                ha='center', va='center', transform=ax4.transAxes)
    
    # Embed in tkinter
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)