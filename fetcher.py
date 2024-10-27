'''

Download daily stock price from Yahoo

'''


import os
import pandas as pd
import numpy as np
import sqlite3

# pip install pandas-datareader
import pandas_datareader as pdr

import yfinance as yf

import option

# https://www.geeksforgeeks.org/python-stock-data-visualisation/

class Fetcher(object):

    def __init__(self, opt, db_connection):
        # opt is an option instance
        self.opt = opt
        self.db_connection = db_connection

    def get_daily_from_yahoo(self, ticker, start_date, end_date):
        stock = yf.Ticker(ticker)                                                  #object representing stock/financial instrument to be called
                                                                               
        df = stock.history(period="1d", start=start_date, end=end_date)            #uses the history method the stock object and stores the data in dataframe 'df'

        return(df)

    def download_data_to_csv(self, list_of_tickers):
    
        for ticker in list_of_tickers:
            # Get daily stock data for the ticker
            df = self.get_daily_from_yahoo(ticker, self.opt.start_date, self.opt.end_date)
        
            # Add a 'Ticker' column with the ticker symbol
            df['Ticker'] = ticker
        
            # Create the filename for the CSV file (e.g., AAPL_daily.csv)
            filename = os.path.join(self.opt.output_dir, f"{ticker}_daily.csv")
        
            # Save the DataFrame to a CSV file
            df.to_csv(filename)
        
            # Added from AP.py
            if df.shape[0] == 0:
                print(f"No data found for {ticker}")

        pass
        
    def csv_to_table(self, csv_file_name, fields_map, db_table):
        
        # insert data from a csv file to a table
        df = pd.read_csv(csv_file_name)
        if df.shape[0] <= 0:
            return
        # change the column header
        df.columns = [fields_map[x] for x in df.columns]

        # move ticker columns
        new_df = df[['Ticker']].copy()
        for c in df.columns[:-1]:
            new_df.loc[:, c] = df[c]

        # Added from AP.py (the drop Stocksplits & insert TurnOver columns code). I manually changed the database schema before in SQL (not good ethic)
        # drop the StockSplits column
        new_df.drop(['StockSplits'], axis=1, inplace=True)
        # insert a TurnOver column with zero
        new_df.insert(loc = new_df.shape[1] - 1, column = 'TurnOver', value = [0] * new_df.shape[0])
        #print(new_df.head())

        ticker = os.path.basename(csv_file_name).replace('.csv','').replace("_daily", "")
        print(ticker)
        cursor = self.db_connection.cursor()

        # Delete old data for the ticker
        sql_delete = f"DELETE FROM {db_table} WHERE Ticker = '{ticker}'"
        #print(sql_delete)
        cursor.execute(sql_delete)
        
        #print(new_df)
        data = new_df.values.tolist()

        # changed using AP.py to not use data_tuples. data_tuples worked but this is cleaner/simpler code
        # Insert new data with IGNORE clause to handle duplicates
        sql_insert = f"INSERT OR REPLACE INTO {db_table} (Ticker, AsOfDate, Open, High, Low, Close, Volume, TurnOver, Dividend) "
        sql_insert += " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?); "
        #print(sql_insert)

        try:
            cursor.executemany(sql_insert, data)
            self.db_connection.commit()
            # Close the cursor and database connection
            cursor.close()
            # Print that data successfully inserted
            print("Data inserted successfully!")
        except Exception as e:
            print(f"Failed in uploading {ticker} because {e}")
        
    def save_daily_data_to_sqlite(self, daily_file_dir, list_of_tickers):

        # read all daily.csv files from a dir and load them into sqlite table
        db_file = os.path.join(self.opt.sqlite_db)
        db_table = 'EquityDailyPrice'
    
        fields_map = {'Date': 'AsOfDate', 'Dividends': 'Dividend', 'Stock Splits': 'StockSplits'}
        for f in ['Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']:
            fields_map[f] = f

        for ticker in list_of_tickers:
            file_name = os.path.join(daily_file_dir, f"{ticker}_daily.csv")
            #print(file_name)
            self.csv_to_table(file_name, fields_map, db_table)

        #close the db connection
        sqlite3.connect(db_file).close()

        '''
        # read all daily.csv files from a dir and load them into the sqlite table
            db_file = os.path.join(self.opt.sqlite_db)
            #db_conn = sqlite3.connect(db_file)
            db_table = 'EquityDailyPrice'

            fields_map = {'Date': 'AsOfDate', 'Dividends': 'Dividend', 'Stock Splits': 'StockSplits'}
            for f in ['Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']:
                fields_map[f] = f

            for ticker in list_of_tickers:
                file_name = os.path.join(daily_file_dir, f"{ticker}_daily.csv")
                print(file_name)
                self.csv_to_table(file_name, fields_map, db_table)
        '''

    def test(self):
        ticker = 'MSFT'
        start_date = '2020-01-01'
        end_date = '2023-08-01'

        print (f"\nTesting getting data for {ticker}:")
        df = self.get_daily_from_yahoo(ticker, start_date, end_date)
        print(df)

    
def run():
    
    parser = option.get_default_parser()
    parser.add_argument('--data_dir', dest = 'data_dir', default='./data', help='data dir')    
    
    args = parser.parse_args()
    opt = option.Option(args = args)

    opt.output_dir = os.path.join(opt.data_dir, "daily")
    opt.sqlite_db = os.path.join(opt.data_dir, "sqlitedb/Equity.db")
    
    if opt.tickers is not None:
        list_of_tickers = opt.tickers.split(',')
    else:
        fname = os.path.join(opt.data_dir, "S&P500.txt")
        list_of_tickers = list(pd.read_csv(fname, header=None).iloc[:, 0])
        print(f"Read tickers from {fname}")
        

    print(list_of_tickers)
    print(opt.start_date, opt.end_date)

    db_file = opt.sqlite_db
    db_connection = sqlite3.connect(db_file)
    
    fetcher = Fetcher(opt, db_connection)
    print(f"Download data to {opt.data_dir} directory")

    fetcher.download_data_to_csv(list_of_tickers)
    fetcher.save_daily_data_to_sqlite(opt.output_dir, list_of_tickers)
    fetcher.test()

if __name__ == "__main__":
    run()