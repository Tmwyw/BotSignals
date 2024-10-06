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

# Параметры EMA (уменьшены для большей чувствительности)
short_ema_period = 9
long_ema_period = 21

# Параметры RSI (меньше для более частых сигналов)
rsi_period = 14
overbought = 60  # Более мягкий порог для перекупленности
oversold = 40  # Более мягкий порог для перепроданности

# Получение данных с Alpha Vantage
def get_data(symbol, interval):
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'datatype': 'json',
        'outputsize': 'compact'
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

# Вычисление RSI
def calculate_rsi(prices, period):
    gains = [0]
    losses = [0]
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = []
    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    
    # Логируем рассчитанный RSI
    logging.info(f"RSI for period {period}: {rsi}")
    
    return rsi

# Вычисление MACD
def calculate_macd(prices):
    short_ema = calculate_ema(prices, short_ema_period)
    long_ema = calculate_ema(prices, long_ema_period)
    macd = [s - l for s, l in zip(short_ema, long_ema)]
    signal_line = calculate_ema(macd, 6)  # Уменьшен период для сигнальной линии до 6
    
    # Логируем MACD и сигнальную линию
    logging.info(f"MACD: {macd}")
    logging.info(f"Signal Line: {signal_line}")
    
    return macd, signal_line

# Проверка условий для сигналов
def check_signals(data):
    prices = [float(candle['4. close']) for candle in data.values()]
    
    # Логируем текущие цены
    logging.info(f"Prices: {prices}")
    
    short_ema = calculate_ema(prices, short_ema_period)
    long_ema = calculate_ema(prices, long_ema_period)
    rsi = calculate_rsi(prices, rsi_period)
    macd, signal_line = calculate_macd(prices)

    # Логируем значения индикаторов
    logging.info(f"Short EMA: {short_ema[-1]}, Long EMA: {long_ema[-1]}, RSI: {rsi[-1]}, MACD: {macd[-1]}, Signal Line: {signal_line[-1]}")

    # Условия для лонга
    if short_ema[-1] > long_ema[-1] and rsi[-1] < oversold and macd[-1] > signal_line[-1]:
        logging.info(f"Signal: LONG")
        return 'LONG', prices[-1]
    
    # Условия для шорта
    elif short_ema[-1] < long_ema[-1] and rsi[-1] > overbought and macd[-1] < signal_line[-1]:
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
def analyze_trend(symbol):
    # Анализ тренда на 15-минутном таймфрейме
    data = get_data(symbol, '15min')
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
    timeframes = ['1min', '2min', '3min', '5min']  # Таймфреймы для анализа
    while True:
        try:
            for asset in assets['forex'] + assets['stocks']:
                trend = analyze_trend(asset)
                for timeframe in timeframes:
                    data = get_data(asset, timeframe)
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
