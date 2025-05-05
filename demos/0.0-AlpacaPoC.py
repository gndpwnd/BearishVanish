import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import time
import hashlib

# Load environment variables
load_dotenv()

datadir = 'data/AlpacaPoC'

def ensure_data_directory():
    """Ensure data/AlpacaPoC directory exists"""
    os.makedirs(datadir, exist_ok=True)
    return datadir

def generate_unique_id(length=12):
    """Generate a unique ID that doesn't collide with existing files/folders in datadir"""
    existing_ids = set()

    # Traverse all files and extract potential ID prefixes
    for root, _, files in os.walk(datadir):
        for file in files:
            if "_" in file:
                prefix = file.split("_", 1)[0]
                if len(prefix) == length:
                    existing_ids.add(prefix)

    # Generate a new, non-colliding ID
    while True:
        new_id = hashlib.sha256(os.urandom(32)).hexdigest()[:length]
        if new_id not in existing_ids:
            return new_id
        
def get_last_week_monday_to_monday():
    """Calculate the date range for last Monday to this Monday"""
    today = datetime.now().date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    return last_monday, this_monday

def fetch_stock_data(symbols, start_date, end_date):
    """
    Fetch stock data using Alpaca's v2 API with proper request models
    Args:
        symbols: List of stock symbols (e.g., ['AAPL', 'MSFT'])
        start_date: Start date (datetime.date)
        end_date: End date (datetime.date)
    Returns:
        pandas.DataFrame with the historical data
    """
    client = StockHistoricalDataClient(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY')
    )
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time())
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_datetime,
        end=end_datetime
    )
    
    bars = client.get_stock_bars(request_params)
    return bars.df

def get_latest_quotes(symbols):
    """Get latest quotes for given symbols"""
    client = StockHistoricalDataClient(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY')
    )
    
    request_params = StockLatestQuoteRequest(
        symbol_or_symbols=symbols
    )
    
    quotes = client.get_stock_latest_quote(request_params)
    return quotes

from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

def make_trade(symbol, qty=1, take_profit_pct=1.01, stop_loss_pct=0.99):
    """
    Place a bracket order to buy and automatically sell with take profit and stop loss.
    Args:
        symbol: Stock symbol to trade
        qty: Quantity to trade
        take_profit_pct: Multiplier for take profit (e.g., 1.01 = 1% gain)
        stop_loss_pct: Multiplier for stop loss (e.g., 0.99 = 1% loss)
    """
    trading_client = TradingClient(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY'),
        paper=True  # Use paper trading
    )

    # Fetch the latest quote for accurate pricing
    quote = get_latest_quotes([symbol])[symbol]
    current_price = quote.ask_price or quote.bid_price
    if current_price is None:
        raise ValueError(f"Could not fetch a valid quote for {symbol}.")

    # Define take profit and stop loss prices
    take_profit_price = round(current_price * take_profit_pct, 2)
    stop_loss_price = round(current_price * stop_loss_pct, 2)

    print(f"\nPlacing bracket order for {qty} share(s) of {symbol} at ${current_price}")
    print(f"Take Profit: ${take_profit_price}, Stop Loss: ${stop_loss_price}")

    # Prepare bracket market order
    bracket_order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC,
        order_class="bracket",
        take_profit={"limit_price": take_profit_price},
        stop_loss={"stop_price": stop_loss_price}
    )

    order = trading_client.submit_order(order_data=bracket_order)
    print(f"Bracket Order ID: {order.id}")
    print(f"Order Status: {order.status}")

    return order


def save_to_csv(data, filename, data_dir):
    """Save DataFrame to CSV with a unique ID prepended"""
    unique_id = generate_unique_id()
    filename_with_id = f"{unique_id}_{filename}"
    filepath = os.path.join(data_dir, filename_with_id)
    data.to_csv(filepath)
    return filepath


def main():
    try:
        # Verify API keys are loaded
        if not all([os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY')]):
            raise ValueError("Missing API credentials. Please check your .env file")
        
        # Ensure data directory exists
        data_dir = ensure_data_directory()
        print(f"Data will be saved in: {os.path.abspath(data_dir)}")
        
        # Define the stocks we want
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        # 1. Market Data - Get historical data
        start_date, end_date = get_last_week_monday_to_monday()
        print(f"\n1. Fetching historical data from {start_date} to {end_date}")
        stock_data = fetch_stock_data(symbols, start_date, end_date)
        
        if not stock_data.empty:
            print("\nHistorical Data Preview:")
            print(stock_data.head())
            
            # Save to CSV
            csv_filename = f"stock_data_{start_date}_to_{end_date}.csv"
            saved_path = save_to_csv(stock_data, csv_filename, data_dir)
            print(f"\nData successfully saved to: {saved_path}")
        else:
            print("No historical data was fetched.")
        
        # 2. Stock Information - Get latest quotes
        print("\n2. Fetching latest quotes...")
        quotes = get_latest_quotes(symbols)
        
        print("\nLatest Quotes:")
        for symbol in symbols:
            quote = quotes[symbol]
            print(f"{symbol}: Ask ${quote.ask_price} (Size: {quote.ask_size}) | Bid ${quote.bid_price} (Size: {quote.bid_size})")
        
        # 3. Trading - Make a test trade (buy then sell)
        print("\n3. Making test trade...")
        test_symbol = 'AAPL'  # Using AAPL for the test trade
        buy_order, sell_order = make_trade(test_symbol)
        
        print("\nProof of Concept Complete!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()