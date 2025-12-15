/* ===================================================================
   Comparison View - Multi-Strategy Comparison
   =================================================================== */

const { useState, useEffect } = React;
const { api, formatPercent } = window.TradingDashboard;
const { LoadingSpinner, ErrorMessage, Card, MetricCard } = window.TradingDashboard.Components;

// ===================================================================
// Comparison View Component
// ===================================================================
const ComparisonView = ({ strategies }) => {
    const [comparison, setComparison] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadComparison();
    }, []);

    const loadComparison = async () => {
        try {
            setLoading(true);
            const data = await api.compareAll();
            setComparison(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorMessage message={error} onRetry={loadComparison} />;
    if (!comparison) return null;

    return (
        <div className="space-y-6 fade-in">
            {/* Best Performers */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard label="Best Return" value={comparison.best_return} color="green" icon="🏆" />
                <MetricCard label="Best Sharpe" value={comparison.best_sharpe} color="blue" icon="📊" />
                <MetricCard label="Best Win Rate" value={comparison.best_win_rate} color="purple" icon="🎯" />
                <MetricCard label="Lowest Drawdown" value={comparison.lowest_drawdown} color="orange" icon="🛡️" />
            </div>

            {/* Comparison Table */}
            <Card title="📊 Strategy Comparison">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left font-semibold">Strategy</th>
                                <th className="px-4 py-3 text-right font-semibold">Return %</th>
                                <th className="px-4 py-3 text-right font-semibold">Sharpe</th>
                                <th className="px-4 py-3 text-right font-semibold">Win Rate</th>
                                <th className="px-4 py-3 text-right font-semibold">Max DD</th>
                                <th className="px-4 py-3 text-right font-semibold">Profit Factor</th>
                                <th className="px-4 py-3 text-right font-semibold">Trades</th>
                            </tr>
                        </thead>
                        <tbody>
                            {comparison.strategies.map((s, i) => (
                                <tr key={i} className="border-b hover:bg-gray-50">
                                    <td className="px-4 py-3 font-medium">{s.strategy_name}</td>
                                    <td className={`px-4 py-3 text-right font-semibold ${
                                        s.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                        {formatPercent(s.total_return_pct)}
                                    </td>
                                    <td className="px-4 py-3 text-right">{s.sharpe_ratio.toFixed(3)}</td>
                                    <td className="px-4 py-3 text-right">{s.win_rate_pct.toFixed(1)}%</td>
                                    <td className="px-4 py-3 text-right text-orange-600">{s.max_drawdown_pct.toFixed(2)}%</td>
                                    <td className="px-4 py-3 text-right">{s.profit_factor.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-right">{s.completed_trades}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
};

// Export component
window.TradingDashboard.Comparison = {
    ComparisonView
};