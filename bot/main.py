import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from handlers import (
    start,
    handle_contact,
    show_main_menu,
    handle_main_menu_selection,
    error_handler
)
from config import config
from logging_config import setup_logging


def main():
    logger = setup_logging(logging.INFO)
    logger.info('Starting bot...')

    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_selection))
    application.add_handler(CallbackQueryHandler(handle_main_menu_selection))

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
