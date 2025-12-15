
# ============================================================================
# FILE 3: visualizer/main.py
# ============================================================================

"""
Visualizer Entry Point
"""

import argparse
from pathlib import Path
from browser import AnalysisBrowser
from dashboard import StrategyDashboard


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Analysis Visualizer')
    parser.add_argument('--db', type=str, help='Path to analysis database')
    parser.add_argument('--latest', action='store_true', help='Open latest analysis')
    
    args = parser.parse_args()
    
    if args.db:
        # Open specific database
        db_path = Path(args.db)
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return
        
        dashboard = StrategyDashboard(db_path)
        dashboard.run()
    
    elif args.latest:
        # Find latest
        analysis_dir = Path('../analysis/analysis_dbs')
        if not analysis_dir.exists():
            print(f"❌ Analysis directory not found: {analysis_dir}")
            return
        
        db_files = list(analysis_dir.glob('analysis_*.db'))
        if not db_files:
            print("❌ No analysis databases found")
            return
        
        latest = sorted(db_files, reverse=True)[0]
        print(f"📊 Opening latest: {latest.name}")
        
        dashboard = StrategyDashboard(latest)
        dashboard.run()
    
    else:
        # Open browser
        browser = AnalysisBrowser()
        browser.run()


if __name__ == '__main__':
    main()