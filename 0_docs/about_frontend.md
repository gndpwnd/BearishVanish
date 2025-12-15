# Trading Dashboard - Modular Frontend Structure

## 🐛 Issues Fixed

### 1. DateTime Serialization Error
**Problem:** `TypeError: Object of type datetime is not JSON serializable`
- Error occurred in error handlers trying to serialize datetime objects
- FastAPI's error responses contained `datetime.now()` that couldn't be JSON serialized

**Solution:**
- Updated all Pydantic models to use `BaseResponse` with proper JSON encoders
- Changed datetime fields to use ISO string format: `datetime.now().isoformat()`
- Added `ConfigDict` with custom `json_encoders` for datetime/date objects

### 2. UTF-8 Decoding Error
**Problem:** `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 in position 1`
- SQLite database contained data that couldn't be decoded as UTF-8
- FastAPI tried to decode bytes as UTF-8 strings automatically

**Solution:**
- Added `_row_to_dict()` method in `AnalysisReader` to handle type conversion
- Implements graceful fallback: UTF-8 → latin-1 → string representation
- Converts datetime/date objects to ISO strings before serialization
- Handles None values properly

## 📁 New Modular Structure

### File Organization

```
static/js/
├── core.js           # Core utilities, API client, config
├── components.js     # Reusable UI components
├── charts.js         # Chart.js chart components
├── dashboard.js      # Overall strategy review (main dashboard)
├── trades.js         # Trade history analysis & performance
├── comparison.js     # Strategy comparison view
└── app.js           # Main application entry point
```

### Loading Order (Critical!)

The files **must** be loaded in this order in `index.html`:

1. **core.js** - Sets up `window.TradingDashboard` namespace
2. **components.js** - Adds UI components to namespace
3. **charts.js** - Adds chart components to namespace
4. **dashboard.js** - Adds dashboard views to namespace
5. **trades.js** - Adds trade analysis to namespace
6. **comparison.js** - Adds comparison view to namespace
7. **app.js** - Main app that uses all above modules

### Module Structure

Each module exports to a global namespace:

```javascript
// core.js exports:
window.TradingDashboard = {
    CONFIG,
    api,
    formatCurrency,
    formatPercent,
    formatDate
}

// components.js adds:
window.TradingDashboard.Components = { ... }

// charts.js adds:
window.TradingDashboard.Charts = { ... }

// And so on...
```

## 🎯 Module Responsibilities

### 1. core.js - Foundation
- **Configuration:** API endpoints, chart settings, colors
- **API Client:** All backend communication methods
- **Utilities:** Currency, percentage, date formatting

### 2. components.js - UI Building Blocks
- **Loading states:** `LoadingSpinner`, `ErrorMessage`
- **Cards:** `Card`, `MetricCard`
- **Tables:** `PerformanceTable`, `StockPerformanceTable`, `MetricRow`

### 3. charts.js - Visualization
- **LineChartComponent:** Equity curves, time series
- **BarChartComponent:** Returns distribution, monthly performance

### 4. dashboard.js - Strategy Overview
- **AnalysisBrowser:** Select analysis database
- **DashboardView:** Main strategy performance view
  - Key metrics cards
  - Equity curve chart
  - Returns distribution
  - Monthly returns
  - Performance metrics table
  - Top/bottom stock performance

### 5. trades.js - Trade Analysis
- **TradesView:** Detailed trade history
  - Trade statistics summary
  - Complete trade history table
  - Pagination support
  - Trade filtering by status

### 6. comparison.js - Multi-Strategy
- **ComparisonView:** Compare multiple strategies
  - Best performers highlights
  - Side-by-side comparison table
  - All key metrics for each strategy

### 7. app.js - Main Application
- **Dashboard:** Main container component
  - Header with navigation
  - Strategy selector
  - View switching (dashboard/trades/comparison)
  - Data loading orchestration
- **App:** Root component
  - Analysis selection flow
  - Global application state

## 🔄 Data Flow

```
User Action
    ↓
App Component
    ↓
View Component (Dashboard/Trades/Comparison)
    ↓
API Client (core.js)
    ↓
Backend FastAPI
    ↓
Database Readers
    ↓
Response
    ↓
Render Components
```

## 🚀 Benefits of Modular Structure

### 1. **Maintainability**
- Each module has a single responsibility
- Easy to locate and fix bugs
- Clear dependencies between modules

### 2. **Scalability**
- Add new views by creating new module files
- Extend functionality without touching existing code
- Modules can be developed independently

### 3. **Reusability**
- Components used across multiple views
- Charts abstracted for any data
- Utilities available globally

### 4. **Testability**
- Each module can be tested independently
- Mock dependencies easily
- Clear input/output contracts

### 5. **Collaboration**
- Different team members can work on different modules
- Less merge conflicts
- Clear ownership of code sections

## 🛠️ Future Enhancements

### Potential New Modules

1. **risk.js** - Risk Analysis in Depth
   - Drawdown analysis
   - VaR and CVaR calculations
   - Risk-adjusted returns
   - Monte Carlo simulations

2. **analytics.js** - Advanced Analytics
   - Correlation analysis
   - Factor attribution
   - Performance attribution
   - Rolling metrics

3. **export.js** - Data Export
   - CSV export
   - PDF reports
   - Excel workbooks
   - Custom report builder

4. **settings.js** - User Preferences
   - Theme selection
   - Chart preferences
   - Default views
   - Saved filters

## 📝 Development Guidelines

### Adding a New Module

1. Create new file in `static/js/`
2. Follow naming convention: `feature.js`
3. Export to namespace:
   ```javascript
   window.TradingDashboard.FeatureName = {
       Component1,
       Component2
   };
   ```
4. Add to `index.html` in correct load order
5. Use in `app.js` or other modules

### Component Guidelines

- Use functional components with hooks
- Keep components focused and small
- Extract reusable logic to utilities
- Handle loading and error states
- Document complex logic with comments

### API Integration

- All API calls go through `api` object in core.js
- Add new endpoints to `api` object
- Handle errors consistently
- Show loading states during requests

## 🐛 Debugging Tips

### If modules aren't loading:
1. Check browser console for script errors
2. Verify load order in `index.html`
3. Ensure each module exports to correct namespace
4. Check for JavaScript syntax errors

### If components aren't rendering:
1. Verify component is exported from module
2. Check import statement uses correct namespace
3. Ensure React and ReactDOM are loaded
4. Check for runtime errors in console

### If API calls fail:
1. Check network tab in browser DevTools
2. Verify API endpoint in `CONFIG.API_BASE`
3. Check backend is running
4. Review error messages from backend

## 📚 Resources

- **React Hooks:** https://react.dev/reference/react
- **Chart.js:** https://www.chartjs.org/docs/latest/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **FastAPI:** https://fastapi.tiangolo.com/