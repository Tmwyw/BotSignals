from telegram import Update
from telegram.ext import Application, CommandHandler

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'

# Обработчик команды /start
async def start(update: Update, context):
    await update.message.reply_text("Бот работает!")

def main():
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавление обработчика для команды /start
    application.add_handler(CommandHandler("start", start))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
