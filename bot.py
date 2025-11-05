
import logging
import os
import json
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import initialize_database, insert_order

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# State definitions for conversations
CITY_FROM, CITY_TO, TARIFF, PHONE_NUMBER, TRIP_TIME = range(5)
AWAITING_SUPPORT_MESSAGE = range(5, 6)

# Data
CITIES = ["Октябрьский", "Туймазы", "Уфа"]
TARIFFS = ["Стандарт", "Комфорт", "Бизнес"]

# --- Helper Functions ---
async def post_init(application: Application) -> None:
    """Sets the bot commands in the Telegram menu."""
    commands = [
        BotCommand("start", "Начать новый заказ"),
        BotCommand("support", "Связаться с поддержкой"),
        BotCommand("cancel", "Отменить текущее действие"),
    ]
    await application.bot.set_my_commands(commands)

async def ask_for_trip_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks for the trip time and moves to the next state."""
    await update.message.reply_text(
        "Спасибо! Теперь, пожалуйста, напишите желаемое время поездки в формате ЧЧ:ММ (например, 18:30).",
        reply_markup=ReplyKeyboardRemove(),
    )
    return TRIP_TIME

# --- Order Conversation Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the order conversation with inline city selection."""
    logger.info(f"User {update.effective_user.id} started the conversation.")
    keyboard = [[InlineKeyboardButton(city, callback_data=city)] for city in CITIES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Здравствуйте! Я бот для заказа межгородского такси.\n"
        "Из какого города вы хотите поехать?",
        reply_markup=reply_markup,
    )
    return CITY_FROM

async def city_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores departure city from callback and asks for destination."""
    query = update.callback_query
    await query.answer()
    
    from_city = query.data
    context.user_data["from_city"] = from_city

    remaining_cities = [city for city in CITIES if city != from_city]
    keyboard = [[InlineKeyboardButton(city, callback_data=city)] for city in remaining_cities]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"Город отправления: {from_city}.\nТеперь выберите город назначения.",
        reply_markup=reply_markup
    )
    return CITY_TO

async def city_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores destination and asks for tariff."""
    query = update.callback_query
    await query.answer()

    to_city = query.data
    context.user_data["to_city"] = to_city

    keyboard = [[InlineKeyboardButton(t, callback_data=t)] for t in TARIFFS]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"Город назначения: {to_city}.\nТеперь выберите тариф.",
        reply_markup=reply_markup
    )
    return TARIFF

async def tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores tariff and asks for phone number via ReplyKeyboard."""
    query = update.callback_query
    await query.answer()

    selected_tariff = query.data
    context.user_data["tariff"] = selected_tariff

    await query.edit_message_text(text=f"Тариф: {selected_tariff}. Отлично!")

    contact_button = KeyboardButton("Поделиться номером телефона", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Пожалуйста, поделитесь своим номером с помощью кнопки или просто напишите его в чат (для заказа другу).",
        reply_markup=reply_markup,
    )
    return PHONE_NUMBER

async def phone_number_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores phone number from contact and asks for trip time."""
    context.user_data["phone_number"] = update.message.contact.phone_number
    return await ask_for_trip_time(update, context)

async def phone_number_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores phone number from text and asks for trip time."""
    text = update.message.text
    cleaned_phone = re.sub(r'\D', '', text)

    if len(cleaned_phone) == 11 and (cleaned_phone.startswith('7') or cleaned_phone.startswith('8')):
        normalized_phone = '+7' + cleaned_phone[1:]
        context.user_data["phone_number"] = normalized_phone
        return await ask_for_trip_time(update, context)
    elif len(cleaned_phone) == 10:
        normalized_phone = '+7' + cleaned_phone
        context.user_data["phone_number"] = normalized_phone
        return await ask_for_trip_time(update, context)
    else:
        await update.message.reply_text(
            "Неверный формат номера. Пожалуйста, введите 10 или 11 цифр (например, 9271234567 или 89271234567)."
        )
        return PHONE_NUMBER

async def trip_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the trip time if valid, otherwise asks again."""
    user_time = update.message.text
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", user_time):
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 18:30)."
        )
        return TRIP_TIME

    context.user_data["trip_time"] = user_time
    data = context.user_data
    
    await update.message.reply_text(
        f"Спасибо! Ваш заказ принят.\n"
        f"  - Откуда: {data['from_city']}\n"
        f"  - Куда: {data['to_city']}\n"
        f"  - Тариф: {data['tariff']}\n"
        f"  - Время: {data['trip_time']}\n"
        f"  - Телефон: {data['phone_number']}\n\n"
        "В ближайшее время с вами свяжется водитель.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Save order to the database
    user_id = update.effective_user.id
    insert_order(
        user_id=user_id,
        from_city=data['from_city'],
        to_city=data['to_city'],
        tariff=data['tariff'],
        trip_time=data['trip_time'],
        phone_number=data['phone_number']
    )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels a conversation."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Действие отменено.")
    else:
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=ReplyKeyboardRemove(),
        )
    context.user_data.clear()
    return ConversationHandler.END

# --- Support Conversation Functions ---
async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the support conversation."""
    await update.message.reply_text(
        "Пожалуйста, напишите ваше обращение в поддержку. Чтобы отменить, введите /cancel.",
        reply_markup=ReplyKeyboardRemove()
    )
    return AWAITING_SUPPORT_MESSAGE

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Forwards the user's message to the support chat."""
    user = update.message.from_user
    support_chat_id = context.bot_data.get("SUPPORT_CHAT_ID")

    if not support_chat_id or support_chat_id == "YOUR_SUPPORT_CHAT_ID_HERE":
        await update.message.reply_text("Функция поддержки временно не настроена.")
        return ConversationHandler.END

    forward_text = f"Новое обращение в поддержку от пользователя: {user.full_name} (ID: {user.id})\n\n---\n{update.message.text}"
    
    try:
        await context.bot.send_message(chat_id=support_chat_id, text=forward_text)
        await update.message.reply_text("Спасибо! Ваше сообщение было отправлено в поддержку.")
    except Exception as e:
        logger.error(f"Failed to send support message to {support_chat_id}: {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения. Попробуйте позже.")

    return ConversationHandler.END

# --- Main Bot Logic ---
def main() -> None:
    """Run the bot."""
    initialize_database()
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        token = config.get('CLIENT_TELEGRAM_TOKEN')
        support_chat_id = config.get('SUPPORT_CHAT_ID')
    except FileNotFoundError:
        logger.error("config.json not found.")
        return
    except json.JSONDecodeError:
        logger.error("Error decoding config.json.")
        return

    if not token or token == "YOUR_CLIENT_TOKEN_HERE":
        logger.error("CLIENT_TELEGRAM_TOKEN not found or is a placeholder in config.json.")
        return

    application = Application.builder().token(token).post_init(post_init).build()
    application.bot_data["SUPPORT_CHAT_ID"] = support_chat_id

    # Order conversation handler
    order_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CITY_FROM: [CallbackQueryHandler(city_from)],
            CITY_TO: [CallbackQueryHandler(city_to)],
            TARIFF: [CallbackQueryHandler(tariff)],
            PHONE_NUMBER: [
                MessageHandler(filters.CONTACT & ~filters.COMMAND, phone_number_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number_text),
            ],
            TRIP_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, trip_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # Support conversation handler
    support_conv = ConversationHandler(
        entry_points=[CommandHandler("support", support_start)],
        states={
            AWAITING_SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(order_conv)
    application.add_handler(support_conv)

    application.run_polling()

if __name__ == "__main__":
    main()
