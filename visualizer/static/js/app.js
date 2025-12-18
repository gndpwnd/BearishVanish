/* ===================================================================
   Trading Dashboard - Main Application
   Modular structure with separate files for each section
   =================================================================== */

// Check if Chart.js loaded
if (typeof Chart === 'undefined') {
    console.error('❌ Chart.js not available!');
    document.getElementById('root').innerHTML = `
        <div style="padding: 50px; text-align: center; font-family: sans-serif;">
            <h1 style="color: #dc2626;">⚠️ Chart.js Library Failed to Load</h1>
            <p style="color: #6b7280; margin-top: 20px;">
                The charting library could not be loaded. Please check your internet connection.
            </p>
            <button onclick="location.reload()" style="margin-top: 30px; padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer;">
                Retry
            </button>
        </div>
    `;
    throw new Error('Chart.js library not loaded');
}

console.log('✅ Chart.js loaded successfully');

// ===================================================================
// Main Dashboard Container Component
// ===================================================================
const { useState, useEffect } = React;
const { api, formatPercent } = window.TradingDashboard;
const { LoadingSpinner, ErrorMessage } = window.TradingDashboard.Components;
const { AnalysisBrowser, DashboardView } = window.TradingDashboard.Dashboard;
const { TradesView } = window.TradingDashboard.Trades;
const { ComparisonView } = window.TradingDashboard.Comparison;

const Dashboard = ({ analysisId }) => {
    const [strategies, setStrategies] = useState([]);
    const [currentStrategy, setCurrentStrategy] = useState(null);
    const [summary, setSummary] = useState(null);
    const [charts, setCharts] = useState(null);
    const [stocks, setStocks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [view, setView] = useState('dashboard');

    useEffect(() => {
        loadStrategies();
    }, []);

    useEffect(() => {
        if (currentStrategy) {
            loadStrategyData();
        }
    }, [currentStrategy]);

    const loadStrategies = async () => {
        try {
            const data = await api.getStrategies();
            setStrategies(data.strategies);
            if (data.strategies.length > 0) {
                setCurrentStrategy(data.strategies[0]);
            }
        } catch (err) {
            setError(err.message);
        }
    };

    const loadStrategyData = async () => {
        try {
            setLoading(true);
            const [summaryData, chartsData, stocksData] = await Promise.all([
                api.getStrategySummary(currentStrategy),
                api.getAllCharts(currentStrategy),
                api.getStockPerformance(currentStrategy)
            ]);
            
            setSummary(summaryData);
            setCharts(chartsData);
            setStocks(stocksData.stocks || []);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (error && !summary) {
        return <ErrorMessage message={error} onRetry={loadStrategyData} />;
    }

    const metrics = summary?.summary;

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
                <div className="container mx-auto px-6 py-4">
                    <h1 className="text-2xl font-bold">📈 Trading Strategy Dashboard</h1>
                    <p className="text-blue-100 text-sm mt-1">Analysis: {analysisId}</p>
                </div>
            </header>

            {/* Navigation */}
            <nav className="bg-white shadow-sm border-b sticky top-0 z-10">
                <div className="container mx-auto px-6">
                    <div className="flex space-x-8">
                        {[
                            { id: 'dashboard', label: 'Dashboard', icon: '📊' },
                            { id: 'trades', label: 'Trade Details', icon: '📋' },
                            { id: 'comparison', label: 'Compare', icon: '📈' }
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setView(tab.id)}
                                className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                                    view === tab.id
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                {tab.icon} {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
            </nav>

            {/* Strategy Selector */}
            <div className="bg-white border-b shadow-sm">
                <div className="container mx-auto px-6 py-4">
                    <div className="flex items-center space-x-4">
                        <label className="font-medium text-gray-700 flex items-center">
                            <span className="mr-2">🎯</span> Strategy:
                        </label>
                        <select
                            value={currentStrategy || ''}
                            onChange={(e) => setCurrentStrategy(e.target.value)}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-64"
                        >
                            {strategies.map((s) => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>

                        {/* Download Report Button */}
                        {currentStrategy && (
                            <button
                                onClick={async () => {
                                    try {
                                        const blob = await api.downloadReport(currentStrategy, 'full');
                                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
                                        const filename = `${currentStrategy.replace(/\s+/g, '_')}_${timestamp}.md`;
                                        downloadFile(blob, filename);
                                    } catch (err) {
                                        alert(`Failed to download report: ${err.message}`);
                                    }
                                }}
                                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center space-x-2"
                            >
                                <span>📥</span>
                                <span>Download Report</span>
                            </button>
                        )}
                        
                        {metrics && (
                            <div className="flex space-x-6 ml-auto text-sm">
                                <span className="text-gray-600">
                                    Return: <strong className={metrics.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                                        {formatPercent(metrics.total_return_pct)}
                                    </strong>
                                </span>
                                <span className="text-gray-600">
                                    Sharpe: <strong className="text-blue-600">{metrics.sharpe_ratio.toFixed(3)}</strong>
                                </span>
                                <span className="text-gray-600">
                                    Win Rate: <strong className="text-purple-600">{metrics.win_rate_pct.toFixed(1)}%</strong>
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="container mx-auto px-6 py-8">
                {loading ? (
                    <LoadingSpinner />
                ) : view === 'dashboard' ? (
                    <DashboardView summary={summary} charts={charts} stocks={stocks} />
                ) : view === 'trades' ? (
                    <TradesView strategy={currentStrategy} />
                ) : (
                    <ComparisonView strategies={strategies} />
                )}
            </div>
        </div>
    );
};

// ===================================================================
// Main App Component
// ===================================================================
const App = () => {
    const [selectedAnalysis, setSelectedAnalysis] = useState(null);

    return (
        <div className="min-h-screen bg-gray-50">
            {!selectedAnalysis ? (
                <AnalysisBrowser onSelectAnalysis={setSelectedAnalysis} />
            ) : (
                <Dashboard analysisId={selectedAnalysis} />
            )}
        </div>
    );
};

// ===================================================================
// Render Application
// ===================================================================
ReactDOM.render(<App />, document.getElementById('root'));