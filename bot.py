import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message
import pytz

# --- ТВОИ ДАННЫЕ ---
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@newChapterJob"
MANAGER_USERNAME = "New_Chapterr24"
OTHER_JOBS_CHANNEL = "https://t.me/jobNchapter"
TEMPLATE_TEXT = "Здравствуйте, меня заинтересовал этот слот. Могу ли я приступить к его выполнению, и что для этого требуется?"

CLOSED_MESSAGE = (
    "Извините, данный слот устарел или был закрыт, в ближайшее время появится новый ожидайте 😀\n"
    "Хорошего настроения! С уважением команда New Chapter👻"
)

MORNING_MESSAGE = (
    "☀️ Доброе утро, друзья!\n"
    "Вот и ещё один прекрасный рабочий день. Скоро появятся новые слоты.\n"
    "Всем хорошего дня! С уважением, команда New Chapter!"
)

EVENING_MESSAGE = (
    "🌙 Рабочий день подошёл к концу.\n"
    "Т.к. работаем с 8 до 22 МСК, рабочий день вышел. Всем спасибо за выполненную работу!\n"
    "У кого ещё есть задания — ожидаем скриншоты до 23:59 МСК.\n"
    "Всем спокойной ночи! С уважением, команда New Chapter!"
)

ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(uid.strip()) for uid in ADMIN_IDS_STR.split(",") if uid.strip()]
# -------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

active_slots = {}
slot_counter = 1

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS

is_admin = IsAdminFilter()

moscow_tz = pytz.timezone("Europe/Moscow")

async def scheduler():
    while True:
        now = datetime.now(moscow_tz)
        morning_target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= morning_target:
            morning_target += timedelta(days=1)
        evening_target = now.replace(hour=22, minute=30, second=0, microsecond=0)
        if now >= evening_target:
            evening_target += timedelta(days=1)

        next_time = min(morning_target, evening_target)
        sleep_seconds = (next_time - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        now_after = datetime.now(moscow_tz)
        if now_after.hour == 8 and now_after.minute == 0:
            try:
                await bot.send_message(CHANNEL_ID, MORNING_MESSAGE)
            except Exception as e:
                logging.error(f"Ошибка утреннего сообщения: {e}")
        elif now_after.hour == 22 and now_after.minute == 30:
            try:
                await bot.send_message(CHANNEL_ID, EVENING_MESSAGE)
            except Exception as e:
                logging.error(f"Ошибка вечернего сообщения: {e}")

async def publish_slot(message: types.Message, slot_name: str, post_text: str):
    global slot_counter
    slot_id = slot_counter
    slot_counter += 1

    active_slots[slot_id] = {
        "message_id": None,
        "command": slot_name,
        "post_text": post_text
    }

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✋ Взять слот",
        callback_data=f"take_slot:{slot_id}"
    )
    builder.button(
        text="📋 Другие задания",
        url=OTHER_JOBS_CHANNEL
    )
    builder.adjust(1)

    sent_msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=post_text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

    active_slots[slot_id]["message_id"] = sent_msg.message_id
    await message.answer(f"✅ Слот «{slot_name}» опубликован в канале! ID: {slot_id}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Я бот для работы со слотами.\n"
        "Чтобы взять задание, перейдите в наш канал @newChapterJob и нажмите кнопку <b>«✋ Взять слот»</b> под интересующим постом.\n\n"
        "После этого ваша заявка будет отправлена менеджеру, и он свяжется с вами.\n\n"
        "Если у вас есть вопросы, обратитесь к @New_Chapterr24.\n\n"
        "Хорошего дня!"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Я бот для работы со слотами.\n"
        "Чтобы взять задание, перейдите в наш канал @newChapterJob и нажмите кнопку <b>«✋ Взять слот»</b> под интересующим постом.\n\n"
        "После этого ваша заявка будет отправлена менеджеру, и он свяжется с вами.\n\n"
        "Если у вас есть вопросы, обратитесь к @New_Chapterr24.\n\n"
        "Хорошего дня!"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("helpadm"), is_admin)
async def cmd_helpadm(message: types.Message):
    text = (
        "🛠 <b>Команды администратора:</b>\n\n"
        "📢 <b>Публикация слотов:</b>\n"
        "/yandex — Яндекс карты (150₽)\n"
        "/google — GOOGLE (50₽)\n"
        "/gis — 2ГИС (50₽)\n"
        "/avito — Авито (700₽)\n"
        "/vk — ВК (50₽)\n"
        "/otzovik — Отзовик (100₽)\n"
        "/doctoru — Docto ru (100₽)\n\n"
        "📋 <b>Управление:</b>\n"
        "/slots — Показать активные слоты\n"
        "/close [номер] — Закрыть слот\n"
        "/closeall — Закрыть все слоты\n\n"
        "ℹ️ <b>Для пользователей:</b> /help"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("yandex"), is_admin)
async def yandex_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: Яндекс карты</b>\n"
        "Задача: Выполнить отзыв/ы Яндекс карты\n"
        "Оплата: 150 руб/шт, после модерации\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "Яндекс карты", text)

@dp.message(Command("google"), is_admin)
async def google_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: GOOGLE</b>\n"
        "Задача: Выполнить отзыв/ы GOOGLE\n"
        "Оплата: 50 руб/шт, Сразу\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "GOOGLE", text)

@dp.message(Command("gis"), is_admin)
async def gis_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: 2ГИС</b>\n"
        "Задача: Выполнить отзыв/ы 2ГИС\n"
        "Оплата: 50 руб/шт, Сразу\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "2ГИС", text)

@dp.message(Command("avito"), is_admin)
async def avito_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: Авито</b>\n"
        "Задача: Выполнить отзыв/ы Авито\n"
        "Оплата: 700 руб/шт, после модерации 1-2 дня\n"
        "Дедлайн: 2 суток с момента принятия слота\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "Авито", text)

@dp.message(Command("vk"), is_admin)
async def vk_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: ВК</b>\n"
        "Задача: Выполнить отзыв/ы ВК\n"
        "Оплата: 50 руб/шт, Сразу\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "ВК", text)

@dp.message(Command("otzovik"), is_admin)
async def otzovik_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: Отзовик</b>\n"
        "Задача: Выполнить отзыв/ы ОТЗОВИК\n"
        "Оплата: 100 руб/шт, после модерации\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "Отзовик", text)

@dp.message(Command("doctoru"), is_admin)
async def doctoru_slot(message: types.Message):
    text = (
        "🔥 <b>Слот: Docto ru</b>\n"
        "Задача: Выполнить отзыв/ы Docto ru\n"
        "Оплата: 100 руб/шт, после модерации\n"
        "Дедлайн: Сегодня до 23:59 (МСК)\n"
        "Требуется человек: До закрытия слота.\n"
        "Нажмите кнопку ниже, чтобы забрать слот."
    )
    await publish_slot(message, "Docto ru", text)

@dp.message(Command("slots"), is_admin)
async def list_slots(message: types.Message):
    if not active_slots:
        await message.answer("Нет активных слотов.")
        return
    lines = ["<b>Активные слоты:</b>"]
    for sid, data in active_slots.items():
        lines.append(f"{sid}. {data['command']} (ID: {data['message_id']})")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@dp.message(Command("close"), is_admin)
async def close_slot(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        slot_id = int(parts[1])
    except:
        await message.answer("Укажите номер слота: /close <номер>\nПосмотреть номера: /slots")
        return

    if slot_id not in active_slots:
        await message.answer(f"Слот с номером {slot_id} не найден.")
        return

    data = active_slots.pop(slot_id)
    try:
        await bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=data["message_id"],
            text=CLOSED_MESSAGE,
            parse_mode=None
        )
        await message.answer(f"✅ Слот {slot_id} («{data['command']}») закрыт.")
    except Exception as e:
        logging.error(f"Не удалось отредактировать сообщение: {e}")
        await message.answer("❌ Ошибка при закрытии слота.")

@dp.message(Command("closeall"), is_admin)
async def close_all_slots(message: types.Message):
    if not active_slots:
        await message.answer("Нет активных слотов для закрытия.")
        return

    count = 0
    for slot_id, data in list(active_slots.items()):
        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=data["message_id"],
                text=CLOSED_MESSAGE,
                parse_mode=None
            )
            count += 1
        except Exception as e:
            logging.error(f"Не удалось закрыть слот {slot_id}: {e}")
        finally:
            active_slots.pop(slot_id, None)

    await message.answer(f"✅ Закрыто слотов: {count}")

@dp.callback_query(F.data.startswith("take_slot:"))
async def process_take_slot(callback: CallbackQuery):
    slot_id = int(callback.data.split(":")[1])

    if slot_id not in active_slots:
        await callback.answer("❌ Этот слот уже неактивен.", show_alert=True)
        return

    slot_data = active_slots[slot_id]
    post_text = slot_data["post_text"]
    user = callback.from_user
    user_mention = f"@{user.username}" if user.username else user.full_name

    message_to_manager = (
        f"📨 <b>Запрос на слот от {user_mention}</b>\n\n"
        f"<i>Слот: {slot_data['command']}</i>\n\n"
        f"<i>Текст поста:</i>\n{post_text}\n\n"
        f"<i>Сообщение от кандидата:</i>\n{TEMPLATE_TEXT}"
    )

    try:
        await bot.send_message(
            chat_id=f"@{MANAGER_USERNAME}",
            text=message_to_manager,
            parse_mode=ParseMode.HTML
        )
        await callback.answer("✅ Ваша заявка отправлена! Менеджер скоро свяжется с вами.", show_alert=True)
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение менеджеру: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже или свяжитесь с менеджером напрямую.", show_alert=True)

    await callback.message.edit_reply_markup(reply_markup=callback.message.reply_markup)

async def main():
    asyncio.create_task(scheduler())
    print("Бот запущен. Ожидаю команды...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
