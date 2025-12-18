"""
Markdown Report Generator for Trading Strategies
Generates comprehensive analysis reports suitable for LLM review
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from io import StringIO


class MarkdownReportGenerator:
    """Generate professional markdown reports for strategy analysis"""
    
    def __init__(self, reader):
        """
        Initialize with analysis reader
        
        Args:
            reader: AnalysisReader instance for fetching data
        """
        self.reader = reader
        self.generated_at = datetime.now()
    
    def get_db_timestamp(self) -> str:
        """
        Get database timestamp from metadata for filename
        
        Returns:
            Formatted timestamp string (YYYYMMDD_HHMMSS)
        """
        try:
            # Try to get timestamp from metadata
            metadata = self.reader.get_metadata()
            if 'created_at' in metadata:
                ts = metadata['created_at']
                # Parse and reformat
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.strftime('%Y%m%d_%H%M%S')
            elif 'timestamp' in metadata:
                ts = metadata['timestamp']
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.strftime('%Y%m%d_%H%M%S')
        except Exception:
            pass
        
        # Fallback to current time if metadata not available
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def generate_full_report(self, strategy_name: str) -> str:
        """
        Generate comprehensive analysis report for a strategy
        
        Args:
            strategy_name: Name of strategy to analyze
            
        Returns:
            Markdown-formatted report string
        """
        report = StringIO()
        
        # Header
        report.write(self._generate_header(strategy_name))
        
        # Executive Summary
        report.write(self._generate_executive_summary(strategy_name))
        
        # Key Metrics
        report.write(self._generate_key_metrics(strategy_name))
        
        # Performance Analysis
        report.write(self._generate_performance_analysis(strategy_name))
        
        # Risk Analysis
        report.write(self._generate_risk_analysis(strategy_name))
        
        # Monthly Performance
        report.write(self._generate_monthly_performance(strategy_name))
        
        # Top Performers
        report.write(self._generate_top_performers(strategy_name))
        
        # Drawdown Analysis
        report.write(self._generate_drawdown_analysis(strategy_name))
        
        # Trade Analysis
        report.write(self._generate_trade_analysis(strategy_name))
        
        # Weaknesses & Opportunities
        report.write(self._generate_weaknesses_and_opportunities(strategy_name))
        
        # Recommendations
        report.write(self._generate_recommendations(strategy_name))
        
        # Metadata
        report.write(self._generate_metadata(strategy_name))
        
        return report.getvalue()
    
    def _generate_header(self, strategy_name: str) -> str:
        """Generate report header"""
        return f"""# Strategy Analysis Report: {strategy_name}

**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

"""
    
    def _generate_executive_summary(self, strategy_name: str) -> str:
        """Generate executive summary"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return "## Executive Summary\n\n*No data available*\n\n"
            
            output = StringIO()
            output.write("## Executive Summary\n\n")
            
            # Overall performance
            total_return = summary.get('total_return_pct', 0)
            total_profit = summary.get('total_profit_dollars', 0)
            total_trades = summary.get('total_trades', 0)
            win_rate = summary.get('win_rate_pct', 0)
            sharpe = summary.get('sharpe_ratio', 0)
            max_dd = summary.get('max_drawdown_pct', 0)
            
            status = self._get_performance_status(total_return, sharpe, max_dd)
            
            output.write(f"**Status:** {status}\n\n")
            output.write(f"This strategy generated a total return of **{total_return:+.2f}%** ")
            output.write(f"({total_profit:+.0f} USD) over {total_trades} trades with a ")
            output.write(f"**{win_rate:.1f}% win rate**.\n\n")
            
            output.write("| Metric | Value |\n")
            output.write("|--------|-------|\n")
            output.write(f"| Total Return | {total_return:+.2f}% |\n")
            output.write(f"| Total Profit | ${total_profit:+,.0f} |\n")
            output.write(f"| Win Rate | {win_rate:.1f}% |\n")
            output.write(f"| Sharpe Ratio | {sharpe:.3f} |\n")
            output.write(f"| Max Drawdown | {max_dd:.2f}% |\n")
            output.write(f"| Total Trades | {total_trades} |\n")
            output.write("\n")
            
            return output.getvalue()
        except Exception as e:
            return f"## Executive Summary\n\n*Error generating summary: {str(e)}*\n\n"
    
    def _generate_key_metrics(self, strategy_name: str) -> str:
        """Generate key metrics section"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## Key Metrics\n\n")
            
            metrics = {
                "Return Metrics": [
                    ("Total Return", summary.get('total_return_pct', 0), "%"),
                    ("Total Profit", summary.get('total_profit_dollars', 0), "$"),
                    ("Average Trade Return", 
                     (summary.get('total_return_pct', 0) / max(summary.get('total_trades', 1), 1)), "%"),
                ],
                "Win/Loss Metrics": [
                    ("Win Rate", summary.get('win_rate_pct', 0), "%"),
                    ("Winning Trades", summary.get('winning_trades', 0), ""),
                    ("Losing Trades", summary.get('losing_trades', 0), ""),
                    ("Profit Factor", summary.get('profit_factor', 0), "x"),
                ],
                "Risk Metrics": [
                    ("Max Drawdown", summary.get('max_drawdown_pct', 0), "%"),
                    ("Sharpe Ratio", summary.get('sharpe_ratio', 0), ""),
                    ("Sortino Ratio", summary.get('sortino_ratio', 0.0), ""),
                    ("Calmar Ratio", summary.get('calmar_ratio', 0.0), ""),
                ],
                "Trade Metrics": [
                    ("Average Trade Duration", summary.get('avg_trade_duration_days', 0), "days"),
                    ("Expectancy", summary.get('expectancy_dollars', 0), "$"),
                ]
            }
            
            for section, metric_list in metrics.items():
                output.write(f"### {section}\n\n")
                output.write("| Metric | Value |\n")
                output.write("|--------|-------|\n")
                for name, value, unit in metric_list:
                    if isinstance(value, float):
                        output.write(f"| {name} | {value:.3f} {unit} |\n")
                    else:
                        output.write(f"| {name} | {value:,.0f} {unit} |\n")
                output.write("\n")
            
            return output.getvalue()
        except Exception as e:
            return f"## Key Metrics\n\n*Error generating metrics: {str(e)}*\n\n"
    
    def _generate_performance_analysis(self, strategy_name: str) -> str:
        """Generate performance analysis"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## Performance Analysis\n\n")
            
            total_return = summary.get('total_return_pct', 0)
            win_rate = summary.get('win_rate_pct', 0)
            profit_factor = summary.get('profit_factor', 0)
            
            # Performance interpretation
            if total_return > 50:
                output.write("**This strategy shows excellent positive returns.** ")
            elif total_return > 20:
                output.write("**This strategy shows strong positive returns.** ")
            elif total_return > 0:
                output.write("**This strategy shows modest positive returns.** ")
            elif total_return > -20:
                output.write("**This strategy shows minor losses.** ")
            else:
                output.write("**This strategy shows significant losses.** ")
            
            output.write(f"With {win_rate:.1f}% winning trades and a profit factor of {profit_factor:.2f}x, ")
            output.write("the strategy demonstrates consistent execution.\n\n")
            
            # Win rate analysis
            if win_rate > 60:
                output.write("- **Win rate is strong** (>60%): The strategy has good signal accuracy\n")
            elif win_rate > 50:
                output.write("- **Win rate is acceptable** (50-60%): Losses may be larger than wins\n")
            elif win_rate > 40:
                output.write("- **Win rate needs improvement** (40-50%): Consider refining entry signals\n")
            else:
                output.write("- **Win rate is poor** (<40%): Signal quality needs significant improvement\n")
            
            # Profit factor analysis
            if profit_factor > 2.0:
                output.write("- **Profit factor is excellent** (>2.0x): Gains significantly exceed losses\n")
            elif profit_factor > 1.5:
                output.write("- **Profit factor is good** (1.5-2.0x): Gains exceed losses substantially\n")
            elif profit_factor > 1.0:
                output.write("- **Profit factor is marginal** (1.0-1.5x): Positive but tight margin for error\n")
            else:
                output.write("- **Profit factor is negative** (<1.0x): Losses exceed gains\n")
            
            output.write("\n")
            return output.getvalue()
        except Exception as e:
            return f"## Performance Analysis\n\n*Error: {str(e)}*\n\n"
    
    def _generate_risk_analysis(self, strategy_name: str) -> str:
        """Generate risk analysis"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## Risk Analysis\n\n")
            
            max_dd = summary.get('max_drawdown_pct', 0)
            sharpe = summary.get('sharpe_ratio', 0)
            sortino = summary.get('sortino_ratio', 0.0)
            
            # Drawdown analysis
            if max_dd < 5:
                output.write("- **Drawdown is excellent** (<5%): Strategy is very conservative\n")
            elif max_dd < 15:
                output.write("- **Drawdown is acceptable** (5-15%): Normal for active strategies\n")
            elif max_dd < 30:
                output.write("- **Drawdown is moderate** (15-30%): Consider position sizing\n")
            else:
                output.write("- **Drawdown is high** (>30%): Risk management needs review\n")
            
            # Sharpe ratio analysis
            if sharpe > 1.5:
                output.write("- **Sharpe ratio is excellent** (>1.5): Strong risk-adjusted returns\n")
            elif sharpe > 1.0:
                output.write("- **Sharpe ratio is good** (1.0-1.5): Acceptable risk-adjusted performance\n")
            elif sharpe > 0.5:
                output.write("- **Sharpe ratio is fair** (0.5-1.0): Consider risk/reward optimization\n")
            else:
                output.write("- **Sharpe ratio is poor** (<0.5): Risk not adequately compensated\n")
            
            output.write(f"\n**Metrics:**\n")
            output.write(f"- Max Drawdown: {max_dd:.2f}%\n")
            output.write(f"- Sharpe Ratio: {sharpe:.3f}\n")
            output.write(f"- Sortino Ratio: {sortino:.3f}\n")
            output.write("\n")
            
            return output.getvalue()
        except Exception as e:
            return f"## Risk Analysis\n\n*Error: {str(e)}*\n\n"
    
    def _generate_monthly_performance(self, strategy_name: str) -> str:
        """Generate monthly performance section"""
        try:
            monthly = self.reader.get_monthly_returns(strategy_name)
            if monthly is None or monthly.empty:
                return ""
            
            output = StringIO()
            output.write("## Monthly Performance\n\n")
            
            output.write("| Month | Return % | Trades | Win Rate % |\n")
            output.write("|-------|----------|--------|------------|\n")
            
            for _, row in monthly.tail(12).iterrows():
                year_month = str(row.get('year_month', ''))
                return_pct = float(row.get('return_pct', 0)) if pd.notna(row.get('return_pct')) else 0
                trades = int(row.get('num_trades', 0)) if pd.notna(row.get('num_trades')) else 0
                win_rate = float(row.get('win_rate_pct', 0)) if pd.notna(row.get('win_rate_pct')) else 0
                
                output.write(f"| {year_month} | {return_pct:+.2f}% | {trades} | {win_rate:.1f}% |\n")
            
            output.write("\n")
            return output.getvalue()
        except Exception as e:
            return f"## Monthly Performance\n\n*Error: {str(e)}*\n\n"
    
    def _generate_top_performers(self, strategy_name: str) -> str:
        """Generate top performing stocks"""
        try:
            perf = self.reader.get_stock_performance(strategy_name)
            if perf is None or perf.empty:
                return ""
            
            output = StringIO()
            output.write("## Top Performing Stocks\n\n")
            
            # Sort by return
            top_stocks = perf.nlargest(10, 'return_pct')
            
            output.write("| Stock | Return % | Trades | Avg Trade Return % |\n")
            output.write("|-------|----------|--------|--------------------|\n")
            
            for _, row in top_stocks.iterrows():
                symbol = str(row.get('symbol', 'N/A'))
                return_pct = float(row.get('return_pct', 0)) if pd.notna(row.get('return_pct')) else 0
                trades = int(row.get('num_trades', 0)) if pd.notna(row.get('num_trades')) else 0
                avg_ret = return_pct / max(trades, 1)
                
                output.write(f"| {symbol} | {return_pct:+.2f}% | {trades} | {avg_ret:+.2f}% |\n")
            
            output.write("\n")
            return output.getvalue()
        except Exception as e:
            return f"## Top Performers\n\n*Error: {str(e)}*\n\n"
    
    def _generate_drawdown_analysis(self, strategy_name: str) -> str:
        """Generate drawdown analysis"""
        try:
            drawdowns = self.reader.get_drawdown_periods(strategy_name, limit=5)
            if drawdowns is None or drawdowns.empty:
                return ""
            
            output = StringIO()
            output.write("## Recent Drawdown Periods\n\n")
            output.write("Top 5 largest drawdowns and recovery details:\n\n")
            
            output.write("| Start Date | End Date | Depth % | Recovery | Days to Recover |\n")
            output.write("|------------|----------|---------|----------|----------------|\n")
            
            for _, row in drawdowns.head(5).iterrows():
                start = str(row.get('start_date', 'N/A')) if pd.notna(row.get('start_date')) else 'N/A'
                end = str(row.get('end_date', 'N/A')) if pd.notna(row.get('end_date')) else 'N/A'
                depth = float(row.get('depth_pct', 0)) if pd.notna(row.get('depth_pct')) else 0
                recovered = str(row.get('recovered', 'N/A')) if pd.notna(row.get('recovered')) else 'N/A'
                days_to_recover = int(row.get('days_to_recover', 0)) if pd.notna(row.get('days_to_recover')) else 0
                
                output.write(f"| {start} | {end} | {depth:.2f}% | {recovered} | {days_to_recover} |\n")
            
            output.write("\n")
            return output.getvalue()
        except Exception as e:
            return f"## Drawdown Analysis\n\n*Error: {str(e)}*\n\n"
    
    def _generate_trade_analysis(self, strategy_name: str) -> str:
        """Generate trade analysis"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## Trade Statistics\n\n")
            
            total_trades = summary.get('total_trades', 0)
            winning = summary.get('winning_trades', 0)
            losing = summary.get('losing_trades', 0)
            avg_duration = summary.get('avg_trade_duration_days', 0)
            expectancy = summary.get('expectancy_dollars', 0)
            
            output.write(f"- **Total Trades:** {total_trades}\n")
            output.write(f"- **Winning Trades:** {winning}\n")
            output.write(f"- **Losing Trades:** {losing}\n")
            output.write(f"- **Average Trade Duration:** {avg_duration:.1f} days\n")
            output.write(f"- **Expected Value per Trade:** ${expectancy:+,.0f}\n")
            output.write("\n")
            
            return output.getvalue()
        except Exception as e:
            return f"## Trade Statistics\n\n*Error: {str(e)}*\n\n"
    
    def _generate_weaknesses_and_opportunities(self, strategy_name: str) -> str:
        """Generate weaknesses and opportunities section"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## Weaknesses & Opportunities for Improvement\n\n")
            
            issues = []
            
            # Win rate issues
            win_rate = summary.get('win_rate_pct', 0)
            if win_rate < 45:
                issues.append({
                    'severity': 'HIGH',
                    'issue': 'Low Win Rate',
                    'detail': f'Current: {win_rate:.1f}% | Targets lose more often than they win',
                    'suggestion': 'Review entry signal logic; consider more conservative triggers'
                })
            
            # Max drawdown issues
            max_dd = summary.get('max_drawdown_pct', 0)
            if max_dd > 25:
                issues.append({
                    'severity': 'MEDIUM',
                    'issue': 'High Drawdown',
                    'detail': f'Current: {max_dd:.2f}% | Large peak-to-trough decline',
                    'suggestion': 'Implement tighter stop losses or position sizing rules'
                })
            
            # Sharpe ratio issues
            sharpe = summary.get('sharpe_ratio', 0)
            if sharpe < 0.5:
                issues.append({
                    'severity': 'HIGH',
                    'issue': 'Poor Risk-Adjusted Returns',
                    'detail': f'Sharpe Ratio: {sharpe:.3f} | Returns not compensating for volatility',
                    'suggestion': 'Consider volatility filtering or dynamic position sizing'
                })
            
            # Profit factor issues
            pf = summary.get('profit_factor', 0)
            if pf < 1.5:
                issues.append({
                    'severity': 'MEDIUM',
                    'issue': 'Tight Profit Margins',
                    'detail': f'Profit Factor: {pf:.2f}x | Little room for slippage',
                    'suggestion': 'Refine exit strategy; consider trailing stops or targets'
                })
            
            # Trade frequency
            total_trades = summary.get('total_trades', 0)
            if total_trades < 10:
                issues.append({
                    'severity': 'LOW',
                    'issue': 'Limited Trade Sample',
                    'detail': f'Only {total_trades} trades | Statistical reliability uncertain',
                    'suggestion': 'Run on more data or expand stock universe'
                })
            
            if issues:
                for issue in issues:
                    output.write(f"### ⚠️ [{issue['severity']}] {issue['issue']}\n\n")
                    output.write(f"**Issue:** {issue['detail']}\n\n")
                    output.write(f"**Suggestion:** {issue['suggestion']}\n\n")
            else:
                output.write("*No major issues identified.*\n\n")
            
            return output.getvalue()
        except Exception as e:
            return f"## Weaknesses & Opportunities\n\n*Error: {str(e)}*\n\n"
    
    def _generate_recommendations(self, strategy_name: str) -> str:
        """Generate recommendations"""
        try:
            summary = self.reader.get_summary(strategy_name)
            if not summary:
                return ""
            
            output = StringIO()
            output.write("## LLM Review Recommendations\n\n")
            output.write("""This report should be sent to an LLM (Claude, GPT-4, etc.) for deeper analysis.
Here are suggested questions to ask:

1. **Signal Quality:** Analyze the win rate and profit factor. What might be causing winning/losing trades?
2. **Entry Logic:** Are there patterns in when the strategy enters? Can entries be refined?
3. **Exit Strategy:** Review average trade duration. Are exits too tight or too loose?
4. **Indicators:** Based on the performance metrics, what indicators might improve signal quality?
5. **Position Sizing:** Given the drawdown statistics, should position sizing be adjusted?
6. **Market Conditions:** Are there specific market conditions where this strategy performs better/worse?
7. **Risk Management:** Suggest improvements to stop loss and take profit logic
8. **New Ideas:** What variations or enhancements might improve performance?

Example LLM prompt structure:
```
Here's my trading strategy analysis report:

[INSERT THIS REPORT HERE]

Based on this data, please:
1. Identify the main issues limiting performance
2. Suggest 3-5 specific code improvements for the entry/exit logic
3. Propose new indicators or filters that might help
4. Recommend risk management enhancements
```

""")
            
            return output.getvalue()
        except Exception as e:
            return f"## Recommendations\n\n*Error: {str(e)}*\n\n"
    
    def _generate_metadata(self, strategy_name: str) -> str:
        """Generate metadata footer"""
        return f"""---

## Report Metadata

- **Generated:** {self.generated_at.isoformat()}
- **Report Type:** Comprehensive Strategy Analysis
- **Format:** Markdown
- **Purpose:** LLM-compatible strategy review and improvement

### How to Use This Report

1. **Export to File:** Save as `.md` and version control
2. **Send to LLM:** Copy the full content into Claude, GPT-4, or similar
3. **Ask for Analysis:** Request specific improvements or new ideas
4. **Implement Changes:** Update strategy code based on recommendations
5. **Re-run Simulation:** Test improvements and generate new report
6. **Iterate:** Repeat until satisfied with performance

### API Access

This report was generated via the visualizer API. Access it anytime:

```bash
curl http://localhost:8000/api/v1/reports/{strategy_name.replace(" ", "%20")}
```

Or within Python:

```python
import requests
response = requests.get('http://localhost:8000/api/v1/reports/My Strategy')
print(response.text)
```

"""
    
    @staticmethod
    def _get_performance_status(total_return: float, sharpe: float, max_dd: float) -> str:
        """Determine overall strategy status"""
        if total_return > 20 and sharpe > 1.0 and max_dd < 20:
            return "🟢 **EXCELLENT** - Strong returns with good risk management"
        elif total_return > 5 and sharpe > 0.5 and max_dd < 30:
            return "🟡 **GOOD** - Positive returns with acceptable risk profile"
        elif total_return > 0:
            return "🟠 **FAIR** - Positive but with room for improvement"
        else:
            return "🔴 **POOR** - Needs significant revision"
