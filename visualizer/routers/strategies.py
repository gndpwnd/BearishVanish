"""
Strategies Router
Endpoints for strategy performance data
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import traceback

from routers.analyses import get_current_analysis_reader
from models.responses import (
    StrategyList,
    StrategySummary,
    StrategyMetrics,
    StockPerformanceList,
    StockPerformance
)


router = APIRouter()


@router.get("", response_model=StrategyList)
async def list_strategies():
    """
    Get list of all strategies in current analysis
    """
    try:
        reader = get_current_analysis_reader()
        strategies = reader.get_strategies()
        
        return StrategyList(
            strategies=strategies,
            count=len(strategies)
        )
    except Exception as e:
        print(f"Error listing strategies: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing strategies: {str(e)}"
        )


@router.get("/{strategy_name}")
async def get_strategy_summary(strategy_name: str):
    """
    Get complete summary for a strategy
    
    Returns all performance metrics, monthly data, and metadata
    """
    import pandas as pd
    try:
        reader = get_current_analysis_reader()
        
        # Get summary
        summary = reader.get_summary(strategy_name)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Get additional data
        try:
            monthly = reader.get_monthly_returns(strategy_name)
            monthly_records = []
            if not monthly.empty:
                # Convert carefully, handling potential encoding issues
                for _, row in monthly.iterrows():
                    monthly_records.append({
                        'year_month': str(row['year_month']),
                        'return_pct': float(row['return_pct']) if row['return_pct'] is not None else None,
                        'num_trades': int(row['num_trades']) if row['num_trades'] is not None else None,
                        'win_rate_pct': float(row['win_rate_pct']) if row['win_rate_pct'] is not None else None,
                    })
        except Exception as e:
            print(f"Error processing monthly returns: {traceback.format_exc()}")
            monthly_records = []
        
        try:
            drawdowns = reader.get_drawdown_periods(strategy_name, limit=5)
            drawdown_records = []
            if not drawdowns.empty:
                # Convert carefully, handling potential encoding issues
                for _, row in drawdowns.iterrows():
                    record = {}
                    for col in drawdowns.columns:
                        val = row[col]
                        if isinstance(val, bytes):
                            try:
                                record[col] = val.decode('utf-8')
                            except:
                                record[col] = val.decode('utf-8', errors='replace')
                        elif isinstance(val, float) and not pd.isna(val):
                            record[col] = float(val)
                        elif isinstance(val, int):
                            record[col] = int(val)
                        else:
                            record[col] = val
                    drawdown_records.append(record)
        except Exception as e:
            print(f"Error processing drawdowns: {traceback.format_exc()}")
            drawdown_records = []
        
        # Clean summary data - remove NaN and Inf values that can't be JSON serialized
        if summary:
            import math
            for key in list(summary.keys()):
                val = summary[key]
                if isinstance(val, float):
                    if math.isnan(val) or math.isinf(val):
                        summary[key] = None
        
        return {
            "strategy_name": strategy_name,
            "summary": summary,
            "monthly_returns": monthly_records,
            "top_drawdowns": drawdown_records,
            "metadata": reader.get_metadata()
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting strategy summary for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving strategy data: {str(e)}"
        )


@router.get("/{strategy_name}/metrics", response_model=StrategyMetrics)
async def get_strategy_metrics(strategy_name: str):
    """
    Get key performance metrics for a strategy
    
    Returns only the core metrics (no detailed data)
    """
    try:
        reader = get_current_analysis_reader()
        
        summary = reader.get_summary(strategy_name)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Filter to only known fields in StrategyMetrics
        allowed_fields = {
            'total_return_pct', 'annualized_return_pct', 'total_profit_dollars',
            'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'max_drawdown_pct', 'volatility_annual_pct',
            'win_rate_pct', 'profit_factor', 'completed_trades', 'winning_trades', 'losing_trades',
            'avg_win_dollars', 'avg_loss_dollars', 'avg_hold_days', 'risk_reward_ratio',
            'best_trade_pct', 'worst_trade_pct', 'total_trades', 'open_positions',
            'gross_profit', 'gross_loss', 'expectancy_dollars', 'omega_ratio',
            'max_drawdown_dollars', 'avg_drawdown_pct', 'downside_deviation_pct',
            'var_95_pct', 'cvar_95_pct', 'beta', 'alpha_pct', 'correlation',
            'information_ratio', 'treynor_ratio', 'max_hold_days', 'min_hold_days',
            'max_win_streak', 'max_loss_streak', 'current_streak', 'computation_timestamp',
            'source_simulation_db'
        }
        filtered_summary = {k: v for k, v in summary.items() if k in allowed_fields}
        
        # Clean NaN and Inf values that can't be JSON serialized
        import math
        for key in list(filtered_summary.keys()):
            val = filtered_summary[key]
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    filtered_summary[key] = None
        
        return StrategyMetrics(**filtered_summary)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting strategy metrics for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving strategy metrics: {str(e)}"
        )


@router.get("/{strategy_name}/monthly")
async def get_monthly_returns(strategy_name: str):
    """
    Get monthly returns for a strategy
    """
    try:
        reader = get_current_analysis_reader()
        
        monthly = reader.get_monthly_returns(strategy_name)
        
        if monthly.empty:
            return {"months": [], "data": []}
        
        return {
            "months": monthly['year_month'].tolist(),
            "returns": monthly['return_pct'].tolist(),
            "trades": monthly['num_trades'].tolist(),
            "win_rates": monthly['win_rate_pct'].tolist()
        }
    except Exception as e:
        print(f"Error getting monthly returns for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving monthly returns: {str(e)}"
        )


@router.get("/{strategy_name}/distribution")
async def get_returns_distribution(strategy_name: str):
    """
    Get returns distribution (histogram) for a strategy
    """
    try:
        reader = get_current_analysis_reader()
        
        dist = reader.get_returns_distribution(strategy_name)
        
        if dist.empty:
            return {"bins": [], "stats": {}}
        
        # Calculate statistics
        returns = []
        for _, row in dist.iterrows():
            center = (row['bin_start'] + row['bin_end']) / 2
            count = int(row['count'])
            returns.extend([center] * count)
        
        import numpy as np
        
        stats = {
            "mean": float(np.mean(returns)) if returns else 0,
            "median": float(np.median(returns)) if returns else 0,
            "std_dev": float(np.std(returns)) if returns else 0,
            "min": float(np.min(returns)) if returns else 0,
            "max": float(np.max(returns)) if returns else 0
        }
        
        return {
            "bins": dist.to_dict('records'),
            "stats": stats
        }
    except Exception as e:
        print(f"Error getting returns distribution for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving returns distribution: {str(e)}"
        )


@router.get("/{strategy_name}/drawdowns")
async def get_drawdown_periods(
    strategy_name: str,
    limit: int = Query(default=5, ge=1, le=20)
):
    """
    Get significant drawdown periods
    
    Args:
        limit: Maximum number of drawdowns to return (1-20)
    """
    try:
        reader = get_current_analysis_reader()
        
        drawdowns = reader.get_drawdown_periods(strategy_name, limit=limit)
        
        if drawdowns.empty:
            return {"drawdowns": []}
        
        return {
            "drawdowns": drawdowns.to_dict('records')
        }
    except Exception as e:
        print(f"Error getting drawdowns for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving drawdown periods: {str(e)}"
        )


@router.get("/{strategy_name}/stocks", response_model=StockPerformanceList)
async def get_stock_performance(
    strategy_name: str,
    sort_by: str = Query(default="net_profit_loss", regex="^(net_profit_loss|win_rate_pct|total_trades)$"),
    limit: Optional[int] = Query(default=None, ge=1, le=100)
):
    """
    Get per-stock performance for a strategy
    
    Args:
        sort_by: Field to sort by (net_profit_loss, win_rate_pct, total_trades)
        limit: Maximum number of stocks to return
    """
    try:
        reader = get_current_analysis_reader()
        
        stocks = reader.get_stock_performance(strategy_name)
        
        if stocks.empty:
            return StockPerformanceList(stocks=[], count=0)
        
        # Sort
        ascending = False if sort_by == 'net_profit_loss' else True
        stocks = stocks.sort_values(by=sort_by, ascending=ascending)
        
        # Limit
        if limit:
            stocks = stocks.head(limit)
        
        # Convert to models
        stock_list = []
        for _, row in stocks.iterrows():
            stock_list.append(StockPerformance(
                symbol=row['symbol'],
                total_trades=int(row['total_trades']),
                winning_trades=int(row.get('winning_trades', 0)),
                losing_trades=int(row.get('losing_trades', 0)),
                win_rate_pct=float(row.get('win_rate_pct', 0)),
                net_profit_loss=float(row.get('net_profit_loss', 0)),
                avg_profit_per_trade=float(row.get('avg_profit_per_trade', 0)),
                best_trade_pct=float(row.get('best_trade_pct', 0)) if 'best_trade_pct' in row else None,
                worst_trade_pct=float(row.get('worst_trade_pct', 0)) if 'worst_trade_pct' in row else None
            ))
        
        return StockPerformanceList(
            stocks=stock_list,
            count=len(stock_list)
        )
    except Exception as e:
        print(f"Error getting stock performance for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stock performance: {str(e)}"
        )


@router.get("/{strategy_name}/stocks/top")
async def get_top_stocks(
    strategy_name: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get top performing stocks for a strategy
    
    Args:
        limit: Number of top stocks to return
    """
    try:
        reader = get_current_analysis_reader()
        
        stocks = reader.get_stock_performance(strategy_name)
        
        if stocks.empty:
            return {"stocks": []}
        
        top = stocks.nlargest(limit, 'net_profit_loss')
        
        return {
            "stocks": top.to_dict('records')
        }
    except Exception as e:
        print(f"Error getting top stocks for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving top stocks: {str(e)}"
        )


@router.get("/{strategy_name}/stocks/bottom")
async def get_bottom_stocks(
    strategy_name: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get bottom performing stocks for a strategy
    
    Args:
        limit: Number of bottom stocks to return
    """
    try:
        reader = get_current_analysis_reader()
        
        stocks = reader.get_stock_performance(strategy_name)
        
        if stocks.empty:
            return {"stocks": []}
        
        bottom = stocks.nsmallest(limit, 'net_profit_loss')
        
        return {
            "stocks": bottom.to_dict('records')
        }
    except Exception as e:
        print(f"Error getting bottom stocks for {strategy_name}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving bottom stocks: {str(e)}"
        )