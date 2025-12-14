"""
Analysis Application - Entry Point
Lightweight main file that orchestrates everything
"""

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from db_reader import SimulationReader
from dashboard import show_strategy_dashboard
from browser import SimulationBrowser

SIMULATIONS_DIR = Path('../simulator/simulations')


def main():
    """Main entry point for analysis app"""
    parser = argparse.ArgumentParser(description='Simulation Analysis Tool')
    parser.add_argument('--sim', type=str, help='Path to specific simulation database')
    parser.add_argument('--latest', action='store_true', help='Analyze most recent simulation')
    parser.add_argument('--list', action='store_true', help='List all simulations')
    
    args = parser.parse_args()
    
    # List simulations
    if args.list:
        print(f"\n{'='*70}")
        print(f"SIMULATIONS IN: {SIMULATIONS_DIR}")
        print(f"{'='*70}\n")
        
        if not SIMULATIONS_DIR.exists():
            print(f"❌ Directory not found: {SIMULATIONS_DIR}")
            return
        
        db_files = list(SIMULATIONS_DIR.glob('simulation_*.db'))
        
        if not db_files:
            print("❌ No simulation databases found")
            return
        
        for db_path in sorted(db_files, reverse=True):
            print(f"📁 {db_path.name}")
            try:
                reader = SimulationReader(db_path)
                strategies = reader.list_strategies()
                print(f"   Strategies: {', '.join(strategies)}")
                reader.close()
            except Exception as e:
                print(f"   Error: {e}")
        
        print(f"\nTotal: {len(db_files)} simulations")
        return
    
    # Analyze specific simulation
    if args.sim:
        db_path = Path(args.sim)
        if not db_path.exists():
            print(f"❌ Database not found: {db_path}")
            return
        
        reader = SimulationReader(db_path)
        strategies = reader.list_strategies()
        
        if not strategies:
            print(f"❌ No strategies found in {db_path.name}")
            return
        
        print(f"\n📊 Simulation: {db_path.name}")
        print(f"Strategies: {', '.join(strategies)}")
        
        # Open browser for strategy selection
        browser = tk.Tk()
        browser.title("Strategy Selection")
        browser.geometry("600x400")
        
        tk.Label(browser, text=f"Select Strategy to Analyze", 
                font=('Arial', 14, 'bold')).pack(pady=20)
        
        for strat in strategies:
            def open_strategy(s=strat):
                browser.destroy()
                show_strategy_dashboard(reader, s, all_strategies=strategies)
            
            tk.Button(browser, text=strat, command=open_strategy,
                     font=('Arial', 11), bg='#4CAF50', fg='white',
                     padx=20, pady=10).pack(pady=5)
        
        tk.Button(browser, text="❌ Cancel", command=browser.destroy,
                 font=('Arial', 11), bg='#F44336', fg='white',
                 padx=20, pady=10).pack(pady=20)
        
        browser.mainloop()
        return
    
    # Analyze latest simulation
    if args.latest:
        if not SIMULATIONS_DIR.exists():
            print(f"❌ Simulations directory not found: {SIMULATIONS_DIR}")
            return
        
        db_files = list(SIMULATIONS_DIR.glob('simulation_*.db'))
        
        if not db_files:
            print(f"❌ No simulation databases found in {SIMULATIONS_DIR}")
            return
        
        latest_db = sorted(db_files, reverse=True)[0]
        reader = SimulationReader(latest_db)
        strategies = reader.list_strategies()
        
        if not strategies:
            print(f"❌ No strategies found in {latest_db.name}")
            return
        
        print(f"\n📊 Latest simulation: {latest_db.name}")
        print(f"Strategies: {', '.join(strategies)}")
        
        # Open first strategy automatically
        if strategies:
            show_strategy_dashboard(reader, strategies[0], all_strategies=strategies)
        return
    
    # Default: Open browser
    browser = SimulationBrowser()
    browser.run()


if __name__ == "__main__":
    main()