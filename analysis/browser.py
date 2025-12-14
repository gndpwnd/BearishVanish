"""
Simulation Browser GUI
For selecting which simulation to analyze
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from db_reader import SimulationReader
from dashboard import show_strategy_dashboard

SIMULATIONS_DIR = Path('../simulator/simulations')


class SimulationBrowser:
    """
    GUI browser for selecting simulations to analyze
    Pure database reading - no simulator dependencies
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Simulation Analysis Browser")
        self.root.geometry("1200x700")
        
        # Discover all simulations
        self.simulations = self._discover_simulations()
        
        if not self.simulations:
            self._show_no_simulations()
            return
        
        self._create_ui()
    
    def _discover_simulations(self):
        """Find all simulation databases"""
        if not SIMULATIONS_DIR.exists():
            print(f"❌ Simulations directory not found: {SIMULATIONS_DIR}")
            return []
        
        db_files = list(SIMULATIONS_DIR.glob('simulation_*.db'))
        
        simulations = []
        for db_path in sorted(db_files, reverse=True):  # Most recent first
            try:
                reader = SimulationReader(db_path)
                
                simulations.append({
                    'db_path': db_path,
                    'sim_id': reader.get_simulation_id(),
                    'universe': reader.get_universe(),
                    'num_symbols': reader.get_num_symbols(),
                    'date_range': f"{reader.get_date_range()['start']} to {reader.get_date_range()['end']}",
                    'num_strategies': len(reader.list_strategies())
                })
                
                reader.close()
            except Exception as e:
                print(f"Error reading {db_path}: {e}")
        
        return simulations
    
    def _show_no_simulations(self):
        """Show message when no simulations found"""
        label = tk.Label(
            self.root,
            text="❌ No simulations found\n\nRun simulator first:\ncd ../simulator && python main.py --universe sp500",
            font=('Arial', 14),
            fg='red'
        )
        label.pack(expand=True)
        
        # Add retry button
        tk.Button(self.root, text="🔄 Retry", command=self._retry_discovery,
                 font=('Arial', 12), bg='#4CAF50', fg='white').pack(pady=20)
    
    def _retry_discovery(self):
        """Retry discovering simulations"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.simulations = self._discover_simulations()
        
        if not self.simulations:
            self._show_no_simulations()
        else:
            self._create_ui()
    
    def _create_ui(self):
        """Create the browser UI"""
        # Header
        header = tk.Frame(self.root, bg='#2196F3', height=60)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text="📊 Simulation Analysis Browser",
            font=('Arial', 16, 'bold'),
            bg='#2196F3',
            fg='white'
        ).pack(pady=15)
        
        # Info label
        info_label = tk.Label(
            self.root,
            text=f"Found {len(self.simulations)} simulation(s) - Select one to analyze",
            font=('Arial', 10)
        )
        info_label.pack(pady=10)
        
        # Create table
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        columns = ('Database', 'Universe', 'Symbols', 'Period', 'Strategies')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar.set
        )
        
        scrollbar.config(command=self.tree.yview)
        
        # Configure columns
        self.tree.heading('Database', text='Database File')
        self.tree.heading('Universe', text='Universe')
        self.tree.heading('Symbols', text='Symbols')
        self.tree.heading('Period', text='Date Range')
        self.tree.heading('Strategies', text='Strategies')
        
        self.tree.column('Database', width=200)
        self.tree.column('Universe', width=100)
        self.tree.column('Symbols', width=80)
        self.tree.column('Period', width=250)
        self.tree.column('Strategies', width=100)
        
        # Populate table
        for sim in self.simulations:
            self.tree.insert('', tk.END, values=(
                sim['db_path'].name,
                sim['universe'],
                sim['num_symbols'],
                sim['date_range'],
                sim['num_strategies']
            ), tags=(str(sim['db_path']),))
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click
        self.tree.bind('<Double-1>', self._on_select)
        
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            button_frame,
            text="📊 Analyze Selected",
            command=self._analyze_selected,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=10
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="🔄 Refresh",
            command=self._retry_discovery,
            bg='#2196F3',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=10
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Close",
            command=self.root.destroy,
            bg='#F44336',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=10
        ).pack(side=tk.RIGHT, padx=5)
    
    def _on_select(self, event):
        """Handle double-click"""
        self._analyze_selected()
    
    def _analyze_selected(self):
        """Open analysis for selected simulation"""
        selection = self.tree.selection()
        
        if not selection:
            return
        
        # Get database path from tags
        item = self.tree.item(selection[0])
        db_path = Path(item['tags'][0])
        
        # Open analysis window
        self._open_simulation_analysis(db_path)
    
    def _open_simulation_analysis(self, db_path):
        """Open full analysis for a simulation"""
        print(f"\n{'='*70}")
        print(f"ANALYZING: {db_path.name}")
        print(f"{'='*70}\n")
        
        # Open database reader
        reader = SimulationReader(db_path)
        
        # Get strategies
        strategies = reader.list_strategies()
        
        print(f"📊 Found {len(strategies)} strategies:")
        for strat in strategies:
            print(f"   - {strat}")
        
        # Create strategy selection window
        self._create_strategy_viewer(reader, strategies)
    
    def _create_strategy_viewer(self, reader, strategies):
        """Create window to select and analyze strategies"""
        viewer = tk.Toplevel(self.root)
        viewer.title(f"Strategies - {reader.db_path.name}")
        viewer.geometry("1000x600")
        
        # Header
        header = tk.Frame(viewer, bg='#4CAF50', height=50)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text=f"📊 {reader.db_path.name}",
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',
            fg='white'
        ).pack(pady=10)
        
        # Create table
        table_frame = tk.Frame(viewer)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Strategy', 'Return %', 'Profit', 'Win Rate', 'Sharpe', 'Max DD')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        tree.heading('Strategy', text='Strategy')
        tree.heading('Return %', text='Return %')
        tree.heading('Profit', text='Profit ($)')
        tree.heading('Win Rate', text='Win Rate')
        tree.heading('Sharpe', text='Sharpe')
        tree.heading('Max DD', text='Max DD %')
        
        # Get comparison data
        comparison = reader.compare_strategies()
        
        if not comparison.empty:
            for _, row in comparison.iterrows():
                tree.insert('', tk.END, values=(
                    row['strategy_name'],
                    f"{row.get('total_return_pct', 0):+.2f}%",
                    f"${row.get('total_profit_dollars', 0):+,.0f}",
                    f"{row.get('win_rate_pct', 0):.1f}%",
                    f"{row.get('sharpe_ratio', 0):.3f}",
                    f"{row.get('max_drawdown_pct', 0):.2f}%"
                ))
        else:
            # Fallback if comparison table doesn't have all columns
            for strat in strategies:
                stats = reader.get_summary_stats(strat)
                if stats:
                    tree.insert('', tk.END, values=(
                        strat,
                        f"{stats.get('total_return_pct', 0):+.2f}%",
                        f"${stats.get('total_profit_dollars', 0):+,.0f}",
                        f"{stats.get('win_rate_pct', 0):.1f}%",
                        f"{stats.get('sharpe_ratio', 0):.3f}",
                        f"{stats.get('max_drawdown_pct', 0):.2f}%"
                    ))
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = tk.Frame(viewer)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def analyze_strategy():
            selection = tree.selection()
            if not selection:
                return
            
            item = tree.item(selection[0])
            strategy_name = item['values'][0]
            
            # Close the browser and strategy viewer
            viewer.destroy()
            self.root.destroy()
            
            # Open detailed analysis in main window
            show_strategy_dashboard(reader, strategy_name, all_strategies=strategies)
        
        tk.Button(
            button_frame,
            text="📊 Detailed Analysis",
            command=analyze_strategy,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Close",
            command=viewer.destroy,
            bg='#F44336',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=15,
            pady=8
        ).pack(side=tk.RIGHT, padx=5)
    
    def run(self):
        """Run the browser"""
        self.root.mainloop()