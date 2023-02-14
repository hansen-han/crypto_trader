import sqlite3
from datetime import datetime
from datetime import timedelta
import logging
import time
import ccxt
import math
import sys
import configparser
import ast


#set up logging
log_format = (
    '[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')

logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    filename=('coinbase_trader.log'),
)

def live_trader(
        rolling_window,
        buy_threshold,
        sell_threshold,
        stop_loss,
        buy_size,
        coin = "BTC"
):
    '''
    This function implements a basic trade strategy based on a moving average and thresholds for buying, selling and stop loss.

    Parameters:
        rolling_window (int): the length of the moving average window, in minutes
        buy_threshold (float): the threshold for buying a coin, a value between 0 and 1 (for example, a 3% threshold is represented by 0.97)
        sell_threshold (float): the threshold for selling a coin to take profit, a value between 0 and 1 (for example, a 3% threshold is represented by 1.03)
        stop_loss (float): the threshold for selling a coin to stop losses, a value between 0 and 1 (for example, a 10% stop loss is represented by 0.9)
        buy_size (float): the amount of available capital to use per trade, a value between 0 and 1
        coin (str, optional): the coin to be traded. Defaults to "BTC".
    '''
    logging.debug("Initializing live trading algorithm")

    # check if the trading parameters are valid
    if buy_size > 1 or buy_size <= 0:
        return "ERROR: could not run live_trader(), buy_size must be between 1 and 0."

    #define variables - use these for the actual running, store them in the database for logging, not use. 
    position_size = 0
    portfolio_balance = []
    purchase_price = 0
    losses = 0
    gains = 0
    buys = 0
    order_pending = False 
    order_wait_time = 0 #if waiting for an order to fill - the time since placing order
    last_order_id = "" #holding variable for the order id (for cancelling)
    sufficient_data = False

    format = "%d/%m/%Y %H:%M:%S"
    timediff = timedelta(minutes=rolling_window)
    logging.debug("Set environmental parameters")

    #establish connection with local db
    conn = sqlite3.connect("pricedata.db")
    c = conn.cursor()
    logging.debug("Established connection with local database")

    #load authentication information
    with open("cb_file1.bin", encoding="utf-8") as binary_file:
        key = binary_file.read()
    with open("cb_file2.bin", encoding="utf-8") as binary_file:
        secret = binary_file.read()
    with open("cb_file3.bin", encoding="utf-8") as binary_file:
        password = binary_file.read()

    #establish exchange connection
    coinbasepro = ccxt.coinbasepro({
        'apiKey': key,
        'secret': secret,
        'password': password
    })

    logging.debug("Established connection with exchange (CoinbasePro)")
    print("")
    print("Intializing live algorithm...")
    
    script_status = "run"
    while script_status == "run":

        #Get Master Parameters
        config = configparser.ConfigParser()
        config.read_file(open("coinbase_parameters.txt"))
        starting_capital = config.get('Mean Reversion Trader Section', 'total_invested') #corrects relevant variables based on new funding
        trade_status = config.get('Mean Reversion Trader Section', 'trade') #controls whether to trade this cycle
        script_status = config.get('Mean Reversion Trader Section', 'trader_script') #controls whether to shut the script down
        intervals = scraper_frequency = ast.literal_eval(config.get("Scraper Section", "scraper_frequency")) #how often the scraper collects data (in minutes)

        if trade_status == "run":

            #Check if there is sufficient data to generate trade signals
            timethreshold = datetime.now() - timediff
            #check if there is enough data to calculate the full moving average (6000 minutes, 600 total given that data is collected every 10 minutes by the scraper)
            if len([x for x in c.execute("SELECT * FROM price_data")]) < (rolling_window/scraper_frequency - 1):
                logging.debug("Insufficient Data: Still Collecting")
                print("Insufficient Data: Still Collecting")
            else:
                #pull data from the set interval
                intervaldata = [list(x) for x in c.execute("SELECT * FROM price_data") if datetime.strptime(list(x)[0], format) >= timethreshold ]
                
                #quality check - make sure that there is at least 65% of the points necessary to calculate the average (n=390)
                if len(intervaldata) > rolling_window/scraper_frequency*0.65:
                    try:
                        interval_average = sum([x[3] for x in intervaldata])/len(intervaldata)
                        print("Moving Average:", interval_average)
                        logging.debug("Moving Average:" + str(interval_average))
                        sufficient_data = True
                    except Exception as e:
                        logging.error("Encountered unkown error while calculating interval average" + str(e))
                        print("Encountered unknown error while calculating interval average" + str(e))
                else:
                    print("Insufficient Data: Missing Data")
                    logging.debug("Insufficient Data: Missing Data")
            if sufficient_data == True:
                #--- trade logic --- 
                #get breakdown of relevant balances for trading
                try:
                    exchange_balance = coinbasepro.fetch_balance()
                    available_position_size = exchange_balance['free'][coin]
                    used_position_size = exchange_balance['used'][coin]
                    total_position_size = exchange_balance['total'][coin]

                    available_fiat = exchange_balance['free']["USD"]
                    used_fiat = exchange_balance['used']["USD"]
                    total_fiat = exchange_balance['total']["USD"]

                except ccxt.NetworkError as e:
                    print( 'fetch_balance failed due to a network error:', str(e))
                    logging.error( 'fetch_balance failed due to a network error:', str(e))
                except ccxt.ExchangeError as e:
                    print( 'fetch_balance failed due to exchange error:', str(e))
                    logging.error( 'fetch_balance failed due to exchange error:', str(e))
                except Exception as e:
                    print( 'fetch_balance failed with:', str(e))
                    logging.error( 'fetch_balance failed with:', str(e))

                
                #Logic for if an order was placed last run
                if order_pending == True:

                    #keep track of how long it has been since the order was placed
                    order_wait_time = order_wait_time + 10

                    #if the order has been filled, reset and log the performance
                    if used_position_size == 0 and used_fiat == 0:
                        print("Order Filled:", order_pending_type, last_order_id)
                        logging.info("Order Filled:", order_pending_type, last_order_id)
                        order_pending = False
                        last_order_id = ""

                        #Record outcome data
                        if order_pending_type == "BUY":
                            buys = buys + 1
                        elif order_pending_type == "WIN":
                            gains = gains + 1
                            position_size = 0
                            purchase_price = 0
                        elif order_pending_type == "LOSS":
                            losses = losses + 1
                            position_size = 0
                            purchase_price = 0

                        order_pending_type = ""

                    #if it has been more than 20 minutes, cancel the orders so the algorithm can adjust the price
                    elif order_wait_time >= 30:
                        #cancel the orders
                        try:
                            coinbasepro.cancel_order(last_order_id, "{coin}/USD".format(coin = coin))
                            order_pending = False
                            print("Cancelled last order after 30 minutes")
                            logging.info("Cancelled last order after 30 minutes")
                            
                        except ccxt.NetworkError as e:
                            print( 'cancel_order failed due to a network error:', str(e))
                            logging.error( 'cancel_order failed due to a network error:', str(e))
                        except ccxt.ExchangeError as e:
                            print( 'cancel_order failed due to exchange error:', str(e))
                            logging.error( 'cancel_order failed due to exchange error:', str(e))
                        except Exception as e:
                            print( 'cancel_order failed with:', str(e))
                            logging.error( 'cancel_order failed with:', str(e))
                
                #--- signal generation and trading mechanisms ---
                if order_pending == False:

                    #--- Generate Data for Decision Making ---
                    try: 
                        ticker_data = coinbasepro.fetch_ticker("{coin}/USD".format(coin = coin))
                        logging.info("Downloaded ticker data from Coinbase Pro")
                        collected_data = True

                    except ccxt.NetworkError as e:
                        print('fetch_ticker failed due to a network error:', str(e))
                        logging.error('fetch_ticker failed due to a network error:', str(e))
                        try:
                            logging.info("Retrying...")
                            print("Retrying...")
                            ticker_data = coinbasepro.fetch_ticker("{coin}/USD".format(coin = coin))
                            logging.info("Downloaded ticker data from Coinbase Pro")
                            collected_data = True
                        except: 
                            logging.error("Attempt failed")
                            try:
                                logging.info("Retrying...")
                                print("Retrying...")
                                ticker_data = coinbasepro.fetch_ticker("{coin}/USD".format(coin = coin))
                                logging.info("Downloaded ticker data from Coinbase Pro")
                                collected_data = True
                            except:
                                collected_data = False

                    except ccxt.ExchangeError as e:
                        print('fetch_ticker failed due to exchange error:', str(e))
                        logging.error( 'fetch_ticker failed due to exchange error:', str(e))
                        try:
                            logging.info("Retrying...")
                            print("Retrying...")
                            ticker_data = coinbasepro.fetch_ticker("{coin}/USD".format(coin = coin))
                            logging.info("Downloaded ticker data from Coinbase Pro")
                            collected_data = True
                        except: 
                            logging.error("Attempt failed")
                            try:
                                logging.info("Retrying...")
                                print("Retrying...")
                                ticker_data = coinbasepro.fetch_ticker("{coin}/USD".format(coin = coin))
                                logging.info("Downloaded ticker data from Coinbase Pro")
                                collected_data = True
                            except:
                                collected_data = False
                    
                    if collected_data == True:
                        best_ask = ticker_data['ask']
                        best_bid = ticker_data['bid']
                        market_price = (best_ask + best_bid)/2

                        #Buy Signals
                        if total_position_size < 0.002:
                            if best_ask <= interval_average*buy_threshold:
                                #calculate how much to buy
                                buy_volume = math.trunc(((available_fiat*buy_size)/best_ask)*10000)/10000
                                
                                #place limit buy at the best_ask price
                                try:
                                    print("Placing Limit Buy Order:", buy_volume, coin, "@ $", best_ask)
                                    r = coinbasepro.create_limit_buy_order("{coin}/USD".format(coin = coin), round(buy_volume*(1-0.005), 8), best_ask)
                                    last_order_id = r['id']
                                    print("Placed Limit Buy Order:", round(buy_volume*(1-0.005), 8), coin, "@ $", best_ask)
                                    logging.info("Placed Limit Buy Order: " + str(round(buy_volume*(1-0.005), 8)) + coin + "@ $" +  str(best_ask))
                                    purchase_price = best_ask 
                                    target_sell = purchase_price*sell_threshold
                                    order_pending = True
                                    order_pending_type = "BUY"
                                except ccxt.NetworkError as e:
                                    print( 'create_limit_buy_order failed due to a network error:', str(e))
                                    logging.error( 'create_limit_buy_order failed due to a network error:', str(e))
                                except ccxt.ExchangeError as e:
                                    print( 'create_limit_buy_order failed due to exchange error:', str(e))
                                    logging.error( 'create_limit_buy_order failed due to exchange error:', str(e))
                                except Exception as e:
                                    print( 'create_limit_buy_order failed with:', str(e))
                                    logging.error( 'create_limit_buy_order failed with:', str(e))
                        
                        #Sell Signals
                        elif total_position_size > 0.002:
                            
                            #Collect Profit
                            if target_sell <= best_bid: 
                                try:
                                    print("Placing Limit Sell Order (WIN):", available_position_size, coin, "@ $", best_bid)
                                    r = coinbasepro.create_limit_sell_order("{coin}/USD".format(coin = coin), round(available_position_size*(1-0.005), 8), best_bid)
                                    last_order_id = r['id']
                                    print("Placed Limit Sell Order (WIN):", round(available_position_size*(1-0.005), 8), coin, "@ $", best_bid)
                                    logging.info("Placed Limit Sell Order (WIN): " + str(round(available_position_size*(1-0.005), 8)) +  coin + " @ $" + str(best_bid))
                                    order_pending = True
                                    order_pending_type = "WIN"
                                except ccxt.NetworkError as e:
                                    print( 'create_limit_sell_order (win) failed due to a network error:', str(e))
                                    logging.error( 'create_limit_sell_order (win) failed due to a network error:', str(e))
                                except ccxt.ExchangeError as e:
                                    print( 'create_limit_sell_order (win) failed due to exchange error:', str(e))
                                    logging.error( 'create_limit_sell_order (win) failed due to exchange error:', str(e))
                                except Exception as e:
                                    print( 'create_limit_sell_order (win) failed with:', str(e))
                                    logging.error( 'create_limit_sell_order (win) failed with:', str(e))
                                
                            #Stop Loss
                            elif purchase_price*stop_loss >= best_bid:
                                try:
                                    print("Placing Limit Sell Order (Loss):", available_position_size, coin, "@ $", best_bid)
                                    r = coinbasepro.create_limit_sell_order("{coin}/USD".format(coin = coin), round(available_position_size*(1-0.005), 8), best_bid)
                                    last_order_id = r['id']
                                    print("Placed Limit Sell Order (Loss):", round(available_position_size*(1-0.005), 8), coin, "@ $", best_bid)
                                    logging.info("Placed Limit Sell Order (Loss): " +  str(round(available_position_size*(1-0.002), 8)) + coin + "@ $" + str(best_bid))
                                    order_pending = True
                                    order_pending_type = "LOSS"
                                except ccxt.NetworkError as e:
                                    print( 'create_limit_sell_order (loss) failed due to a network error:', str(e))
                                    logging.error( 'create_limit_sell_order (loss) failed due to a network error:', str(e))

                                except ccxt.ExchangeError as e:
                                    print( 'create_limit_sell_order (loss) failed due to exchange error:', str(e))
                                    logging.error( 'create_limit_sell_order (loss) failed due to exchange error:', str(e))

                                except Exception as e:
                                    print( 'create_limit_sell_order (loss) failed with:', str(e))
                                    logging.error( 'create_limit_sell_order (loss) failed with:', str(e))
                                


                        #Fetch another update of the account balance for summary (this also checks if the orders have been filled)
                        try:
                            exchange_balance = coinbasepro.fetch_balance()
                            available_position_size = exchange_balance['free'][coin]
                            used_position_size = exchange_balance['used'][coin]
                            total_position_size = exchange_balance['total'][coin]

                            available_fiat = exchange_balance['free']['USD']
                            used_fiat = exchange_balance['used']['USD']
                            total_fiat = exchange_balance['total']['USD']

                            #Check to see if the order has been filled
                            if order_pending == True:

                                #if the order has been filled, reset and record the outcome
                                if used_position_size == 0 and used_fiat == 0:
                                    print("Order Filled:", order_pending_type, last_order_id)
                                    logging.info("Order Filled:", order_pending_type, last_order_id)
                                    order_pending = False
                                    last_order_id = ""

                                    #Record outcome data
                                    if order_pending_type == "BUY":
                                        buys = buys + 1
                                    elif order_pending_type == "WIN":
                                        gains = gains + 1
                                        position_size = 0
                                        purchase_price = 0
                                    elif order_pending_type == "LOSS":
                                        losses = losses + 1
                                        position_size = 0
                                        purchase_price = 0

                                    order_pending_type = ""
                            
                        except ccxt.NetworkError as e:
                            print( 'fetch_balance failed due to a network error:', str(e))
                            logging.error( 'fetch_balance failed due to a network error:', str(e))
                        except ccxt.ExchangeError as e:
                            print( 'fetch_balance failed due to exchange error:', str(e))
                            logging.error( 'fetch_balance failed due to exchange error:', str(e))
                        except Exception as e:
                            print( 'fetch_balance failed with:', str(e))
                            logging.error( 'fetch_balance failed with:', str(e))
                    
                    #if there is no collected data, pass
                    else:
                        pass
                        

                # --- SUMMARRY --- 
                print("Trades:", buys+losses+gains)
                logging.info("-- BEGIN SUMMARY --")
                logging.info(("Trades: " + str(buys+losses+gains)))
                try:
                    print("Hit Rate:", gains/(losses+gains))
                    logging.info(("Hit Rate: " + str(gains/(losses+gains))))
                except:
                    print("Hit Rate: N/A")
                    logging.info(("Hit Rate: NA"))
                print("Fiat: $", total_fiat)
                logging.info(("Fiat: $" + str(total_fiat)))
                print("Position:", total_position_size)
                logging.info(("Position: " + str(total_position_size) + coin))
                try:
                    print("Entry Price:", purchase_price)
                    logging.info(("Entry Price: $" + str(purchase_price)))
                    print("Position Change:", round(((market_price/purchase_price)-1)*100, 3), "%")
                    logging.info(("Position Change: " + str(round(((market_price/purchase_price)-1)*100, 3)) + "%" ))
                except:
                    pass

                print("Portfolio Worth:", (total_fiat + total_position_size*market_price), "(", round((((total_fiat + total_position_size*market_price)/float(starting_capital))-1)*100, 2), "% )")
                logging.info(("Portfolio Worth:" + str(total_fiat + total_position_size*market_price) + "(" + str(round((((total_fiat + total_position_size*market_price)/float(starting_capital))-1)*100, 2)) + "%)"))
                #print(round((((fiat + position_size*market_price)/starting_capital)-1)*100, 2), "% )")
                print(" ")
                logging.info("--- END SUMMARY --- ")
                portfolio_balance.append(total_fiat + total_position_size*market_price)

            #if there is insufficient data pass until next interval
            else:
                pass

                        
        #if the trade status is not run
        else:
            #wait for signal to change
            print("Paused Trading - Waiting")
            logging.debug("Paused Trading - Waiting")

        #if the script status is not run
        if script_status != "run":
            print("Termination Signal Recieved: Stopping Script...")
            logging.debug("Termination Signal Recieved: Stopping Script")

        #otherwise sleep until the next interval
        else:
            time.sleep(intervals-1) #factor in the ~1 second it takes to run the script


if __name__ == "__main__":
    live_trader(
        rolling_window = sys.argv[1],
        buy_threshold = sys.argv[2],
        sell_threshold = sys.argv[3],
        stop_loss = sys.argv[4],
        buy_size = sys.argv[5],
        coin = sys.argv[6]
    )