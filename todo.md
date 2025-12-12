- need to clean up reports
    - don't show all stocks used by strategy, make a separate button on analysis tab to view performnace of individual stocks
    - maybe make trade execution timeline graph its own button
    - fix monthly and daily returns graphs...
    - maybe make "profit/loss by stock" a heatmap with averages so can more clearly see if more profits than losses
    - maybe show s&p 500 charted with the "portfolio value over time" chart for a quick comparison...
- need to figure out why loading data is so slow, change to a different database? is the disk the limiting factor? are there not actually multiple workers running when checking if data exists?
- maybe a new strategy: staying ahead of the index
    - sp500 intersection -> russel 3000 intersection, try to skim the tops of the indexes?
- need to figure out why weekly threshold strategy is so low compared to s&p - need more stocks?

- need to make summaries of previous chats and patches.
- need to find more strategies to test - maybe find indicator books? but then this is not trading based on an overall theme like "the system is rigged, so overall it should go up", is automating predicting indicators worth it?

- don't think i need the automated testing script anymore... maybe a simple bash script for configuring number of days of history, making sure everything is downloaded, then testing with specific parameters
- need to make sure that simulation is able to configure amount of backtesting history and startup capital based on user input 

- just log errors or warnings to a logfile with a timestamp, tired of excessive terminal output, just have a counter that doesn't reprint to the terminal when increments for various things like the following:


⚠️  CCK: Partial data available
  ❌ CCK: No data returned                                                                    
Loading data:  19%|███████                              | 489/2570 [08:19<55:57,  1.61s/stock]❌ API error for CDE (attempt 3/3): {"message": "too many requests."}

⚠️  CDE: Partial data available
  ❌ CDE: No data returned                                                                    
Loading data:  20%|███████▎                             | 510/2570 [08:39<40:23,  1.18s/stock]❌ API error for CHH (attempt 3/3): {"message": "too many requests."}


would turn into "Number of Stocks Without Complete Data"