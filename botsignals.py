from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import requests

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
ALPHA_VANTAGE_API_KEY = 'GBMTX86HTLNQYH2F'

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

def get_currency_data(from_symbol, to_symbol=None):
    """
    Получение данных о валютной паре или активе с Alpha Vantage API.
    """
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
        return None, "Не удалось получить данные."

async def send_signal(update: Update, context: CallbackContext, asset: str):
    """
    Отправка актуальной цены актива в ответ на команду.
    """
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

async def handle_command(update: Update, context: CallbackContext):
    """
    Универсальный обработчик для команд актива.
    """
    command = update.message.text[1:]  # Получаем название актива (убираем "/")
    await send_signal(update, context, command)

async def main():
    # Создаём бота
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Инициализация приложения
    await application.initialize()

    # Добавляем обработчики для команд
    for asset in assets.keys():
        application.add_handler(CommandHandler(asset, handle_command))

    # Запускаем бота
    await application.start()
    await application.updater.start_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
