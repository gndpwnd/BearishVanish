# ============================================================================
# FILE 4: visualizer/dashboard.py
# ============================================================================

"""
Strategy Dashboard
Main visualization window with layout-safe design
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from analysis_reader import AnalysisReader


class StrategyDashboard:
    """
    Main dashboard for visualizing strategy performance
    Layout-safe design with no overlapping elements
    """
    
    def __init__(self, db_path):
        """
        Initialize dashboard
        
        Args:
            db_path: Path to analysis database
        """
        self.reader = AnalysisReader(db_path)
        self.strategies = self.reader.get_strategies()
        self.current_strategy = self.strategies[0] if self.strategies else None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"📊 Strategy Dashboard - {db_path.name}")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f5f5f5')
        
        # Data caching for performance
        self._data_cache = {}
        self._chart_cache = {}
        
        # Prevent window resizing issues
        self.root.update_idletasks()
        
        self._create_ui()
    
    def _get_cached_data(self, data_type, strategy_name):
        """Get data from cache or load it"""
        cache_key = f"{strategy_name}_{data_type}"
        
        if cache_key not in self._data_cache:
            # Load on demand
            try:
                if data_type == 'summary':
                    self._data_cache[cache_key] = self.reader.get_summary(strategy_name)
                elif data_type == 'monthly':
                    self._data_cache[cache_key] = self.reader.get_monthly_returns(strategy_name)
                elif data_type == 'distribution':
                    self._data_cache[cache_key] = self.reader.get_returns_distribution(strategy_name)
                elif data_type == 'stock_perf':
                    self._data_cache[cache_key] = self.reader.get_stock_performance(strategy_name)
                elif data_type == 'drawdown':
                    self._data_cache[cache_key] = self.reader.get_drawdown_periods(strategy_name)
            except Exception as e:
                print(f"Error loading {data_type} for {strategy_name}: {e}")
                self._data_cache[cache_key] = None
        
        return self._data_cache.get(cache_key)
    
    def _create_ui(self):
        """Create main UI with proper layout"""
        # =====================================================================
        # HEADER BAR (Fixed height)
        # =====================================================================
        header = tk.Frame(self.root, bg='#1976D2', height=60)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)  # Prevent shrinking
        
        tk.Label(
            header,
            text="📊 Strategy Performance Dashboard",
            font=('Arial', 16, 'bold'),
            bg='#1976D2',
            fg='white'
        ).pack(side=tk.LEFT, padx=20, pady=15)
        
        # Metadata
        metadata = self.reader.get_metadata()
        info_text = f"Simulation: {metadata.get('simulation_id', 'N/A')} | Universe: {metadata.get('universe', 'N/A')}"
        
        tk.Label(
            header,
            text=info_text,
            font=('Arial', 10),
            bg='#1976D2',
            fg='white'
        ).pack(side=tk.RIGHT, padx=20)
        
        # =====================================================================
        # STRATEGY SELECTOR BAR (Fixed height)
        # =====================================================================
        selector = tk.Frame(self.root, bg='#E3F2FD', height=50)
        selector.pack(side=tk.TOP, fill=tk.X)
        selector.pack_propagate(False)
        
        tk.Label(
            selector,
            text="Strategy:",
            font=('Arial', 11, 'bold'),
            bg='#E3F2FD'
        ).pack(side=tk.LEFT, padx=10)
        
        self.strategy_var = tk.StringVar(value=self.current_strategy)
        
        strategy_combo = ttk.Combobox(
            selector,
            textvariable=self.strategy_var,
            values=self.strategies,
            state='readonly',
            width=30,
            font=('Arial', 10)
        )
        strategy_combo.pack(side=tk.LEFT, padx=5, pady=10)
        strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_changed)
        
        # Quick stats
        self.quick_stats_label = tk.Label(
            selector,
            text="",
            font=('Arial', 10),
            bg='#E3F2FD'
        )
        self.quick_stats_label.pack(side=tk.LEFT, padx=20)
        
        # =====================================================================
        # BUTTON BAR (Fixed height)
        # =====================================================================
        button_bar = tk.Frame(self.root, bg='#f0f0f0', height=50)
        button_bar.pack(side=tk.TOP, fill=tk.X)
        button_bar.pack_propagate(False)
        
        buttons = [
            ("📋 Export Report", self._export_report, '#90CAF9'),
            ("📊 Trade Details", self._show_trade_details, '#FFE082'),
            ("📈 Risk Analysis", self._show_risk_analysis, '#FFAB91'),
            ("🔄 Compare Strategies", self._compare_strategies, '#CE93D8'),
        ]
        
        for text, command, color in buttons:
            tk.Button(
                button_bar,
                text=text,
                command=command,
                font=('Arial', 10, 'bold'),
                bg=color,
                padx=15,
                pady=5
            ).pack(side=tk.LEFT, padx=5, pady=10)
        
        tk.Button(
            button_bar,
            text="❌ Close",
            command=self.root.destroy,
            font=('Arial', 10, 'bold'),
            bg='#FFCDD2',
            padx=15,
            pady=5
        ).pack(side=tk.RIGHT, padx=10, pady=10)
        
        # =====================================================================
        # MAIN CONTENT AREA (Scrollable)
        # =====================================================================
        
        # Create canvas for scrolling
        canvas_frame = tk.Frame(self.root, bg='#f5f5f5')
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg='#f5f5f5', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=canvas.yview)
        
        self.scrollable_frame = tk.Frame(canvas, bg='#f5f5f5')
        
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # =====================================================================
        # LOAD DASHBOARD CONTENT
        # =====================================================================
        self._load_dashboard()
    
    def _load_dashboard(self):
        """Load dashboard content for current strategy"""
        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.current_strategy:
            tk.Label(
                self.scrollable_frame,
                text="No strategy selected",
                font=('Arial', 14),
                bg='#f5f5f5'
            ).pack(pady=50)
            return
        
        # Show loading indicator
        loading = tk.Label(
            self.scrollable_frame,
            text="⏳ Loading strategy data...",
            font=('Arial', 14, 'bold'),
            bg='#f5f5f5'
        )
        loading.pack(pady=50)
        self.root.update()
        
        # Get data
        summary = self._get_cached_data('summary', self.current_strategy)
        
        if not summary:
            loading.config(text="❌ No data available for this strategy")
            return
        
        loading.destroy()
        
        # Update quick stats
        self.quick_stats_label.config(
            text=f"Return: {summary.get('total_return_pct', 0):+.2f}% | "
                 f"Win Rate: {summary.get('win_rate_pct', 0):.1f}% | "
                 f"Sharpe: {summary.get('sharpe_ratio', 0):.3f}"
        )
        
        # =====================================================================
        # SECTION 1: KEY METRICS (Fixed height)
        # =====================================================================
        metrics_section = tk.Frame(self.scrollable_frame, bg='white', relief=tk.RAISED, bd=2)
        metrics_section.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            metrics_section,
            text="📊 Key Performance Metrics",
            font=('Arial', 13, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=10)
        
        self._create_metrics_grid(metrics_section, summary)
        
        # =====================================================================
        # SECTION 2: CHARTS (Fixed sizes)
        # =====================================================================
        
        # Row 1: Equity curve + Performance table
        row1 = tk.Frame(self.scrollable_frame, bg='#f5f5f5')
        row1.pack(fill=tk.X, pady=(0, 10))
        
        equity_frame = tk.Frame(row1, bg='white', relief=tk.RAISED, bd=2, width=1000, height=400)
        equity_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        equity_frame.pack_propagate(False)
        
        performance_frame = tk.Frame(row1, bg='white', relief=tk.RAISED, bd=2, width=500, height=400)
        performance_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        performance_frame.pack_propagate(False)
        
        self._create_equity_chart(equity_frame)
        self._create_performance_table(performance_frame, summary)
        
        # Row 2: Returns histogram + Monthly returns
        row2 = tk.Frame(self.scrollable_frame, bg='#f5f5f5')
        row2.pack(fill=tk.X, pady=(0, 10))
        
        histogram_frame = tk.Frame(row2, bg='white', relief=tk.RAISED, bd=2, width=750, height=350)
        histogram_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        histogram_frame.pack_propagate(False)
        
        monthly_frame = tk.Frame(row2, bg='white', relief=tk.RAISED, bd=2, width=750, height=350)
        monthly_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        monthly_frame.pack_propagate(False)
        
        self._create_returns_histogram(histogram_frame)
        self._create_monthly_returns(monthly_frame)
        
        # Row 3: Benchmark comparison
        row3 = tk.Frame(self.scrollable_frame, bg='#f5f5f5')
        row3.pack(fill=tk.X, pady=(0, 10))
        
        benchmark_frame = tk.Frame(row3, bg='white', relief=tk.RAISED, bd=2, height=350)
        benchmark_frame.pack(fill=tk.BOTH, expand=True)
        benchmark_frame.pack_propagate(False)
        
        self._create_benchmark_comparison(benchmark_frame)
        
        # Row 4: Drawdown analysis
        row4 = tk.Frame(self.scrollable_frame, bg='#f5f5f5')
        row4.pack(fill=tk.X, pady=(0, 10))
        
        drawdown_frame = tk.Frame(row4, bg='white', relief=tk.RAISED, bd=2, height=350)
        drawdown_frame.pack(fill=tk.BOTH, expand=True)
        drawdown_frame.pack_propagate(False)
        
        self._create_drawdown_chart(drawdown_frame)
        
        # Row 5: Stock performance table
        row5 = tk.Frame(self.scrollable_frame, bg='#f5f5f5')
        row5.pack(fill=tk.X, pady=(0, 10))
        
        stock_frame = tk.Frame(row5, bg='white', relief=tk.RAISED, bd=2, height=300)
        stock_frame.pack(fill=tk.BOTH, expand=True)
        stock_frame.pack_propagate(False)
        
        self._create_stock_performance_table(stock_frame)
        
        # Force update
        self.root.update()
    
    def _create_metrics_grid(self, parent, summary):
        """Create metrics grid with cards"""
        grid = tk.Frame(parent, bg='white')
        grid.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        metrics = [
            ("Total Return", f"{summary.get('total_return_pct', 0):+.2f}%", 
             '#4CAF50' if summary.get('total_return_pct', 0) > 0 else '#f44336'),
            ("Total Profit", f"${summary.get('total_profit_dollars', 0):+,.0f}", 
             '#4CAF50' if summary.get('total_profit_dollars', 0) > 0 else '#f44336'),
            ("Sharpe Ratio", f"{summary.get('sharpe_ratio', 0):.3f}", '#2196F3'),
            ("Win Rate", f"{summary.get('win_rate_pct', 0):.1f}%", '#9C27B0'),
            ("Max Drawdown", f"{summary.get('max_drawdown_pct', 0):.2f}%", '#FF9800'),
            ("Profit Factor", f"{summary.get('profit_factor', 0):.2f}", '#00BCD4'),
            ("Completed Trades", f"{summary.get('completed_trades', 0)}", '#607D8B'),
            ("Avg Hold", f"{summary.get('avg_hold_days', 0):.1f} days", '#795548'),
        ]
        
        for i, (label, value, color) in enumerate(metrics):
            row = i // 4
            col = i % 4
            
            card = tk.Frame(grid, bg=color, width=180, height=80, relief=tk.RAISED, bd=2)
            card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            card.grid_propagate(False)
            
            tk.Label(
                card,
                text=label,
                font=('Arial', 9, 'bold'),
                bg=color,
                fg='white'
            ).pack(pady=(10, 0))
            
            tk.Label(
                card,
                text=value,
                font=('Arial', 14, 'bold'),
                bg=color,
                fg='white'
            ).pack()
        
        # Configure grid weights
        for i in range(4):
            grid.columnconfigure(i, weight=1)
    
    def _create_equity_chart(self, parent):
        """Create equity curve chart with proper error handling"""
        tk.Label(
            parent,
            text="Portfolio Equity Curve",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=5)
        
        # Get chart data
        chart_data = self.reader.get_chart_data(self.current_strategy, 'equity_curve')
        
        if not chart_data or 'dates' not in chart_data or 'values' not in chart_data:
            tk.Label(
                parent,
                text="⚠️ No equity curve data available\n\nThis chart is pre-computed by the analysis engine.\nPlease re-run: python analysis_engine.py --latest",
                font=('Arial', 10),
                bg='white',
                fg='#666',
                justify=tk.CENTER
            ).pack(expand=True)
            return
        
        try:
            # Create figure
            fig = Figure(figsize=(10, 3.5), facecolor='white')
            ax = fig.add_subplot(111)
            
            dates = chart_data['dates']
            values = chart_data['values']
            initial_cash = chart_data.get('initial_cash', values[0] if values else 100000)
            
            # Plot
            ax.plot(dates, values, color='#2196F3', linewidth=2.5, label='Portfolio Value')
            ax.axhline(initial_cash, color='gray', linestyle=':', linewidth=1.5, 
                      alpha=0.7, label='Initial Capital')
            
            # Fill areas
            ax.fill_between(range(len(values)), initial_cash, values,
                            where=[v > initial_cash for v in values],
                            color='#4CAF50', alpha=0.2)
            ax.fill_between(range(len(values)), initial_cash, values,
                            where=[v <= initial_cash for v in values],
                            color='#f44336', alpha=0.2)
            
            ax.set_xlabel('Date', fontsize=10, fontweight='bold')
            ax.set_ylabel('Portfolio Value ($)', fontsize=10, fontweight='bold')
            ax.legend(fontsize=9, loc='best')
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Format x-axis
            step = max(1, len(dates) // 10)
            ax.set_xticks(range(0, len(dates), step))
            ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], 
                              rotation=45, ha='right', fontsize=8)
            
            # Format y-axis with commas
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            fig.tight_layout()
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        except Exception as e:
            tk.Label(
                parent,
                text=f"❌ Error creating chart: {str(e)}",
                font=('Arial', 10),
                bg='white',
                fg='red'
            ).pack(expand=True)
            print(f"Error in _create_equity_chart: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_performance_table(self, parent, summary):
        """Create performance metrics table"""
        tk.Label(
            parent,
            text="Performance Details",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=10)
        
        # Create scrollable frame
        canvas = tk.Canvas(parent, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        
        table_frame = tk.Frame(canvas, bg='white')
        table_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        canvas.create_window((0, 0), window=table_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Data
        data = [
            ("RETURNS", ""),
            ("Total Return", f"{summary.get('total_return_pct', 0):+.2f}%"),
            ("Annualized Return", f"{summary.get('annualized_return_pct', 0):+.2f}%"),
            ("Total Profit", f"${summary.get('total_profit_dollars', 0):+,.0f}"),
            ("", ""),
            ("RISK METRICS", ""),
            ("Sharpe Ratio", f"{summary.get('sharpe_ratio', 0):.3f}"),
            ("Sortino Ratio", f"{summary.get('sortino_ratio', 0):.3f}"),
            ("Calmar Ratio", f"{summary.get('calmar_ratio', 0):.3f}"),
            ("Max Drawdown", f"{summary.get('max_drawdown_pct', 0):.2f}%"),
            ("Volatility", f"{summary.get('volatility_annual_pct', 0):.2f}%"),
            ("", ""),
            ("TRADE STATS", ""),
            ("Win Rate", f"{summary.get('win_rate_pct', 0):.1f}%"),
            ("Profit Factor", f"{summary.get('profit_factor', 0):.2f}"),
            ("Avg Win", f"${summary.get('avg_win_dollars', 0):,.0f}"),
            ("Avg Loss", f"${summary.get('avg_loss_dollars', 0):,.0f}"),
            ("Risk/Reward", f"{summary.get('risk_reward_ratio', 0):.2f}:1"),
        ]
        
        for i, (label, value) in enumerate(data):
            if value == "":
                # Section header
                tk.Label(
                    table_frame,
                    text=label,
                    font=('Arial', 10, 'bold'),
                    bg='#E3F2FD',
                    anchor='w'
                ).grid(row=i, column=0, columnspan=2, sticky='ew', pady=2)
            else:
                tk.Label(
                    table_frame,
                    text=label,
                    font=('Arial', 9),
                    bg='white',
                    anchor='w'
                ).grid(row=i, column=0, sticky='w', padx=10, pady=2)
                
                tk.Label(
                    table_frame,
                    text=value,
                    font=('Arial', 9, 'bold'),
                    bg='white',
                    anchor='e'
                ).grid(row=i, column=1, sticky='e', padx=10, pady=2)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_returns_histogram(self, parent):
        """Create returns distribution histogram"""
        tk.Label(
            parent,
            text="Trade Returns Distribution",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=5)
        
        dist = self._get_cached_data('distribution', self.current_strategy)
        
        if dist is None or dist.empty:
            tk.Label(parent, text="⚠️ No distribution data", 
                    font=('Arial', 10), bg='white', fg='#666').pack(expand=True)
            return
        
        try:
            fig = Figure(figsize=(7, 3), facecolor='white')
            ax = fig.add_subplot(111)
            
            # Calculate bin centers - ensure numeric types
            bin_centers = pd.to_numeric((dist['bin_start'] + dist['bin_end']) / 2, errors='coerce')
            counts = pd.to_numeric(dist['count'], errors='coerce')
            
            # Drop any NaN values
            valid_mask = ~(bin_centers.isna() | counts.isna())
            bin_centers = bin_centers[valid_mask]
            counts = counts[valid_mask]
            
            if len(bin_centers) == 0:
                raise ValueError("No valid data after type conversion")
            
            # Color by positive/negative
            colors = ['#f44336' if c < 0 else '#4CAF50' for c in bin_centers]
            
            # Plot
            ax.bar(bin_centers, counts, width=4, color=colors, edgecolor='black', linewidth=0.5)
            ax.axvline(0, color='black', linestyle='--', linewidth=1, alpha=0.7)
            
            ax.set_xlabel('Return (%)', fontsize=9, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=9, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y', linestyle='--')
            ax.tick_params(labelsize=8)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        except Exception as e:
            tk.Label(parent, text=f"❌ Error: {str(e)}", 
                    font=('Arial', 9), bg='white', fg='red').pack(expand=True)
            print(f"Error in _create_returns_histogram: {e}")
    
    def _create_monthly_returns(self, parent):
        """Create monthly returns bar chart"""
        tk.Label(
            parent,
            text="Monthly Returns",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=5)
        
        monthly = self._get_cached_data('monthly', self.current_strategy)
        
        if monthly is None or monthly.empty:
            tk.Label(parent, text="⚠️ No monthly data", 
                    font=('Arial', 10), bg='white', fg='#666').pack(expand=True)
            return
        
        try:
            fig = Figure(figsize=(7, 3), facecolor='white')
            ax = fig.add_subplot(111)
            
            # Plot
            colors = ['#4CAF50' if r > 0 else '#f44336' for r in monthly['return_pct']]
            bars = ax.bar(range(len(monthly)), monthly['return_pct'], 
                         color=colors, edgecolor='black', linewidth=0.5)
            
            ax.axhline(0, color='black', linewidth=1)
            ax.set_xlabel('Month', fontsize=9, fontweight='bold')
            ax.set_ylabel('Return (%)', fontsize=9, fontweight='bold')
            ax.set_xticks(range(len(monthly)))
            ax.set_xticklabels(monthly['year_month'], rotation=45, ha='right', fontsize=7)
            ax.grid(True, alpha=0.3, axis='y', linestyle='--')
            ax.tick_params(labelsize=8)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        except Exception as e:
            tk.Label(parent, text=f"❌ Error: {str(e)}", 
                    font=('Arial', 9), bg='white', fg='red').pack(expand=True)
            print(f"Error in _create_monthly_returns: {e}")
    
    def _create_benchmark_comparison(self, parent):
        """Create portfolio vs SPY comparison chart"""
        tk.Label(
            parent,
            text="Strategy vs S&P 500 Performance",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=5)
        
        # Get portfolio equity data
        portfolio_data = self.reader.get_chart_data(self.current_strategy, 'equity_curve')
        
        if not portfolio_data or 'values' not in portfolio_data:
            tk.Label(parent, text="⚠️ No portfolio data available", 
                    font=('Arial', 10), bg='white', fg='#666').pack(expand=True)
            return
        
        try:
            fig = Figure(figsize=(14, 3.5), facecolor='white')
            ax = fig.add_subplot(111)
            
            # Normalize to percentage returns for comparison
            portfolio_values = np.array(portfolio_data['values'])
            portfolio_initial = portfolio_values[0]
            portfolio_returns = (portfolio_values / portfolio_initial - 1) * 100
            
            dates = portfolio_data.get('dates', list(range(len(portfolio_returns))))
            
            # Plot portfolio
            ax.plot(portfolio_returns, label=self.current_strategy, 
                    color='#2196F3', linewidth=2.5)
            
            # Try to get SPY data
            spy_data = self.reader.get_chart_data('SPY', 'equity_curve')
            
            if spy_data and 'values' in spy_data:
                spy_values = np.array(spy_data['values'])
                spy_initial = spy_values[0]
                spy_returns = (spy_values / spy_initial - 1) * 100
                
                # Align lengths
                min_len = min(len(portfolio_returns), len(spy_returns))
                ax.plot(spy_returns[:min_len], label='S&P 500 (SPY)', 
                        color='#FF9800', linewidth=2.5, alpha=0.7)
            else:
                # Add note that SPY not available
                ax.text(0.02, 0.98, "⚠️ SPY benchmark not available in analysis", 
                       transform=ax.transAxes, fontsize=9, 
                       verticalalignment='top', color='#666')
            
            ax.axhline(0, color='black', linestyle=':', linewidth=1, alpha=0.5)
            ax.set_xlabel('Trading Days', fontsize=10, fontweight='bold')
            ax.set_ylabel('Return (%)', fontsize=10, fontweight='bold')
            ax.legend(fontsize=10, loc='best')
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Format x-axis
            step = max(1, len(dates) // 15)
            ax.set_xticks(range(0, len(dates), step))
            if isinstance(dates[0], str):
                ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], 
                                  rotation=45, ha='right', fontsize=8)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        except Exception as e:
            tk.Label(parent, text=f"❌ Error: {str(e)}", 
                    font=('Arial', 9), bg='white', fg='red').pack(expand=True)
            print(f"Error in _create_benchmark_comparison: {e}")
    
    def _create_drawdown_chart(self, parent):
        """Create drawdown chart"""
        tk.Label(
            parent,
            text="Drawdown Over Time",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=5)
        
        chart_data = self.reader.get_chart_data(self.current_strategy, 'drawdown_curve')
        
        if not chart_data or 'drawdowns' not in chart_data:
            tk.Label(parent, text="⚠️ No drawdown data available", 
                    font=('Arial', 10), bg='white', fg='#666').pack(expand=True)
            return
        
        try:
            fig = Figure(figsize=(14, 3), facecolor='white')
            ax = fig.add_subplot(111)
            
            dates = chart_data.get('dates', [])
            drawdowns = chart_data['drawdowns']
            
            ax.fill_between(range(len(drawdowns)), 0, drawdowns, color='#f44336', alpha=0.3)
            ax.plot(drawdowns, color='#d32f2f', linewidth=1.5)
            ax.axhline(0, color='black', linewidth=1, linestyle='-')
            
            ax.set_xlabel('Date', fontsize=9, fontweight='bold')
            ax.set_ylabel('Drawdown (%)', fontsize=9, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Format x-axis
            if dates:
                step = max(1, len(dates) // 15)
                ax.set_xticks(range(0, len(dates), step))
                ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], 
                                  rotation=45, ha='right', fontsize=8)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        except Exception as e:
            tk.Label(parent, text=f"❌ Error: {str(e)}", 
                    font=('Arial', 9), bg='white', fg='red').pack(expand=True)
            print(f"Error in _create_drawdown_chart: {e}")
    
    def _create_stock_performance_table(self, parent):
        """Create stock performance table"""
        tk.Label(
            parent,
            text="Top/Bottom Stock Performance",
            font=('Arial', 12, 'bold'),
            bg='white'
        ).pack(anchor='w', padx=10, pady=10)
        
        top, bottom = self._get_cached_data('stock_perf', self.current_strategy) or (pd.DataFrame(), pd.DataFrame())
        
        if top.empty:
            tk.Label(parent, text="⚠️ No stock performance data", 
                    font=('Arial', 10), bg='white', fg='#666').pack(expand=True)
            return
        
        try:
            table_frame = tk.Frame(parent, bg='white')
            table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Headers
            headers = ['Symbol', 'Trades', 'Win Rate', 'Net P&L', 'Type']
            for i, header in enumerate(headers):
                tk.Label(
                    table_frame,
                    text=header,
                    font=('Arial', 9, 'bold'),
                    bg='#E3F2FD',
                    borderwidth=1,
                    relief=tk.SOLID
                ).grid(row=0, column=i, sticky='ew', padx=1, pady=1)
            
            # Top performers
            for i, (_, row) in enumerate(top.iterrows(), 1):
                cells = [
                    row['symbol'],
                    str(int(row.get('total_trades', 0))),
                    f"{row.get('win_rate_pct', 0):.1f}%",
                    f"${row.get('net_profit_loss', 0):+,.0f}",
                    "⬆️ Top"
                ]
                
                for j, cell in enumerate(cells):
                    bg_color = '#C8E6C9' if j == 4 else 'white'
                    tk.Label(
                        table_frame,
                        text=cell,
                        font=('Arial', 8),
                        bg=bg_color,
                        anchor='center',
                        borderwidth=1,
                        relief=tk.SOLID
                    ).grid(row=i, column=j, sticky='ew', padx=1, pady=1)
            
            # Bottom performers
            for i, (_, row) in enumerate(bottom.iterrows(), len(top) + 1):
                cells = [
                    row['symbol'],
                    str(int(row.get('total_trades', 0))),
                    f"{row.get('win_rate_pct', 0):.1f}%",
                    f"${row.get('net_profit_loss', 0):+,.0f}",
                    "⬇️ Bottom"
                ]
                
                for j, cell in enumerate(cells):
                    bg_color = '#FFCDD2' if j == 4 else 'white'
                    tk.Label(
                        table_frame,
                        text=cell,
                        font=('Arial', 8),
                        bg=bg_color,
                        anchor='center',
                        borderwidth=1,
                        relief=tk.SOLID
                    ).grid(row=i, column=j, sticky='ew', padx=1, pady=1)
            
            # Configure column weights
            for i in range(5):
                table_frame.columnconfigure(i, weight=1)
                
        except Exception as e:
            tk.Label(parent, text=f"❌ Error: {str(e)}", 
                    font=('Arial', 9), bg='white', fg='red').pack(expand=True)
            print(f"Error in _create_stock_performance_table: {e}")
    
    def _on_strategy_changed(self, event=None):
        """Handle strategy selection change"""
        self.current_strategy = self.strategy_var.get()
        
        # Clear cache for new strategy
        self._data_cache.clear()
        self._chart_cache.clear()
        
        self._load_dashboard()
    
    def _export_report(self):
        """Export report to markdown"""
        messagebox.showinfo("Export", "Export functionality will be implemented soon")
    
    def _show_trade_details(self):
        """Show detailed trade list"""
        try:
            from trade_details_window import TradeDetailsWindow
            TradeDetailsWindow(self.root, self.current_strategy, self.reader.db_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open trade details:\n{str(e)}")
    
    def _show_risk_analysis(self):
        """Show risk analysis"""
        messagebox.showinfo("Risk Analysis", "Risk analysis window will be implemented soon")
    
    def _compare_strategies(self):
        """Compare all strategies"""
        messagebox.showinfo("Compare", "Strategy comparison will be implemented soon")
    
    def run(self):
        """Run the dashboard"""
        self.root.mainloop()


# ============================================================================
# USAGE
# ============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
        dashboard = StrategyDashboard(db_path)
        dashboard.run()
    else:
        print("Usage: python dashboard.py <analysis_db_path>")