import yfinance as yf
import sqlite3
import pandas as pd
from datetime import datetime
from upload_tickers import load_tickers_config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_PATH = os.getenv('DB_PATH', 'trading_data.db')

def fetch_and_save_data(ticker, period, interval, table_suffix):
    """
    Generic function to download market data and save it to a specific SQLite table.
    Includes the long_name column as requested.
    """
    conn = sqlite3.connect(DB_PATH)
    success = False
    
    try:
        # 1. Get company metadata
        ticker_obj = yf.Ticker(ticker)
        long_name = ticker_obj.info.get('longName', ticker)

        # 3. NETWORK REQUEST: EARNINGS (PARALLEL)
        earnings_date = "N/A"
        
        if ticker in ["BTC-USD", "GC=F", "SI=F"]:
            pass # No earnings for Crypto/Commodities
        else:
            try:
                cal = ticker_obj.calendar
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    date_list = cal['Earnings Date']
                    earnings_date = date_list[0] if date_list else "N/A"
            except Exception:
                earnings_date = "Error"

        # 2. Download historical data
        print(f"Downloading {interval} data for {ticker} ({period})...")
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)

        if not df.empty:
            # 3. Clean MultiIndex columns if present
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            
            # 4. Add the requested long_name column
            df['long_name'] = long_name
            df['earnings_date'] = earnings_date
            df.index.name = 'Date'
            
            # 5. Save to SQLite
            table_name = f"{ticker}_{table_suffix}"
            df.to_sql(table_name, conn, if_exists='replace', index=True)
            print(f"✅ {table_name} saved successfully.")
            success = True
        else:
            print(f"⚠️ No data found for {ticker} with interval {interval}.")

    except Exception as e:
        print(f"❌ Error processing {ticker} ({interval}): {e}")
    
    finally:
        conn.close()
    
    return success

# Simplified wrappers using the factored function
def download_full_history(ticker):
    return fetch_and_save_data(ticker, period="max", interval="1d", table_suffix="1d")

def initialize_hourly_db(ticker):
    return fetch_and_save_data(ticker, period="730d", interval="1h", table_suffix="1h")

def ensure_ticker_existence(ticker):
    """
    Verifies and initializes ticker tables in the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure existence tracking table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS existence (
            name TEXT PRIMARY KEY,
            daily TEXT,
            hourly TEXT
        )
    ''')
    conn.commit()
    
    # Check for existing tables in SQLite metadata
    required_configs = [
        {'suffix': '1d', 'field': 'daily', 'func': download_full_history},
        {'suffix': '1h', 'field': 'hourly', 'func': initialize_hourly_db}
    ]

    for config in required_configs:
        table_name = f"{ticker}_{config['suffix']}"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        
        if not cursor.fetchone():
            print(f"🔍 {table_name} missing. Initializing...")
            if config['func'](ticker):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Update or insert into existence table
                cursor.execute(f'''
                    INSERT INTO existence (name, {config['field']}) 
                    VALUES (?, ?) 
                    ON CONFLICT(name) DO UPDATE SET {config['field']} = excluded.{config['field']}
                ''', (ticker, now))
                conn.commit()
        else:
            print(f"💎 {table_name} already exists.")

    conn.close()