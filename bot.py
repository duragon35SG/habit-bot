import os
import sqlite3
import nest_asyncio
import asyncio
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ===== Настройки =====
TOKEN = os.getenv("BOT_TOKEN")  # Для локального теста можно прямо вставить токен
DB_FILE = "habit_bot.db"
ADMIN_ID = 815921198  # твой Telegram ID

nest_asyncio.apply()

# ===== База данных =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    active INTEGER DEFAULT 1
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS habits (
                    user_id TEXT,
                    habit_name TEXT,
                    PRIMARY KEY(user_id, habit_name)
                )""")
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (str(user_id),))
    conn.commit()
    conn.close()

def get_all_users(active_only=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if active_only:
        c.execute("SELECT user_id FROM users WHERE active=1")
    else:
        c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# ===== Команды бота =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)
    keyboard = [
        [InlineKeyboardButton("Добавить привычку", callback_data="add_habit")],
        [InlineKeyboardButton("Мои привычки", callback_data="list_habits")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Админ панель", callback_data="admin_panel")])
    await update.message.reply_text("Привет! Выбери действие:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Админ панель =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Сделать рассылку всем", callback_data="broadcast")],
        [InlineKeyboardButton("Статистика пользователей", callback_data="stats")],
        [InlineKeyboardButton("Закрыть панель", callback_data="close_admin")]
    ]
    await query.edit_message_text("Админ панель:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Обработчик кнопок =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "admin_panel" and user_id == ADMIN_ID:
        await admin_panel(update, context)

    elif data == "broadcast" and user_id == ADMIN_ID:
        await query.edit_message_text("Отправь сообщение для рассылки:")
        context.user_data["broadcast_mode"] = True

    elif data == "stats" and user_id == ADMIN_ID:
        users = get_all_users()
        await query.edit_message_text(f"Всего пользователей: {len(users)}")

    elif data == "close_admin":
        await query.edit_message_text("Админ панель закрыта.")

# ===== Сообщения бота =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Проверяем режим рассылки
    if context.user_data.get("broadcast_mode") and user_id == ADMIN_ID:
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
                sent += 1
            except:
                pass
        await update.message.reply_text(f"Сообщение отправлено {sent} пользователям.")
        context.user_data["broadcast_mode"] = False
        return

    # Для обычных пользователей
    await update.message.reply_text("Я получил твоё сообщение!")

# ===== Основной запуск =====
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
