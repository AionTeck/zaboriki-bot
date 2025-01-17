import logging
import aiohttp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import config
from .calculation_states import CalcStates

logger = logging.getLogger(__name__)


async def start_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()

    if update.message:
        await update.message.reply_text("Запускаем расчёт забора...")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("Запускаем расчёт забора...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.BASE_API_URL}fences/types") as response:
                if response.status == 200:
                    data = await response.json()
                    fence_types = data.get("data", [])

                    if not fence_types:
                        await update.effective_message.reply_text(
                            "К сожалению, нет доступных типов забора."
                        )
                        return ConversationHandler.END

                    keyboard = [
                        [InlineKeyboardButton(ft["name"], callback_data=str(ft["id"]))]
                        for ft in fence_types
                    ]

                    keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])

                    markup = InlineKeyboardMarkup(keyboard)
                    await update.effective_message.reply_text(
                        "Выберите тип забора:",
                        reply_markup=markup
                    )
                    return CalcStates.FENCE_TYPE.value
                else:
                    await update.effective_message.reply_text("Ошибка сервера при загрузке типов забора.")
                    return ConversationHandler.END
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        await update.effective_message.reply_text("Проблема с сетью. Попробуйте позже.")
        return ConversationHandler.END


async def choose_fence_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    choice = query.data

    if choice == "main_menu":
        await query.message.reply_text("Возвращаемся в главное меню.")
        context.user_data.clear()
        return ConversationHandler.END

    fence_type_id = int(choice)
    context.user_data["fence_type_id"] = fence_type_id

    await query.message.reply_text(
        f"Отлично.\n"
        "Теперь загрузим популярные параметры высоты..."
    )

    return await ask_fence_popular_specs(update, context)


async def ask_fence_popular_specs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    fence_type_id = context.user_data.get("fence_type_id")
    if not fence_type_id:
        await update.effective_message.reply_text("Ошибка: нет типа забора.")
        return ConversationHandler.END

    try:
        url = f"{config.BASE_API_URL}fences/popular-specs?typeId={fence_type_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    specs = data.get("data", [])

                    if not specs:
                        await update.effective_message.reply_text(
                            "К сожалению, нет популярных высот. Попробуйте начать заново."
                        )
                        return ConversationHandler.END

                    keyboard = []
                    for spec in specs:
                        mm_height = spec["height"]  # например, 2000
                        meters = mm_height / 1000.0
                        text_label = f"{meters} м"
                        callback_data = str(meters)
                        keyboard.append([InlineKeyboardButton(text_label, callback_data=callback_data)])

                    keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])

                    markup = InlineKeyboardMarkup(keyboard)
                    await update.effective_message.reply_text(
                        "Выберите популярную высоту забора:",
                        reply_markup=markup
                    )
                    return CalcStates.FENCE_VARIANTS.value
                else:
                    await update.effective_message.reply_text("Ошибка сервера при получении популярных высот.")
                    return ConversationHandler.END
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        await update.effective_message.reply_text("Не удалось связаться с сервером. Попробуйте позже.")
        return ConversationHandler.END


async def choose_fence_variant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "main_menu":
        await query.message.reply_text("Возвращаемся в главное меню.")
        context.user_data.clear()
        return ConversationHandler.END

    fence_type_id = context.user_data.get("fence_type_id")
    if not fence_type_id:
        await query.message.reply_text("Ошибка: отсутствует выбранный тип забора.")
        return ConversationHandler.END

    height_meters = float(choice)
    context.user_data["fence_height"] = height_meters

    try:
        url = f"{config.BASE_API_URL}fences?typeId={fence_type_id}&height={height_meters}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    fence_variants = data.get("data", [])

                    if not fence_variants:
                        await query.message.reply_text(
                            "К сожалению, по выбранным параметрам ничего не нашлось.\n"
                            "Можете начать заново (нажмите /calc или 'Расчет')."
                        )
                        return ConversationHandler.END

                    context.user_data["fence_variants_map"] = {
                        fv["id"]: fv["name"] for fv in fence_variants
                    }

                    keyboard = [
                        [InlineKeyboardButton(fv["name"], callback_data=str(fv["id"]))]
                        for fv in fence_variants
                    ]

                    keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])

                    markup = InlineKeyboardMarkup(keyboard)
                    await query.message.edit_text(
                        "Выберите вариант забора из списка:",
                        reply_markup=markup
                    )
                    return CalcStates.FENCE_LENGTH.value
                else:
                    await query.message.reply_text("Ошибка сервера при получении вариантов забора.")
                    return ConversationHandler.END
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {e}")
        await query.message.reply_text("Проблема с сетью. Попробуйте позже.")
        return ConversationHandler.END


async def save_fence_variant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "main_menu":
        await query.message.reply_text("Возвращаемся в главное меню.")
        context.user_data.clear()
        return ConversationHandler.END

    fence_variant_id = int(choice)
    context.user_data["fence_variant_id"] = fence_variant_id

    variants_map = context.user_data.get("fence_variants_map", {})

    fence_variant_name = variants_map.get(fence_variant_id, "неизвестный забор")

    await query.message.reply_text(
        f"Отлично! Вы выбрали вариант забора: «{fence_variant_name}».\n"
        "Теперь введите общую длину забора (в метрах)."
    )

    return CalcStates.FENCE_LENGTH.value


async def ask_fence_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text
    try:
        length = float(message_text.replace(",", "."))
        if length <= 0:
            raise ValueError("Length must be positive")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите положительное число, например 25.5")
        return CalcStates.FENCE_LENGTH.value

    context.user_data["fence_length"] = length

    await update.message.reply_text(
        f"Отлично! Длина забора: {length} м.\n"
        "Теперь мы подбираем аксессуары для вашего забора..."
    )

    return await ask_fence_accessories(update, context)


async def ask_fence_accessories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        url = f"{config.BASE_API_URL}accessories?accessoriableType=fence"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    accessories = data.get("data", [])

                    if not accessories:
                        await update.effective_message.reply_text(
                            "Аксессуаров для забора не найдено. Переходим к следующему шагу."
                        )
                        return CalcStates.NEED_GATES.value

                    context.user_data["fence_accessories_map"] = {
                        acc["id"]: acc["name"] for acc in accessories
                    }

                    keyboard = []
                    for acc in accessories:
                        btn_text = acc["name"]
                        btn_data = str(acc["id"])  # callback_data = ID
                        keyboard.append([InlineKeyboardButton(btn_text, callback_data=btn_data)])

                    keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])

                    markup = InlineKeyboardMarkup(keyboard)

                    if "fence_accessories_chosen" not in context.user_data:
                        context.user_data["fence_accessories_chosen"] = []

                    await update.effective_message.reply_text(
                        "Выберите аксессуар (каждый раз после выбора введите количество), "
                        "или нажмите «Готово»:",
                        reply_markup=markup
                    )
                    return CalcStates.FENCE_ACCESSORIES.value
                else:
                    await update.effective_message.reply_text(
                        "Ошибка сервера при получении списка аксессуаров. Переходим дальше."
                    )
                    return CalcStates.NEED_GATES.value
    except aiohttp.ClientError as e:
        logger.error(f"Network error (accessories/fence): {e}")
        await update.effective_message.reply_text("Проблема с сетью. Пропускаем выбор аксессуаров.")
        return CalcStates.NEED_GATES.value


async def handle_fence_accessory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    choice = query.data
    if choice == "done":
        chosen_list = context.user_data.get("fence_accessories_chosen", [])
        if chosen_list:
            text = "Вы выбрали аксессуары:\n"
            acc_map = context.user_data.get("fence_accessories_map", {})
            for item in chosen_list:
                acc_id = item["id"]
                qty = item["quantity"]
                name = acc_map.get(acc_id, str(acc_id))
                text += f"• {name} x {qty}\n"
            await query.message.reply_text(text)
        else:
            await query.message.reply_text("Вы не выбрали ни одного аксессуара.")

        return CalcStates.NEED_GATES.value

    acc_id = int(choice)
    context.user_data["current_accessory_id"] = acc_id
    acc_map = context.user_data.get("fence_accessories_map", {})
    acc_name = acc_map.get(acc_id, "неизвестный аксессуар")

    await query.message.reply_text(
        f"Сколько штук «{acc_name}» вам нужно? Введите число."
    )

    return CalcStates.FENCE_ACCESSORIES_QUANTITY.value


async def handle_fence_accessory_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    try:
        qty = float(text.replace(",", "."))
        if qty <= 0:
            raise ValueError("Quantity must be > 0")
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите положительное число, например '2' или '5'."
        )
        return CalcStates.FENCE_ACCESSORIES_QUANTITY.value

    acc_id = context.user_data.get("current_accessory_id")
    if not acc_id:
        await update.message.reply_text("Неизвестный аксессуар, попробуйте заново.")
        return await ask_fence_accessories(update, context)

    chosen_list = context.user_data.get("fence_accessories_chosen", [])
    chosen_list.append({
        "id": acc_id,
        "quantity": qty
    })
    context.user_data["fence_accessories_chosen"] = chosen_list

    acc_map = context.user_data.get("fence_accessories_map", {})
    acc_name = acc_map.get(acc_id, "неизвестный аксессуар")
    await update.message.reply_text(
        f"Добавлено: {acc_name} x {qty}.\n"
        "Если хотите выбрать ещё аксессуары — снова нажмите на нужный пункт.\n"
        "Или нажмите «Готово»."
    )

    return await ask_fence_accessories(update, context)