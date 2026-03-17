import os
import sqlite3
from dotenv import load_dotenv

# Test with default value
print("Testing with default value (no .env)...")
if os.path.exists('.env'):
    os.rename('.env', '.env.bak')

try:
    load_dotenv()
    db_path = os.getenv('DB_PATH', 'trading_data.db')
    print(f"DB_PATH: {db_path}")
    assert db_path == 'trading_data.db'
finally:
    if os.path.exists('.env.bak'):
        os.rename('.env.bak', '.env')

# Test with custom value in .env
print("\nTesting with custom value in .env...")
with open('.env.test', 'w') as f:
    f.write('DB_PATH="test_env.db"')

try:
    from dotenv import dotenv_values
    config = dotenv_values('.env.test')
    db_path = config.get('DB_PATH', 'trading_data.db')
    print(f"DB_PATH from .env.test: {db_path}")
    assert db_path == 'test_env.db'
finally:
    if os.path.exists('.env.test'):
        os.remove('.env.test')

print("\nVerification successful!")
