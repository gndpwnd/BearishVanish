"""
Charts Router
Endpoints for chart data
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from routers.analyses import get_current_analysis_reader
from models.responses import (
    EquityCurveData,
    DrawdownData,
    MonthlyReturnsData,
    BenchmarkComparisonData
)


router = APIRouter()


@router.get("/{strategy_name}/equity")
async def get_equity_curve(strategy_name: str):
    """
    Get equity curve data for a strategy
    
    Returns portfolio value over time
    """
    reader = get_current_analysis_reader()
    
    chart_data = reader.get_chart_data(strategy_name, 'equity_curve')
    
    if not chart_data:
        raise HTTPException(
            status_code=404,
            detail=f"Equity curve data not found for '{strategy_name}'"
        )
    
    return {
        "dates": chart_data.get('dates', []),
        "values": chart_data.get('values', []),
        "initial_cash": chart_data.get('initial_cash', 100000),
        "final_value": chart_data['values'][-1] if chart_data.get('values') else 0,
        "peak_value": max(chart_data.get('values', [0]))
    }


@router.get("/{strategy_name}/drawdown")
async def get_drawdown_curve(strategy_name: str):
    """
    Get drawdown curve data for a strategy
    
    Returns drawdown percentage over time
    """
    reader = get_current_analysis_reader()
    
    chart_data = reader.get_chart_data(strategy_name, 'drawdown_curve')
    
    if not chart_data:
        raise HTTPException(
            status_code=404,
            detail=f"Drawdown data not found for '{strategy_name}'"
        )
    
    drawdowns = chart_data.get('drawdowns', [])
    dates = chart_data.get('dates', [])
    
    # Find max drawdown
    max_dd = min(drawdowns) if drawdowns else 0
    max_dd_idx = drawdowns.index(max_dd) if max_dd in drawdowns else 0
    max_dd_date = dates[max_dd_idx] if dates else None
    
    return {
        "dates": dates,
        "drawdowns": drawdowns,
        "max_drawdown": max_dd,
        "max_drawdown_date": max_dd_date
    }


@router.get("/{strategy_name}/monthly")
async def get_monthly_chart(strategy_name: str):
    """
    Get monthly returns chart data
    
    Returns monthly performance bars
    """
    reader = get_current_analysis_reader()
    
    monthly = reader.get_monthly_returns(strategy_name)
    
    if monthly.empty:
        return {
            "months": [],
            "returns": [],
            "trades": [],
            "win_rates": []
        }
    
    return {
        "months": monthly['year_month'].tolist(),
        "returns": monthly['return_pct'].tolist(),
        "trades": monthly['num_trades'].tolist(),
        "win_rates": monthly['win_rate_pct'].tolist()
    }


@router.get("/{strategy_name}/benchmark")
async def get_benchmark_comparison(strategy_name: str):
    """
    Get benchmark comparison data
    
    Compares strategy performance to S&P 500 (if available)
    """
    reader = get_current_analysis_reader()
    
    # Get strategy equity curve
    strategy_data = reader.get_chart_data(strategy_name, 'equity_curve')
    
    if not strategy_data:
        raise HTTPException(
            status_code=404,
            detail=f"Data not found for '{strategy_name}'"
        )
    
    # Calculate returns
    strategy_values = strategy_data.get('values', [])
    if not strategy_values:
        return {
            "dates": [],
            "strategy_returns": [],
            "benchmark_returns": None,
            "outperformance": None
        }
    
    initial = strategy_values[0]
    strategy_returns = [(v / initial - 1) * 100 for v in strategy_values]
    
    # Try to get SPY benchmark
    spy_data = reader.get_chart_data('SPY', 'equity_curve')
    benchmark_returns = None
    outperformance = None
    
    if spy_data and 'values' in spy_data:
        spy_values = spy_data['values']
        spy_initial = spy_values[0]
        
        # Align lengths
        min_len = min(len(strategy_returns), len(spy_values))
        benchmark_returns = [(v / spy_initial - 1) * 100 for v in spy_values[:min_len]]
        
        # Calculate outperformance
        if strategy_returns and benchmark_returns:
            outperformance = strategy_returns[-1] - benchmark_returns[-1]
    
    return {
        "dates": strategy_data.get('dates', []),
        "strategy_returns": strategy_returns,
        "benchmark_returns": benchmark_returns,
        "outperformance": outperformance
    }


@router.get("/{strategy_name}/all")
async def get_all_chart_data(strategy_name: str):
    """
    Get all chart data for a strategy in one request
    
    Optimized endpoint to reduce round trips
    """
    reader = get_current_analysis_reader()
    
    # Get all data
    equity = reader.get_chart_data(strategy_name, 'equity_curve')
    drawdown = reader.get_chart_data(strategy_name, 'drawdown_curve')
    monthly = reader.get_monthly_returns(strategy_name)
    distribution = reader.get_returns_distribution(strategy_name)
    
    response = {
        "equity_curve": equity if equity else {},
        "drawdown_curve": drawdown if drawdown else {},
        "monthly_returns": monthly.to_dict('records') if not monthly.empty else [],
        "returns_distribution": distribution.to_dict('records') if not distribution.empty else []
    }
    
    # Add benchmark if available
    spy_data = reader.get_chart_data('SPY', 'equity_curve')
    if spy_data:
        response["benchmark"] = spy_data
    
    return response