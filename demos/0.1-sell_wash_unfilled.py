from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
import os
from dotenv import load_dotenv

# sell one share of APPL, if you own it, otherwise cancel unfilled orders of that stock

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')

# Initialize the TradingClient with paper=True for paper trading
trading_client = TradingClient(api_key, secret_key, paper=True)

# Check if you have a position for a given symbol
def has_position(symbol):
    positions = trading_client.get_all_positions()
    for position in positions:
        if position.symbol == symbol:
            return True
    return False

# Cancel unfilled orders for a given symbol
def cancel_unfilled_orders(symbol):
    print(f"Checking for unfilled orders for {symbol}...")
    
    # Fetch open orders with the status OPEN (unfilled) and side=BUY
    request_params = GetOrdersRequest(status=QueryOrderStatus.OPEN, side=OrderSide.BUY)
    orders = trading_client.get_orders(filter=request_params)
    
    # Create a list of orders to cancel (filter by symbol)
    orders_to_cancel = [order for order in orders if order.symbol == symbol]
    
    if orders_to_cancel:
        # Attempt to cancel each unfilled order individually
        for order in orders_to_cancel:
            try:
                cancel_status = trading_client.cancel_order_by_id(order.id)
                
                # Check if cancel_status is valid before accessing success attribute
                if cancel_status is not None and hasattr(cancel_status, 'success'):
                    if cancel_status.success:
                        print(f"Canceled unfilled buy order {order.id} for {symbol}")
                    else:
                        print(f"Failed to cancel order {order.id} for {symbol}")
                else:
                    print(f"Received invalid response while canceling order {order.id} for {symbol}")
            except Exception as e:
                print(f"Error canceling order {order.id}: {str(e)}")
    else:
        print(f"No unfilled orders found for {symbol}")


# Submit a sell order
def sell_share(symbol, qty=1):
    print(f"Placing sell order for {qty} share(s) of {symbol}...")
    
    # Create a market sell order
    market_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    
    # Submit the sell order
    market_order = trading_client.submit_order(order_data=market_order_data)
    print(f"Sell order submitted: {market_order.id}")

def main():
    symbol = "AAPL"
    
    # Check if the user has a position in the symbol
    if has_position(symbol):
        # Sell the share if the user has a position
        sell_share(symbol)
    else:
        # Cancel unfilled orders if you don't own the stock
        cancel_unfilled_orders(symbol)
    
if __name__ == "__main__":
    main()
