from telegram import Bot
import time
from itertools import cycle
import pandas as pd
import requests

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

def get_sma_data(from_symbol, to_symbol, api_key, interval='5min', time_period=10):
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
    Определение времени сделки на основе пересечения скользящих средних.
    """
    last_crosses = df['Short_MA'] - df['Long_MA']  # Разница между скользящими средними
    last_crosses_sign = last_crosses.apply(lambda x: 1 if x > 0 else -1)  # Определяем знак

    # Находим индекс последнего пересечения
    last_cross_index = (last_crosses_sign != last_crosses_sign.shift(1)).idxmax()
    
    # Определяем количество свечей, прошедших с момента пересечения
    candles_since_cross = len(df) - df.index.get_loc(last_cross_index)

    # Выбираем таймфрейм в зависимости от времени, прошедшего с момента пересечения
    if candles_since_cross <= 2:
        return "1M"
    elif candles_since_cross <= 5:
        return "2M"
    else:
        return "5M"

def check_for_signal(df, from_symbol, to_symbol):
    """
    Проверка пересечения скользящих средних для определения сигналов на покупку/продажу.
    Формирование сообщения о сигнале.
    """
    latest_data = df.iloc[-1]  # Последняя строка данных
    previous_data = df.iloc[-2]  # Предыдущая строка данных
    current_price = latest_data['SMA']  # Текущая SMA

    # Форматируем валютную пару для сообщения
    pair_symbol = f"{from_symbol}/{to_symbol}"

    # Определяем время сделки
    time_frame = choose_time_frame(df)

    # Проверка пересечения скользящих средних и формирование сигнала
    if latest_data['SMA'] > previous_data['SMA']:
        # Сигнал на покупку (LONG)
        signal_message = (f"🔥LONG🟢🔼\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📈 {current_price:.4f}")
        return signal_message
    elif latest_data['SMA'] < previous_data['SMA']:
        # Сигнал на продажу (SHORT)
        signal_message = (f"🔥SHORT🔴🔽\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📉 {current_price:.4f}")
        return signal_message
    return None

def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Функция отправки сигнала в Telegram через бота.
    message_thread_id — используется для отправки сообщений в конкретный топик.
    """
    bot.send_message(chat_id=chat_id, text=signal_message, message_thread_id=message_thread_id)

def main():
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
            df_sma = get_sma_data(from_symbol, to_symbol, api_key)

            if df_sma is not None:
                # Проверяем наличие сигнала
                signal_message = check_for_signal(df_sma, from_symbol, to_symbol)
                if signal_message:
                    # Отправка сигнала в оба канала и топики
                    for channel in channels_and_topics:
                        notify_signals(
                            bot,
                            signal_message,
                            chat_id=channel['chat_id'],
                            message_thread_id=channel.get('message_thread_id')
                        )
            
            # Пауза между запросами для предотвращения превышения лимитов API
            time.sleep(5)

if __name__ == '__main__':
    main()
