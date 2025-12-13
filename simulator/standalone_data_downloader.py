#!/usr/bin/env python3
"""
Lightweight Standalone Stock Data Downloader
Uses DataManager's hybrid download capabilities
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from data_manager import DataManager
from stock_universe import UniverseManager

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

def main():
    parser = argparse.ArgumentParser(
        description='Lightweight Stock Data Downloader using DataManager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Download S&P 500:
    python download_data.py --universe sp500
  
  Download with 1 year history:
    python download_data.py --universe sp500 --days 365
  
  Download all universes:
    python download_data.py --all-universes
  
  Force trickle mode:
    python download_data.py --universe sp500 --trickle-only
  
  Check cache:
    python download_data.py --cache-status
        """
    )
    
    # Input options
    parser.add_argument('--universe', type=str, 
                       help='Download universe: sp500, nasdaq100, russell3000')
    parser.add_argument('--all-universes', action='store_true',
                       help='Download all universes')
    parser.add_argument('--tickers', type=str,
                       help='Comma-separated list of tickers')
    
    # Time period options
    parser.add_argument('--days', type=int, default=180,
                       help='Number of days of historical data')
    parser.add_argument('--period', type=str, choices=['1month', '3months', '6months', '1year', '2years', '3years', '5years', 'max'],
                       help='Preset time period')
    
    # Download mode
    parser.add_argument('--trickle-only', action='store_true',
                       help='Force trickle mode from start')
    parser.add_argument('--workers', type=int, default=4,
                       help='Parallel workers before trickle mode')
    
    # Utility
    parser.add_argument('--cache-status', action='store_true',
                       help='Show cache status')
    parser.add_argument('--offline', action='store_true',
                       help='Offline mode')
    
    args = parser.parse_args()
    
    # Handle preset periods
    period_days = {
        '1month': 30, '3months': 90, '6months': 180,
        '1year': 365, '2years': 730, '3years': 1095,
        '5years': 1825, 'max': 2000
    }
    
    if args.period:
        args.days = period_days[args.period]
    
    # Initialize data manager
    data_manager = DataManager(api_key, secret_key, offline_mode=args.offline)
    
    if args.cache_status:
        data_manager.print_cache_status()
        return
    
    # Determine symbols
    symbols = []
    
    if args.all_universes:
        universe_manager = UniverseManager(api_key, secret_key)
        all_symbols = set()
        for univ in ['sp500', 'nasdaq100', 'russell3000']:
            univ_symbols = universe_manager.get_approved_tickers(univ)
            print(f"✅ {univ}: {len(univ_symbols)} stocks")
            all_symbols.update(univ_symbols)
        symbols = sorted(list(all_symbols)) + ['SPY']
        
    elif args.universe:
        universe_manager = UniverseManager(api_key, secret_key)
        symbols = universe_manager.get_approved_tickers(args.universe) + ['SPY']
        
    elif args.tickers:
        symbols = [t.strip().upper() for t in args.tickers.split(',')]
    
    else:
        print("❌ Specify --universe, --tickers, or --all-universes")
        return
    
    # Download using data manager's hybrid method
    print(f"\n📦 Downloading {len(symbols)} symbols ({args.days} days)...")
    
    data_manager.max_parallel_workers = args.workers
    
    results = data_manager.download_symbols_with_hybrid_mode(
        symbols=symbols,
        days=args.days,
        trickle_only=args.trickle_only
    )
    
    # Print summary
    successful = sum(1 for v in results.values() if v is not None)
    print(f"\n✅ Download complete: {successful}/{len(symbols)} successful")
    
    if successful > 0:
        data_manager.save_download_progress(symbols, args.days, results)
        print("💾 Progress saved")

if __name__ == '__main__':
    main()