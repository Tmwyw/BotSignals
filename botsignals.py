import requests
import time
import logging
from telegram import Bot

# Конфигурации API
API_KEY = 'QSPA6IIRC5CGQU43'  # Ключ Alpha Vantage
API_URL = 'https://www.alphavantage.co/query'
TELEGRAM_BOT_TOKEN = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Конфигурации каналов Telegram
channels = [
    {'chat_id': '-1002243376132', 'message_thread_id': '2'},  # Первый канал, топик
    {'chat_id': '-1002290780268', 'message_thread_id': '4'}   # Второй канал, топик
]

# Настройка логов
logging.basicConfig(filename='bot_logs.log', level=logging.INFO)

# Валютные пары и акции для отслеживания
assets = {
    'forex': ['EUR_USD', 'USD_TRY', 'GBP_USD', 'EUR_AUD', 'EUR_CHF', 'USD_ZAR'],
    'stocks': ['INTC', 'MSFT', 'KO', 'LTC']
}

# Параметры EMA
short_ema_period = 5
long_ema_period = 10

# Таймфреймы для валютных пар и акций
forex_timeframes = ['1min', '5min', '15min', '30min', '60min']
stocks_timeframes = ['1min', '5min', '15min', '30min', '60min']

# Получение данных с Alpha Vantage с учетом типов активов
def get_data(symbol, interval, asset_type):
    function = 'FX_INTRADAY' if asset_type == 'forex' else 'TIME_SERIES_INTRADAY'
    params = {
        'function': function,
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'datatype': 'json',
        'outputsize': 'compact',
        'entitlement': 'realtime'  # Добавляем параметр для реальных данных
    }
    response = requests.get(API_URL, params=params)
    
    # Логируем полученные данные
    logging.info(f"Data for {symbol} ({interval}): {response.json()}")
    
    return response.json()

# Вычисление EMA
def calculate_ema(prices, period):
    ema = [sum(prices[:period]) / period]  # Первая EMA - среднее значение первых "period" цен
    multiplier = 2 / (period + 1)
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    
    # Логируем рассчитанную EMA
    logging.info(f"EMA for period {period}: {ema}")
    
    return ema

# Проверка условий для сигналов на основе пересечения EMA
def check_signals(data):
    prices = [float(candle['4. close']) for candle in data.values()]
    
    # Логируем текущие цены
    logging.info(f"Prices: {prices}")
    
    short_ema = calculate_ema(prices, short_ema_period)
    long_ema = calculate_ema(prices, long_ema_period)

    # Логируем значения EMA
    logging.info(f"Short EMA: {short_ema[-1]}, Long EMA: {long_ema[-1]}")

    # Условия для лонга
    if short_ema[-1] > long_ema[-1]:
        logging.info(f"Signal: LONG")
        return 'LONG', prices[-1]
    
    # Условия для шорта
    elif short_ema[-1] < long_ema[-1]:
        logging.info(f"Signal: SHORT")
        return 'SHORT', prices[-1]

    logging.info(f"No signals generated.")
    return None, None

# Отправка сигнала в Telegram
def send_signal(direction, asset, price):
    signal = f"⬆️ LONG 🟢\n🔥 {asset} 👈🏻\n💵 Текущая цена: {price} 📈" if direction == 'LONG' else \
             f"⬇️ SHORT 🔴\n🔥 {asset} 👈🏻\n💵 Текущая цена: {price} 📉"
    
    for channel in channels:
        bot.send_message(chat_id=channel['chat_id'], text=signal, message_thread_id=channel['message_thread_id'])
    
    logging.info(f"Signal sent: {direction} {asset} at {price}")

# Анализ трендов на более долгом таймфрейме
def analyze_trend(symbol, asset_type):
    # Анализ тренда на 15-минутном таймфрейме
    data = get_data(symbol, '15min', asset_type)
    prices = [float(candle['4. close']) for candle in data['Time Series (15min)'].values()]
    long_ema = calculate_ema(prices, long_ema_period)
    short_ema = calculate_ema(prices, short_ema_period)
    
    # Логируем тренд
    if short_ema[-1] > long_ema[-1]:
        logging.info(f"Trend: UPTREND for {symbol}")
        return 'UPTREND'
    else:
        logging.info(f"Trend: DOWNTREND for {symbol}")
        return 'DOWNTREND'

# Основной цикл получения данных и отправки сигналов
def run_bot():
    while True:
        try:
            for asset_type, asset_list in assets.items():
                timeframes = forex_timeframes if asset_type == 'forex' else stocks_timeframes
                for asset in asset_list:
                    trend = analyze_trend(asset, asset_type)
                    for timeframe in timeframes:
                        data = get_data(asset, timeframe, asset_type)
                        signals, price = check_signals(data[f"Time Series ({timeframe})"])
                        
                        # Логируем сигналы
                        logging.info(f"Checking signals for {asset} on {timeframe} timeframe")
                        
                        # Отправляем сигнал только если тренд совпадает с направлением
                        if signals == 'LONG' and trend == 'UPTREND':
                            send_signal(signals, asset, price)
                        elif signals == 'SHORT' and trend == 'DOWNTREND':
                            send_signal(signals, asset, price)
            time.sleep(30)  # Пауза между запросами для всех активов
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(60)  # В случае ошибки делаем паузу

if __name__ == "__main__":
    run_bot()
