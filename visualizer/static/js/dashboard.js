/* ===================================================================
   Dashboard View - Overall Strategy Review
   =================================================================== */

const { useState, useEffect } = React;
const { api, CONFIG } = window.TradingDashboard;
const { Card, MetricCard, PerformanceTable, StockPerformanceTable } = window.TradingDashboard.Components;
const { LineChartComponent, BarChartComponent } = window.TradingDashboard.Charts;

// ===================================================================
// Analysis Browser Component
// ===================================================================
const AnalysisBrowser = ({ onSelectAnalysis }) => {
    const [analyses, setAnalyses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadAnalyses();
    }, []);

    const loadAnalyses = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await api.getAnalyses();
            setAnalyses(data.analyses);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = async (analysisId) => {
        try {
            await api.selectAnalysis(analysisId);
            onSelectAnalysis(analysisId);
        } catch (err) {
            setError(err.message);
        }
    };

    if (loading) return <window.TradingDashboard.Components.LoadingSpinner />;
    if (error) return <window.TradingDashboard.Components.ErrorMessage message={error} onRetry={loadAnalyses} />;

    if (analyses.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center max-w-md">
                    <div className="text-6xl mb-4">📊</div>
                    <h2 className="text-2xl font-bold text-gray-800 mb-4">No Analysis Databases Found</h2>
                    <p className="text-gray-600 mb-6">
                        Please run the analysis engine first to generate analysis databases.
                    </p>
                    <div className="bg-gray-100 rounded-lg p-4 text-left">
                        <code className="text-sm text-gray-800">
                            cd ../analysis<br/>
                            python analysis_engine.py --latest
                        </code>
                    </div>
                    <button
                        onClick={loadAnalyses}
                        className="mt-6 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700"
                    >
                        🔄 Refresh
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-6xl mx-auto px-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-800 mb-2">📊 Select Analysis Database</h1>
                    <p className="text-gray-600">Choose an analysis to visualize trading strategy performance</p>
                </div>
                
                <div className="grid gap-4">
                    {analyses.map((analysis) => (
                        <div
                            key={analysis.analysis_id}
                            onClick={() => handleSelect(analysis.analysis_id)}
                            className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg hover:border-blue-500 border-2 border-transparent transition-all"
                        >
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <h3 className="text-xl font-bold text-gray-800 mb-3">{analysis.filename}</h3>
                                    <div className="grid grid-cols-3 gap-6 text-sm">
                                        <div>
                                            <span className="text-gray-500 block mb-1">Simulation</span>
                                            <span className="font-medium text-gray-800">{analysis.simulation_id}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 block mb-1">Universe</span>
                                            <span className="font-medium text-gray-800">{analysis.universe}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 block mb-1">Strategies</span>
                                            <span className="font-medium text-gray-800">{analysis.num_strategies}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right ml-6">
                                    <div className="text-sm text-gray-600 mb-1">
                                        {new Date(analysis.created_at).toLocaleDateString()}
                                    </div>
                                    <div className="text-sm text-gray-600">
                                        {new Date(analysis.created_at).toLocaleTimeString()}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">
                                        {analysis.size_kb.toFixed(1)} KB
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="mt-6 text-center">
                    <button
                        onClick={loadAnalyses}
                        className="px-4 py-2 text-blue-600 hover:text-blue-800 font-medium"
                    >
                        🔄 Refresh List
                    </button>
                </div>
            </div>
        </div>
    );
};

// ===================================================================
// Dashboard View Component
// ===================================================================
const DashboardView = ({ summary, charts, stocks }) => {
    const { formatPercent } = window.TradingDashboard;
    
    if (!summary) return null;

    const metrics = summary.summary;

    return (
        <div className="space-y-6 fade-in">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                    label="Total Return"
                    value={formatPercent(metrics.total_return_pct)}
                    color={metrics.total_return_pct >= 0 ? 'green' : 'red'}
                    icon="💰"
                />
                <MetricCard
                    label="Sharpe Ratio"
                    value={metrics.sharpe_ratio.toFixed(3)}
                    color="blue"
                    icon="📊"
                />
                <MetricCard
                    label="Win Rate"
                    value={`${metrics.win_rate_pct.toFixed(1)}%`}
                    color="purple"
                    icon="🎯"
                />
                <MetricCard
                    label="Max Drawdown"
                    value={`${metrics.max_drawdown_pct.toFixed(2)}%`}
                    color="orange"
                    icon="⚠️"
                />
            </div>

            {/* Equity Curve */}
            <Card title="📈 Portfolio Equity Curve">
                {charts?.equity_curve && charts.equity_curve.dates && charts.equity_curve.values ? (
                    <LineChartComponent 
                        data={charts.equity_curve.values}
                        labels={charts.equity_curve.dates}
                        label="Portfolio Value"
                        showBaseline={true}
                        baselineValue={charts.equity_curve.initial_cash}
                        height={CONFIG.CHART_HEIGHT}
                    />
                ) : (
                    <div className="text-center py-8 text-gray-500">No equity curve data available</div>
                )}
            </Card>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card title="📊 Returns Distribution">
                    {charts?.returns_distribution && charts.returns_distribution.length > 0 ? (
                        <BarChartComponent 
                            data={charts.returns_distribution.map(d => d.count)}
                            labels={charts.returns_distribution.map(d => ((d.bin_start + d.bin_end) / 2).toFixed(1) + '%')}
                            label="Trade Count"
                            height={250}
                        />
                    ) : (
                        <div className="text-center py-8 text-gray-500">No distribution data</div>
                    )}
                </Card>

                <Card title="📅 Monthly Returns">
                    {charts?.monthly_returns && charts.monthly_returns.length > 0 ? (
                        <BarChartComponent 
                            data={charts.monthly_returns.map(d => d.return_pct)}
                            labels={charts.monthly_returns.map(d => d.year_month)}
                            label="Return %"
                            height={250}
                            colorize={true}
                        />
                    ) : (
                        <div className="text-center py-8 text-gray-500">No monthly data</div>
                    )}
                </Card>
            </div>

            {/* Performance Table */}
            <Card title="📋 Performance Metrics">
                <PerformanceTable metrics={metrics} />
            </Card>

            {/* Stock Performance */}
            <Card title="🏆 Top/Bottom Stock Performance">
                <StockPerformanceTable stocks={stocks} />
            </Card>
        </div>
    );
};

// Export components
window.TradingDashboard.Dashboard = {
    AnalysisBrowser,
    DashboardView
};