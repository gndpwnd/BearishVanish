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

# Load API credentials
load_dotenv()

# Initialize Alpaca clients
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
data_client = StockHistoricalDataClient(api_key, secret_key)
trading_client = TradingClient(api_key, secret_key, paper=True)

# Time range for historical data
HISTORY = 90
end_date = datetime.now()
start_date = end_date - timedelta(days=HISTORY)

# Create figure and widgets once
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
plt.subplots_adjust(bottom=0.25, hspace=0.4)
current_symbol = 'AAPL'

# Create widgets
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

buy_btn = Button(ax_buy, 'Buy')
sell_btn = Button(ax_sell, 'Sell')
cancel_btn = Button(ax_cancel, 'Cancel')
stop_btn = Button(ax_stop, 'Stop')

def fetch_stock_data(symbol):
    symbol = symbol.upper()
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
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

def detect_crosses(stock_cum, sp500_cum):
    crosses = []
    for i in range(1, len(stock_cum)):
        diff_prev = stock_cum[i-1] - sp500_cum[i-1]
        diff_curr = stock_cum[i] - sp500_cum[i]
        if diff_prev * diff_curr < 0:
            crosses.append(i)
    return crosses

def update_plot(symbol):
    global current_symbol
    current_symbol = symbol.upper()
    ax1.clear()
    ax2.clear()

    try:
        stock_data = fetch_stock_data(current_symbol)
        sp500_data = fetch_stock_data("SPY")
    except ValueError as e:
        print(e)
        return

    stock_returns = stock_data['close'].pct_change().fillna(0)
    sp500_returns = sp500_data['close'].pct_change().fillna(0)

    stock_cum = np.cumsum(stock_returns) * 100
    sp500_cum = np.cumsum(sp500_returns) * 100

    stock_slope = np.gradient(stock_cum)
    dates = stock_data.index
    crosses = detect_crosses(stock_cum, sp500_cum)

    last_cross_index = -1
    last_cross_slope = 0
    signals = []
    last_signal = None  # To track if a signal has been triggered (buy or sell)

    for i in range(2, len(stock_cum)):
        prev_slope = stock_slope[i - 2]
        curr_slope = stock_slope[i]

        # Detect if a cross occurs between stock and S&P 500
        if i in crosses:
            last_cross_index = i
            last_cross_slope = stock_slope[i]
            last_signal = None  # Reset the signal after a cross

        # BUY condition: Slope reversal from negative to positive and previously crossed below S&P
        if prev_slope < 0 and curr_slope > 0 and last_cross_index != -1 and last_cross_index < i:
            if last_cross_slope < 0 and last_signal != 'BUY':
                signals.append(('BUY', i))
                last_signal = 'BUY'  # Set the last signal to BUY

        # SELL condition: Slope reversal from positive to negative and previously crossed above S&P
        if prev_slope > 0 and curr_slope < 0 and last_cross_index != -1 and last_cross_index < i:
            if last_cross_slope > 0 and last_signal != 'SELL':
                signals.append(('SELL', i))
                last_signal = 'SELL'  # Set the last signal to SELL

    # Plotting cumulative returns on ax1
    ax1.plot(dates, stock_cum, label=f'{current_symbol} Cumulative Returns')
    ax1.plot(dates, sp500_cum, label='S&P 500 Cumulative Returns')

    for signal, idx in signals:
        color = 'green' if signal == 'BUY' else 'red'
        ax1.plot(dates[idx], stock_cum[idx], 'o', color=color,
                label=signal if signal not in ax1.get_legend_handles_labels()[1] else "")

    ax1.set_title(f'{current_symbol} vs S&P 500 ({HISTORY} Days)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative Return (%)')
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    ax1.legend()

    # Plotting stock prices on ax2
    ax2.plot(dates, stock_data['close'], label=f'{current_symbol} Stock Price', color='blue')

    for signal, idx in signals:
        color = 'green' if signal == 'BUY' else 'red'
        ax2.plot(dates[idx], stock_data['close'][idx], 'o', color=color,
                label=signal if signal not in ax2.get_legend_handles_labels()[1] else "")

    ax2.set_title(f'{current_symbol} Stock Price')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Price (USD)')
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    ax2.legend()

    fig.canvas.draw_idle()

# Event handlers
def handle_submit(text):
    update_plot(text.strip().upper())

def handle_buy(event):
    print(f"Buying {current_symbol}")
    # Example order (uncomment to enable live trading)
    # order = MarketOrderRequest(
    #     symbol=current_symbol,
    #     qty=1,
    #     side=OrderSide.BUY,
    #     time_in_force=TimeInForce.DAY
    # )
    # trading_client.submit_order(order)

def handle_sell(event):
    print(f"Selling {current_symbol}")
    # Example order (uncomment to enable live trading)
    # order = MarketOrderRequest(
    #     symbol=current_symbol,
    #     qty=1,
    #     side=OrderSide.SELL,
    #     time_in_force=TimeInForce.DAY
    # )
    # trading_client.submit_order(order)

def handle_cancel(event):
    print(f"Canceling orders for {current_symbol}")
    # Cancel orders if implemented

def handle_stop(event):
    plt.close(fig)

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
