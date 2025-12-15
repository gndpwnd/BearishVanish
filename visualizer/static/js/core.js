/* ===================================================================
   Core Utilities & API Client
   =================================================================== */

// ===================================================================
// Configuration
// ===================================================================
const CONFIG = {
    API_BASE: 'http://localhost:8000/api',
    PAGE_SIZE: 50,
    CHART_HEIGHT: 300,
    CHART_COLORS: {
        primary: '#2196F3',
        secondary: '#FF9800',
        success: '#4CAF50',
        danger: '#f44336',
        warning: '#FFC107',
        info: '#00BCD4',
        gray: '#999'
    }
};

// ===================================================================
// API Client
// ===================================================================
const api = {
    async request(endpoint, options = {}) {
        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'API Error' }));
            throw new Error(error.detail || 'API Error');
        }
        return response.json();
    },

    get(endpoint) {
        return this.request(endpoint);
    },

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    // Analyses
    getAnalyses: () => api.get('/analyses'),
    selectAnalysis: (id) => api.post(`/analyses/select/${id}`, {}),
    getCurrentAnalysis: () => api.get('/analyses/current/info'),

    // Strategies
    getStrategies: () => api.get('/strategies'),
    getStrategySummary: (name) => api.get(`/strategies/${name}`),
    getStockPerformance: (name) => api.get(`/strategies/${name}/stocks`),

    // Charts
    getAllCharts: (name) => api.get(`/charts/${name}/all`),
    getEquityCurve: (name) => api.get(`/charts/${name}/equity`),

    // Trades
    getTrades: (name, page = 1) => api.get(`/trades/${name}?page=${page}&page_size=${CONFIG.PAGE_SIZE}`),
    getTradeStatistics: (name) => api.get(`/trades/${name}/statistics`),

    // Comparison
    compareAll: () => api.get('/compare'),
};

// ===================================================================
// Utility Functions
// ===================================================================
const formatCurrency = (value) => {
    if (value === null || value === undefined) return '--';
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};

const formatPercent = (value, decimals = 2) => {
    if (value === null || value === undefined) return '--';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(decimals)}%`;
};

const formatDate = (dateStr) => {
    if (!dateStr) return '--';
    return new Date(dateStr).toLocaleDateString();
};

// Export for global use
window.TradingDashboard = {
    CONFIG,
    api,
    formatCurrency,
    formatPercent,
    formatDate
};