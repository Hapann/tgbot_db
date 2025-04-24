from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
    InputMediaAnimation,
)
from telegram.ext import MessageHandler, filters, CallbackContext, JobQueue
from database import db
from globals.config import GROUP_CHAT_ID, MAX_FILE_SIZE, MAX_VOICE_SIZE
from loger.logger import logger
from typing import Dict, List, Union

# from globals.storage import MAX_FILE_SIZE
import time

# Типы медиа для обработки
MEDIA_TYPES = {
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "document": InputMediaDocument,
    "audio": InputMediaAudio,
    "animation": InputMediaAnimation,
}


async def new_message_handler(update: Update, context: CallbackContext):
    """Универсальный обработчик входящих сообщений"""
    try:
        user = update.effective_user
        message = update.message
        if not message or message.chat.type != "private":
            return

        log_extra = {
            "user_id": user.id,
            "username": user.username or "N/A",
            "message_id": message.message_id,
        }

        user_data = await db.get_user(user.id)
        if not user_data:
            await message.reply_text("❌ Сначала создайте топик через /start")
            logger.warning("Попытка отправки без топика", extra=log_extra)
            return

        thread_id = user_data["thread_id"]
        log_extra["thread_id"] = thread_id

        # Обработка медиагрупп
        if message.media_group_id:
            await _handle_media_group(message, context, user, thread_id)
            return

        # Обработка одиночных сообщений
        await _handle_single_message(message, context, thread_id, user.id, log_extra)

    except Exception as e:
        logger.critical(f"Ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text("💥 Системная ошибка")


async def _handle_media_group(message, context, user, thread_id):
    """Обработчик медиагрупп с временным кешированием"""
    media_group_id = f"{user.id}_{message.media_group_id}"
    media_cache = context.bot_data.setdefault("media_groups", {})

    if media_group_id not in media_cache:
        media_cache[media_group_id] = {
            "messages": [],
            "user_id": user.id,
            "thread_id": thread_id,
            "created": time.time(),
            "caption": message.caption or "",
        }
        # Запускаем обработку через 1 секунду
        context.job_queue.run_once(
            process_media_group, 1, name=media_group_id, data=media_group_id
        )

    media_cache[media_group_id]["messages"].append(message)


async def process_media_group(context: CallbackContext):
    """Обработка собранных медиагрупп"""
    media_group_id = context.job.data
    media_data = context.bot_data["media_groups"].get(media_group_id)

    if not media_data or time.time() - media_data["created"] > 120:
        return

    try:
        media = []
        caption = media_data["caption"]

        for idx, msg in enumerate(media_data["messages"]):
            media_type = next((t for t in MEDIA_TYPES if getattr(msg, t)), None)

            if media_type:
                file_id = _get_file_id(msg)
                media_class = MEDIA_TYPES[media_type]

                # Добавляем подпись только к первому элементу
                media.append(
                    media_class(media=file_id, caption=caption if idx == 0 else None)
                )

        if media:
            sent_messages = await context.bot.send_media_group(
                chat_id=GROUP_CHAT_ID,
                media=media,
                message_thread_id=media_data["thread_id"],
            )

            # Сохранение в БД
            for sent_msg in sent_messages:
                await db.save_bot_message(
                    message_id=sent_msg.message_id,
                    user_id=media_data["user_id"],
                    thread_id=media_data["thread_id"],
                )

            logger.info(f"Медиагруппа из {len(media)} элементов отправлена")

    except Exception as e:
        logger.error(f"Ошибка медиагруппы: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=media_data["user_id"], text="❌ Ошибка отправки медиагруппы"
        )
    finally:
        context.bot_data["media_groups"].pop(media_group_id, None)


def _get_file_id(msg) -> Union[str, None]:
    """Получение file_id из сообщения"""
    for media_type in MEDIA_TYPES:
        if media_obj := getattr(msg, media_type, None):
            if media_type == "photo":
                return media_obj[-1].file_id
            return media_obj.file_id
    return None


async def _handle_single_message(message, context, thread_id, user_id, log_extra):
    """Обработка одиночных сообщений всех типов"""
    content_handlers = {
        "animation": {
            "method": "send_animation",
            "args": lambda: {
                "animation": message.animation.file_id,
                "caption": message.caption,
            },
            "condition": bool(message.animation),
        },
        "voice": {
            "method": "send_voice",
            "args": lambda: {
                "voice": message.voice.file_id,
                "caption": message.caption,
            },
            "condition": bool(
                message.voice and message.voice.file_size <= MAX_VOICE_SIZE
            ),
        },
        "sticker": {
            "method": "send_sticker",
            "args": lambda: {"sticker": message.sticker.file_id},
            "condition": bool(message.sticker),
        },
        "video_note": {
            "method": "send_video_note",
            "args": lambda: {"video_note": message.video_note.file_id},
            "condition": bool(
                message.video_note
                and getattr(message.video_note, "file_size", 0) <= MAX_VOICE_SIZE
            ),
        },
        "location": {
            "method": "send_location",
            "args": lambda: {
                "latitude": message.location.latitude,
                "longitude": message.location.longitude,
                **(
                    {"horizontal_accuracy": message.location.horizontal_accuracy}
                    if message.location.horizontal_accuracy
                    else {}
                ),
                **(
                    {"live_period": message.location.live_period}
                    if message.location.live_period
                    else {}
                ),
            },
            "condition": bool(message.location),
        },
        "photo": {
            "method": "send_photo",
            "args": lambda: {
                "photo": message.photo[-1].file_id,
                "caption": message.caption,
            },
            "condition": bool(message.photo),
        },
        "video": {
            "method": "send_video",
            "args": lambda: {
                "video": message.video.file_id,
                "caption": message.caption,
            },
            "condition": bool(message.video),
        },
        "audio": {
            "method": "send_audio",
            "args": lambda: {
                "audio": message.audio.file_id,
                "caption": message.caption,
                "title": message.audio.title,
                "performer": message.audio.performer,
            },
            "condition": bool(message.audio),
        },
        "document": {
            "method": "send_document",
            "args": lambda: {
                "document": message.document.file_id,
                "caption": message.caption,
            },
            "condition": bool(
                message.document and message.document.file_size <= MAX_FILE_SIZE
            ),
        },
        "text": {
            "method": "send_message",
            "args": lambda: {"text": message.text or message.caption},
            "condition": bool(
                message.text
                or (
                    message.caption
                    and not any(
                        [
                            message.animation,
                            message.sticker,
                            message.photo,
                            message.video,
                            message.audio,
                            message.voice,
                            message.video_note,
                            message.location,
                            message.document,
                        ]
                    )
                )
            ),
        },
    }

    for media_type, handler in content_handlers.items():
        if handler["condition"]:
            try:
                args = {
                    k: v for k, v in handler["args"]().items() if v is not None
                }  # Фильтрация None
                sent_message = await getattr(context.bot, handler["method"])(
                    chat_id=GROUP_CHAT_ID, message_thread_id=thread_id, **args
                )

                await db.save_bot_message(
                    user_id=user_id,
                    thread_id=thread_id,
                    message_id=sent_message.message_id,
                )
                logger.info(
                    f"Сообщение {media_type} отправлено (ID: {sent_message.message_id})",
                    extra=log_extra,
                )
                return

            except Exception as e:
                logger.error(
                    f"Ошибка отправки {media_type}: {str(e)}",
                    exc_info=True,
                    extra=log_extra,
                )
                if "file is too big" in str(e).lower():
                    max_size = (
                        MAX_VOICE_SIZE // (1024 * 1024)
                        if media_type in ["voice", "video_note"]
                        else MAX_FILE_SIZE // (1024 * 1024)
                    )
                    await message.reply_text(
                        f"❌ Файл слишком большой (максимум {max_size}MB)"
                    )
                else:
                    await message.reply_text(f"❌ Ошибка: {str(e)}")
                return


# Регистрация обработчиков
message_handlers = [MessageHandler(filters.ALL & ~filters.COMMAND, new_message_handler)]
