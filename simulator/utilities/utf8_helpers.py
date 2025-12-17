"""
UTF-8 Safety Utilities
Shared across all database operations to ensure consistent UTF-8 handling
"""

import json
import sqlite3


def ensure_utf8(text):
    """
    Ensure a string is valid UTF-8
    
    Args:
        text: Input string (can be str, bytes, or None)
    
    Returns:
        UTF-8 encoded string or None
    """
    if text is None:
        return None
    
    if isinstance(text, bytes):
        # Try to decode bytes
        try:
            return text.decode('utf-8', errors='replace')
        except:
            return text.decode('latin-1', errors='replace')
    
    if not isinstance(text, str):
        text = str(text)
    
    # Ensure string is valid UTF-8 by encoding and decoding
    try:
        # This will catch any encoding issues
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # Replace problematic characters
        return text.encode('utf-8', errors='replace').decode('utf-8')


def sanitize_json(data):
    """
    Sanitize data before JSON serialization to ensure UTF-8 compatibility
    
    Args:
        data: Dictionary or object to serialize
    
    Returns:
        JSON string with UTF-8 safe encoding
    """
    if data is None:
        return None
    
    try:
        # First attempt: normal serialization
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError, UnicodeDecodeError):
        # Second attempt: sanitize the data
        if isinstance(data, dict):
            sanitized = {
                ensure_utf8(k): sanitize_value(v) 
                for k, v in data.items()
            }
        elif isinstance(data, list):
            sanitized = [sanitize_value(item) for item in data]
        else:
            sanitized = sanitize_value(data)
        
        try:
            return json.dumps(sanitized, ensure_ascii=False)
        except:
            # Final fallback: ASCII-only encoding
            return json.dumps(sanitized, ensure_ascii=True)


def sanitize_value(value):
    """
    Recursively sanitize values for JSON
    
    Args:
        value: Any value to sanitize
    
    Returns:
        Sanitized value safe for JSON serialization
    """
    if value is None:
        return None
    elif isinstance(value, (str, bytes)):
        return ensure_utf8(value)
    elif isinstance(value, dict):
        return {ensure_utf8(k): sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [sanitize_value(v) for v in value]
    elif isinstance(value, (int, float, bool)):
        return value
    else:
        return ensure_utf8(str(value))


def get_utf8_connection(db_path, **pragma_options):
    """
    Create SQLite connection with UTF-8 encoding and optional pragmas
    
    Args:
        db_path: Path to database file
        **pragma_options: Optional PRAGMA settings (e.g., journal_mode='WAL')
    
    Returns:
        sqlite3.Connection with UTF-8 settings
    """
    conn = sqlite3.connect(db_path)
    conn.text_factory = str  # Ensure strings are returned as str
    
    # Set UTF-8 encoding
    conn.execute("PRAGMA encoding = 'UTF-8'")
    
    # Apply optional pragmas
    for pragma, value in pragma_options.items():
        if isinstance(value, str):
            conn.execute(f"PRAGMA {pragma} = '{value}'")
        else:
            conn.execute(f"PRAGMA {pragma} = {value}")
    
    return conn


def clean_ticker(ticker):
    """
    Clean and validate ticker symbol (ASCII only)
    
    Args:
        ticker: Ticker symbol string
    
    Returns:
        Cleaned ticker symbol or None if invalid
    """
    if not ticker:
        return None
    
    # Ensure UTF-8 first
    ticker = ensure_utf8(ticker)
    
    # Strip whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Tickers should be ASCII only - remove any non-ASCII characters
    ticker = ''.join(c for c in ticker if ord(c) < 128)
    
    return ticker if ticker else None