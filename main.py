import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from upload_tickers import load_tickers_config
from incremental_add import incremental_update
from incremental_add import validate_existence
from upload_history import ensure_ticker_existence
from telegram import create_pdf, send_document, dataframe_to_pdf, send_pdf_as_image
import requests
import os
import sqlite3

# strategy in https://docs.google.com/document/d/1Z64rx5PmskZ9oHD36wor9tblu1l_oVeXSyFhV1g461o/edit?tab=t.0
current_dir = os.path.dirname(os.path.abspath(__file__))
tickers = load_tickers_config(os.path.join(current_dir, 'tickers.json'))
earnings_dates_results = {}

def check_earnings_risk(report_date):
    if report_date == "N/A" or report_date == "Error":
        return "Unknown"
    
    # Convert report date and today to 'date' for the calculation
    today = datetime.now().date()
    try:
        if hasattr(report_date, 'date'):
            r_date = report_date.date()
        else:
            r_date = report_date
        
        remaining_days = (r_date - today).days
    except Exception:
        return "Unknown"
    
    if remaining_days < 0:
        return "Reported recently"
    elif remaining_days <= 5:
        return f"⚠️ HIGH RISK: Reports in {remaining_days} days"
    else:
        return f"Safe ({remaining_days} days)"

def process_strategy(ticker_list):
    daily_prices = {}
    four_hour_prices = {}
    earnings_dates_results = {}
    for ticker_sym in ticker_list:

        print(f"Processing {ticker_sym}...")

        ensure_ticker_existence(ticker_sym)

        if not validate_existence(ticker_sym, interval="1d") or not validate_existence(ticker_sym, interval="1h"):
            print(f"Skipping {ticker_sym}: Ticker does not exist in local database")
            continue

        incremental_update(ticker_sym, interval="1d")
        incremental_update(ticker_sym, interval="1h")
        
        t = yf.Ticker(ticker_sym)
        
        # --- PART A: DOWNLOAD ---
        conn = sqlite3.connect('trading_data.db')
        df_daily = pd.read_sql(f"SELECT * FROM \"{ticker_sym}_1d\"", conn, index_col='Date', parse_dates=True)
        df_1h = pd.read_sql(f"SELECT * FROM \"{ticker_sym}_1h\"", conn, index_col='Date', parse_dates=True)
        
        conn.close()

        # 1. Convert 'Date' column to real datetime
        df_daily['Date'] = pd.to_datetime(df_daily.index)
        df_1h['Date'] = pd.to_datetime(df_1h.index)
        
        # 2. Set index as DatetimeIndex
        df_daily.set_index('Date', inplace=True)
        df_1h.set_index('Date', inplace=True)
        
        # Download earnings date
        if ticker_sym in ["BTC-USD", "GC=F", "SI=F"]:
            earnings_dates_results[ticker_sym] = "N/A"
            print("No Earnings Date")
        else:
            try:
                cal = t.calendar
                # Check if it is a dict and has the dates key
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    date_list = cal['Earnings Date']
                    # Take the first date from the list
                    earnings_dates_results[ticker_sym] = date_list[0] if date_list else "N/A"
                else:
                    earnings_dates_results[ticker_sym] = "N/A"
            except Exception:
                earnings_dates_results[ticker_sym] = "Error"

            # --- PART B: TECHNICAL CALCULATIONS ---
            print(check_earnings_risk(earnings_dates_results[ticker_sym]))
        # 1. Daily Indicators (Trend and Volatility)
        df_daily.ta.sma(length=200, append=True)
        df_daily.ta.sma(length=50, append=True)
        df_daily.ta.ema(length=20, append=True)
        df_daily.ta.macd(append=True)
        df_daily.ta.atr(length=14, append=True)
        
        # 2. Convert 1h to 4h and calculate Triggers
        # Group candles: Open (first), High (max), Low (min), Close (last)
        df_4h = df_1h.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        df_4h.ta.rsi(length=14, append=True)
        df_4h.ta.bbands(length=20, std=2, append=True)

        # Save results (optional, for Part C)
        # Here you already have the DataFrames with all the new columns
        print(f"Calculated indicators for {ticker_sym}")

        daily_prices[ticker_sym] = df_daily
        four_hour_prices[ticker_sym] = df_4h

    return daily_prices, four_hour_prices, earnings_dates_results


def detect_abnormal_drop(df_daily, k=2.5):
    """
    Detects if the current movement is a bearish outlier based on ATR.
    """
    if len(df_daily) < 2:
        return False
        
    latest = df_daily.iloc[-1]
    previous = df_daily.iloc[-2]
    
    drop = previous['Close'] - latest['Close']
    volatility_threshold = k * latest['ATRr_14']
    
    return drop > volatility_threshold

# Update of Part C with News Alert
# Replace your entire execute_advanced_scanner function with this:

def execute_advanced_scanner(daily_prices, four_hour_prices, earnings_dates_results):
    results = []

    for ticker in daily_prices.keys():
        df_d = daily_prices[ticker]
        df_4 = four_hour_prices[ticker]
        
        # Safety validation: Ensure enough data
        if df_d.empty or df_4.empty or len(df_d) < 2: continue

        # Extract current and previous row (to compare MACD)
        latest_d = df_d.iloc[-1]
        previous_d = df_d.iloc[-2]
        latest_4 = df_4.iloc[-1]
        
        current_price = latest_d['Close']
        
        # --- 1. STRUCTURAL TREND FILTER (1D) ---
        is_bullish = False
        if len(df_d) > 200:
            is_bullish = bool((current_price > latest_d['SMA_200']) and (latest_d['SMA_50'] > latest_d['SMA_200']))
        
        # --- 2. PULLBACK TO VALUE ZONE FILTER (1D) ---
        # A. Distance to EMA 20 (We accept a 3% margin of error to consider it "touches" the zone)
        ema20_distance = abs(current_price - latest_d['EMA_20']) / current_price
        near_ema20 = bool(ema20_distance <= 0.03)
        
        # B. MACD Structure: Histogram must be positive or growing vs previous day
        growing_macd = bool((latest_d['MACDh_12_26_9'] > previous_d['MACDh_12_26_9']) or (latest_d['MACDh_12_26_9'] > 0))
        
        # --- 3. EXECUTION TRIGGER (4H) ---
        # A. Oversold RSI
        oversold_rsi = bool(latest_4['RSI_14'] < 35)
        
        # B. Bollinger Bands: Price touching or below Lower Band
        # We give a tiny margin (0.5%) for intraday noise
        touches_lower_bb = bool(current_price <= (latest_4['BBL_20_2.0_2.0'] * 1.005))
        
        # --- 4. RISK FILTERS ---
        abnormal_movement = detect_abnormal_drop(df_d, k=2.5)
        earnings_status = check_earnings_risk(earnings_dates_results.get(ticker, "N/A"))
        danger = abnormal_movement or "⚠️" in earnings_status

        # --- FINAL ALGORITHM EVALUATION ---
        score_percentage = (int(is_bullish) + int(near_ema20) + int(growing_macd) + int(oversold_rsi) + int(touches_lower_bb)) * 20
        master_condition = score_percentage == 100

        # Output calculations
        stop_loss = current_price - (2 * latest_d['ATRr_14'])
        take_profit = current_price + ((current_price - stop_loss) * 2) # Risk:Reward 1:2
        
        if danger:
            status = "⚠️ AVOID"
            alert = "Fundamental Risk"
        elif master_condition:
            status = "✅ BUY"
            alert = "Filters Passed"
        else:
            status = "⏳ WAITING"
            alert = "Incomplete Filters"
            
        results.append({
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "RSI_4H": round(latest_4['RSI_14'], 2),
            "EMA20_Deviation": f"{round(ema20_distance * 100, 2)}%",
            "Suggested_SL": round(stop_loss, 2),
            "Suggested_TP": round(take_profit, 2),
            "Score": score_percentage,
            "Status": status,
            "Alert": alert
        })

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by="Score", ascending=False)
        df_results["Score"] = df_results["Score"].astype(str) + "%"
        
    return df_results


daily_prices, four_hour_prices, earnings_dates_results = process_strategy(tickers)
results_df = execute_advanced_scanner(daily_prices, four_hour_prices, earnings_dates_results)

message = "\n" + "="*50 + "\n"
message += "🎯 SCAN RESULTS\n"
message += "="*50 + "\n"
if not results_df.empty:
    message += results_df.to_string(index=False) + "\n"
else:
    message += "No processed tickers found.\n"
message += "="*50 + "\n"

print(message)

date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f"message_{date_time}.pdf"
dataframe_to_pdf(results_df, file_name)
send_pdf_as_image(file_name)
os.remove(file_name)
