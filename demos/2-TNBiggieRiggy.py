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

HISTORY = 360
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

def weekly_threshold_strategy(df, buy_threshold=-0.05, sell_threshold=0.10):
    signals = []
    close_prices = df['close']
    dates = close_prices.index

    # Filter for Mondays
    mondays = dates[dates.weekday == 0]

    for i in range(1, len(mondays)):
        prev_monday = mondays[i - 1]
        this_monday = mondays[i]

        if prev_monday not in close_prices.index or this_monday not in close_prices.index:
            continue

        past_price = close_prices.loc[prev_monday]
        current_price = close_prices.loc[this_monday]
        pct_change = (current_price - past_price) / past_price

        if pct_change <= buy_threshold:
            idx = close_prices.index.get_loc(this_monday)
            signals.append(('BUY $5', idx))
        elif pct_change >= sell_threshold:
            idx = close_prices.index.get_loc(this_monday)
            signals.append(('SELL $10', idx))

    return signals

def update_plot(symbol):
    global current_symbol
    current_symbol = symbol.upper()
    ax1.clear()
    ax2.clear()

    try:
        stock_data = fetch_stock_data(current_symbol)
    except ValueError as e:
        print(e)
        return

    stock_returns = stock_data['close'].pct_change().fillna(0)
    stock_cum = np.cumsum(stock_returns) * 100
    dates = stock_data.index

    # Get signals using weekly strategy
    signals = weekly_threshold_strategy(stock_data)

    # Plot cumulative returns
    ax1.plot(dates, stock_cum, label=f'{current_symbol} Cumulative Returns')

    for signal, idx in signals:
        color = 'green' if 'BUY' in signal else 'red'
        ax1.plot(dates[idx], stock_cum.iloc[idx], 'o', color=color,
                 label=signal if signal not in ax1.get_legend_handles_labels()[1] else "")

    ax1.set_title(f'{symbol} Weekly % Change Algorithm ({HISTORY} Days)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cumulative Weekly % Change')
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    ax1.legend()

    # Plot price chart with signals
    ax2.plot(dates, stock_data['close'], label=f'{current_symbol} Price', color='blue')
    for signal, idx in signals:
        color = 'green' if 'BUY' in signal else 'red'
        ax2.plot(dates[idx], stock_data['close'].iloc[idx], 'o', color=color,
                 label=signal if signal not in ax2.get_legend_handles_labels()[1] else "")

    ax2.set_title(f'{symbol} Stock Price')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Price (USD)')
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MONDAY))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
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
