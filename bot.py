import json
import os
from datetime import date
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

TOKEN = "8591958220:AAE3yTUZ7heX9jV-lx61mdG5fZ7c5SRyh8c"

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def main_menu():
    keyboard = [
        ["➕ Добавить привычку"],
        ["📋 Мои привычки"],
        ["✅ Отметить выполнение"],
        ["🗑 Удалить привычку"],
        ["📊 Статистика"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Трекер привычек готов к работе 💪",
        reply_markup=main_menu()
    )


# ===== ОБРАБОТКА ТЕКСТА =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.message.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {}

    # --- Добавление ---
    if text == "➕ Добавить привычку":
        context.user_data["adding"] = True
        await update.message.reply_text("Введите название привычки:")
        return

    if context.user_data.get("adding"):
        habit = text.strip()
        if habit in data[user_id]:
            await update.message.reply_text("Такая привычка уже есть.")
        else:
            data[user_id][habit] = []
            save_data(data)
            await update.message.reply_text(f"Привычка '{habit}' добавлена!")
        context.user_data["adding"] = False
        await update.message.reply_text("Меню 👇", reply_markup=main_menu())
        return

    # --- Показать привычки ---
    if text == "📋 Мои привычки":
        habits = data[user_id]
        if habits:
            msg = "Твои привычки:\n"
            for habit in habits:
                msg += f"• {habit}\n"
        else:
            msg = "У тебя пока нет привычек."
        await update.message.reply_text(msg)
        return

    # --- Отметить выполнение ---
    if text == "✅ Отметить выполнение":
        habits = list(data[user_id].keys())
        if not habits:
            await update.message.reply_text("Нет привычек.")
            return

        keyboard = [
            [InlineKeyboardButton(h, callback_data=f"mark|{h}")]
            for h in habits
        ]

        await update.message.reply_text(
            "Выберите привычку:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- Удалить привычку ---
    if text == "🗑 Удалить привычку":
        habits = list(data[user_id].keys())
        if not habits:
            await update.message.reply_text("Нет привычек для удаления.")
            return

        keyboard = [
            [InlineKeyboardButton(h, callback_data=f"delete|{h}")]
            for h in habits
        ]

        await update.message.reply_text(
            "Выберите привычку для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- Статистика ---
    if text == "📊 Статистика":
        habits = data[user_id]
        if habits:
            msg = "Статистика:\n"
            for habit, days in habits.items():
                msg += f"{habit}: {len(days)} дней\n"
        else:
            msg = "Нет данных."
        await update.message.reply_text(msg)


# ===== ОБРАБОТКА INLINE-КНОПОК =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = load_data()

    action, habit = query.data.split("|")

    if action == "mark":
        today = str(date.today())

        if today not in data[user_id][habit]:
            data[user_id][habit].append(today)
            save_data(data)
            await query.edit_message_text(f"{habit} отмечено ✅")
        else:
            await query.edit_message_text("Сегодня уже отмечено 😉")

    elif action == "delete":
        del data[user_id][habit]
        save_data(data)
        await query.edit_message_text(f"{habit} удалена 🗑")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))

app.run_polling()
