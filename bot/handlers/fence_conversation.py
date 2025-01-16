import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import config

logger = logging.getLogger(__name__)

CHOOSING_TYPE = 1
CHOOSING_FENCE = 2


async def start_fence_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Давайте посмотрим, какие у нас есть типы заборов...")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.BASE_API_URL}fences/types") as response:
            if response.status == 200:
                data = await response.json()
                types = data.get("data", [])

                keyboard = [
                    [InlineKeyboardButton(type_["name"], callback_data=str(type_["id"]))] for type_ in types
                ]

                keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    "Выберите необходимый тип забора",
                    reply_markup=reply_markup
                )

            else:
                await update.message.reply_text("Не удалось получить список типов заборов.")
                return ConversationHandler.END


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_choice = query.data
    if user_choice == "cancel":
        await query.edit_message_text("В следующий раз обязательно все получится")
        return ConversationHandler.END

    context.user_data["type_id"] = user_choice

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.BASE_API_URL}fences?typeId={user_choice}") as response:
            if response.status == 200:
                data = await response.json()
                fences = data.get("data", [])

                keyboard = [
                    [InlineKeyboardButton(fence["name"], callback_data=str(fence["id"]))] for fence in fences
                ]

                keyboard.append([InlineKeyboardButton("Назад", callback_data="go_back")])

                keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    "Выберете подходящий забор из списка",
                    reply_markup=reply_markup
                )

                return CHOOSING_FENCE
            else:
                await query.message.reply_text("Произошла ошибка при получении данных забора.")
                return ConversationHandler.END
