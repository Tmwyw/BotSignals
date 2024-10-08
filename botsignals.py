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

# Валютные пары для отслеживания
assets = {
    'forex': ['EUR/USD', 'USD/JPY', 'GBP/USD', 'AUD/USD', 'USD/CAD', 'NZD/USD', 'CHF/JPY']
}

# Параметры RSI
rsi_period = 7
overbought_threshold = 80  # Уровень перекупленности
oversold_threshold = 20     # Уровень перепроданности

# Получение данных с Alpha Vantage
def get_data(symbol):
    params = {
        'function': 'FX_INTRADAY',
        'symbol': symbol,
        'interval': '1min',  # Используем 1-минутный интервал
        'apikey': API_KEY,
        'datatype': 'json',
        'outputsize': 'compact',
    }
    response = requests.get(API_URL, params=params)
    
    # Логируем полученные данные
    logging.info(f"Data for {symbol}: {response.json()}")
    
    return response.json()

# Вычисление RSI
def calculate_rsi(prices, period):
    if len(prices) < period:
        logging.info("Not enough data to calculate RSI.")
        return None
    
    deltas = [j - i for i, j in zip(prices[:-1], prices[1:])]
    gain = sum(x for x in deltas if x > 0) / period
    loss = -sum(x for x in deltas if x < 0) / period
    rs = gain / loss if loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    
    logging.info(f"RSI for period {period}: {rsi}")
    
    return rsi

# Проверка условий для сигналов на основе RSI
def check_signals(data):
    prices = [float(candle['4. close']) for candle in data['Time Series FX (1min)'].values()]
    
    # Логируем текущие цены
    logging.info(f"Prices: {prices}")
    
    rsi = calculate_rsi(prices, rsi_period)

    # Условия для лонга
    if rsi is not None and rsi < oversold_threshold:
        logging.info(f"Signal: LONG (RSI: {rsi})")
        return 'LONG', prices[-1]
    
    # Условия для шорта
    elif rsi is not None and rsi > overbought_threshold:
        logging.info(f"Signal: SHORT (RSI: {rsi})")
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

# Основной цикл получения данных и отправки сигналов
def run_bot():
    while True:
        try:
            for asset in assets['forex']:
                data = get_data(asset)
                signals, price = check_signals(data)

                # Логируем сигналы
                logging.info(f"Checking signals for {asset}")

                # Отправляем сигнал, если он сгенерирован
                if signals:
                    send_signal(signals, asset, price)
            time.sleep(30)  # Пауза между запросами для всех активов
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(60)  # В случае ошибки делаем паузу

if __name__ == "__main__":
    run_bot()
