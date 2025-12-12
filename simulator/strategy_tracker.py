"""
Strategy Tracker Module
Handles tracking of trades, positions, and portfolio value for each strategy
"""

import numpy as np
import pandas as pd

INITIAL_CASH = 10000  # Starting cash per strategy

class StrategyTracker:
    def __init__(self, strategy_name, initial_cash):
        self.name = strategy_name
        self.cash = initial_cash
        self.positions = {}  # symbol: shares
        self.trades = []  # List of trade dicts
        self.portfolio_value_history = []
        self.dates = []
        
    def execute_trade(self, symbol, signal, price, date):
        if signal == 'BUY' and self.cash > 0:
            shares = self.cash / price  # Buy with all available cash
            self.positions[symbol] = self.positions.get(symbol, 0) + shares
            self.cash = 0
            self.trades.append({
                'date': date, 'symbol': symbol, 'action': 'BUY',
                'price': price, 'shares': shares
            })
            
        elif signal == 'SELL' and self.positions.get(symbol, 0) > 0:
            shares = self.positions[symbol]
            proceeds = shares * price
            self.cash += proceeds
            self.positions[symbol] = 0
            self.trades.append({
                'date': date, 'symbol': symbol, 'action': 'SELL',
                'price': price, 'shares': shares, 'proceeds': proceeds
            })
    
    def update_portfolio_value(self, date, current_prices):
        total_value = self.cash
        for symbol, shares in self.positions.items():
            if symbol in current_prices and shares > 0:
                total_value += shares * current_prices[symbol]
        
        self.portfolio_value_history.append(total_value)
        self.dates.append(date)
        return total_value
    
    def get_final_value(self):
        return self.portfolio_value_history[-1] if self.portfolio_value_history else INITIAL_CASH
    
    def get_return_pct(self):
        return ((self.get_final_value() - INITIAL_CASH) / INITIAL_CASH) * 100
    
    def get_num_trades(self):
        return len(self.trades)
    
    def get_num_buys(self):
        return sum(1 for t in self.trades if t['action'] == 'BUY')
    
    def get_num_sells(self):
        return sum(1 for t in self.trades if t['action'] == 'SELL')
    
    def get_win_rate(self):
        """Calculate win rate based on completed trades (buy-sell pairs)"""
        wins = 0
        total_completed = 0
        
        # Group trades by symbol
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            # Match buys with sells
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    buy_price = symbol_trades[i]['price']
                    sell_price = symbol_trades[i+1]['price']
                    
                    if sell_price > buy_price:
                        wins += 1
                    total_completed += 1
                    i += 2
                else:
                    i += 1
        
        return (wins / total_completed * 100) if total_completed > 0 else 0
    
    def get_profit_dollars(self):
        """Get absolute profit in dollars"""
        return self.get_final_value() - INITIAL_CASH
    
    def get_max_drawdown(self):
        """Calculate maximum drawdown percentage"""
        if not self.portfolio_value_history:
            return 0
        
        peak = self.portfolio_value_history[0]
        max_dd = 0
        
        for value in self.portfolio_value_history:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def get_sharpe_ratio(self):
        """Calculate Sharpe ratio (assuming 0% risk-free rate)"""
        if len(self.portfolio_value_history) < 2:
            return 0
        
        returns = pd.Series(self.portfolio_value_history).pct_change().dropna()
        if len(returns) == 0 or returns.std() == 0:
            return 0
        
        return (returns.mean() / returns.std()) * np.sqrt(252 * 6.5)  # Annualized for hourly data
    
    def get_winning_trades(self):
        """Get list of winning trades"""
        winning = []
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    buy_price = symbol_trades[i]['price']
                    sell_price = symbol_trades[i+1]['price']
                    profit = symbol_trades[i]['shares'] * (sell_price - buy_price)
                    
                    if profit > 0:
                        winning.append({
                            'symbol': symbol,
                            'buy_date': symbol_trades[i]['date'],
                            'sell_date': symbol_trades[i+1]['date'],
                            'profit': profit,
                            'return_pct': (sell_price - buy_price) / buy_price * 100
                        })
                    i += 2
                else:
                    i += 1
        
        return winning
    
    def get_losing_trades(self):
        """Get list of losing trades"""
        losing = []
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    buy_price = symbol_trades[i]['price']
                    sell_price = symbol_trades[i+1]['price']
                    profit = symbol_trades[i]['shares'] * (sell_price - buy_price)
                    
                    if profit < 0:
                        losing.append({
                            'symbol': symbol,
                            'buy_date': symbol_trades[i]['date'],
                            'sell_date': symbol_trades[i+1]['date'],
                            'loss': profit,
                            'return_pct': (sell_price - buy_price) / buy_price * 100
                        })
                    i += 2
                else:
                    i += 1
        
        return losing
    
    def get_profit_factor(self):
        """Profit Factor: Gross profit / Gross loss"""
        winning = self.get_winning_trades()
        losing = self.get_losing_trades()
        
        gross_profit = sum(w['profit'] for w in winning)
        gross_loss = abs(sum(l['loss'] for l in losing))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    
    def get_avg_win(self):
        """Average winning trade profit"""
        winning = self.get_winning_trades()
        return sum(w['profit'] for w in winning) / len(winning) if winning else 0
    
    def get_avg_loss(self):
        """Average losing trade loss"""
        losing = self.get_losing_trades()
        return sum(l['loss'] for l in losing) / len(losing) if losing else 0
    
    def get_largest_win(self):
        """Largest winning trade"""
        winning = self.get_winning_trades()
        return max(w['profit'] for w in winning) if winning else 0
    
    def get_largest_loss(self):
        """Largest losing trade"""
        losing = self.get_losing_trades()
        return min(l['loss'] for l in losing) if losing else 0
    
    def get_avg_trade_duration(self):
        """Average time held per trade (in days)"""
        durations = []
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    duration = (symbol_trades[i+1]['date'] - symbol_trades[i]['date']).total_seconds() / 86400
                    durations.append(duration)
                    i += 2
                else:
                    i += 1
        
        return sum(durations) / len(durations) if durations else 0
    
    def get_consecutive_wins(self):
        """Maximum consecutive winning trades"""
        trades_outcomes = []
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    buy_price = symbol_trades[i]['price']
                    sell_price = symbol_trades[i+1]['price']
                    trades_outcomes.append(1 if sell_price > buy_price else 0)
                    i += 2
                else:
                    i += 1
        
        max_consecutive = 0
        current_consecutive = 0
        for outcome in trades_outcomes:
            if outcome == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def get_consecutive_losses(self):
        """Maximum consecutive losing trades"""
        trades_outcomes = []
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    buy_price = symbol_trades[i]['price']
                    sell_price = symbol_trades[i+1]['price']
                    trades_outcomes.append(0 if sell_price > buy_price else 1)
                    i += 2
                else:
                    i += 1
        
        max_consecutive = 0
        current_consecutive = 0
        for outcome in trades_outcomes:
            if outcome == 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def get_expectancy(self):
        """Expected return per trade"""
        winning = self.get_winning_trades()
        losing = self.get_losing_trades()
        total_trades = len(winning) + len(losing)
        
        if total_trades == 0:
            return 0
        
        win_rate = len(winning) / total_trades
        avg_win = self.get_avg_win()
        avg_loss = abs(self.get_avg_loss())
        
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    def get_sortino_ratio(self):
        """Sortino Ratio - like Sharpe but only penalizes downside volatility"""
        if len(self.portfolio_value_history) < 2:
            return 0
        
        returns = pd.Series(self.portfolio_value_history).pct_change().dropna()
        if len(returns) == 0:
            return 0
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        
        if downside_std == 0 or pd.isna(downside_std):
            return 0
        
        return (returns.mean() / downside_std) * np.sqrt(252 * 6.5)  # Annualized
    
    def get_calmar_ratio(self):
        """Calmar Ratio: Annual return / Max drawdown"""
        max_dd = self.get_max_drawdown()
        annual_return = self.get_return_pct() * 2  # Approximate annual from 6 months
        
        return annual_return / max_dd if max_dd > 0 else 0
    
    def get_ulcer_index(self):
        """Ulcer Index: Measures downside volatility"""
        if not self.portfolio_value_history:
            return 0
        
        values = np.array(self.portfolio_value_history)
        running_max = np.maximum.accumulate(values)
        drawdowns = ((values - running_max) / running_max) * 100
        
        squared_drawdowns = drawdowns ** 2
        ulcer = np.sqrt(np.mean(squared_drawdowns))
        
        return ulcer
    
    def get_recovery_factor(self):
        """Recovery Factor: Net profit / Max drawdown"""
        profit = self.get_profit_dollars()
        max_dd_dollars = self.get_max_drawdown_dollars()
        
        return profit / max_dd_dollars if max_dd_dollars > 0 else 0
    
    def get_max_drawdown_dollars(self):
        """Maximum drawdown in dollar terms"""
        if not self.portfolio_value_history:
            return 0
        
        peak = self.portfolio_value_history[0]
        max_dd = 0
        
        for value in self.portfolio_value_history:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def get_avg_drawdown(self):
        """Average of all drawdown periods"""
        if not self.portfolio_value_history:
            return 0
        
        values = np.array(self.portfolio_value_history)
        running_max = np.maximum.accumulate(values)
        drawdowns = ((values - running_max) / running_max) * 100
        
        # Only count periods in drawdown
        dd_periods = drawdowns[drawdowns < 0]
        
        return abs(np.mean(dd_periods)) if len(dd_periods) > 0 else 0

    def get_exposure_time(self):
        """Percentage of time capital was invested"""
        if not self.dates:
            return 0
        
        invested_bars = sum(1 for i in range(len(self.dates)) 
                           if sum(self.positions.values()) > 0)
        
        return (invested_bars / len(self.dates)) * 100
    
    def get_payoff_ratio(self):
        """Payoff Ratio: Average win / Average loss"""
        avg_win = self.get_avg_win()
        avg_loss = abs(self.get_avg_loss())
        
        return avg_win / avg_loss if avg_loss > 0 else 0