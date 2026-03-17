import json
import os

def load_tickers_config(file_path='tickers.json'):
    """
    Loads the list of tickers from a JSON file.
    If the file does not exist, it creates one with a base list.
    """
    base_tickers = ["MELI", "AAPL", "SSNLF", "MSFT"]
    
    # 1. Check if the file exists
    if not os.path.exists(file_path):
        print(f"⚠️ File {file_path} not found. Creating a new one with a base list...")
        with open(file_path, 'w') as f:
            json.dump({"tickers": base_tickers}, f, indent=4)
        return base_tickers

    # 2. Attempt to read the file
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
            # Returns the list for the "tickers" key, or the base list if the key doesn't exist
            return config.get("tickers", base_tickers)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ Error parsing JSON file: {e}. Using default list.")
        return base_tickers
