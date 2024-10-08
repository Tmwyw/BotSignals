import requests
import random
from telegram import Bot

# Константы для Alpha Vantage API и Telegram
API_KEY = 'QSPA6IIRC5CGQU43'
TELEGRAM_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
CHAT_ID = '-1002243376132'
MESSAGE_THREAD_ID = '2'
CURRENCY_PAIR = 'EUR/GBP'

# URL для получения данных по валютной паре
ALPHA_VANTAGE_URL = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=GBP&apikey={API_KEY}'

# Функция для получения текущей цены валютной пары
def get_currency_price():
    response = requests.get(ALPHA_VANTAGE_URL)
    data = response.json()
    if 'Realtime Currency Exchange Rate' in data:
        price = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        return float(price)
    else:
        print('Ошибка при получении данных от Alpha Vantage:', data)
        return None

# Функция для генерации случайного сигнала
def generate_signal():
    signal_type = random.choice(['🔥LONG🟢🔼', '🔥SHORT🔴🔽'])
    return signal_type

# Функция для отправки сообщения в Telegram
def send_signal_to_telegram(price, signal):
    message = f"{signal}\n🔥#EUR/GBP☝️\n💵Текущая цена:📈 {price:.4f}"
    
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=message)

# Основная логика
def main():
    price = get_currency_price()
    if price is not None:
        signal = generate_signal()
        send_signal_to_telegram(price, signal)

if __name__ == '__main__':
    main()
