"""
Enhanced Strategy Tracker with Flexible Position Sizing and Force-Liquidation Support
Supports multiple starting capital amounts and flexible position limits
"""

import numpy as np
import pandas as pd

# Configurable starting capital
INITIAL_CASH = 100000  # Start with $100k

class StrategyTracker:
    def __init__(self, strategy_name, initial_cash=INITIAL_CASH, position_size_pct=0.20, max_positions=10):
        """
        Initialize Strategy Tracker with flexible parameters
        
        Args:
            strategy_name: Name of the strategy
            initial_cash: Starting capital amount
            position_size_pct: Percentage of portfolio per position (default 20%)
            max_positions: Maximum concurrent positions (default 10, was 5)
        """
        self.name = strategy_name
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position_size_pct = position_size_pct
        self.max_positions = max_positions
        
        self.positions = {}  # symbol: shares
        self.trades = []  # List of trade dicts
        self.portfolio_value_history = []
        self.dates = []
        
        # Track position allocations
        self.position_values = {}  # symbol: current value
        
    def get_current_position_count(self):
        """Count non-zero positions"""
        return sum(1 for shares in self.positions.values() if shares > 0)
    
    def execute_trade(self, symbol, signal, price, date, force=False):
        """
        Execute trade with SMART POSITION SIZING and return success status
        
        Args:
            symbol: Stock symbol
            signal: 'BUY' or 'SELL'
            price: Current price
            date: Current date
            force: If True, bypass position limits (for forced liquidation)
            
        Returns:
            bool: True if trade executed, False if blocked
        """
        
        if signal == 'BUY' and self.cash > 0:
            # Check if we're at max positions (unless forced)
            if not force:
                current_positions = self.get_current_position_count()
                if current_positions >= self.max_positions:
                    # Only block if opening a NEW position
                    if symbol not in self.positions or self.positions.get(symbol, 0) == 0:
                        return False  # Blocked by max positions
            
            # Calculate allocation based on PORTFOLIO value, not just cash
            portfolio_value = self.get_current_portfolio_value(
                {s: price for s in self.positions if self.positions.get(s, 0) > 0}
            )
            allocation = portfolio_value * self.position_size_pct
            
            # Ensure we don't exceed available cash
            allocation = min(allocation, self.cash)
            
            if allocation >= 100:  # Minimum position size
                shares = round(allocation / price, 2)  # Fractional shares
                actual_cost = shares * price
                
                if actual_cost <= self.cash:
                    self.positions[symbol] = self.positions.get(symbol, 0) + shares
                    self.cash -= actual_cost
                    self.position_values[symbol] = actual_cost
                    
                    self.trades.append({
                        'date': date, 
                        'symbol': symbol, 
                        'action': 'BUY',
                        'price': price, 
                        'shares': shares,
                        'cost': actual_cost,
                        'forced': force
                    })
                    return True  # Trade succeeded
            return False  # Insufficient allocation
                    
        elif signal == 'SELL' and self.positions.get(symbol, 0) > 0:
            shares = self.positions[symbol]
            proceeds = shares * price
            self.cash += proceeds
            self.positions[symbol] = 0
            
            if symbol in self.position_values:
                del self.position_values[symbol]
            
            self.trades.append({
                'date': date, 
                'symbol': symbol, 
                'action': 'SELL',
                'price': price, 
                'shares': shares, 
                'proceeds': proceeds,
                'forced': force
            })
            return True  # Trade succeeded
        
        return False  # No trade executed
    
    def get_current_portfolio_value(self, current_prices):
        """Calculate current portfolio value including cash and positions"""
        total_value = self.cash
        for symbol, shares in self.positions.items():
            if symbol in current_prices and shares > 0:
                total_value += shares * current_prices[symbol]
        return total_value

    def update_portfolio_value(self, date, current_prices):
        """Update portfolio value and track position values"""
        total_value = self.get_current_portfolio_value(current_prices)
        
        # Update position values for tracking
        for symbol, shares in self.positions.items():
            if symbol in current_prices and shares > 0:
                self.position_values[symbol] = shares * current_prices[symbol]
        
        self.portfolio_value_history.append(total_value)
        self.dates.append(date)
        return total_value
    
    def force_liquidate_all(self, date, current_prices):
        """
        Force liquidate all positions at end of simulation
        
        Args:
            date: Current date
            current_prices: Dict of {symbol: price}
            
        Returns:
            int: Number of positions liquidated
        """
        liquidated = 0
        for symbol in list(self.positions.keys()):
            if self.positions.get(symbol, 0) > 0 and symbol in current_prices:
                success = self.execute_trade(
                    symbol, 'SELL', 
                    current_prices[symbol], 
                    date, 
                    force=True
                )
                if success:
                    liquidated += 1
        
        return liquidated
    
    def get_final_value(self):
        return self.portfolio_value_history[-1] if self.portfolio_value_history else self.initial_cash
    
    def get_return_pct(self):
        return ((self.get_final_value() - self.initial_cash) / self.initial_cash) * 100
    
    def get_profit_dollars(self):
        """Get absolute profit in dollars"""
        return self.get_final_value() - self.initial_cash
    
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
        
        return (returns.mean() / returns.std()) * np.sqrt(252 * 6.5)  # Annualized
    
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
        
        return (returns.mean() / downside_std) * np.sqrt(252 * 6.5)
    
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
    
    def print_debug_info(self):
        """Print debug information about current portfolio state"""
        print(f"\n {self.name} Portfolio State:")
        print(f"   Cash: ${self.cash:,.2f}")
        print(f"   Positions: {self.get_current_position_count()}/{self.max_positions}")
        print(f"   Total Trades: {len(self.trades)} (Buy: {self.get_num_buys()}, Sell: {self.get_num_sells()})")
        print(f"   Portfolio Value: ${self.get_final_value():,.2f}")
        print(f"   Return: {self.get_return_pct():.2f}%")
        
        if self.positions:
            print(f"\n   Active Positions:")
            for symbol, shares in self.positions.items():
                if shares > 0:
                    value = self.position_values.get(symbol, 0)
                    print(f"      {symbol}: {shares:.2f} shares (${value:,.2f})")


    def get_portfolio_beta(self, spy_returns=None):
        """
        Calculate portfolio beta vs S&P 500
        Beta measures volatility relative to the market
        """
        if len(self.portfolio_value_history) < 2:
            return 1.0
        
        # Calculate portfolio returns
        portfolio_returns = pd.Series(self.portfolio_value_history).pct_change().dropna()
        
        if spy_returns is None or len(spy_returns) == 0:
            return 1.0  # Default to market beta if no SPY data
        
        # Ensure same length
        min_len = min(len(portfolio_returns), len(spy_returns))
        portfolio_returns = portfolio_returns.iloc[-min_len:]
        spy_returns = spy_returns.iloc[-min_len:]
        
        # Calculate covariance and variance
        covariance = portfolio_returns.cov(spy_returns)
        spy_variance = spy_returns.var()
        
        if spy_variance == 0 or pd.isna(spy_variance):
            return 1.0
        
        beta = covariance / spy_variance
        return beta if not pd.isna(beta) else 1.0

    def get_information_ratio(self, spy_returns=None):
        """
        Information Ratio: Risk-adjusted return vs benchmark
        IR = (Portfolio Return - Benchmark Return) / Tracking Error
        """
        if len(self.portfolio_value_history) < 2:
            return 0.0
        
        portfolio_returns = pd.Series(self.portfolio_value_history).pct_change().dropna()
        
        if spy_returns is None or len(spy_returns) == 0:
            return 0.0
        
        # Ensure same length
        min_len = min(len(portfolio_returns), len(spy_returns))
        portfolio_returns = portfolio_returns.iloc[-min_len:]
        spy_returns = spy_returns.iloc[-min_len:]
        
        # Calculate excess returns
        excess_returns = portfolio_returns - spy_returns
        
        # Tracking error is std dev of excess returns
        tracking_error = excess_returns.std()
        
        if tracking_error == 0 or pd.isna(tracking_error):
            return 0.0
        
        # Information ratio
        ir = excess_returns.mean() / tracking_error
        return ir * np.sqrt(252 * 6.5) if not pd.isna(ir) else 0.0  # Annualized

    def get_alpha(self, spy_return_pct=None):
        """
        Jensen's Alpha: Excess return above what CAPM predicts
        Alpha = Portfolio Return - (Risk-free rate + Beta * (Market Return - Risk-free rate))
        Assuming risk-free rate = 0 for simplicity
        """
        portfolio_return = self.get_return_pct()
        
        if spy_return_pct is None:
            return portfolio_return  # If no benchmark, return portfolio return
        
        beta = self.get_portfolio_beta()
        
        # Alpha = Portfolio Return - Beta * Market Return
        alpha = portfolio_return - (beta * spy_return_pct)
        
        return alpha

    def get_trade_history_dataframe(self):
        """
        Get complete trade history as a DataFrame for easy analysis
        """
        if not self.trades:
            return pd.DataFrame()
        
        # Convert trades to DataFrame
        df = pd.DataFrame(self.trades)
        
        # Add computed columns
        df['amount'] = df['price'] * df['shares']
        
        # Calculate P&L for sells
        df['pnl'] = 0.0
        df['pnl_pct'] = 0.0
        
        for symbol in df['symbol'].unique():
            symbol_trades = df[df['symbol'] == symbol].copy()
            
            for i in range(len(symbol_trades)):
                if symbol_trades.iloc[i]['action'] == 'SELL' and i > 0:
                    # Find previous buy
                    prev_buys = symbol_trades.iloc[:i]
                    prev_buys = prev_buys[prev_buys['action'] == 'BUY']
                    
                    if len(prev_buys) > 0:
                        # Calculate weighted average buy price
                        total_shares = prev_buys['shares'].sum()
                        total_cost = (prev_buys['price'] * prev_buys['shares']).sum()
                        avg_buy_price = total_cost / total_shares if total_shares > 0 else 0
                        
                        sell_price = symbol_trades.iloc[i]['price']
                        sell_shares = symbol_trades.iloc[i]['shares']
                        
                        pnl = (sell_price - avg_buy_price) * sell_shares
                        pnl_pct = (sell_price - avg_buy_price) / avg_buy_price * 100 if avg_buy_price > 0 else 0
                        
                        # Update in main df
                        df.loc[symbol_trades.iloc[i].name, 'pnl'] = pnl
                        df.loc[symbol_trades.iloc[i].name, 'pnl_pct'] = pnl_pct
        
        return df

    def get_stock_performance_summary(self):
        """
        Get performance summary for each stock traded
        Returns dict with stock-level metrics
        """
        stock_summary = {}
        
        for symbol in set(t['symbol'] for t in self.trades):
            symbol_trades = [t for t in self.trades if t['symbol'] == symbol]
            
            buys = [t for t in symbol_trades if t['action'] == 'BUY']
            sells = [t for t in symbol_trades if t['action'] == 'SELL']
            
            total_invested = sum(t['shares'] * t['price'] for t in buys)
            total_returned = sum(t.get('proceeds', 0) for t in sells)
            
            # Add unrealized value if still holding
            current_shares = self.positions.get(symbol, 0)
            unrealized_value = 0
            
            # Calculate P&L
            pnl = total_returned - total_invested
            pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0
            
            # Win rate for this stock
            wins = 0
            total_trades = 0
            
            i = 0
            while i < len(symbol_trades) - 1:
                if symbol_trades[i]['action'] == 'BUY' and symbol_trades[i+1]['action'] == 'SELL':
                    if symbol_trades[i+1]['price'] > symbol_trades[i]['price']:
                        wins += 1
                    total_trades += 1
                    i += 2
                else:
                    i += 1
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            stock_summary[symbol] = {
                'num_trades': len(symbol_trades),
                'num_buys': len(buys),
                'num_sells': len(sells),
                'total_invested': total_invested,
                'total_returned': total_returned,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'win_rate': win_rate,
                'wins': wins,
                'losses': total_trades - wins,
                'current_shares': current_shares
            }
        
        return stock_summary