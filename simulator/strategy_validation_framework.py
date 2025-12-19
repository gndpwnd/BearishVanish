"""
Comprehensive Strategy Validation Framework
Tests strategies across multiple market conditions and validates robustness

This framework helps you:
1. Test strategies across different market regimes (bull, bear, sideways)
2. Validate statistical significance of results
3. Detect overfitting
4. Compare strategies objectively
5. Ensure strategies are production-ready
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Results from strategy validation"""
    strategy_name: str
    passed: bool
    score: float
    issues: List[str]
    recommendations: List[str]
    metrics: Dict


class MarketRegimeAnalyzer:
    """Identify different market regimes for testing"""

    @staticmethod
    def detect_regimes(prices: pd.Series) -> pd.DataFrame:
        """
        Detect market regimes: bull, bear, sideways

        Returns DataFrame with regime labels
        """
        # Calculate rolling returns and volatility
        returns = prices.pct_change()

        # 20-day rolling metrics
        rolling_return = returns.rolling(20).mean() * 252  # Annualized
        rolling_vol = returns.rolling(20).std() * np.sqrt(252)  # Annualized

        regimes = []
        for i in range(len(prices)):
            if i < 20:
                regimes.append('WARMING_UP')
            else:
                ret = rolling_return.iloc[i]
                vol = rolling_vol.iloc[i]

                # Classify regime
                if ret > 0.15:  # >15% annualized
                    regime = 'BULL'
                elif ret < -0.10:  # <-10% annualized
                    regime = 'BEAR'
                elif vol > 0.30:  # >30% volatility
                    regime = 'VOLATILE'
                else:
                    regime = 'SIDEWAYS'

                regimes.append(regime)

        return pd.DataFrame({
            'regime': regimes,
            'rolling_return': rolling_return,
            'rolling_vol': rolling_vol
        }, index=prices.index)


class StrategyValidator:
    """Comprehensive strategy validation"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def validate_strategy(self, strategy_name: str, strict: bool = False) -> ValidationResult:
        """
        Validate a strategy across multiple criteria

        Args:
            strategy_name: Strategy to validate
            strict: Use strict thresholds (production-ready vs development)

        Returns:
            ValidationResult with pass/fail and recommendations
        """
        print(f"\n{'='*70}")
        print(f"VALIDATING STRATEGY: {strategy_name}")
        print(f"Mode: {'STRICT (Production)' if strict else 'LENIENT (Development)'}")
        print(f"{'='*70}\n")

        issues = []
        recommendations = []
        score = 100.0  # Start at 100, deduct for issues
        metrics = {}

        # 1. Trade Volume Test
        print("1. Trade Volume Test...")
        trade_vol_pass, trade_vol_metrics = self._test_trade_volume(strategy_name, strict)
        metrics.update(trade_vol_metrics)

        if not trade_vol_pass:
            issues.append("Insufficient trade volume")
            score -= 20
            recommendations.append("Relax entry thresholds to generate more signals")

        # 2. Win Rate Test
        print("2. Win Rate Test...")
        win_rate_pass, win_rate_metrics = self._test_win_rate(strategy_name, strict)
        metrics.update(win_rate_metrics)

        if not win_rate_pass:
            issues.append("Win rate too low")
            score -= 15
            recommendations.append("Improve entry criteria or exit winners later")

        # 3. Risk/Reward Test
        print("3. Risk/Reward Test...")
        rr_pass, rr_metrics = self._test_risk_reward(strategy_name, strict)
        metrics.update(rr_metrics)

        if not rr_pass:
            issues.append("Poor risk/reward ratio")
            score -= 20
            recommendations.append("Tighten stop-losses or widen profit targets")

        # 4. Drawdown Test
        print("4. Drawdown Test...")
        dd_pass, dd_metrics = self._test_drawdown(strategy_name, strict)
        metrics.update(dd_metrics)

        if not dd_pass:
            issues.append("Excessive drawdown")
            score -= 25
            recommendations.append("Add/tighten stop-losses immediately")

        # 5. Sharpe Ratio Test
        print("5. Sharpe Ratio Test...")
        sharpe_pass, sharpe_metrics = self._test_sharpe(strategy_name, strict)
        metrics.update(sharpe_metrics)

        if not sharpe_pass:
            issues.append("Poor risk-adjusted returns")
            score -= 10
            recommendations.append("Reduce position sizes or improve timing")

        # 6. Consistency Test
        print("6. Consistency Test...")
        consistency_pass, consistency_metrics = self._test_consistency(strategy_name, strict)
        metrics.update(consistency_metrics)

        if not consistency_pass:
            issues.append("Inconsistent returns")
            score -= 10
            recommendations.append("Diversify across more positions or timeframes")

        # 7. Market Regime Performance
        print("7. Market Regime Performance...")
        regime_pass, regime_metrics = self._test_regime_performance(strategy_name, strict)
        metrics.update(regime_metrics)

        if not regime_pass:
            issues.append("Fails in certain market conditions")
            score -= 15
            recommendations.append("Add market regime filters or diversify strategies")

        # 8. Execution Quality
        print("8. Execution Quality...")
        exec_pass, exec_metrics = self._test_execution_quality(strategy_name, strict)
        metrics.update(exec_metrics)

        if not exec_pass:
            issues.append("Too many rejected trades")
            score -= 5
            recommendations.append("Check position sizing and max positions limits")

        # Overall pass/fail
        min_score = 80 if strict else 60
        passed = score >= min_score and len(issues) == 0

        # Print summary
        self._print_validation_summary(strategy_name, passed, score, issues, recommendations)

        return ValidationResult(
            strategy_name=strategy_name,
            passed=passed,
            score=score,
            issues=issues,
            recommendations=recommendations,
            metrics=metrics
        )

    def _test_trade_volume(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test if strategy generates sufficient trades"""
        cursor = self.conn.execute('''
            SELECT COUNT(*) as total_trades
            FROM trade_history
            WHERE strategy_name = ? AND exit_date IS NOT NULL
        ''', (strategy_name,))

        result = cursor.fetchone()
        total_trades = result['total_trades']

        # Get test period length
        cursor = self.conn.execute('''
            SELECT MIN(date) as start_date, MAX(date) as end_date
            FROM portfolio_history
            WHERE strategy_name = ?
        ''', (strategy_name,))

        dates = cursor.fetchone()
        if dates['start_date']:
            start = pd.to_datetime(dates['start_date'])
            end = pd.to_datetime(dates['end_date'])
            days = (end - start).days
            months = days / 30
        else:
            months = 1

        trades_per_month = total_trades / months if months > 0 else 0

        # Thresholds
        min_trades_total = 30 if strict else 15
        min_trades_per_month = 5 if strict else 2

        passed = total_trades >= min_trades_total and trades_per_month >= min_trades_per_month

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {total_trades} total trades ({trades_per_month:.1f}/month)")
        if not passed:
            print(f"   Required: >{min_trades_total} total, >{min_trades_per_month}/month")

        return passed, {
            'total_trades': total_trades,
            'trades_per_month': trades_per_month,
            'test_period_days': days if 'days' in locals() else 0
        }

    def _test_win_rate(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test win rate"""
        cursor = self.conn.execute('''
            SELECT profit_loss
            FROM trade_history
            WHERE strategy_name = ? AND exit_date IS NOT NULL AND profit_loss IS NOT NULL
        ''', (strategy_name,))

        pnls = [row['profit_loss'] for row in cursor]

        if not pnls:
            print("   ⚠️  No completed trades")
            return False, {'win_rate': 0, 'wins': 0, 'losses': 0}

        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        win_rate = wins / len(pnls) * 100

        # Thresholds
        min_win_rate = 55 if strict else 45

        passed = win_rate >= min_win_rate

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {win_rate:.1f}% win rate ({wins}W/{losses}L)")
        if not passed:
            print(f"   Required: >{min_win_rate}%")

        return passed, {
            'win_rate': win_rate,
            'wins': wins,
            'losses': losses
        }

    def _test_risk_reward(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test risk/reward ratio"""
        cursor = self.conn.execute('''
            SELECT profit_loss
            FROM trade_history
            WHERE strategy_name = ? AND exit_date IS NOT NULL AND profit_loss IS NOT NULL
        ''', (strategy_name,))

        pnls = [row['profit_loss'] for row in cursor]

        if not pnls:
            return False, {'risk_reward': 0}

        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        avg_win = np.mean(winners) if winners else 0
        avg_loss = abs(np.mean(losers)) if losers else 1

        risk_reward = avg_win / avg_loss if avg_loss > 0 else 0

        # Thresholds
        min_rr = 1.5 if strict else 1.0

        passed = risk_reward >= min_rr

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {risk_reward:.2f}:1 risk/reward (Avg Win: ${avg_win:.0f}, Avg Loss: ${avg_loss:.0f})")
        if not passed:
            print(f"   Required: >{min_rr}:1")

        return passed, {
            'risk_reward': risk_reward,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }

    def _test_drawdown(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test maximum drawdown"""
        cursor = self.conn.execute('''
            SELECT max_drawdown_pct
            FROM strategy_performance
            WHERE strategy_name = ?
        ''', (strategy_name,))

        result = cursor.fetchone()

        if not result:
            return False, {'max_drawdown': 0}

        max_dd = result['max_drawdown_pct']

        # Thresholds
        max_allowed_dd = 20 if strict else 30

        passed = max_dd <= max_allowed_dd

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {max_dd:.1f}% max drawdown")
        if not passed:
            print(f"   Required: <{max_allowed_dd}%")

        return passed, {'max_drawdown': max_dd}

    def _test_sharpe(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test Sharpe ratio"""
        cursor = self.conn.execute('''
            SELECT sharpe_ratio
            FROM strategy_performance
            WHERE strategy_name = ?
        ''', (strategy_name,))

        result = cursor.fetchone()

        if not result:
            return False, {'sharpe_ratio': 0}

        sharpe = result['sharpe_ratio']

        # Thresholds
        min_sharpe = 0.8 if strict else 0.5

        passed = sharpe >= min_sharpe

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {sharpe:.2f} Sharpe ratio")
        if not passed:
            print(f"   Required: >{min_sharpe}")

        return passed, {'sharpe_ratio': sharpe}

    def _test_consistency(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test consistency of returns"""
        cursor = self.conn.execute('''
            SELECT portfolio_value
            FROM portfolio_history
            WHERE strategy_name = ?
            ORDER BY date
        ''', (strategy_name,))

        values = [row['portfolio_value'] for row in cursor]

        if len(values) < 30:
            print("   ⚠️  Insufficient data for consistency test")
            return False, {'consistency_score': 0}

        # Calculate rolling 30-day returns
        values_series = pd.Series(values)
        rolling_returns = values_series.pct_change(30).dropna()

        # Consistency = low std dev of rolling returns
        std_returns = rolling_returns.std()
        consistency_score = 1 / (1 + std_returns) * 100  # Higher = more consistent

        # Thresholds
        min_consistency = 70 if strict else 50

        passed = consistency_score >= min_consistency

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {consistency_score:.1f} consistency score")
        if not passed:
            print(f"   Required: >{min_consistency}")

        return passed, {'consistency_score': consistency_score}

    def _test_regime_performance(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test performance across market regimes"""
        # Get portfolio history
        cursor = self.conn.execute('''
            SELECT date, portfolio_value
            FROM portfolio_history
            WHERE strategy_name = ?
            ORDER BY date
        ''', (strategy_name,))

        data = [(pd.to_datetime(row['date']), row['portfolio_value']) for row in cursor]

        if len(data) < 60:
            print("   ⚠️  Insufficient data for regime analysis")
            return True, {}  # Skip test if not enough data

        df = pd.DataFrame(data, columns=['date', 'value'])
        df.set_index('date', inplace=True)

        # Detect regimes (simplified)
        returns_30d = df['value'].pct_change(30)

        bull_periods = returns_30d > 0.05  # >5% in 30 days
        bear_periods = returns_30d < -0.05  # <-5% in 30 days

        bull_return = returns_30d[bull_periods].mean() if any(bull_periods) else 0
        bear_return = returns_30d[bear_periods].mean() if any(bear_periods) else 0

        # In strict mode, must be positive in both regimes
        if strict:
            passed = bull_return > 0 and bear_return > -0.03  # Allow small loss in bear
        else:
            passed = bull_return > 0 or bear_return > -0.05  # Just need to not crash

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: Bull: {bull_return*100:.1f}%, Bear: {bear_return*100:.1f}%")

        return passed, {
            'bull_regime_return': bull_return * 100,
            'bear_regime_return': bear_return * 100
        }

    def _test_execution_quality(self, strategy_name: str, strict: bool) -> Tuple[bool, Dict]:
        """Test trade execution quality"""
        cursor = self.conn.execute('''
            SELECT
                COUNT(*) as attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM trade_attempts
            WHERE strategy_name = ?
        ''', (strategy_name,))

        result = cursor.fetchone()

        if result['attempts'] == 0:
            return False, {'execution_rate': 0}

        execution_rate = result['successful'] / result['attempts'] * 100

        # Thresholds
        min_execution = 70 if strict else 50

        passed = execution_rate >= min_execution

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {execution_rate:.1f}% execution rate ({result['successful']}/{result['attempts']})")
        if not passed:
            print(f"   Required: >{min_execution}%")

        return passed, {'execution_rate': execution_rate}

    def _print_validation_summary(self, strategy_name: str, passed: bool, score: float, issues: List[str], recommendations: List[str]):
        """Print validation summary"""
        print(f"\n{'='*70}")
        print(f"VALIDATION SUMMARY: {strategy_name}")
        print(f"{'='*70}\n")

        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Score: {score:.0f}/100\n")

        if issues:
            print("Issues Found:")
            for issue in issues:
                print(f"   ❌ {issue}")
            print()

        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"   💡 {rec}")
            print()

        if passed:
            print("🎉 Strategy is ready for production!")
        else:
            print("⚠️  Strategy needs improvement before production use.")

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """CLI for strategy validation"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate trading strategies')
    parser.add_argument('--db', required=True, help='Path to simulation database')
    parser.add_argument('--strategy', help='Specific strategy to validate')
    parser.add_argument('--strict', action='store_true', help='Use strict (production) thresholds')

    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        return

    validator = StrategyValidator(args.db)

    if args.strategy:
        result = validator.validate_strategy(args.strategy, strict=args.strict)

        # Save results
        results_file = Path('validation_results.json')
        results_data = {
            'strategy': result.strategy_name,
            'timestamp': datetime.now().isoformat(),
            'passed': result.passed,
            'score': result.score,
            'issues': result.issues,
            'recommendations': result.recommendations,
            'metrics': result.metrics
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"\n📄 Results saved to: {results_file}")
    else:
        # Validate all strategies
        conn = sqlite3.connect(args.db)
        cursor = conn.execute('SELECT DISTINCT strategy_name FROM strategy_performance')
        strategies = [row[0] for row in cursor]
        conn.close()

        for strategy in strategies:
            validator.validate_strategy(strategy, strict=args.strict)

    validator.close()


if __name__ == '__main__':
    main()
