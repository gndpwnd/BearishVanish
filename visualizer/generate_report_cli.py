#!/usr/bin/env python3
"""
Headless Report Generator CLI
Generates markdown reports from analysis databases without starting the web server
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add visualizer to path
sys.path.insert(0, str(Path(__file__).parent))

from config import discover_analysis_databases
from database.analysis_reader import AnalysisReader
from report_generator import MarkdownReportGenerator


def find_latest_analysis_db():
    """Find the most recent analysis database"""
    dbs = discover_analysis_databases()
    if not dbs:
        print("ERROR: No analysis databases found", file=sys.stderr)
        print("Expected location: ../analysis/analysis_dbs/", file=sys.stderr)
        return None

    # Sort by modification time (newest first)
    dbs_sorted = sorted(dbs, key=lambda p: p.stat().st_mtime, reverse=True)
    return dbs_sorted[0]


def generate_reports(db_path, output_dir, strategies=None, report_type='full'):
    """
    Generate reports for strategies in the analysis database

    Args:
        db_path: Path to analysis database
        output_dir: Directory to save reports
        strategies: List of strategy names (None = all strategies)
        report_type: Type of report (full, summary, performance, improvement)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using analysis database: {db_path}")
    print(f"Output directory: {output_dir}")
    print()

    # Create reader
    reader = AnalysisReader(str(db_path))

    # Get all strategies if not specified
    if not strategies:
        strategies = reader.list_strategies()
        if not strategies:
            print("ERROR: No strategies found in database", file=sys.stderr)
            return 1
        print(f"Found {len(strategies)} strategies")

    # Generate reports
    generator = MarkdownReportGenerator(reader)
    db_timestamp = generator.get_db_timestamp()

    generated_files = []

    for strategy_name in strategies:
        print(f"Generating {report_type} report for: {strategy_name}...")

        try:
            # Generate report based on type
            if report_type == 'summary':
                from io import StringIO
                report = StringIO()
                report.write(generator._generate_header(strategy_name))
                report.write(generator._generate_executive_summary(strategy_name))
                report.write(generator._generate_key_metrics(strategy_name))
                content = report.getvalue()
            elif report_type == 'performance':
                from io import StringIO
                report = StringIO()
                report.write(generator._generate_header(strategy_name))
                report.write(generator._generate_performance_analysis(strategy_name))
                report.write(generator._generate_risk_analysis(strategy_name))
                report.write(generator._generate_key_metrics(strategy_name))
                report.write(generator._generate_trade_analysis(strategy_name))
                content = report.getvalue()
            elif report_type == 'improvement':
                from io import StringIO
                report = StringIO()
                report.write(generator._generate_header(strategy_name))
                report.write(generator._generate_executive_summary(strategy_name))
                report.write(generator._generate_key_metrics(strategy_name))
                report.write(generator._generate_weaknesses_and_opportunities(strategy_name))
                report.write(generator._generate_recommendations(strategy_name))
                content = report.getvalue()
            else:  # full
                content = generator.generate_full_report(strategy_name)

            # Create filename
            safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_name}_{db_timestamp}.md"
            output_path = output_dir / filename

            # Write file
            output_path.write_text(content, encoding='utf-8')
            generated_files.append(output_path)

            print(f"  ✓ Saved: {output_path}")

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}", file=sys.stderr)
            continue

    print()
    print(f"Generated {len(generated_files)} report(s)")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate markdown reports from analysis databases (headless mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full reports for all strategies (using latest analysis)
  %(prog)s --output ../docs/reports

  # Generate reports from specific database
  %(prog)s --database ../analysis/analysis_dbs/analysis_20241228_123456.db --output ../docs/reports

  # Generate only summary reports
  %(prog)s --output ../docs/reports --type summary

  # Generate reports for specific strategies
  %(prog)s --output ../docs/reports --strategies "Conservative Income" "Momentum Example"

  # Generate improvement-focused reports (for LLM review)
  %(prog)s --output ../docs/reports --type improvement
        """
    )

    parser.add_argument(
        '--database', '-d',
        type=Path,
        help='Path to analysis database (default: latest in ../analysis/analysis_dbs/)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        required=True,
        help='Output directory for generated reports'
    )

    parser.add_argument(
        '--strategies', '-s',
        nargs='+',
        help='Strategy names to generate reports for (default: all strategies)'
    )

    parser.add_argument(
        '--type', '-t',
        choices=['full', 'summary', 'performance', 'improvement'],
        default='full',
        help='Type of report to generate (default: full)'
    )

    args = parser.parse_args()

    # Find database
    if args.database:
        db_path = args.database
        if not db_path.exists():
            print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
            return 1
    else:
        db_path = find_latest_analysis_db()
        if not db_path:
            return 1

    # Generate reports
    return generate_reports(db_path, args.output, args.strategies, args.type)


if __name__ == '__main__':
    sys.exit(main())
