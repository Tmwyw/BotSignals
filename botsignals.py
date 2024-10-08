import requests
import pandas as pd
import numpy as np
import asyncio
from telegram import Bot
from telegram.constants import ParseMode

# Константы для Alpha Vantage API и Telegram
API_KEY = 'QSPA6IIRC5CGQU43'
TELEGRAM_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
CHAT_ID = '-1002243376132'
MESSAGE_THREAD_ID = '2'
CURRENCY_PAIR = 'EUR/GBP'

# URL для получения дневных данных по валютной паре
ALPHA_VANTAGE_URL = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=GBP&apikey={API_KEY}'

# Функция для получения исторических данных по валютной паре
def get_historical_data():
    response = requests.get(ALPHA_VANTAGE_URL)
    data = response.json()
    if 'Time Series FX (Daily)' in data:
        return data['Time Series FX (Daily)']
    else:
        print('Ошибка при получении данных от Alpha Vantage:', data)
        return None

# Функция для вычисления скользящих средних
def calculate_moving_averages(data):
    df = pd.DataFrame(data).T  # транспонируем, чтобы даты были индексом
    df.columns = ['open', 'high', 'low', 'close']
    df = df.astype(float)

    df['SMA_5'] = df['close'].rolling(window=5).mean()  # короткая средняя
    df['SMA_20'] = df['close'].rolling(window=20).mean()  # длинная средняя
    return df

# Функция для генерации торгового сигнала на основе пересечения скользящих средних
def generate_signal(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # Если короткая пересекает длинную сверху -> сигнал на покупку (LONG)
    if latest['SMA_5'] > latest['SMA_20'] and previous['SMA_5'] <= previous['SMA_20']:
        return "🔥LONG🟢🔼", latest['close']
    # Если короткая пересекает длинную снизу -> сигнал на продажу (SHORT)
    elif latest['SMA_5'] < latest['SMA_20'] and previous['SMA_5'] >= previous['SMA_20']:
        return "🔥SHORT🔴🔽", latest['close']
    else:
        return None, latest['close']

# Асинхронная функция для отправки сообщения в Telegram
async def send_signal_to_telegram(price, signal):
    message = f"{signal}\n🔥#EUR/GBP☝️\n💵Текущая цена:📈 {price:.4f}"
    
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, message_thread_id=MESSAGE_THREAD_ID, text=message, parse_mode=ParseMode.MARKDOWN)

# Основная логика программы
async def main():
    data = get_historical_data()
    if data:
        df = calculate_moving_averages(data)
        signal, price = generate_signal(df)
        if signal:
            await send_signal_to_telegram(price, signal)

if __name__ == '__main__':
    asyncio.run(main())
