I want to maintain the core features of the program: 
 
* be able to download stock universes
   * able to configure stock universes, can download csv files and parse for stock universes
   * able to specify a list of stocks if want to make custom universes
   * able to specify how many days in history to download data (ex previous 180 days)
* download market data
   * download in parallel, and when rate limited perform trickle download 
   * store market data in local sqlite database so don't have to keep re-downloading for multiple simulations
   * before every simulation, check to make sure all necessary data exists, only download missing data
* execute simulations of stocks using historical market data
   * prevent look-ahead bias in strategies by performing iterations of data, simulating the real world where you can only access so much data at once and cannot see the future
* allow users to develop their own trading strategies in ./strategies
   * import all strategy files from ./strategies
   * run all available strategies on all stocks in specified universes for simulation
   * also able to specify how many days of history to run trading simulations (ex previous 180 days)
   * users should also be able to configure portfolio parameters like initial capital, how much each trade should be, whether or not to perform calculations on one stock and then calculations on another stock will be impacted, really make it open ended.
* allow users to develop their own indicators 
   * make sure to have timestamp, stock price, and volume for market data
   * indicators can be embedded in trading strategies, and then perform math and statistics on market data as specified. 
   * indicators can be created to be dependent on other indicators so users can build complex indicators for new statistical theory and mathematical models 
* overall every feature should be able to access as much data from other features as possible to really open everything up and encourage community develpment of trading strategies and indicators so that eventually there can be lots of files in ./indicators and lots of files in ./strategies
* i then want to employ computational optimzation techniques on my simulation engine so that simulations will automatically make the best use of the hardware available to it
   * i also want to optimize based on the strucutre that i want, i recognize that things might go faster if i don't make modular strategies and indicators, but this is a requirement to complete the project, i want to make the best project that meets the requirements
* store "telemetry" in a database every time the simulation is run
   * store universes used, strategies used, indicators used
   * store the portfolio parameters of strategies
   * store results of calculations from strategies, be able to see when buy and sell signals where made, etc... 
   * this way i can make a comprehensive analaysis app that will allow me to look at the performance of various strategeis and asses risk and other factors. does thsi make sense?

these are the features that are required of this simulation engine, if most of the simulation needs to be refactored due to code that would become legacy then so be it. please make sure to keep everything modular and make files have small footprints if possible. this is the ultimate goal for further development.