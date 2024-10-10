import asyncio
from telegram import Bot
from itertools import cycle
import pandas as pd
import requests
import random  # Для генерации случайной оценки риска

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

# Хранение последних сигналов для валютных пар и таймфреймов
last_signals = {}  # Будет хранить последнюю цену и тип сигнала
price_threshold_percentage = 0.005  # Порог изменения цены в 5% (0.05 = 5%)

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
        short_window = 1
        long_window = 3
    elif timeframe == '2M':
        short_window = 3
        long_window = 7
    elif timeframe == '3M':
        short_window = 5
        long_window = 10
    elif timeframe == '5M':
        short_window = 7
        long_window = 15

    # Рассчитываем скользящие средние
    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()
    
    print(f"⚙️ СКОЛЬЗЯЩИЕ РАССЧИТАНЫ ⚙️ для {timeframe}")
    
    return df

def check_for_signal(df, from_symbol, to_symbol, timeframe):
    """
    Проверка пересечения скользящих средних для определения сигналов на покупку/продажу.
    Формирование сообщения о сигнале.
    """
    latest_data = df.iloc[-1]  # Последняя строка данных
    current_price = latest_data['Close']  # Текущая цена пары

    short_ma = latest_data['Short_MA']
    long_ma = latest_data['Long_MA']
    pair_symbol = f"{from_symbol}/{to_symbol}"

    # Определение риска аналитиков (рандомно 1 или 2)
    risk_assessment = random.choice([1, 2])
    if risk_assessment == 1:
        risk_message = "🟡 ОЦЕНКА РИСКА - 1 🟡"
    else:
        risk_message = "🔴 ОЦЕНКА РИСКА - 2 🔴"

    if short_ma > long_ma:
        # Сигнал на покупку (LONG)
        signal_message = (f"📥 ДАННЫЕ ПОЛУЧЕНЫ 📥\n\n"
                          f"⚙️ СКОЛЬЗЯЩИЕ РАССЧИТАНЫ ⚙️\n"
                          f"(S/MA: {short_ma:.4f}, L/MA: {long_ma:.4f})\n\n"
                          f"🟢 LONG ⬆️\n\n"
                          f"💰 {pair_symbol} 👈🏻\n\n"
                          f"⌛️ ВРЕМЯ СДЕЛКИ: {timeframe}\n\n"
                          f"{risk_message}")
        return 'LONG', current_price, signal_message
    elif short_ma < long_ma:
        # Сигнал на продажу (SHORT)
        signal_message = (f"📥 ДАННЫЕ ПОЛУЧЕНЫ 📥\n\n"
                          f"⚙️ СКОЛЬЗЯЩИЕ РАССЧИТАНЫ ⚙️\n"
                          f"(S/MA: {short_ma:.4f}, L/MA: {long_ma:.4f})\n\n"
                          f"🔴 SHORT ⬇️\n\n"
                          f"💰 {pair_symbol} 👈🏻\n\n"
                          f"⌛️ ВРЕМЯ СДЕЛКИ: {timeframe}\n\n"
                          f"{risk_message}")
        return 'SHORT', current_price, signal_message
    return None, None, None

async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Функция отправки сигнала в Telegram через бота.
    message_thread_id — используется для отправки сообщений в конкретный топик.
    """
    try:
        print(f"Отправка сообщения в чат {chat_id} с топиком {message_thread_id}")
        print(f"Сообщение: {signal_message}")
        
        await bot.send_message(chat_id=chat_id, text=signal_message, message_thread_id=message_thread_id)
        await asyncio.sleep(1)  # Задержка перед следующим запросом
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    bot = Bot(token=token)

    channels_and_topics = [
        {'chat_id': '-1002243376132', 'message_thread_id': '2'},
        {'chat_id': '-1002290780268', 'message_thread_id': '4'},
    ]
    
    currency_pairs = [
        ('EUR', 'USD'),  
        ('GBP', 'USD'),  
        ('USD', 'CHF'),  
        ('AUD', 'CAD'),  
        ('EUR', 'GBP'),  
        ('USD', 'MXN'),  
    ]

    api_keys_cycle = cycle(API_KEYS)

    while True:
        for from_symbol, to_symbol in currency_pairs:
            api_key = next(api_keys_cycle)

            # Получаем данные валютной пары
            df = await get_currency_data(from_symbol, to_symbol, api_key)

            if df is not None:
                for timeframe in timeframes:
                    # Рассчитываем скользящие средние для текущего таймфрейма
                    df_with_ma = calculate_moving_averages(df, timeframe)

                    # Проверяем наличие сигнала
                    signal_type, current_price, signal_message = check_for_signal(df_with_ma, from_symbol, to_symbol, timeframe)

                    if signal_message:
                        signal_key = (from_symbol, to_symbol, timeframe)
                        last_signal = last_signals.get(signal_key, {'price': None})

                        # Рассчитываем процент изменения цены
                        if last_signal['price'] is None or abs((current_price - last_signal['price']) / last_signal['price']) >= price_threshold_percentage:
                            last_signals[signal_key] = {'price': current_price, 'signal_type': signal_type}

                            for channel in channels_and_topics:
                                await notify_signals(
                                    bot,
                                    signal_message,
                                    chat_id=channel['chat_id'],
                                    message_thread_id=channel.get('message_thread_id')
                                )
                            print(f"Отправлен сигнал {signal_type} для {from_symbol}/{to_symbol} на таймфрейме {timeframe}, цена: {current_price}")
                        else:
                            print(f"Изменение цены для {from_symbol}/{to_symbol} недостаточно для отправки сигнала")
                    else:
                        print(f"Сигнал для {from_symbol}/{to_symbol} на таймфрейме {timeframe} не найден.")
            
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
