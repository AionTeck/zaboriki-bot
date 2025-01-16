import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext


logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext) -> int:
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Привет, {user_name}!\n\n"
        "Мы изготавливаем, продаем и устанавливаем заборы\n"
        "Я могу быстро посчитать большинство востребованных ограждений.\n"
        "Для расчета потребуется любой ваш контакт."
    )

    keyboard = [
        [KeyboardButton("📱 Поделиться номером телефона", request_contact=True)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Пожалуйста, поделитесь вашим номером телефона, чтобы мы могли продолжить.",
        reply_markup=reply_markup,
    )
    return 0
