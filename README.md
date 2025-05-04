# BearishVanish
Trying stock trading bots
> [Alpaca API Python Reference](https://pypi.org/project/alpaca-py/)

**Setup a .env**

```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```


**Setup venv and install requirements**

```bash
python3 -m venv venv; source venv/bin/activate; pip install --upgrade pip; pip install -r requirements.txt
```

What is being run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```


Clean up environment

```bash
deactivate
```

view what would be deleted, except for venv/

```bash
git clean -xdn -e venv/
```

delete what would be deleted, except for venv/

```bash
git clean -xdf -e venv/
```

---

# Trading Methodologies


### Intersectorcide

> S&P 500 Intersection with Stock Price

### TNBiggieRiggy
> "The Notorious Biggie Rigged System" Method

### AllYouCanEatBuffet
> If the company is so good it could be run by an idiot and still make money, but actually run by a good person, then no-brainer buy.

### NewsFeels
> News scraping and sentiment analysis to determine stock price movement?


# Potential Errors


### Order failed: potential wash trade detected. use complex orders alpaca

[reference](https://forum.alpaca.markets/t/apierror-potential-wash-trade-detected-use-complex-orders/13441/6)
The order is being rejected because it could result in a a ‘wash trade’. A wash trade (not to be confused with a wash sale) is when one trades with oneself. This is when one’s buy order fills against one’s sell order. The SEC looks very unfavorably on that and imposes harsh penalties for repeat offenders.

Because of that, Alpaca puts in place protections which reject any order where there is an existing open order having the opposite side. In general, one’s algo should be either increasing a position or decreasing a position (ie buying or selling) and not be doing those simultaneously.