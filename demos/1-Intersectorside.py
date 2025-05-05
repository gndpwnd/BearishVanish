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
from dotenv import load_dotenv

# Load API credentials
load_dotenv()
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
data_client = StockHistoricalDataClient(api_key, secret_key)

HISTORY = 30
end_date = datetime.now()
start_date = end_date - timedelta(days=HISTORY)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
plt.subplots_adjust(bottom=0.25, hspace=0.4)
current_symbol = 'AAPL'

# Widgets
ax_text = fig.add_axes([0.25, 0.05, 0.4, 0.05])
text_box = TextBox(ax_text, 'Symbol:', initial=current_symbol)
ax_submit = fig.add_axes([0.66, 0.05, 0.1, 0.05])
submit_btn = Button(ax_submit, 'Update')

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
        prev_diff = stock_cum.iloc[i - 1] - sp500_cum.iloc[i - 1]
        curr_diff = stock_cum.iloc[i] - sp500_cum.iloc[i]
        if prev_diff * curr_diff < 0:
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
    dates = stock_data.index

    stock_slope = np.gradient(stock_cum)
    crosses = detect_crosses(stock_cum, sp500_cum)

    last_cross_index = -1
    last_cross_was_below = None
    signals = []
    last_signal = None  # Track last signal to enforce alternation

    for i in range(2, len(stock_cum)):
        prev_slope = stock_slope[i - 2]
        curr_slope = stock_slope[i]

        # Detect cross
        if i in crosses:
            last_cross_index = i
            last_cross_was_below = stock_cum.iloc[i] < sp500_cum.iloc[i]

        # Buy logic (must have crossed below and last signal was not BUY)
        if (
            last_cross_index != -1 and
            last_cross_was_below and
            prev_slope < 0 and curr_slope > 0 and
            stock_cum.iloc[i] < sp500_cum.iloc[i] and
            last_signal != 'BUY'
        ):
            signals.append(('BUY', i))
            last_signal = 'BUY'

        # Sell logic (must have crossed above and last signal was not SELL)
        elif (
            last_cross_index != -1 and
            not last_cross_was_below and
            prev_slope > 0 and curr_slope < 0 and
            stock_cum.iloc[i] > sp500_cum.iloc[i] and
            last_signal != 'SELL'
        ):
            signals.append(('SELL', i))
            last_signal = 'SELL'

    # Plotting cumulative returns
    ax1.plot(dates, stock_cum, label=f'{current_symbol} Cumulative Returns')
    ax1.plot(dates, sp500_cum, label='S&P 500 Cumulative Returns')

    for signal, idx in signals:
        color = 'green' if signal == 'BUY' else 'red'
        ax1.plot(dates[idx], stock_cum.iloc[idx], 'o', color=color,
                 label=signal if signal not in ax1.get_legend_handles_labels()[1] else "")

    ax1.set_title(f'{current_symbol} vs S&P 500 ({HISTORY} Days)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative Return (%)')
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    ax1.legend()

    # Plotting prices
    ax2.plot(dates, stock_data['close'], label=f'{current_symbol} Price', color='blue')
    for signal, idx in signals:
        color = 'green' if signal == 'BUY' else 'red'
        ax2.plot(dates[idx], stock_data['close'].iloc[idx], 'o', color=color,
                 label=signal if signal not in ax2.get_legend_handles_labels()[1] else "")

    ax2.set_title(f'{current_symbol} Stock Price')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Price (USD)')
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    ax2.legend()

    fig.canvas.draw_idle()

# Event handler
def handle_submit(text):
    update_plot(text.strip().upper())

# Connect widget
submit_btn.on_clicked(lambda event: handle_submit(text_box.text))

# Initial plot
update_plot(current_symbol)
plt.show()
