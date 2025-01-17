import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from logging_config import setup_logging
from config import config
from handlers.calculation_conversation import (
    start_calculation,
    choose_fence_type,
    ask_fence_popular_specs,
    choose_fence_variant,
    save_fence_variant,
    ask_fence_length,
    ask_fence_accessories,
    handle_fence_accessory,
    handle_fence_accessory_quantity,
)
from handlers.calculation_states import CalcStates
from handlers import (
    start,
    handle_contact,
    show_main_menu,
    handle_main_menu_selection,
    error_handler
)


def main():
    logger = setup_logging(logging.INFO)
    logger.info('Starting bot...')

    application = Application.builder().token(config.BOT_TOKEN).build()

    calc_handler = ConversationHandler(
        entry_points=[
            CommandHandler("calc", start_calculation),
            MessageHandler(filters.Text("Расчет"), start_calculation),
        ],
        states={
            CalcStates.FENCE_TYPE.value: [
                CallbackQueryHandler(choose_fence_type),
            ],
            CalcStates.FENCE_POPULAR_SPECS.value: [
                CallbackQueryHandler(ask_fence_popular_specs),
            ],
            CalcStates.FENCE_VARIANTS.value: [
                CallbackQueryHandler(choose_fence_variant),
            ],
            CalcStates.FENCE_LENGTH.value: [
                CallbackQueryHandler(save_fence_variant),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_fence_length)
            ],
            CalcStates.FENCE_ACCESSORIES.value: [
                CallbackQueryHandler(handle_fence_accessory),
            ],
            CalcStates.FENCE_ACCESSORIES_QUANTITY.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fence_accessory_quantity),
            ],
            CalcStates.NEED_GATES.value: [
                # ...
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_dialog),
            MessageHandler(filters.Text("Главное меню"), cancel_dialog),
        ],
        allow_reentry=True,
    )

    application.add_handler(calc_handler)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_selection))
    application.add_handler(CallbackQueryHandler(handle_main_menu_selection))

    application.add_error_handler(error_handler)

    application.run_polling()


def cancel_dialog(update, context):
    context.user_data.clear()
    update.message.reply_text("Диалог отменён. Возвращаемся в главное меню.")
    return ConversationHandler.END


if __name__ == '__main__':
    main()
