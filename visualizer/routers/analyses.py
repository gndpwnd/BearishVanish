"""
Analyses Router
Endpoints for listing and selecting analysis databases
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime
import sqlite3

from config import discover_analysis_databases, get_analysis_db_path
from models.responses import AnalysisMetadata, AnalysisList
from database.analysis_reader import AnalysisReader


router = APIRouter()


# Cache for current analysis
_current_analysis = None
_current_analysis_reader = None


def get_current_analysis_reader() -> AnalysisReader:
    """Get the current analysis reader"""
    global _current_analysis_reader
    
    if _current_analysis_reader is None:
        # Default to latest
        databases = discover_analysis_databases()
        if not databases:
            raise HTTPException(
                status_code=404,
                detail="No analysis databases found"
            )
        
        _current_analysis_reader = AnalysisReader(databases[0])
    
    return _current_analysis_reader


@router.get("", response_model=AnalysisList)
async def list_analyses():
    """
    List all available analysis databases
    
    Returns list sorted by creation date (most recent first)
    """
    databases = discover_analysis_databases()
    
    analyses = []
    for db_path in databases:
        try:
            # Get metadata
            conn = sqlite3.connect(str(db_path))
            conn.text_factory = str  # ADD THIS LINE
            cursor = conn.cursor()
            
            cursor.execute("SELECT key, value FROM analysis_metadata")
            metadata = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM strategy_summary")
            num_strategies = cursor.fetchone()[0]
            
            conn.close()
            
            # Get file stats
            stat = db_path.stat()
            
            analyses.append(AnalysisMetadata(
                analysis_id=db_path.stem,
                filename=db_path.name,
                simulation_id=metadata.get('simulation_id', 'Unknown'),
                universe=metadata.get('universe', 'Unknown'),
                created_at=datetime.fromtimestamp(stat.st_mtime),
                num_strategies=num_strategies,
                size_kb=stat.st_size / 1024
            ))
            
        except Exception as e:
            print(f"Error reading {db_path}: {e}")
            continue
    
    return AnalysisList(
        analyses=analyses,
        count=len(analyses)
    )


@router.get("/latest", response_model=AnalysisMetadata)
async def get_latest_analysis():
    """
    Get metadata for the most recent analysis
    """
    analyses_list = await list_analyses()
    
    if not analyses_list.analyses:
        raise HTTPException(
            status_code=404,
            detail="No analysis databases found"
        )
    
    return analyses_list.analyses[0]


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    """
    Get detailed information about a specific analysis
    
    Args:
        analysis_id: Analysis database ID (filename without extension)
    """
    # Find the database
    databases = discover_analysis_databases()
    db_path = None
    
    for db in databases:
        if db.stem == analysis_id:
            db_path = db
            break
    
    if not db_path:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_id}' not found"
        )
    
    try:
        with AnalysisReader(db_path) as reader:
            metadata = reader.get_metadata()
            strategies = reader.get_strategies()
            
            return {
                "analysis_id": analysis_id,
                "filename": db_path.name,
                "metadata": metadata,
                "strategies": strategies,
                "num_strategies": len(strategies)
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading analysis: {str(e)}"
        )


@router.post("/select/{analysis_id}")
async def select_analysis(analysis_id: str):
    """
    Select an analysis database to use for subsequent requests
    
    This sets the current analysis context for other endpoints
    """
    global _current_analysis, _current_analysis_reader
    
    databases = discover_analysis_databases()
    db_path = None
    
    for db in databases:
        if db.stem == analysis_id:
            db_path = db
            break
    
    if not db_path:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_id}' not found"
        )
    
    try:
        # ⭐ FIX: Close old reader properly to avoid connection leaks
        if _current_analysis_reader:
            try:
                print(f"Closing previous analysis reader...")
                _current_analysis_reader.close()
                _current_analysis_reader = None
            except Exception as close_error:
                print(f"Warning: Error closing old reader: {close_error}")
        
        # Open new reader
        print(f"Opening analysis: {analysis_id}")
        _current_analysis_reader = AnalysisReader(db_path)
        _current_analysis = analysis_id
        
        return {
            "success": True,
            "message": f"Analysis '{analysis_id}' selected",
            "strategies": _current_analysis_reader.get_strategies()
        }
    
    except Exception as e:
        # Clean up on error
        if _current_analysis_reader:
            try:
                _current_analysis_reader.close()
            except:
                pass
            _current_analysis_reader = None
        
        raise HTTPException(
            status_code=500,
            detail=f"Error selecting analysis: {str(e)}"
        )

@router.get("/current/info")
async def get_current_analysis_info():
    """
    Get information about the currently selected analysis
    """
    reader = get_current_analysis_reader()
    
    return {
        "analysis_id": _current_analysis or "latest",
        "metadata": reader.get_metadata(),
        "strategies": reader.get_strategies(),
        "num_strategies": len(reader.get_strategies())
    }