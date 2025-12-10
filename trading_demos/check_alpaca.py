"""
Setup utility for BearishVanish trading bot
Helps verify API credentials and test connection
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from datetime import datetime, timedelta
import sys

def verify_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("✗ No .env file found")
        create = input("Would you like to create one? (y/n): ")
        if create.lower() == 'y':
            create_env_template()
            return False
        return False
    
    load_dotenv()
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        print("✗ ALPACA_API_KEY not set in .env file")
        return False
    
    if not secret_key or secret_key == 'your_secret_key_here':
        print("✗ ALPACA_SECRET_KEY not set in .env file")
        return False
    
    print("✓ .env file found with API credentials")
    return True


def test_trading_connection():
    """Test connection to Alpaca trading API"""
    try:
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        trading_client = TradingClient(api_key, secret_key, paper=True)
        
        # Get account info
        account = trading_client.get_account()
        
        print("\n" + "="*60)
        print("ALPACA ACCOUNT INFORMATION")
        print("="*60)
        print(f"Account Status:       {account.status}")
        print(f"Account Number:       {account.account_number}")
        print(f"Cash:                 ${float(account.cash):,.2f}")
        print(f"Portfolio Value:      ${float(account.portfolio_value):,.2f}")
        print(f"Buying Power:         ${float(account.buying_power):,.2f}")
        print(f"Pattern Day Trader:   {account.pattern_day_trader}")
        print("="*60 + "\n")
        
        print("✓ Successfully connected to Alpaca Trading API")
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to Alpaca Trading API: {e}")
        return False


def test_data_connection():
    """Test connection to Alpaca data API"""
    try:
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        data_client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get latest quote for AAPL
        request = StockLatestQuoteRequest(symbol_or_symbols=['AAPL'])
        quotes = data_client.get_stock_latest_quote(request)
        
        quote = quotes['AAPL']
        
        print("\n" + "="*60)
        print("SAMPLE DATA FETCH (AAPL)")
        print("="*60)
        print(f"Ask Price:            ${quote.ask_price}")
        print(f"Bid Price:            ${quote.bid_price}")
        print(f"Ask Size:             {quote.ask_size}")
        print(f"Bid Size:             {quote.bid_size}")
        print("="*60 + "\n")
        
        print("✓ Successfully connected to Alpaca Data API")
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to Alpaca Data API: {e}")
        return False


def check_positions():
    """Check current positions in paper trading account"""
    try:
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        trading_client = TradingClient(api_key, secret_key, paper=True)
        positions = trading_client.get_all_positions()
        
        if not positions:
            print("\nNo open positions in your paper trading account")
            return True
        
        print("\n" + "="*60)
        print("CURRENT POSITIONS")
        print("="*60)
        for pos in positions:
            pnl_pct = (float(pos.unrealized_plpc) * 100)
            print(f"\n{pos.symbol}:")
            print(f"  Quantity:           {pos.qty}")
            print(f"  Entry Price:        ${float(pos.avg_entry_price):.2f}")
            print(f"  Current Price:      ${float(pos.current_price):.2f}")
            print(f"  Market Value:       ${float(pos.market_value):,.2f}")
            print(f"  Unrealized P&L:     ${float(pos.unrealized_pl):,.2f} ({pnl_pct:+.2f}%)")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to get positions: {e}")
        return False


def check_orders():
    """Check open orders in paper trading account"""
    try:
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        trading_client = TradingClient(api_key, secret_key, paper=True)
        orders = trading_client.get_orders()
        
        if not orders:
            print("\nNo open orders in your paper trading account")
            return True
        
        print("\n" + "="*60)
        print("OPEN ORDERS")
        print("="*60)
        for order in orders:
            print(f"\n{order.symbol} - {order.side.value}:")
            print(f"  Order ID:           {order.id}")
            print(f"  Status:             {order.status}")
            print(f"  Quantity:           {order.qty}")
            print(f"  Order Type:         {order.order_type}")
            print(f"  Time in Force:      {order.time_in_force}")
            print(f"  Created:            {order.created_at}")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to get orders: {e}")
        return False


def main():
    """Main setup verification flow"""
    print("\n" + "="*60)
    print("BEARISHVANISH TRADING BOT - SETUP VERIFICATION")
    print("="*60 + "\n")
    
    # Step 1: Check .env file
    print("Step 1: Checking environment configuration...")
    if not verify_env_file():
        print("\nSetup incomplete. Please configure your .env file and run again.")
        return
    
    # Step 2: Test trading connection
    print("\nStep 2: Testing Alpaca Trading API connection...")
    if not test_trading_connection():
        print("\nConnection failed. Please check your API credentials.")
        return
    
    # Step 3: Test data connection
    print("\nStep 3: Testing Alpaca Data API connection...")
    if not test_data_connection():
        print("\nData connection failed. Please check your API credentials.")
        return
    
    # Step 4: Check current positions and orders
    print("\nStep 4: Checking current positions and orders...")
    check_positions()
    check_orders()
    
    print("\n" + "="*60)
    print("✓ SETUP COMPLETE - ALL SYSTEMS READY")
    print("="*60)
    print("\nYou can now run your trading strategies:")
    print("  python strat1.py   # S&P 500 Intersection Strategy")
    print("  python strat2.py   # Weekly Threshold Strategy")
    print("\nOr run backtests:")
    print("  python backtest_framework.py")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()