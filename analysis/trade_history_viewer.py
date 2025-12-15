"""
Trade History Viewer - REFACTORED FOR DATABASE
NO MockTracker dependency - works directly with SimulationReader

Shows complete trade history table with filtering
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd


def show_trade_history_window(reader, strategy_name):
    """
    Show window with complete trade history table
    
    Args:
        reader: SimulationReader instance
        strategy_name: Strategy to analyze
    """
    
    # Get trade history directly from database
    trade_df = reader.get_trade_history(strategy_name)
    
    if trade_df.empty:
        print("⚠️  No trades to display")
        messagebox.showinfo("No Trades", f"No trade history found for {strategy_name}")
        return
    
    # Create new window
    history_window = tk.Tk()
    history_window.title(f"{strategy_name} - Complete Trade History")
    history_window.geometry("1600x900")
    
    # Create main container
    main_frame = tk.Frame(history_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top control panel
    control_frame = tk.Frame(main_frame, bg='#f0f0f0', relief=tk.RAISED, borderwidth=2)
    control_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(control_frame, text="📜 Trade History", 
             font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(side=tk.LEFT, padx=10, pady=5)
    
    # Filter controls
    filter_frame = tk.Frame(control_frame, bg='#f0f0f0')
    filter_frame.pack(side=tk.LEFT, padx=20)
    
    tk.Label(filter_frame, text="Filter:", bg='#f0f0f0', 
             font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5)
    
    # Status filter
    status_var = tk.StringVar(value="ALL")
    tk.Label(filter_frame, text="Status:", bg='#f0f0f0').grid(row=0, column=1, padx=5)
    status_combo = ttk.Combobox(filter_frame, textvariable=status_var, 
                                values=["ALL", "OPEN", "CLOSED"], width=8, state='readonly')
    status_combo.grid(row=0, column=2, padx=5)
    
    # Symbol filter
    symbol_var = tk.StringVar(value="ALL")
    symbols = ["ALL"] + sorted(trade_df['symbol'].unique().tolist())
    
    tk.Label(filter_frame, text="Symbol:", bg='#f0f0f0').grid(row=0, column=3, padx=5)
    symbol_combo = ttk.Combobox(filter_frame, textvariable=symbol_var, 
                                values=symbols, width=10, state='readonly')
    symbol_combo.grid(row=0, column=4, padx=5)
    
    # Summary stats
    stats_frame = tk.Frame(control_frame, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=1)
    stats_frame.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def update_summary_stats(filtered_df):
        """Update summary statistics display"""
        for widget in stats_frame.winfo_children():
            widget.destroy()
        
        total = len(filtered_df)
        open_count = len(filtered_df[filtered_df['trade_status'] == 'OPEN'])
        closed_count = len(filtered_df[filtered_df['trade_status'] == 'CLOSED'])
        
        tk.Label(stats_frame, 
                text=f"Total: {total} | Open: {open_count} | Closed: {closed_count}", 
                bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(padx=10, pady=3)
    
    # Initial stats
    update_summary_stats(trade_df)
    
    # Create Treeview (table)
    tree_frame = tk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    
    # Scrollbars
    v_scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    h_scrollbar = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Define columns
    columns = ('id', 'symbol', 'status', 'entry_date', 'entry_price', 'shares', 
               'exit_date', 'exit_price', 'pnl_dollars', 'pnl_pct', 'holding_days')
    
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                       yscrollcommand=v_scrollbar.set,
                       xscrollcommand=h_scrollbar.set)
    
    v_scrollbar.config(command=tree.yview)
    h_scrollbar.config(command=tree.xview)
    
    # Configure column headings
    tree.heading('id', text='ID', command=lambda: sort_column('id'))
    tree.heading('symbol', text='Symbol', command=lambda: sort_column('symbol'))
    tree.heading('status', text='Status', command=lambda: sort_column('trade_status'))
    tree.heading('entry_date', text='Entry Date', command=lambda: sort_column('entry_date'))
    tree.heading('entry_price', text='Entry Price', command=lambda: sort_column('entry_price'))
    tree.heading('shares', text='Shares', command=lambda: sort_column('shares'))
    tree.heading('exit_date', text='Exit Date', command=lambda: sort_column('exit_date'))
    tree.heading('exit_price', text='Exit Price', command=lambda: sort_column('exit_price'))
    tree.heading('pnl_dollars', text='P&L ($)', command=lambda: sort_column('profit_loss_dollars'))
    tree.heading('pnl_pct', text='P&L %', command=lambda: sort_column('profit_loss_pct'))
    tree.heading('holding_days', text='Hold Days', command=lambda: sort_column('holding_days'))
    
    # Configure column widths
    tree.column('id', width=60, anchor='center')
    tree.column('symbol', width=80, anchor='center')
    tree.column('status', width=70, anchor='center')
    tree.column('entry_date', width=100, anchor='center')
    tree.column('entry_price', width=100, anchor='e')
    tree.column('shares', width=80, anchor='e')
    tree.column('exit_date', width=100, anchor='center')
    tree.column('exit_price', width=100, anchor='e')
    tree.column('pnl_dollars', width=120, anchor='e')
    tree.column('pnl_pct', width=100, anchor='e')
    tree.column('holding_days', width=80, anchor='center')
    
    tree.pack(fill=tk.BOTH, expand=True)
    
    # Configure tags for row colors
    tree.tag_configure('open', background='#FFF9C4')
    tree.tag_configure('closed_profit', background='#C8E6C9')
    tree.tag_configure('closed_loss', background='#FFCDD2')
    
    # Sort state
    sort_state = {'column': 'entry_date', 'reverse': True}
    
    def sort_column(col):
        """Sort table by column"""
        sort_state['reverse'] = not sort_state['reverse'] if sort_state['column'] == col else False
        sort_state['column'] = col
        populate_table()
    
    def populate_table():
        """Populate table with filtered and sorted data"""
        # Clear existing
        for item in tree.get_children():
            tree.delete(item)
        
        # Apply filters
        filtered_df = trade_df.copy()
        
        if status_var.get() != "ALL":
            filtered_df = filtered_df[filtered_df['trade_status'] == status_var.get()]
        
        if symbol_var.get() != "ALL":
            filtered_df = filtered_df[filtered_df['symbol'] == symbol_var.get()]
        
        # Sort
        if sort_state['column'] in filtered_df.columns:
            filtered_df = filtered_df.sort_values(
                by=sort_state['column'], 
                ascending=not sort_state['reverse']
            )
        
        # Insert rows
        for idx, row in filtered_df.iterrows():
            # Format values
            entry_date_str = row['entry_date'].strftime('%Y-%m-%d') if pd.notna(row['entry_date']) else '-'
            exit_date_str = row['exit_date'].strftime('%Y-%m-%d') if pd.notna(row['exit_date']) else '-'
            
            pnl_dollars = row.get('profit_loss_dollars', 0)
            pnl_pct = row.get('profit_loss_pct', 0)
            
            # Handle None values
            if pnl_dollars is None:
                pnl_dollars = 0
            if pnl_pct is None:
                pnl_pct = 0
            
            holding_days = row.get('holding_days', 0)
            if holding_days is None:
                holding_days = 0
            
            values = (
                int(row['id']) if 'id' in row else idx,
                row['symbol'],
                row['trade_status'],
                entry_date_str,
                f"${row['entry_price']:.2f}",
                f"{row['shares']:.2f}",
                exit_date_str,
                f"${row['exit_price']:.2f}" if pd.notna(row.get('exit_price')) else '-',
                f"${pnl_dollars:+,.2f}" if pnl_dollars != 0 else "-",
                f"{pnl_pct:+.1f}%" if pnl_pct != 0 else "-",
                f"{holding_days:.0f}" if holding_days > 0 else "-"
            )
            
            # Determine tags
            tags = []
            if row['trade_status'] == 'OPEN':
                tags.append('open')
            elif pnl_dollars > 0:
                tags.append('closed_profit')
            elif pnl_dollars < 0:
                tags.append('closed_loss')
            
            tree.insert('', tk.END, values=values, tags=tags)
        
        # Update summary
        update_summary_stats(filtered_df)
    
    # Bind filter changes
    status_combo.bind('<<ComboboxSelected>>', lambda e: populate_table())
    symbol_combo.bind('<<ComboboxSelected>>', lambda e: populate_table())
    
    # Initial population
    populate_table()
    
    # Button frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))
    
    def export_to_csv():
        """Export filtered data to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"trades_{strategy_name.replace(' ', '_')}.csv"
        )
        
        if filename:
            # Get current filtered data
            filtered_df = trade_df.copy()
            
            if status_var.get() != "ALL":
                filtered_df = filtered_df[filtered_df['trade_status'] == status_var.get()]
            
            if symbol_var.get() != "ALL":
                filtered_df = filtered_df[filtered_df['symbol'] == symbol_var.get()]
            
            filtered_df.to_csv(filename, index=False)
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(filtered_df)} trades to:\n{filename}")
    
    def show_trade_details():
        """Show detailed info for selected trade"""
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a trade to view details")
            return
        
        # Get trade ID from selection
        item = tree.item(selection[0])
        trade_id = item['values'][0]
        
        # Get full trade details
        trade = trade_df[trade_df['id'] == trade_id].iloc[0]
        
        # Create detail window
        detail_window = tk.Toplevel(history_window)
        detail_window.title(f"Trade Details - {trade['symbol']}")
        detail_window.geometry("600x700")
        
        # Create text widget with scrollbar
        text_frame = tk.Frame(detail_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                      font=('Courier', 9))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        
        # Format trade details
        details = f"""
{'='*60}
TRADE DETAILS
{'='*60}

BASIC INFO:
  Trade ID: {trade['id']}
  Symbol: {trade['symbol']}
  Status: {trade['trade_status']}

ENTRY:
  Date: {trade['entry_date']}
  Price: ${trade['entry_price']:.2f}
  Shares: {trade['shares']:.2f}
  Volume: {trade.get('entry_volume', 'N/A')}
  Relative Volume: {trade.get('entry_relative_volume', 'N/A')}
  Portfolio Value: ${trade.get('entry_portfolio_value', 0):,.2f}
  Cash Available: ${trade.get('entry_cash', 0):,.2f}
  Open Positions: {trade.get('entry_num_positions', 0)}

EXIT:
  Date: {trade['exit_date'] if pd.notna(trade.get('exit_date')) else 'Still Open'}
  Price: ${trade['exit_price']:.2f if pd.notna(trade.get('exit_price')) else 0}
  Volume: {trade.get('exit_volume', 'N/A')}
  Relative Volume: {trade.get('exit_relative_volume', 'N/A')}
  Portfolio Value: ${trade.get('exit_portfolio_value', 0):,.2f}
  Cash Available: ${trade.get('exit_cash', 0):,.2f}

PERFORMANCE:
  P&L Dollars: ${trade.get('profit_loss_dollars', 0):+,.2f}
  P&L Percent: {trade.get('profit_loss_pct', 0):+.2f}%
  Holding Days: {trade.get('holding_days', 0):.1f}
  Holding Bars: {trade.get('holding_bars', 0)}

METADATA:
  Entry Reason: {trade.get('entry_reason', 'N/A')}
  Exit Reason: {trade.get('exit_reason', 'N/A')}
  Forced Exit: {trade.get('forced_exit', False)}

{'='*60}
        """
        
        text.insert(1.0, details)
        text.config(state=tk.DISABLED)
        
        tk.Button(detail_window, text="Close", command=detail_window.destroy,
                 bg='#FFCDD2', font=('Arial', 10, 'bold')).pack(pady=10)
    
    # Buttons
    tk.Button(button_frame, text="📥 Export to CSV", command=export_to_csv,
              bg='#81C784', font=('Arial', 10, 'bold'), padx=15, pady=5).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_frame, text="🔍 View Details", command=show_trade_details,
              bg='#90CAF9', font=('Arial', 10, 'bold'), padx=15, pady=5).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_frame, text="❌ Close", command=history_window.destroy,
              bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=5).pack(side=tk.RIGHT, padx=5)
    
    # Instructions label
    tk.Label(button_frame, text="💡 Click column headers to sort | Use filters to narrow results | Double-click row for details",
             font=('Arial', 9, 'italic'), fg='#666').pack(side=tk.LEFT, padx=20)
    
    # Bind double-click to show details
    tree.bind('<Double-1>', lambda e: show_trade_details())
    
    history_window.mainloop()


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_trade_history(reader, strategy_name):
    """
    Convenience function to open trade history viewer
    
    Usage:
        analyze_trade_history(reader, 'My Strategy')
    """
    show_trade_history_window(reader, strategy_name)