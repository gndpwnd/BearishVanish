"""
Configuration settings for Trading Dashboard API
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    app_name: str = "Trading Strategy Dashboard API"
    version: str = "1.0.0"
    debug: bool = True
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # CORS Settings
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    # Database Paths (relative to backend directory)
    analysis_db_dir: Path = Path("../analysis/analysis_dbs")
    simulation_db_dir: Path = Path("../simulator/simulations")
    
    # Cache Settings
    enable_cache: bool = True
    cache_ttl: int = 300  # 5 minutes
    
    # API Settings
    max_page_size: int = 1000
    default_page_size: int = 100
    
    # Response Settings
    pretty_json: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# Helper functions
def get_analysis_db_path(filename: str) -> Path:
    """Get full path to analysis database"""
    return settings.analysis_db_dir / filename


def get_simulation_db_path(filename: str) -> Path:
    """Get full path to simulation database"""
    return settings.simulation_db_dir / filename


def discover_analysis_databases() -> list[Path]:
    """Find all analysis database files"""
    if not settings.analysis_db_dir.exists():
        return []
    
    return sorted(
        settings.analysis_db_dir.glob("analysis_*.db"),
        reverse=True  # Most recent first
    )


def discover_simulation_databases() -> list[Path]:
    """Find all simulation database files"""
    if not settings.simulation_db_dir.exists():
        return []
    
    return sorted(
        settings.simulation_db_dir.glob("*.db"),
        reverse=True
    )