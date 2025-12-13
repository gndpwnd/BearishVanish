"""Remove stocks with insufficient data"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "offline_data" / "stock_data.db"

MIN_BARS = 100

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    DELETE FROM stock_bars
    WHERE symbol IN (
        SELECT symbol
        FROM stock_bars
        GROUP BY symbol
        HAVING COUNT(*) < ?
    )
""", (MIN_BARS,))

deleted = cursor.rowcount
conn.commit()

cursor.execute("""
    DELETE FROM symbol_metadata
    WHERE symbol NOT IN (SELECT DISTINCT symbol FROM stock_bars)
""")
conn.commit()

print(f"✅ Deleted {deleted} bars from stocks with insufficient data")

cursor.execute("VACUUM")
print("✅ Database optimized")

conn.close()
