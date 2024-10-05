from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import requests

# Токен Telegram бота
API_KEYS = ['ТВОЙ_КЛЮЧ_1', 'ТВОЙ_КЛЮЧ_2']
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

def get_currency_data(from_symbol, to_symbol=None):
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

def send_signal(update: Update, context: CallbackContext, asset: str):
    """
    Отправка актуальной цены актива в ответ на команду.
    """
    if asset in assets:
        from_symbol, to_symbol = assets[asset]
        price, error = get_currency_data(from_symbol, to_symbol)

        if error:
            update.message.reply_text(error)
        else:
            pair_symbol = f"{from_symbol}/{to_symbol}" if to_symbol else from_symbol
            signal_message = (f"🔥Актуальная цена для {pair_symbol}: {price}")
            update.message.reply_text(signal_message)
    else:
        update.message.reply_text(f"Актив {asset} не поддерживается.")

def handle_command(update: Update, context: CallbackContext):
    """
    Универсальный обработчик для команд актива.
    """
    command = update.message.text[1:]  # Получаем название актива (убираем "/")
    send_signal(update, context, command)

def main():
    token = 'ТВОЙ_ТЕЛЕГРАМ_ТОКЕН'
    application = Application.builder().token(token).build()

    # Добавляем обработчики для команд
    for asset in assets.keys():
        application.add_handler(CommandHandler(asset, handle_command))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
