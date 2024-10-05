from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен Telegram бота
API_KEYS = ['GNP3HU5R5LBILMSB']
API_KEY = API_KEYS[0]

# Список активов
assets = {
    "eurusd": ("EUR", "USD"),
    "gold_silver": ("XAU", "XAG"),  # Золото и серебро
    "gbpusd": ("GBP", "USD"),
    "nzd_cad": ("NZD", "CAD"),
    "eur_aud": ("EUR", "AUD"),
    "ton": ("TONCOIN", "USD"),  # Тонкоин против USD
    "eur_chf": ("EUR", "CHF"),
    "microsoft_apple": ("MSFT", "AAPL"),
    "mcdonalds": ("MCD", None),
    "bitcoin": ("BTC", "USD"),
}

async def get_currency_data(from_symbol, to_symbol=None):
    """
    Получение данных о валютной паре или активе с Alpha Vantage API.
    """
    if to_symbol:  # Если это валютная пара или пара активов
        url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_symbol}&to_currency={to_symbol}&apikey={API_KEY}'
    else:  # Для акций, криптовалют
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={from_symbol}&apikey={API_KEY}'

    response = requests.get(url)
    data = response.json()

    if "Error Message" in data:
        return None, f"Ошибка при получении данных для {from_symbol}/{to_symbol}: {data['Error Message']}"
    
    if "Realtime Currency Exchange Rate" in data:
        rate = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        return rate, None
    elif "Global Quote" in data:
        price = data['Global Quote']['05. price']
        return price, None
    return None, "Не удалось получить данные"

async def send_signal(update: Update, context: CallbackContext, asset: str):
    """
    Отправка актуальной цены актива в ответ на команду.
    """
    if asset in assets:
        from_symbol, to_symbol = assets[asset]
        price, error = await get_currency_data(from_symbol, to_symbol)

        if error:
            await update.message.reply_text(error)
        else:
            pair_symbol = f"{from_symbol}/{to_symbol}" if to_symbol else from_symbol
            signal_message = (f"🔥Актуальная цена для {pair_symbol}: {price}")
            await update.message.reply_text(signal_message)
    else:
        await update.message.reply_text(f"Актив {asset} не поддерживается.")

async def handle_command(update: Update, context: CallbackContext):
    """
    Универсальный обработчик для команд актива.
    """
    command = update.message.text[1:]  # Получаем название актива (убираем "/")
    await send_signal(update, context, command)

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    application = Application.builder().token(token).build()

    logger.info("Бот запущен")

    # Добавляем обработчики для команд
    for asset in assets.keys():
        application.add_handler(CommandHandler(asset, handle_command))

    # Запуск бота и постоянное ожидание команд
    application.run_polling()

if __name__ == '__main__':
    main()
