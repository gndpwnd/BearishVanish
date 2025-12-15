"""
Trade Details Window
Shows detailed trade history with filtering
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sqlite3

from simulation_reader import SimulationReader  # LOCAL IMPORT


class TradeDetailsWindow:
    """Window for showing detailed trade history"""
    
    def __init__(self, parent, strategy_name, analysis_db_path):
        self.parent = parent
        self.strategy_name = strategy_name
        self.analysis_db_path = analysis_db_path
        
        # Window
        self.window = tk.Toplevel(parent)
        self.window.title(f"📊 Trade Details - {strategy_name}")
        self.window.geometry("1400x800")
        
        # Get simulation DB path from analysis metadata
        self.sim_db_path = self._get_simulation_db_path()
        
        if not self.sim_db_path or not self.sim_db_path.exists():
            tk.Label(
                self.window,
                text="❌ Could not find source simulation database\n\n"
                     "The simulation database must be in:\n"
                     "../simulator/simulations/\n\n"
                     f"Looking for: {self.sim_db_path}",
                font=('Arial', 11),
                justify=tk.CENTER
            ).pack(pady=50)
            return
        
        try:
            self.reader = SimulationReader(self.sim_db_path)
            self._create_ui()
        except Exception as e:
            tk.Label(
                self.window,
                text=f"❌ Error loading simulation database:\n{str(e)}",
                font=('Arial', 11),
                fg='red'
            ).pack(pady=50)
    
    def _get_simulation_db_path(self):
        """Get path to source simulation database"""
        try:
            conn = sqlite3.connect(str(self.analysis_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM analysis_metadata WHERE key = 'source_simulation'")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                sim_name = row[0]
                # Try multiple possible locations
                possible_paths = [
                    Path(__file__).parent.parent / 'simulator' / 'simulations' / sim_name,
                    Path('../simulator/simulations') / sim_name,
                    Path('../../simulator/simulations') / sim_name,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        return path
                
                # Return first path even if doesn't exist (for error message)
                return possible_paths[0]
        except Exception as e:
            print(f"Error getting simulation path: {e}")
            return None
    
    def _create_ui(self):
        """Create UI"""
        # Header
        header = tk.Frame(self.window, bg='#1976D2', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text=f"📋 Trade History - {self.strategy_name}",
            font=('Arial', 16, 'bold'),
            bg='#1976D2',
            fg='white'
        ).pack(pady=15)
        
        # Filters
        filter_frame = tk.Frame(self.window, bg='#f0f0f0')
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(filter_frame, text="Status:", bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value='ALL')
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var,
                                     values=['ALL', 'CLOSED', 'OPEN'], width=10, state='readonly')
        status_combo.pack(side=tk.LEFT, padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self._load_trades())
        
        tk.Label(filter_frame, text="Min P&L %:", bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT, padx=20)
        self.min_pnl_var = tk.StringVar(value='')
        tk.Entry(filter_frame, textvariable=self.min_pnl_var, width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(filter_frame, text="🔍 Apply Filters", 
                 command=self._load_trades, bg='#4CAF50', fg='white',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=20)
        
        tk.Button(filter_frame, text="📥 Export CSV", 
                 command=self._export_csv, bg='#2196F3', fg='white',
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Table
        table_frame = tk.Frame(self.window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        v_scroll = tk.Scrollbar(table_frame)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scroll = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        columns = ('symbol', 'entry_date', 'exit_date', 'shares', 'entry_price', 
                   'exit_price', 'pnl_dollars', 'pnl_pct', 'hold_days', 'status')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                 yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        # Headers
        headers = {
            'symbol': ('Symbol', 80),
            'entry_date': ('Entry Date', 100),
            'exit_date': ('Exit Date', 100),
            'shares': ('Shares', 70),
            'entry_price': ('Entry $', 80),
            'exit_price': ('Exit $', 80),
            'pnl_dollars': ('P&L $', 100),
            'pnl_pct': ('P&L %', 80),
            'hold_days': ('Hold Days', 80),
            'status': ('Status', 80)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text, command=lambda c=col: self._sort_by_column(c))
            self.tree.column(col, width=width)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Style
        style = ttk.Style()
        style.configure('Treeview', rowheight=25, font=('Arial', 9))
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        
        # Load data
        self._load_trades()
        
        # Stats footer
        self.stats_label = tk.Label(self.window, text="", bg='#e3f2fd', 
                                    font=('Arial', 10, 'bold'), pady=10)
        self.stats_label.pack(fill=tk.X)
    
    def _load_trades(self):
        """Load and display trades"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # Get trades
            trades = self.reader.get_trade_history(self.strategy_name)
            
            if trades.empty:
                self.stats_label.config(text="No trades found", fg='orange')
                return
            
            # Apply filters
            status_filter = self.status_var.get()
            if status_filter != 'ALL':
                trades = trades[trades['trade_status'] == status_filter]
            
            min_pnl = self.min_pnl_var.get()
            if min_pnl:
                try:
                    min_pnl_val = float(min_pnl)
                    if 'profit_loss_pct' in trades.columns:
                        trades = trades[trades['profit_loss_pct'] >= min_pnl_val]
                except ValueError:
                    pass
            
            # Populate
            total_pnl = 0
            win_count = 0
            
            for _, row in trades.iterrows():
                pnl_dollars = row.get('profit_loss_dollars', 0) or 0
                pnl_pct = row.get('profit_loss_pct', 0) or 0
                
                if row['trade_status'] == 'CLOSED':
                    total_pnl += pnl_dollars
                    if pnl_dollars > 0:
                        win_count += 1
                
                # Format dates
                entry_date = row.get('entry_date', 'N/A')
                if hasattr(entry_date, 'strftime'):
                    entry_date = entry_date.strftime('%Y-%m-%d')
                
                exit_date = row.get('exit_date', 'N/A')
                if row['trade_status'] == 'CLOSED' and hasattr(exit_date, 'strftime'):
                    exit_date = exit_date.strftime('%Y-%m-%d')
                elif row['trade_status'] == 'OPEN':
                    exit_date = '--'
                
                values = (
                    row.get('symbol', 'N/A'),
                    str(entry_date),
                    str(exit_date),
                    f"{row.get('shares', 0):.0f}",
                    f"${row.get('entry_price', 0):.2f}",
                    f"${row.get('exit_price', 0):.2f}" if row['trade_status'] == 'CLOSED' else '--',
                    f"${pnl_dollars:+,.0f}" if row['trade_status'] == 'CLOSED' else '--',
                    f"{pnl_pct:+.2f}%" if row['trade_status'] == 'CLOSED' else '--',
                    f"{row.get('holding_days', 0):.0f}" if row['trade_status'] == 'CLOSED' else '--',
                    row['trade_status']
                )
                
                # Color code by P&L
                if row['trade_status'] == 'CLOSED':
                    tag = 'positive' if pnl_dollars > 0 else 'negative' if pnl_dollars < 0 else 'neutral'
                else:
                    tag = 'open'
                    
                self.tree.insert('', tk.END, values=values, tags=(tag,))
            
            # Configure tags
            self.tree.tag_configure('positive', background='#C8E6C9')
            self.tree.tag_configure('negative', background='#FFCDD2')
            self.tree.tag_configure('neutral', background='white')
            self.tree.tag_configure('open', background='#FFF9C4')
            
            # Update stats
            closed_trades = len(trades[trades['trade_status'] == 'CLOSED'])
            win_rate = (win_count / closed_trades * 100) if closed_trades > 0 else 0
            
            self.stats_label.config(
                text=f"📊 Total Trades: {len(trades)} | "
                     f"Closed: {closed_trades} | "
                     f"Open: {len(trades[trades['trade_status'] == 'OPEN'])} | "
                     f"Wins: {win_count} | "
                     f"Win Rate: {win_rate:.1f}% | "
                     f"Total P&L: ${total_pnl:+,.0f}",
                fg='black'
            )
            
        except Exception as e:
            self.stats_label.config(text=f"❌ Error loading trades: {str(e)}", fg='red')
            print(f"Error in _load_trades: {e}")
            import traceback
            traceback.print_exc()
    
    def _sort_by_column(self, col):
        """Sort table by column"""
        # Get all items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Sort
        try:
            # Try numeric sort
            items.sort(key=lambda t: float(t[0].replace('$', '').replace(',', '').replace('%', '').replace('--', '0')))
        except:
            # Fall back to string sort
            items.sort(key=lambda t: t[0])
        
        # Rearrange
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
    
    def _export_csv(self):
        """Export trades to CSV"""
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.strategy_name}_trades.csv"
        )
        
        if not filename:
            return
        
        try:
            trades = self.reader.get_trade_history(self.strategy_name)
            trades.to_csv(filename, index=False)
            
            from tkinter import messagebox
            messagebox.showinfo("Success", f"Exported {len(trades)} trades to:\n{filename}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to export:\n{str(e)}")
```

Now your visualizer app is completely independent! The file structure is:
```
BearishVanish/
├── simulator/
│   ├── simulations/          # Simulation databases
│   └── ...
├── analysis/
│   ├── analysis_dbs/         # Analysis databases
│   ├── analysis_engine.py
│   ├── db_reader.py          # Reads simulation DBs
│   └── ...
└── visualizer/
    ├── main.py
    ├── browser.py
    ├── dashboard.py
    ├── analysis_reader.py     # Reads analysis DBs
    ├── simulation_reader.py   # NEW: Reads simulation DBs (independent)
    └── trade_details_window.py