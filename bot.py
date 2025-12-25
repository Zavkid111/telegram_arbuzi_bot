import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import os

# ==================== НАСТРОЙКИ ====================
TOKEN_BOT = os.environ.get(7966124362:AAGd_QNjB1Sc9gOkR8qEbvEcQx2Qg3gHIQA)  # Telegram токен из Secrets
CHAT_API_KEY = os.environ.get(orNxtK7UWgdQa5LN09mGNyzTjOBbxte2)  # Твой ключ для другого ИИ
ADMIN_ID = 8102275345  # <-- замените на ваш ID
DAILY_REWARD = 5  # 5 арбузов в день
MAX_IMAGES_PER_DAY = 5

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN_BOT)
dp = Dispatcher(bot)

# ==================== БД ====================
conn = sqlite3.connect('arbuz.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    mode TEXT DEFAULT 'none',
    arbuzy INTEGER DEFAULT 0,
    last_daily TEXT,
    images_today INTEGER DEFAULT 0,
    subscribed INTEGER DEFAULT 0
)
''')
conn.commit()

# ==================== КНОПКИ ====================
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("💬 Чат GPT"))
main_kb.add(KeyboardButton("🎨 Генерация картинок"))
main_kb.add(KeyboardButton("👤 Профиль"))
main_kb.add(KeyboardButton("🎁 Ежедневная награда"))

subscription_kb = InlineKeyboardMarkup(row_width=1)
subscription_kb.add(
    InlineKeyboardButton("Подписаться на первый канал", url="https://t.me/my_forward_go_bot?start=_tgr_GiWPX2o1OTMy"),
    InlineKeyboardButton("Подписаться на второй канал", url="https://t.me/gosiripobot?start=_tgr_EyIjbmhhZWRi"),
    InlineKeyboardButton("Проверить подписку", callback_data="check_sub")
)

# ==================== ФУНКЦИИ ====================
def get_user(user_id, username):
    cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?,?)', (user_id, username))
        conn.commit()
        return get_user(user_id, username)
    return user

async def send_main_menu(user_id):
    await bot.send_message(user_id, "Выбери режим работы:", reply_markup=main_kb)

def can_take_daily(user):
    last_daily = user[4]
    if not last_daily:
        return True
    last = datetime.fromisoformat(last_daily)
    return datetime.now() - last >= timedelta(days=1)

def update_daily(user_id):
    cursor.execute('UPDATE users SET arbuzy = arbuzy + ?, last_daily = ? WHERE user_id=?',
                   (DAILY_REWARD, datetime.now().isoformat(), user_id))
    conn.commit()

def add_arbuzy(user_id, amount):
    cursor.execute('UPDATE users SET arbuzy = arbuzy + ? WHERE user_id=?', (amount, user_id))
    conn.commit()

def can_generate_image(user):
    return user[6] < MAX_IMAGES_PER_DAY and user[3] > 0

def update_image_count(user_id):
    cursor.execute('UPDATE users SET images_today = images_today + 1, arbuzy = arbuzy - 1 WHERE user_id=?', (user_id,))
    conn.commit()

def reset_daily_image_count():
    cursor.execute('UPDATE users SET images_today = 0')
    conn.commit()

async def generate_image(prompt):
    """Генерация картинки через SubNP free API (без ключа)"""
    data = {'prompt': prompt, 'model': 'turbo'}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://t2i.mcpcore.xyz/api/free/generate', json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get('url')
    return None

# ==================== ХЭНДЛЕРЫ ====================
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    await bot.send_message(message.from_user.id, f"Привет! Я Arbuz 🍉\nВыбери режим работы", reply_markup=main_kb)

@dp.message_handler(lambda message: message.text == "💬 Чат GPT")
async def chat_mode(message: types.Message):
    cursor.execute('UPDATE users SET mode = ? WHERE user_id=?', ('chat', message.from_user.id))
    conn.commit()
    await bot.send_message(message.from_user.id, "💬 Режим ChatGPT активирован! Отправь сообщение, и я отвечу тебе.")

@dp.message_handler(lambda message: message.text == "🎨 Генерация картинок")
async def image_mode(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    if not user[6]:  # subscribed = 0
        await bot.send_message(message.from_user.id, "Сначала подпишись на каналы, чтобы использовать генерацию картинок!", reply_markup=subscription_kb)
        return
    cursor.execute('UPDATE users SET mode = ? WHERE user_id=?', ('image', message.from_user.id))
    conn.commit()
    await bot.send_message(message.from_user.id, f"🎨 Режим генерации картинок активирован!\nУ тебя {user[3]} арбузов, максимум {MAX_IMAGES_PER_DAY} картинок в день. Отправь описание картинки.")

@dp.message_handler(lambda message: message.text == "👤 Профиль")
async def profile(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    text = f"👤 Профиль:\nАрбузы: {user[3]}\nКартинок сегодня: {user[6]}/{MAX_IMAGES_PER_DAY}\nРежим: {user[2]}"
    await bot.send_message(message.from_user.id, text)

@dp.message_handler(lambda message: message.text == "🎁 Ежедневная награда")
async def daily_reward(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    if not user[6]:
        await bot.send_message(message.from_user.id, "Сначала подпишись на каналы, чтобы получать ежедневные арбузы!", reply_markup=subscription_kb)
        return
    if can_take_daily(user):
        update_daily(message.from_user.id)
        await bot.send_message(message.from_user.id, f"🎁 Ты получил {DAILY_REWARD} арбузов! 🍉")
    else:
        next_time = datetime.fromisoformat(user[4]) + timedelta(days=1)
        await bot.send_message(message.from_user.id, f"⏳ Следующая награда через: {next_time.strftime('%H:%M:%S')}")

@dp.callback_query_handler(lambda c: c.data == 'check_sub')
async def check_subscription(callback_query: types.CallbackQuery):
    cursor.execute('UPDATE users SET subscribed = 1 WHERE user_id=?', (callback_query.from_user.id,))
    conn.commit()
    await bot.send_message(callback_query.from_user.id, "✅ Подписка подтверждена! Теперь можно использовать генерацию картинок.")

@dp.message_handler()
async def handle_text(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    mode = user[2]

    if mode == 'none':
        await send_main_menu(message.from_user.id)
        return

    if mode == 'chat':
        # Запрос к другому ИИ через твой API ключ
        headers = {'Authorization': f'Bearer {CHAT_API_KEY}'}
        data = {'prompt': message.text}
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.example.com/v1/chat', headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    answer = result.get('response', '🤖 Ошибка при получении ответа')
                else:
                    answer = '🤖 Ошибка API чата'
        await bot.send_message(message.from_user.id, answer)
        return

    if mode == 'image':
        if not can_generate_image(user):
            await bot.send_message(message.from_user.id, f"❌ Невозможно сгенерировать картинку. Либо лимит {MAX_IMAGES_PER_DAY} исчерпан, либо нет арбузов.")
            return
        img_url = await generate_image(message.text)
        if img_url:
            update_image_count(message.from_user.id)
            await bot.send_photo(message.from_user.id, img_url)
        else:
            await bot.send_message(message.from_user.id, "❌ Ошибка при генерации картинки.")

# ==================== ЦИКЛ ====================
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.run_forever()
