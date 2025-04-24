# main.py
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from globals.config import TOKEN
from handlers.start import register_start_handler
from handlers.rules import register_rules_handler
from handlers.replies import register_replies_handler
from handlers.messages import new_message_handler
from handlers.unknown import register_unknown_handler
from loger.logger import logger
from database import db
import asyncio
import sys


async def shutdown():
    """Корректное завершение работы"""
    logger.info("🛑 Завершение работы...")
    try:
        if hasattr(application, "updater") and application.updater.running:
            await application.updater.stop()
    except Exception as e:
        logger.error(f"Ошибка при остановке Updater: {str(e)}")

    try:
        if application:
            await application.stop()
    except Exception as e:
        logger.error(f"Ошибка при остановке Application: {str(e)}")

    try:
        # Предполагаем, что db имеет метод is_connected() или атрибут
        if await db.is_connected():
            await db.close()
            logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка закрытия БД: {str(e)}")


async def main():
    global application
    application = None

    try:
        # Инициализация БД (убедитесь, что внутри методов нет логов)
        await db.connect()
        logger.info("✅ База данных подключена")
        await db.create_tables()
        logger.info("✅ Таблицы созданы")

        application = ApplicationBuilder().token(TOKEN).build()

        # Регистрация обработчиков
        register_start_handler(application)
        register_rules_handler(application)
        register_replies_handler(application)
        application.add_handler(
            MessageHandler(
                filters.ChatType.PRIVATE & ~filters.COMMAND,
                new_message_handler,
            )
        )
        register_unknown_handler(application)

        logger.info("🚀 Бот запущен")

        # Запуск polling
        await application.initialize()
        await application.start()
        if application.updater:
            await application.updater.start_polling(drop_pending_updates=True)

        # Ожидание бесконечно (прерывается Ctrl+C)
        await asyncio.Event().wait()

    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
