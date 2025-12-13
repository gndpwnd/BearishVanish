"""Check for stocks with insufficient data"""
import sqlite3
from pathlib import Path

DB_PATH = Path('./offline_data/stock_data.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Find stocks with less than 100 bars
cursor.execute('''
    SELECT symbol, COUNT(*) as bar_count
    FROM stock_bars
    GROUP BY symbol
    HAVING bar_count < 100
    ORDER BY bar_count
''')

partial_data = cursor.fetchall()

if partial_data:
    print(f"\n⚠️  Found {len(partial_data)} stocks with insufficient data:")
    for symbol, count in partial_data[:20]:
        print(f"   {symbol}: {count} bars")
    
    if len(partial_data) > 20:
        print(f"   ... and {len(partial_data) - 20} more")
else:
    print("✅ All stocks have sufficient data")

conn.close()