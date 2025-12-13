I have the following project that needs to download alot of stock market data to backtest various trading strategies, but i don't want to get rate limited. I want to introduce the method of "trickle downloading" when needing to download lots of data from lots of stocks. for example:



```markdown

⚠️  CCK: Partial data available
  ❌ CCK: No data returned                                                                    
Loading data:  19%|███████                              | 489/2570 [08:19<55:57,  1.61s/stock]❌ API error for CDE (attempt 3/3): {"message": "too many requests."}

⚠️  CDE: Partial data available
  ❌ CDE: No data returned                                                                    
Loading data:  20%|███████▎                             | 510/2570 [08:39<40:23,  1.18s/stock]❌ API error for CHH (attempt 3/3): {"message": "too many requests."}



```



I basically want to turn the universe downloading into a hybrid model, keep the normal funcitonality but when run into a "too many requests." then switch to trickle downloading. also i want to be able to run the universe or data management script, whichever one downloads all the stock data or tells the program to download all the stock data to be run independently so i can run the downloader in the background and not have to run a simulation. does this make sense? Please help me implement both the hybrid download model and the independent download features so i can get the proper amount of data that i want from the API without being rate limited... does this make sense? please let me know if you need more context... I uploaded most of the code in my program, enough for you to understand how you need to implement trickle downloading...