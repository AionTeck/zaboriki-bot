import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Произошла ошибка при обработке обновления: {context.error}")
