# bot/handlers/menu.py
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def show_main_menu(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton('Расчет'), KeyboardButton('О компании')],
        [KeyboardButton('Заявка'), KeyboardButton('Цены')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Чтобы продолжить работу, выберите дальнейшее действие",
        reply_markup=reply_markup
    )


async def handle_main_menu_selection(update: Update, context: CallbackContext):
    if update.callback_query:
        user_choice = update.callback_query.data
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        user_choice = update.message.text
        message = update.message

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
            # Если это текстовое сообщение, отвечаем
            if not update.callback_query:
                await message.reply_text("Вы выбрали неизвестную опцию.")
            else:
                # Если это был коллбек, можно обновить сообщение
                await message.edit_text("Вы выбрали неизвестную опцию.")


# Временно разместим эти функции тут, а потом можем вынести в другие файлы
async def about_company(update: Update, context: CallbackContext):
    await update.message.reply_text("About company info...")


async def request_contact(update: Update, context: CallbackContext):
    await update.message.reply_text("Request contact info...")


async def get_prices(update: Update, context: CallbackContext):
    await update.message.reply_text("Get prices info...")


# Импортируем fence_calculation из handlers/fence_conversation.py
from .fence_conversation import fence_calculation
