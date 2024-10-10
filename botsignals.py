import asyncio
from telegram import Bot
from itertools import cycle
import pandas as pd
import requests
import random  # Для генерации случайной оценки риска

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

# Хранение последних сигналов для валютных пар и таймфреймов
last_signals = {}

# Таймфреймы, которые мы хотим использовать
timeframes = ['1M', '2M', '3M', '5M']

async def get_currency_data(from_symbol, to_symbol, api_key):
    """
    Получение данных о валютной паре с Alpha Vantage API.
    """
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&entitlement=realtime&apikey={api_key}'
    response = requests.get(url)
    data = response.json()

    try:
        # Извлечение временных рядов и преобразование в DataFrame
        time_series = data['Time Series FX (Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'4. close': 'Close'})  # Берем только цены закрытия
        df['Close'] = df['Close'].astype(float)
        df = df.sort_index()  # Сортировка по дате
        
        # Отладочный вывод данных
        print(f"📥 ДАННЫЕ ПОЛУЧЕНЫ 📥 для {from_symbol}/{to_symbol}")
        
        return df
    except KeyError:
        print(f"Ошибка в получении данных от API ключа {api_key}: {data}")
        return None

def calculate_moving_averages(df, timeframe):
    """
    Рассчитываем краткосрочную и долгосрочную скользящие средние в зависимости от таймфрейма.
    """
    if timeframe == '1M':
        short_window = 1  # Краткосрочная средняя на 3 свечи
        long_window = 3  # Долгосрочная средняя на 10 свечей
    elif timeframe == '2M':
        short_window = 3  # Краткосрочная средняя на 5 свечей
        long_window = 7  # Долгосрочная средняя на 15 свечей
    elif timeframe == '3M':
        short_window = 5  # Краткосрочная средняя на 7 свечей
        long_window = 10  # Долгосрочная средняя на 20 свечей
    elif timeframe == '5M':
        short_window = 7  # Краткосрочная средняя на 10 свечей
        long_window = 15  # Долгосрочная средняя на 30 свечей

    # Рассчитываем скользящие средние
    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()
    
    # Отладочный вывод для скользящих средних
    print(f"⚙️ СКОЛЬЗЯЩИЕ РАССЧИТАНЫ ⚙️ для {timeframe}")
    
    return df

def check_for_signal(df, from_symbol, to_symbol, timeframe):
    """
    Проверка пересечения скользящих средних для определения сигналов на покупку/продажу.
    Формирование сообщения о сигнале.
    """
    latest_data = df.iloc[-1]  # Последняя строка данных
    previous_data = df.iloc[-2]  # Предыдущая строка данных
    current_price = latest_data['Close']  # Текущая цена пары

    # Текущие значения скользящих средних
    short_ma = latest_data['Short_MA']
    long_ma = latest_data['Long_MA']

    # Форматируем валютную пару для сообщения
    pair_symbol = f"{from_symbol}/{to_symbol}"

    # Определение риска аналитиков (рандомно 1 или 2)
    risk_assessment = random.choice([1, 2])
    if risk_assessment == 1:
        risk_message = "🟡 ОЦЕНКА РИСКА - 1 🟡"
    else:
        risk_message = "🔴 ОЦЕНКА РИСКА - 2 🔴"

    # Формирование сигнала с MarkdownV2
    if short_ma > long_ma and previous_data['Short_MA'] <= previous_data['Long_MA']:
        # Сигнал на покупку (LONG)
        signal_message = (f"📥 *ДАННЫЕ ПОЛУЧЕНЫ* 📥\n\n"
                          f"⚙️ *СКОЛЬЗЯЩИЕ РАССЧИТАНЫ* ⚙️\n"
                          f"\(S\/MA: {short_ma:.4f}, L\/MA: {long_ma:.4f}\)\n\n"
                          f"🟢 *LONG ⬆️*\n\n"
                          f"💰 *{pair_symbol} 👈🏻*\n\n"
                          f"⌛️ *ВРЕМЯ СДЕЛКИ: {timeframe}*\n\n"
                          f"{risk_message}")
        return 'LONG', signal_message
    elif short_ma < long_ma and previous_data['Short_MA'] >= previous_data['Long_MA']:
        # Сигнал на продажу (SHORT)
        signal_message = (f"📥 *ДАННЫЕ ПОЛУЧЕНЫ* 📥\n\n"
                          f"⚙️ *СКОЛЬЗЯЩИЕ РАССЧИТАНЫ* ⚙️\n"
                          f"\(S\/MA: {short_ma:.4f}, L\/MA: {long_ma:.4f}\)\n\n"
                          f"🔴 *SHORT ⬇️*\n\n"
                          f"💰 *{pair_symbol} 👈🏻*\n\n"
                          f"⌛️ *ВРЕМЯ СДЕЛКИ: {timeframe}*\n\n"
                          f"{risk_message}")
        return 'SHORT', signal_message
    return None, None




async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Функция отправки сигнала в Telegram через бота.
    message_thread_id — используется для отправки сообщений в конкретный топик.
    """
    await bot.send_message(chat_id=chat_id, text=signal_message, parse_mode="MarkdownV2", message_thread_id=message_thread_id)


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

            # Получаем данные валютной пары
            df = await get_currency_data(from_symbol, to_symbol, api_key)

            if df is not None:
                # Проходим по каждому таймфрейму
                for timeframe in timeframes:
                    # Рассчитываем скользящие средние для текущего таймфрейма
                    df_with_ma = calculate_moving_averages(df, timeframe)

                    # Проверяем наличие сигнала
                    signal_type, signal_message = check_for_signal(df_with_ma, from_symbol, to_symbol, timeframe)

                    if signal_message:
                        # Проверяем, изменился ли сигнал для данной валютной пары и таймфрейма
                        signal_key = (from_symbol, to_symbol, timeframe)
                        if last_signals.get(signal_key) != signal_type:
                            # Обновляем последний сигнал
                            last_signals[signal_key] = signal_type
                            
                            # Отправка сигнала в оба канала и топики
                            for channel in channels_and_topics:
                                await notify_signals(
                                    bot,
                                    signal_message,
                                    chat_id=channel['chat_id'],
                                    message_thread_id=channel.get('message_thread_id')
                                )
                            print(f"Отправлен сигнал {signal_type} для {from_symbol}/{to_symbol} на таймфрейме {timeframe}")
                    else:
                        print(f"Сигнал для {from_symbol}/{to_symbol} на таймфрейме {timeframe} не найден.")
            
            # Пауза между запросами для предотвращения превышения лимитов API
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
