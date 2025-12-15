/* ===================================================================
   Reusable UI Components
   =================================================================== */

const { useState, useEffect, useMemo, useRef } = React;
const { formatCurrency, formatPercent, formatDate } = window.TradingDashboard;

// ===================================================================
// Loading & Error Components
// ===================================================================
const LoadingSpinner = () => (
    <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
        <span className="ml-3 text-gray-600">Loading...</span>
    </div>
);

const ErrorMessage = ({ message, onRetry }) => (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 m-4">
        <div className="flex items-start">
            <span className="text-2xl mr-3">❌</span>
            <div className="flex-1">
                <p className="text-red-800 font-medium">Error</p>
                <p className="text-red-700 text-sm mt-1">{message}</p>
                {onRetry && (
                    <button
                        onClick={onRetry}
                        className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
                    >
                        Try Again
                    </button>
                )}
            </div>
        </div>
    </div>
);

// ===================================================================
// Card Components
// ===================================================================
const Card = ({ title, children, className = '', actions }) => (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
        {(title || actions) && (
            <div className="flex justify-between items-center mb-4">
                {title && <h3 className="text-lg font-bold text-gray-800">{title}</h3>}
                {actions && <div className="flex space-x-2">{actions}</div>}
            </div>
        )}
        {children}
    </div>
);

const MetricCard = ({ label, value, color = 'blue', icon = '📊' }) => {
    const colors = {
        blue: 'from-blue-400 to-blue-600',
        green: 'from-green-400 to-green-600',
        red: 'from-red-400 to-red-600',
        purple: 'from-purple-400 to-purple-600',
        orange: 'from-orange-400 to-orange-600',
        yellow: 'from-yellow-400 to-yellow-600'
    };

    return (
        <div className={`bg-gradient-to-br ${colors[color]} rounded-lg p-4 text-white shadow-lg hover:shadow-xl transition-all`}>
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium opacity-90">{label}</span>
                <span className="text-2xl">{icon}</span>
            </div>
            <div className="text-2xl font-bold">{value}</div>
        </div>
    );
};

// ===================================================================
// Table Components
// ===================================================================
const MetricRow = ({ label, value }) => (
    <div className="flex justify-between py-2 border-b border-gray-100 hover:bg-gray-50 px-2 rounded">
        <span className="text-gray-600 text-sm">{label}</span>
        <span className="font-medium text-gray-800 text-sm">{value}</span>
    </div>
);

const PerformanceTable = ({ metrics }) => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-2">
            <h4 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wide">Returns</h4>
            <MetricRow label="Total Return" value={formatPercent(metrics.total_return_pct)} />
            <MetricRow label="Annualized Return" value={formatPercent(metrics.annualized_return_pct)} />
            <MetricRow label="Total Profit" value={formatCurrency(metrics.total_profit_dollars)} />
            
            <h4 className="font-bold text-gray-700 mb-3 mt-6 text-sm uppercase tracking-wide">Risk</h4>
            <MetricRow label="Sharpe Ratio" value={metrics.sharpe_ratio.toFixed(3)} />
            <MetricRow label="Sortino Ratio" value={metrics.sortino_ratio.toFixed(3)} />
            <MetricRow label="Calmar Ratio" value={metrics.calmar_ratio.toFixed(3)} />
            <MetricRow label="Max Drawdown" value={`${metrics.max_drawdown_pct.toFixed(2)}%`} />
            <MetricRow label="Volatility (Annual)" value={`${metrics.volatility_annual_pct.toFixed(2)}%`} />
        </div>
        
        <div className="space-y-2">
            <h4 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wide">Trade Statistics</h4>
            <MetricRow label="Win Rate" value={`${metrics.win_rate_pct.toFixed(1)}%`} />
            <MetricRow label="Profit Factor" value={metrics.profit_factor.toFixed(2)} />
            <MetricRow label="Completed Trades" value={metrics.completed_trades} />
            <MetricRow label="Winning Trades" value={metrics.winning_trades} />
            <MetricRow label="Losing Trades" value={metrics.losing_trades} />
            <MetricRow label="Avg Win" value={formatCurrency(metrics.avg_win_dollars)} />
            <MetricRow label="Avg Loss" value={formatCurrency(metrics.avg_loss_dollars)} />
            <MetricRow label="Risk/Reward Ratio" value={`${metrics.risk_reward_ratio.toFixed(2)}:1`} />
            <MetricRow label="Avg Hold Days" value={`${metrics.avg_hold_days.toFixed(1)} days`} />
        </div>
    </div>
);

const StockPerformanceTable = ({ stocks }) => {
    if (!stocks || stocks.length === 0) {
        return <div className="text-center py-8 text-gray-500">No stock performance data available</div>;
    }

    const top10 = stocks.slice(0, 10);
    const bottom10 = stocks.slice(-10).reverse();

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
                <h4 className="font-bold text-green-700 mb-3 flex items-center">
                    <span className="mr-2">🔼</span> Top Performers
                </h4>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-3 py-2 text-left">Symbol</th>
                                <th className="px-3 py-2 text-right">Trades</th>
                                <th className="px-3 py-2 text-right">Win Rate</th>
                                <th className="px-3 py-2 text-right">Net P&L</th>
                            </tr>
                        </thead>
                        <tbody>
                            {top10.map((stock, i) => (
                                <tr key={i} className="border-b hover:bg-green-50">
                                    <td className="px-3 py-2 font-medium">{stock.symbol}</td>
                                    <td className="px-3 py-2 text-right">{stock.total_trades}</td>
                                    <td className="px-3 py-2 text-right">{stock.win_rate_pct.toFixed(1)}%</td>
                                    <td className="px-3 py-2 text-right text-green-600 font-medium">
                                        {formatCurrency(stock.net_profit_loss)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <div>
                <h4 className="font-bold text-red-700 mb-3 flex items-center">
                    <span className="mr-2">🔽</span> Bottom Performers
                </h4>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-3 py-2 text-left">Symbol</th>
                                <th className="px-3 py-2 text-right">Trades</th>
                                <th className="px-3 py-2 text-right">Win Rate</th>
                                <th className="px-3 py-2 text-right">Net P&L</th>
                            </tr>
                        </thead>
                        <tbody>
                            {bottom10.map((stock, i) => (
                                <tr key={i} className="border-b hover:bg-red-50">
                                    <td className="px-3 py-2 font-medium">{stock.symbol}</td>
                                    <td className="px-3 py-2 text-right">{stock.total_trades}</td>
                                    <td className="px-3 py-2 text-right">{stock.win_rate_pct.toFixed(1)}%</td>
                                    <td className="px-3 py-2 text-right text-red-600 font-medium">
                                        {formatCurrency(stock.net_profit_loss)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// Export components
window.TradingDashboard.Components = {
    LoadingSpinner,
    ErrorMessage,
    Card,
    MetricCard,
    MetricRow,
    PerformanceTable,
    StockPerformanceTable
};