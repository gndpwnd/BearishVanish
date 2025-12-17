"""
Enhanced Database Diagnostics - Deep Analysis v2.1
Fixed recommendations logic to match current database state
"""

import sqlite3
import sys
from pathlib import Path
import pandas as pd

def find_latest_simulation_db():
    """Find the latest simulation database file"""
    sim_dir = Path("../simulator/simulations")
    if not sim_dir.exists():
        sim_dir = Path("./simulations")
    
    if not sim_dir.exists():
        print("❌ simulations directory not found")
        return None
    
    db_files = list(sim_dir.glob("simulation_*.db"))
    if not db_files:
        print("❌ No simulation database files found")
        return None
    
    latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
    return latest_db

def analyze_table_deeply(cursor, table_name):
    """Deep analysis of a table"""
    print(f"\n{'='*70}")
    print(f"📊 DEEP ANALYSIS: {table_name}")
    print(f"{'='*70}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Total Rows: {count:,}")
    
    if count == 0:
        print("⚠️  Table is EMPTY - this may indicate a data recording issue")
        return
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    
    print(f"\nColumns ({len(col_names)}): {', '.join(col_names[:10])}...")
    
    # Sample data
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        samples = cursor.fetchall()
        
        if samples:
            print(f"\n📋 Sample Data (first 3 rows):")
            for i, row in enumerate(samples, 1):
                print(f"\n  Row {i}:")
                for col_name, value in zip(col_names[:5], row[:5]):
                    print(f"    {col_name}: {value}")
    except Exception as e:
        print(f"  ⚠️  Error reading samples: {e}")
    
    # Check for NULL values
    null_counts = {}
    for col in col_names[:10]:  # Check first 10 columns
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL")
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                null_counts[col] = null_count
        except:
            pass
    
    if null_counts:
        print(f"\n⚠️  NULL Values Detected:")
        for col, count in null_counts.items():
            print(f"    {col}: {count} NULL values ({count/max(count, 1)*100:.1f}%)")

def diagnose_trade_flow(cursor):
    """Diagnose the complete trade flow"""
    print(f"\n{'='*70}")
    print("🔍 TRADE FLOW DIAGNOSIS")
    print(f"{'='*70}")
    
    # Get strategy names
    cursor.execute("SELECT DISTINCT strategy_name FROM strategy_performance")
    strategies = [row[0] for row in cursor.fetchall()]
    
    if not strategies:
        print("❌ No strategies found in strategy_performance table")
        return
    
    print(f"\n📊 Found {len(strategies)} strategies:")
    for strat in strategies:
        print(f"  • {strat}")
    
    # For each strategy, trace the data flow
    for strategy in strategies:
        print(f"\n{'─'*70}")
        print(f"Strategy: {strategy}")
        print(f"{'─'*70}")
        
        # 1. Check trade_attempts
        cursor.execute("""
            SELECT COUNT(*), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
            FROM trade_attempts
            WHERE strategy_name = ?
        """, (strategy,))
        attempts = cursor.fetchone()
        total_attempts = attempts[0] if attempts else 0
        successful_attempts = attempts[1] if attempts else 0
        
        print(f"\n1️⃣ Trade Attempts:")
        print(f"   Total: {total_attempts:,}")
        print(f"   Successful: {successful_attempts:,}")
        print(f"   Rejected: {total_attempts - successful_attempts:,}")
        
        if total_attempts == 0:
            print("   ❌ NO TRADE ATTEMPTS RECORDED!")
        
        # 2. Check trade_history entries
        cursor.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN trade_status = 'OPEN' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN trade_status = 'CLOSED' THEN 1 ELSE 0 END)
            FROM trade_history
            WHERE strategy_name = ?
        """, (strategy,))
        trades = cursor.fetchone()
        total_trades = trades[0] if trades else 0
        open_trades = trades[1] if trades else 0
        closed_trades = trades[2] if trades else 0
        
        print(f"\n2️⃣ Trade History:")
        print(f"   Total Entries: {total_trades:,}")
        print(f"   Open: {open_trades or 0:,}")
        print(f"   Closed: {closed_trades or 0:,}")
        
        if total_trades == 0:
            print("   ❌ NO TRADES IN TRADE_HISTORY!")
            print("   🔍 Possible causes:")
            print("      • Strategy generates no signals (normal for some strategies)")
            print("      • All signals were rejected by portfolio constraints")
            print("      • Strategy logic may need adjustment")
        
        # 3. Check strategy_performance table
        cursor.execute("""
            SELECT total_trades, completed_trades, open_positions,
                   winning_trades, losing_trades, total_return_pct
            FROM strategy_performance
            WHERE strategy_name = ?
        """, (strategy,))
        perf = cursor.fetchone()
        
        if perf:
            print(f"\n3️⃣ Strategy Performance Record:")
            print(f"   total_trades: {perf[0]}")
            print(f"   completed_trades: {perf[1]}")
            print(f"   open_positions: {perf[2]}")
            print(f"   winning_trades: {perf[3]}")
            print(f"   losing_trades: {perf[4]}")
            print(f"   total_return_pct: {perf[5]:.2f}%")
            
            # Check for inconsistencies
            if perf[0] == 0 and total_trades > 0:
                print(f"\n   ❌ INCONSISTENCY DETECTED!")
                print(f"   strategy_performance.total_trades = 0")
                print(f"   but trade_history has {total_trades} entries")
                print(f"   🔍 This suggests database reading issue")
            elif perf[0] > 0 and perf[0] != total_trades:
                print(f"\n   ⚠️  PARTIAL INCONSISTENCY:")
                print(f"   strategy_performance.total_trades = {perf[0]}")
                print(f"   trade_history count = {total_trades}")
                print(f"   Difference: {abs(perf[0] - total_trades)} trades")
            elif perf[0] == total_trades:
                print(f"\n   ✅ Trade counts MATCH between tables")
        else:
            print(f"\n3️⃣ Strategy Performance Record: NOT FOUND")
        
        # 4. Check portfolio_history
        cursor.execute("""
            SELECT COUNT(*), MIN(portfolio_value), MAX(portfolio_value)
            FROM portfolio_history
            WHERE strategy_name = ?
        """, (strategy,))
        portfolio = cursor.fetchone()
        
        if portfolio:
            print(f"\n4️⃣ Portfolio History:")
            print(f"   Snapshots: {portfolio[0]:,}")
            print(f"   Min Value: ${portfolio[1]:,.2f}")
            print(f"   Max Value: ${portfolio[2]:,.2f}")
        
        # 5. Diagnostic summary
        print(f"\n📋 DIAGNOSTIC SUMMARY:")
        if total_attempts > 0 and total_trades == 0:
            print("   ⚠️  No trades executed despite attempts")
            print("   → This may be NORMAL for some strategies")
            print("   → Check strategy logic in strategies/ folder")
            print("   → Verify signals are being generated")
        elif total_trades > 0 and perf and perf[0] == 0:
            print("   ❌ CRITICAL: Trades in history but performance shows 0")
            print("   → finalize_strategy() not reading from database")
        elif total_trades > 0 and perf and perf[0] > 0:
            print("   ✅ Data flow looks correct!")
        else:
            print("   📊 Strategy has no trading activity")

def main():
    db_path = find_latest_simulation_db()
    if not db_path:
        return
    
    print(f"\n{'='*70}")
    print(f"DATABASE DIAGNOSTICS v2.1")
    print(f"{'='*70}")
    print(f"📁 Database: {db_path.name}")
    print(f"📏 Size: {db_path.stat().st_size / 1024:.1f} KB")
    print(f"🕐 Modified: {pd.Timestamp.fromtimestamp(db_path.stat().st_mtime)}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.text_factory = str  # Ensure UTF-8 compatibility
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Tables ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {table}: {count:,} rows")
        
        # Deep analysis of key tables
        critical_tables = ['trade_history', 'trade_attempts', 'strategy_performance', 'portfolio_history']
        for table in critical_tables:
            if table in tables:
                analyze_table_deeply(cursor, table)
        
        # Diagnose trade flow
        diagnose_trade_flow(cursor)
        
        # FINAL RECOMMENDATIONS (FIXED!)
        print(f"\n{'='*70}")
        print("💡 FINAL STATUS & RECOMMENDATIONS")
        print(f"{'='*70}")
        
        # Get comprehensive status
        cursor.execute("""
            SELECT 
                sp.strategy_name,
                sp.total_trades as perf_trades,
                COUNT(DISTINCT th.id) as actual_trades,
                COUNT(DISTINCT ta.id) as attempts,
                sp.total_return_pct,
                sp.win_rate_pct
            FROM strategy_performance sp
            LEFT JOIN trade_history th ON sp.strategy_name = th.strategy_name
            LEFT JOIN trade_attempts ta ON sp.strategy_name = ta.strategy_name
            GROUP BY sp.strategy_name
            ORDER BY sp.total_return_pct DESC
        """)
        
        strategies_status = cursor.fetchall()
        
        print("\n📊 STRATEGY PERFORMANCE SUMMARY:")
        print(f"{'Strategy':<20} {'Trades':<8} {'Attempts':<10} {'Return':<10} {'Win Rate':<10} {'Status':<10}")
        print("-" * 70)
        
        healthy_strategies = 0
        no_trade_strategies = 0
        issue_strategies = 0
        
        for strategy_name, perf_trades, actual_trades, attempts, return_pct, win_rate in strategies_status:
            # Check status
            if perf_trades == 0 and attempts == 0:
                status = "❌ NO DATA"
                issue_strategies += 1
            elif perf_trades == 0 and attempts > 0:
                status = "⚠️ NO TRADES"
                no_trade_strategies += 1
            elif perf_trades > 0 and perf_trades == actual_trades:
                status = "✅ HEALTHY"
                healthy_strategies += 1
            elif perf_trades > 0 and perf_trades != actual_trades:
                status = "❌ MISMATCH"
                issue_strategies += 1
            else:
                status = "📊 ACTIVE"
                healthy_strategies += 1
            
            print(f"{strategy_name:<20} {perf_trades:<8,} {attempts:<10,} {return_pct:<10.2f}% {win_rate or 0:<10.1f}% {status:<10}")
        
        print("-" * 70)
        
        # Overall assessment
        print(f"\n📈 OVERALL ASSESSMENT:")
        print(f"   ✅ Healthy strategies: {healthy_strategies}")
        print(f"   ⚠️  No-trade strategies: {no_trade_strategies}")
        print(f"   ❌ Issue strategies: {issue_strategies}")
        
        # Specific recommendations
        print(f"\n🔧 SPECIFIC RECOMMENDATIONS:")
        
        if healthy_strategies > 0:
            print(f"1. ✅ {healthy_strategies} strategy(ies) are working correctly")
            print("   • Trade counts match between tables")
            print("   • Performance metrics calculated properly")
            print("   • Analysis app will show correct statistics")
        
        if no_trade_strategies > 0:
            print(f"\n2. ⚠️  {no_trade_strategies} strategy(ies) have no trades:")
            print("   • This may be NORMAL for certain strategies")
            print("   • Some strategies generate few or no signals")
            print("   • Check strategy logic if you expect trades")
        
        if issue_strategies > 0:
            print(f"\n3. ❌ {issue_strategies} strategy(ies) have issues:")
            print("   • Trade counts don't match between tables")
            print("   • May need database fixes")
        
        # Final verification query
        print(f"\n📋 VERIFICATION QUERY:")
        print("   SELECT strategy_name, total_trades, completed_trades, open_positions,")
        print("          winning_trades, losing_trades, total_return_pct")
        print("   FROM strategy_performance;")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()