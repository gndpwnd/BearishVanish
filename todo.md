- need to properly focus on selected stocks/universes in simulation
  - filter out stocks before running strategies
  - iterate through all strategies on all stocks for each iteration
  - try to minimize override liquidations


## Reporting

- need to make summaries of previous chats and patches.
- need to clean up reports
    - don't show all stocks used by strategy, make a separate button on analysis tab to view performnace of individual stocks
    - maybe make trade execution timeline graph its own button
    - fix monthly and daily returns graphs...
    - maybe make "profit/loss by stock" a heatmap with averages so can more clearly see if more profits than losses
    - maybe show s&p 500 charted with the "portfolio value over time" chart for a quick comparison...

## Strategies

- maybe a new strategy: staying ahead of the index
    - sp500 intersection -> russel 3000 intersection, try to skim the tops of the indexes?
- need to figure out why weekly threshold strategy is so low compared to s&p - need more stocks?
- need to find more strategies to test - maybe find indicator books? but then this is not trading based on an overall theme like "the system is rigged, so overall it should go up", is automating predicting indicators worth it?
- try to figure out how to minimize losses in current strategies while maximizing profits


## General Errors and Bugs



- need to cleanup strategy testing and only allow stocks from approved universe or selected list or universe. then iterate through all stocks on all iterations so that simulation does not flatline with so many override liquidations....


⚠️  OVERRIDE: BY not in approved universe
   → Forcing liquidation for Weekly Threshold
   → Sold 344.42 shares @ $25.73

⚠️  OVERRIDE: CDNS not in approved universe
   → Forcing liquidation for 500 Intersection
   → Sold 62.51 shares @ $327.29

⚠️  OVERRIDE: CEG not in approved universe
   → Forcing liquidation for Weekly Threshold
   → Sold 49.30 shares @ $357.30

⚠️  OVERRIDE: CADE not in approved universe
   → Forcing liquidation for 500 Intersection
   → Sold 572.20 shares @ $35.65



- then also fix these errors:

❌ Error generating markdown: 'StrategyTracker' object has no attribute 'get_portfolio_beta'

❌ Error saving report: 'StrategyTracker' object has no attribute 'get_portfolio_beta'
