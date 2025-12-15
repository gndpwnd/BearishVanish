/* ===================================================================
   Trades View - Trade History & Performance Analysis
   =================================================================== */

const { useState, useEffect } = React;
const { api, formatCurrency, formatPercent, formatDate } = window.TradingDashboard;
const { LoadingSpinner, ErrorMessage, Card, MetricCard } = window.TradingDashboard.Components;

// ===================================================================
// Trades View Component
// ===================================================================
const TradesView = ({ strategy }) => {
    const [trades, setTrades] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadTrades();
    }, [strategy, page]);

    const loadTrades = async () => {
        try {
            setLoading(true);
            const [tradesData, statsData] = await Promise.all([
                api.getTrades(strategy, page),
                api.getTradeStatistics(strategy)
            ]);
            setTrades(tradesData.trades);
            setStats(statsData);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorMessage message={error} onRetry={loadTrades} />;

    return (
        <div className="space-y-6 fade-in">
            {/* Statistics */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <MetricCard label="Total Trades" value={stats.total_trades} color="blue" icon="📈" />
                    <MetricCard label="Closed" value={stats.closed_trades} color="green" icon="✅" />
                    <MetricCard label="Open" value={stats.open_positions} color="yellow" icon="⏳" />
                    <MetricCard label="Win Rate" value={`${stats.win_rate.toFixed(1)}%`} color="purple" icon="🎯" />
                    <MetricCard 
                        label="Total P&L" 
                        value={formatCurrency(stats.total_pnl)} 
                        color={stats.total_pnl >= 0 ? 'green' : 'red'} 
                        icon="💵" 
                    />
                </div>
            )}

            {/* Trades Table */}
            <Card title="📋 Trade History">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-3 py-2 text-left">Symbol</th>
                                <th className="px-3 py-2 text-left">Entry Date</th>
                                <th className="px-3 py-2 text-left">Exit Date</th>
                                <th className="px-3 py-2 text-right">Shares</th>
                                <th className="px-3 py-2 text-right">Entry $</th>
                                <th className="px-3 py-2 text-right">Exit $</th>
                                <th className="px-3 py-2 text-right">P&L $</th>
                                <th className="px-3 py-2 text-right">P&L %</th>
                                <th className="px-3 py-2 text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades.map((trade, i) => {
                                const pnlPositive = trade.profit_loss_dollars > 0;
                                const pnlNegative = trade.profit_loss_dollars < 0;
                                const isClosed = trade.trade_status === 'CLOSED';
                                
                                return (
                                    <tr key={i} className={`border-b hover:bg-gray-50 ${
                                        isClosed && pnlPositive ? 'bg-green-50' :
                                        isClosed && pnlNegative ? 'bg-red-50' :
                                        'bg-yellow-50'
                                    }`}>
                                        <td className="px-3 py-2 font-medium">{trade.symbol}</td>
                                        <td className="px-3 py-2">{formatDate(trade.entry_date)}</td>
                                        <td className="px-3 py-2">{formatDate(trade.exit_date)}</td>
                                        <td className="px-3 py-2 text-right">{trade.shares}</td>
                                        <td className="px-3 py-2 text-right">${trade.entry_price.toFixed(2)}</td>
                                        <td className="px-3 py-2 text-right">
                                            {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '--'}
                                        </td>
                                        <td className={`px-3 py-2 text-right font-medium ${
                                            pnlPositive ? 'text-green-600' : pnlNegative ? 'text-red-600' : ''
                                        }`}>
                                            {trade.profit_loss_dollars !== null ? formatCurrency(trade.profit_loss_dollars) : '--'}
                                        </td>
                                        <td className={`px-3 py-2 text-right font-medium ${
                                            pnlPositive ? 'text-green-600' : pnlNegative ? 'text-red-600' : ''
                                        }`}>
                                            {trade.profit_loss_pct !== null ? formatPercent(trade.profit_loss_pct) : '--'}
                                        </td>
                                        <td className="px-3 py-2 text-center">
                                            <span className={`status-badge ${trade.trade_status.toLowerCase()}`}>
                                                {trade.trade_status}
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
};

// Export component
window.TradingDashboard.Trades = {
    TradesView
};