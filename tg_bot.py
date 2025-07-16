import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

load_dotenv()
TG_TOKEN = os.environ['TG_BOT_TOKEN']


def start(update, context):
    update.message.reply_text('Привет!')

def echo(update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(TG_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()