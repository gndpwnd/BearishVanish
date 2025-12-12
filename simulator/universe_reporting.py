"""
Universe Reporting Module
Status displays, summaries, and reporting for stock universes
"""

import sqlite3
from datetime import datetime

class UniverseReporter:
    def __init__(self, universe_manager):
        """
        Initialize reporter with universe manager instance
        
        Args:
            universe_manager: UniverseManager instance
        """
        self.universe_manager = universe_manager
        self.db_path = universe_manager.db_path
    
    def print_status(self):
        """Print comprehensive status of all universes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print(f"\n{'='*70}")
        print(f"STOCK UNIVERSE STATUS")
        print(f"{'='*70}")
        print(f"Database: {self.db_path.absolute()}")
        
        # Get database size
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        print(f"Database size: {db_size_mb:.2f} MB")
        
        print(f"\n{'Universe':<15} {'Active':<10} {'Total Ever':<12} {'Last Updated':<15} {'Changes (30d)'}")
        print(f"{'-'*70}")
        
        for universe_name in ['sp500', 'nasdaq100', 'russell3000']:
            # Get active constituents count
            cursor.execute('''
                SELECT COUNT(DISTINCT symbol)
                FROM universe_constituents
                WHERE universe_name = ? AND date_removed IS NULL
            ''', (universe_name,))
            active_count = cursor.fetchone()[0]
            
            # Get total ever seen
            cursor.execute('''
                SELECT COUNT(DISTINCT symbol)
                FROM universe_constituents
                WHERE universe_name = ?
            ''', (universe_name,))
            total_count = cursor.fetchone()[0]
            
            # Get last update
            cursor.execute('''
                SELECT MAX(date)
                FROM daily_snapshots
                WHERE universe_name = ?
            ''', (universe_name,))
            last_update = cursor.fetchone()[0] or 'Never'
            
            # Get recent changes
            cursor.execute('''
                SELECT COUNT(*)
                FROM change_log
                WHERE universe_name = ? AND date >= date('now', '-30 days')
            ''', (universe_name,))
            recent_changes = cursor.fetchone()[0]
            
            print(f"{universe_name.upper():<15} {active_count:<10} {total_count:<12} {last_update:<15} {recent_changes}")
        
        # Show overlap statistics
        print(f"\n{'='*70}")
        print(f"OVERLAP STATISTICS")
        print(f"{'='*70}")
        
        # Get all active symbols across universes
        cursor.execute('''
            SELECT DISTINCT symbol
            FROM universe_constituents
            WHERE date_removed IS NULL
        ''')
        all_symbols = set(row[0] for row in cursor.fetchall())
        
        print(f"Total unique active symbols: {len(all_symbols)}")
        
        # Symbols in multiple universes
        cursor.execute('''
            SELECT symbol, COUNT(DISTINCT universe_name) as num_universes
            FROM universe_constituents
            WHERE date_removed IS NULL
            GROUP BY symbol
            HAVING COUNT(DISTINCT universe_name) > 1
            ORDER BY num_universes DESC
        ''')
        
        multi_universe = cursor.fetchall()
        
        if multi_universe:
            print(f"\nSymbols in multiple universes: {len(multi_universe)}")
            
            # Count by number of universes
            in_3 = sum(1 for _, count in multi_universe if count == 3)
            in_2 = sum(1 for _, count in multi_universe if count == 2)
            
            if in_3 > 0:
                print(f"  • In all 3 universes: {in_3} stocks")
            if in_2 > 0:
                print(f"  • In 2 universes: {in_2} stocks")
            
            # Show sample of stocks in all 3
            if in_3 > 0:
                cursor.execute('''
                    SELECT symbol
                    FROM universe_constituents
                    WHERE date_removed IS NULL
                    GROUP BY symbol
                    HAVING COUNT(DISTINCT universe_name) = 3
                    LIMIT 5
                ''')
                sample = [row[0] for row in cursor.fetchall()]
                print(f"\n  Sample stocks in all universes: {', '.join(sample)}")
        
        conn.close()
        print(f"\n{'='*70}\n")
    
    def print_ticker_info(self, symbol):
        """
        Print detailed information about a specific ticker
        
        Args:
            symbol: Stock ticker symbol
        """
        symbol = symbol.upper()
        
        print(f"\n{'='*70}")
        print(f"TICKER INFORMATION: {symbol}")
        print(f"{'='*70}")
        
        info = self.universe_manager.check_ticker(symbol)
        
        if not info['found']:
            print(f"\n❌ {symbol} not found in any universe")
            print(f"\n{'='*70}\n")
            return
        
        print(f"\n✅ {symbol} found in {len(info['universes'])} universe(s)\n")
        
        for univ_info in info['universes']:
            print(f"{univ_info['universe'].upper()}:")
            print(f"  Status: {univ_info['status']}")
            print(f"  Added: {univ_info['date_added']}")
            if univ_info['date_removed']:
                print(f"  Removed: {univ_info['date_removed']}")
            
            tradable = univ_info['is_tradable']
            if tradable == 'Not verified':
                print(f"  Tradable on Alpaca: ⏳ {tradable}")
            elif tradable:
                print(f"  Tradable on Alpaca: ✅ Yes")
            else:
                print(f"  Tradable on Alpaca: ❌ No")
            print()
        
        print(f"{'='*70}\n")
    
    def print_recent_changes(self, universe_name=None, days=30):
        """
        Print recent changes for a universe
        
        Args:
            universe_name: Specific universe or None for all
            days: Number of days to look back
        """
        changes = self.universe_manager.get_recent_changes(universe_name, days)
        
        print(f"\n{'='*70}")
        if universe_name:
            print(f"RECENT CHANGES: {universe_name.upper()} (Last {days} days)")
        else:
            print(f"RECENT CHANGES: ALL UNIVERSES (Last {days} days)")
        print(f"{'='*70}\n")
        
        if not changes:
            print("No changes in the specified period.")
        else:
            print(f"Total changes: {len(changes)}\n")
            
            for change in changes[:50]:  # Show first 50
                if universe_name:
                    date, symbol, action, reason = change
                    print(f"  {date}: {symbol} {action}")
                    if reason:
                        print(f"    Reason: {reason}")
                else:
                    universe, date, symbol, action, reason = change
                    print(f"  {date} [{universe.upper()}]: {symbol} {action}")
                    if reason:
                        print(f"    Reason: {reason}")
            
            if len(changes) > 50:
                print(f"\n  ... and {len(changes) - 50} more")
        
        print(f"\n{'='*70}\n")
    
    def print_summary(self, universe_name):
        """
        Print summary statistics for a universe
        
        Args:
            universe_name: Universe to summarize
        """
        info = self.universe_manager.get_universe_info(universe_name)
        
        print(f"\n{'='*70}")
        print(f"{universe_name.upper()} SUMMARY")
        print(f"{'='*70}")
        
        print(f"\nCurrent count: {info['current_count']} stocks")
        print(f"Last updated: {info['last_updated']}")
        print(f"Recent changes (30d): {info['recent_changes']}")
        
        # Show sample tickers
        print(f"\nSample tickers (first 20):")
        for ticker in sorted(info['tickers'])[:20]:
            print(f"  • {ticker}")
        
        if len(info['tickers']) > 20:
            print(f"  • ... and {len(info['tickers']) - 20} more")
        
        print(f"\n{'='*70}\n")