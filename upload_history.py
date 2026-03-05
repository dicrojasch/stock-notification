import yfinance as yf
import sqlite3
import pandas as pd
from datetime import datetime
from upload_tickers import load_tickers_config

def download_full_history(ticker):
    conn = sqlite3.connect('trading_data.db')
    print("Starting massive historical download...")

    success = False
    try:
        # 'max' downloads everything Yahoo Finance has available
        df = yf.download(ticker, period="max", interval="1d", progress=False, auto_adjust=False, actions=False)
        if not df.empty:
            # Clean column names for SQL
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            df.index.name = 'Date'
            df.to_sql(f"{ticker}_1d", conn, if_exists='replace', index=True)
            print(f"✅ {ticker}_1d: Full history saved.")
            success = True
    except Exception as e:
        print(f"❌ Error with {ticker}: {e}")
    
    conn.close()
    return success

def initialize_hourly_db(ticker):
    conn = sqlite3.connect('trading_data.db')
    print(f"Downloading 730-day base for {ticker}...")
    # Download the maximum allowed for 1H
    df = yf.download(ticker, period="730d", interval="1h", progress=False)
    
    success = False
    if not df.empty:
        # Clean columns MultiIndex if it exists (common in new versions of yfinance)
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        # Save to specific hourly table
        df.index.name = 'Date'
        df.to_sql(f"{ticker}_1h", conn, if_exists='replace', index=True)
        print(f"✅ {ticker}_1h ready with {len(df)} records.")
        success = True
    conn.close()
    return success


def ensure_ticker_existence(ticker):
    """
    Verifies if a ticker's tables exist in the DB.
    If they do not exist, downloads full history (1d) and 730d (1h).
    """
    conn = sqlite3.connect('trading_data.db')
    cursor = conn.cursor()
    
    # Create the existence table if it does not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS existence (
            name TEXT PRIMARY KEY,
            daily TEXT,
            hourly TEXT
        )
    ''')
    conn.commit()
    
    # Required tables for Swing strategy
    required_tables = [f"{ticker}_1d", f"{ticker}_1h"]
    existing_tables = []

    # 1. Query SQLite metadata to see which tables already exist
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
        if cursor.fetchone():
            existing_tables.append(table)

    # 2. If tables are missing, proceed to download
    if len(existing_tables) < len(required_tables):
        print(f"🔍 Ticker {ticker} not found or incomplete in DB. Starting download...")
        
        try:
            # Daily Download (Max history for trend and thesis)
            if f"{ticker}_1d" not in existing_tables:
                if download_full_history(ticker):
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('SELECT 1 FROM existence WHERE name = ?', (ticker,))
                    if cursor.fetchone():
                        cursor.execute('UPDATE existence SET daily = ? WHERE name = ?', (now, ticker))
                    else:
                        cursor.execute('INSERT INTO existence (name, daily) VALUES (?, ?)', (ticker, now))
                    conn.commit()

            # Hourly Download (730 days for 4H trigger)
            if f"{ticker}_1h" not in existing_tables:
                if initialize_hourly_db(ticker):
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('SELECT 1 FROM existence WHERE name = ?', (ticker,))
                    if cursor.fetchone():
                        cursor.execute('UPDATE existence SET hourly = ? WHERE name = ?', (now, ticker))
                    else:
                        cursor.execute('INSERT INTO existence (name, hourly) VALUES (?, ?)', (ticker, now))
                    conn.commit()

        except Exception as e:
            print(f"❌ Error initializing {ticker}: {e}")
    else:
        print(f"💎 {ticker} already exists in local database.")

    conn.close()
