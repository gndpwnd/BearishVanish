"""
Strategy Diagnostics Tool
Analyzes why strategies fail and provides actionable fixes

Usage:
    python strategy_diagnostics.py --db path/to/simulation.db
"""

import sqlite3
import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from collections import defaultdict


class StrategyDiagnostics:
    """Diagnose strategy failures and suggest fixes"""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def analyze_strategy(self, strategy_name):
        """Complete diagnostic analysis of a strategy"""
        print(f"\n{'='*70}")
        print(f"DIAGNOSTIC ANALYSIS: {strategy_name}")
        print(f"{'='*70}\n")

        # 1. Trade execution analysis
        self.analyze_trade_execution(strategy_name)

        # 2. Win/Loss analysis
        self.analyze_win_loss_profile(strategy_name)

        # 3. Signal generation analysis
        self.analyze_signal_generation(strategy_name)

        # 4. Risk management analysis
        self.analyze_risk_management(strategy_name)

        # 5. Market condition analysis
        self.analyze_market_conditions(strategy_name)

        # 6. Provide recommendations
        self.provide_recommendations(strategy_name)

    def analyze_trade_execution(self, strategy_name):
        """Analyze trade execution rate"""
        print("1️⃣  TRADE EXECUTION ANALYSIS")
        print("-" * 70)

        # Get trade attempts
        cursor = self.conn.execute('''
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as rejected
            FROM trade_attempts
            WHERE strategy_name = ?
        ''', (strategy_name,))

        row = cursor.fetchone()

        if row['total_attempts'] == 0:
            print("   ❌ NO TRADE ATTEMPTS - Strategy generated no signals!")
            print("   → Problem: Indicator thresholds too strict")
            return

        success_rate = (row['successful'] / row['total_attempts'] * 100) if row['total_attempts'] > 0 else 0

        print(f"   Total Attempts: {row['total_attempts']:,}")
        print(f"   Successful: {row['successful']:,} ({success_rate:.1f}%)")
        print(f"   Rejected: {row['rejected']:,} ({100-success_rate:.1f}%)")

        if row['rejected'] > row['successful']:
            print("\n   ⚠️  MORE TRADES REJECTED THAN EXECUTED")
            self.analyze_rejection_reasons(strategy_name)

    def analyze_rejection_reasons(self, strategy_name):
        """Analyze why trades were rejected"""
        cursor = self.conn.execute('''
            SELECT rejection_reason, COUNT(*) as count
            FROM trade_attempts
            WHERE strategy_name = ? AND success = 0
            GROUP BY rejection_reason
            ORDER BY count DESC
        ''', (strategy_name,))

        print("\n   Top Rejection Reasons:")
        for row in cursor:
            if row['rejection_reason']:
                print(f"      • {row['rejection_reason']}: {row['count']:,} times")

    def analyze_win_loss_profile(self, strategy_name):
        """Analyze win/loss characteristics"""
        print(f"\n2️⃣  WIN/LOSS PROFILE")
        print("-" * 70)

        # Get completed trades
        cursor = self.conn.execute('''
            SELECT
                profit_loss,
                profit_loss_pct,
                holding_days
            FROM trade_history
            WHERE strategy_name = ?
              AND exit_date IS NOT NULL
              AND profit_loss IS NOT NULL
        ''', (strategy_name,))

        trades = cursor.fetchall()

        if not trades:
            print("   ❌ NO COMPLETED TRADES")
            print("   → Strategy may not be generating SELL signals")
            return

        pnls = [t['profit_loss'] for t in trades]
        pnl_pcts = [t['profit_loss_pct'] for t in trades]

        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        win_rate = len(winners) / len(trades) * 100 if trades else 0
        avg_win = np.mean(winners) if winners else 0
        avg_loss = np.mean(losers) if losers else 0
        avg_win_pct = np.mean([p for p in pnl_pcts if p > 0]) if any(p > 0 for p in pnl_pcts) else 0
        avg_loss_pct = np.mean([p for p in pnl_pcts if p < 0]) if any(p < 0 for p in pnl_pcts) else 0

        print(f"   Total Trades: {len(trades)}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Average Win: ${avg_win:,.2f} ({avg_win_pct:.1f}%)")
        print(f"   Average Loss: ${avg_loss:,.2f} ({avg_loss_pct:.1f}%)")

        # Risk/Reward ratio
        if avg_loss != 0:
            risk_reward = abs(avg_win / avg_loss)
            print(f"   Risk/Reward Ratio: {risk_reward:.2f}:1")

            # Diagnosis
            if win_rate < 50 and risk_reward < 2:
                print("\n   ❌ CRITICAL ISSUE: Low win rate + Poor risk/reward")
                print("   → You're losing more often AND losses are bigger than wins")
                print("   → FIX: Tighten stop-losses OR widen profit targets")

            elif risk_reward < 1:
                print("\n   ❌ CRITICAL ISSUE: Losses bigger than wins")
                print("   → Average loss is LARGER than average win")
                print("   → FIX: Add stop-losses immediately!")

            elif win_rate < 40:
                print("\n   ⚠️  WARNING: Low win rate")
                print("   → Winning less than 40% of the time")
                print("   → FIX: Improve entry criteria or exit winners later")

    def analyze_signal_generation(self, strategy_name):
        """Analyze signal generation patterns"""
        print(f"\n3️⃣  SIGNAL GENERATION")
        print("-" * 70)

        # Count BUY vs SELL signals
        cursor = self.conn.execute('''
            SELECT
                signal,
                COUNT(*) as count
            FROM trade_attempts
            WHERE strategy_name = ?
            GROUP BY signal
        ''', (strategy_name,))

        signals = {row['signal']: row['count'] for row in cursor}

        buy_count = signals.get('BUY', 0)
        sell_count = signals.get('SELL', 0)

        print(f"   BUY signals: {buy_count:,}")
        print(f"   SELL signals: {sell_count:,}")

        if buy_count == 0:
            print("\n   ❌ NO BUY SIGNALS")
            print("   → Strategy entry conditions are TOO STRICT")
            print("   → FIX: Relax indicator thresholds")

        elif abs(buy_count - sell_count) > buy_count * 0.5:
            print("\n   ⚠️  WARNING: Imbalanced signals")
            print(f"   → BUY:SELL ratio is {buy_count}:{sell_count}")
            print("   → Strategy may be holding positions too long")

    def analyze_risk_management(self, strategy_name):
        """Analyze risk management"""
        print(f"\n4️⃣  RISK MANAGEMENT")
        print("-" * 70)

        # Get max drawdown
        cursor = self.conn.execute('''
            SELECT
                total_return_pct,
                max_drawdown_pct,
                sharpe_ratio
            FROM strategy_performance
            WHERE strategy_name = ?
        ''', (strategy_name,))

        row = cursor.fetchone()

        if not row:
            print("   ⚠️  No performance data available")
            return

        print(f"   Total Return: {row['total_return_pct']:.1f}%")
        print(f"   Max Drawdown: {row['max_drawdown_pct']:.1f}%")
        print(f"   Sharpe Ratio: {row['sharpe_ratio']:.2f}")

        # Diagnosis
        if row['max_drawdown_pct'] > 30:
            print("\n   ❌ CRITICAL: Drawdown too high (>30%)")
            print("   → No proper stop-losses in place")
            print("   → FIX: Add 5-10% stop-losses on all positions")

        if row['sharpe_ratio'] < 0.5:
            print("\n   ❌ CRITICAL: Poor risk-adjusted returns")
            print("   → Too much volatility for the returns")
            print("   → FIX: Reduce position sizes or improve entry timing")

        if row['total_return_pct'] < 0:
            print("\n   ❌ CRITICAL: Negative returns")
            print("   → Strategy is losing money")

    def analyze_market_conditions(self, strategy_name):
        """Analyze market conditions during test period"""
        print(f"\n5️⃣  MARKET CONDITIONS")
        print("-" * 70)

        # Get date range
        cursor = self.conn.execute('''
            SELECT MIN(date) as start_date, MAX(date) as end_date
            FROM portfolio_history
            WHERE strategy_name = ?
        ''', (strategy_name,))

        row = cursor.fetchone()

        if row['start_date']:
            print(f"   Test Period: {row['start_date']} to {row['end_date']}")

            # Check if test period is too short
            start = pd.to_datetime(row['start_date'])
            end = pd.to_datetime(row['end_date'])
            days = (end - start).days

            if days < 180:
                print(f"\n   ⚠️  WARNING: Short test period ({days} days)")
                print("   → Need at least 180 days for reliable results")

            if start.year >= 2024:
                print("\n   ⚠️  WARNING: Only tested in 2024 bull market")
                print("   → Strategy may fail in bear/choppy markets")
                print("   → RECOMMEND: Test from 2022 (includes bear market)")

    def provide_recommendations(self, strategy_name):
        """Provide actionable recommendations"""
        print(f"\n6️⃣  RECOMMENDATIONS")
        print("-" * 70)

        # Get all metrics
        cursor = self.conn.execute('''
            SELECT COUNT(*) as total_trades
            FROM trade_history
            WHERE strategy_name = ? AND exit_date IS NOT NULL
        ''', (strategy_name,))

        trades = cursor.fetchone()['total_trades']

        cursor = self.conn.execute('''
            SELECT COUNT(*) as total_attempts
            FROM trade_attempts
            WHERE strategy_name = ?
        ''', (strategy_name,))

        attempts = cursor.fetchone()['total_attempts']

        # Generate recommendations
        recommendations = []

        if attempts == 0:
            recommendations.append("🔧 CRITICAL: Relax indicator thresholds - strategy generates NO signals")
            recommendations.append("   → Lower ADX threshold from 25 to 20")
            recommendations.append("   → Remove volume requirement or lower to 1.0x")
            recommendations.append("   → Use OR logic instead of AND for some conditions")

        if trades < 10:
            recommendations.append("🔧 Increase trade frequency - only generated {trades} trades")
            recommendations.append("   → Lower entry thresholds")
            recommendations.append("   → Consider shorter timeframes")

        # Check risk/reward
        cursor = self.conn.execute('''
            SELECT profit_loss
            FROM trade_history
            WHERE strategy_name = ? AND exit_date IS NOT NULL
        ''', (strategy_name,))

        pnls = [row['profit_loss'] for row in cursor if row['profit_loss'] is not None]

        if pnls:
            winners = [p for p in pnls if p > 0]
            losers = [p for p in pnls if p < 0]

            if losers and winners:
                avg_loss = abs(np.mean(losers))
                avg_win = np.mean(winners)

                if avg_loss > avg_win:
                    recommendations.append("🔧 CRITICAL: Add stop-losses - losses bigger than wins")
                    recommendations.append("   → Add 5% stop-loss on all positions")
                    recommendations.append("   → Exit losing trades earlier")

        if not recommendations:
            recommendations.append("✅ Strategy structure looks OK - may just need parameter tuning")

        for rec in recommendations:
            print(f"\n   {rec}")

    def analyze_all_strategies(self):
        """Analyze all strategies in database"""
        cursor = self.conn.execute('''
            SELECT DISTINCT strategy_name
            FROM strategy_performance
        ''')

        strategies = [row['strategy_name'] for row in cursor]

        if not strategies:
            print("❌ No strategies found in database")
            return

        for strategy in strategies:
            self.analyze_strategy(strategy)

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Diagnose strategy failures')
    parser.add_argument('--db', required=True, help='Path to simulation database')
    parser.add_argument('--strategy', help='Specific strategy to analyze (optional)')

    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        return

    diagnostics = StrategyDiagnostics(args.db)

    if args.strategy:
        diagnostics.analyze_strategy(args.strategy)
    else:
        diagnostics.analyze_all_strategies()

    diagnostics.close()


if __name__ == '__main__':
    main()
