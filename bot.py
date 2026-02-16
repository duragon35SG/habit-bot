import os
import sqlite3
import asyncio
from datetime import datetime, date
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")  # В Render: Environment -> BOT_TOKEN

DB_FILE = "habit_bot.db"

# ===== Инициализация базы данных =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            user_id TEXT,
            habit TEXT,
            date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            user_id TEXT PRIMARY KEY,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ===== Функции работы с привычками =====
def add_habit(user_id, habit):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM habits WHERE user_id=? AND habit=? AND date IS NULL", (user_id, habit))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO habits (user_id, habit, date) VALUES (?, ?, ?)", (user_id, habit, None))
    conn.commit()
    conn.close()
    return True

def delete_habit(user_id, habit):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE user_id=? AND habit=?", (user_id, habit))
    conn.commit()
    conn.close()

def get_habits(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT habit FROM habits WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def mark_habit(user_id, habit):
    today = str(date.today())
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM habits WHERE user_id=? AND habit=? AND date=?", (user_id, habit, today))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO habits (user_id, habit, date) VALUES (?, ?, ?)", (user_id, habit, today))
    conn.commit()
    conn.close()
    return True

def get_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT habit, COUNT(date) FROM habits 
        WHERE user_id=? AND date IS NOT NULL 
        GROUP BY habit
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ===== Функции работы с напоминаниями =====
def set_reminder(user_id, time_str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO reminders (user_id, time) VALUES (?, ?)", (user_id, time_str))
    conn.commit()
    conn.close()

def get_reminder(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT time FROM reminders WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_reminders():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, time FROM reminders")
    rows = cursor.fetchall()
    conn.close()
    return rows

# ===== Главное меню =====
def main_menu():
    keyboard = [
        ["➕ Добавить привычку"],
        ["📋 Мои привычки"],
        ["✅ Отметить выполнение"],
        ["🗑 Удалить привычку"],
        ["📊 Статистика"],
        ["⏰ Установить напоминание"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== Старт =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adding"] = False
    context.user_data["setting_reminder"] = False
    await update.message.reply_text(
        "Привет! Я твой трекер привычек 💪",
        reply_markup=main_menu()
    )

# ===== Обработка текста =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.from_user.id)

    # --- Добавление привычки ---
    if text == "➕ Добавить привычку":
        context.user_data["adding"] = True
        await update.message.reply_text("Введите название привычки:", reply_markup=main_menu())
        return

    if context.user_data.get("adding"):
        habit = text.strip()
        if add_habit(user_id, habit):
            await update.message.reply_text(f"'{habit}' добавлено ✅", reply_markup=main_menu())
        else:
            await update.message.reply_text("Такая привычка уже есть.", reply_markup=main_menu())
        context.user_data["adding"] = False
        return

    # --- Показать привычки ---
    if text == "📋 Мои привычки":
        habits = get_habits(user_id)
        if habits:
            msg = "Твои привычки:\n" + "\n".join(f"• {h}" for h in habits)
        else:
            msg = "У тебя пока нет привычек."
        await update.message.reply_text(msg, reply_markup=main_menu())
        return

    # --- Отметить выполнение ---
    if text == "✅ Отметить выполнение":
        habits = get_habits(user_id)
        if not habits:
            await update.message.reply_text("Нет привычек.", reply_markup=main_menu())
            return
        keyboard = [[InlineKeyboardButton(h, callback_data=f"mark|{h}")] for h in habits]
        await update.message.reply_text("Выберите привычку:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # --- Удалить привычку ---
    if text == "🗑 Удалить привычку":
        habits = get_habits(user_id)
        if not habits:
            await update.message.reply_text("Нет привычек для удаления.", reply_markup=main_menu())
            return
        keyboard = [[InlineKeyboardButton(h, callback_data=f"delete|{h}")] for h in habits]
        await update.message.reply_text("Выберите привычку для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # --- Статистика ---
    if text == "📊 Статистика":
        stats = get_stats(user_id)
        if stats:
            msg = "Статистика:\n" + "\n".join(f"{h}: {c} дней" for h, c in stats)
        else:
            msg = "Нет данных."
        await update.message.reply_text(msg, reply_markup=main_menu())
        return

    # --- Установить напоминание ---
    if text == "⏰ Установить напоминание":
        context.user_data["setting_reminder"] = True
        await update.message.reply_text(
            "Введите время напоминания в формате ЧЧ.MM (например, 20.30):",
            reply_markup=main_menu()
        )
        return

    if context.user_data.get("setting_reminder"):
        time_str = text.strip()
        try:
            h, m = map(int, time_str.split("."))
            if 0 <= h < 24 and 0 <= m < 60:
                set_reminder(user_id, time_str)
                await update.message.reply_text(f"Напоминание установлено на {time_str} ⏰", reply_markup=main_menu())
            else:
                await update.message.reply_text("Неверный формат времени. Попробуйте снова.", reply_markup=main_menu())
        except:
            await update.message.reply_text("Неверный формат времени. Попробуйте снова.", reply_markup=main_menu())
        context.user_data["setting_reminder"] = False
        return

# ===== Обработка inline-кнопок =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    action, habit = query.data.split("|")

    if action == "mark":
        if mark_habit(user_id, habit):
            await query.edit_message_text(f"{habit} отмечено ✅")
        else:
            await query.edit_message_text("Сегодня уже отмечено 😉")
    elif action == "delete":
        delete_habit(user_id, habit)
        await query.edit_message_text(f"{habit} удалена 🗑")

# ===== Напоминания =====
async def reminder_loop(app):
    while True:
        now = datetime.now().strftime("%H.%M")
        for user_id, time_str in get_all_reminders():
            if now == time_str:
                habits = get_habits(user_id)
                if habits:
                    msg = "Не забудь выполнить свои привычки:\n" + "\n".join(f"• {h}" for h in habits)
                    try:
                        await app.bot.send_message(chat_id=int(user_id), text=msg)
                    except:
                        pass
        await asyncio.sleep(60)

# ===== Основной блок =====
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))

# Запускаем напоминания параллельно с ботом
async def on_startup(app):
    app.create_task(reminder_loop(app))

if __name__ == "__main__":
    app.run_polling(on_startup=on_startup)
