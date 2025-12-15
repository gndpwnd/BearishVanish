# ============================================================================
# FILE 2: visualizer/browser.py
# ============================================================================

"""
Analysis Database Browser
Select which analysis to visualize
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime


class AnalysisBrowser:
    """
    Browser for selecting analysis databases
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Analysis Browser")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f5f5f5')
        
        # Find analysis databases
        self.analysis_dir = Path('../analysis/analysis_dbs')
        self.databases = self._discover_databases()
        
        if not self.databases:
            self._show_no_databases()
        else:
            self._create_ui()
    
    def _discover_databases(self):
        """Find all analysis databases"""
        if not self.analysis_dir.exists():
            return []
        
        db_files = list(self.analysis_dir.glob('analysis_*.db'))
        
        databases = []
        for db_path in sorted(db_files, reverse=True):
            try:
                # Get metadata
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT key, value FROM analysis_metadata")
                metadata = dict(cursor.fetchall())
                
                cursor.execute("SELECT COUNT(*) FROM strategy_summary")
                num_strategies = cursor.fetchone()[0]
                
                conn.close()
                
                databases.append({
                    'path': db_path,
                    'name': db_path.name,
                    'size': db_path.stat().st_size / 1024,  # KB
                    'modified': datetime.fromtimestamp(db_path.stat().st_mtime),
                    'simulation_id': metadata.get('simulation_id', 'Unknown'),
                    'universe': metadata.get('universe', 'Unknown'),
                    'num_strategies': num_strategies,
                })
            except Exception as e:
                print(f"Error reading {db_path}: {e}")
        
        return databases
    
    def _show_no_databases(self):
        """Show message when no databases found"""
        frame = tk.Frame(self.root, bg='#f5f5f5')
        frame.pack(expand=True)
        
        tk.Label(
            frame,
            text="❌ No Analysis Databases Found",
            font=('Arial', 16, 'bold'),
            bg='#f5f5f5',
            fg='#d32f2f'
        ).pack(pady=20)
        
        tk.Label(
            frame,
            text="Please run the analysis engine first:\n\n"
                 "cd ../analysis\n"
                 "python analysis_engine.py --latest",
            font=('Courier', 11),
            bg='#f5f5f5',
            justify=tk.LEFT
        ).pack(pady=10)
        
        tk.Button(
            frame,
            text="🔄 Retry",
            command=self._retry,
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10
        ).pack(pady=20)
    
    def _retry(self):
        """Retry database discovery"""
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.databases = self._discover_databases()
        
        if not self.databases:
            self._show_no_databases()
        else:
            self._create_ui()
    
    def _create_ui(self):
        """Create browser UI"""
        # Header
        header = tk.Frame(self.root, bg='#1976D2', height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="📊 Analysis Browser",
            font=('Arial', 18, 'bold'),
            bg='#1976D2',
            fg='white'
        ).pack(side=tk.LEFT, padx=20, pady=20)
        
        tk.Label(
            header,
            text=f"Found {len(self.databases)} analysis databases",
            font=('Arial', 11),
            bg='#1976D2',
            fg='white'
        ).pack(side=tk.RIGHT, padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg='#f5f5f5')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Instructions
        tk.Label(
            content,
            text="Select an analysis to visualize:",
            font=('Arial', 12, 'bold'),
            bg='#f5f5f5'
        ).pack(anchor='w', pady=(0, 10))
        
        # Table frame
        table_frame = tk.Frame(content, bg='white', relief=tk.SUNKEN, bd=2)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        columns = ('name', 'strategies', 'universe', 'size', 'modified')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar.set,
            height=20
        )
        
        scrollbar.config(command=self.tree.yview)
        
        # Configure columns
        self.tree.heading('name', text='Analysis Database')
        self.tree.heading('strategies', text='Strategies')
        self.tree.heading('universe', text='Universe')
        self.tree.heading('size', text='Size (KB)')
        self.tree.heading('modified', text='Created')
        
        self.tree.column('name', width=350)
        self.tree.column('strategies', width=100, anchor='center')
        self.tree.column('universe', width=120, anchor='center')
        self.tree.column('size', width=100, anchor='e')
        self.tree.column('modified', width=180, anchor='center')
        
        # Style
        style = ttk.Style()
        style.configure('Treeview', rowheight=30, font=('Arial', 10))
        style.configure('Treeview.Heading', font=('Arial', 11, 'bold'))
        
        # Populate
        for db in self.databases:
            self.tree.insert('', tk.END, values=(
                db['name'],
                db['num_strategies'],
                db['universe'],
                f"{db['size']:.1f}",
                db['modified'].strftime('%Y-%m-%d %H:%M:%S')
            ), tags=(str(db['path']),))
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Double-click to open
        self.tree.bind('<Double-1>', lambda e: self._open_selected())
        
        # Button frame
        button_frame = tk.Frame(content, bg='#f5f5f5')
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(
            button_frame,
            text="📊 Open Dashboard",
            command=self._open_selected,
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10
        ).pack(side=tk.LEFT)
        
        tk.Button(
            button_frame,
            text="🔄 Refresh",
            command=self._retry,
            font=('Arial', 12),
            bg='#2196F3',
            fg='white',
            padx=20,
            pady=10
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            button_frame,
            text="❌ Close",
            command=self.root.destroy,
            font=('Arial', 12),
            bg='#f44336',
            fg='white',
            padx=20,
            pady=10
        ).pack(side=tk.RIGHT)
    
    def _open_selected(self):
        """Open selected analysis"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an analysis to open")
            return
        
        # Get path from tags
        item = self.tree.item(selection[0])
        db_path = Path(item['tags'][0])
        
        # Close browser
        self.root.destroy()
        
        # Open dashboard
        from dashboard import StrategyDashboard
        StrategyDashboard(db_path).run()
    
    def run(self):
        """Run the browser"""
        self.root.mainloop()
