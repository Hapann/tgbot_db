# handlers/start.py
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from database import db
from globals.config import GROUP_CHAT_ID
from loger.logger import logger


async def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    username = user.username or f"User_{user_id}"
    log_extra = {"user_id": user_id}

    try:
        # Проверка существующего пользователя
        existing_user = await db.get_user(user_id)
        if existing_user:
            await update.message.reply_text("🚫 У вас уже есть активный диалог!")
            logger.info("Повторный /start", extra=log_extra)
            return

        # Создание топика
        chat = await context.bot.get_chat(GROUP_CHAT_ID)
        topic = await chat.create_forum_topic(name=f"Диалог с {username}")

        # Сохранение в базу
        await db.create_user(
            user_id=user_id, username=username, thread_id=topic.message_thread_id
        )

        await update.message.reply_text("🎉 Диалог создан! Задавайте вопросы здесь.")
        logger.info("Новый пользователь", extra=log_extra)

    except Exception as e:
        logger.critical(f"Ошибка: {e}", exc_info=True, extra=log_extra)
        await update.message.reply_text("💥 Ошибка при создании диалога")


def register_start_handler(application):
    application.add_handler(CommandHandler("start", start_command))
    logger.info("Обработчик /start зарегистрирован")
