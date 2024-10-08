import asyncio
from telegram import Bot
from itertools import cycle
import pandas as pd
import requests

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

# Хранение последних сигналов для валютных пар
last_signals = {}

async def check_api_key(api_key):
    """
    Функция для проверки работоспособности API ключа.
    Возвращает True, если ключ работает, False — если достиг лимита или невалиден.
    """
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey={api_key}'
    response = requests.get(url)
    data = response.json()

    if "Error Message" in data:
        print(f"Ключ {api_key} не работает: {data['Error Message']}")
        return False
    elif "Information" in data and "API rate limit" in data['Information']:
        print(f"Ключ {api_key} достиг лимита: {data['Information']}")
        return False
    else:
        print(f"Ключ {api_key} работает корректно!")
        return True

async def get_currency_data(from_symbol, to_symbol, api_key):
    """
    Получение данных о валютной паре с Alpha Vantage API.
    """
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&apikey={api_key}'
    response = requests.get(url)
    data = response.json()

    try:
        # Извлечение временных рядов и преобразование в DataFrame
        time_series = data['Time Series FX (Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'4. close': 'Close'})  # Берем только цены закрытия
        df['Close'] = df['Close'].astype(float)
        df = df.sort_index()  # Сортировка по дате
        return df
    except KeyError:
        print(f"Ошибка в получении данных от API ключа {api_key}: {data}")
        return None

def calculate_moving_averages(df, short_window=5, long_window=20):
    """
    Вычисление краткосрочной и долгосрочной скользящих средних.
    """
    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()
    return df

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
    elif candles_since_cross <= 10:
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
    current_price = latest_data['Close']  # Текущая цена пары

    # Форматируем валютную пару для сообщения
    pair_symbol = f"{from_symbol}/{to_symbol}"

    # Определяем время сделки
    time_frame = choose_time_frame(df)

    # Проверка пересечения скользящих средних и формирование сигнала
    if latest_data['Short_MA'] > latest_data['Long_MA'] and previous_data['Short_MA'] <= previous_data['Long_MA']:
        # Сигнал на покупку (LONG)
        signal_message = (f"🔥LONG🟢🔼\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📈 {current_price:.4f}")
        return 'LONG', signal_message
    elif latest_data['Short_MA'] < latest_data['Long_MA'] and previous_data['Short_MA'] >= previous_data['Long_MA']:
        # Сигнал на продажу (SHORT)
        signal_message = (f"🔥SHORT🔴🔽\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📉 {current_price:.4f}")
        return 'SHORT', signal_message
    return None, None

async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Функция отправки сигнала в Telegram через бота.
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
        ('EUR', 'USD'),  # EUR/USD (OTC)
    ('GBP', 'USD'),  # GBP/USD (OTC)
    ('USD', 'CHF'),  # USD/CHF (OTC)
    ('AUD', 'CAD'),  # AUD/CAD (OTC)
    ('EUR', 'GBP'),  # EUR/GBP (OTC)
    ('USD', 'MXN'),  # USD/MXN (OTC)
    ]

    # Создание цикла API ключей
    api_keys_cycle = cycle(API_KEYS)

    while True:
        for from_symbol, to_symbol in currency_pairs:
            api_key = next(api_keys_cycle)
            
            # Проверяем, работает ли API ключ
            if not await check_api_key(api_key):
                print(f"Пропуск ключа {api_key}, так как он не работает или достиг лимита.")
                continue

            # Если ключ рабочий, получаем данные валютной пары
            df = await get_currency_data(from_symbol, to_symbol, api_key)

            if df is not None:
                # Рассчитываем скользящие средние
                df_with_ma = calculate_moving_averages(df)

                # Проверяем наличие сигнала
                signal_type, signal_message = check_for_signal(df_with_ma, from_symbol, to_symbol)

                if signal_message:
                    # Проверяем, изменился ли сигнал для данной валютной пары
                    if last_signals.get((from_symbol, to_symbol)) != signal_type:
                        # Обновляем последний сигнал
                        last_signals[(from_symbol, to_symbol)] = signal_type
                        
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
