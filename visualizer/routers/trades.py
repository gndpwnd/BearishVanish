"""
Trades Router
Endpoints for detailed trade history and analysis
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import io
from pathlib import Path
import sqlite3

from routers.analyses import get_current_analysis_reader
from database.simulation_reader import SimulationReader
from config import settings
from models.responses import Trade, TradeList, TradeStatistics


router = APIRouter()


def get_simulation_reader(strategy_name: str) -> SimulationReader:
    """
    Get simulation reader for detailed trade data
    
    Finds the source simulation database from analysis metadata
    """
    analysis_reader = get_current_analysis_reader()
    metadata = analysis_reader.get_metadata()
    
    sim_name = metadata.get('source_simulation')
    if not sim_name:
        raise HTTPException(
            status_code=404,
            detail="Source simulation not specified in analysis metadata"
        )
    
    # Try multiple possible locations
    possible_paths = [
        settings.simulation_db_dir / sim_name,
        Path('../simulator/simulations') / sim_name,
        Path('../../simulator/simulations') / sim_name,
    ]
    
    sim_path = None
    for path in possible_paths:
        if path.exists():
            sim_path = path
            break
    
    if not sim_path:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation database not found: {sim_name}"
        )
    
    return SimulationReader(sim_path)


@router.get("/{strategy_name}")
async def get_trade_history(
    strategy_name: str,
    status: Optional[str] = Query(default=None, regex="^(OPEN|CLOSED)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000)
):
    """
    Get trade history for a strategy
    
    Args:
        status: Filter by trade status (OPEN, CLOSED, or None for all)
        page: Page number (starts at 1)
        page_size: Number of trades per page
    """
    try:
        reader = get_simulation_reader(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    
    # Get total count
    total = reader.get_trade_count(strategy_name, status=status)
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get trades
    trades_df = reader.get_trade_history(
        strategy_name,
        status=status,
        limit=page_size,
        offset=offset
    )
    
    # Convert to models
    trades = []
    for _, row in trades_df.iterrows():
        trade = Trade(
            trade_id=int(row.get('trade_id', 0)) if 'trade_id' in row else None,
            symbol=row['symbol'],
            strategy_name=row['strategy_name'],
            trade_status=row['trade_status'],
            entry_date=row['entry_date'].date() if 'entry_date' in row else None,
            entry_price=float(row['entry_price']),
            shares=int(row['shares']),
            entry_value=float(row.get('entry_value', 0)),
            exit_date=row['exit_date'].date() if row['trade_status'] == 'CLOSED' and 'exit_date' in row else None,
            exit_price=float(row['exit_price']) if row['trade_status'] == 'CLOSED' else None,
            exit_value=float(row.get('exit_value', 0)) if row['trade_status'] == 'CLOSED' else None,
            profit_loss_dollars=float(row.get('profit_loss_dollars', 0)) if row['trade_status'] == 'CLOSED' else None,
            profit_loss_pct=float(row.get('profit_loss_pct', 0)) if row['trade_status'] == 'CLOSED' else None,
            holding_days=int(row.get('holding_days', 0)) if row['trade_status'] == 'CLOSED' else None,
            entry_reason=row.get('entry_reason'),
            exit_reason=row.get('exit_reason')
        )
        trades.append(trade)
    
    reader.close()
    
    return TradeList(
        trades=trades,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{strategy_name}/statistics", response_model=TradeStatistics)
async def get_trade_statistics(strategy_name: str):
    """
    Get trade statistics summary
    """
    try:
        reader = get_simulation_reader(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    
    # Get all trades
    all_trades = reader.get_trade_history(strategy_name)
    
    if all_trades.empty:
        reader.close()
        return TradeStatistics(
            total_trades=0,
            closed_trades=0,
            open_positions=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            avg_win=0.0,
            avg_loss=0.0
        )
    
    # Calculate statistics
    closed = all_trades[all_trades['trade_status'] == 'CLOSED']
    open_pos = all_trades[all_trades['trade_status'] == 'OPEN']
    
    winning = closed[closed['profit_loss_dollars'] > 0]
    losing = closed[closed['profit_loss_dollars'] < 0]
    
    win_rate = (len(winning) / len(closed) * 100) if len(closed) > 0 else 0
    total_pnl = closed['profit_loss_dollars'].sum() if not closed.empty else 0
    avg_win = winning['profit_loss_dollars'].mean() if not winning.empty else 0
    avg_loss = losing['profit_loss_dollars'].mean() if not losing.empty else 0
    
    reader.close()
    
    return TradeStatistics(
        total_trades=len(all_trades),
        closed_trades=len(closed),
        open_positions=len(open_pos),
        winning_trades=len(winning),
        losing_trades=len(losing),
        win_rate=float(win_rate),
        total_pnl=float(total_pnl),
        avg_win=float(avg_win),
        avg_loss=float(avg_loss)
    )


@router.get("/{strategy_name}/closed")
async def get_closed_trades(
    strategy_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000)
):
    """
    Get only closed trades
    """
    return await get_trade_history(strategy_name, status="CLOSED", page=page, page_size=page_size)


@router.get("/{strategy_name}/open")
async def get_open_positions(strategy_name: str):
    """
    Get only open positions
    """
    return await get_trade_history(strategy_name, status="OPEN", page=1, page_size=1000)


@router.get("/{strategy_name}/best")
async def get_best_trades(
    strategy_name: str,
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get best trades by profit percentage
    """
    try:
        reader = get_simulation_reader(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    
    best = reader.get_best_trades(strategy_name, limit=limit)
    reader.close()
    
    return {
        "trades": best.to_dict('records')
    }


@router.get("/{strategy_name}/worst")
async def get_worst_trades(
    strategy_name: str,
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get worst trades by profit percentage
    """
    try:
        reader = get_simulation_reader(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    
    worst = reader.get_worst_trades(strategy_name, limit=limit)
    reader.close()
    
    return {
        "trades": worst.to_dict('records')
    }


@router.get("/{strategy_name}/export")
async def export_trades_csv(
    strategy_name: str,
    status: Optional[str] = Query(default=None, regex="^(OPEN|CLOSED)$")
):
    """
    Export trade history as CSV
    
    Args:
        status: Filter by trade status (OPEN, CLOSED, or None for all)
    """
    try:
        reader = get_simulation_reader(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    
    # Get all trades (no pagination for export)
    trades = reader.get_trade_history(strategy_name, status=status)
    reader.close()
    
    if trades.empty:
        raise HTTPException(
            status_code=404,
            detail="No trades found"
        )
    
    # Convert to CSV
    output = io.StringIO()
    trades.to_csv(output, index=False)
    output.seek(0)
    
    # Determine filename
    status_suffix = f"_{status.lower()}" if status else ""
    filename = f"{strategy_name}_trades{status_suffix}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )