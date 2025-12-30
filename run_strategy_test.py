#!/usr/bin/env python3
"""
Automated Strategy Testing Pipeline
Runs complete simulation -> analysis -> report generation workflow
Organizes all outputs in timestamped folders with comprehensive documentation

Usage:
    python run_strategy_test.py                    # Use cached data from offline_data/stock_data.db
    python run_strategy_test.py --universe sp500   # Specific universe
    python run_strategy_test.py --workers 48       # HPC with 48 workers
"""

import argparse
import subprocess
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Project paths
PROJECT_ROOT = Path(__file__).parent
SIMULATOR_DIR = PROJECT_ROOT / "simulator"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
VISUALIZER_DIR = PROJECT_ROOT / "visualizer"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_BASE_DIR = DOCS_DIR / "reports"


def get_timestamp() -> str:
    """Get formatted timestamp for folder naming"""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def run_command(cmd: List[str], cwd: Path, description: str) -> tuple[bool, str]:
    """
    Run a command and capture output

    Returns:
        (success: bool, output: str)
    """
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Directory: {cwd}")
    print()

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        success = result.returncode == 0
        output = result.stdout + result.stderr

        if success:
            print(f"  SUCCESS")
        else:
            print(f"  FAILED (return code: {result.returncode})")

        return success, output

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after 1 hour")
        return False, "Timeout"
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False, str(e)


def run_simulation(universe: str = "test", workers: int = 4, offline: bool = True) -> Optional[Path]:
    """
    Run trading simulation

    Returns:
        Path to simulation database if successful, None otherwise
    """
    cmd = [
        sys.executable, "main.py",
        "--universe", universe,
        "--sim-workers", str(workers)
    ]

    if offline:
        cmd.append("--offline")

    success, output = run_command(cmd, SIMULATOR_DIR, "Running Trading Simulation")

    if not success:
        return None

    # Find the created simulation database
    sim_dir = SIMULATOR_DIR / "simulations"
    if sim_dir.exists():
        dbs = sorted(sim_dir.glob("simulation_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dbs:
            print(f"  Simulation database: {dbs[0]}")
            return dbs[0]

    return None


def run_analysis(sim_db: Path = None) -> Optional[Path]:
    """
    Run analysis on simulation results

    Returns:
        Path to analysis database if successful, None otherwise
    """
    cmd = [sys.executable, "analysis_engine.py"]

    if sim_db:
        cmd.extend(["--sim", str(sim_db)])
    else:
        cmd.append("--latest")

    success, output = run_command(cmd, ANALYSIS_DIR, "Running Analysis Engine")

    if not success:
        return None

    # Find the created analysis database
    analysis_db_dir = ANALYSIS_DIR / "analysis_dbs"
    if analysis_db_dir.exists():
        dbs = sorted(analysis_db_dir.glob("analysis_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dbs:
            print(f"  Analysis database: {dbs[0]}")
            return dbs[0]

    return None


def generate_reports(analysis_db: Path, output_dir: Path, report_type: str = "full") -> List[Path]:
    """
    Generate strategy reports using visualizer

    Returns:
        List of generated report paths
    """
    cmd = [
        sys.executable, "generate_report_cli.py",
        "--database", str(analysis_db),
        "--output", str(output_dir),
        "--type", report_type
    ]

    success, output = run_command(cmd, VISUALIZER_DIR, f"Generating {report_type.title()} Reports")

    if not success:
        return []

    # Return list of generated files
    reports = list(output_dir.glob("*.md"))
    return reports


def get_strategy_changes_summary() -> str:
    """Generate a summary of recent strategy changes"""
    summary = """# Strategy Changes Summary

## Recent Modifications

### Stop-Loss Protection Added

The following strategies now have fixed percentage stop-losses:

| Strategy | Stop-Loss % | Description |
|----------|-------------|-------------|
| AMIS (Advanced Multi-Indicator) | 7% | Multi-signal confirmation strategy |
| 500 Intersection | 7% | S&P 500 relative performance |
| Monthly Rolling | 8% | 30-day rolling return strategy |
| Momentum MFI | 7% | MFI + volume confirmation |
| WAM (Weekly Threshold) | 6% | Weekly return reversal |
| Trend Following | 8% | ADX + Supertrend confirmation |
| Rolling Windows | 6% | 7-day rolling return |
| SP500 Slope v2 | 7% | Slope reversal relative to SPY |
| Momentum Example | 7% | Golden/Death cross with RSI |
| Breakout | ATR-based | Dynamic stop at breakout - 2xATR |
| Mean Reversion | Pre-existing | Already had stop-loss |
| Conservative Income | Pre-existing | Already had stop-loss |

### New Indicators Added

1. **ATR (Average True Range)** - `simulator/indicators/indicator_atr.py`
   - Volatility measurement for position sizing
   - Helper methods: `get_stop_loss()`, `get_position_size()`
   - Numba JIT optimized

2. **ADX (Average Directional Index)** - `simulator/indicators/indicator_adx.py`
   - Trend strength measurement (0-100 scale)
   - Multi-value return: ADX, +DI, -DI
   - Helper methods: `is_trending()`, `get_trend_direction()`, `get_trend_strength()`

### Monitoring Integration

- Analysis engine now reports progress to monitoring API
- Real-time visibility into analysis steps
- Silent failover if monitoring unavailable

"""
    return summary


def create_test_summary(
    test_dir: Path,
    sim_db: Optional[Path],
    analysis_db: Optional[Path],
    reports: List[Path],
    duration_seconds: float,
    success: bool
) -> Path:
    """Create a summary markdown file for the test run"""

    summary_path = test_dir / "TEST_SUMMARY.md"
    timestamp = datetime.now()

    content = f"""# Strategy Test Summary

**Test Run ID:** {test_dir.name}
**Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration_seconds:.1f} seconds
**Status:** {'SUCCESS' if success else 'FAILED'}

---

## Test Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Simulation DB | {sim_db.name if sim_db else 'N/A'} | {'Created' if sim_db and sim_db.exists() else 'Missing'} |
| Analysis DB | {analysis_db.name if analysis_db else 'N/A'} | {'Created' if analysis_db and analysis_db.exists() else 'Missing'} |
| Reports Generated | {len(reports)} | {'Success' if reports else 'Failed'} |

---

## Generated Reports

"""

    if reports:
        for report in sorted(reports):
            content += f"- [{report.name}]({report.name})\n"
    else:
        content += "*No reports generated*\n"

    content += "\n---\n\n"
    content += get_strategy_changes_summary()

    content += f"""
---

## Pipeline Steps

1. **Simulation** - {'Completed' if sim_db else 'Failed'}
2. **Analysis** - {'Completed' if analysis_db else 'Failed'}
3. **Report Generation** - {'Completed' if reports else 'Failed'}

## How to Review

1. Read the strategy reports in this folder
2. Each report contains:
   - Executive summary with key metrics
   - Win rate, profit factor, Sharpe ratio analysis
   - Weaknesses and improvement suggestions
   - Recommendations for LLM review

3. Send reports to Claude or GPT-4 for deeper analysis:
   ```
   Here's my trading strategy report:
   [PASTE REPORT CONTENT]

   Please analyze and suggest improvements.
   ```

---

*Generated by BearishVanish Strategy Testing Pipeline*
"""

    summary_path.write_text(content, encoding='utf-8')
    print(f"  Created test summary: {summary_path}")

    return summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Automated Strategy Testing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test with cached data
  python run_strategy_test.py

  # HPC test with 48 workers
  python run_strategy_test.py --workers 48 --universe sp500

  # Generate only summary reports (faster)
  python run_strategy_test.py --report-type summary
        """
    )

    parser.add_argument(
        '--universe', '-u', default='test',
        help='Stock universe to test (default: test)'
    )
    parser.add_argument(
        '--workers', '-w', type=int, default=4,
        help='Number of simulation workers (default: 4)'
    )
    parser.add_argument(
        '--report-type', '-t',
        choices=['full', 'summary', 'performance', 'improvement'],
        default='full',
        help='Type of reports to generate (default: full)'
    )
    parser.add_argument(
        '--skip-simulation', action='store_true',
        help='Skip simulation, use latest existing database'
    )
    parser.add_argument(
        '--skip-analysis', action='store_true',
        help='Skip analysis, use latest existing database'
    )

    args = parser.parse_args()

    start_time = datetime.now()

    print("\n" + "="*60)
    print("  BEARISHVANISH STRATEGY TESTING PIPELINE")
    print("="*60)
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Universe: {args.universe}")
    print(f"  Workers: {args.workers}")
    print(f"  Report Type: {args.report_type}")

    # Create timestamped output directory
    test_timestamp = get_timestamp()
    test_dir = REPORTS_BASE_DIR / f"test_{test_timestamp}"
    test_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Output: {test_dir}")

    sim_db = None
    analysis_db = None
    reports = []
    success = True

    try:
        # Step 1: Run simulation
        if not args.skip_simulation and success:
            sim_db = run_simulation(
                universe=args.universe,
                workers=args.workers,
                offline=True
            )
            if not sim_db:
                print("\nERROR: Simulation failed")
                success = False
        elif args.skip_simulation:
            # Find latest simulation database
            sim_dir = SIMULATOR_DIR / "simulations"
            if sim_dir.exists():
                dbs = sorted(sim_dir.glob("simulation_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
                if dbs:
                    sim_db = dbs[0]
                    print(f"\nUsing existing simulation: {sim_db}")

        # Step 2: Run analysis
        if not args.skip_analysis and success:
            analysis_db = run_analysis(sim_db)
            if not analysis_db:
                print("\nERROR: Analysis failed")
                success = False
        elif args.skip_analysis:
            # Find latest analysis database
            analysis_db_dir = ANALYSIS_DIR / "analysis_dbs"
            if analysis_db_dir.exists():
                dbs = sorted(analysis_db_dir.glob("analysis_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
                if dbs:
                    analysis_db = dbs[0]
                    print(f"\nUsing existing analysis: {analysis_db}")

        # Step 3: Generate reports
        if analysis_db and success:
            reports = generate_reports(analysis_db, test_dir, args.report_type)
            if not reports:
                print("\nWARNING: No reports generated")

    except Exception as e:
        print(f"\nFATAL ERROR: {str(e)}")
        success = False

    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Create test summary
    create_test_summary(test_dir, sim_db, analysis_db, reports, duration, success)

    # Final summary
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print("="*60)
    print(f"  Status: {'SUCCESS' if success else 'FAILED'}")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Reports: {len(reports)} generated")
    print(f"  Output: {test_dir}")
    print()

    if reports:
        print("  Generated Reports:")
        for report in sorted(reports):
            print(f"    - {report.name}")

    print()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
