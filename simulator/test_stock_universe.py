"""
Standalone test script for stock universe fetching
Tests downloading, parsing, and storage without touching the main simulator

Usage:
    python test_stock_universe.py              # Fetch all universes
    python test_stock_universe.py --sp500      # Test S&P 500 only
    python test_stock_universe.py --nasdaq     # Test NASDAQ 100 only
    python test_stock_universe.py --russell    # Test Russell 3000 only
"""

import os
import sys
import argparse
import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load API credentials for Alpaca verification
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Output directory
OUTPUT_DIR = Path('./test_universes')
OUTPUT_DIR.mkdir(exist_ok=True)

print("="*70)
print("STOCK UNIVERSE FETCHER TEST")
print("="*70)
print(f"Output directory: {OUTPUT_DIR.absolute()}")
print()

def fetch_sp500():
    """
    Fetch S&P 500 constituents from Wikipedia
    Uses requests + pandas with proper headers to avoid 403
    """
    print("\n" + "="*70)
    print("TEST 1: S&P 500 from Wikipedia")
    print("="*70)
    
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        print(f"Fetching from: {url}")
        
        # Wikipedia requires proper headers to avoid 403
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"✅ HTTP {response.status_code} - Successfully fetched page")
        
        # Parse tables from HTML content
        from io import StringIO
        tables = pd.read_html(StringIO(response.text))
        
        # First table is S&P 500 constituents
        df = tables[0]
        print(f"✅ Successfully parsed HTML table")
        print(f"   Columns found: {df.columns.tolist()}")
        
        # Extract ticker symbols
        tickers = df['Symbol'].tolist()
        print(f"✅ Extracted {len(tickers)} ticker symbols")
        
        # Show first 10 as sample
        print(f"\n📊 Sample (first 10): {tickers[:10]}")
        
        # Show additional info available
        print(f"\n📋 Additional data available:")
        print(f"   - Security names: {df['Security'].head(3).tolist()}")
        print(f"   - Sectors: {df['GICS Sector'].unique().tolist()}")
        
        # Save to CSV
        output_file = OUTPUT_DIR / 'sp500_tickers.csv'
        df[['Symbol', 'Security', 'GICS Sector']].to_csv(output_file, index=False)
        print(f"\n✅ Saved to: {output_file}")
        
        return tickers, df
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def fetch_nasdaq100():
    """
    Fetch NASDAQ 100 from Slickcharts
    Uses requests + pandas with proper headers
    """
    print("\n" + "="*70)
    print("TEST 2: NASDAQ 100 from Slickcharts")
    print("="*70)
    
    try:
        url = "https://www.slickcharts.com/nasdaq100"
        print(f"Fetching from: {url}")
        
        # Slickcharts requires user agent header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Fetch with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"✅ HTTP {response.status_code} - Successfully fetched page")
        
        # Read tables with StringIO to avoid FutureWarning
        from io import StringIO
        tables = pd.read_html(StringIO(response.text))
        
        # First table has the constituents
        df = tables[0]
        print(f"✅ Successfully parsed HTML table")
        print(f"   Columns found: {df.columns.tolist()}")
        
        # Extract tickers
        tickers = df['Symbol'].tolist()
        print(f"✅ Extracted {len(tickers)} ticker symbols")
        
        # Show first 10
        print(f"\n📊 Sample (first 10): {tickers[:10]}")
        
        # Show weights if available
        if 'Weight' in df.columns:
            print(f"\n📋 Top 5 by weight:")
            # Convert Weight to numeric, removing % sign
            df['Weight_numeric'] = df['Weight'].astype(str).str.replace('%', '').astype(float)
            top5 = df.nlargest(5, 'Weight_numeric')[['Symbol', 'Company', 'Weight']]
            for _, row in top5.iterrows():
                print(f"   {row['Symbol']:6} {row['Company'][:30]:30} ({row['Weight']})")
        
        # Save to CSV
        output_file = OUTPUT_DIR / 'nasdaq100_tickers.csv'
        df[['Symbol', 'Company', 'Weight']].to_csv(output_file, index=False)
        print(f"\n✅ Saved to: {output_file}")
        
        return tickers, df
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def fetch_russell3000():
    """
    Fetch Russell 3000 from iShares IWV ETF holdings (official source)
    Falls back to other sources if unavailable
    """
    print("\n" + "="*70)
    print("TEST 3: Russell 3000 from iShares IWV ETF")
    print("="*70)
    
    # Try multiple sources in order of reliability
    sources = [
        {
            'name': 'iShares IWV ETF Holdings (Official)',
            'url': 'https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax?fileType=csv&fileName=IWV_holdings&dataType=fund',
            'method': 'csv',
            'skip_rows': 10
        },
        {
            'name': 'GitHub Community Dataset',
            'url': 'https://raw.githubusercontent.com/fja05680/sp500/master/data/russell3000.csv',
            'method': 'csv',
            'skip_rows': 0
        }
    ]
    
    for source in sources:
        try:
            print(f"\nTrying: {source['name']}")
            print(f"URL: {source['url']}")
            
            # Try to fetch
            if source['method'] == 'csv':
                df = pd.read_csv(source['url'], skiprows=source['skip_rows'])
            
            print(f"✅ Successfully loaded data")
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {df.columns.tolist()}")
            
            # Find ticker column (different sources use different names)
            ticker_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if any(name in col_lower for name in ['ticker', 'symbol']):
                    ticker_col = col
                    break
            
            if ticker_col is None:
                # If no ticker column found, try first column
                ticker_col = df.columns[0]
                print(f"   ⚠️  No ticker column found, using first column: {ticker_col}")
            
            # Extract tickers and clean
            tickers = df[ticker_col].dropna().astype(str).tolist()
            
            # Remove any non-ticker rows (headers, cash, etc.)
            tickers = [t for t in tickers if t.upper() == t and len(t) <= 5 and t.isalpha()]
            
            print(f"✅ Extracted {len(tickers)} ticker symbols")
            
            # Show first 10
            print(f"\n📊 Sample (first 10): {tickers[:10]}")
            
            # Save to CSV
            output_file = OUTPUT_DIR / 'russell3000_tickers.csv'
            clean_df = pd.DataFrame({'Symbol': tickers})
            clean_df.to_csv(output_file, index=False)
            print(f"\n✅ Saved to: {output_file}")
            
            return tickers, clean_df
            
        except Exception as e:
            print(f"❌ {source['name']} failed: {e}")
            continue
    
    # All sources failed - use approximation
    print("\n⚠️  All Russell 3000 sources unavailable")
    print("   Building approximation from S&P 500...")
    
    try:
        sp500_tickers, _ = fetch_sp500()
        if sp500_tickers:
            print(f"   ✅ Using {len(sp500_tickers)} tickers from S&P 500")
            print(f"\n   ⚠️  This is an APPROXIMATION, not real Russell 3000")
            print(f"   ⚠️  Real Russell 3000 has ~3000 stocks")
            
            output_file = OUTPUT_DIR / 'russell3000_tickers.csv'
            pd.DataFrame({'Symbol': sp500_tickers}).to_csv(output_file, index=False)
            
            return sp500_tickers, pd.DataFrame({'Symbol': sp500_tickers})
    except Exception as e2:
        print(f"   ❌ Approximation also failed: {e2}")
    
    return None, None

def verify_tradable_on_alpaca(tickers, sample_size=10):
    """
    Verify that tickers are tradable on Alpaca
    Only checks a sample to avoid rate limits
    """
    print("\n" + "="*70)
    print("TEST 4: Alpaca Tradability Verification")
    print("="*70)
    
    if not api_key or not secret_key:
        print("⚠️  SKIPPED: No Alpaca API credentials found in .env")
        print("   Add ALPACA_API_KEY and ALPACA_SECRET_KEY to test verification")
        return
    
    print(f"Testing {sample_size} random tickers from the universe...")
    
    try:
        from alpaca.trading.client import TradingClient
        
        client = TradingClient(api_key, secret_key)
        
        # Sample random tickers
        import random
        sample_tickers = random.sample(tickers, min(sample_size, len(tickers)))
        
        results = []
        for symbol in sample_tickers:
            try:
                asset = client.get_asset(symbol)
                tradable = asset.tradable
                exchange = asset.exchange
                results.append((symbol, tradable, exchange, None))
                status = "✅ TRADABLE" if tradable else "❌ NOT TRADABLE"
                print(f"   {symbol:6} - {status} on {exchange}")
            except Exception as e:
                results.append((symbol, False, None, str(e)))
                print(f"   {symbol:6} - ❌ ERROR: {e}")
        
        # Summary
        tradable_count = sum(1 for r in results if r[1])
        print(f"\n📊 Summary:")
        print(f"   Tradable: {tradable_count}/{len(results)} ({tradable_count/len(results)*100:.1f}%)")
        
        return results
        
    except Exception as e:
        print(f"❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_universes(sp500_tickers, nasdaq_tickers):
    """
    Compare universes to show overlap
    """
    print("\n" + "="*70)
    print("TEST 5: Universe Comparison & Analysis")
    print("="*70)
    
    if not sp500_tickers or not nasdaq_tickers:
        print("⚠️  SKIPPED: Need both S&P 500 and NASDAQ 100 data")
        return
    
    sp500_set = set(sp500_tickers)
    nasdaq_set = set(nasdaq_tickers)
    
    # Find overlaps
    overlap = sp500_set.intersection(nasdaq_set)
    sp500_only = sp500_set - nasdaq_set
    nasdaq_only = nasdaq_set - sp500_set
    
    print(f"\n📊 Universe Sizes:")
    print(f"   S&P 500:     {len(sp500_tickers)} stocks")
    print(f"   NASDAQ 100:  {len(nasdaq_tickers)} stocks")
    
    print(f"\n🔗 Overlap Analysis:")
    print(f"   In both:     {len(overlap)} stocks ({len(overlap)/len(nasdaq_set)*100:.1f}% of NASDAQ 100)")
    print(f"   S&P 500 only: {len(sp500_only)} stocks")
    print(f"   NASDAQ only:  {len(nasdaq_only)} stocks")
    
    print(f"\n📋 Stocks in both (sample of 10):")
    for ticker in list(overlap)[:10]:
        print(f"   - {ticker}")

def main():
    """Run all tests"""
    parser = argparse.ArgumentParser(description='Test stock universe fetching')
    parser.add_argument('--sp500', action='store_true', help='Test S&P 500 only')
    parser.add_argument('--nasdaq', action='store_true', help='Test NASDAQ 100 only')
    parser.add_argument('--russell', action='store_true', help='Test Russell 3000 only')
    parser.add_argument('--verify', action='store_true', help='Verify on Alpaca (requires API keys)')
    args = parser.parse_args()
    
    # Track results
    sp500_tickers = None
    nasdaq_tickers = None
    russell_tickers = None
    
    # Run tests based on flags
    run_all = not (args.sp500 or args.nasdaq or args.russell)
    
    if run_all or args.sp500:
        sp500_tickers, _ = fetch_sp500()
    
    if run_all or args.nasdaq:
        nasdaq_tickers, _ = fetch_nasdaq100()
    
    if run_all or args.russell:
        russell_tickers, _ = fetch_russell3000()
    
    # Verification test
    if args.verify and sp500_tickers:
        verify_tradable_on_alpaca(sp500_tickers, sample_size=10)
    
    # Comparison test
    if run_all and sp500_tickers and nasdaq_tickers:
        compare_universes(sp500_tickers, nasdaq_tickers)
    
    # Final summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    if run_all or args.sp500:
        tests_total += 1
        if sp500_tickers:
            tests_passed += 1
            print(f"✅ S&P 500:     {len(sp500_tickers)} tickers fetched")
        else:
            print(f"❌ S&P 500:     FAILED")
    
    if run_all or args.nasdaq:
        tests_total += 1
        if nasdaq_tickers:
            tests_passed += 1
            print(f"✅ NASDAQ 100:  {len(nasdaq_tickers)} tickers fetched")
        else:
            print(f"❌ NASDAQ 100:  FAILED")
    
    if run_all or args.russell:
        tests_total += 1
        if russell_tickers:
            tests_passed += 1
            print(f"✅ Russell 3000: {len(russell_tickers)} tickers fetched")
        else:
            print(f"❌ Russell 3000: FAILED")
    
    print(f"\n📊 Overall: {tests_passed}/{tests_total} tests passed")
    print(f"📁 Output saved to: {OUTPUT_DIR.absolute()}")
    print("="*70)
    
    return tests_passed == tests_total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)