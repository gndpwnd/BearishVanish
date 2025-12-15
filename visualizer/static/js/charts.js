/* ===================================================================
   Chart Components using Chart.js
   =================================================================== */

const { useRef, useEffect } = React;
const { CONFIG, formatCurrency } = window.TradingDashboard;

// ===================================================================
// Line Chart Component
// ===================================================================
const LineChartComponent = ({ data, labels, label, height = 300, showBaseline = false, baselineValue = null }) => {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current) return;

        // Destroy existing chart
        if (chartRef.current) {
            chartRef.current.destroy();
        }

        const ctx = canvasRef.current.getContext('2d');

        const datasets = [{
            label: label,
            data: data,
            borderColor: CONFIG.CHART_COLORS.primary,
            backgroundColor: CONFIG.CHART_COLORS.primary + '20',
            borderWidth: 2,
            tension: 0.1,
            fill: true
        }];

        if (showBaseline && baselineValue) {
            datasets.push({
                label: 'Initial',
                data: new Array(data.length).fill(baselineValue),
                borderColor: CONFIG.CHART_COLORS.gray,
                borderWidth: 1,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0
            });
        }

        chartRef.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += formatCurrency(context.parsed.y);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return '$' + (value / 1000).toFixed(0) + 'k';
                            }
                        }
                    },
                    x: {
                        ticks: {
                            maxTicksLimit: 10
                        }
                    }
                }
            }
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [data, labels]);

    return <canvas ref={canvasRef} height={height}></canvas>;
};

// ===================================================================
// Bar Chart Component
// ===================================================================
const BarChartComponent = ({ data, labels, label, height = 250, colorize = false }) => {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current) return;

        if (chartRef.current) {
            chartRef.current.destroy();
        }

        const ctx = canvasRef.current.getContext('2d');

        const backgroundColor = colorize 
            ? data.map(val => val >= 0 ? CONFIG.CHART_COLORS.success : CONFIG.CHART_COLORS.danger)
            : CONFIG.CHART_COLORS.primary;

        chartRef.current = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    backgroundColor: backgroundColor,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return label + ': ' + context.parsed.y.toFixed(2) + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            font: {
                                size: 9
                            }
                        }
                    }
                }
            }
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, [data, labels]);

    return <canvas ref={canvasRef} height={height}></canvas>;
};

// Export chart components
window.TradingDashboard.Charts = {
    LineChartComponent,
    BarChartComponent
};