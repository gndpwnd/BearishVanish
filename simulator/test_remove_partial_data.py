"""Remove stocks with insufficient data"""
import sqlite3
from pathlib import Path

DB_PATH = Path('./offline_data/stock_data.db')
MIN_BARS = 100

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Find and delete stocks with < 100 bars
cursor.execute('''
    DELETE FROM stock_bars
    WHERE symbol IN (
        SELECT symbol
        FROM stock_bars
        GROUP BY symbol
        HAVING COUNT(*) < ?
    )
''', (MIN_BARS,))

deleted = cursor.rowcount
conn.commit()

# Update metadata
cursor.execute('DELETE FROM symbol_metadata WHERE symbol NOT IN (SELECT DISTINCT symbol FROM stock_bars)')
conn.commit()

print(f"✅ Deleted {deleted} bars from stocks with insufficient data")

# Vacuum to reclaim space
cursor.execute('VACUUM')
print("✅ Database optimized")

conn.close()