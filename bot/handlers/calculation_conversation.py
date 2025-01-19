import logging
import aiohttp
import asyncio
import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
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
                        btn_data = str(acc["id"])
                        keyboard.append([InlineKeyboardButton(btn_text, callback_data=btn_data)])

                    keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])

                    markup = InlineKeyboardMarkup(keyboard)

                    if "fence_accessories_chosen" not in context.user_data:
                        context.user_data["fence_accessories_chosen"] = []

                    await update.effective_message.reply_text(
                        "Выберите аксессуар для вашего забора (каждый раз после выбора введите количество), "
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

        return await ask_need_gates(update, context)

    acc_id = int(choice)
    context.user_data["current_fence_accessory_id"] = acc_id

    try:
        url = f"{config.BASE_API_URL}accessories/{acc_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    acc_data = data.get("data", {})

                    acc_name = acc_data.get("name", "неизвестный аксессуар")
                    specs_list = acc_data.get("specs", [])

                    context.user_data["current_fence_accessory_name"] = acc_name

                    if not specs_list:
                        await query.message.reply_text(
                            f"Для «{acc_name}» нет характеристик. Сколько штук вам нужно?"
                        )
                        return CalcStates.FENCE_ACCESSORIES_QUANTITY.value
                    elif len(specs_list) == 1:
                        only_spec = specs_list[0]
                        spec_id = only_spec["spec_id"]
                        dimension = only_spec["dimension"]
                        context.user_data["current_spec_id"] = spec_id
                        context.user_data["current_spec_dimension"] = dimension

                        await query.message.reply_text(
                            f"Вы выбрали «{acc_name}» ({dimension}). Сколько штук вам нужно?"
                        )
                        return CalcStates.FENCE_ACCESSORIES_QUANTITY.value
                    else:
                        specs_map = {}
                        for spec in specs_list:
                            sp_id = spec["spec_id"]
                            sp_dim = spec["dimension"]
                            specs_map[sp_id] = sp_dim

                        context.user_data["current_specs_map"] = specs_map

                        keyboard = []
                        for spec in specs_list:
                            btn_data = f"spec_{spec['spec_id']}"
                            keyboard.append([InlineKeyboardButton(
                                spec["dimension"],
                                callback_data=btn_data
                            )])

                        await query.message.reply_text(
                            f"Вы выбрали «{acc_name}».\nТеперь выберите характеристику:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        return CalcStates.FENCE_ACCESSORY_SPECS.value
                else:
                    await query.message.reply_text("Ошибка при получении данных аксессуара.")
                    return CalcStates.FENCE_ACCESSORIES.value
    except aiohttp.ClientError as e:
        logger.error(f"Network error (GET /accessories/{acc_id}): {e}")
        await query.message.reply_text("Проблема с сетью. Попробуйте позже.")
        return CalcStates.FENCE_ACCESSORIES.value


async def handle_fence_accessory_spec_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if not choice.startswith("spec_"):
        await query.message.reply_text("Неверный выбор спецификации.")
        return CalcStates.FENCE_ACCESSORY_SPECS.value

    spec_id_str = choice[len("spec_"):]
    spec_id = int(spec_id_str)

    specs_map = context.user_data.get("current_specs_map", {})
    dimension = specs_map.get(spec_id, "неизвестная характеристика")

    context.user_data["current_spec_id"] = spec_id
    context.user_data["current_spec_dimension"] = dimension

    acc_name = context.user_data.get("current_fence_accessory_name", "неизвестный аксессуар")

    await query.message.reply_text(
        f"Вы выбрали «{acc_name}» ({dimension}). Сколько штук вам нужно?"
    )

    return CalcStates.FENCE_ACCESSORIES_QUANTITY.value


async def handle_fence_accessory_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    try:
        qty = int(text)
        if qty <= 0:
            raise ValueError("Quantity must be > 0")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите положительное число")
        return CalcStates.FENCE_ACCESSORIES_QUANTITY.value

    acc_id = context.user_data.get("current_fence_accessory_id")
    acc_name = context.user_data.get("current_fence_accessory_name", "неизвестный аксессуар")
    spec_id = context.user_data.get("current_spec_id")
    dimension = context.user_data.get("current_spec_dimension", "неизвестная характеристика")

    if not acc_id:
        await update.message.reply_text("Неизвестный аксессуар, попробуйте заново.")
        return await ask_fence_accessories(update, context)

    chosen_list = context.user_data.get("fence_accessories_chosen", [])

    chosen_list.append({
        "id": acc_id,
        "spec_id": spec_id,
        "quantity": qty
    })

    context.user_data["fence_accessories_chosen"] = chosen_list

    msg = f"Добавлено: {acc_name}"
    if dimension:
        msg += f" ({dimension})"
    msg += f" x {qty}."

    await update.message.reply_text(
        msg + "\nЕсли хотите выбрать ещё аксессуары, нажмите на нужный пункт.\n"
              "Или нажмите «Готово»."
    )

    return await ask_fence_accessories(update, context)


async def ask_need_gates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="gates_yes"),
            InlineKeyboardButton("Нет", callback_data="gates_no"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "Нужны ли вам ворота?",
        reply_markup=markup
    )
    return CalcStates.NEED_GATES.value


async def handle_need_gates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    choice = query.data
    if choice == "gates_yes":
        context.user_data["need_gates"] = True
        return await ask_gate_types(update, context)
    elif choice == "gates_no":
        context.user_data["need_gates"] = False
        await query.message.reply_text("Окей, идём без ворот.")
        return CalcStates.MOUNTING_TYPE.value
    else:
        await query.message.reply_text("Неверный ответ. Выберите 'Да' или 'Нет'.")
        return CalcStates.NEED_GATES.value


async def ask_gate_types(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = f"{config.BASE_API_URL}gates/types"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            gate_types = data["data"]

            context.user_data["gate_types_map"] = {
                gt["id"]: gt["name"] for gt in gate_types
            }

            keyboard = [
                [InlineKeyboardButton(gt["name"], callback_data=str(gt["id"]))]
                for gt in gate_types
            ]

            markup = InlineKeyboardMarkup(keyboard)

            await update.effective_message.reply_text(
                "Выберите тип ворот:",
                reply_markup=markup
            )
            return CalcStates.GATE_TYPE.value


async def handle_gate_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    gate_type_id = int(query.data)
    context.user_data["gate_type_id"] = gate_type_id

    gate_types_map = context.user_data.get("gate_types_map", {})
    gate_type_name = gate_types_map.get(gate_type_id, "неизвестные ворота")

    await query.message.reply_text(
        f"Вы выбрали ворота {gate_type_name}. Теперь загрузим популярные размеры..."
    )
    return await ask_gate_popular_specs_for_gates(update, context)


async def ask_gate_popular_specs_for_gates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gate_type_id = context.user_data["gate_type_id"]

    url = f"{config.BASE_API_URL}gates/popular-specs?typeId={gate_type_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            specs_data = data["data"]  # не пуст, по условию

            keyboard = []
            for spec in specs_data:
                mm_height = spec["height"]
                mm_width = spec["width"]
                h_m = mm_height / 1000.0
                w_m = mm_width / 1000.0
                text_label = f"{h_m} м x {w_m} м"
                callback_data = f"size_{h_m}x{w_m}"
                keyboard.append([InlineKeyboardButton(text_label, callback_data=callback_data)])

            markup = InlineKeyboardMarkup(keyboard)

            await update.effective_message.reply_text(
                "Выберите популярные размеры ворот (в метрах):",
                reply_markup=markup
            )
            return CalcStates.GATE_POPULAR_SPECS.value


async def handle_gate_size_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    choice = query.data
    gate_type_id = context.user_data["gate_type_id"]

    if not choice.startswith("size_"):
        await query.message.reply_text("Неверный формат. Попробуйте снова.")
        return CalcStates.GATE_POPULAR_SPECS.value

    size_part = choice[len("size_"):]  # например "3.0x1.5"
    h_str, w_str = size_part.split("x")
    h_m = float(h_str)
    w_m = float(w_str)

    context.user_data["gate_height"] = h_m
    context.user_data["gate_width"] = w_m

    url = f"{config.BASE_API_URL}gates?typeId={gate_type_id}&height={h_m}&width={w_m}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            gate_variants = data["data"]  # по условию не пусто

            context.user_data["gate_variants_map"] = {
                gv["id"]: gv["name"] for gv in gate_variants
            }
            keyboard = [
                [InlineKeyboardButton(gv["name"], callback_data=str(gv["id"]))]
                for gv in gate_variants
            ]
            keyboard.append([InlineKeyboardButton("Без ворот", callback_data="no_gate_variant")])

            await query.message.edit_text(
                "Выберите конкретную модель ворот:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CalcStates.GATE_VARIANTS.value


async def handle_chosen_gate_variant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    choice = query.data
    if choice == "no_gate_variant":
        context.user_data["gate_variant_id"] = None
        await query.message.reply_text("Окей, без ворот. Идём дальше.")
        return CalcStates.MOUNTING_TYPE.value

    gate_variant_id = int(choice)
    context.user_data["gate_variant_id"] = gate_variant_id

    gate_map = context.user_data["gate_variants_map"]
    gate_name = gate_map.get(gate_variant_id, "неизвестные ворота")

    await query.message.reply_text(
        f"Вы выбрали: {gate_name}.\nНужна ли автоматика к воротам?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Да", callback_data="automation_yes"),
                InlineKeyboardButton("Нет", callback_data="automation_no")
            ]
        ])
    )
    return CalcStates.GATE_AUTOMATION.value


async def handle_gate_automation_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "automation_yes":
        context.user_data["gate_automation"] = True
        await query.message.reply_text("Автоматика выбрана.")
    elif choice == "automation_no":
        context.user_data["gate_automation"] = False
        await query.message.reply_text("Окей, без автоматики.")
    else:
        await query.message.reply_text("Неверный выбор. Попробуйте снова.")
        return CalcStates.GATE_AUTOMATION.value

    await query.message.reply_text("Хорошо! Теперь давайте выберем аксессуары для ворот...")
    return await ask_gate_accessories(update, context)


async def ask_gate_accessories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        url = f"{config.BASE_API_URL}accessories?accessoriableType=gate"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    accessories = data.get("data", [])

                    context.user_data["gate_accessories_map"] = {
                        acc["id"]: acc["name"] for acc in accessories
                    }

                    keyboard = []
                    for acc in accessories:
                        btn_text = acc["name"]
                        btn_data = str(acc["id"])  # callback_data
                        keyboard.append([InlineKeyboardButton(btn_text, callback_data=btn_data)])

                    keyboard.append([InlineKeyboardButton("Готово", callback_data="done")])

                    markup = InlineKeyboardMarkup(keyboard)

                    if "gate_accessories_chosen" not in context.user_data:
                        context.user_data["gate_accessories_chosen"] = []

                    await update.effective_message.reply_text(
                        "Выберите аксессуар к воротам (после выбора характеристики/количества можно повторять) "
                        "или нажмите «Готово»:",
                        reply_markup=markup
                    )
                    return CalcStates.GATE_ACCESSORIES.value
                else:
                    await update.effective_message.reply_text(
                        "Ошибка сервера при получении списка аксессуаров для ворот. Пропустим аксессуары."
                    )
                    return CalcStates.MOUNTING_TYPE.value
    except aiohttp.ClientError as e:
        logger.error(f"Network error (GET /accessories gate): {e}")
        await update.effective_message.reply_text("Проблема с сетью. Пропустим аксессуары.")
        return CalcStates.MOUNTING_TYPE.value


async def handle_gate_accessory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "done":
        chosen_list = context.user_data.get("gate_accessories_chosen", [])
        if chosen_list:
            text = "Вы выбрали аксессуары к воротам:\n"
            map_ = context.user_data.get("gate_accessories_map", {})
            for item in chosen_list:
                acc_id = item["id"]
                qty = item["quantity"]
                name = map_.get(acc_id, f"ID={acc_id}")
                text += f"• {name} x {qty}\n"
            await query.message.reply_text(text)
        else:
            await query.message.reply_text("Вы не выбрали ни одного аксессуара для ворот.")

        return await ask_mounting_type(update, context)

    acc_id = int(choice)
    context.user_data["current_gate_accessory_id"] = acc_id

    try:
        url = f"{config.BASE_API_URL}accessories/{acc_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    acc_data = data.get("data", {})
                    acc_name = acc_data.get("name", "неизвестный аксессуар")
                    specs_list = acc_data.get("specs", [])

                    context.user_data["current_gate_accessory_name"] = acc_name

                    if not specs_list:
                        await query.message.reply_text(
                            f"Для «{acc_name}» нет характеристик. Сколько штук вам нужно?"
                        )
                        return CalcStates.GATE_ACCESSORIES_QUANTITY.value
                    elif len(specs_list) == 1:
                        only_spec = specs_list[0]
                        spec_id = only_spec["spec_id"]
                        dimension = only_spec["dimension"]
                        context.user_data["current_spec_id"] = spec_id
                        context.user_data["current_spec_dimension"] = dimension

                        await query.message.reply_text(
                            f"Вы выбрали «{acc_name}» ({dimension}). Сколько штук вам нужно?"
                        )
                        return CalcStates.GATE_ACCESSORIES_QUANTITY.value
                    else:
                        specs_map = {}
                        for spec in specs_list:
                            specs_map[spec["spec_id"]] = spec["dimension"]
                        context.user_data["current_specs_map"] = specs_map

                        keyboard = []
                        for spec in specs_list:
                            btn_data = f"spec_{spec['spec_id']}"
                            keyboard.append([InlineKeyboardButton(
                                spec["dimension"], callback_data=btn_data
                            )])

                        await query.message.reply_text(
                            f"Вы выбрали «{acc_name}».\nТеперь выберите характеристику:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        return CalcStates.GATE_ACCESSORY_SPECS.value
                else:
                    await query.message.reply_text("Ошибка при получении данных аксессуара.")
                    return CalcStates.GATE_ACCESSORIES.value
    except aiohttp.ClientError as e:
        logger.error(f"Network error get accessory: {e}")
        await query.message.reply_text("Проблема с сетью. Попробуйте позже.")
        return CalcStates.GATE_ACCESSORIES.value


async def handle_gate_accessory_spec_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if not choice.startswith("spec_"):
        await query.message.reply_text("Неверный выбор спецификации.")
        return CalcStates.GATE_ACCESSORY_SPECS.value

    spec_id_str = choice[len("spec_"):]
    spec_id = int(spec_id_str)

    specs_map = context.user_data.get("current_specs_map", {})
    dimension = specs_map.get(spec_id, "неизвестная характеристика")

    context.user_data["current_spec_id"] = spec_id
    context.user_data["current_spec_dimension"] = dimension

    acc_name = context.user_data.get("current_gate_accessory_name", "неизвестный аксессуар")

    await query.message.reply_text(
        f"Вы выбрали «{acc_name}» ({dimension}). Сколько штук вам нужно?"
    )

    return CalcStates.GATE_ACCESSORIES_QUANTITY.value


async def handle_gate_accessory_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    try:
        qty = int(text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое положительное число.")
        return CalcStates.GATE_ACCESSORIES_QUANTITY.value

    acc_id = context.user_data.get("current_gate_accessory_id")
    acc_name = context.user_data.get("current_gate_accessory_name", "неизвестный акс")
    spec_id = context.user_data.get("current_spec_id")
    dimension = context.user_data.get("current_spec_dimension")

    chosen_list = context.user_data.get("gate_accessories_chosen", [])

    chosen_list.append({
        "id": acc_id,
        "spec_id": spec_id,
        "quantity": qty
    })

    context.user_data["gate_accessories_chosen"] = chosen_list

    msg = f"Добавлено: {acc_name}"
    if dimension:
        msg += f" ({dimension})"
    msg += f" x {qty}."

    await update.message.reply_text(
        msg + "\nЕсли хотите выбрать ещё аксессуары, нажмите на нужный пункт.\n"
              "Или нажмите «Готово»."
    )

    return await ask_gate_accessories(update, context)


async def ask_mounting_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        url = f"{config.BASE_API_URL}mountings"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    mountings = data.get("data", [])

                    context.user_data["mountings_map"] = {
                        m["id"]: m["name"] for m in mountings
                    }

                    keyboard = [
                        [InlineKeyboardButton(m["name"], callback_data=str(m["id"]))]
                        for m in mountings
                    ]
                    markup = InlineKeyboardMarkup(keyboard)

                    await update.effective_message.reply_text(
                        "Выберите тип монтажа:",
                        reply_markup=markup
                    )
                    return CalcStates.MOUNTING_TYPE.value
                else:
                    await update.effective_message.reply_text(
                        "Ошибка сервера при получении типов монтажа."
                    )
                    return CalcStates.END.value
    except aiohttp.ClientError as e:
        logger.error(f"Network error (GET /mountings): {e}")
        await update.effective_message.reply_text("Проблема с сетью. Завершаем.")
        return CalcStates.END.value


async def handle_mounting_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    mounting_id = int(choice)
    context.user_data["mounting_id"] = mounting_id

    mountings_map = context.user_data.get("mountings_map", {})
    mounting_name = mountings_map.get(mounting_id, "неизвестный монтаж")

    await query.message.reply_text(f"Вы выбрали монтаж: {mounting_name}.\nТеперь формируем итог...")

    # Переходим к финальному шагу
    return await final_calculation(update, context)


async def final_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    fence_type_id = context.user_data.get("fence_type_id")
    fence_variant_id = context.user_data.get("fence_variant_id")
    fence_length = context.user_data.get("fence_length")
    fence_accessories = context.user_data.get("fence_accessories_chosen", [])

    need_gates = context.user_data.get("need_gates")
    gate_type_id = context.user_data.get("gate_type_id")
    gate_variant_id = context.user_data.get("gate_variant_id")
    gate_automation = context.user_data.get("gate_automation", False)
    gate_accessories = context.user_data.get("gate_accessories_chosen", [])

    mounting_id = context.user_data.get("mounting_id")

    report_id = str(update.effective_user.id) + '_' + str(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))

    post_data = {
        "fence": {
            "typeId": fence_type_id,
            "variantId": fence_variant_id,
            "length": fence_length,
            "accessories": fence_accessories,
        },
        "gates": {
            "needGates": need_gates,
            "typeId": gate_type_id,
            "variantId": gate_variant_id,
            "automation": gate_automation,
            "accessories": gate_accessories,
        },
        "mountingId": mounting_id,
        "report_id": report_id
    }

    try:
        url = f"{config.BASE_API_URL}calculations"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=post_data) as response:
                if response.status == 200:
                    await update.effective_message.reply_text(
                        "Спасибо! Ваш отчет формируется. Это займет несколько минут."
                    )
                    await asyncio.create_task(check_report_status(report_id, update, context))
                else:
                    await update.effective_message.reply_text(
                        f"Ошибка сервера при сохранении. Попробуйте позже."
                    )
    except aiohttp.ClientError as e:
        logger.error(f"Network error final_calculation: {e}")
        await update.effective_message.reply_text("Сетевая ошибка при сохранении. Попробуйте позже.")

    context.user_data.clear()
    return ConversationHandler.END


async def check_report_status(report_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = f"{config.BASE_API_URL}reports/{report_id}/status"
        for _ in range(30):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        if status_data["status"] == "ready":
                            pdf_url = status_data["pdfUrl"]
                            async with session.get(pdf_url) as pdf_response:
                                if pdf_response.status == 200:
                                    pdf_file = await pdf_response.read()
                                    await update.effective_message.reply_document(
                                        document=pdf_file,
                                        filename="report.pdf",
                                        caption="Ваш отчет готов!"
                                    )
                                    return
                    elif response.status != 202:
                        logger.warning(f"Unexpected status code {response.status}")
                        break
            await asyncio.sleep(10)
    except aiohttp.ClientError as e:
        logger.error(f"Network error in check_report_status: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in check_report_status: {e}")

