# DeepSeek Conversation

## User Message 1

ok, please help me refactor my analysis app into an analysis engine so that it will generate a "summary sqlite database", so that i can cofus on the results of important calculations and not have to calculate them live. then also create a "visulizer app" that will display all these charts and mort. I would prefer just a simple tkinter python app like what i already have, just make it read from the latest analysis database and make it so that i can select which analysis database to use from a dropdown menu or somthing. does this make sense? just make the analysis engine automatically read from the latest simulation database, but keep the functionality of specifying older databases or custom database paths. does this all make sense?

For now just help me separate the code for analysis and the code for visualization. please make a document for proposed changes and what files to create, modify, and delete. and please make sure to create these changes as you are creating two different applications, "analysis engine" and "visualization app". does this make sense?

I wnat the analysis app to perform in depth analysis and write results to a databse similar to how the simulation code would write to a datbase, use timestamp and then write to ./analysis_dbs/

then the visualization app would be in the same folder as ./simulator and ./analysis (./visualization) so the main.py for the visual app would need to access ../analysis/analysis_dbs/(most current database)


does this make sense?

### DeepSeek Response

# Analysis Engine + Visualizer Architecture Proposal

## 📊 PROBLEM STATEMENT

Your current analysis app is slow because it performs complex calculations live from the simulation database. Each chart requires recalculating returns, drawdowns, Sharpe ratios, etc. This creates lag when switching between strategies or viewing different metrics.

## 🚀 PROPOSED SOLUTION: Two-Tier Architecture

### Tier 1: Analysis Engine

- Purpose: Run once after simulation completes
- Function: Perform ALL complex calculations and save to a summary database
- Location: ./analysis/analysis_engine.py
- Output: Creates analysis_dbs/analysis_YYYYMMDD_HHMMSS_simulation_id.db

Purpose: Run once after simulation completes

Function: Perform ALL complex calculations and save to a summary database

Location: ./analysis/analysis_engine.py

`./analysis/analysis_engine.py` Output: Creates analysis_dbs/analysis_YYYYMMDD_HHMMSS_simulation_id.db

`analysis_dbs/analysis_YYYYMMDD_HHMMSS_simulation_id.db` ### Tier 2: Visualization App

- Purpose: Fast, responsive GUI for viewing pre-computed results
- Function: Reads from analysis database (instant loading)
- Location: ./visualizer/ (new folder at same level as simulator and analysis)
- Input: Selects from available analysis databases

Purpose: Fast, responsive GUI for viewing pre-computed results

Function: Reads from analysis database (instant loading)

Location: ./visualizer/ (new folder at same level as simulator and analysis)

`./visualizer/` Input: Selects from available analysis databases

## 📁 PROPOSED FILE STRUCTURE

```text
BearishVanish/
├── simulator/                 # Existing simulation engine
├── analysis/                  # Existing analysis code (modified)
│   ├── analysis_engine.py     # NEW: Pre-computes all analytics
│   ├── analysis_dbs/          # NEW: Store analysis databases
│   │   └── analysis_20251216_143045_sim123.db
│   └── ... existing files ...
│
├── visualizer/                # NEW: Fast visualization app
│   ├── main.py                # Entry point
│   ├── dashboard.py           # Modified dashboard (reads analysis DB)
│   ├── analysis_cache_reader.py  # NEW: Reads pre-computed analytics
│   └── browser.py             # Modified browser for analysis DBs
│
└── shared/                    # NEW: Shared utilities
    ├── db_schemas.py          # Analysis database schema
    └── constants.py           # Shared constants
```

## 🔧 FILE CHANGES REQUIRED

### 1. NEW FILES TO CREATE

#### A. Analysis Engine (analysis/analysis_engine.py)

`analysis/analysis_engine.py` ```python
"""
Analysis Engine - Pre-compute ALL analytics and cache in summary database
Run once after simulation completes: python analysis_engine.py --sim path/to/simulation.db
"""
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import json
import time
from datetime import datetime
from db_reader import SimulationReader
from risk_analysis import RiskAnalyzerDB
from portfolio_risk_analyzer import PortfolioRiskAnalyzerDB
from performance_timeline import PerformanceTimelineDB

class AnalysisEngine:
    """Pre-compute and cache ALL analytics for fast visualization"""
    
    def __init__(self, simulation_db_path):
        self.simulation_db = Path(simulation_db_path)
        self.reader = SimulationReader(self.simulation_db)
        
        # Create analysis database path
        analysis_dir = Path(__file__).parent / 'analysis_dbs'
        analysis_dir.mkdir(exist_ok=True)
        
        sim_id = self.reader.get_simulation_id()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.analysis_db = analysis_dir / f'analysis_{timestamp}_{sim_id}.db'
        
        self.conn = sqlite3.connect(str(self.analysis_db))
        
    def run_full_analysis(self):
        """Run complete analysis pipeline"""
        print(f"\n🔬 ANALYSIS ENGINE")
        print(f"   Input: {self.simulation_db.name}")
        print(f"   Output: {self.analysis_db.name}")
        print(f"{'='*60}")
        
        # Create analysis schema
        self._create_analysis_schema()
        
        strategies = self.reader.list_strategies()
        
        # Analyze each strategy
        for strategy in strategies:
            print(f"\n  📊 Analyzing: {strategy}")
            self._analyze_strategy(strategy)
        
        # Analyze portfolio combinations
        if len(strategies) > 1:
            print(f"\n  📈 Analyzing portfolio combinations...")
            self._analyze_portfolios(strategies)
        
        # Add metadata
        self._add_metadata()
        
        # Optimize database
        self._optimize_database()
        
        print(f"\n✅ Analysis complete!")
        print(f"   Results saved to: {self.analysis_db}")
        print(f"   Size: {self.analysis_db.stat().st_size / 1024:.1f} KB")
        
        return self.analysis_db
    
    def _create_analysis_schema(self):
        """Create analysis database schema"""
        cursor = self.conn.cursor()
        
        # Strategy-level cached metrics
        cursor.execute('''
            CREATE TABLE strategy_cache (
                strategy_name TEXT PRIMARY KEY,
                trade_analysis TEXT NOT NULL,          -- JSON: trade stats
                portfolio_analysis TEXT NOT NULL,      -- JSON: portfolio metrics
                risk_analysis TEXT NOT NULL,           -- JSON: risk metrics
                timeline_analysis TEXT NOT NULL,       -- JSON: timeline data
                stock_breakdown TEXT NOT NULL,         -- JSON: stock performance
                monthly_returns TEXT NOT NULL,         -- JSON: monthly returns
                correlation_data TEXT NOT NULL,        -- JSON: correlations
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Portfolio combinations (multi-strategy)
        cursor.execute('''
            CREATE TABLE portfolio_cache (
                portfolio_id TEXT PRIMARY KEY,
                strategy_names TEXT NOT NULL,          -- JSON list
                weights TEXT NOT NULL,                 -- JSON dict
                metrics TEXT NOT NULL,                 -- JSON: portfolio metrics
                diversification_benefit REAL,
                correlation_matrix TEXT,               -- JSON: correlation matrix
                risk_contributions TEXT,               -- JSON: risk contributions
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Pre-rendered chart data (for instant plotting)
        cursor.execute('''
            CREATE TABLE chart_cache (
                chart_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                chart_type TEXT NOT NULL,              -- 'equity', 'returns_dist', 'monthly', etc.
                chart_data TEXT NOT NULL,              -- JSON: x, y, colors, etc.
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Metadata
        cursor.execute('''
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_timestamp INTEGER NOT NULL
            )
        ''')
        
        self.conn.commit()
    
    def _analyze_strategy(self, strategy_name):
        """Pre-compute ALL analytics for a single strategy"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Trade analysis
        trade_analysis = self._compute_trade_analysis(strategy_name)
        
        # 2. Portfolio analysis
        portfolio_analysis = self._compute_portfolio_analysis(strategy_name)
        
        # 3. Risk analysis
        risk_analysis = self._compute_risk_analysis(strategy_name)
        
        # 4. Timeline analysis
        timeline_analysis = self._compute_timeline_analysis(strategy_name)
        
        # 5. Stock breakdown
        stock_breakdown = self._compute_stock_breakdown(strategy_name)
        
        # 6. Monthly returns
        monthly_returns = self._compute_monthly_returns(strategy_name)
        
        # 7. Correlation data
        correlation_data = self._compute_correlation_data(strategy_name)
        
        # 8. Pre-render chart data
        self._cache_chart_data(strategy_name)
        
        # Store in database
        cursor.execute('''
            INSERT INTO strategy_cache 
            (strategy_name, trade_analysis, portfolio_analysis, risk_analysis,
             timeline_analysis, stock_breakdown, monthly_returns, correlation_data,
             computed_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            json.dumps(trade_analysis),
            json.dumps(portfolio_analysis),
            json.dumps(risk_analysis),
            json.dumps(timeline_analysis),
            json.dumps(stock_breakdown),
            json.dumps(monthly_returns),
            json.dumps(correlation_data),
            timestamp
        ))
        
        self.conn.commit()
    
    def _compute_trade_analysis(self, strategy_name):
        """Pre-compute trade statistics"""
        trades = self.reader.get_closed_trades(strategy_name)
        
        if trades.empty:
            return {}
        
        # All calculations here (not shown for brevity)
        return {
            'total_trades': len(trades),
            'avg_return': trades['profit_loss_pct'].mean(),
            'return_std': trades['profit_loss_pct'].std(),
            # ... 20+ more metrics
        }
    
    # ... similar methods for other analyses ...
    
    def _cache_chart_data(self, strategy_name):
        """Pre-render chart data for instant plotting"""
        portfolio = self.reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        # Equity curve data
        equity_data = {
            'x': portfolio['date'].dt.strftime('%Y-%m-%d').tolist(),
            'y': portfolio['portfolio_value'].tolist(),
            'initial_cash': self.reader.get_initial_cash()
        }
        
        # Store in chart_cache
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chart_cache (chart_id, strategy_name, chart_type, chart_data, computed_timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            f"{strategy_name}_equity",
            strategy_name,
            'equity',
            json.dumps(equity_data),
            int(time.time())
        ))
        
        # ... add more chart types
    
    def _optimize_database(self):
        """Optimize database for fast reading"""
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA optimize')
        cursor.execute('VACUUM')
        self.conn.commit()
```

#### B. Analysis Cache Reader (visualizer/analysis_cache_reader.py)

`visualizer/analysis_cache_reader.py` ```python
"""
Fast reader for pre-computed analysis databases
Lightning-fast - no calculations, just reading cached JSON
"""
import sqlite3
import json
import pandas as pd
from pathlib import Path

class AnalysisCacheReader:
    """Reads from analysis database (pre-computed results)"""
    
    def __init__(self, analysis_db_path):
        self.db_path = Path(analysis_db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        
        # Load ALL cached data into memory for instant access
        self._load_cache()
    
    def _load_cache(self):
        """Load all cached data into memory"""
        cursor = self.conn.cursor()
        
        # Load strategy caches
        cursor.execute("SELECT * FROM strategy_cache")
        self.strategy_cache = {}
        for row in cursor.fetchall():
            self.strategy_cache[row[0]] = {
                'trade_analysis': json.loads(row[1]),
                'portfolio_analysis': json.loads(row[2]),
                'risk_analysis': json.loads(row[3]),
                'timeline_analysis': json.loads(row[4]),
                'stock_breakdown': json.loads(row[5]),
                'monthly_returns': json.loads(row[6]),
                'correlation_data': json.loads(row[7])
            }
        
        # Load chart caches
        cursor.execute("SELECT * FROM chart_cache")
        self.chart_cache = {}
        for row in cursor.fetchall():
            self.chart_cache[row[0]] = json.loads(row[3])
        
        print(f"📦 Loaded {len(self.strategy_cache)} strategies from cache")
    
    def get_strategy_names(self):
        """Get list of strategies (instant)"""
        return list(self.strategy_cache.keys())
    
    def get_trade_analysis(self, strategy_name):
        """Get trade analysis (instant - pre-computed)"""
        return self.strategy_cache.get(strategy_name, {}).get('trade_analysis', {})
    
    def get_equity_chart_data(self, strategy_name):
        """Get equity curve data (instant - pre-rendered)"""
        return self.chart_cache.get(f"{strategy_name}_equity")
    
    # ... more getters for all cached data ...
```

#### C. Visualizer Main (visualizer/main.py)

`visualizer/main.py` ```python
"""
Visualization App - Fast GUI using pre-computed analysis databases
Entry point: python visualizer/main.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from analysis_cache_reader import AnalysisCacheReader
from dashboard import FastDashboard  # Modified dashboard

ANALYSIS_DBS_DIR = Path('../analysis/analysis_dbs')

def find_latest_analysis_db():
    """Find the latest analysis database"""
    if not ANALYSIS_DBS_DIR.exists():
        return None
    
    db_files = list(ANALYSIS_DBS_DIR.glob('analysis_*.db'))
    if not db_files:
        return None
    
    return sorted(db_files, reverse=True)[0]

def main():
    """Main entry point for visualization app"""
    root = tk.Tk()
    root.title("📊 Strategy Visualizer")
    root.geometry("1200x800")
    
    # Try to load latest analysis DB
    latest_db = find_latest_analysis_db()
    
    if latest_db:
        print(f"📁 Loading: {latest_db.name}")
        reader = AnalysisCacheReader(latest_db)
        
        # Show strategy selector
        strategies = reader.get_strategy_names()
        
        if strategies:
            # Open first strategy dashboard
            dashboard = FastDashboard(root, reader, strategies[0])
            dashboard.pack(fill=tk.BOTH, expand=True)
        else:
            messagebox.showwarning("No Data", "No strategies found in analysis database")
    else:
        messagebox.showinfo("No Analysis", 
                          "No analysis databases found.\n\n"
                          "Run analysis engine first:\n"
                          "cd ../analysis && python analysis_engine.py --sim ../simulator/simulations/latest.db")
    
    root.mainloop()

if __name__ == "__main__":
    main()
```

#### D. Fast Dashboard (visualizer/dashboard.py)

`visualizer/dashboard.py` ```python
"""
Fast Dashboard - Uses pre-computed data for instant display
Modified version of existing dashboard.py
"""

import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json

class FastDashboard(tk.Frame):
    """Dashboard that reads from analysis cache (instant loading)"""
    
    def __init__(self, parent, cache_reader, strategy_name):
        super().__init__(parent)
        self.cache_reader = cache_reader
        self.strategy_name = strategy_name
        
        self._create_ui()
    
    def _create_ui(self):
        """Create UI using cached data"""
        # Get ALL cached data for this strategy (instant)
        trade_data = self.cache_reader.get_trade_analysis(self.strategy_name)
        equity_data = self.cache_reader.get_equity_chart_data(self.strategy_name)
        
        # Create matplotlib figure using pre-computed data
        fig = self._create_fast_charts(equity_data, trade_data)
        
        # Embed in tkinter (same as before, but much faster)
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_fast_charts(self, equity_data, trade_data):
        """Create charts using pre-computed data (no calculations)"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Plot 1: Equity curve (using pre-computed x,y)
        if equity_data:
            axes[0, 0].plot(equity_data['x'], equity_data['y'], linewidth=2)
            axes[0, 0].axhline(equity_data['initial_cash'], color='gray', linestyle=':')
        
        # Plot 2: Returns distribution (using pre-computed histogram bins)
        if 'returns_histogram' in trade_data:
            axes[0, 1].bar(trade_data['returns_histogram']['bins'],
                          trade_data['returns_histogram']['counts'])
        
        # ... etc - all using pre-computed data
        
        return fig
```

### 2. FILES TO MODIFY

#### A. Modify existing analysis/main.py

`analysis/main.py` ```python
"""
Modified analysis entry point - now runs analysis engine
Usage: python main.py --analyze simulations/latest.db
"""

import argparse
from analysis_engine import AnalysisEngine

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analyze', help='Run analysis engine on simulation database')
    parser.add_argument('--visualize', action='store_true', help='Open visualizer (legacy)')
    
    args = parser.parse_args()
    
    if args.analyze:
        # Run analysis engine
        engine = AnalysisEngine(args.analyze)
        result_db = engine.run_full_analysis()
        print(f"\n✅ Analysis saved to: {result_db}")
        print(f"   Open visualizer: cd ../visualizer && python main.py")
    
    elif args.visualize:
        # Open the old browser (for backward compatibility)
        from browser import SimulationBrowser
        browser = SimulationBrowser()
        browser.run()

if __name__ == "__main__":
    main()
```

#### B. Modify existing analysis/db_reader.py

`analysis/db_reader.py` - Keep as-is for backward compatibility
- Analysis engine will use this to read simulation databases

Keep as-is for backward compatibility

Analysis engine will use this to read simulation databases

### 3. FILES TO KEEP (UNCHANGED)

- analysis/db_reader.py - Still needed for reading simulation DBs
- analysis/risk_analysis.py - Used by analysis engine
- analysis/portfolio_risk_analyzer.py - Used by analysis engine
- analysis/analysis_components.py - Can be adapted or kept for reference
- analysis/analysis_functions.py - Can be simplified in visualizer

analysis/db_reader.py - Still needed for reading simulation DBs

`analysis/db_reader.py` analysis/risk_analysis.py - Used by analysis engine

`analysis/risk_analysis.py` analysis/portfolio_risk_analyzer.py - Used by analysis engine

`analysis/portfolio_risk_analyzer.py` analysis/analysis_components.py - Can be adapted or kept for reference

`analysis/analysis_components.py` analysis/analysis_functions.py - Can be simplified in visualizer

`analysis/analysis_functions.py` ## 🔄 NEW WORKFLOW

### Step 1: Run Simulation (unchanged)

```bash
cd simulator
python main.py --universe sp500
```

### Step 2: Run Analysis Engine (NEW - one time)

```bash
cd analysis
python main.py --analyze ../simulator/simulations/latest.db
```

Output: Creates analysis_dbs/analysis_20251216_143045_sim123.db with ALL pre-computed analytics.

`analysis_dbs/analysis_20251216_143045_sim123.db` ### Step 3: Open Visualizer (FAST - reads cache)

```bash
cd visualizer
python main.py
```

Experience: Instant loading, no lag when switching between strategies.

## 📊 ANALYSIS DATABASE SCHEMA

The analysis database (analysis_*.db) will contain:

`analysis_*.db` ### Tables:

- strategy_cache - JSON blobs with ALL metrics for each strategy
- portfolio_cache - Multi-strategy portfolio analytics
- chart_cache - Pre-rendered chart data (x, y coordinates, colors)
- metadata - Analysis metadata

strategy_cache - JSON blobs with ALL metrics for each strategy

`strategy_cache` portfolio_cache - Multi-strategy portfolio analytics

`portfolio_cache` chart_cache - Pre-rendered chart data (x, y coordinates, colors)

`chart_cache` metadata - Analysis metadata

`metadata` ### Example JSON Structure in strategy_cache:

`strategy_cache` ```json
{
  "trade_analysis": {
    "total_trades": 142,
    "win_rate": 58.7,
    "avg_return": 1.24,
    "max_win": 12.5,
    "max_loss": -8.3,
    "profit_factor": 1.8,
    "returns_histogram": {
      "bins": [-10, -5, 0, 5, 10],
      "counts": [15, 25, 30, 45, 27]
    }
  },
  "portfolio_analysis": {
    "max_drawdown": -15.2,
    "sharpe_ratio": 1.4,
    "volatility": 12.5,
    "equity_curve": {
      "dates": ["2024-01-01", ...],
      "values": [100000, 101200, ...]
    }
  }
  // ... more pre-computed data
}
```

## 🚀 PERFORMANCE BENEFITS

## 🎯 NEXT STEPS IMPLEMENTATION

I'll now create these files for you. Let me know if you want:

- Full analysis engine implementation with all calculations
- Complete visualizer app with browser for selecting analysis DBs
- Migration script to convert existing dashboards to use cache
- Performance comparison to demonstrate the speedup

Full analysis engine implementation with all calculations

Complete visualizer app with browser for selecting analysis DBs

Migration script to convert existing dashboards to use cache

Performance comparison to demonstrate the speedup

Which would you like me to implement first?

```text
BearishVanish/
├── simulator/                 # Existing simulation engine
├── analysis/                  # Existing analysis code (modified)
│   ├── analysis_engine.py     # NEW: Pre-computes all analytics
│   ├── analysis_dbs/          # NEW: Store analysis databases
│   │   └── analysis_20251216_143045_sim123.db
│   └── ... existing files ...
│
├── visualizer/                # NEW: Fast visualization app
│   ├── main.py                # Entry point
│   ├── dashboard.py           # Modified dashboard (reads analysis DB)
│   ├── analysis_cache_reader.py  # NEW: Reads pre-computed analytics
│   └── browser.py             # Modified browser for analysis DBs
│
└── shared/                    # NEW: Shared utilities
    ├── db_schemas.py          # Analysis database schema
    └── constants.py           # Shared constants
```

```python
"""
Analysis Engine - Pre-compute ALL analytics and cache in summary database
Run once after simulation completes: python analysis_engine.py --sim path/to/simulation.db
"""
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
import json
import time
from datetime import datetime
from db_reader import SimulationReader
from risk_analysis import RiskAnalyzerDB
from portfolio_risk_analyzer import PortfolioRiskAnalyzerDB
from performance_timeline import PerformanceTimelineDB

class AnalysisEngine:
    """Pre-compute and cache ALL analytics for fast visualization"""
    
    def __init__(self, simulation_db_path):
        self.simulation_db = Path(simulation_db_path)
        self.reader = SimulationReader(self.simulation_db)
        
        # Create analysis database path
        analysis_dir = Path(__file__).parent / 'analysis_dbs'
        analysis_dir.mkdir(exist_ok=True)
        
        sim_id = self.reader.get_simulation_id()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.analysis_db = analysis_dir / f'analysis_{timestamp}_{sim_id}.db'
        
        self.conn = sqlite3.connect(str(self.analysis_db))
        
    def run_full_analysis(self):
        """Run complete analysis pipeline"""
        print(f"\n🔬 ANALYSIS ENGINE")
        print(f"   Input: {self.simulation_db.name}")
        print(f"   Output: {self.analysis_db.name}")
        print(f"{'='*60}")
        
        # Create analysis schema
        self._create_analysis_schema()
        
        strategies = self.reader.list_strategies()
        
        # Analyze each strategy
        for strategy in strategies:
            print(f"\n  📊 Analyzing: {strategy}")
            self._analyze_strategy(strategy)
        
        # Analyze portfolio combinations
        if len(strategies) > 1:
            print(f"\n  📈 Analyzing portfolio combinations...")
            self._analyze_portfolios(strategies)
        
        # Add metadata
        self._add_metadata()
        
        # Optimize database
        self._optimize_database()
        
        print(f"\n✅ Analysis complete!")
        print(f"   Results saved to: {self.analysis_db}")
        print(f"   Size: {self.analysis_db.stat().st_size / 1024:.1f} KB")
        
        return self.analysis_db
    
    def _create_analysis_schema(self):
        """Create analysis database schema"""
        cursor = self.conn.cursor()
        
        # Strategy-level cached metrics
        cursor.execute('''
            CREATE TABLE strategy_cache (
                strategy_name TEXT PRIMARY KEY,
                trade_analysis TEXT NOT NULL,          -- JSON: trade stats
                portfolio_analysis TEXT NOT NULL,      -- JSON: portfolio metrics
                risk_analysis TEXT NOT NULL,           -- JSON: risk metrics
                timeline_analysis TEXT NOT NULL,       -- JSON: timeline data
                stock_breakdown TEXT NOT NULL,         -- JSON: stock performance
                monthly_returns TEXT NOT NULL,         -- JSON: monthly returns
                correlation_data TEXT NOT NULL,        -- JSON: correlations
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Portfolio combinations (multi-strategy)
        cursor.execute('''
            CREATE TABLE portfolio_cache (
                portfolio_id TEXT PRIMARY KEY,
                strategy_names TEXT NOT NULL,          -- JSON list
                weights TEXT NOT NULL,                 -- JSON dict
                metrics TEXT NOT NULL,                 -- JSON: portfolio metrics
                diversification_benefit REAL,
                correlation_matrix TEXT,               -- JSON: correlation matrix
                risk_contributions TEXT,               -- JSON: risk contributions
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Pre-rendered chart data (for instant plotting)
        cursor.execute('''
            CREATE TABLE chart_cache (
                chart_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                chart_type TEXT NOT NULL,              -- 'equity', 'returns_dist', 'monthly', etc.
                chart_data TEXT NOT NULL,              -- JSON: x, y, colors, etc.
                computed_timestamp INTEGER NOT NULL
            )
        ''')
        
        # Metadata
        cursor.execute('''
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_timestamp INTEGER NOT NULL
            )
        ''')
        
        self.conn.commit()
    
    def _analyze_strategy(self, strategy_name):
        """Pre-compute ALL analytics for a single strategy"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Trade analysis
        trade_analysis = self._compute_trade_analysis(strategy_name)
        
        # 2. Portfolio analysis
        portfolio_analysis = self._compute_portfolio_analysis(strategy_name)
        
        # 3. Risk analysis
        risk_analysis = self._compute_risk_analysis(strategy_name)
        
        # 4. Timeline analysis
        timeline_analysis = self._compute_timeline_analysis(strategy_name)
        
        # 5. Stock breakdown
        stock_breakdown = self._compute_stock_breakdown(strategy_name)
        
        # 6. Monthly returns
        monthly_returns = self._compute_monthly_returns(strategy_name)
        
        # 7. Correlation data
        correlation_data = self._compute_correlation_data(strategy_name)
        
        # 8. Pre-render chart data
        self._cache_chart_data(strategy_name)
        
        # Store in database
        cursor.execute('''
            INSERT INTO strategy_cache 
            (strategy_name, trade_analysis, portfolio_analysis, risk_analysis,
             timeline_analysis, stock_breakdown, monthly_returns, correlation_data,
             computed_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            json.dumps(trade_analysis),
            json.dumps(portfolio_analysis),
            json.dumps(risk_analysis),
            json.dumps(timeline_analysis),
            json.dumps(stock_breakdown),
            json.dumps(monthly_returns),
            json.dumps(correlation_data),
            timestamp
        ))
        
        self.conn.commit()
    
    def _compute_trade_analysis(self, strategy_name):
        """Pre-compute trade statistics"""
        trades = self.reader.get_closed_trades(strategy_name)
        
        if trades.empty:
            return {}
        
        # All calculations here (not shown for brevity)
        return {
            'total_trades': len(trades),
            'avg_return': trades['profit_loss_pct'].mean(),
            'return_std': trades['profit_loss_pct'].std(),
            # ... 20+ more metrics
        }
    
    # ... similar methods for other analyses ...
    
    def _cache_chart_data(self, strategy_name):
        """Pre-render chart data for instant plotting"""
        portfolio = self.reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        # Equity curve data
        equity_data = {
            'x': portfolio['date'].dt.strftime('%Y-%m-%d').tolist(),
            'y': portfolio['portfolio_value'].tolist(),
            'initial_cash': self.reader.get_initial_cash()
        }
        
        # Store in chart_cache
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chart_cache (chart_id, strategy_name, chart_type, chart_data, computed_timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            f"{strategy_name}_equity",
            strategy_name,
            'equity',
            json.dumps(equity_data),
            int(time.time())
        ))
        
        # ... add more chart types
    
    def _optimize_database(self):
        """Optimize database for fast reading"""
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA optimize')
        cursor.execute('VACUUM')
        self.conn.commit()
```

```python
"""
Fast reader for pre-computed analysis databases
Lightning-fast - no calculations, just reading cached JSON
"""
import sqlite3
import json
import pandas as pd
from pathlib import Path

class AnalysisCacheReader:
    """Reads from analysis database (pre-computed results)"""
    
    def __init__(self, analysis_db_path):
        self.db_path = Path(analysis_db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        
        # Load ALL cached data into memory for instant access
        self._load_cache()
    
    def _load_cache(self):
        """Load all cached data into memory"""
        cursor = self.conn.cursor()
        
        # Load strategy caches
        cursor.execute("SELECT * FROM strategy_cache")
        self.strategy_cache = {}
        for row in cursor.fetchall():
            self.strategy_cache[row[0]] = {
                'trade_analysis': json.loads(row[1]),
                'portfolio_analysis': json.loads(row[2]),
                'risk_analysis': json.loads(row[3]),
                'timeline_analysis': json.loads(row[4]),
                'stock_breakdown': json.loads(row[5]),
                'monthly_returns': json.loads(row[6]),
                'correlation_data': json.loads(row[7])
            }
        
        # Load chart caches
        cursor.execute("SELECT * FROM chart_cache")
        self.chart_cache = {}
        for row in cursor.fetchall():
            self.chart_cache[row[0]] = json.loads(row[3])
        
        print(f"📦 Loaded {len(self.strategy_cache)} strategies from cache")
    
    def get_strategy_names(self):
        """Get list of strategies (instant)"""
        return list(self.strategy_cache.keys())
    
    def get_trade_analysis(self, strategy_name):
        """Get trade analysis (instant - pre-computed)"""
        return self.strategy_cache.get(strategy_name, {}).get('trade_analysis', {})
    
    def get_equity_chart_data(self, strategy_name):
        """Get equity curve data (instant - pre-rendered)"""
        return self.chart_cache.get(f"{strategy_name}_equity")
    
    # ... more getters for all cached data ...
```

```python
"""
Visualization App - Fast GUI using pre-computed analysis databases
Entry point: python visualizer/main.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from analysis_cache_reader import AnalysisCacheReader
from dashboard import FastDashboard  # Modified dashboard

ANALYSIS_DBS_DIR = Path('../analysis/analysis_dbs')

def find_latest_analysis_db():
    """Find the latest analysis database"""
    if not ANALYSIS_DBS_DIR.exists():
        return None
    
    db_files = list(ANALYSIS_DBS_DIR.glob('analysis_*.db'))
    if not db_files:
        return None
    
    return sorted(db_files, reverse=True)[0]

def main():
    """Main entry point for visualization app"""
    root = tk.Tk()
    root.title("📊 Strategy Visualizer")
    root.geometry("1200x800")
    
    # Try to load latest analysis DB
    latest_db = find_latest_analysis_db()
    
    if latest_db:
        print(f"📁 Loading: {latest_db.name}")
        reader = AnalysisCacheReader(latest_db)
        
        # Show strategy selector
        strategies = reader.get_strategy_names()
        
        if strategies:
            # Open first strategy dashboard
            dashboard = FastDashboard(root, reader, strategies[0])
            dashboard.pack(fill=tk.BOTH, expand=True)
        else:
            messagebox.showwarning("No Data", "No strategies found in analysis database")
    else:
        messagebox.showinfo("No Analysis", 
                          "No analysis databases found.\n\n"
                          "Run analysis engine first:\n"
                          "cd ../analysis && python analysis_engine.py --sim ../simulator/simulations/latest.db")
    
    root.mainloop()

if __name__ == "__main__":
    main()
```

```python
"""
Fast Dashboard - Uses pre-computed data for instant display
Modified version of existing dashboard.py
"""

import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json

class FastDashboard(tk.Frame):
    """Dashboard that reads from analysis cache (instant loading)"""
    
    def __init__(self, parent, cache_reader, strategy_name):
        super().__init__(parent)
        self.cache_reader = cache_reader
        self.strategy_name = strategy_name
        
        self._create_ui()
    
    def _create_ui(self):
        """Create UI using cached data"""
        # Get ALL cached data for this strategy (instant)
        trade_data = self.cache_reader.get_trade_analysis(self.strategy_name)
        equity_data = self.cache_reader.get_equity_chart_data(self.strategy_name)
        
        # Create matplotlib figure using pre-computed data
        fig = self._create_fast_charts(equity_data, trade_data)
        
        # Embed in tkinter (same as before, but much faster)
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _create_fast_charts(self, equity_data, trade_data):
        """Create charts using pre-computed data (no calculations)"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Plot 1: Equity curve (using pre-computed x,y)
        if equity_data:
            axes[0, 0].plot(equity_data['x'], equity_data['y'], linewidth=2)
            axes[0, 0].axhline(equity_data['initial_cash'], color='gray', linestyle=':')
        
        # Plot 2: Returns distribution (using pre-computed histogram bins)
        if 'returns_histogram' in trade_data:
            axes[0, 1].bar(trade_data['returns_histogram']['bins'],
                          trade_data['returns_histogram']['counts'])
        
        # ... etc - all using pre-computed data
        
        return fig
```

```python
"""
Modified analysis entry point - now runs analysis engine
Usage: python main.py --analyze simulations/latest.db
"""

import argparse
from analysis_engine import AnalysisEngine

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analyze', help='Run analysis engine on simulation database')
    parser.add_argument('--visualize', action='store_true', help='Open visualizer (legacy)')
    
    args = parser.parse_args()
    
    if args.analyze:
        # Run analysis engine
        engine = AnalysisEngine(args.analyze)
        result_db = engine.run_full_analysis()
        print(f"\n✅ Analysis saved to: {result_db}")
        print(f"   Open visualizer: cd ../visualizer && python main.py")
    
    elif args.visualize:
        # Open the old browser (for backward compatibility)
        from browser import SimulationBrowser
        browser = SimulationBrowser()
        browser.run()

if __name__ == "__main__":
    main()
```

```bash
cd simulator
python main.py --universe sp500
```

```bash
cd analysis
python main.py --analyze ../simulator/simulations/latest.db
```

```bash
cd visualizer
python main.py
```

```json
{
  "trade_analysis": {
    "total_trades": 142,
    "win_rate": 58.7,
    "avg_return": 1.24,
    "max_win": 12.5,
    "max_loss": -8.3,
    "profit_factor": 1.8,
    "returns_histogram": {
      "bins": [-10, -5, 0, 5, 10],
      "counts": [15, 25, 30, 45, 27]
    }
  },
  "portfolio_analysis": {
    "max_drawdown": -15.2,
    "sharpe_ratio": 1.4,
    "volatility": 12.5,
    "equity_curve": {
      "dates": ["2024-01-01", ...],
      "values": [100000, 101200, ...]
    }
  }
  // ... more pre-computed data
}
```

---

## User Message 2

there should be no "shared" database schemas, if everything was shared i would just make this one large app, but my computer can't handle it, which is why i am trying to make each app with a specific purpose, simulator simulates strategy trading, analysis analyzes trading strategy performance, and then visualizer allows me to make plots by reading from analysis database and even simulator database if needed. Does this make sense? if something already exists in simulator database, then just use that for visualization

### DeepSeek Response

You're absolutely right! I completely misunderstood your architecture. Let me correct this:

## 🔄 CORRECTED ARCHITECTURE UNDERSTANDING

- Simulator App → Writes to simulation_*.db (raw trade/portfolio data)
- Analysis App → Reads from simulation_*.db, writes to analysis_*.db (pre-computed metrics)
- Visualizer App → Reads from BOTH databases as needed:Simple charts: Read pre-computed from analysis_*.db (FAST)Detailed debugging: Read raw data from simulation_*.db (when needed)
- Simple charts: Read pre-computed from analysis_*.db (FAST)
- Detailed debugging: Read raw data from simulation_*.db (when needed)

Simulator App → Writes to simulation_*.db (raw trade/portfolio data)

`simulation_*.db` Analysis App → Reads from simulation_*.db, writes to analysis_*.db (pre-computed metrics)

`simulation_*.db` `analysis_*.db` Visualizer App → Reads from BOTH databases as needed:

- Simple charts: Read pre-computed from analysis_*.db (FAST)
- Detailed debugging: Read raw data from simulation_*.db (when needed)

Simple charts: Read pre-computed from analysis_*.db (FAST)

`analysis_*.db` Detailed debugging: Read raw data from simulation_*.db (when needed)

`simulation_*.db` This way you get speed when you need it, but can still drill down to raw data when debugging.

## 📁 CORRECTED FILE STRUCTURE

```text
BearishVanish/
├── simulator/                    # Existing - writes simulation DBs
│   ├── simulations/
│   │   └── simulation_20251216_143045.db  # Raw trade data
│   └── ...
├── analysis/                     # Modified - creates analysis DBs
│   ├── analysis_engine.py        # NEW: Processes simulation DB → analysis DB
│   ├── analysis_dbs/             # NEW: Stores analysis results
│   │   └── analysis_20251216_143045.db    # Pre-computed metrics
│   └── ... existing analysis code ...
└── visualizer/                   # NEW: Fast visualization
    ├── main.py                   # Entry point
    ├── fast_dashboard.py         # Reads analysis DB (fast)
    ├── db_browser.py             # Browser for both DB types
    └── hybrid_reader.py          # Can read both DB types
```

## 🎯 KEY INSIGHTS

- Analysis Engine should NOT duplicate raw data from simulation DB
- Visualizer should read from whichever DB has what it needs
- No shared schemas - each app has its own purpose

Analysis Engine should NOT duplicate raw data from simulation DB

Visualizer should read from whichever DB has what it needs

No shared schemas - each app has its own purpose

Let me create the corrected files:

## 1. ANALYSIS ENGINE (analysis/analysis_engine.py)

`analysis/analysis_engine.py` ```python
"""
Analysis Engine - Pre-computes metrics from simulation database
Purpose: Calculate complex metrics ONCE, store in analysis database
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import json
import time
from datetime import datetime
import sys

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent))
from db_reader import SimulationReader


class AnalysisEngine:
    """
    Converts simulation database → analysis database
    Only stores COMPUTED METRICS, not raw data
    """
    
    def __init__(self, simulation_db_path):
        """
        Args:
            simulation_db_path: Path to simulation database (simulation_*.db)
        """
        self.sim_db_path = Path(simulation_db_path)
        if not self.sim_db_path.exists():
            raise FileNotFoundError(f"Simulation DB not found: {simulation_db_path}")
        
        # Create output database path
        self.analysis_db_dir = Path(__file__).parent / 'analysis_dbs'
        self.analysis_db_dir.mkdir(exist_ok=True)
        
        # Use simulation ID in analysis DB name
        sim_reader = SimulationReader(self.sim_db_path)
        sim_id = sim_reader.get_simulation_id()
        sim_reader.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.analysis_db_path = self.analysis_db_dir / f'analysis_{timestamp}_{sim_id}.db'
        
        print(f"🔬 ANALYSIS ENGINE")
        print(f"   Input:  {self.sim_db_path.name}")
        print(f"   Output: {self.analysis_db_path.name}")
        print(f"{'='*60}")
    
    def run_analysis(self):
        """Run complete analysis pipeline"""
        start_time = time.time()
        
        # Connect to simulation database
        sim_reader = SimulationReader(self.sim_db_path)
        
        # Create analysis database
        self.conn = sqlite3.connect(str(self.analysis_db_path))
        self._create_analysis_schema()
        
        # Get all strategies
        strategies = sim_reader.list_strategies()
        print(f"📊 Found {len(strategies)} strategies")
        
        # Analyze each strategy
        for i, strategy in enumerate(strategies, 1):
            print(f"\n  [{i}/{len(strategies)}] Analyzing: {strategy}")
            self._analyze_strategy(sim_reader, strategy)
        
        # Store simulation metadata
        self._store_simulation_metadata(sim_reader)
        
        # Close connections
        sim_reader.close()
        self.conn.close()
        
        elapsed = time.time() - start_time
        print(f"\n✅ Analysis complete in {elapsed:.1f} seconds!")
        print(f"   Results: {self.analysis_db_path}")
        
        return self.analysis_db_path
    
    def _create_analysis_schema(self):
        """Create analysis database schema - METRICS ONLY"""
        cursor = self.conn.cursor()
        
        # Strategy summary (pre-computed metrics)
        cursor.execute('''
            CREATE TABLE strategy_summary (
                strategy_name TEXT PRIMARY KEY,
                total_return_pct REAL,
                total_profit_dollars REAL,
                win_rate_pct REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                max_drawdown_pct REAL,
                total_trades INTEGER,
                completed_trades INTEGER,
                open_positions INTEGER,
                profit_factor REAL,
                avg_win_dollars REAL,
                avg_loss_dollars REAL,
                risk_reward_ratio REAL,
                expectancy_dollars REAL,
                avg_trade_duration_days REAL,
                exposure_time_pct REAL,
                beta REAL,
                alpha_pct REAL,
                information_ratio REAL,
                computed_timestamp INTEGER
            )
        ''')
        
        # Monthly returns (pre-computed)
        cursor.execute('''
            CREATE TABLE monthly_returns (
                strategy_name TEXT,
                year_month TEXT,  -- '2024-01'
                return_pct REAL,
                PRIMARY KEY (strategy_name, year_month)
            )
        ''')
        
        # Trade returns distribution (pre-computed histogram)
        cursor.execute('''
            CREATE TABLE returns_distribution (
                strategy_name TEXT,
                bin_start REAL,    -- -10.0, -5.0, 0.0, 5.0, 10.0
                bin_end REAL,
                count INTEGER,
                PRIMARY KEY (strategy_name, bin_start)
            )
        ''')
        
        # Stock performance summary (top/bottom stocks)
        cursor.execute('''
            CREATE TABLE stock_summary (
                strategy_name TEXT,
                symbol TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                net_profit_loss REAL,
                win_rate_pct REAL,
                avg_return_pct REAL,
                PRIMARY KEY (strategy_name, symbol)
            )
        ''')
        
        # Drawdown periods (pre-computed)
        cursor.execute('''
            CREATE TABLE drawdown_periods (
                strategy_name TEXT,
                peak_date TEXT,
                trough_date TEXT,
                recovery_date TEXT,
                drawdown_pct REAL,
                recovery_days INTEGER,
                drawdown_dollars REAL
            )
        ''')
        
        # Chart data cache (for instant plotting)
        cursor.execute('''
            CREATE TABLE chart_cache (
                chart_id TEXT PRIMARY KEY,
                strategy_name TEXT,
                chart_type TEXT,
                chart_data TEXT,  -- JSON: {'x': [...], 'y': [...], 'colors': [...]}
                computed_timestamp INTEGER
            )
        ''')
        
        # Analysis metadata
        cursor.execute('''
            CREATE TABLE analysis_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_timestamp INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def _analyze_strategy(self, sim_reader, strategy_name):
        """Analyze a single strategy and store metrics"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Get pre-computed metrics from simulation DB
        perf_stats = sim_reader.get_summary_stats(strategy_name)
        
        if not perf_stats:
            print(f"    ⚠️  No performance data for {strategy_name}")
            return
        
        # 2. Store strategy summary
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_summary
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            perf_stats.get('total_return_pct', 0),
            perf_stats.get('total_profit_dollars', 0),
            perf_stats.get('win_rate_pct', 0),
            perf_stats.get('sharpe_ratio', 0),
            perf_stats.get('sortino_ratio', 0),
            perf_stats.get('max_drawdown_pct', 0),
            perf_stats.get('total_trades', 0),
            perf_stats.get('completed_trades', 0),
            perf_stats.get('open_positions', 0),
            perf_stats.get('profit_factor', 0),
            perf_stats.get('avg_win_dollars', 0),
            perf_stats.get('avg_loss_dollars', 0),
            perf_stats.get('risk_reward_ratio', 0),
            perf_stats.get('expectancy_dollars', 0),
            perf_stats.get('avg_trade_duration_days', 0),
            perf_stats.get('exposure_time_pct', 0),
            perf_stats.get('beta', 0),
            perf_stats.get('alpha_pct', 0),
            perf_stats.get('information_ratio', 0),
            timestamp
        ))
        
        # 3. Compute and store monthly returns
        self._compute_monthly_returns(sim_reader, strategy_name)
        
        # 4. Compute returns distribution
        self._compute_returns_distribution(sim_reader, strategy_name)
        
        # 5. Compute stock performance
        self._compute_stock_summary(sim_reader, strategy_name)
        
        # 6. Compute drawdown periods
        self._compute_drawdown_periods(sim_reader, strategy_name)
        
        # 7. Cache chart data
        self._cache_chart_data(sim_reader, strategy_name)
        
        self.conn.commit()
    
    def _compute_monthly_returns(self, sim_reader, strategy_name):
        """Compute and store monthly returns"""
        monthly = sim_reader.get_monthly_returns(strategy_name)
        
        cursor = self.conn.cursor()
        for date, return_pct in monthly.items():
            year_month = date.strftime('%Y-%m')
            cursor.execute('''
                INSERT OR REPLACE INTO monthly_returns
                VALUES (?, ?, ?)
            ''', (strategy_name, year_month, return_pct))
    
    def _compute_returns_distribution(self, sim_reader, strategy_name):
        """Compute returns histogram"""
        trades = sim_reader.get_closed_trades(strategy_name)
        
        if trades.empty or 'profit_loss_pct' not in trades.columns:
            return
        
        returns = trades['profit_loss_pct'].dropna()
        
        # Create histogram bins
        bins = np.arange(-20, 21, 5)  # -20%, -15%, ..., +20%
        counts, bin_edges = np.histogram(returns, bins=bins)
        
        cursor = self.conn.cursor()
        for i, count in enumerate(counts):
            cursor.execute('''
                INSERT INTO returns_distribution
                VALUES (?, ?, ?, ?)
            ''', (strategy_name, bin_edges[i], bin_edges[i+1], int(count)))
    
    def _compute_stock_summary(self, sim_reader, strategy_name):
        """Compute stock-level performance"""
        stock_perf = sim_reader.get_stock_performance(strategy_name)
        
        if stock_perf.empty:
            return
        
        cursor = self.conn.cursor()
        for _, row in stock_perf.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO stock_summary
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                row['symbol'],
                row.get('total_trades', 0),
                row.get('winning_trades', 0),
                row.get('losing_trades', 0),
                row.get('net_profit_loss', 0),
                row.get('win_rate_pct', 0),
                row.get('avg_return_pct', 0) if 'avg_return_pct' in row else 0
            ))
    
    def _compute_drawdown_periods(self, sim_reader, strategy_name):
        """Identify major drawdown periods"""
        portfolio = sim_reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        # Simple drawdown detection (could be enhanced)
        values = portfolio['portfolio_value'].values
        dates = portfolio['date'].values
        
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        
        # Find significant drawdowns (>5%)
        significant_dd = drawdowns < -5
        
        cursor = self.conn.cursor()
        # Store top 5 drawdowns
        for i in np.argsort(drawdowns)[:5]:
            if drawdowns[i] < -5:
                cursor.execute('''
                    INSERT INTO drawdown_periods
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    strategy_name,
                    str(dates[np.argmax(values[:i+1])]) if i > 0 else str(dates[0]),
                    str(dates[i]),
                    None,  # Recovery date - would need to compute
                    abs(drawdowns[i]),
                    0,     # Recovery days
                    values[np.argmax(values[:i+1])] - values[i] if i > 0 else 0
                ))
    
    def _cache_chart_data(self, sim_reader, strategy_name):
        """Pre-compute chart data for instant plotting"""
        portfolio = sim_reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Equity curve data
        equity_data = {
            'dates': portfolio['date'].dt.strftime('%Y-%m-%d').tolist(),
            'values': portfolio['portfolio_value'].tolist(),
            'initial_cash': sim_reader.get_initial_cash()
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO chart_cache
            VALUES (?, ?, ?, ?, ?)
        ''', (
            f"{strategy_name}_equity",
            strategy_name,
            'equity',
            json.dumps(equity_data),
            timestamp
        ))
        
        # 2. Monthly returns bar chart data
        monthly = sim_reader.get_monthly_returns(strategy_name)
        if not monthly.empty:
            monthly_data = {
                'months': monthly.index.strftime('%Y-%m').tolist(),
                'returns': monthly.values.tolist(),
                'colors': ['green' if r > 0 else 'red' for r in monthly.values]
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO chart_cache
                VALUES (?, ?, ?, ?, ?)
            ''', (
                f"{strategy_name}_monthly",
                strategy_name,
                'monthly_returns',
                json.dumps(monthly_data),
                timestamp
            ))
    
    def _store_simulation_metadata(self, sim_reader):
        """Store which simulation this analysis came from"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        metadata = [
            ('source_simulation', str(self.sim_db_path.name), timestamp),
            ('simulation_id', sim_reader.get_simulation_id(), timestamp),
            ('universe', sim_reader.get_universe(), timestamp),
            ('num_symbols', str(sim_reader.get_num_symbols()), timestamp),
            ('date_range_start', sim_reader.get_date_range()['start'], timestamp),
            ('date_range_end', sim_reader.get_date_range()['end'], timestamp),
            ('initial_capital', str(sim_reader.get_initial_cash()), timestamp),
            ('analysis_timestamp', str(timestamp), timestamp)
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO analysis_metadata
            VALUES (?, ?, ?)
        ''', metadata)
        
        self.conn.commit()


def main():
    """Command line interface for analysis engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run analysis engine on simulation database')
    parser.add_argument('--sim', required=True, help='Path to simulation database')
    parser.add_argument('--latest', action='store_true', help='Use latest simulation')
    
    args = parser.parse_args()
    
    if args.latest:
        # Find latest simulation
        sim_dir = Path('../simulator/simulations')
        if not sim_dir.exists():
            print(f"❌ Simulations directory not found: {sim_dir}")
            return
        
        db_files = list(sim_dir.glob('simulation_*.db'))
        if not db_files:
            print(f"❌ No simulation databases found")
            return
        
        latest_db = sorted(db_files, reverse=True)[0]
        db_path = latest_db
    else:
        db_path = args.sim
    
    print(f"🎯 Analyzing: {db_path}")
    
    try:
        engine = AnalysisEngine(db_path)
        result_db = engine.run_analysis()
        
        print(f"\n📊 Analysis complete!")
        print(f"   Output: {result_db}")
        print(f"\n📈 To visualize:")
        print(f"   cd ../visualizer && python main.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
```

## 2. VISUALIZER MAIN (visualizer/main.py)

`visualizer/main.py` ```python
"""
Visualizer App - Fast visualization using analysis database
Can also fall back to simulation database for raw data
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add path to import from analysis directory
sys.path.append(str(Path(__file__).parent.parent / 'analysis'))

from analysis_cache_reader import AnalysisCacheReader
from db_browser import DatabaseBrowser


class VisualizerApp:
    """Main visualizer application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Strategy Visualizer")
        self.root.geometry("1400x900")
        
        # Set up paths
        self.analysis_dbs_dir = Path('../analysis/analysis_dbs')
        self.simulation_dbs_dir = Path('../simulator/simulations')
        
        self.current_reader = None
        self.current_db_type = None  # 'analysis' or 'simulation'
        
        self._create_ui()
    
    def _create_ui(self):
        """Create main UI"""
        # Header
        header = tk.Frame(self.root, bg='#2196F3', height=60)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text="📊 Strategy Performance Visualizer",
            font=('Arial', 16, 'bold'),
            bg='#2196F3',
            fg='white'
        ).pack(pady=15)
        
        # Control panel
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Database type selector
        tk.Label(control_frame, text="Database Type:", 
                bg='#f0f0f0', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.db_type_var = tk.StringVar(value='analysis')
        db_type_combo = ttk.Combobox(control_frame, textvariable=self.db_type_var,
                                     values=['analysis', 'simulation'], width=12, state='readonly')
        db_type_combo.pack(side=tk.LEFT, padx=5)
        db_type_combo.bind('<<ComboboxSelected>>', self._on_db_type_changed)
        
        # Database selector
        tk.Label(control_frame, text="Database:", 
                bg='#f0f0f0', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=20)
        
        self.db_selector = ttk.Combobox(control_frame, width=40, state='readonly')
        self.db_selector.pack(side=tk.LEFT, padx=5)
        self.db_selector.bind('<<ComboboxSelected>>', self._on_database_selected)
        
        # Refresh button
        tk.Button(control_frame, text="🔄 Refresh", command=self._refresh_databases,
                 bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=20)
        
        # Run analysis button
        tk.Button(control_frame, text="🔬 Run Analysis", command=self._run_analysis,
                 bg='#FF9800', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(control_frame, text="Select a database", 
                                    bg='#f0f0f0', font=('Arial', 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content area
        self.content_frame = tk.Frame(self.root)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initial refresh
        self._refresh_databases()
        
        # Try to auto-select latest analysis DB
        self._select_latest_analysis()
    
    def _refresh_databases(self):
        """Refresh database lists based on selected type"""
        db_type = self.db_type_var.get()
        
        if db_type == 'analysis':
            db_dir = self.analysis_dbs_dir
            pattern = 'analysis_*.db'
        else:  # simulation
            db_dir = self.simulation_dbs_dir
            pattern = 'simulation_*.db'
        
        if not db_dir.exists():
            databases = []
            self.status_label.config(text=f"Directory not found: {db_dir}", fg='red')
        else:
            db_files = list(db_dir.glob(pattern))
            databases = sorted(db_files, reverse=True)  # Newest first
            
            if databases:
                self.status_label.config(text=f"Found {len(databases)} databases", fg='green')
            else:
                self.status_label.config(text=f"No {db_type} databases found", fg='orange')
        
        # Update combobox
        self.db_selector['values'] = [db.name for db in databases]
        
        if databases:
            self.db_selector.set(databases[0].name)
            self._load_database(databases[0])
        else:
            self.db_selector.set('')
            self._clear_content()
    
    def _on_db_type_changed(self, event):
        """Handle database type change"""
        self._refresh_databases()
    
    def _on_database_selected(self, event):
        """Handle database selection"""
        db_name = self.db_selector.get()
        if not db_name:
            return
        
        db_type = self.db_type_var.get()
        if db_type == 'analysis':
            db_path = self.analysis_dbs_dir / db_name
        else:
            db_path = self.simulation_dbs_dir / db_name
        
        self._load_database(db_path)
    
    def _load_database(self, db_path):
        """Load selected database"""
        if not db_path.exists():
            messagebox.showerror("Error", f"Database not found: {db_path}")
            return
        
        # Clear previous content
        self._clear_content()
        
        # Update status
        self.status_label.config(text=f"Loading {db_path.name}...", fg='blue')
        self.root.update()
        
        try:
            db_type = self.db_type_var.get()
            
            if db_type == 'analysis':
                # Load analysis database (fast)
                self.current_reader = AnalysisCacheReader(db_path)
                self.current_db_type = 'analysis'
                
                # Show analysis browser
                from analysis_browser import AnalysisBrowser
                browser = AnalysisBrowser(self.content_frame, self.current_reader)
                browser.pack(fill=tk.BOTH, expand=True)
                
                self.status_label.config(text=f"✓ Loaded analysis DB: {db_path.name}", fg='green')
                
            else:
                # Load simulation database (slower, more detailed)
                from db_reader import SimulationReader
                self.current_reader = SimulationReader(db_path)
                self.current_db_type = 'simulation'
                
                # Show simulation browser
                from db_browser import DatabaseBrowser
                browser = DatabaseBrowser(self.content_frame, self.current_reader)
                browser.pack(fill=tk.BOTH, expand=True)
                
                self.status_label.config(text=f"✓ Loaded simulation DB: {db_path.name}", fg='green')
                
        except Exception as e:
            self.status_label.config(text=f"Error loading database: {e}", fg='red')
            import traceback
            traceback.print_exc()
    
    def _clear_content(self):
        """Clear main content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Show welcome message
        welcome = tk.Label(self.content_frame, 
                          text="📊 Select a database to visualize\n\n"
                               "• Analysis DB: Fast, pre-computed metrics\n"
                               "• Simulation DB: Raw data, detailed analysis",
                          font=('Arial', 12),
                          justify=tk.LEFT)
        welcome.pack(expand=True)
    
    def _select_latest_analysis(self):
        """Auto-select the latest analysis database"""
        if self.analysis_dbs_dir.exists():
            db_files = list(self.analysis_dbs_dir.glob('analysis_*.db'))
            if db_files:
                latest = sorted(db_files, reverse=True)[0]
                self.db_type_var.set('analysis')
                self.db_selector.set(latest.name)
                self._load_database(latest)
    
    def _run_analysis(self):
        """Run analysis engine on selected simulation database"""
        # This would launch the analysis engine
        messagebox.showinfo("Run Analysis", 
                          "This would run: cd ../analysis && python analysis_engine.py\n\n"
                          "For now, run manually from terminal.")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Entry point"""
    app = VisualizerApp()
    app.run()


if __name__ == '__main__':
    main()
```

## 3. ANALYSIS CACHE READER (visualizer/analysis_cache_reader.py)

`visualizer/analysis_cache_reader.py` ```python
"""
Fast reader for analysis databases
Reads pre-computed metrics - NO calculations!
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path


class AnalysisCacheReader:
    """Reads from analysis database (pre-computed metrics only)"""
    
    def __init__(self, analysis_db_path):
        self.db_path = Path(analysis_db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        
        # Cache data in memory for instant access
        self._load_cache()
    
    def _load_cache(self):
        """Load all cached data into memory"""
        self.strategy_summary = {}
        self.chart_cache = {}
        self.monthly_returns = {}
        
        cursor = self.conn.cursor()
        
        # Load strategy summaries
        cursor.execute("SELECT * FROM strategy_summary")
        for row in cursor.fetchall():
            self.strategy_summary[row[0]] = {
                'total_return_pct': row[1],
                'total_profit_dollars': row[2],
                'win_rate_pct': row[3],
                'sharpe_ratio': row[4],
                'sortino_ratio': row[5],
                'max_drawdown_pct': row[6],
                'total_trades': row[7],
                'completed_trades': row[8],
                'open_positions': row[9],
                'profit_factor': row[10],
                'avg_win_dollars': row[11],
                'avg_loss_dollars': row[12],
                'risk_reward_ratio': row[13],
                'expectancy_dollars': row[14],
                'avg_trade_duration_days': row[15],
                'exposure_time_pct': row[16],
                'beta': row[17],
                'alpha_pct': row[18],
                'information_ratio': row[19]
            }
        
        # Load chart cache
        cursor.execute("SELECT * FROM chart_cache")
        for row in cursor.fetchall():
            self.chart_cache[row[0]] = json.loads(row[3])
        
        # Load monthly returns
        cursor.execute("SELECT * FROM monthly_returns")
        for row in cursor.fetchall():
            strategy = row[0]
            if strategy not in self.monthly_returns:
                self.monthly_returns[strategy] = {}
            self.monthly_returns[strategy][row[1]] = row[2]
        
        print(f"📦 Loaded {len(self.strategy_summary)} strategies from analysis cache")
    
    def get_strategy_names(self):
        """Get list of strategies (instant)"""
        return list(self.strategy_summary.keys())
    
    def get_strategy_summary(self, strategy_name):
        """Get all pre-computed metrics for a strategy (instant)"""
        return self.strategy_summary.get(strategy_name, {})
    
    def get_equity_chart_data(self, strategy_name):
        """Get pre-computed equity curve data (instant)"""
        return self.chart_cache.get(f"{strategy_name}_equity")
    
    def get_monthly_returns_data(self, strategy_name):
        """Get pre-computed monthly returns (instant)"""
        return self.monthly_returns.get(strategy_name, {})
    
    def get_metadata(self):
        """Get analysis metadata"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM analysis_metadata")
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

## 4. ANALYSIS BROWSER (visualizer/analysis_browser.py)

`visualizer/analysis_browser.py` ```python
"""
Browser for analysis databases (fast, pre-computed data)
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json


class AnalysisBrowser(tk.Frame):
    """Browser for analysis databases - FAST version"""
    
    def __init__(self, parent, cache_reader):
        super().__init__(parent)
        self.cache_reader = cache_reader
        self.current_strategy = None
        
        self._create_ui()
    
    def _create_ui(self):
        """Create browser UI"""
        # Strategy selector
        selector_frame = tk.Frame(self, bg='#e3f2fd')
        selector_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(selector_frame, text="Strategy:", 
                font=('Arial', 11, 'bold'), bg='#e3f2fd').pack(side=tk.LEFT, padx=5)
        
        self.strategy_var = tk.StringVar()
        strategies = self.cache_reader.get_strategy_names()
        
        strategy_combo = ttk.Combobox(selector_frame, textvariable=self.strategy_var,
                                     values=strategies, width=30, state='readonly')
        strategy_combo.pack(side=tk.LEFT, padx=5)
        strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_selected)
        
        # Metrics display
        self.metrics_frame = tk.Frame(self, bg='white', relief=tk.SUNKEN, borderwidth=1)
        self.metrics_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Chart area
        self.chart_frame = tk.Frame(self)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Select first strategy
        if strategies:
            self.strategy_var.set(strategies[0])
            self._on_strategy_selected()
    
    def _on_strategy_selected(self, event=None):
        """Handle strategy selection"""
        strategy = self.strategy_var.get()
        if not strategy:
            return
        
        self.current_strategy = strategy
        self._update_metrics_display()
        self._update_charts()
    
    def _update_metrics_display(self):
        """Update metrics display (instant - pre-computed)"""
        # Clear previous metrics
        for widget in self.metrics_frame.winfo_children():
            widget.destroy()
        
        # Get pre-computed metrics
        metrics = self.cache_reader.get_strategy_summary(self.current_strategy)
        
        if not metrics:
            tk.Label(self.metrics_frame, text="No metrics available",
                    font=('Arial', 10)).pack(pady=20)
            return
        
        # Create metrics grid
        grid_frame = tk.Frame(self.metrics_frame, bg='white')
        grid_frame.pack(padx=10, pady=10)
        
        # Performance metrics
        perf_metrics = [
            ('Total Return', f"{metrics['total_return_pct']:+.2f}%"),
            ('Total Profit', f"${metrics['total_profit_dollars']:+,.0f}"),
            ('Win Rate', f"{metrics['win_rate_pct']:.1f}%"),
            ('Sharpe Ratio', f"{metrics['sharpe_ratio']:.3f}"),
            ('Max Drawdown', f"{metrics['max_drawdown_pct']:.2f}%"),
            ('Profit Factor', f"{metrics['profit_factor']:.2f}"),
        ]
        
        for i, (label, value) in enumerate(perf_metrics):
            row = i // 3
            col = i % 3
            
            frame = tk.Frame(grid_frame, bg='white')
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')
            
            tk.Label(frame, text=label, font=('Arial', 9), 
                    bg='white', fg='#666').pack(anchor='w')
            tk.Label(frame, text=value, font=('Arial', 11, 'bold'), 
                    bg='white').pack(anchor='w')
    
    def _update_charts(self):
        """Update charts using pre-computed data (instant)"""
        # Clear previous charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Get pre-computed chart data
        equity_data = self.cache_reader.get_equity_chart_data(self.current_strategy)
        monthly_data = self.cache_reader.get_monthly_returns_data(self.current_strategy)
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'{self.current_strategy} - Performance Analysis', fontsize=14)
        
        # Plot 1: Equity curve (from cache)
        if equity_data:
            axes[0].plot(equity_data['dates'], equity_data['values'], 
                        linewidth=2, color='blue')
            axes[0].axhline(equity_data['initial_cash'], color='gray', 
                           linestyle=':', label='Initial Capital')
            axes[0].set_title('Portfolio Equity Curve', fontweight='bold')
            axes[0].set_ylabel('Portfolio Value ($)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            axes[0].tick_params(axis='x', rotation=45)
        
        # Plot 2: Monthly returns (from cache)
        if monthly_data:
            months = list(monthly_data.keys())
            returns = list(monthly_data.values())
            
            colors = ['green' if r > 0 else 'red' for r in returns]
            bars = axes[1].bar(range(len(months)), returns, color=colors)
            
            axes[1].axhline(0, color
```

```text
BearishVanish/
├── simulator/                    # Existing - writes simulation DBs
│   ├── simulations/
│   │   └── simulation_20251216_143045.db  # Raw trade data
│   └── ...
├── analysis/                     # Modified - creates analysis DBs
│   ├── analysis_engine.py        # NEW: Processes simulation DB → analysis DB
│   ├── analysis_dbs/             # NEW: Stores analysis results
│   │   └── analysis_20251216_143045.db    # Pre-computed metrics
│   └── ... existing analysis code ...
└── visualizer/                   # NEW: Fast visualization
    ├── main.py                   # Entry point
    ├── fast_dashboard.py         # Reads analysis DB (fast)
    ├── db_browser.py             # Browser for both DB types
    └── hybrid_reader.py          # Can read both DB types
```

```python
"""
Analysis Engine - Pre-computes metrics from simulation database
Purpose: Calculate complex metrics ONCE, store in analysis database
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import json
import time
from datetime import datetime
import sys

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent))
from db_reader import SimulationReader


class AnalysisEngine:
    """
    Converts simulation database → analysis database
    Only stores COMPUTED METRICS, not raw data
    """
    
    def __init__(self, simulation_db_path):
        """
        Args:
            simulation_db_path: Path to simulation database (simulation_*.db)
        """
        self.sim_db_path = Path(simulation_db_path)
        if not self.sim_db_path.exists():
            raise FileNotFoundError(f"Simulation DB not found: {simulation_db_path}")
        
        # Create output database path
        self.analysis_db_dir = Path(__file__).parent / 'analysis_dbs'
        self.analysis_db_dir.mkdir(exist_ok=True)
        
        # Use simulation ID in analysis DB name
        sim_reader = SimulationReader(self.sim_db_path)
        sim_id = sim_reader.get_simulation_id()
        sim_reader.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.analysis_db_path = self.analysis_db_dir / f'analysis_{timestamp}_{sim_id}.db'
        
        print(f"🔬 ANALYSIS ENGINE")
        print(f"   Input:  {self.sim_db_path.name}")
        print(f"   Output: {self.analysis_db_path.name}")
        print(f"{'='*60}")
    
    def run_analysis(self):
        """Run complete analysis pipeline"""
        start_time = time.time()
        
        # Connect to simulation database
        sim_reader = SimulationReader(self.sim_db_path)
        
        # Create analysis database
        self.conn = sqlite3.connect(str(self.analysis_db_path))
        self._create_analysis_schema()
        
        # Get all strategies
        strategies = sim_reader.list_strategies()
        print(f"📊 Found {len(strategies)} strategies")
        
        # Analyze each strategy
        for i, strategy in enumerate(strategies, 1):
            print(f"\n  [{i}/{len(strategies)}] Analyzing: {strategy}")
            self._analyze_strategy(sim_reader, strategy)
        
        # Store simulation metadata
        self._store_simulation_metadata(sim_reader)
        
        # Close connections
        sim_reader.close()
        self.conn.close()
        
        elapsed = time.time() - start_time
        print(f"\n✅ Analysis complete in {elapsed:.1f} seconds!")
        print(f"   Results: {self.analysis_db_path}")
        
        return self.analysis_db_path
    
    def _create_analysis_schema(self):
        """Create analysis database schema - METRICS ONLY"""
        cursor = self.conn.cursor()
        
        # Strategy summary (pre-computed metrics)
        cursor.execute('''
            CREATE TABLE strategy_summary (
                strategy_name TEXT PRIMARY KEY,
                total_return_pct REAL,
                total_profit_dollars REAL,
                win_rate_pct REAL,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                max_drawdown_pct REAL,
                total_trades INTEGER,
                completed_trades INTEGER,
                open_positions INTEGER,
                profit_factor REAL,
                avg_win_dollars REAL,
                avg_loss_dollars REAL,
                risk_reward_ratio REAL,
                expectancy_dollars REAL,
                avg_trade_duration_days REAL,
                exposure_time_pct REAL,
                beta REAL,
                alpha_pct REAL,
                information_ratio REAL,
                computed_timestamp INTEGER
            )
        ''')
        
        # Monthly returns (pre-computed)
        cursor.execute('''
            CREATE TABLE monthly_returns (
                strategy_name TEXT,
                year_month TEXT,  -- '2024-01'
                return_pct REAL,
                PRIMARY KEY (strategy_name, year_month)
            )
        ''')
        
        # Trade returns distribution (pre-computed histogram)
        cursor.execute('''
            CREATE TABLE returns_distribution (
                strategy_name TEXT,
                bin_start REAL,    -- -10.0, -5.0, 0.0, 5.0, 10.0
                bin_end REAL,
                count INTEGER,
                PRIMARY KEY (strategy_name, bin_start)
            )
        ''')
        
        # Stock performance summary (top/bottom stocks)
        cursor.execute('''
            CREATE TABLE stock_summary (
                strategy_name TEXT,
                symbol TEXT,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                net_profit_loss REAL,
                win_rate_pct REAL,
                avg_return_pct REAL,
                PRIMARY KEY (strategy_name, symbol)
            )
        ''')
        
        # Drawdown periods (pre-computed)
        cursor.execute('''
            CREATE TABLE drawdown_periods (
                strategy_name TEXT,
                peak_date TEXT,
                trough_date TEXT,
                recovery_date TEXT,
                drawdown_pct REAL,
                recovery_days INTEGER,
                drawdown_dollars REAL
            )
        ''')
        
        # Chart data cache (for instant plotting)
        cursor.execute('''
            CREATE TABLE chart_cache (
                chart_id TEXT PRIMARY KEY,
                strategy_name TEXT,
                chart_type TEXT,
                chart_data TEXT,  -- JSON: {'x': [...], 'y': [...], 'colors': [...]}
                computed_timestamp INTEGER
            )
        ''')
        
        # Analysis metadata
        cursor.execute('''
            CREATE TABLE analysis_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_timestamp INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def _analyze_strategy(self, sim_reader, strategy_name):
        """Analyze a single strategy and store metrics"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Get pre-computed metrics from simulation DB
        perf_stats = sim_reader.get_summary_stats(strategy_name)
        
        if not perf_stats:
            print(f"    ⚠️  No performance data for {strategy_name}")
            return
        
        # 2. Store strategy summary
        cursor.execute('''
            INSERT OR REPLACE INTO strategy_summary
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            perf_stats.get('total_return_pct', 0),
            perf_stats.get('total_profit_dollars', 0),
            perf_stats.get('win_rate_pct', 0),
            perf_stats.get('sharpe_ratio', 0),
            perf_stats.get('sortino_ratio', 0),
            perf_stats.get('max_drawdown_pct', 0),
            perf_stats.get('total_trades', 0),
            perf_stats.get('completed_trades', 0),
            perf_stats.get('open_positions', 0),
            perf_stats.get('profit_factor', 0),
            perf_stats.get('avg_win_dollars', 0),
            perf_stats.get('avg_loss_dollars', 0),
            perf_stats.get('risk_reward_ratio', 0),
            perf_stats.get('expectancy_dollars', 0),
            perf_stats.get('avg_trade_duration_days', 0),
            perf_stats.get('exposure_time_pct', 0),
            perf_stats.get('beta', 0),
            perf_stats.get('alpha_pct', 0),
            perf_stats.get('information_ratio', 0),
            timestamp
        ))
        
        # 3. Compute and store monthly returns
        self._compute_monthly_returns(sim_reader, strategy_name)
        
        # 4. Compute returns distribution
        self._compute_returns_distribution(sim_reader, strategy_name)
        
        # 5. Compute stock performance
        self._compute_stock_summary(sim_reader, strategy_name)
        
        # 6. Compute drawdown periods
        self._compute_drawdown_periods(sim_reader, strategy_name)
        
        # 7. Cache chart data
        self._cache_chart_data(sim_reader, strategy_name)
        
        self.conn.commit()
    
    def _compute_monthly_returns(self, sim_reader, strategy_name):
        """Compute and store monthly returns"""
        monthly = sim_reader.get_monthly_returns(strategy_name)
        
        cursor = self.conn.cursor()
        for date, return_pct in monthly.items():
            year_month = date.strftime('%Y-%m')
            cursor.execute('''
                INSERT OR REPLACE INTO monthly_returns
                VALUES (?, ?, ?)
            ''', (strategy_name, year_month, return_pct))
    
    def _compute_returns_distribution(self, sim_reader, strategy_name):
        """Compute returns histogram"""
        trades = sim_reader.get_closed_trades(strategy_name)
        
        if trades.empty or 'profit_loss_pct' not in trades.columns:
            return
        
        returns = trades['profit_loss_pct'].dropna()
        
        # Create histogram bins
        bins = np.arange(-20, 21, 5)  # -20%, -15%, ..., +20%
        counts, bin_edges = np.histogram(returns, bins=bins)
        
        cursor = self.conn.cursor()
        for i, count in enumerate(counts):
            cursor.execute('''
                INSERT INTO returns_distribution
                VALUES (?, ?, ?, ?)
            ''', (strategy_name, bin_edges[i], bin_edges[i+1], int(count)))
    
    def _compute_stock_summary(self, sim_reader, strategy_name):
        """Compute stock-level performance"""
        stock_perf = sim_reader.get_stock_performance(strategy_name)
        
        if stock_perf.empty:
            return
        
        cursor = self.conn.cursor()
        for _, row in stock_perf.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO stock_summary
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                row['symbol'],
                row.get('total_trades', 0),
                row.get('winning_trades', 0),
                row.get('losing_trades', 0),
                row.get('net_profit_loss', 0),
                row.get('win_rate_pct', 0),
                row.get('avg_return_pct', 0) if 'avg_return_pct' in row else 0
            ))
    
    def _compute_drawdown_periods(self, sim_reader, strategy_name):
        """Identify major drawdown periods"""
        portfolio = sim_reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        # Simple drawdown detection (could be enhanced)
        values = portfolio['portfolio_value'].values
        dates = portfolio['date'].values
        
        running_max = np.maximum.accumulate(values)
        drawdowns = (values - running_max) / running_max * 100
        
        # Find significant drawdowns (>5%)
        significant_dd = drawdowns < -5
        
        cursor = self.conn.cursor()
        # Store top 5 drawdowns
        for i in np.argsort(drawdowns)[:5]:
            if drawdowns[i] < -5:
                cursor.execute('''
                    INSERT INTO drawdown_periods
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    strategy_name,
                    str(dates[np.argmax(values[:i+1])]) if i > 0 else str(dates[0]),
                    str(dates[i]),
                    None,  # Recovery date - would need to compute
                    abs(drawdowns[i]),
                    0,     # Recovery days
                    values[np.argmax(values[:i+1])] - values[i] if i > 0 else 0
                ))
    
    def _cache_chart_data(self, sim_reader, strategy_name):
        """Pre-compute chart data for instant plotting"""
        portfolio = sim_reader.get_portfolio_history(strategy_name)
        
        if portfolio.empty:
            return
        
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        # 1. Equity curve data
        equity_data = {
            'dates': portfolio['date'].dt.strftime('%Y-%m-%d').tolist(),
            'values': portfolio['portfolio_value'].tolist(),
            'initial_cash': sim_reader.get_initial_cash()
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO chart_cache
            VALUES (?, ?, ?, ?, ?)
        ''', (
            f"{strategy_name}_equity",
            strategy_name,
            'equity',
            json.dumps(equity_data),
            timestamp
        ))
        
        # 2. Monthly returns bar chart data
        monthly = sim_reader.get_monthly_returns(strategy_name)
        if not monthly.empty:
            monthly_data = {
                'months': monthly.index.strftime('%Y-%m').tolist(),
                'returns': monthly.values.tolist(),
                'colors': ['green' if r > 0 else 'red' for r in monthly.values]
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO chart_cache
                VALUES (?, ?, ?, ?, ?)
            ''', (
                f"{strategy_name}_monthly",
                strategy_name,
                'monthly_returns',
                json.dumps(monthly_data),
                timestamp
            ))
    
    def _store_simulation_metadata(self, sim_reader):
        """Store which simulation this analysis came from"""
        cursor = self.conn.cursor()
        timestamp = int(time.time())
        
        metadata = [
            ('source_simulation', str(self.sim_db_path.name), timestamp),
            ('simulation_id', sim_reader.get_simulation_id(), timestamp),
            ('universe', sim_reader.get_universe(), timestamp),
            ('num_symbols', str(sim_reader.get_num_symbols()), timestamp),
            ('date_range_start', sim_reader.get_date_range()['start'], timestamp),
            ('date_range_end', sim_reader.get_date_range()['end'], timestamp),
            ('initial_capital', str(sim_reader.get_initial_cash()), timestamp),
            ('analysis_timestamp', str(timestamp), timestamp)
        ]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO analysis_metadata
            VALUES (?, ?, ?)
        ''', metadata)
        
        self.conn.commit()


def main():
    """Command line interface for analysis engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run analysis engine on simulation database')
    parser.add_argument('--sim', required=True, help='Path to simulation database')
    parser.add_argument('--latest', action='store_true', help='Use latest simulation')
    
    args = parser.parse_args()
    
    if args.latest:
        # Find latest simulation
        sim_dir = Path('../simulator/simulations')
        if not sim_dir.exists():
            print(f"❌ Simulations directory not found: {sim_dir}")
            return
        
        db_files = list(sim_dir.glob('simulation_*.db'))
        if not db_files:
            print(f"❌ No simulation databases found")
            return
        
        latest_db = sorted(db_files, reverse=True)[0]
        db_path = latest_db
    else:
        db_path = args.sim
    
    print(f"🎯 Analyzing: {db_path}")
    
    try:
        engine = AnalysisEngine(db_path)
        result_db = engine.run_analysis()
        
        print(f"\n📊 Analysis complete!")
        print(f"   Output: {result_db}")
        print(f"\n📈 To visualize:")
        print(f"   cd ../visualizer && python main.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
```

```python
"""
Visualizer App - Fast visualization using analysis database
Can also fall back to simulation database for raw data
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add path to import from analysis directory
sys.path.append(str(Path(__file__).parent.parent / 'analysis'))

from analysis_cache_reader import AnalysisCacheReader
from db_browser import DatabaseBrowser


class VisualizerApp:
    """Main visualizer application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Strategy Visualizer")
        self.root.geometry("1400x900")
        
        # Set up paths
        self.analysis_dbs_dir = Path('../analysis/analysis_dbs')
        self.simulation_dbs_dir = Path('../simulator/simulations')
        
        self.current_reader = None
        self.current_db_type = None  # 'analysis' or 'simulation'
        
        self._create_ui()
    
    def _create_ui(self):
        """Create main UI"""
        # Header
        header = tk.Frame(self.root, bg='#2196F3', height=60)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text="📊 Strategy Performance Visualizer",
            font=('Arial', 16, 'bold'),
            bg='#2196F3',
            fg='white'
        ).pack(pady=15)
        
        # Control panel
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Database type selector
        tk.Label(control_frame, text="Database Type:", 
                bg='#f0f0f0', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.db_type_var = tk.StringVar(value='analysis')
        db_type_combo = ttk.Combobox(control_frame, textvariable=self.db_type_var,
                                     values=['analysis', 'simulation'], width=12, state='readonly')
        db_type_combo.pack(side=tk.LEFT, padx=5)
        db_type_combo.bind('<<ComboboxSelected>>', self._on_db_type_changed)
        
        # Database selector
        tk.Label(control_frame, text="Database:", 
                bg='#f0f0f0', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=20)
        
        self.db_selector = ttk.Combobox(control_frame, width=40, state='readonly')
        self.db_selector.pack(side=tk.LEFT, padx=5)
        self.db_selector.bind('<<ComboboxSelected>>', self._on_database_selected)
        
        # Refresh button
        tk.Button(control_frame, text="🔄 Refresh", command=self._refresh_databases,
                 bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=20)
        
        # Run analysis button
        tk.Button(control_frame, text="🔬 Run Analysis", command=self._run_analysis,
                 bg='#FF9800', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(control_frame, text="Select a database", 
                                    bg='#f0f0f0', font=('Arial', 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content area
        self.content_frame = tk.Frame(self.root)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initial refresh
        self._refresh_databases()
        
        # Try to auto-select latest analysis DB
        self._select_latest_analysis()
    
    def _refresh_databases(self):
        """Refresh database lists based on selected type"""
        db_type = self.db_type_var.get()
        
        if db_type == 'analysis':
            db_dir = self.analysis_dbs_dir
            pattern = 'analysis_*.db'
        else:  # simulation
            db_dir = self.simulation_dbs_dir
            pattern = 'simulation_*.db'
        
        if not db_dir.exists():
            databases = []
            self.status_label.config(text=f"Directory not found: {db_dir}", fg='red')
        else:
            db_files = list(db_dir.glob(pattern))
            databases = sorted(db_files, reverse=True)  # Newest first
            
            if databases:
                self.status_label.config(text=f"Found {len(databases)} databases", fg='green')
            else:
                self.status_label.config(text=f"No {db_type} databases found", fg='orange')
        
        # Update combobox
        self.db_selector['values'] = [db.name for db in databases]
        
        if databases:
            self.db_selector.set(databases[0].name)
            self._load_database(databases[0])
        else:
            self.db_selector.set('')
            self._clear_content()
    
    def _on_db_type_changed(self, event):
        """Handle database type change"""
        self._refresh_databases()
    
    def _on_database_selected(self, event):
        """Handle database selection"""
        db_name = self.db_selector.get()
        if not db_name:
            return
        
        db_type = self.db_type_var.get()
        if db_type == 'analysis':
            db_path = self.analysis_dbs_dir / db_name
        else:
            db_path = self.simulation_dbs_dir / db_name
        
        self._load_database(db_path)
    
    def _load_database(self, db_path):
        """Load selected database"""
        if not db_path.exists():
            messagebox.showerror("Error", f"Database not found: {db_path}")
            return
        
        # Clear previous content
        self._clear_content()
        
        # Update status
        self.status_label.config(text=f"Loading {db_path.name}...", fg='blue')
        self.root.update()
        
        try:
            db_type = self.db_type_var.get()
            
            if db_type == 'analysis':
                # Load analysis database (fast)
                self.current_reader = AnalysisCacheReader(db_path)
                self.current_db_type = 'analysis'
                
                # Show analysis browser
                from analysis_browser import AnalysisBrowser
                browser = AnalysisBrowser(self.content_frame, self.current_reader)
                browser.pack(fill=tk.BOTH, expand=True)
                
                self.status_label.config(text=f"✓ Loaded analysis DB: {db_path.name}", fg='green')
                
            else:
                # Load simulation database (slower, more detailed)
                from db_reader import SimulationReader
                self.current_reader = SimulationReader(db_path)
                self.current_db_type = 'simulation'
                
                # Show simulation browser
                from db_browser import DatabaseBrowser
                browser = DatabaseBrowser(self.content_frame, self.current_reader)
                browser.pack(fill=tk.BOTH, expand=True)
                
                self.status_label.config(text=f"✓ Loaded simulation DB: {db_path.name}", fg='green')
                
        except Exception as e:
            self.status_label.config(text=f"Error loading database: {e}", fg='red')
            import traceback
            traceback.print_exc()
    
    def _clear_content(self):
        """Clear main content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Show welcome message
        welcome = tk.Label(self.content_frame, 
                          text="📊 Select a database to visualize\n\n"
                               "• Analysis DB: Fast, pre-computed metrics\n"
                               "• Simulation DB: Raw data, detailed analysis",
                          font=('Arial', 12),
                          justify=tk.LEFT)
        welcome.pack(expand=True)
    
    def _select_latest_analysis(self):
        """Auto-select the latest analysis database"""
        if self.analysis_dbs_dir.exists():
            db_files = list(self.analysis_dbs_dir.glob('analysis_*.db'))
            if db_files:
                latest = sorted(db_files, reverse=True)[0]
                self.db_type_var.set('analysis')
                self.db_selector.set(latest.name)
                self._load_database(latest)
    
    def _run_analysis(self):
        """Run analysis engine on selected simulation database"""
        # This would launch the analysis engine
        messagebox.showinfo("Run Analysis", 
                          "This would run: cd ../analysis && python analysis_engine.py\n\n"
                          "For now, run manually from terminal.")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Entry point"""
    app = VisualizerApp()
    app.run()


if __name__ == '__main__':
    main()
```

```python
"""
Fast reader for analysis databases
Reads pre-computed metrics - NO calculations!
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path


class AnalysisCacheReader:
    """Reads from analysis database (pre-computed metrics only)"""
    
    def __init__(self, analysis_db_path):
        self.db_path = Path(analysis_db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        
        # Cache data in memory for instant access
        self._load_cache()
    
    def _load_cache(self):
        """Load all cached data into memory"""
        self.strategy_summary = {}
        self.chart_cache = {}
        self.monthly_returns = {}
        
        cursor = self.conn.cursor()
        
        # Load strategy summaries
        cursor.execute("SELECT * FROM strategy_summary")
        for row in cursor.fetchall():
            self.strategy_summary[row[0]] = {
                'total_return_pct': row[1],
                'total_profit_dollars': row[2],
                'win_rate_pct': row[3],
                'sharpe_ratio': row[4],
                'sortino_ratio': row[5],
                'max_drawdown_pct': row[6],
                'total_trades': row[7],
                'completed_trades': row[8],
                'open_positions': row[9],
                'profit_factor': row[10],
                'avg_win_dollars': row[11],
                'avg_loss_dollars': row[12],
                'risk_reward_ratio': row[13],
                'expectancy_dollars': row[14],
                'avg_trade_duration_days': row[15],
                'exposure_time_pct': row[16],
                'beta': row[17],
                'alpha_pct': row[18],
                'information_ratio': row[19]
            }
        
        # Load chart cache
        cursor.execute("SELECT * FROM chart_cache")
        for row in cursor.fetchall():
            self.chart_cache[row[0]] = json.loads(row[3])
        
        # Load monthly returns
        cursor.execute("SELECT * FROM monthly_returns")
        for row in cursor.fetchall():
            strategy = row[0]
            if strategy not in self.monthly_returns:
                self.monthly_returns[strategy] = {}
            self.monthly_returns[strategy][row[1]] = row[2]
        
        print(f"📦 Loaded {len(self.strategy_summary)} strategies from analysis cache")
    
    def get_strategy_names(self):
        """Get list of strategies (instant)"""
        return list(self.strategy_summary.keys())
    
    def get_strategy_summary(self, strategy_name):
        """Get all pre-computed metrics for a strategy (instant)"""
        return self.strategy_summary.get(strategy_name, {})
    
    def get_equity_chart_data(self, strategy_name):
        """Get pre-computed equity curve data (instant)"""
        return self.chart_cache.get(f"{strategy_name}_equity")
    
    def get_monthly_returns_data(self, strategy_name):
        """Get pre-computed monthly returns (instant)"""
        return self.monthly_returns.get(strategy_name, {})
    
    def get_metadata(self):
        """Get analysis metadata"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM analysis_metadata")
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

```python
"""
Browser for analysis databases (fast, pre-computed data)
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json


class AnalysisBrowser(tk.Frame):
    """Browser for analysis databases - FAST version"""
    
    def __init__(self, parent, cache_reader):
        super().__init__(parent)
        self.cache_reader = cache_reader
        self.current_strategy = None
        
        self._create_ui()
    
    def _create_ui(self):
        """Create browser UI"""
        # Strategy selector
        selector_frame = tk.Frame(self, bg='#e3f2fd')
        selector_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(selector_frame, text="Strategy:", 
                font=('Arial', 11, 'bold'), bg='#e3f2fd').pack(side=tk.LEFT, padx=5)
        
        self.strategy_var = tk.StringVar()
        strategies = self.cache_reader.get_strategy_names()
        
        strategy_combo = ttk.Combobox(selector_frame, textvariable=self.strategy_var,
                                     values=strategies, width=30, state='readonly')
        strategy_combo.pack(side=tk.LEFT, padx=5)
        strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_selected)
        
        # Metrics display
        self.metrics_frame = tk.Frame(self, bg='white', relief=tk.SUNKEN, borderwidth=1)
        self.metrics_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Chart area
        self.chart_frame = tk.Frame(self)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Select first strategy
        if strategies:
            self.strategy_var.set(strategies[0])
            self._on_strategy_selected()
    
    def _on_strategy_selected(self, event=None):
        """Handle strategy selection"""
        strategy = self.strategy_var.get()
        if not strategy:
            return
        
        self.current_strategy = strategy
        self._update_metrics_display()
        self._update_charts()
    
    def _update_metrics_display(self):
        """Update metrics display (instant - pre-computed)"""
        # Clear previous metrics
        for widget in self.metrics_frame.winfo_children():
            widget.destroy()
        
        # Get pre-computed metrics
        metrics = self.cache_reader.get_strategy_summary(self.current_strategy)
        
        if not metrics:
            tk.Label(self.metrics_frame, text="No metrics available",
                    font=('Arial', 10)).pack(pady=20)
            return
        
        # Create metrics grid
        grid_frame = tk.Frame(self.metrics_frame, bg='white')
        grid_frame.pack(padx=10, pady=10)
        
        # Performance metrics
        perf_metrics = [
            ('Total Return', f"{metrics['total_return_pct']:+.2f}%"),
            ('Total Profit', f"${metrics['total_profit_dollars']:+,.0f}"),
            ('Win Rate', f"{metrics['win_rate_pct']:.1f}%"),
            ('Sharpe Ratio', f"{metrics['sharpe_ratio']:.3f}"),
            ('Max Drawdown', f"{metrics['max_drawdown_pct']:.2f}%"),
            ('Profit Factor', f"{metrics['profit_factor']:.2f}"),
        ]
        
        for i, (label, value) in enumerate(perf_metrics):
            row = i // 3
            col = i % 3
            
            frame = tk.Frame(grid_frame, bg='white')
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')
            
            tk.Label(frame, text=label, font=('Arial', 9), 
                    bg='white', fg='#666').pack(anchor='w')
            tk.Label(frame, text=value, font=('Arial', 11, 'bold'), 
                    bg='white').pack(anchor='w')
    
    def _update_charts(self):
        """Update charts using pre-computed data (instant)"""
        # Clear previous charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Get pre-computed chart data
        equity_data = self.cache_reader.get_equity_chart_data(self.current_strategy)
        monthly_data = self.cache_reader.get_monthly_returns_data(self.current_strategy)
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        fig.suptitle(f'{self.current_strategy} - Performance Analysis', fontsize=14)
        
        # Plot 1: Equity curve (from cache)
        if equity_data:
            axes[0].plot(equity_data['dates'], equity_data['values'], 
                        linewidth=2, color='blue')
            axes[0].axhline(equity_data['initial_cash'], color='gray', 
                           linestyle=':', label='Initial Capital')
            axes[0].set_title('Portfolio Equity Curve', fontweight='bold')
            axes[0].set_ylabel('Portfolio Value ($)')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            axes[0].tick_params(axis='x', rotation=45)
        
        # Plot 2: Monthly returns (from cache)
        if monthly_data:
            months = list(monthly_data.keys())
            returns = list(monthly_data.values())
            
            colors = ['green' if r > 0 else 'red' for r in returns]
            bars = axes[1].bar(range(len(months)), returns, color=colors)
            
            axes[1].axhline(0, color
```

---



---
*Exported on 12/15/2025, 11:42:29 AM*