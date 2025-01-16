import requests
import logging
import aiohttp
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
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


async def handle_main_menu_selection(update: Update, context: CallbackContext):
    if update.callback_query:
        user_choice = update.callback_query.data
        await update.callback_query.answer()
    else:
        user_choice = update.message.text

    match user_choice:
        case "Главное меню":
            await show_main_menu(update, context)
        case "Расчет":
            await fence_calculation(update, context)
        case "О компании":
            await about_company(update, context)
        case "Заявка":
            await request_contact(update, context)
        case "Цены":
            await get_prices(update, context)
        case _:
            await update.message.reply_text("Вы выбрали неизвестную опцию.")


async def handle_fence_selection(update: Update, context: CallbackContext, type_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.BASE_API_URL}fences?typeId={type_id}") as response:
            if response.status == 200:
                data = await response.json()
                fences = data.get("data", [])

                keyboard = [
                    [InlineKeyboardButton(fence["name"], callback_data=str(fence["id"]))] for fence in fences
                ]

                keyboard.append([InlineKeyboardButton("Назад")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.callback_query.message.edit_text(
                    "Выберите забор из списка:",
                    reply_markup=reply_markup
                )
            else:
                await update.callback_query.message.edit_text("Произошла ошибка при получении забора.")


async def fence_calculation(update: Update, context: CallbackContext):
    await update.message.reply_text("Давайте посмотрим что у нас есть...")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.BASE_API_URL}fences/types") as response:
            if response.status == 200:
                data = await response.json()
                types = data.get("data")

                keyboard = [
                    [InlineKeyboardButton(type_["name"], callback_data=str(type_["id"]))] for type_ in types
                ]
                keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    "Выберите необходимый тип забора",
                    reply_markup=reply_markup
                )
            else:
                logger.error("Unexpected error. Fence types not found.")
                await update.message.reply_text("Произошла ошибка при получении данных.")


async def about_company(update: Update, context: CallbackContext):
    await update.message.reply_text("About")


async def request_contact(update: Update, context: CallbackContext):
    await update.message.reply_text("Request contact")


async def get_prices(update: Update, context: CallbackContext):
    await update.message.reply_text("Get prices")
