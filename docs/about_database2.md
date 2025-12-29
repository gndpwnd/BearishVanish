# Stock Trading Simulation Database Documentation

## Overview

The simulation engine stores all results in a SQLite database with a comprehensive schema designed to capture every aspect of strategy performance, trade execution, and portfolio evolution.

**Database Location**: `./simulations/simulation_YYYYMMDD_HHMMSS_*.db`

**Key Features**:
- Complete trade history with entry/exit details
- Volume tracking for all trades
- Trade attempt logging (including rejections)
- Bar-by-bar portfolio snapshots
- Strategy configurations and parameters
- Indicator history for debugging
- All timestamps use simulation time (prevents look-ahead bias)

---

## Database Schema

### 1. `simulation_info`
Stores metadata about the simulation run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `simulation_id` | TEXT UNIQUE NOT NULL | Unique simulation identifier |
| `start_time` | INTEGER NOT NULL | Unix timestamp of simulation start |
| `end_time` | INTEGER | Unix timestamp of simulation end |
| `universe_name` | TEXT | Universe used (e.g., "sp500", "nasdaq100") |
| `num_symbols` | INTEGER | Number of symbols in simulation |
| `date_range_start` | TEXT | Start date of historical data |
| `date_range_end` | TEXT | End date of historical data |
| `initial_capital` | REAL | Starting capital amount |
| `config_json` | TEXT | JSON of simulation configuration |

**Example Query**:
```sql
SELECT * FROM simulation_info;
```

---

### 2. `strategy_performance`
Overall performance metrics for each strategy.

| Column | Type | Description |
|--------|------|-------------|
| `strategy_name` | TEXT PRIMARY KEY | Name of the strategy |
| `initial_capital` | REAL | Starting capital |
| `final_value` | REAL | Final portfolio value |
| `total_return_pct` | REAL | Total return percentage |
| `total_profit_dollars` | REAL | Total profit in dollars |
| `total_trades` | INTEGER | Total number of trades |
| `completed_trades` | INTEGER | Number of completed (closed) trades |
| `open_positions` | INTEGER | Number of still-open positions |
| `rejected_trades` | INTEGER | Number of rejected trade attempts |
| `win_rate_pct` | REAL | Percentage of winning trades |
| `winning_trades` | INTEGER | Number of winning trades |
| `losing_trades` | INTEGER | Number of losing trades |
| `profit_factor` | REAL | Gross profit / Gross loss |
| `sharpe_ratio` | REAL | Risk-adjusted return metric |
| `sortino_ratio` | REAL | Downside risk-adjusted return |
| `calmar_ratio` | REAL | Annual return / Max drawdown |
| `max_drawdown_pct` | REAL | Maximum drawdown percentage |
| `avg_win_dollars` | REAL | Average winning trade amount |
| `avg_loss_dollars` | REAL | Average losing trade amount |
| `avg_trade_duration_days` | REAL | Average holding period in days |
| `risk_reward_ratio` | REAL | Avg win / Avg loss |
| `expectancy_dollars` | REAL | Expected return per trade |
| `exposure_time_pct` | REAL | Percentage of time invested |
| `beta` | REAL | Portfolio beta vs S&P 500 |
| `alpha_pct` | REAL | Alpha vs S&P 500 |
| `information_ratio` | REAL | Risk-adjusted excess return |
| `position_size_pct` | REAL | Position sizing percentage |
| `max_positions` | INTEGER | Maximum concurrent positions |
| `strategy_config_json` | TEXT | JSON of strategy configuration |

**Example Queries**:
```sql
-- Get top performing strategies
SELECT strategy_name, total_return_pct, win_rate_pct, sharpe_ratio
FROM strategy_performance
ORDER BY total_return_pct DESC;

-- Compare risk-adjusted returns
SELECT strategy_name, sharpe_ratio, sortino_ratio, calmar_ratio
FROM strategy_performance
ORDER BY sharpe_ratio DESC;
```

---

### 3. `trade_history`
Detailed history of all trades with entry/exit information and volume data.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment trade ID |
| `strategy_name` | TEXT NOT NULL | Strategy that made the trade |
| `symbol` | TEXT NOT NULL | Stock symbol |
| `entry_timestamp` | INTEGER NOT NULL | Unix timestamp of entry |
| `entry_date` | TEXT NOT NULL | Human-readable entry date |
| `entry_price` | REAL NOT NULL | Entry price |
| `shares` | REAL NOT NULL | Number of shares |
| `entry_volume` | INTEGER | Volume at entry |
| `entry_avg_volume_20d` | REAL | 20-day average volume at entry |
| `entry_relative_volume` | REAL | Relative volume at entry |
| `entry_portfolio_value` | REAL | Portfolio value at entry |
| `entry_cash` | REAL | Available cash at entry |
| `entry_num_positions` | INTEGER | Number of open positions at entry |
| `exit_timestamp` | INTEGER | Unix timestamp of exit (NULL if open) |
| `exit_date` | TEXT | Human-readable exit date |
| `exit_price` | REAL | Exit price |
| `exit_volume` | INTEGER | Volume at exit |
| `exit_avg_volume_20d` | REAL | 20-day average volume at exit |
| `exit_relative_volume` | REAL | Relative volume at exit |
| `exit_portfolio_value` | REAL | Portfolio value at exit |
| `exit_cash` | REAL | Available cash at exit |
| `profit_loss_dollars` | REAL | P&L in dollars |
| `profit_loss_pct` | REAL | P&L percentage |
| `holding_days` | REAL | Holding period in days |
| `holding_bars` | INTEGER | Holding period in bars |
| `trade_status` | TEXT NOT NULL | 'OPEN' or 'CLOSED' |
| `forced_exit` | BOOLEAN | Whether exit was forced |
| `exit_reason` | TEXT | Reason for exit |
| `entry_reason` | TEXT | Reason for entry |

**Indexes**:
- `idx_trades_strategy` on `(strategy_name, trade_status)`
- `idx_trades_symbol` on `(symbol)`
- `idx_trades_entry_ts` on `(entry_timestamp)`
- `idx_trades_volume` on `(entry_relative_volume, exit_relative_volume)`

**Example Queries**:
```sql
-- Get all winning trades
SELECT strategy_name, symbol, entry_date, exit_date, 
       profit_loss_dollars, profit_loss_pct
FROM trade_history
WHERE trade_status = 'CLOSED' AND profit_loss_dollars > 0
ORDER BY profit_loss_pct DESC;

-- Get trades with high relative volume
SELECT strategy_name, symbol, entry_date, 
       entry_relative_volume, profit_loss_pct
FROM trade_history
WHERE entry_relative_volume > 2.0 AND trade_status = 'CLOSED'
ORDER BY entry_relative_volume DESC;

-- Get open positions
SELECT strategy_name, symbol, entry_date, entry_price, shares
FROM trade_history
WHERE trade_status = 'OPEN'
ORDER BY entry_date;

-- Calculate average holding period by strategy
SELECT strategy_name, AVG(holding_days) as avg_hold_days
FROM trade_history
WHERE trade_status = 'CLOSED'
GROUP BY strategy_name;
```

---

### 4. `trade_attempts`
Records EVERY trade attempt, including those that were rejected.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `timestamp` | INTEGER NOT NULL | Unix timestamp of attempt |
| `date` | TEXT NOT NULL | Human-readable date |
| `strategy_name` | TEXT NOT NULL | Strategy name |
| `symbol` | TEXT NOT NULL | Stock symbol |
| `signal` | TEXT NOT NULL | 'BUY' or 'SELL' |
| `price` | REAL NOT NULL | Price at signal |
| `volume` | INTEGER | Volume at signal |
| `avg_volume_20d` | REAL | 20-day average volume |
| `relative_volume` | REAL | Relative volume |
| `portfolio_value` | REAL | Portfolio value at attempt |
| `cash` | REAL | Available cash |
| `num_positions` | INTEGER | Current number of positions |
| `max_positions` | INTEGER | Maximum allowed positions |
| `success` | BOOLEAN NOT NULL | Whether trade was executed |
| `rejection_reason` | TEXT | Reason for rejection if failed |

**Indexes**:
- `idx_attempts_strategy` on `(strategy_name, success)`
- `idx_attempts_volume` on `(relative_volume, success)`

**Example Queries**:
```sql
-- Get rejection statistics by strategy
SELECT strategy_name, 
       COUNT(*) as total_attempts,
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
       SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as rejected
FROM trade_attempts
GROUP BY strategy_name;

-- Find most common rejection reasons
SELECT rejection_reason, COUNT(*) as count
FROM trade_attempts
WHERE NOT success
GROUP BY rejection_reason
ORDER BY count DESC;

-- Analyze signal success by volume
SELECT 
    CASE 
        WHEN relative_volume < 1.0 THEN 'Low'
        WHEN relative_volume < 2.0 THEN 'Normal'
        ELSE 'High'
    END as volume_category,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    COUNT(*) as total
FROM trade_attempts
WHERE signal = 'BUY'
GROUP BY volume_category;
```

---

### 5. `portfolio_history`
Daily snapshots of portfolio state for each strategy.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `timestamp` | INTEGER NOT NULL | Unix timestamp |
| `strategy_name` | TEXT NOT NULL | Strategy name |
| `date` | TEXT NOT NULL | Human-readable date |
| `portfolio_value` | REAL NOT NULL | Total portfolio value |
| `cash` | REAL | Available cash |
| `positions_value` | REAL | Value of open positions |
| `num_positions` | INTEGER | Number of open positions |
| `daily_return_pct` | REAL | Daily return percentage |

**Index**:
- `idx_portfolio_strategy` on `(strategy_name, timestamp)`

**Example Queries**:
```sql
-- Get portfolio evolution for a strategy
SELECT date, portfolio_value, num_positions
FROM portfolio_history
WHERE strategy_name = 'Your Strategy'
ORDER BY timestamp;

-- Calculate drawdown periods
SELECT strategy_name, date, portfolio_value,
       MAX(portfolio_value) OVER (
           PARTITION BY strategy_name 
           ORDER BY timestamp
       ) as peak_value,
       (portfolio_value - MAX(portfolio_value) OVER (
           PARTITION BY strategy_name 
           ORDER BY timestamp
       )) / MAX(portfolio_value) OVER (
           PARTITION BY strategy_name 
           ORDER BY timestamp
       ) * 100 as drawdown_pct
FROM portfolio_history
ORDER BY strategy_name, timestamp;
```

---

### 6. `stock_performance`
Per-symbol performance summary for each strategy.

| Column | Type | Description |
|--------|------|-------------|
| `strategy_name` | TEXT NOT NULL | Strategy name |
| `symbol` | TEXT NOT NULL | Stock symbol |
| `total_trades` | INTEGER | Total trades for this symbol |
| `winning_trades` | INTEGER | Number of winning trades |
| `losing_trades` | INTEGER | Number of losing trades |
| `net_profit_loss` | REAL | Net P&L for this symbol |
| `win_rate_pct` | REAL | Win rate for this symbol |

**Primary Key**: `(strategy_name, symbol)`

**Example Queries**:
```sql
-- Best performing stocks per strategy
SELECT strategy_name, symbol, net_profit_loss, win_rate_pct
FROM stock_performance
WHERE net_profit_loss > 0
ORDER BY net_profit_loss DESC
LIMIT 20;

-- Worst performing stocks
SELECT strategy_name, symbol, net_profit_loss, win_rate_pct
FROM stock_performance
WHERE net_profit_loss < 0
ORDER BY net_profit_loss ASC
LIMIT 20;
```

---

### 7. `execution_log`
Bar-by-bar execution log for detailed debugging.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `timestamp` | INTEGER NOT NULL | Unix timestamp |
| `date` | TEXT NOT NULL | Human-readable date |
| `bar_number` | INTEGER NOT NULL | Sequential bar number |
| `strategy_name` | TEXT NOT NULL | Strategy name |
| `symbol` | TEXT NOT NULL | Stock symbol |
| `action` | TEXT NOT NULL | Action taken |
| `details` | TEXT | JSON with additional details |

**Index**:
- `idx_execution_strategy` on `(strategy_name, timestamp)`

**Example Query**:
```sql
-- Get execution timeline for a specific symbol
SELECT date, bar_number, action, details
FROM execution_log
WHERE symbol = 'AAPL' AND strategy_name = 'Your Strategy'
ORDER BY timestamp;
```

---

### 8. `strategy_configs`
Stores strategy configurations and parameters.

| Column | Type | Description |
|--------|------|-------------|
| `strategy_name` | TEXT PRIMARY KEY | Strategy name |
| `initial_capital` | REAL | Starting capital |
| `position_size_pct` | REAL | Position sizing percentage |
| `max_positions` | INTEGER | Maximum concurrent positions |
| `color` | TEXT | Color for visualization |
| `parameters_json` | TEXT | JSON of all parameters |
| `created_timestamp` | INTEGER | Creation timestamp |

**Example Query**:
```sql
-- Get all strategy configurations
SELECT strategy_name, initial_capital, position_size_pct, max_positions
FROM strategy_configs;
```

---

### 9. `indicator_history`
Stores indicator values for debugging and analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `timestamp` | INTEGER NOT NULL | Unix timestamp |
| `date` | TEXT NOT NULL | Human-readable date |
| `strategy_name` | TEXT NOT NULL | Strategy name |
| `symbol` | TEXT NOT NULL | Stock symbol |
| `indicator_name` | TEXT NOT NULL | Indicator name (e.g., 'rsi_14') |
| `indicator_value` | REAL | Indicator value |
| `indicator_params` | TEXT | JSON of indicator parameters |

**Index**:
- `idx_indicator_history` on `(strategy_name, symbol, indicator_name)`

**Example Queries**:
```sql
-- Get RSI values for a specific symbol
SELECT date, indicator_value
FROM indicator_history
WHERE symbol = 'AAPL' 
  AND indicator_name = 'rsi_14'
  AND strategy_name = 'Your Strategy'
ORDER BY timestamp;

-- Find extreme indicator values
SELECT strategy_name, symbol, date, indicator_name, indicator_value
FROM indicator_history
WHERE indicator_name = 'rsi_14' 
  AND (indicator_value > 70 OR indicator_value < 30)
ORDER BY date;
```

---

## Relationships Between Tables

```
simulation_info (1) --> (many) strategy_performance
                    --> (many) trade_history
                    --> (many) trade_attempts
                    --> (many) portfolio_history

strategy_performance (1) --> (many) trade_history [via strategy_name]
                         --> (many) trade_attempts [via strategy_name]
                         --> (many) portfolio_history [via strategy_name]
                         --> (many) stock_performance [via strategy_name]

trade_history --> stock_performance [aggregated by symbol]
```

---

## Common Analysis Queries

### 1. Strategy Comparison
```sql
SELECT 
    s.strategy_name,
    s.total_return_pct,
    s.win_rate_pct,
    s.max_drawdown_pct,
    s.sharpe_ratio,
    s.completed_trades,
    s.rejected_trades
FROM strategy_performance s
ORDER BY s.total_return_pct DESC;
```

### 2. Best Trades Analysis
```sql
SELECT 
    strategy_name,
    symbol,
    entry_date,
    exit_date,
    entry_price,
    exit_price,
    profit_loss_pct,
    holding_days,
    entry_relative_volume
FROM trade_history
WHERE trade_status = 'CLOSED'
ORDER BY profit_loss_pct DESC
LIMIT 10;
```

### 3. Volume Impact Analysis
```sql
SELECT 
    CASE 
        WHEN entry_relative_volume < 1.0 THEN 'Low Volume'
        WHEN entry_relative_volume < 2.0 THEN 'Normal Volume'
        ELSE 'High Volume'
    END as volume_category,
    COUNT(*) as num_trades,
    AVG(profit_loss_pct) as avg_return,
    SUM(CASE WHEN profit_loss_dollars > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate
FROM trade_history
WHERE trade_status = 'CLOSED'
GROUP BY volume_category;
```

### 4. Monthly Performance
```sql
SELECT 
    strategy_name,
    strftime('%Y-%m', date) as month,
    SUM(profit_loss_dollars) as monthly_pnl,
    COUNT(*) as trades_closed
FROM trade_history
WHERE trade_status = 'CLOSED'
GROUP BY strategy_name, month
ORDER BY strategy_name, month;
```

### 5. Risk Analysis
```sql
SELECT 
    strategy_name,
    symbol,
    COUNT(*) as num_trades,
    AVG(profit_loss_pct) as avg_return,
    STDEV(profit_loss_pct) as volatility,
    MIN(profit_loss_pct) as worst_trade,
    MAX(profit_loss_pct) as best_trade
FROM trade_history
WHERE trade_status = 'CLOSED'
GROUP BY strategy_name, symbol
HAVING num_trades >= 3
ORDER BY volatility DESC;
```

### 6. Portfolio Evolution with Trades
```sql
SELECT 
    p.date,
    p.portfolio_value,
    p.num_positions,
    COUNT(t.id) as trades_today
FROM portfolio_history p
LEFT JOIN trade_history t ON p.date = t.entry_date AND p.strategy_name = t.strategy_name
WHERE p.strategy_name = 'Your Strategy'
GROUP BY p.date, p.portfolio_value, p.num_positions
ORDER BY p.date;
```

---

## Important Notes

### Timestamp Convention
- **All timestamps use SIMULATION TIME, not real-world time**
- This prevents look-ahead bias in analysis
- Convert using: `datetime.fromtimestamp(timestamp)`

### Volume Metrics
- `entry_volume`: Actual volume at entry bar
- `entry_avg_volume_20d`: 20-day rolling average
- `entry_relative_volume`: Current volume / Average volume

### Trade Status
- `OPEN`: Position is still held
- `CLOSED`: Position has been exited

### Forced Exits
- When `forced_exit = TRUE`, the position was liquidated at simulation end
- Useful for understanding which positions would have continued

---

## Python Connection Example

```python
import sqlite3
import pandas as pd

# Connect to database
db_path = './simulations/simulation_20241214_123456_hash.db'
conn = sqlite3.connect(db_path)

# Read strategy performance
strategies = pd.read_sql_query(
    'SELECT * FROM strategy_performance ORDER BY total_return_pct DESC',
    conn
)

# Read trade history
trades = pd.read_sql_query(
    'SELECT * FROM trade_history WHERE trade_status = "CLOSED"',
    conn
)

# Read portfolio evolution
portfolio = pd.read_sql_query(
    'SELECT * FROM portfolio_history WHERE strategy_name = "Your Strategy"',
    conn
)

conn.close()
```

---

## Performance Tips

1. **Use indexed columns** in WHERE clauses for faster queries
2. **Limit result sets** when exploring data
3. **Use EXPLAIN QUERY PLAN** to optimize slow queries
4. **Consider creating views** for commonly used queries
5. **Batch inserts** during simulation for better performance

---

## Schema Version

**Version**: 1.0  
**Last Updated**: December 2024  
**Compatible With**: Optimized Stock Trading Simulator v1.0

---

## Support

For questions about the database schema or simulation engine:
1. Check the source code in `simulation_telemetry.py`
2. Review example queries in this document
3. Use SQLite Browser for visual exploration

---

**End of Documentation**