import sqlite3
from datetime import datetime
import logging
import time
import configparser
import ccxt
import sys
import ast


#set up logging
log_format = (
    '[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')

logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    filename=('scraper.log'),
)

#connect to database
conn = sqlite3.connect('pricedata.db')
c = conn.cursor()

#try to create a new table if it doesnt exist
try:
    c.execute('''CREATE TABLE price_data (
        date_time text, 
        currency_pair text,
        ask_price numeric, 
        bid_price numeric, 
        market_price numeric
        )''')
except:
    pass

coinbase = ccxt.coinbasepro({})

def price_scraper(currency_pair = "BTC/USD"):
    '''
    Collects currency pair price data from coinbase and stores it in an sqlite database. 
    
    Parameters:
        currency_pair: what currency pair data to collect (default = "BTC/USD")
    Returns:
        None
    '''
    logging.debug("Initializing price scraper (Coinbase)")
    format = "%d/%m/%Y %H:%M:%S"
    logging.debug("Set environmental parameters")
    conn = sqlite3.connect("pricedata.db")
    c = conn.cursor()
    logging.debug("Established connection with local database")

    config = configparser.ConfigParser()
    config.read_file(open("coinbase_parameters.txt"))
    seconds_to_sleep = ast.literal_eval(config.get('Scraper Section', 'scraper_frequency'))*60 

    #start loop
    script_status = "run"
    while script_status == "run":

        #Get Master Parameters
        config = configparser.ConfigParser()
        config.read_file(open("coinbase_parameters.txt"))
        scrape_status = config.get('Scraper Section', 'scrape') #controls whether to scrape this cycle
        script_status = config.get('Scraper Section', 'scraper_script') #controls whether to shut the script down
        download_status = ""

        if scrape_status == "run":
            try:
                ticker_data = coinbase.fetch_ticker(currency_pair)
                logging.debug("Downloaded ticker data from Coinbase API")
                best_ask = ticker_data['ask']
                best_bid = ticker_data['bid']
                market_price = (best_ask + best_bid)/2
                logging.debug("Market Price:" + str(market_price))
                print("Market Price:", market_price)
                download_status = "success"
    
            except Exception as e:
                download_status = "failure"
                logging.error("Failed to download ticker data:" + +  str(e))

            #add data to the database if succesfully downloaded
            if download_status == "success":
                entry = (datetime.now().strftime(format), currency_pair, best_ask, best_bid, market_price)
                c.execute("INSERT INTO price_data VALUES (?, ?, ?, ?, ?)", entry)
                conn.commit()
                logging.debug("Succesfully updated database")


        elif scrape_status == "pause":
            print("Paused Scraping")
            logging.debug("Paused Scraping")

        if script_status != "run":
            print("Termination Signal Recieved: Stopping Script...")
            logging.debug("Termination Signal Recieved: Stopping Script")
        
        # sleep 
        time.sleep(seconds_to_sleep)


if __name__ == "__main__":
    price_scraper(currency_pair=sys.argv[1]) 

