# handlers/unknown.py
from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackContext
from loger.logger import logger

async def unknown_command(update: Update, context: CallbackContext):
    """Обработчик неизвестных команд"""
    try:
        await update.message.reply_text(
            "❌ Неизвестная команда!\n"
            "Доступные команды:\n"
            "/start - Начать диалог\n"
            "/rules - Правила использования"
        )
        logger.warning(f"Неизвестная команда от {update.effective_user.id}: {update.message.text}")
    except Exception as e:
        logger.error(f"Ошибка обработки неизвестной команды: {str(e)}")

def register_unknown_handler(application):
    """Регистрация обработчика"""
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    logger.info("Обработчик неизвестных команд зарегистрирован")