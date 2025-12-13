ok, here are the files for the actual strategies i am using, why are the losses so large and the wins so small? Here are the notes, i want the pure strategies not mixed up with other ideas for risk management, this is what the simulaiton is for, to test raw strategies that are exactly what i want to test, do i need to refactor the strategies to better match exactly what i want?







strategy #1 - buying and selling based on slope reversal after crossing the S&P 500

basically find when the slope of the cumulative return percentage of the stock reverse direction

if it starts going up and it previously cross the s&P 500 while the slope of the cumulative return percentage of the stock was negative, then buy

if it starts going down and it previously cross the s&P 500 while the slope of the cumulative return percentage of the stock was positive, then sell

and then only buy once until it crosses the s&P again, and then only sell once until it crosses the s&p again

i don't want just one buy and one sell total, i want one buy charted per cross as in the first buy after it dips below the s&P and then one sell charted per cross as in the first sell after it climbs across the s&p

you cannot buy if the stock is above the s&p500 and you cannot sell if the stock is below the s&p500

make sure to only have one buy while below the s&p500 and one sell while above the s&p500

make sure to have a buy signal before the next sell signal and a sell signal before the next buy signal



strategy #2 - buying and selling based on percentage increase and decrease over week.

if the stock goes down 5% in a week monday to monday, buy $5
if the stock goes up 10% in a week monday to monday, sell $10
if the stock goes down 5% in a month 1st to 1st, buy $5
if the stock goes up 10% in a month 1st to 1st, sell $10

I want the week long signals to be tied together, for example don't make a sell-weeek signal if there is no buy-week signal right before it

now i want to have streaming data handling, instead of hard-coded monday to monday and 15-15, simply take the past 7 days, the past 15 day, and the past 30 days


strategy #3 - buying and selling based on percentange increase and decresase over a month

for example don't make a sell-month signal if there is no buy-month signal right before it





please also make documentation for how to create strategies to use the full suite of available data from the simulation, and please help improve the simulation to make as much data available to the strategies as possible, without allowing seeing the future... basically, the strategies should be able to ask for whatever they want, as long as data is not from the futrue from the current iteration in the simulaiton. please also improve my risk analysis module and make sure it is properly integrated into the simulation and strategy testing and analysis framework, i want to perform risk analysis just like how large banks, hedge funds, and trading firms do it, and i want to be able to see the risk metrics for each strategy tested, as well as for the overall portfolio of all strategies combined. I want to focus on improving my simulation and analysis framework to be as good as possible, then i can then focus on creating and testing strategies that work well within that framework. I have also uploaded my current code and some work history for more context.