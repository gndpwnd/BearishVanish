## Documentation

- need to make summaries of previous chats and patches.

## Reporting

- need to clean up reports
    - don't show all stocks used by the given strategy, make a separate button on analysis tab to view performnace of individual stocks
    - maybe make trade execution timeline graph its own button, so many stocks that the legend gets cluttered, maybe not do trade execution timeline at all for individual stocks, just overall portfolio trade volume - do i have this already?
    - still want some sort of history for stock trades, maybe make a separate button for "view trade history" that shows a table of all trades executed for that stock with date, buy/sell, price, quantity, total value, profit/loss. this could be added to the performance tab for each stock.
    - fix monthly and daily returns graphs...
    - maybe make "profit/loss by stock" a heatmap with averages so can more clearly see if more profits than losses, if so how many, etc...
    - maybe show s&p 500 charted with the "portfolio value over time" chart for a quick comparison...

- then also fix these errors:

❌ Error generating markdown: 'StrategyTracker' object has no attribute 'get_portfolio_beta'

❌ Error saving report: 'StrategyTracker' object has no attribute 'get_portfolio_beta'


## Strategies

- maybe a new strategy: staying ahead of the index
    - sp500 intersection -> russel 3000 intersection, try to skim the tops of the indexes?
- need to figure out why weekly threshold strategy is so low compared to s&p - need more stocks?
- need to find more strategies to test - maybe find indicator books? but then this is not trading based on an overall theme like "the system is rigged, so overall it should go up", is automating predicting indicators worth it?
- try to figure out how to minimize losses in current strategies while maximizing profits


## General Errors and Bugs