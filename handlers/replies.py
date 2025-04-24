from telegram import Update, ReactionTypeEmoji
from telegram.ext import MessageHandler, filters, CallbackContext
from database import db
from loger.logger import logger
from globals.config import GROUP_CHAT_ID


async def handle_group_reply(update: Update, context: CallbackContext):
    """Обработчик ответов администраторов с сохранением связей сообщений"""
    try:
        # Базовые проверки
        if not (update.message and update.message.reply_to_message):
            logger.debug("Сообщение не является ответом")
            return

        if update.message.chat_id != GROUP_CHAT_ID:
            return

        original_message = update.message.reply_to_message
        thread_id = original_message.message_thread_id

        # Проверка на сообщение бота
        if (
            not original_message.from_user
            or original_message.from_user.id != context.bot.id
        ):
            logger.debug("Ответ не на сообщение бота")
            return

        # Игнорирование системных сообщений о создании топика
        if getattr(original_message, "forum_topic_created", None):
            logger.debug("Ответ на системное сообщение о топике")
            return

        # Получаем информацию о пользователе
        user_data = await db.get_user_by_bot_message(original_message.message_id)
        if not user_data:
            await update.message.reply_text("❌ Диалог не существует")
            logger.error("Топик не найден")
            return

        user_id = user_data["user_id"]
        message_map = context.bot_data.setdefault("message_map", {})
        sent = False
        sent_types = []

        # Обработка текста
        if update.message.text and not sent:
            try:
                sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=update.message.text,
                    reply_to_message_id=message_map.get(original_message.message_id),
                )
                sent = True
                sent_types.append("текст")
                logger.info("Текст отправлен")
            except Exception as e:
                logger.error(f"Ошибка отправки текста: {e}")
                await update.message.reply_text("❌ Ошибка пересылки")
                return

        # Обработка медиаконтента
        media_handlers = [
            ("animation", "send_animation", update.message.animation),
            (
                "photo",
                "send_photo",
                update.message.photo[-1] if update.message.photo else None,
            ),
            ("video", "send_video", update.message.video),
            ("audio", "send_audio", update.message.audio),
            ("voice", "send_voice", update.message.voice),
            ("document", "send_document", update.message.document),
            ("sticker", "send_sticker", update.message.sticker),
            ("video_note", "send_video_note", update.message.video_note),
            ("location", "send_location", update.message.location),
        ]

        for media_type, method_name, media_obj in media_handlers:
            if media_obj and not sent:
                try:
                    method = getattr(context.bot, method_name)
                    kwargs = {
                        "chat_id": user_id,
                        media_type: media_obj.file_id,
                        "reply_to_message_id": message_map.get(
                            original_message.message_id
                        ),
                    }

                    # Специальная обработка для геопозиции
                    if media_type == "location":
                        kwargs["latitude"] = media_obj.latitude
                        kwargs["longitude"] = media_obj.longitude
                        del kwargs["location"]

                    # Добавление подписи для поддерживаемых типов
                    if media_type not in {"sticker", "voice", "video_note", "location"}:
                        kwargs["caption"] = update.message.caption

                    sent_message = await method(**kwargs)
                    sent = True
                    sent_types.append(media_type)
                    logger.info(f"Отправлен {media_type}")
                    break
                except Exception as e:
                    logger.error(f"Ошибка отправки {media_type}: {e}")

        # Сохранение связей сообщений
        if sent:
            # Сохраняем связь между групповым и личным сообщением
            await db.add_message_mapping(
                group_message_id=update.message.message_id,
                user_message_id=sent_message.message_id,
                user_id=user_id,
            )

            # Сохраняем сообщение бота для будущих ответов
            await db.save_bot_message(
                message_id=sent_message.message_id, user_id=user_id, thread_id=thread_id
            )

            # Установка реакции и метрик
            # try:
            #    await update.message.set_reaction([ReactionTypeEmoji("✅")])
            #    await db.execute(
            #        "INSERT INTO metrics (name, value) VALUES ($1, 1) "
            #        "ON CONFLICT (name) DO UPDATE SET value = metrics.value + 1",
            #        "messages_sent"
            #    )
            # except Exception as e:
            #    logger.warning(f"Ошибка реакции: {e}")

            logger.info(f"Успешно отправлено: {', '.join(sent_types)}")

        elif not sent:
            await update.message.reply_text("❌ Неподдерживаемый тип сообщения")
            logger.warning("Неподдерживаемый тип контента")

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text("💥 Системная ошибка")


def register_replies_handler(application):
    """Регистрация обработчика ответов"""
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.REPLY, handle_group_reply)
    )
    logger.info("Обработчик ответов в группе зарегистрирован")
