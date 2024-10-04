import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import logging

API_TOKEN = '8068789170:AAHmKXcP9g_qTVuP_KNBAFGU56__-0nDseQ'  # Укажи свой реальный токен здесь

# Логирование для отслеживания работы
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Функция для команды /chat_id и /thread_id
async def chat_id(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id  # ID группы или канала
    thread_id = update.message.message_thread_id  # ID топика (если есть)

    if thread_id:
        # Если сообщение в топике, отправляем и ID топика
        await update.message.reply_text(f"ID группы или канала: {chat_id}\nID топика: {thread_id}")
    else:
        # Если сообщение не в топике, отправляем только ID группы или канала
        await update.message.reply_text(f"ID этой группы или канала: {chat_id}")

# Функция для команды /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Я бот, который будет отправлять тебе ID чата и топика.')

def main():
    # Создаём приложение для бота
    application = Application.builder().token(API_TOKEN).build()
    
    # Добавляем команду /chat_id
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.add_handler(CommandHandler("start", start))

    # Запуск бота
    logger.info("Бот запущен и готов к работе.")
    application.run_polling()

if __name__ == '__main__':
    main()
