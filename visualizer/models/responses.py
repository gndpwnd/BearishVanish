"""
Pydantic models for API responses
Type-safe data models for all API endpoints
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date


# Configure JSON encoding for datetime objects
class BaseResponse(BaseModel):
    """Base response with proper datetime handling"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
        }
    )


# ============================================================================
# Analysis Models
# ============================================================================

class AnalysisMetadata(BaseResponse):
    """Analysis database metadata"""
    analysis_id: str
    filename: str
    simulation_id: str
    universe: str
    created_at: datetime
    num_strategies: int
    size_kb: float


class AnalysisList(BaseResponse):
    """List of available analyses"""
    analyses: List[AnalysisMetadata]
    count: int


# ============================================================================
# Strategy Models
# ============================================================================

class StrategyMetrics(BaseResponse):
    """Key performance metrics for a strategy"""
    # Returns
    total_return_pct: float
    annualized_return_pct: float
    total_profit_dollars: float
    
    # Risk Metrics
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    volatility_annual_pct: float
    
    # Trade Statistics
    win_rate_pct: float
    profit_factor: float
    completed_trades: int
    winning_trades: int
    losing_trades: int
    
    # Trade Details
    avg_win_dollars: float
    avg_loss_dollars: float
    avg_hold_days: float
    risk_reward_ratio: float
    
    # Additional
    best_trade_pct: Optional[float] = None
    worst_trade_pct: Optional[float] = None


class StrategySummary(BaseResponse):
    """Complete strategy summary"""
    strategy_name: str
    metrics: StrategyMetrics
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StrategyList(BaseResponse):
    """List of strategies"""
    strategies: List[str]
    count: int


# ============================================================================
# Chart Data Models
# ============================================================================

class EquityCurveData(BaseResponse):
    """Equity curve chart data"""
    dates: List[str]
    values: List[float]
    initial_cash: float
    final_value: float
    peak_value: float


class ReturnsDistributionData(BaseResponse):
    """Returns distribution histogram data"""
    bins: List[Dict[str, float]]  # List of {bin_start, bin_end, count, percentage}
    mean_return: float
    median_return: float
    std_dev: float


class MonthlyReturnsData(BaseResponse):
    """Monthly returns chart data"""
    months: List[str]
    returns: List[float]
    trades: List[int]
    win_rates: List[float]


class DrawdownData(BaseResponse):
    """Drawdown chart data"""
    dates: List[str]
    drawdowns: List[float]
    max_drawdown: float
    max_drawdown_date: Optional[str] = None


class BenchmarkComparisonData(BaseResponse):
    """Benchmark comparison data"""
    dates: List[str]
    strategy_returns: List[float]
    benchmark_returns: Optional[List[float]] = None
    outperformance: Optional[float] = None


# ============================================================================
# Trade Models
# ============================================================================

class Trade(BaseResponse):
    """Individual trade data"""
    trade_id: Optional[int] = None
    symbol: str
    strategy_name: str
    trade_status: str  # OPEN or CLOSED
    
    # Entry
    entry_date: date
    entry_price: float
    shares: int
    entry_value: float
    
    # Exit (for closed trades)
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    exit_value: Optional[float] = None
    
    # Performance
    profit_loss_dollars: Optional[float] = None
    profit_loss_pct: Optional[float] = None
    holding_days: Optional[int] = None
    
    # Metadata
    entry_reason: Optional[str] = None
    exit_reason: Optional[str] = None


class TradeList(BaseResponse):
    """Paginated trade list"""
    trades: List[Trade]
    total: int
    page: int
    page_size: int
    total_pages: int


class TradeStatistics(BaseResponse):
    """Trade statistics summary"""
    total_trades: int
    closed_trades: int
    open_positions: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float


# ============================================================================
# Stock Performance Models
# ============================================================================

class StockPerformance(BaseResponse):
    """Per-stock performance summary"""
    symbol: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    net_profit_loss: float
    avg_profit_per_trade: float
    best_trade_pct: Optional[float] = None
    worst_trade_pct: Optional[float] = None


class StockPerformanceList(BaseResponse):
    """List of stock performances"""
    stocks: List[StockPerformance]
    count: int


# ============================================================================
# Comparison Models
# ============================================================================

class StrategyComparison(BaseResponse):
    """Strategy comparison data"""
    strategy_name: str
    total_return_pct: float
    sharpe_ratio: float
    win_rate_pct: float
    max_drawdown_pct: float
    profit_factor: float
    completed_trades: int


class ComparisonResult(BaseResponse):
    """Multi-strategy comparison"""
    strategies: List[StrategyComparison]
    best_return: str
    best_sharpe: str
    best_win_rate: str
    lowest_drawdown: str


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseResponse):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Generic Response Models
# ============================================================================

class SuccessResponse(BaseResponse):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class HealthCheck(BaseResponse):
    """Health check response"""
    status: str
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    databases: Dict[str, int]  # {analysis: count, simulation: count}