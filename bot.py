import asyncio
import logging
import os
import threading
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import Flask, Response
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

# Шаблон текста для ссылки (только сумма)
MESSAGE_TEMPLATE = (
    "Здравствуйте, меня интересует слот {slot_name} ({price}). "
    "Обязуюсь отправить скриншот/ы до 23:59 МСК, с правилами ознакомлен."
)

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

# Хранилище активных слотов: ключ = message_id (реальный ID сообщения в Telegram)
active_slots = {}

class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS

is_admin = IsAdminFilter()

# --- Flask для Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return Response(status=200)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- Планировщик авто-сообщений (по МСК) ---
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

# --- Вспомогательная функция отправки слота ---
async def publish_slot(message: types.Message, slot_name: str, post_text: str, price: str):
    # Формируем URL для кнопки
    raw_text = MESSAGE_TEMPLATE.format(slot_name=slot_name, price=price)
    encoded_text = quote(raw_text, safe='')
    url = f"https://t.me/{MANAGER_USERNAME}?text={encoded_text}"

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✋ Взять слот",
        url=url
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

    # Ключ — реальный message_id из Telegram
    msg_id = sent_msg.message_id
    active_slots[msg_id] = {
        "command": slot_name,
        "post_text": post_text
    }
    await message.answer(f"✅ Слот «{slot_name}» опубликован в канале! ID: {msg_id}")

# --- Команды для всех пользователей ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "👋 <b>Привет!</b>\n\n"
        "Я бот для работы со слотами.\n"
        "Чтобы взять задание, перейдите в наш канал @newChapterJob и нажмите кнопку <b>«✋ Взять слот»</b> под интересующим постом.\n\n"
        "После этого откроется чат с менеджером, где уже будет готовый текст заявки. Вам останется только отправить его.\n\n"
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
        "После этого откроется чат с менеджером, где уже будет готовый текст заявки. Вам останется только отправить его.\n\n"
        "Если у вас есть вопросы, обратитесь к @New_Chapterr24.\n\n"
        "Хорошего дня!"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

# --- Команды для администраторов ---
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
        "/slots — Показать активные слоты (с ID)\n"
        "/close [ID] — Закрыть слот по ID\n"
        "/closeall — Закрыть все слоты\n\n"
        "ℹ️ <b>Для пользователей:</b> /help"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

# --- Публикация слотов (только админы) ---
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
    await publish_slot(message, "Яндекс карты", text, "150₽")

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
    await publish_slot(message, "GOOGLE", text, "50₽")

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
    await publish_slot(message, "2ГИС", text, "50₽")

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
    await publish_slot(message, "Авито", text, "700₽")

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
    await publish_slot(message, "ВК", text, "50₽")

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
    await publish_slot(message, "Отзовик", text, "100₽")

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
    await publish_slot(message, "Docto ru", text, "100₽")

# --- Управление слотами (только админы) ---
@dp.message(Command("slots"), is_admin)
async def list_slots(message: types.Message):
    if not active_slots:
        await message.answer("Нет активных слотов.")
        return
    lines = ["<b>Активные слоты (ID = message_id):</b>"]
    for msg_id, data in active_slots.items():
        lines.append(f"🔸 {data['command']} — ID: {msg_id}")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@dp.message(Command("close"), is_admin)
async def close_slot(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        slot_id = int(parts[1])
    except:
        await message.answer("Укажите ID слота: /close <ID>\nПосмотреть ID: /slots")
        return

    if slot_id not in active_slots:
        await message.answer(f"❌ Слот с ID {slot_id} не найден среди активных.\nПроверьте список: /slots")
        return

    data = active_slots.pop(slot_id)
    try:
        await bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=slot_id,
            text=CLOSED_MESSAGE,
            parse_mode=None
        )
        await message.answer(f"✅ Слот «{data['command']}» (ID: {slot_id}) закрыт.")
    except Exception as e:
        logging.error(f"Не удалось отредактировать сообщение {slot_id}: {e}")
        await message.answer("❌ Ошибка при закрытии слота. Возможно, сообщение уже удалено.")

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
                message_id=slot_id,
                text=CLOSED_MESSAGE,
                parse_mode=None
            )
            count += 1
        except Exception as e:
            logging.error(f"Не удалось закрыть слот {slot_id}: {e}")
        finally:
            active_slots.pop(slot_id, None)

    await message.answer(f"✅ Закрыто слотов: {count}")

# --- Точка входа ---
async def main():
    asyncio.create_task(scheduler())
    print("Бот запущен. Ожидаю команды...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    asyncio.run(main())
