import logging
from pathlib import Path
import sys
import io

# Принудительная настройка кодировки системы
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Создание директорий
Path("logs").mkdir(exist_ok=True)


# Основной логгер
logger = logging.getLogger("Bot")
logger.setLevel(logging.DEBUG)

# Форматтер с UTF-8
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Обработчики с UTF-8
debug_handler = logging.FileHandler("logs/debug.log", encoding="utf-8")
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

info_handler = logging.FileHandler("logs/info.log", encoding="utf-8")
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Добавление обработчиков
logger.addHandler(debug_handler)
logger.addHandler(info_handler)
logger.addHandler(console_handler)

# Настройка библиотек
for lib in [
    "telegram",
    "telegram.ext",
    "telegram.bot",
    "httpcore",
    "httpx",
    "httpcore.http11",
    "httpcore.connection",
]:
    lib_logger = logging.getLogger(lib)
    lib_logger.setLevel(logging.DEBUG)
    lib_logger.addHandler(debug_handler)
    lib_logger.propagate = False

handlers = [
    logging.FileHandler("logs/debug.log", encoding="utf-8"),
    logging.FileHandler("logs/info.log", encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
