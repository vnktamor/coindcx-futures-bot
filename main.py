from telegram.ext import Application, CommandHandler
from config import TELEGRAM_BOT_TOKEN
from handlers.commands import start, price, long_cmd, short_cmd, positions, status

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("long", long_cmd))
    app.add_handler(CommandHandler("short", short_cmd))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("status", status))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
