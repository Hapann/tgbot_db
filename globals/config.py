# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT", 5432),  # Значение по умолчанию для порта
}

TOKEN = os.getenv("TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ для документов
MAX_VOICE_SIZE = 20 * 1024 * 1024  # 20 МБ для голосовых/видеокружков

# ID группы для пересылки сообщений
try:
    GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
except (ValueError, TypeError):
    raise ValueError("GROUP_CHAT_ID должен быть целым числом")

if not TOKEN:
    raise EnvironmentError("Не задан BOT_TOKEN в переменных окружения")

if not all(DB_CONFIG.values()):
    missing = [k for k, v in DB_CONFIG.items() if not v]
    raise EnvironmentError(f"Не заданы параметры БД: {', '.join(missing)}")
