import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button, TextBox
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Alpaca clients
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
data_client = StockHistoricalDataClient(api_key, secret_key)
trading_client = TradingClient(api_key, secret_key, paper=True)

# Configuration
HISTORY = 49  # Last 49 days
end_date = datetime.now()
start_date = end_date - timedelta(days=HISTORY)

# Create figure and widgets
fig, ax = plt.subplots(figsize=(12, 8))
plt.subplots_adjust(bottom=0.25)
current_symbol = 'AAPL'

# Widget setup
ax_text = fig.add_axes([0.25, 0.05, 0.4, 0.05])
text_box = TextBox(ax_text, 'Symbol:', initial=current_symbol)
ax_submit = fig.add_axes([0.66, 0.05, 0.1, 0.05])
submit_btn = Button(ax_submit, 'Update')

# Trading buttons
button_width = 0.12
button_spacing = 0.02
start_x = 0.1
ax_buy = fig.add_axes([start_x, 0.12, button_width, 0.05])
ax_sell = fig.add_axes([start_x + button_width + button_spacing, 0.12, button_width, 0.05])
ax_cancel = fig.add_axes([start_x + 2*(button_width + button_spacing), 0.12, button_width, 0.05])
ax_stop = fig.add_axes([start_x + 3*(button_width + button_spacing), 0.12, button_width, 0.05])

buy_btn = Button(ax_buy, 'Buy ($5)')
sell_btn = Button(ax_sell, 'Sell ($10)')
cancel_btn = Button(ax_cancel, 'Cancel Orders')
stop_btn = Button(ax_stop, 'Exit')

def fetch_stock_data(symbol, timeframe=TimeFrame.Day):
    """Fetch historical data for a symbol"""
    symbol = symbol.upper()
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start_date,
        end=end_date
    )
    bars = data_client.get_stock_bars(request_params)
    df = bars.df

    if df.empty:
        raise ValueError(f"No data for {symbol}")

    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level=0)

    df.index = pd.to_datetime(df.index)
    return df

def calculate_weekly_signals(stock_data):
    """Calculate buy/sell signals based on weekly performance (Monday to Monday)."""
    signals = []
    # Resample data from Monday to Monday
    weekly_data = stock_data.resample('W-MON').agg({'open': 'first', 'close': 'last'})
    
    for week_end, row in weekly_data.iterrows():
        pct_change = (row['close'] - row['open']) / row['open'] * 100
        if pct_change <= -5:
            signals.append((week_end, 'buy', row['close']))
        elif pct_change >= 10:
            signals.append((week_end, 'sell', row['close']))
    return signals


def update_plot(symbol):
    """Update the plot with new data and signals."""
    global current_symbol
    current_symbol = symbol.upper()
    ax.clear()
    
    try:
        stock_data = fetch_stock_data(current_symbol)
    except ValueError as e:
        print(e)
        return

    # Plot daily closing prices
    ax.plot(stock_data.index, stock_data['close'], label=f'{current_symbol} Price', color='black')

    # Add trading signals
    signals = calculate_weekly_signals(stock_data)
    for date, signal_type, price in signals:
        if signal_type == 'buy':
            ax.plot(date, price, 'go', markersize=10, alpha=0.7, label='Buy Signal')
        elif signal_type == 'sell':
            ax.plot(date, price, 'ro', markersize=10, alpha=0.7, label='Sell Signal')

    # Formatting
    ax.set_title(f'{current_symbol} Price and Trading Signals ({HISTORY} Days)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price (USD)')
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)

    # Remove duplicate legend entries
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys())

    fig.canvas.draw_idle()


# Trading functions
def get_weekly_performance(symbol):
    """Get percentage change for the current week (Monday to Monday)."""
    today = datetime.now().date()
    last_monday = today - timedelta(days=today.weekday())
    next_monday = last_monday + timedelta(days=7)
    
    try:
        stock_data = fetch_stock_data(symbol)
        weekly_data = stock_data[(stock_data.index.date >= last_monday) & (stock_data.index.date < next_monday)]
        if not weekly_data.empty:
            open_price = weekly_data.iloc[0]['open']
            close_price = weekly_data.iloc[-1]['close']
            return (close_price - open_price) / open_price * 100
    except:
        return None
    return None


def has_position(symbol):
    """Check if we have a position in the symbol"""
    try:
        position = trading_client.get_open_position(symbol)
        return float(position.qty) > 0
    except:
        return False

def get_latest_quote(symbol):
    """Get latest quote for a symbol"""
    quote = data_client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=[symbol]))
    return quote[symbol].ask_price or quote[symbol].bid_price

# Event handlers
def handle_buy(event):
    pct_change = get_weekly_performance(current_symbol)
    if pct_change is not None and pct_change <= -5:
        price = get_latest_quote(current_symbol)
        if price:
            qty = round(5 / price, 5)
            order = MarketOrderRequest(
                symbol=current_symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order)
            print(f"Bought ${5} of {current_symbol} at {price}")
            update_plot(current_symbol)
    else:
        print(f"Buy conditions not met. Weekly change: {pct_change}%")

def handle_sell(event):
    pct_change = get_weekly_performance(current_symbol)
    if pct_change is not None and pct_change >= 10 and has_position(current_symbol):
        price = get_latest_quote(current_symbol)
        if price:
            qty = round(10 / price, 5)
            order = MarketOrderRequest(
                symbol=current_symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order)
            print(f"Sold ${10} of {current_symbol} at {price}")
            update_plot(current_symbol)
    else:
        print(f"Sell conditions not met. Weekly change: {pct_change}%")

def handle_cancel(event):
    orders = trading_client.get_orders(status='open')
    for order in orders:
        if order.symbol == current_symbol:
            trading_client.cancel_order_by_id(order.id)
            print(f"Cancelled order {order.id}")
    update_plot(current_symbol)

def handle_stop(event):
    plt.close(fig)

def handle_submit(text):
    update_plot(text.strip().upper())

# Connect events
text_box.on_submit(handle_submit)
submit_btn.on_clicked(lambda event: handle_submit(text_box.text))
buy_btn.on_clicked(handle_buy)
sell_btn.on_clicked(handle_sell)
cancel_btn.on_clicked(handle_cancel)
stop_btn.on_clicked(handle_stop)

# Initial plot
update_plot(current_symbol)
plt.show()
