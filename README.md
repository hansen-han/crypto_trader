# crypto_trader
This repository contains a cryptocurrency trading system that uses the Coinbase exchange to execute trades. The system consists of two main components: a data scraping script and trading algorithms.

The data scraping script is written in Python and uses the Coinbase API to collect price data for a specified cryptocurrency. The script then stores the collected data in an SQLite database for later use by the trading algorithms.

The the two trading algorithms are a mean reversion script and a trend following script that read the price data from the SQLite database and uses this information to execute trades on the Coinbase exchange. Either or both can be used depending on the desired trading approach.

## Getting Started
To get started with the trading system, you will need to set up an account on the Coinbase exchange and obtain API credentials. API credentials need to be stored in the repository using the ```encode_coinbase_api_keys.py``` script. You will also need to install the necessary Python libraries, such as the ccxt library.


## Usage

### **1. Edit and run ```encode_coinbase_api_keys.py``` to encode coinbase API keys for scraping and trading**  


### **2. Configure settings in ```config.txt```**  

```scraper_script```: Specifies the state of the scraper script. Set to "run" to enable the scraper script, and set to any other value to terminate the script.

```scrape```: Specifies the state of the data scraping. Set to "run" to enable the data scraping, and set to any other value to pause scraping. The scraping script will continue running, but will not collect and store data until it is set back to "run"

```scraper_frequency```: Specifies the frequency of data scraping in minutes.

```total_invested```: Specifies the total amount invested in the cryptocurrency trading. This value should be updated whenever funds are added or withdrawn from the coinbase account to keep an accurate report of losses and gains in the logs.

```trader_script```: Specifies the state of the trading script. Set to "run" to enable the trading script, and set to any other value to terminate the script.

```trade```: Specifies the state of trading. Set to "run" to enable trading, and set to any other value to pause trading. The trading script will continue running, but will not execute trades until it is set back to "run".

### **3. Start scraper to collect price data**  
Must be started before running either trading bot to gather price data to calculate moving averages. 

- ```coin``` (str): the coin to be collect data on. Defaults to "BTC".

``` 
python3 coinbase_scraper.py BTC
```

### **4a. Run mean reversion trading bot**  
Bot that automatically buys and sells cryptocurrencies based on the principle of mean reversion. This strategy assumes that prices will eventually revert back to their average and seeks to profit from this tendency. The bot monitors the market data, calculates the mean (average) price, and uses this information to make trades. If the price of a cryptocurrency is below its average, the bot buys the coin, and if the price is above the average, it sells the coin. The goal is to buy low and sell high and generate profits over time by exploiting the mean-reverting behavior of the market.

- ```rolling_window``` (int): the length of the moving average window, in minutes
- ```buy_threshold ```(float): the threshold for buying a coin, a value between 0 and 1 (for example, a 3% threshold is represented by 0.97)
- ```sell_threshold ```(float): the threshold for selling a coin to take profit, a value between 0 and 1 (for example, a 3% threshold is represented by 1.03)
- ```stop_loss``` (float): the threshold for selling a coin to stop losses, a value between 0 and 1 (for example, a 10% stop loss is represented by 0.9)
- ```buy_size ```(float): the amount of available capital to use per trade, a value between 0 and 1
- ```coin``` (str, optional): the coin to be traded. Defaults to "BTC".
``` 
python3 mean_reversion_trader.py 6000 0.97 1.03 0.9 1 BTC
```

### **4b. Run SMA Crossover trading bot**  
Bot that executes trades based on the crossover of two moving averages of the price of a cryptocurrency. The two moving averages are typically referred to as the "short" and "long" moving averages. The bot monitors the market data and calculates the moving averages of the price. If the short moving average crosses above the long moving average, it signals a potential buy opportunity and the bot buys the coin. Conversely, if the short moving average crosses below the long moving average, it signals a potential sell opportunity and the bot sells the coin. The crossover of the two moving averages is a popular technical analysis indicator used by traders to identify potential buy and sell signals. By implementing this strategy, the bot aims to take advantage of the trend changes in the market and generate profits over time.

- ```intervals```: Specifies how often the function should check for new data in seconds.
- ```rolling_window_1```: Specifies the length of the long moving average in minutes.
- ```rolling_window_2```: Specifies the length of the short moving average in minutes.
- ```buy_size```: Specifies the amount of available capital to use per trade, given as a fraction between 0 and 1.
- ```coin```:  Specifies the coin to be traded. The default value is "BTC".

``` 
python3 sma_crossover_trader.py 600 480 2490 0.9 BTC
```

## Related Analysis

https://github.com/hansenrhan/backtesting/bitcoin

If you are interested in running these bots, you may want to check out this analysis I wrote to identify the optimal parameters for the bots. I used 1-minute Bitcoin data from 2014 to 2019 and applied both a simple moving average (SMA) crossover system and a mean reversion system to determine the performance of each strategy. The results of the analysis show that the highest cumulative return for each strategy was 3,929.8% for mean reversion and 5,569.8% for SMA crossover.

Please note that this analysis is a starting point for understanding the potential performance of these trading strategies and is not a guarantee of future results. 

## Disclaimer
It is important to note that cryptocurrency trading is inherently risky and that this system is provided for educational purposes only. It is up to the user to properly evaluate the risk and to use the system responsibly. The author of this repository assumes no liability for any losses incurred as a result of using this system.
