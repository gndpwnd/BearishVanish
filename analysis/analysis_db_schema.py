"""
Analysis Database Schema
Creates tables for storing pre-computed analysis results
"""

ANALYSIS_SCHEMA = """
-- Table 1: Strategy Summary (main metrics)
CREATE TABLE IF NOT EXISTS strategy_summary (
    strategy_name TEXT PRIMARY KEY,
    
    -- Basic Performance
    total_return_pct REAL,
    total_profit_dollars REAL,
    annualized_return_pct REAL,
    
    -- Trade Statistics
    total_trades INTEGER,
    completed_trades INTEGER,
    open_positions INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate_pct REAL,
    
    -- Profit Metrics
    gross_profit REAL,
    gross_loss REAL,
    profit_factor REAL,
    avg_win_dollars REAL,
    avg_loss_dollars REAL,
    risk_reward_ratio REAL,
    expectancy_dollars REAL,
    
    -- Risk Metrics
    sharpe_ratio REAL,
    sortino_ratio REAL,
    calmar_ratio REAL,
    omega_ratio REAL,
    max_drawdown_pct REAL,
    max_drawdown_dollars REAL,
    avg_drawdown_pct REAL,
    volatility_annual_pct REAL,
    downside_deviation_pct REAL,
    
    -- Value at Risk
    var_95_pct REAL,
    cvar_95_pct REAL,
    
    -- Market Exposure
    beta REAL,
    alpha_pct REAL,
    correlation REAL,
    information_ratio REAL,
    treynor_ratio REAL,
    
    -- Holding Period
    avg_hold_days REAL,
    max_hold_days REAL,
    min_hold_days REAL,
    
    -- Streaks
    max_win_streak INTEGER,
    max_loss_streak INTEGER,
    current_streak INTEGER,
    
    -- Metadata
    computation_timestamp INTEGER,
    source_simulation_db TEXT
);

-- Table 2: Monthly Returns (for heatmaps & charts)
CREATE TABLE IF NOT EXISTS monthly_returns (
    strategy_name TEXT,
    year_month TEXT,
    return_pct REAL,
    num_trades INTEGER,
    win_rate_pct REAL,
    PRIMARY KEY (strategy_name, year_month)
);

-- Table 3: Drawdown Periods (significant drawdowns)
CREATE TABLE IF NOT EXISTS drawdown_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT,
    peak_date TEXT,
    trough_date TEXT,
    recovery_date TEXT,
    drawdown_pct REAL,
    drawdown_dollars REAL,
    recovery_days INTEGER,
    duration_days INTEGER
);

-- Table 4: Stock Performance (per-symbol summary)
CREATE TABLE IF NOT EXISTS stock_performance_cache (
    strategy_name TEXT,
    symbol TEXT,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate_pct REAL,
    net_profit_loss REAL,
    avg_return_pct REAL,
    best_trade_pct REAL,
    worst_trade_pct REAL,
    avg_volume_ratio REAL,
    PRIMARY KEY (strategy_name, symbol)
);

-- Table 5: Returns Distribution (histogram bins)
CREATE TABLE IF NOT EXISTS returns_distribution (
    strategy_name TEXT,
    bin_start REAL,
    bin_end REAL,
    count INTEGER,
    percentage REAL,
    PRIMARY KEY (strategy_name, bin_start)
);

-- Table 6: Volume Analysis
CREATE TABLE IF NOT EXISTS volume_analysis (
    strategy_name TEXT PRIMARY KEY,
    trades_with_volume_data INTEGER,
    avg_entry_volume_ratio REAL,
    avg_exit_volume_ratio REAL,
    high_volume_trades INTEGER,
    low_volume_trades INTEGER,
    high_vol_win_rate_pct REAL,
    low_vol_win_rate_pct REAL
);

-- Table 7: Correlation Matrix (for portfolio analysis)
CREATE TABLE IF NOT EXISTS correlation_matrix (
    strategy1 TEXT,
    strategy2 TEXT,
    correlation REAL,
    PRIMARY KEY (strategy1, strategy2)
);

-- Table 8: Chart Cache (pre-computed chart data)
CREATE TABLE IF NOT EXISTS chart_cache (
    chart_id TEXT PRIMARY KEY,
    strategy_name TEXT,
    chart_type TEXT,
    chart_data TEXT,  -- JSON with x, y, colors, etc.
    computation_timestamp INTEGER
);

-- Table 9: Trade Streaks (detailed streak information)
CREATE TABLE IF NOT EXISTS trade_streaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT,
    streak_type TEXT,  -- 'WIN' or 'LOSS'
    start_date TEXT,
    end_date TEXT,
    length INTEGER,
    cumulative_pnl REAL
);

-- Table 10: Analysis Metadata
CREATE TABLE IF NOT EXISTS analysis_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_timestamp INTEGER
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_monthly_strategy ON monthly_returns(strategy_name);
CREATE INDEX IF NOT EXISTS idx_drawdown_strategy ON drawdown_periods(strategy_name);
CREATE INDEX IF NOT EXISTS idx_stock_perf_strategy ON stock_performance_cache(strategy_name);
CREATE INDEX IF NOT EXISTS idx_chart_strategy ON chart_cache(strategy_name, chart_type);
"""

def create_analysis_database(db_path):
    """
    Create analysis database with schema and UTF-8 safety
    
    Args:
        db_path: Path to create database
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    # Add UTF-8 safety
    conn.text_factory = str
    conn.execute("PRAGMA encoding = 'UTF-8'")
    
    conn.executescript(ANALYSIS_SCHEMA)
    conn.commit()
    conn.close()
    
    print(f"✅ Analysis database created: {db_path}")