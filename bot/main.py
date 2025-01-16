from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers import *
from config import config


def main():
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
