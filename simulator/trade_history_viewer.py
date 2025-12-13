"""
Trade History Viewer - FIXED VERSION
Fixes: Tkinter anchor error, improved layout, accurate data display
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd


def show_trade_history_window(strategy, tracker, sim_id=None):
    """
    Show window with complete trade history table
    FIXED: Uses correct Tkinter anchors and telemetry data if available
    """
    
    if not tracker.trades:
        print("⚠️  No trades to display")
        return
    
    # Create new window
    history_window = tk.Tk()
    history_window.title(f"{strategy.name} - Complete Trade History")
    history_window.geometry("1500x900")
    
    # Create main container
    main_frame = tk.Frame(history_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Top control panel
    control_frame = tk.Frame(main_frame, bg='#f0f0f0', relief=tk.RAISED, borderwidth=2)
    control_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(control_frame, text="📜 Trade History", 
             font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(side=tk.LEFT, padx=10, pady=5)
    
    # Try to get telemetry data if available
    try:
        from simulation_telemetry import telemetry
        if sim_id:
            trade_df = telemetry.get_trade_history(sim_id, strategy.name, status=None)
            if not trade_df.empty:
                print(f"✅ Loaded {len(trade_df)} trades from telemetry")
            else:
                # Fallback to tracker data
                trade_df = tracker.get_trade_history_dataframe()
        else:
            trade_df = tracker.get_trade_history_dataframe()
    except:
        # Fallback to tracker data
        trade_df = tracker.get_trade_history_dataframe()
    
    # Filter controls
    filter_frame = tk.Frame(control_frame, bg='#f0f0f0')
    filter_frame.pack(side=tk.LEFT, padx=20)
    
    tk.Label(filter_frame, text="Filter:", bg='#f0f0f0', 
             font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5)
    
    # Action filter
    action_var = tk.StringVar(value="ALL")
    tk.Label(filter_frame, text="Action:", bg='#f0f0f0').grid(row=0, column=1, padx=5)
    action_combo = ttk.Combobox(filter_frame, textvariable=action_var, 
                                values=["ALL", "BUY", "SELL"], width=8, state='readonly')
    action_combo.grid(row=0, column=2, padx=5)
    
    # Symbol filter
    symbol_var = tk.StringVar(value="ALL")
    
    # Get unique symbols
    if 'symbol' in trade_df.columns:
        symbols = ["ALL"] + sorted(trade_df['symbol'].unique().tolist())
    else:
        symbols = ["ALL"]
    
    tk.Label(filter_frame, text="Symbol:", bg='#f0f0f0').grid(row=0, column=3, padx=5)
    symbol_combo = ttk.Combobox(filter_frame, textvariable=symbol_var, 
                                values=symbols, width=10, state='readonly')
    symbol_combo.grid(row=0, column=4, padx=5)
    
    # Summary stats
    stats_frame = tk.Frame(control_frame, bg='#e0e0e0', relief=tk.SUNKEN, borderwidth=1)
    stats_frame.pack(side=tk.RIGHT, padx=10, pady=5)
    
    # Calculate stats
    if 'action' in trade_df.columns:
        total_trades = len(trade_df)
        total_buys = len(trade_df[trade_df['action'] == 'BUY'])
        total_sells = len(trade_df[trade_df['action'] == 'SELL'])
    else:
        total_trades = len(trade_df)
        total_buys = 0
        total_sells = 0
    
    tk.Label(stats_frame, text=f"Total: {total_trades} | Buys: {total_buys} | Sells: {total_sells}", 
             bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(padx=10, pady=3)
    
    # Create Treeview (table)
    tree_frame = tk.Frame(main_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    
    # Scrollbars
    v_scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    h_scrollbar = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Define columns
    columns = ('date', 'symbol', 'action', 'price', 'shares', 'amount', 'pnl', 'pnl_pct')
    
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                       yscrollcommand=v_scrollbar.set,
                       xscrollcommand=h_scrollbar.set)
    
    v_scrollbar.config(command=tree.yview)
    h_scrollbar.config(command=tree.xview)
    
    # Configure column headings
    tree.heading('date', text='Date', command=lambda: sort_column('date'))
    tree.heading('symbol', text='Symbol', command=lambda: sort_column('symbol'))
    tree.heading('action', text='Action', command=lambda: sort_column('action'))
    tree.heading('price', text='Price', command=lambda: sort_column('price'))
    tree.heading('shares', text='Shares', command=lambda: sort_column('shares'))
    tree.heading('amount', text='Amount', command=lambda: sort_column('amount'))
    tree.heading('pnl', text='P&L', command=lambda: sort_column('pnl'))
    tree.heading('pnl_pct', text='P&L %', command=lambda: sort_column('pnl_pct'))
    
    # FIXED: Use 'e' instead of 'right' for east alignment
    tree.column('date', width=100, anchor='center')
    tree.column('symbol', width=80, anchor='center')
    tree.column('action', width=70, anchor='center')
    tree.column('price', width=100, anchor='e')  # FIXED: 'e' = east = right
    tree.column('shares', width=100, anchor='e')
    tree.column('amount', width=120, anchor='e')
    tree.column('pnl', width=120, anchor='e')
    tree.column('pnl_pct', width=100, anchor='e')
    
    tree.pack(fill=tk.BOTH, expand=True)
    
    # Configure tags for row colors
    tree.tag_configure('buy', background='#C8E6C9')
    tree.tag_configure('sell', background='#FFCDD2')
    tree.tag_configure('profit', foreground='#1B5E20')
    tree.tag_configure('loss', foreground='#B71C1C')
    
    # Sort state
    sort_state = {'column': 'date', 'reverse': True}
    
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
        
        if 'action' in filtered_df.columns and action_var.get() != "ALL":
            filtered_df = filtered_df[filtered_df['action'] == action_var.get()]
        
        if 'symbol' in filtered_df.columns and symbol_var.get() != "ALL":
            filtered_df = filtered_df[filtered_df['symbol'] == symbol_var.get()]
        
        # Sort
        if sort_state['column'] in filtered_df.columns:
            filtered_df = filtered_df.sort_values(
                by=sort_state['column'], 
                ascending=not sort_state['reverse']
            )
        
        # Insert rows
        for idx, row in filtered_df.iterrows():
            # Handle both old and new column names
            date_col = 'entry_date' if 'entry_date' in row else 'date'
            symbol_col = 'symbol' if 'symbol' in row else ''
            action_col = 'action' if 'action' in row else ''
            price_col = 'entry_price' if 'entry_price' in row else 'price'
            shares_col = 'shares'
            
            date_str = row[date_col].strftime('%Y-%m-%d %H:%M') if hasattr(row[date_col], 'strftime') else str(row[date_col])
            
            # Calculate amount
            if 'amount' in row:
                amount = row['amount']
            elif price_col in row and shares_col in row:
                amount = row[price_col] * row[shares_col]
            else:
                amount = 0
            
            # Get P&L
            if 'profit_loss_dollars' in row:
                pnl = row['profit_loss_dollars']
                pnl_pct = row['profit_loss_pct']
            elif 'pnl' in row:
                pnl = row['pnl']
                pnl_pct = row['pnl_pct']
            else:
                pnl = 0
                pnl_pct = 0
            
            values = (
                date_str,
                row[symbol_col] if symbol_col in row else '',
                row[action_col] if action_col in row else '',
                f"${row[price_col]:.2f}" if price_col in row else '-',
                f"{row[shares_col]:.2f}" if shares_col in row else '-',
                f"${amount:,.2f}",
                f"${pnl:+,.2f}" if pnl != 0 else "-",
                f"{pnl_pct:+.1f}%" if pnl_pct != 0 else "-"
            )
            
            # Determine tags
            tags = []
            if action_col in row:
                if row[action_col] == 'BUY':
                    tags.append('buy')
                else:
                    tags.append('sell')
            
            if pnl > 0:
                tags.append('profit')
            elif pnl < 0:
                tags.append('loss')
            
            tree.insert('', tk.END, values=values, tags=tags)
        
        # Update summary
        total = len(filtered_df)
        if 'action' in filtered_df.columns:
            buys = len(filtered_df[filtered_df['action'] == 'BUY'])
            sells = len(filtered_df[filtered_df['action'] == 'SELL'])
        else:
            buys = 0
            sells = 0
        
        for widget in stats_frame.winfo_children():
            widget.destroy()
        
        tk.Label(stats_frame, 
                text=f"Showing: {total} trades | Buys: {buys} | Sells: {sells}", 
                bg='#e0e0e0', font=('Arial', 9, 'bold')).pack(padx=10, pady=3)
    
    # Bind filter changes
    action_combo.bind('<<ComboboxSelected>>', lambda e: populate_table())
    symbol_combo.bind('<<ComboboxSelected>>', lambda e: populate_table())
    
    # Initial population
    populate_table()
    
    # Export button
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))
    
    def export_to_csv():
        """Export filtered data to CSV"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"trades_{strategy.name.replace(' ', '_')}.csv"
        )
        
        if filename:
            # Get current filtered data
            filtered_df = trade_df.copy()
            
            if 'action' in filtered_df.columns and action_var.get() != "ALL":
                filtered_df = filtered_df[filtered_df['action'] == action_var.get()]
            
            if 'symbol' in filtered_df.columns and symbol_var.get() != "ALL":
                filtered_df = filtered_df[filtered_df['symbol'] == symbol_var.get()]
            
            filtered_df.to_csv(filename, index=False)
            print(f"\n✅ Exported {len(filtered_df)} trades to: {filename}")
    
    tk.Button(button_frame, text="📥 Export to CSV", command=export_to_csv,
              bg='#81C784', font=('Arial', 10, 'bold'), padx=15, pady=5).pack(side=tk.LEFT, padx=5)
    
    tk.Button(button_frame, text="❌ Close", command=history_window.destroy,
              bg='#FFCDD2', font=('Arial', 10, 'bold'), padx=15, pady=5).pack(side=tk.RIGHT, padx=5)
    
    # Instructions label
    tk.Label(button_frame, text="💡 Click column headers to sort | Use filters to narrow results",
             font=('Arial', 9, 'italic'), fg='#666').pack(side=tk.LEFT, padx=20)
    
    history_window.mainloop()