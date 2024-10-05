from telegram import Bot
import time
from itertools import cycle
import pandas as pd
import requests
import asyncio

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU4']

async def get_sma_data(from_symbol, to_symbol, api_key, interval='5min', time_period=10):
    """
    Получение данных SMA о валютной паре с Alpha Vantage API.
    """
    symbol = f"{from_symbol}{to_symbol}"
    url = f'https://www.alphavantage.co/query?function=SMA&symbol={symbol}&interval={interval}&time_period={time_period}&series_type=close&entitlement=realtime&apikey={api_key}'
    
    response = requests.get(url)
    data = response.json()

    try:
        # Извлечение временных рядов и преобразование в DataFrame
        time_series = data['Technical Analysis: SMA']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'SMA': 'SMA'})  # Берем SMA
        df['SMA'] = df['SMA'].astype(float)
        df = df.sort_index()  # Сортировка по дате
        return df
    except KeyError:
        print("Ошибка в получении данных от API:", data)
        return None

def choose_time_frame(df):
    """
    Определение времени сделки на основе движения скользящей средней (SMA).
    """
    # Используем разницу между текущим и предыдущим значением SMA
    last_crosses = df['SMA'].diff()  # Разница между текущей и предыдущей SMA

    # Находим индекс последнего изменения направления SMA
    last_cross_sign = last_crosses.apply(lambda x: 1 if x > 0 else -1)  # Определяем знак
    last_cross_index = (last_cross_sign != last_cross_sign.shift(1)).idxmax()

    # Определяем количество свечей, прошедших с момента изменения
    candles_since_cross = len(df) - df.index.get_loc(last_cross_index)

    # Выбираем таймфрейм в зависимости от времени, прошедшего с момента изменения
    if candles_since_cross <= 2:
        return "1M"
    elif candles_since_cross <= 5:
        return "2M"
    else:
        return "5M"

def check_for_signal(df, from_symbol, to_symbol):
    """
    Проверка движения скользящей средней для определения сигналов на покупку/продажу.
    Формирование сообщения о сигнале.
    """
    latest_data = df.iloc[-1]  # Последняя строка данных
    previous_data = df.iloc[-2]  # Предыдущая строка данных
    current_sma = latest_data['SMA']  # Текущая SMA

    # Форматируем валютную пару для сообщения
    pair_symbol = f"{from_symbol}/{to_symbol}"

    # Определяем время сделки
    time_frame = choose_time_frame(df)

    # Проверка роста или падения SMA и формирование сигнала
    if current_sma > previous_data['SMA']:
        # Сигнал на покупку (LONG)
        signal_message = (f"🔥LONG🟢🔼\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📈 {current_sma:.4f}")
        return signal_message
    elif current_sma < previous_data['SMA']:
        # Сигнал на продажу (SHORT)
        signal_message = (f"🔥SHORT🔴🔽\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📉 {current_sma:.4f}")
        return signal_message
    return None

async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Асинхронная функция отправки сигнала в Telegram через бота.
    message_thread_id — используется для отправки сообщений в конкретный топик.
    """
    await bot.send_message(chat_id=chat_id, text=signal_message, message_thread_id=message_thread_id)

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    bot = Bot(token=token)

    # Список каналов и топиков
    channels_and_topics = [
        {'chat_id': '-1002243376132', 'message_thread_id': '2'},  # Первый канал, топик
        {'chat_id': '-1002290780268', 'message_thread_id': '4'},  # Второй канал, топик
    ]
    
    # Валютные пары
    currency_pairs = [
        ('EUR', 'GBP'),
        ('AUD', 'CAD'),
        ('GBP', 'CHF'),
        ('NZD', 'CAD'),
        ('EUR', 'AUD'),
        ('AUD', 'NZD'),
        ('EUR', 'CHF'),
        ('GBP', 'AUD'),
        ('CAD', 'CHF'),
        ('NZD', 'CHF'),
    ]

    # Создание цикла API ключей
    api_keys_cycle = cycle(API_KEYS)

    while True:
        for from_symbol, to_symbol in currency_pairs:
            api_key = next(api_keys_cycle)

            # Получаем SMA данные
            df_sma = await get_sma_data(from_symbol, to_symbol, api_key)

            if df_sma is not None:
                # Проверяем наличие сигнала
                signal_message = check_for_signal(df_sma, from_symbol, to_symbol)
                if signal_message:
                    # Отправка сигнала в оба канала и топики
                    for channel in channels_and_topics:
                        await notify_signals(
                            bot,
                            signal_message,
                            chat_id=channel['chat_id'],
                            message_thread_id=channel.get('message_thread_id')
                        )
            
            # Пауза между запросами для предотвращения превышения лимитов API
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
