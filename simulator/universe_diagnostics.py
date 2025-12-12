"""
Universe Diagnostics Module
Troubleshooting tools for stock universe mismatches and data issues
"""

import pandas as pd
from datetime import datetime

class UniverseDiagnostics:
    def __init__(self, universe_manager):
        """
        Initialize diagnostics with universe manager instance
        
        Args:
            universe_manager: UniverseManager instance
        """
        self.universe_manager = universe_manager
    
    def diagnose_mismatch(self, universe_name):
        """
        Diagnose why fetched count doesn't match database count
        Shows which stocks are in source but not in database, and vice versa
        
        Args:
            universe_name: 'sp500', 'nasdaq100', or 'russell3000'
        """
        print(f"\n{'='*70}")
        print(f"DIAGNOSING {universe_name.upper()} MISMATCH")
        print(f"{'='*70}")
        
        # Fetch current tickers from source
        if universe_name == 'sp500':
            source_tickers, _ = self.universe_manager._fetch_sp500()
        elif universe_name == 'nasdaq100':
            source_tickers, _ = self.universe_manager._fetch_nasdaq100()
        elif universe_name == 'russell3000':
            source_tickers, _ = self.universe_manager._fetch_russell3000()
        else:
            print(f"❌ Unknown universe: {universe_name}")
            return
        
        if not source_tickers:
            print(f"❌ Failed to fetch {universe_name}")
            return
        
        # Get database tickers
        db_tickers = self.universe_manager.get_approved_tickers(universe_name)
        
        # Convert to sets for comparison
        source_set = set(ticker.strip().upper() for ticker in source_tickers)
        db_set = set(ticker.strip().upper() for ticker in db_tickers)
        
        # Find differences
        in_source_not_db = source_set - db_set
        in_db_not_source = db_set - source_set
        
        print(f"\n📊 COUNTS:")
        print(f"  Source (fetched):     {len(source_set)} unique tickers")
        print(f"  Database (active):    {len(db_set)} unique tickers")
        print(f"  Difference:           {abs(len(source_set) - len(db_set))} stocks")
        
        if in_source_not_db:
            print(f"\n❌ IN SOURCE BUT NOT IN DATABASE ({len(in_source_not_db)} stocks):")
            for ticker in sorted(list(in_source_not_db)[:20]):
                print(f"  • {ticker}")
            if len(in_source_not_db) > 20:
                print(f"  • ... and {len(in_source_not_db) - 20} more")
        
        if in_db_not_source:
            print(f"\n⚠️  IN DATABASE BUT NOT IN SOURCE ({len(in_db_not_source)} stocks):")
            print(f"  (These might be recently removed or data issues)")
            for ticker in sorted(list(in_db_not_source)[:20]):
                print(f"  • {ticker}")
            if len(in_db_not_source) > 20:
                print(f"  • ... and {len(in_db_not_source) - 20} more")
        
        if not in_source_not_db and not in_db_not_source:
            print(f"\n✅ PERFECT MATCH - No differences found!")
        
        # Check for potential issues
        print(f"\n🔍 POTENTIAL ISSUES:")
        
        # Check for duplicates in source
        source_lower = [t.lower() for t in source_tickers]
        duplicates = set([t for t in source_lower if source_lower.count(t) > 1])
        if duplicates:
            print(f"  ⚠️  Duplicate tickers in source: {len(duplicates)}")
            for dup in sorted(list(duplicates)[:10]):
                count = source_lower.count(dup)
                print(f"    • {dup.upper()} appears {count} times")
        else:
            print(f"  ✅ No duplicates in source")
        
        # Check for special characters
        special_chars = [t for t in source_tickers if not t.replace('.', '').replace('-', '').isalnum()]
        if special_chars:
            print(f"\n  ℹ️  Tickers with special characters: {len(special_chars)}")
            for ticker in sorted(special_chars[:10]):
                print(f"    • {ticker}")
        
        print(f"\n{'='*70}\n")
    
    def analyze_ticker_format(self, tickers):
        """
        Analyze ticker format issues (special chars, lengths, etc.)
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            dict with format analysis
        """
        analysis = {
            'total': len(tickers),
            'with_dots': [],
            'with_dashes': [],
            'long_tickers': [],
            'short_tickers': [],
            'numeric': [],
            'special_chars': []
        }
        
        for ticker in tickers:
            if '.' in ticker:
                analysis['with_dots'].append(ticker)
            if '-' in ticker:
                analysis['with_dashes'].append(ticker)
            if len(ticker) > 5:
                analysis['long_tickers'].append(ticker)
            if len(ticker) <= 2:
                analysis['short_tickers'].append(ticker)
            if any(c.isdigit() for c in ticker):
                analysis['numeric'].append(ticker)
            if not ticker.replace('.', '').replace('-', '').isalnum():
                analysis['special_chars'].append(ticker)
        
        return analysis
    
    def compare_universes(self, universe1, universe2):
        """
        Compare two universes to find overlaps and unique stocks
        
        Args:
            universe1: First universe name ('sp500', 'nasdaq100', 'russell3000')
            universe2: Second universe name
        """
        print(f"\n{'='*70}")
        print(f"COMPARING {universe1.upper()} vs {universe2.upper()}")
        print(f"{'='*70}")
        
        tickers1 = set(self.universe_manager.get_approved_tickers(universe1))
        tickers2 = set(self.universe_manager.get_approved_tickers(universe2))
        
        overlap = tickers1.intersection(tickers2)
        unique1 = tickers1 - tickers2
        unique2 = tickers2 - tickers1
        
        print(f"\n📊 STATISTICS:")
        print(f"  {universe1.upper()}: {len(tickers1)} stocks")
        print(f"  {universe2.upper()}: {len(tickers2)} stocks")
        print(f"\n  Overlap: {len(overlap)} stocks ({len(overlap)/len(tickers1)*100:.1f}% of {universe1})")
        print(f"  Unique to {universe1}: {len(unique1)} stocks")
        print(f"  Unique to {universe2}: {len(unique2)} stocks")
        
        if overlap:
            print(f"\n📋 Sample overlap (first 10):")
            for ticker in sorted(list(overlap)[:10]):
                print(f"  • {ticker}")
        
        print(f"\n{'='*70}\n")
    
    def check_data_quality(self, universe_name):
        """
        Check data quality issues for a universe
        
        Args:
            universe_name: Universe to check
        """
        print(f"\n{'='*70}")
        print(f"DATA QUALITY CHECK: {universe_name.upper()}")
        print(f"{'='*70}")
        
        tickers = self.universe_manager.get_approved_tickers(universe_name)
        
        # Format analysis
        format_analysis = self.analyze_ticker_format(tickers)
        
        print(f"\n📊 FORMAT ANALYSIS:")
        print(f"  Total tickers: {format_analysis['total']}")
        
        if format_analysis['with_dots']:
            print(f"\n  Tickers with dots (.): {len(format_analysis['with_dots'])}")
            print(f"    Examples: {', '.join(format_analysis['with_dots'][:5])}")
        
        if format_analysis['with_dashes']:
            print(f"\n  Tickers with dashes (-): {len(format_analysis['with_dashes'])}")
            print(f"    Examples: {', '.join(format_analysis['with_dashes'][:5])}")
        
        if format_analysis['long_tickers']:
            print(f"\n  Long tickers (>5 chars): {len(format_analysis['long_tickers'])}")
            print(f"    Examples: {', '.join(format_analysis['long_tickers'][:5])}")
        
        if format_analysis['numeric']:
            print(f"\n  Tickers with numbers: {len(format_analysis['numeric'])}")
            print(f"    Examples: {', '.join(format_analysis['numeric'][:5])}")
        
        print(f"\n{'='*70}\n")
    
    def find_duplicate_issues(self, universe_name):
        """
        Find potential duplicate ticker issues
        (e.g., GOOGL/GOOG, BRK.A/BRK.B)
        
        Args:
            universe_name: Universe to check
        """
        print(f"\n{'='*70}")
        print(f"DUPLICATE ANALYSIS: {universe_name.upper()}")
        print(f"{'='*70}")
        
        tickers = self.universe_manager.get_approved_tickers(universe_name)
        
        # Find potential duplicates (same base ticker, different suffix)
        base_tickers = {}
        for ticker in tickers:
            # Extract base ticker (before . or -)
            base = ticker.split('.')[0].split('-')[0]
            if base not in base_tickers:
                base_tickers[base] = []
            base_tickers[base].append(ticker)
        
        # Find bases with multiple tickers
        duplicates = {base: ticks for base, ticks in base_tickers.items() if len(ticks) > 1}
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} potential duplicate groups:")
            for base, ticks in sorted(duplicates.items())[:20]:
                print(f"  • {base}: {', '.join(sorted(ticks))}")
            
            if len(duplicates) > 20:
                print(f"  • ... and {len(duplicates) - 20} more")
        else:
            print(f"\n✅ No duplicate issues found")
        
        print(f"\n{'='*70}\n")