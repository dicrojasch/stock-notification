from datetime import datetime, timedelta
from upload_tickers import load_tickers_config
import sqlite3
import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_PATH = os.getenv('DB_PATH', 'trading_data.db')

def validate_existence(ticker, interval="1d"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ticker_exists = True
    try:
        if interval == "1d":
            cursor.execute("SELECT 1 FROM existence WHERE name = ? AND daily IS NOT NULL AND daily != ''", (ticker,))
        else:
            cursor.execute("SELECT 1 FROM existence WHERE name = ? AND hourly IS NOT NULL AND hourly != ''", (ticker,))
            
        if not cursor.fetchone():
            print(f"❌ Ticker {ticker} has no initialization records for the {interval} interval.")
            ticker_exists = False
    except sqlite3.OperationalError:
        print("❌ The 'existence' table does not exist in the database.")
        ticker_exists = False

    conn.close()
    return ticker_exists

def incremental_update(ticker, interval="1d"):
    conn = sqlite3.connect(DB_PATH)
    table = f"{ticker}_1d" if interval == "1d" else f"{ticker}_1h"

    try:
        # 1. Get the last date
        query = f"SELECT MAX(Date) FROM \"{table}\""
        last_date_str = pd.read_sql(query, conn).iloc[0, 0]

        if last_date_str:
            # Convert to datetime
            last_date = pd.to_datetime(last_date_str)
            
            # USE THE SAME START DATE (without adding 1 day)
            # This prevents start_date from being > today
            start_date = last_date.strftime('%Y-%m-%d')
            
            # 2. Download
            new_df = yf.download(ticker, start=start_date, interval=interval, progress=False)
            
            if not new_df.empty:
                # Clean MultiIndex columns if it exists
                new_df.columns = [col[0] if isinstance(col, tuple) else col for col in new_df.columns]
                new_df.index.name = 'Date'
                # REMOVE DUPLICATES: 
                # We remove what we already have to avoid repeating the last candle in the DB
                new_df = new_df[new_df.index > last_date]

                if not new_df.empty:
                    new_df.to_sql(table, conn, if_exists='append', index=True)
                    print(f"➕ {ticker}: {len(new_df)} new rows added.")
                else:
                    print(f"☕ {ticker}: Already up to date.")
            else:
                print(f"☕ {ticker}: No new data since {start_date}.")
        else:
            raise ValueError("Empty table") # Jumps to except for initial download

    except Exception as e:
        print(f"📦 Creating/Resetting table for {ticker} (Reason: {e})...")
        # For intervals smaller than 1d, '2y' might be too much. 
        # 1h/4h only allow up to 730 days.
        period = "730d" if interval != "1d" else "2y"
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        
        if not df.empty:
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            df.to_sql(table, conn, if_exists='replace', index=True)
            print(f"✅ {ticker}: Table created with {len(df)} records.")

    finally:
        conn.close()
