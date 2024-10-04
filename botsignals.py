from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import time
from itertools import cycle
import pandas as pd
import requests
import sys

# Токен Telegram бота
API_KEYS = ['KOXI6CITVOWODSHI', '746GWA2WFN18H08D', '74O1PFK2C59IB5ND', '', 
            '', 'AA65UM6300G1Z3I1', '5EUEU0UEJY0PGTCN', 'MKCJQ7I9O9E9LM20', 
            'NXUF3LWUVDD3A0UG', 'CBRYAJSAMK75M6NS']

def check_api_key(api_key):
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

def get_currency_data(from_symbol, to_symbol, api_key):
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
        return signal_message
    elif latest_data['Short_MA'] < latest_data['Long_MA'] and previous_data['Short_MA'] >= previous_data['Long_MA']:
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

def stop(update: Update, context: CallbackContext):
    """Остановка бота через команду /stop."""
    update.message.reply_text('Бот остановлен.')
    print("Получена команда /stop. Бот завершает работу.")
    sys.exit(0)

def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    updater = Updater(token)
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

    # Обработчик команды /stop
    updater.dispatcher.add_handler(CommandHandler('stop', stop))

    updater.start_polling()

    try:
        while True:
            for from_symbol, to_symbol in currency_pairs:
                api_key = next(api_keys_cycle)
                
                # Проверяем, работает ли API ключ
                if not check_api_key(api_key):
                    print(f"Пропуск ключа {api_key}, так как он не работает или достиг лимита.")
                    continue

                # Если ключ рабочий, получаем данные валютной пары
                df = get_currency_data(from_symbol, to_symbol, api_key)

                if df is not None:
                    # Рассчитываем скользящие средние
                    df_with_ma = calculate_moving_averages(df)

                    # Проверяем наличие сигнала
                    signal_message = check_for_signal(df_with_ma, from_symbol, to_symbol)
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
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")

if __name__ == '__main__':
    main()
