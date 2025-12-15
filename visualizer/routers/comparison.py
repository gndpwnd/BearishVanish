"""
Comparison Router
Endpoints for comparing multiple strategies
"""

from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional

from routers.analyses import get_current_analysis_reader
from models.responses import ComparisonResult, StrategyComparison


router = APIRouter()


@router.get("")
async def compare_all_strategies():
    """
    Compare all strategies in the current analysis
    
    Returns comparison metrics for all strategies sorted by total return
    """
    reader = get_current_analysis_reader()
    
    # Get all summaries
    summaries = reader.get_all_summaries()
    
    if not summaries:
        raise HTTPException(
            status_code=404,
            detail="No strategies found"
        )
    
    # Convert to comparison models
    comparisons = []
    for summary in summaries:
        comparisons.append(StrategyComparison(
            strategy_name=summary['strategy_name'],
            total_return_pct=float(summary.get('total_return_pct', 0)),
            sharpe_ratio=float(summary.get('sharpe_ratio', 0)),
            win_rate_pct=float(summary.get('win_rate_pct', 0)),
            max_drawdown_pct=float(summary.get('max_drawdown_pct', 0)),
            profit_factor=float(summary.get('profit_factor', 0)),
            completed_trades=int(summary.get('completed_trades', 0))
        ))
    
    # Find best performers
    best_return = max(comparisons, key=lambda x: x.total_return_pct).strategy_name
    best_sharpe = max(comparisons, key=lambda x: x.sharpe_ratio).strategy_name
    best_win_rate = max(comparisons, key=lambda x: x.win_rate_pct).strategy_name
    
    # Lowest drawdown (closest to 0, since drawdowns are negative)
    lowest_drawdown = max(comparisons, key=lambda x: x.max_drawdown_pct).strategy_name
    
    return ComparisonResult(
        strategies=comparisons,
        best_return=best_return,
        best_sharpe=best_sharpe,
        best_win_rate=best_win_rate,
        lowest_drawdown=lowest_drawdown
    )


@router.post("")
async def compare_selected_strategies(
    strategy_names: List[str] = Body(..., embed=True)
):
    """
    Compare selected strategies
    
    Args:
        strategy_names: List of strategy names to compare
    
    Example:
        POST /api/compare
        {
            "strategy_names": ["Strategy1", "Strategy2", "Strategy3"]
        }
    """
    if not strategy_names:
        raise HTTPException(
            status_code=400,
            detail="No strategies specified"
        )
    
    reader = get_current_analysis_reader()
    
    # Get summaries for selected strategies
    comparisons = []
    not_found = []
    
    for name in strategy_names:
        summary = reader.get_summary(name)
        
        if not summary:
            not_found.append(name)
            continue
        
        comparisons.append(StrategyComparison(
            strategy_name=summary['strategy_name'],
            total_return_pct=float(summary.get('total_return_pct', 0)),
            sharpe_ratio=float(summary.get('sharpe_ratio', 0)),
            win_rate_pct=float(summary.get('win_rate_pct', 0)),
            max_drawdown_pct=float(summary.get('max_drawdown_pct', 0)),
            profit_factor=float(summary.get('profit_factor', 0)),
            completed_trades=int(summary.get('completed_trades', 0))
        ))
    
    if not comparisons:
        raise HTTPException(
            status_code=404,
            detail=f"Strategies not found: {', '.join(not_found)}"
        )
    
    # Sort by return
    comparisons.sort(key=lambda x: x.total_return_pct, reverse=True)
    
    # Find best performers
    best_return = max(comparisons, key=lambda x: x.total_return_pct).strategy_name
    best_sharpe = max(comparisons, key=lambda x: x.sharpe_ratio).strategy_name
    best_win_rate = max(comparisons, key=lambda x: x.win_rate_pct).strategy_name
    lowest_drawdown = max(comparisons, key=lambda x: x.max_drawdown_pct).strategy_name
    
    result = ComparisonResult(
        strategies=comparisons,
        best_return=best_return,
        best_sharpe=best_sharpe,
        best_win_rate=best_win_rate,
        lowest_drawdown=lowest_drawdown
    )
    
    if not_found:
        return {
            **result.model_dump(),
            "warnings": {
                "not_found": not_found
            }
        }
    
    return result


@router.get("/metrics/{metric}")
async def compare_by_metric(
    metric: str,
    limit: Optional[int] = 10
):
    """
    Compare strategies by a specific metric
    
    Args:
        metric: Metric name (total_return_pct, sharpe_ratio, win_rate_pct, etc.)
        limit: Number of top strategies to return
    
    Supported metrics:
    - total_return_pct
    - sharpe_ratio
    - win_rate_pct
    - max_drawdown_pct
    - profit_factor
    - completed_trades
    """
    valid_metrics = [
        'total_return_pct',
        'sharpe_ratio',
        'win_rate_pct',
        'max_drawdown_pct',
        'profit_factor',
        'completed_trades'
    ]
    
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        )
    
    reader = get_current_analysis_reader()
    summaries = reader.get_all_summaries()
    
    if not summaries:
        raise HTTPException(
            status_code=404,
            detail="No strategies found"
        )
    
    # Sort by metric
    ascending = True if metric == 'max_drawdown_pct' else False
    sorted_summaries = sorted(
        summaries,
        key=lambda x: float(x.get(metric, 0)),
        reverse=not ascending
    )
    
    # Limit results
    if limit:
        sorted_summaries = sorted_summaries[:limit]
    
    # Format response
    results = []
    for s in sorted_summaries:
        results.append({
            'strategy_name': s['strategy_name'],
            metric: float(s.get(metric, 0)),
            'rank': len(results) + 1
        })
    
    return {
        'metric': metric,
        'strategies': results,
        'count': len(results)
    }


@router.get("/table")
async def get_comparison_table():
    """
    Get comparison data in table format
    
    Returns all key metrics for all strategies in a table-friendly format
    """
    reader = get_current_analysis_reader()
    
    comparison_df = reader.compare_strategies()
    
    if comparison_df.empty:
        raise HTTPException(
            status_code=404,
            detail="No strategies found"
        )
    
    return {
        'columns': comparison_df.columns.tolist(),
        'data': comparison_df.to_dict('records'),
        'count': len(comparison_df)
    }