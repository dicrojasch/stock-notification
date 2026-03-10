import os
import sqlite3
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from db_setup import init_db_from_json

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv('DB_PATH', 'trading_data.db')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and instructions."""
    await update.message.reply_text(
        "Welcome to the Stock Notification Bot!\n\n"
        "Commands:\n"
        "/add [ticker] - Add a ticker to the active list\n"
        "/remove [ticker] - Remove a ticker from the active list\n"
        "/list - List all active tickers"
    )

async def add_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a ticker to the database."""
    if not context.args:
        await update.message.reply_text("Usage: /add [ticker]")
        return
    
    ticker = context.args[0].upper()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO active_tickers (ticker) VALUES (?)", (ticker,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Added {ticker} to active tickers.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"⚠️ {ticker} is already in the list.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def remove_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a ticker from the database."""
    if not context.args:
        await update.message.reply_text("Usage: /remove [ticker]")
        return
    
    ticker = context.args[0].upper()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_tickers WHERE ticker = ?", (ticker,))
        if cursor.rowcount > 0:
            await update.message.reply_text(f"✅ Removed {ticker} from active tickers.")
        else:
            await update.message.reply_text(f"⚠️ {ticker} was not found in the list.")
        conn.commit()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def list_tickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active tickers from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM active_tickers ORDER BY ticker")
        tickers = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if tickers:
            message = "📋 **Active Tickers:**\n\n" + "\n".join(tickers)
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("📋 The active tickers list is empty.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

if __name__ == '__main__':
    # Initialize DB on startup
    init_db_from_json()
    
    if not TOKEN:
        print("❌ Error: TOKEN environment variable not set.")
    else:
        # Build and start the bot
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_ticker))
        application.add_handler(CommandHandler("remove", remove_ticker))
        application.add_handler(CommandHandler("list", list_tickers))
        
        print("🤖 Bot is running...")
        application.run_polling()
