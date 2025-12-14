def execute_trade(self, symbol, signal, price, date, force=False, volume=None):
    """
    Execute trade with SMART POSITION SIZING and return success status
    """
    
    if signal == 'BUY' and self.cash > 0:
        # Check if we're at max positions (unless forced)
        if not force:
            current_positions = self.get_current_position_count()
            if current_positions >= self.max_positions:
                # Only block if opening a NEW position
                if symbol not in self.positions or self.positions.get(symbol, 0) == 0:
                    print(f"❌ {self.name}: BUY {symbol} BLOCKED - Max positions reached ({current_positions}/{self.max_positions})")
                    return False
        
        # Calculate allocation
        portfolio_value = self.get_current_portfolio_value(
            {s: price for s in self.positions if self.positions.get(s, 0) > 0}
        )
        allocation = portfolio_value * self.position_size_pct
        allocation = min(allocation, self.cash)
        
        if allocation < 100:
            print(f"❌ {self.name}: BUY {symbol} BLOCKED - Insufficient allocation (${allocation:.2f} < $100)")
            return False
            
        shares = round(allocation / price, 2)
        actual_cost = shares * price
        
        if actual_cost > self.cash:
            print(f"❌ {self.name}: BUY {symbol} BLOCKED - Insufficient cash (${actual_cost:.2f} > ${self.cash:.2f})")
            return False
            
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
            'forced': force,
            'volume': volume  # NEW: Store volume
        })
        print(f"✅ {self.name}: BOUGHT {shares:.2f} shares of {symbol} at ${price:.2f} (${actual_cost:.2f})")
        return True
                
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
            'forced': force,
            'volume': volume  # NEW: Store volume
        })
        print(f"✅ {self.name}: SOLD {shares:.2f} shares of {symbol} at ${price:.2f} (${proceeds:.2f})")
        return True
    
    elif signal == 'SELL' and self.positions.get(symbol, 0) <= 0:
        print(f"❌ {self.name}: SELL {symbol} BLOCKED - No position to sell")
        return False
        
    return False