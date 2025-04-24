import asyncpg
import os
from typing import Optional
from loger.logger import logger


class Database:
    def __init__(self):
        self.pool = None  # Поле инициализируется позже в методе connect()

    async def is_connected(self):
        return self.pool is not None and not self.pool._closed

    async def connect(self):
        """Подключение к PostgreSQL с автосозданием БД и таблиц"""
        try:
            # Подключаемся к основной базе данных
            sys_pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                database=os.getenv("POSTGRES_DB"),
            )

            # Проверяем наличие нужной базы данных
            async with sys_pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    os.getenv("POSTGRES_DB"),
                )
                if not exists:
                    await conn.execute(f"CREATE DATABASE {os.getenv('POSTGRES_DB')}")
                    logger.info("✅ База данных создана")

            # Закрываем временный пул
            await sys_pool.close()

            # Создаем конечный пул соединений с реальной базой данных
            self.pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                database=os.getenv("POSTGRES_DB"),
            )

            # Создание необходимых таблиц
            await self._create_tables()

        except Exception as e:
            logger.critical(f"❌ Ошибка подключения: {e}")
            raise

    async def _create_tables(self):
        """Создание всех нужных таблиц"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    thread_id INT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Таблица связей между сообщениями
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS message_map (
                    group_message_id INT,
                    user_message_id INT,
                    user_id BIGINT REFERENCES users(user_id),
                    PRIMARY KEY (group_message_id, user_id)
                );
                """
            )

            # Таблица сообщений бота
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_messages (
                    message_id INT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    thread_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Таблица медиагрупп
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_groups (
                    media_group_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    async def save_bot_message(self, message_id: int, user_id: int, thread_id: int):
        """Сохраняет сообщение бота в базу данных."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_messages (message_id, user_id, thread_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (message_id) DO NOTHING
                """,
                message_id,
                user_id,
                thread_id,
            )

    async def get_user_by_bot_message(self, message_id: int) -> Optional[dict]:
        """Возвращает пользователя по идентификатору сообщения бота."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT u.* FROM users u
                JOIN bot_messages bm ON u.user_id = bm.user_id
                WHERE bm.message_id = $1
                """,
                message_id,
            )

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Возвращает пользователя по его идентификатору."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )

    async def get_user_by_thread(self, thread_id: int) -> Optional[dict]:
        """Возвращает пользователя по идентификатору потока."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE thread_id = $1", thread_id
            )

    async def create_user(self, user_id: int, username: str, thread_id: int) -> None:
        """Создает запись о новом пользователе."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, thread_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id,
                username,
                thread_id,
            )

    async def add_message_mapping(
        self, group_message_id: int, user_message_id: int, user_id: int
    ) -> None:
        """Добавляет связь между групповым и личным сообщением."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO message_map 
                (group_message_id, user_message_id, user_id)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                group_message_id,
                user_message_id,
                user_id,
            )

    async def check_media_group(self, media_group_id: str) -> Optional[int]:
        """Проверяет существование медиагруппы."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT 1 FROM media_groups WHERE media_group_id = $1", media_group_id
            )

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Соединение с базой данных закрыто")

    async def get_message_mapping(
        self, group_message_id: int, user_id: int
    ) -> Optional[int]:
        """Получает связанное личное сообщение по идентификатору группы и пользователя."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT user_message_id FROM message_map "
                "WHERE group_message_id = $1 AND user_id = $2",
                group_message_id,
                user_id,
            )

    async def execute(self, query: str, *args):
        """Выполняет SQL-запрос."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def create_tables(self):
        """Создание необходимых таблиц"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    content TEXT,
                    file_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """
            )


# Глобальная инстансация экземпляра базы данных
db = Database()
