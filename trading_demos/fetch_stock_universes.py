"""
Stock Universe Fetcher
Helps you understand and download different stock universes for trading
"""

import pandas as pd
import requests
from io import StringIO
import os
from datetime import datetime


class StockUniverseFetcher:
    """Fetch and manage different stock universe lists"""
    
    def __init__(self):
        self.universes = {
            'sp500': {
                'name': 'S&P 500',
                'count': '~503 stocks',
                'description': 'Largest 500 US companies, ~80% of US market cap',
                'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            },
            'russell1000': {
                'name': 'Russell 1000',
                'count': '~1,000 stocks',
                'description': 'Largest 1,000 US companies, ~93% of US market cap',
                'url': 'https://en.wikipedia.org/wiki/Russell_1000_Index'
            },
            'russell3000': {
                'name': 'Russell 3000',
                'count': '~3,000 stocks',
                'description': 'Top 3,000 US companies, ~98% of US market cap',
                'url': 'https://en.wikipedia.org/wiki/Russell_3000_Index'
            },
            'nasdaq100': {
                'name': 'NASDAQ-100',
                'count': '100 stocks',
                'description': 'Largest 100 non-financial companies on NASDAQ',
                'url': 'https://en.wikipedia.org/wiki/Nasdaq-100'
            },
            'djia': {
                'name': 'Dow Jones Industrial Average',
                'count': '30 stocks',
                'description': '30 prominent US companies',
                'url': 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
            }
        }
    
    def print_universe_overview(self):
        """Print overview of all stock universes"""
        print("\n" + "="*80)
        print("STOCK UNIVERSE OVERVIEW")
        print("="*80)
        print("\nChoosing which stocks to trade depends on your strategy and resources:\n")
        
        for key, info in self.universes.items():
            print(f"{info['name']:30} | {info['count']:15} | {info['description']}")
        
        print("\n" + "-"*80)
        print("RECOMMENDATIONS BY STRATEGY TYPE:")
        print("-"*80)
        print("\n1. BEGINNER / LIMITED CAPITAL:")
        print("   → S&P 500 (503 stocks)")
        print("   → Focus on liquid, stable, large-cap companies")
        print("   → Lower risk, easier to analyze")
        
        print("\n2. INTERMEDIATE / MEDIUM CAPITAL:")
        print("   → Russell 1000 (1,000 stocks)")
        print("   → Includes large and mid-cap companies")
        print("   → Good balance of liquidity and opportunity")
        
        print("\n3. ADVANCED / HIGH CAPITAL:")
        print("   → Russell 3000 (3,000 stocks)")
        print("   → Includes small-cap companies")
        print("   → More opportunities but less liquid")
        
        print("\n4. ALGORITHMIC / HIGH-FREQUENCY:")
        print("   → Filter by liquidity (volume > 1M shares/day)")
        print("   → Focus on 500-2,000 most liquid stocks")
        print("   → Avoid penny stocks and low-volume securities")
        
        print("\n" + "-"*80)
        print("KEY CONSIDERATIONS:")
        print("-"*80)
        print("• Liquidity: Can you enter/exit without moving the price?")
        print("• Volatility: Does your strategy profit from price movement?")
        print("• Data costs: More stocks = more data to process")
        print("• Computing power: Can you analyze all stocks in real-time?")
        print("• Capital: Do you have enough to diversify across many stocks?")
        print("="*80 + "\n")
    
    def fetch_sp500_list(self):
        """Fetch S&P 500 companies from Wikipedia"""
        try:
            print("Fetching S&P 500 companies from Wikipedia...")
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            
            # Read all tables from the page
            tables = pd.read_html(url)
            
            # The first table contains the S&P 500 companies
            df = tables[0]
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            # Select relevant columns
            if 'Symbol' in df.columns:
                df = df[['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Date added', 'Founded']]
                df = df.rename(columns={'Security': 'Company', 'GICS Sector': 'Sector', 'GICS Sub-Industry': 'Industry'})
            
            print(f"✓ Successfully fetched {len(df)} S&P 500 companies")
            return df
            
        except Exception as e:
            print(f"✗ Error fetching S&P 500 list: {e}")
            return None
    
    def fetch_nasdaq100_list(self):
        """Fetch NASDAQ-100 companies from Wikipedia"""
        try:
            print("Fetching NASDAQ-100 companies from Wikipedia...")
            url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
            
            tables = pd.read_html(url)
            
            # Find the table with company information
            for table in tables:
                if 'Ticker' in table.columns or 'Symbol' in table.columns:
                    df = table
                    break
            
            # Clean up
            if 'Ticker' in df.columns:
                df = df.rename(columns={'Ticker': 'Symbol'})
            
            print(f"✓ Successfully fetched {len(df)} NASDAQ-100 companies")
            return df
            
        except Exception as e:
            print(f"✗ Error fetching NASDAQ-100 list: {e}")
            return None
    
    def create_custom_universe(self, min_market_cap=None, sectors=None, min_volume=None):
        """
        Create a custom stock universe with filters
        
        Parameters:
        - min_market_cap: Minimum market cap in billions (e.g., 10 for $10B+)
        - sectors: List of sectors to include (e.g., ['Technology', 'Healthcare'])
        - min_volume: Minimum average daily volume
        """
        print("\nCreating custom stock universe...")
        
        # Start with S&P 500 as base
        df = self.fetch_sp500_list()
        
        if df is None:
            return None
        
        print(f"Starting with {len(df)} stocks")
        
        # Apply filters
        if sectors:
            df = df[df['Sector'].isin(sectors)]
            print(f"After sector filter: {len(df)} stocks")
        
        # Note: Market cap and volume filtering would require real-time data
        # from Alpaca or another API
        
        return df
    
    def save_universe(self, df, filename):
        """Save stock universe to CSV"""
        if df is None:
            print("No data to save")
            return
        
        os.makedirs('data/universes', exist_ok=True)
        filepath = f'data/universes/{filename}'
        df.to_csv(filepath, index=False)
        print(f"✓ Saved to {filepath}")
        return filepath
    
    def get_trading_recommendations(self):
        """Get recommendations for which universe to trade"""
        print("\n" + "="*80)
        print("HOW PROFESSIONAL TRADERS CHOOSE STOCKS")
        print("="*80)
        
        print("\n📊 BY NUMBER OF STOCKS:")
        print("-"*80)
        print("• Day Traders:          50-200 stocks (high liquidity only)")
        print("• Swing Traders:        100-500 stocks (S&P 500 is common)")
        print("• Algorithmic Traders:  500-3,000 stocks (depends on strategy)")
        print("• Long-term Investors:  20-50 stocks (concentrated portfolio)")
        
        print("\n💡 FILTERING CRITERIA PROFESSIONALS USE:")
        print("-"*80)
        print("1. Liquidity Filter:")
        print("   • Average daily volume > 1 million shares")
        print("   • Market cap > $1 billion")
        print("   • Bid-ask spread < 0.1%")
        
        print("\n2. Sector Diversification:")
        print("   • Technology: 15-20%")
        print("   • Healthcare: 10-15%")
        print("   • Financials: 10-15%")
        print("   • Consumer: 10-15%")
        print("   • Other sectors: remaining allocation")
        
        print("\n3. Volatility Filter:")
        print("   • For mean reversion: High volatility (beta > 1.5)")
        print("   • For trend following: Medium volatility (beta 1.0-1.5)")
        print("   • For conservative: Low volatility (beta < 1.0)")
        
        print("\n4. Price Range:")
        print("   • Avoid penny stocks (< $5)")
        print("   • Optimal range: $20-$500")
        print("   • High-price stocks (> $500) have different dynamics")
        
        print("\n" + "="*80)
        print("ANSWER TO YOUR QUESTION: 'People trading 4,000 stocks'")
        print("="*80)
        print("\nThose are likely:")
        print("• Large hedge funds with massive computing infrastructure")
        print("• Market makers providing liquidity")
        print("• High-frequency trading firms with co-located servers")
        print("\nFor retail/small algo traders like us:")
        print("• START with 50-500 stocks (S&P 500 is perfect)")
        print("• FOCUS on strategy quality, not quantity")
        print("• SCALE UP gradually as you prove profitability")
        print("="*80 + "\n")


def main():
    """Main function to demonstrate usage"""
    fetcher = StockUniverseFetcher()
    
    # Show overview
    fetcher.print_universe_overview()
    
    # Get recommendations
    fetcher.get_trading_recommendations()
    
    # Fetch S&P 500
    print("\n" + "="*80)
    print("FETCHING S&P 500 STOCKS")
    print("="*80 + "\n")
    
    sp500 = fetcher.fetch_sp500_list()
    
    if sp500 is not None:
        print("\nS&P 500 Preview:")
        print(sp500.head(10))
        
        print("\n" + "-"*80)
        print("SECTOR BREAKDOWN:")
        print("-"*80)
        sector_counts = sp500['Sector'].value_counts()
        for sector, count in sector_counts.items():
            percentage = (count / len(sp500)) * 100
            print(f"{sector:30} | {count:3} stocks ({percentage:5.1f}%)")
        
        # Save to CSV
        print("\n" + "-"*80)
        choice = input("Save S&P 500 list to CSV? (y/n): ")
        if choice.lower() == 'y':
            timestamp = datetime.now().strftime("%Y%m%d")
            fetcher.save_universe(sp500, f'sp500_{timestamp}.csv')
            
            # Also save just the tickers for easy use
            tickers_only = sp500[['Symbol']]
            fetcher.save_universe(tickers_only, f'sp500_tickers_{timestamp}.csv')
            
            print("\nYou can now use these files in your trading strategies!")
            print("Example usage:")
            print("  symbols = pd.read_csv('data/universes/sp500_tickers_YYYYMMDD.csv')['Symbol'].tolist()")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR YOUR STRATEGIES")
    print("="*80)
    print("\nStrategy #1 (S&P 500 Intersection):")
    print("→ Test on S&P 500 stocks (503 stocks)")
    print("→ These are liquid and have reliable data")
    print("→ Your strategy compares to SPY, so S&P 500 makes sense")
    
    print("\nStrategy #2 (Weekly Threshold):")
    print("→ Start with top 100 S&P 500 stocks by market cap")
    print("→ These have the best liquidity for your $5-$10 trades")
    print("→ Expand to full S&P 500 as you scale")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()