import telebot
from telebot import types
import datetime

TOKEN = "8242446491:AAFwVqXnaB_iyJWfgH5HFO5EsPqYHwFwIWk"
ADMIN_ID = 5695898938  # твой Telegram ID

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ------------------- ДАННЫЕ -------------------
vip_users = {}          # user_id: {"until": datetime, "status": "week"/"month"/"forever"}
blocked_users = {}      # user_id: datetime окончания бана
search_queue = []       # очередь на поиск собеседника
chat_pairs = {}         # user_id: partner_id
awaiting_vip_screen = set()  # кто должен отправить скрин после оплаты

# Плохие слова
bad_words = [
    "хуй", "пизда", "ебать", "сука", "блять", "нахуй", "чмо", "мразь", "пидор", "уёбок",
    "даун", "долбоёб", "гондон", "залупа", "шлюха", "проститутка", "мудак", "гандон", "еблан", "идиот",
    "fuck", "shit", "bitch", "asshole", "motherfucker", "cunt", "bastard", "slut", "whore", "faggot",
    "кретин", "ублюдок", "лох", "гнида", "козёл", "чёрт", "тварь", "говно", "ебло", "жопа",
    "сиськи", "жопу", "киску", "попку", "пизду"
]

# ------------------- VIP -------------------
def is_vip(user_id):
    if user_id not in vip_users:
        return False
    if vip_users[user_id]["until"] is None:
        return True
    if datetime.datetime.now() < vip_users[user_id]["until"]:
        return True
    else:
        del vip_users[user_id]
        return False

# ------------------- СТАРТ -------------------
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    search_btn = types.KeyboardButton("🔎 Поиск собеседника")
    vip_btn = types.KeyboardButton("💳 Оплатить VIP")
    help_btn = types.KeyboardButton("ℹ️ Помощь")
    stop_btn = types.KeyboardButton("⛔ Стоп")
    markup.add(search_btn, vip_btn, help_btn, stop_btn)

    text = (
        "Привет👋 Это Анонимный чат!\n\n"
        "Чтобы общаться и найти собеседника, нажми <b>🔎 Поиск собеседника</b>\n"
        "ℹ️ Помощь по боту — /help\n"
        "💎 Чтобы общаться без ограничений, купи VIP — /vip"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

# ------------------- ПОМОЩЬ -------------------
@bot.message_handler(commands=["help"])
def help_menu(message):
    bot.send_message(message.chat.id,
                     "ℹ️ Используй кнопки:\n\n"
                     "🔎 Поиск собеседника — найти нового собеседника\n"
                     "⛔ Стоп — закончить диалог\n"
                     "💳 Оплатить VIP — купить VIP\n\n"
                     "❗ При нарушениях — бан на 1 день (без VIP)")

# ------------------- VIP -------------------
@bot.message_handler(func=lambda msg: msg.text == "💳 Оплатить VIP" or msg.text == "/vip")
def buy_vip(message):
    text = (
        "📌 Тарифы VIP:\n\n"
        "▫️ 1 неделя — 100 ₽\n"
        "▫️ 1 месяц — 350 ₽\n"
        "▫️ Навсегда — 1500 ₽\n\n"
        "💳 Реквизиты для оплаты:\n"
        "<code>2202 2069 0937 4519</code> (Сбербанк)\n\n"
        "После оплаты отправь скриншот сюда ✅"
    )
    awaiting_vip_screen.add(message.chat.id)
    bot.send_message(message.chat.id, text)

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    user_id = message.chat.id
    if user_id in awaiting_vip_screen:
        bot.forward_message(ADMIN_ID, user_id, message.message_id)
        bot.send_message(ADMIN_ID, f"📩 Скрин оплаты от пользователя ID: <code>{user_id}</code>")
        bot.send_message(user_id, "✅ Скрин отправлен админу, ожидай подтверждения!")
        awaiting_vip_screen.remove(user_id)
    else:
        bot.send_message(user_id, "📷 Фото не принимается здесь. Используй только после оплаты VIP!")

@bot.message_handler(commands=["approve"])
def approve_payment(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(ADMIN_ID, "❌ Используй: /approve <user_id> <week|month|forever>")
            return

        user_id = int(parts[1])
        tariff = parts[2]

        if tariff == "week":
            until = datetime.datetime.now() + datetime.timedelta(days=7)
        elif tariff == "month":
            until = datetime.datetime.now() + datetime.timedelta(days=30)
        elif tariff == "forever":
            until = None
        else:
            bot.send_message(ADMIN_ID, "❌ Неверный тариф. week/month/forever")
            return

        vip_users[user_id] = {"until": until, "status": tariff}
        bot.send_message(user_id, f"✅ Тебе выдан VIP ({tariff})! Приятного общения 🎉")
        bot.send_message(ADMIN_ID, f"Выдал VIP {tariff} пользователю {user_id}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"⚠ Ошибка: {e}")

# ------------------- ПОИСК -------------------
@bot.message_handler(func=lambda msg: msg.text == "🔎 Поиск собеседника")
def find_partner(message):
    user_id = message.chat.id

    if user_id in blocked_users and datetime.datetime.now() < blocked_users[user_id]:
        bot.send_message(user_id, "⛔ Ты заблокирован на 1 день за нарушения.")
        return

    if user_id in search_queue or user_id in chat_pairs:
        bot.send_message(user_id, "⏳ Ты уже в поиске или в чате.")
        return

    if search_queue:
        partner_id = search_queue.pop(0)
        if partner_id in blocked_users and datetime.datetime.now() < blocked_users[partner_id]:
            bot.send_message(user_id, "❌ Не удалось найти собеседника, попробуй позже.")
            return

        chat_pairs[user_id] = partner_id
        chat_pairs[partner_id] = user_id

        bot.send_message(user_id, "✅ Собеседник найден!\n\n/next — искать нового\n/stop — закончить диалог")
        bot.send_message(partner_id, "✅ Собеседник найден!\n\n/next — искать нового\n/stop — закончить диалог")
    else:
        search_queue.append(user_id)
        bot.send_message(user_id, "🔎 Поиск собеседника...")

# ------------------- СТОП -------------------
@bot.message_handler(commands=["stop"])
@bot.message_handler(func=lambda msg: msg.text == "⛔ Стоп")
def stop_chat(message):
    user_id = message.chat.id
    if user_id in chat_pairs:
        partner_id = chat_pairs[user_id]
        bot.send_message(partner_id, "❌ Собеседник вышел из чата.")
        del chat_pairs[partner_id]
        del chat_pairs[user_id]
    else:
        bot.send_message(user_id, "❌ Ты не в чате.")

# ------------------- АДМИН-ПАНЕЛЬ -------------------
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 Статистика", "📢 Рассылка")
    markup.add("🔒 Забанить", "🔓 Разбанить")
    markup.add("👁 Онлайн", "⬅️ Выйти")
    bot.send_message(ADMIN_ID, "⚙️ Админ-панель:", reply_markup=markup)

# ------------------- СТАТИСТИКА -------------------
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.text == "📊 Статистика")
def admin_stats(message):
    online_users = len(search_queue) + len(chat_pairs)
    bot.send_message(ADMIN_ID,
                     f"📊 Статистика:\n\n"
                     f"👥 VIP: {len(vip_users)}\n"
                     f"⛔ Бан: {len(blocked_users)}\n"
                     f"🔎 В поиске: {len(search_queue)}\n"
                     f"💬 В чате: {len(chat_pairs)//2}\n"
                     f"🟢 Онлайн: {online_users}")

# ------------------- СПИСОК ОНЛАЙНА -------------------
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.text == "👁 Онлайн")
def admin_online(message):
    online = set(search_queue + list(chat_pairs.keys()))
    if not online:
        bot.send_message(ADMIN_ID, "🟢 Сейчас никого онлайн нет.")
        return

    text = "🟢 Онлайн пользователи:\n\n"
    for uid in online:
        text += f"• <a href='tg://user?id={uid}'>{uid}</a>\n"
    bot.send_message(ADMIN_ID, text, parse_mode="HTML")

# ------------------- КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕМ -------------------
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.text.isdigit())
def admin_user_control(message):
    user_id = int(message.text)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔒 Забанить", callback_data=f"ban_{user_id}"))
    markup.add(types.InlineKeyboardButton("🔓 Разбанить", callback_data=f"unban_{user_id}"))
    markup.add(types.InlineKeyboardButton("⭐ Выдать VIP", callback_data=f"vip_{user_id}"))
    bot.send_message(ADMIN_ID, f"⚙️ Управление пользователем <code>{user_id}</code>",
                     parse_mode="HTML", reply_markup=markup)

# ------------------- ОБРАБОТКА КНОПОК -------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("ban_", "unban_", "vip_")))
def callback_admin(call):
    action, uid = call.data.split("_")
    user_id = int(uid)

    if action == "ban":
        blocked_users[user_id] = datetime.datetime.now() + datetime.timedelta(days=1)
        bot.send_message(ADMIN_ID, f"✅ Пользователь {user_id} забанен на 1 день")
        bot.send_message(user_id, "⛔ Ты был забанен админом на 1 день.")
    elif action == "unban":
        blocked_users.pop(user_id, None)
        bot.send_message(ADMIN_ID, f"✅ Пользователь {user_id} разбанен")
        bot.send_message(user_id, "✅ Админ снял с тебя бан.")
    elif action == "vip":
        vip_users[user_id] = {"until": None, "status": "forever"}
        bot.send_message(ADMIN_ID, f"⭐ Пользователю {user_id} выдан VIP навсегда")
        bot.send_message(user_id, "🎉 Тебе админ выдал VIP навсегда!")

# ------------------- ВЫХОД ИЗ АДМИН-ПАНЕЛИ -------------------
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and msg.text == "⬅️ Выйти")
def admin_exit(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    pay_btn = types.KeyboardButton("💳 Оплатить VIP")
    help_btn = types.KeyboardButton("ℹ️ Помощь")
    search_btn = types.KeyboardButton("🔎 Поиск собеседника")
    stop_btn = types.KeyboardButton("⛔ Стоп")
    markup.add(search_btn, pay_btn, help_btn, stop_btn)
    bot.send_message(ADMIN_ID, "↩️ Ты вышел из админ-панели", reply_markup=markup)

# ------------------- АНТИМАТ + ЧАТ -------------------
@bot.message_handler(func=lambda msg: True)
def chat_handler(message):
    user_id = message.chat.id

    # анти-мат и ссылки
    text = (message.text or "").lower()
    if not is_vip(user_id):
        if any(word in text for word in bad_words) or "http" in text or ".ru" in text or ".com" in text:
            blocked_users[user_id] = datetime.datetime.now() + datetime.timedelta(days=1)
            bot.send_message(user_id, "🚫 Нарушение! Ты заблокирован на 1 день.")
            return

    # если в чате
    if user_id in chat_pairs:
        partner_id = chat_pairs[user_id]
        prefix = "👑 Админ: " if user_id == ADMIN_ID else ""
        bot.send_message(partner_id, prefix + message.text)

# ------------------- ЗАПУСК -------------------
print("Бот запущен...")
bot.infinity_polling()
