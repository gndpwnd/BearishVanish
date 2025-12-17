"""
UTF-8 Helper Utilities
Provides safe UTF-8 handling for database operations
"""

import sqlite3
import json
from typing import Any


def get_utf8_connection(db_path: str) -> sqlite3.Connection:
    """Create SQLite connection with proper UTF-8 handling"""
    conn = sqlite3.connect(db_path)
    conn.text_factory = str  # Handle UTF-8 text properly
    conn.execute("PRAGMA encoding = 'UTF-8'")
    return conn


def ensure_utf8(value: Any) -> Any:
    """Ensure value is UTF-8 compatible string"""
    if value is None:
        return None
    
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return value.decode('latin-1')
            except:
                return value.decode('utf-8', errors='replace')
    
    if isinstance(value, str):
        try:
            value.encode('utf-8')
            return value
        except UnicodeEncodeError:
            return value.encode('utf-8', errors='replace').decode('utf-8')
    
    return str(value)


def sanitize_json(data: Any) -> str:
    """Convert data to UTF-8 safe JSON string"""
    def _clean(obj):
        if obj is None:
            return None
        elif isinstance(obj, (bytes, bytearray)):
            return ensure_utf8(obj)
        elif isinstance(obj, str):
            return ensure_utf8(obj)
        elif isinstance(obj, dict):
            return {_clean(k): _clean(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_clean(item) for item in obj]
        else:
            return obj
    
    cleaned_data = _clean(data)
    return json.dumps(cleaned_data, ensure_ascii=False)