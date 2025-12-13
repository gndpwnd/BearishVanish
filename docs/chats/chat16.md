I want to make the following simulation project more modular. I want to separate the run simulation function from all the arguments and the other functions that load important infomration in. Could you help me refactor this code into a main.py (main entry point with arguments and other loading funcitons) and then simulation.py that is effectively the run simulation funciton? THis would greatly help my development by having modular files with smaller footprints.

I'll help you refactor this into two modular files. This will make the code much more maintainable and easier to work with.Perfect! I've successfully refactored your code into two modular files:

## 📁 **main.py** - Main Entry Point
- **Argument parsing** - All command-line argument definitions
- **Command handlers** - Separate functions for each command type:
  - `handle_benchmark_command()` - Benchmark operations
  - `handle_universe_commands()` - Universe management
  - `handle_diagnostic_commands()` - Diagnostic tools
  - `handle_validation_commands()` - Ticker validation
  - `handle_download_command()` - Data downloading
- **Strategy loading** - `load_strategies()` function
- **Symbol selection** - `select_symbols()` function
- **Main flow** - Clean, linear execution path

## 📁 **simulation.py** - Simulation Engine
- **Core simulation** - `run_simulation()` function with clear parameters
- **Data fetching** - `fetch_stock_data()` and `fetch_stock_data_parallel()`
- **Position management** - `check_and_liquidate_invalid_positions()`
- **All simulation logic** - Visualization, tracking, analysis buttons

## 🎯 Benefits of This Refactor

1. **Smaller footprints** - Each file has a single, clear purpose
2. **Easier development** - Work on simulation logic without command parsing clutter
3. **Better testing** - Can test simulation independently with mock parameters
4. **Cleaner imports** - Simulation module is now reusable
5. **Maintainability** - Changes to commands don't affect simulation logic

## 🚀 Usage

Nothing changes for end users:
```bash
python main.py --universe sp500
python main.py --download --tickers AAPL,GOOGL
python main.py --benchmark
```

The `main.py` handles all the command-line logic, then calls `run_simulation()` with the prepared data.

## 🔧 Key Changes

1. **Clear parameter passing** - `run_simulation()` now accepts explicit parameters instead of using global variables
2. **Separated concerns** - Commands in main.py, simulation logic in simulation.py
3. **Reusable functions** - Data fetching and simulation can be imported and used elsewhere
4. **Better organization** - Each function has a clear responsibility

The refactor maintains 100% of the original functionality while making the codebase much more modular and maintainable! 🎉


