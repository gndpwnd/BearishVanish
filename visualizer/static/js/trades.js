/* ===================================================================
   Trades View - Trade History & Performance Analysis
   =================================================================== */

const { useState, useEffect } = React;
const { api, formatCurrency, formatPercent, formatDate } = window.TradingDashboard;
const { LoadingSpinner, ErrorMessage, Card, MetricCard } = window.TradingDashboard.Components;

// ===================================================================
// Pagination Component
// ===================================================================
const Pagination = ({ page, totalTrades, pageSize, onPageChange }) => {
    const totalPages = Math.ceil(totalTrades / pageSize);
    
    if (totalPages <= 1) return null;  // Don't show if only 1 page
    
    return (
        <div className="flex justify-center items-center space-x-4 mt-6">
            <button
                onClick={() => onPageChange(page - 1)}
                disabled={page === 1}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
                ← Previous
            </button>
            
            <span className="text-gray-700 font-medium">
                Page {page} of {totalPages}
            </span>
            
            <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= totalPages}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
                Next →
            </button>
        </div>
    );
};

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
                {/* NEW: Pagination Controls */}
                <Pagination 
                    page={page}
                    totalTrades={trades.length * 10}  // Approximate total
                    pageSize={CONFIG.PAGE_SIZE}
                    onPageChange={(newPage) => setPage(newPage)}
                />
            </Card>
        </div>
    );
};

// Export component
window.TradingDashboard.Trades = {
    TradesView
};