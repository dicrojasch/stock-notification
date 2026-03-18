import sqlite3
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_PATH = os.getenv('DB_PATH', 'trading_data.db')

logger = logging.getLogger(__name__)

def init_db_from_json(json_path='data/tickers.json', db_path=DB_PATH):
    """
    Initializes the database and seeds the active_tickers table from a JSON file.
    If the table already exists and has data, the JSON file is ignored.
    """
    fallback_tickers = ["AAPL", "GOOGL", "MSFT", "AMZN"]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create active_tickers table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_tickers (
                ticker TEXT PRIMARY KEY
            )
        ''')
        
        # Check if table has data
        cursor.execute('SELECT COUNT(*) FROM active_tickers')
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info(f"Database table 'active_tickers' is empty. Seeding from {json_path}...")
            
            tickers_to_insert = []
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        tickers_to_insert = data.get('tickers', [])
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Error reading JSON file {json_path}: {e}. Using fallback tickers.")
                    tickers_to_insert = fallback_tickers
            else:
                logger.warning(f"JSON file {json_path} not found. Using fallback tickers.")
                tickers_to_insert = fallback_tickers
            
            # Insert initial data
            if tickers_to_insert:
                cursor.executemany(
                    'INSERT OR IGNORE INTO active_tickers (ticker) VALUES (?)',
                    [(t,) for t in tickers_to_insert]
                )
                conn.commit()
                logger.info(f"Successfully seeded {len(tickers_to_insert)} tickers into the database.")
            else:
                logger.info("No tickers found to seed.")
        else:
            logger.info("Database already contains tickers. Skipping seed from JSON.")
            
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Test initialization
    init_db_from_json()
