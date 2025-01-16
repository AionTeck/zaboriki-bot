import logging

import aiohttp
from telegram import Update
from telegram.ext import CallbackContext
from config import config
from .menu import show_main_menu

logger = logging.getLogger(__name__)


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
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{config.BASE_API_URL}clients", json=post_data) as response:
                if response.status == 200:
                    await update.message.reply_text(f"Спасибо! Ваш номер телефона {phone_number} был сохранён.")
                    await show_main_menu(update, context)
                elif response.status == 400:
                    logger.error(f"HTTP error occurred. {response.json()}")
                    await update.message.reply_text("Произошла ошибка при сохранении вашего номера. Попробуйте позже.")
                else:
                    logger.error(f"Unexpected error occurred.")
                    await update.message.reply_text("Произошла непредвиденная ошибка, попробуйте позже.")
    except aiohttp.ClientError as e:
        logger.error(f"Notwork error occurred: {e}")
        await update.message.reply_text("Проблема с сетью или сервером. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        await update.message.reply_text("Произошла непредвиденная ошибка. Попробуйте позже.")
