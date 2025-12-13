# Replace the argument parsing section in simulator.py with this:

# Get recommended workers from benchmark if available
default_download_workers = SystemBenchmark.get_recommended_workers()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Stock Strategy Simulator')

# Data management arguments
parser.add_argument('--cache-status', action='store_true', help='Show offline cache status')
parser.add_argument('--download', action='store_true', help='Download data for symbols')
parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers to download')
parser.add_argument('--offline', action='store_true', help='Run in offline mode')
parser.add_argument('--workers', type=int, default=default_download_workers,
                   help=f'Number of workers for API downloads (default: {default_download_workers} from benchmark)')

# Universe management arguments
parser.add_argument('--update-universe', type=str, help='Update universe: sp500, nasdaq100, russell3000, or all')
parser.add_argument('--universe', type=str, help='Run simulation with specific universe')
parser.add_argument('--universe-status', action='store_true', help='Show universe status')
parser.add_argument('--check-ticker', type=str, help='Check if a ticker is in any universe')
parser.add_argument('--clear-universe', type=str, help='Clear universe data')

# Diagnostic arguments
parser.add_argument('--diagnose', type=str, help='Diagnose mismatch for universe')
parser.add_argument('--check-quality', type=str, help='Check data quality for universe')
parser.add_argument('--find-duplicates', type=str, help='Find duplicate ticker issues')
parser.add_argument('--compare', nargs=2, help='Compare two universes')

# Validation arguments
parser.add_argument('--validate', type=str, help='Validate tickers for universe')
parser.add_argument('--cleanup-db', action='store_true', help='Clean up database')

# Benchmark arguments
parser.add_argument('--benchmark', action='store_true', help='Run network benchmark')
parser.add_argument('--show-benchmark', action='store_true', help='Show saved benchmark results')

# Strategy testing arguments
parser.add_argument('--force-liquidate', action='store_true', 
                   help='Force liquidation of all positions at end of simulation')
parser.add_argument('--no-universe-check', action='store_true',
                   help='Disable universe checking during simulation')

args = parser.parse_args()


# Then in the download section, change this line:
# FROM:
# print(f"🔧 Using {args.download_workers} parallel workers\n")
# TO:
print(f"🔧 Using {args.workers} parallel workers\n")

# And update the download call:
# FROM:
# with ThreadPoolExecutor(max_workers=args.download_workers) as executor:
# TO:
with ThreadPoolExecutor(max_workers=args.workers) as executor:


# Remove this line entirely (no longer needed):
# args.download_workers = args.workers
# args.db_workers = args.workers
















# Replace the fetch_stock_data_parallel function in simulator.py with this:

def fetch_stock_data_parallel(symbols, days=HISTORY):
    """
    🚀 OPTIMIZED: Fetch multiple stocks using batch loading
    This is 10-50x faster than loading symbols individually
    No workers needed - batch loading uses a single optimized query
    """
    
    print(f"\n📊 Loading {len(symbols)} symbols from database...")
    print(f"⚡ Using BATCH LOADING for maximum speed\n")
    
    start_time = time.time()
    
    # Calculate date range
    end_date = datetime.now().replace(tzinfo=None)
    start_date = (end_date - timedelta(days=days)).replace(tzinfo=None)
    
    # 🚀 OPTION 1: Load ALL symbols in ONE query (fastest for < 1000 symbols)
    if len(symbols) <= 1000:
        print(f"⚡ Loading all {len(symbols)} symbols in a single batch query...")
        stock_data_dict = data_manager.load_multiple_symbols_batch(
            symbols, 
            start_date, 
            end_date
        )
        
        loaded = len(stock_data_dict)
        missing = len(symbols) - loaded
        
        elapsed = time.time() - start_time
        print(f"\n✅ Loaded {loaded}/{len(symbols)} symbols in {elapsed:.2f}s")
        print(f"   Speed: {loaded/elapsed:.1f} symbols/second")
        
        if missing > 0:
            print(f"⚠️  {missing} symbols not found in cache")
        
        return stock_data_dict
    
    # 🚀 OPTION 2: Load in chunks (for > 1000 symbols)
    else:
        print(f"⚡ Loading {len(symbols)} symbols in chunks...")
        chunk_size = 250  # Load 250 symbols per query
        stock_data_dict = {}
        
        from tqdm import tqdm
        
        with tqdm(total=len(symbols), desc="Loading data", unit="stock") as pbar:
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i+chunk_size]
                
                # Load this chunk
                chunk_data = data_manager.load_multiple_symbols_batch(
                    chunk,
                    start_date,
                    end_date
                )
                
                stock_data_dict.update(chunk_data)
                pbar.update(len(chunk))
        
        loaded = len(stock_data_dict)
        missing = len(symbols) - loaded
        
        elapsed = time.time() - start_time
        print(f"\n✅ Loaded {loaded}/{len(symbols)} symbols in {elapsed:.2f}s")
        print(f"   Speed: {loaded/elapsed:.1f} symbols/second")
        
        if missing > 0:
            print(f"⚠️  {missing} symbols not found in cache")
        
        return stock_data_dict


# Also add this import at the top of simulator.py:
import time
from datetime import timedelta