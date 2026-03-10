# Telegram Bot Integration (ChatOps)

This module provides a **ChatOps** interface for the Swing Trading Scanner. It allows you to dynamically manage the list of active stock tickers monitored by the daily scanner directly from Telegram.

## Architecture & Data Flow

The system implements a **Seed Data** architecture using SQLite as the source of truth:

1.  **JSON Seed (`tickers.json`)**: Serves as the initial configuration or "factory default" list of stocks.
2.  **SQLite Database (`trading_data.db`)**: The central **Single Source of Truth**. During the first execution, the system populates the `active_tickers` table from the JSON file.
3.  **Telegram Bot**: An asynchronous service using Long Polling. It interacts exclusively with the `active_tickers` table in SQLite.
4.  **Main Scanner**: The scanner script reads the target list of assets exclusively from the SQLite database.

## Bot Commands

Interact with the bot using the following commands:

-   `/start`: Displays the welcome message and command list.
-   `/add [TICKER]`: Adds a new stock symbol to the monitoring list (e.g., `/add NVDA`).
-   `/remove [TICKER]`: Removes a stock symbol from the list (e.g., `/remove AAPL`).
-   `/list`: Displays all currently active tickers stored in the database.

---

## Deployment on Raspberry Pi (systemd)

To ensure the bot runs continuously and restarts automatically, it should be deployed as a `systemd` service.

### 1. Create the Service File

```bash
sudo nano /etc/systemd/system/telegram_bot.service
```

### 2. Configure the Service

Paste the following configuration, adjusting paths as necessary:

```ini
[Unit]
Description=Telegram Bot for Swing Trading System
After=network.target

[Service]
User=diego
WorkingDirectory=/home/diego/repos/stock-notification
# Path to python inside your virtual environment
ExecStart=/home/diego/repos/stock-notification/.venv/bin/python /home/diego/repos/stock-notification/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start the Daemon

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram_bot.service
sudo systemctl start telegram_bot.service
```

### 4. Monitor the Bot Status

```bash
# View live logs
sudo journalctl -u telegram_bot.service -f

# Check service status
sudo systemctl status telegram_bot.service
```