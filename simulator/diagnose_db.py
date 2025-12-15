# diagnose_db.py
import sqlite3
import sys
import os
from pathlib import Path

def find_latest_simulation_db():
    """Find the latest simulation database file"""
    sim_dir = Path("./simulations")
    if not sim_dir.exists():
        print("❌ simulations directory not found")
        return None
    
    db_files = list(sim_dir.glob("simulation_*.db"))
    if not db_files:
        print("❌ No simulation database files found")
        return None
    
    # Sort by modification time (newest first)
    latest_db = max(db_files, key=os.path.getmtime)
    return latest_db

def diagnose_database(db_path):
    """Diagnose database structure and content"""
    print(f"🔍 Diagnosing database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. List all tables
        print("\n📊 Tables in database:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        if not tables:
            print("   No tables found!")
            return
        
        for table in tables:
            table_name = table[0]
            print(f"\n  ┌─ {table_name}")
            
            # 2. Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  ├─ Columns: {len(columns)}")
            
            # 3. Count rows
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  ├─ Rows: {count}")
                
                # 4. Show sample data for small tables or empty ones
                if count > 0 and count <= 5:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    sample = cursor.fetchall()
                    print(f"  └─ Sample data:")
                    for row in sample:
                        print(f"     {row}")
                elif count == 0:
                    print(f"  └─ ❗ Table is empty")
                else:
                    # For larger tables, just show column names
                    col_names = [col[1] for col in columns]
                    print(f"  └─ Columns: {', '.join(col_names[:5])}...")
            
            except sqlite3.Error as e:
                print(f"  └─ ❗ Error reading table: {e}")
        
        print("\n" + "="*50)
        
        # 5. Specifically check strategy-related tables
        print("\n🔎 Checking strategy-related tables:")
        
        strategy_tables = ['strategy_performance', 'strategy_configs', 'trade_history']
        for table in strategy_tables:
            cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                status = "✅" if count > 0 else "❌ EMPTY"
                print(f"  {status} {table}: {count} rows")
                
                if count == 0 and table == 'strategy_performance':
                    print(f"     ⚠️  This is likely why 'No strategies found'")
            else:
                print(f"  ❌ {table}: Table does not exist")
        
        # 6. Check simulation_info
        print("\n📋 Checking simulation_info:")
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='simulation_info'")
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT * FROM simulation_info LIMIT 1")
            sim_info = cursor.fetchone()
            if sim_info:
                print(f"  ✅ Found simulation info")
                # Try to get column names
                cursor.execute("PRAGMA table_info(simulation_info)")
                cols = cursor.fetchall()
                col_names = [col[1] for col in cols]
                
                print(f"  Simulation ID: {sim_info[col_names.index('simulation_id')] if 'simulation_id' in col_names else 'N/A'}")
                print(f"  Start time: {sim_info[col_names.index('start_time')] if 'start_time' in col_names else 'N/A'}")
            else:
                print(f"  ❌ simulation_info table is empty")
        else:
            print(f"  ❌ simulation_info table does not exist")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

def main():
    # Find latest database
    db_path = find_latest_simulation_db()
    if not db_path:
        return
    
    print(f"📁 Latest database: {db_path.name}")
    print(f"📏 Size: {db_path.stat().st_size / 1024:.1f} KB")
    
    diagnose_database(db_path)
    
    # Also check if main.py has access issues
    print("\n" + "="*50)
    print("🛠️  Suggested fixes:")
    print("1. Make sure the database file exists and is readable")
    print("2. Check if tables follow the expected schema")
    print("3. Run this command to list all DBs:")
    print("   find ./simulations -name \"*.db\" -exec ls -la {} \\;")

if __name__ == "__main__":
    main()