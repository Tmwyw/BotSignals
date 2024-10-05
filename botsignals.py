import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
ALPHA_VANTAGE_API_KEY = 'GNP3HU5R5LBILMSB'

# Список активов
assets = {
    "eur_usd": ("EUR", "USD"),
    "usd_try": ("USD", "TRY"),
    "gbp_usd": ("GBP", "USD"),
    "eur_aud": ("EUR", "AUD"),
    "eur_chf": ("EUR", "CHF"),
    "usd_zar": ("USD", "ZAR"),
    "intel": ("INTC", None),  # Intel stock
    "microsoft": ("MSFT", None),  # Microsoft stock
    "coca_cola": ("KO", None),  # Coca-Cola stock
    "litecoin": ("LTC", "USD"),  # Litecoin against USD
}

def get_currency_data(from_symbol, to_symbol=None):
    """
    Получение данных о валютной паре или активе с Alpha Vantage API.
    """
    logger.info(f"Запрос данных для {from_symbol}/{to_symbol}")
    if to_symbol:  # Если это валютная пара или пара активов
        url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_symbol}&to_currency={to_symbol}&apikey={ALPHA_VANTAGE_API_KEY}'
    else:  # Для акций и криптовалют
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={from_symbol}&apikey={ALPHA_VANTAGE_API_KEY}'

    response = requests.get(url)
    data = response.json()

    # Возвращаем цену или сообщение об ошибке
    if "Realtime Currency Exchange Rate" in data:
        return data['Realtime Currency Exchange Rate']['5. Exchange Rate'], None
    elif "Global Quote" in data:
        return data['Global Quote']['05. price'], None
    else:
        logger.error(f"Ошибка получения данных для {from_symbol}/{to_symbol}")
        return None, "Не удалось получить данные."

# Обработчик команды для получения данных
async def send_signal(update: Update, context, asset: str):
    if asset in assets:
        from_symbol, to_symbol = assets[asset]
        price, error = get_currency_data(from_symbol, to_symbol)

        if error:
            await update.message.reply_text(error)
        else:
            pair_symbol = f"{from_symbol}/{to_symbol}" if to_symbol else from_symbol
            signal_message = (f"🔥 Актуальная цена для {pair_symbol}: {price}")
            await update.message.reply_text(signal_message)
    else:
        await update.message.reply_text(f"Актив {asset} не поддерживается.")

async def handle_command(update: Update, context):
    command = update.message.text[1:]  # Убираем "/"
    logger.info(f"Получена команда: {command}")
    await send_signal(update, context, command)

def main():
    logger.info("Инициализация бота...")

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    logger.info("Приложение создано, добавляем обработчики")

    # Добавляем обработчики для активов
    for asset in assets.keys():
        application.add_handler(CommandHandler(asset, handle_command))

    logger.info("Обработчики добавлены, запускаем бота")

    # Запуск бота
    application.run_polling()

    logger.info("Бот запущен и ожидает команды")

if __name__ == '__main__':
    main()
