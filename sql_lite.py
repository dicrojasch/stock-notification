import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_PATH = os.getenv('DB_PATH', 'trading_data.db')

# Create database connection
conn = sqlite3.connect(DB_PATH)

# Save a DataFrame to the database
def save_to_db(df, ticker, table):
    df.to_sql(f"{ticker}_{table}", conn, if_exists='replace')

# Read data
def read_from_db(ticker, table):
    return pd.read_sql(f"SELECT * FROM {ticker}_{table}", conn)