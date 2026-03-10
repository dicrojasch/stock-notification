# Stock Notification System

An automated Swing Trading scanner that monitors a list of stocks, calculates technical indicators, and sends visual reports via Telegram.

## Key Features

- **Automated Scanner**: Daily execution to identify bullish pullbacks and value zones.
- **Dynamic Ticker Management**: Manage the monitoring list via a Telegram bot without restarting services.
- **Rich Visual Reports**: Generates PDF reports with technical signals, including SMA, EMA, RSI, MACD, and Bollinger Bands.
- **Seed Data Architecture**: Initialized from JSON, persisted in SQLite for high availability and dynamic updates.

## System Components

### 1. Main Scanner (`main.py`)
The core logic that processes stock data, calculates technical indicators, and determines trading signals. It reads the active stock list from the SQLite database.

### 2. Database Setup (`db_setup.py`)
Handles the migration from static JSON (`tickers.json`) to the SQLite database (`trading_data.db`). It seeds the database on the first run.

### 3. Telegram Bot (`telegram_bot.py`)
A ChatOps interface for managing tickers. See [telegram_bot.md](./telegram_bot.md) for detailed documentation and deployment instructions.

### 4. Utilities
- **`my_telegram.py`**: Handles PDF generation and Telegram messaging.
- **`sql_lite.py`**: Basic SQLite database utilities.
- **`incremental_add.py`**: Manages efficient historical data updates.

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd stock-notification
   ```

2. **Setup Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file with your credentials:
   ```env
   TOKEN=your_telegram_bot_token
   CHAT_ID=your_telegram_chat_id
   DB_PATH=trading_data.db
   ```

4. **Initialize and Run**:
   The first run of `main.py` or `telegram_bot.py` will automatically initialize the database from `tickers.json`.

## Usage

- **Run Scanner**: `python main.py`
- **Start Management Bot**: `python telegram_bot.py`

## License
MIT
