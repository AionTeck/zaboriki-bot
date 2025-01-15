import requests
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from config import config

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Произошла ошибка при обработке обновления: {context.error}")


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


async def handle_contact(update: Update, context: CallbackContext):
    contact = update.message.contact
    user_name = update.message.from_user.first_name
    phone_number = contact.phone_number
    user_id = update.message.from_user.id

    post_data = {
        'name': user_name,
        'phoneNumber': phone_number,
        'telegramId': user_id,
    }

    try:
        response = requests.post(f"{config.BASE_API_URL}clients", json=post_data)
        response.raise_for_status()

        await update.message.reply_text(f"Спасибо! Ваш номер телефона {phone_number} был сохранён.")

        await show_main_menu(update, context)
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        await update.message.reply_text(f"Произошла ошибка при сохранении вашего номера. Попробуйте позже.")
    except Exception as err:
        logger.error(f"Unexpected error occurred: {err}")
        await update.message.reply_text(f"Произошла непредвиденная ошибка, попробуйте позже.")


async def show_main_menu(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton('Расчет'), KeyboardButton('О компании')],
        [KeyboardButton('Заявка'), KeyboardButton('Цены')]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Чтобы продолжить работу, необходимо выбрать дальнейшее действие",
        reply_markup=reply_markup
    )
