# handlers/rules.py
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from loger.logger import logger

RULES_TEXT = (
    "📜 *Правила использования бота:*\n\n"
    "1. Запрещено спамить и флудить\n"
    "2. Не нарушайте законодательство РФ\n"
    "3. Отправляйте вложения по одному\n"
    "4. Текст пишите отдельным сообщением\n"
    "5. Ответ администратора может занять время\n"
    "6. Запрещено требовать флаги/ответы"
)


async def rules_command(update: Update, context: CallbackContext):
    """Обработчик команды /rules"""
    try:
        await update.message.reply_text(
            RULES_TEXT, parse_mode="Markdown", disable_web_page_preview=True
        )
        logger.info(f"Правила отправлены пользователю {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Ошибка отправки правил: {str(e)}")
        await update.message.reply_text("❌ Не удалось загрузить правила")


def register_rules_handler(application):
    """Регистрация обработчика"""
    application.add_handler(CommandHandler("rules", rules_command))
    logger.info("Обработчик /rules зарегистрирован")
