"""
FastAPI Trading Dashboard - Main Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import traceback
from pathlib import Path

from config import settings, discover_analysis_databases, discover_simulation_databases
from models.responses import ErrorResponse, HealthCheck
from routers import analyses, strategies, trades, charts, comparison


# ============================================================================
# Lifespan Events (defined before app creation)
# ============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("=" * 80)
    print(f"🚀 {settings.app_name} v{settings.version}")
    print("=" * 80)
    
    # Check database directories
    analysis_dbs = discover_analysis_databases()
    simulation_dbs = discover_simulation_databases()
    
    print(f"📊 Analysis databases: {len(analysis_dbs)}")
    print(f"🎯 Simulation databases: {len(simulation_dbs)}")
    
    if not analysis_dbs:
        print("⚠️  Warning: No analysis databases found!")
        print(f"   Expected location: {settings.analysis_db_dir}")
    
    print(f"🌐 Server running on http://{settings.host}:{settings.port}")
    print(f"📚 API docs at http://{settings.host}:{settings.port}/docs")
    print(f"🎨 Dashboard at http://{settings.host}:{settings.port}/")
    print("=" * 80)
    
    yield
    
    # Shutdown
    print("\n👋 Shutting down...")


# ============================================================================
# Create FastAPI App
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="API for visualizing trading strategy performance",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ============================================================================
# Mount Static Files
# ============================================================================

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    error_detail = str(exc)
    
    if settings.debug:
        error_detail = traceback.format_exc()
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=error_detail
        ).model_dump()
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors"""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Resource Not Found",
            detail=str(exc)
        ).model_dump()
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="Invalid Request",
            detail=str(exc)
        ).model_dump()
    )


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(
    analyses.router,
    prefix="/api/analyses",
    tags=["Analyses"]
)

app.include_router(
    strategies.router,
    prefix="/api/strategies",
    tags=["Strategies"]
)

app.include_router(
    trades.router,
    prefix="/api/trades",
    tags=["Trades"]
)

app.include_router(
    charts.router,
    prefix="/api/charts",
    tags=["Charts"]
)

app.include_router(
    comparison.router,
    prefix="/api/compare",
    tags=["Comparison"]
)


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve the main dashboard HTML"""
    html_file = Path("templates/index.html")
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>Dashboard HTML not found</h1><p>Please ensure templates/index.html exists</p>",
            status_code=404
        )


@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """Health check endpoint"""
    analysis_dbs = discover_analysis_databases()
    simulation_dbs = discover_simulation_databases()
    
    return HealthCheck(
        status="healthy",
        version=settings.version,
        databases={
            "analysis": len(analysis_dbs),
            "simulation": len(simulation_dbs)
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )