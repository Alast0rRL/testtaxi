
import logging
import os
import json
import httpx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import (
    get_waiting_orders, 
    update_order_status, 
    get_order_by_id,
    get_driver_by_phone,
    add_driver,
    get_driver_by_telegram_id,
    update_driver_telegram_id,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for registration conversation
PHONE_NUMBER, FULL_NAME, CAR_NUMBER = range(3)


async def show_waiting_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays waiting orders to the driver."""
    await update.message.reply_text("Вот доступные заказы:", reply_markup=ReplyKeyboardRemove())
    orders = get_waiting_orders()
    if not orders:
        await update.message.reply_text("Нет доступных заказов.")
        return

    for order in orders:
        order_id, user_id, from_city, to_city, tariff, trip_time, phone_number, status = order
        order_text = (
            f"Новый заказ! (ID: {order_id})\n"
            f"Откуда: {from_city}\n"
            f"Куда: {to_city}\n"
            f"Тариф: {tariff}\n"
            f"Время: {trip_time}\n"
            f"Телефон: {phone_number}"
        )
        keyboard = [[InlineKeyboardButton("Взять заказ", callback_data=f"accept_{order_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(order_text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the bot, checks for registration, and either shows orders or starts registration."""
    driver = get_driver_by_telegram_id(update.effective_user.id)
    if driver:
        await update.message.reply_text(f"Здравствуйте, {driver[2]}!")
        await show_waiting_orders(update, context)
        return ConversationHandler.END
    else:
        contact_button = KeyboardButton("Поделиться номером телефона", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Здравствуйте! Для начала работы, пожалуйста, поделитесь своим номером телефона.",
            reply_markup=reply_markup,
        )
        return PHONE_NUMBER

async def phone_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the phone number, checks if the driver exists, and proceeds accordingly."""
    phone = update.message.contact.phone_number
    context.user_data['phone_number'] = phone
    
    driver = get_driver_by_phone(phone)
    if driver:
        update_driver_telegram_id(phone, update.effective_user.id)
        await update.message.reply_text(f"Рады снова вас видеть, {driver[2]}!")
        await show_waiting_orders(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Вы новый водитель! Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        return FULL_NAME

async def full_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the full name and asks for the car number."""
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Теперь, пожалуйста, введите номер вашей машины:")
    return CAR_NUMBER

async def car_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the car number, saves the new driver, and shows orders."""
    context.user_data['car_number'] = update.message.text
    
    add_driver(
        telegram_id=update.effective_user.id,
        phone_number=context.user_data['phone_number'],
        full_name=context.user_data['full_name'],
        car_number=context.user_data['car_number'],
    )
    
    await update.message.reply_text("Поздравляем, вы успешно зарегистрированы!")
    await show_waiting_orders(update, context)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays help information."""
    await update.message.reply_text(
        "Этот бот предназначен для водителей такси.\n\n"
        "**Команды:**\n"
        "/start - Начать работу или показать доступные заказы\n"
        "/help - Показать это сообщение"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("accept_"):
        order_id = int(query.data.split("_")[1])
        driver_user = query.from_user
        
        update_order_status(order_id, "Принят")
        logger.info(f"Driver {driver_user.id} ({driver_user.full_name}) accepted order {order_id}")
        
        original_message = query.message.text
        await query.edit_message_text(text=f"Заказ {order_id} принят вами.\n\n{original_message}")

        # Notify the client
        order = get_order_by_id(order_id)
        driver = get_driver_by_telegram_id(driver_user.id)

        if order and driver:
            client_user_id = order[1]
            driver_name = driver[2]
            driver_car = driver[3]

            notification_text = (
                f"Ваш заказ принят!\n\n"
                f"Водитель: {driver_name}\n"
                f"Машина: {driver_car}"
            )

            client_token = context.bot_data['CLIENT_TELEGRAM_TOKEN']
            url = f"https://api.telegram.org/bot{client_token}/sendMessage"
            params = {"chat_id": client_user_id, "text": notification_text}

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(url, json=params)
                    response.raise_for_status()
                    logger.info(f"Successfully sent notification to client {client_user_id} for order {order_id}")
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to send notification for order {order_id}: {e.response.text}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while sending notification for order {order_id}: {e}")

async def post_init(application: Application) -> None:
    """Sets the bot commands in the Telegram menu."""
    commands = [
        BotCommand("start", "Начать работу / Показать заказы"),
        BotCommand("help", "Помощь"),
    ]
    await application.bot.set_my_commands(commands)

async def show_waiting_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays waiting orders to the driver."""
    await update.message.reply_text("Вот доступные заказы:", reply_markup=ReplyKeyboardRemove())
    orders = get_waiting_orders()
    if not orders:
        await update.message.reply_text("Нет доступных заказов.")
        return

    for order in orders:
        order_id, user_id, from_city, to_city, tariff, trip_time, phone_number, status = order
        order_text = (
            f"Новый заказ! (ID: {order_id})\n"
            f"Откуда: {from_city}\n"
            f"Куда: {to_city}\n"
            f"Тариф: {tariff}\n"
            f"Время: {trip_time}\n"
            f"Телефон: {phone_number}"
        )
        keyboard = [[InlineKeyboardButton("Взять заказ", callback_data=f"accept_{order_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(order_text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the bot, checks for registration, and either shows orders or starts registration."""
    driver = get_driver_by_telegram_id(update.effective_user.id)
    if driver:
        await update.message.reply_text(f"Здравствуйте, {driver[2]}!")
        await show_waiting_orders(update, context)
        return ConversationHandler.END
    else:
        contact_button = KeyboardButton("Поделиться номером телефона", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Здравствуйте! Для начала работы, пожалуйста, поделитесь своим номером телефона.",
            reply_markup=reply_markup,
        )
        return PHONE_NUMBER

async def phone_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the phone number, checks if the driver exists, and proceeds accordingly."""
    phone = update.message.contact.phone_number
    context.user_data['phone_number'] = phone
    
    driver = get_driver_by_phone(phone)
    if driver:
        update_driver_telegram_id(phone, update.effective_user.id)
        await update.message.reply_text(f"Рады снова вас видеть, {driver[2]}!")
        await show_waiting_orders(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Вы новый водитель! Пожалуйста, введите ваше ФИО:", reply_markup=ReplyKeyboardRemove())
        return FULL_NAME

async def full_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the full name and asks for the car number."""
    context.user_data['full_name'] = update.message.text
    await update.message.reply_text("Теперь, пожалуйста, введите номер вашей машины:")
    return CAR_NUMBER

async def car_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the car number, saves the new driver, and shows orders."""
    context.user_data['car_number'] = update.message.text
    
    add_driver(
        telegram_id=update.effective_user.id,
        phone_number=context.user_data['phone_number'],
        full_name=context.user_data['full_name'],
        car_number=context.user_data['car_number'],
    )
    
    await update.message.reply_text("Поздравляем, вы успешно зарегистрированы!")
    await show_waiting_orders(update, context)
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays help information."""
    await update.message.reply_text(
        "Этот бот предназначен для водителей такси.\n\n"
        "**Команды:**\n"
        "/start - Начать работу или показать доступные заказы\n"
        "/help - Показать это сообщение"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("accept_"):
        order_id = int(query.data.split("_")[1])
        driver_user = query.from_user
        
        update_order_status(order_id, "Принят")
        logger.info(f"Driver {driver_user.id} ({driver_user.full_name}) accepted order {order_id}")
        
        original_message = query.message.text
        await query.edit_message_text(text=f"Заказ {order_id} принят вами.\n\n{original_message}")

        # Notify the client
        order = get_order_by_id(order_id)
        driver = get_driver_by_telegram_id(driver_user.id)

        if order and driver:
            client_user_id = order[1]
            driver_name = driver[2]
            driver_car = driver[3]

            notification_text = (
                f"Ваш заказ принят!\n\n"
                f"Водитель: {driver_name}\n"
                f"Машина: {driver_car}"
            )

            client_token = context.bot_data['CLIENT_TELEGRAM_TOKEN']
            url = f"https://api.telegram.org/bot{client_token}/sendMessage"
            params = {"chat_id": client_user_id, "text": notification_text}

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(url, json=params)
                    response.raise_for_status()
                    logger.info(f"Successfully sent notification to client {client_user_id} for order {order_id}")
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to send notification for order {order_id}: {e.response.text}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while sending notification for order {order_id}: {e}")

def main() -> None:
    """Run the driver bot."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        driver_token = config.get('DRIVER_TELEGRAM_TOKEN')
        client_token = config.get('CLIENT_TELEGRAM_TOKEN')

    except FileNotFoundError:
        logger.error("config.json not found.")
        return
    except json.JSONDecodeError:
        logger.error("Error decoding config.json.")
        return

    if not driver_token or driver_token == "YOUR_DRIVER_TOKEN_HERE":
        logger.error("DRIVER_TELEGRAM_TOKEN not found or is a placeholder in config.json.")
        return

    application = Application.builder().token(driver_token).post_init(post_init).build()
    application.bot_data['CLIENT_TELEGRAM_TOKEN'] = client_token

    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE_NUMBER: [MessageHandler(filters.CONTACT, phone_number_handler)],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name_handler)],
            CAR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_number_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(registration_conv)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == "__main__":
    main()
