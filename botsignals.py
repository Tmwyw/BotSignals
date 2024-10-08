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
logging.basicConfig(filename='bot_logs.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Валютные пары для отслеживания
assets = {
    'forex': ['EUR/USD', 'USD/JPY', 'GBP/USD', 'AUD/USD', 'USD/CAD', 'NZD/USD', 'CHF/JPY']
}

# Параметры
risk_percentage = 0.35  # Риск 35%

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
    logging.info(f"Fetching data for {symbol}. Response: {response.status_code}")
    
    if response.status_code != 200:
        logging.error(f"Error fetching data for {symbol}: {response.text}")
        return {}

    return response.json()

# Определение уровней Фибоначчи
def calculate_fibonacci_levels(prices):
    max_price = max(prices)
    min_price = min(prices)
    
    # Уровни Фибоначчи
    levels = {
        "0.0%": max_price,
        "23.6%": max_price - (max_price - min_price) * 0.236,
        "38.2%": max_price - (max_price - min_price) * 0.382,
        "50.0%": (max_price + min_price) / 2,
        "61.8%": max_price - (max_price - min_price) * 0.618,
        "100%": min_price
    }
    
    logging.info(f"Fibonacci levels: {levels}")
    return levels

# Генерация сигнала на основе уровней Фибоначчи
def generate_signal(data, asset):
    prices = [float(candle['4. close']) for candle in data['Time Series FX (1min)'].values()]
    
    if len(prices) < 2:
        logging.info("Not enough data to generate signal.")
        return None
    
    fibonacci_levels = calculate_fibonacci_levels(prices)
    current_price = prices[-1]

    # Предполагаем, что цена может достичь этих уровней
    long_entry_price = fibonacci_levels["23.6%"]  # Уровень для LONG сигнала
    stop_loss = fibonacci_levels["61.8%"]  # Уровень для STOP LOSS
    take_profit_1 = fibonacci_levels["38.2%"]  # Первый уровень тейк-профита
    take_profit_2 = fibonacci_levels["50.0%"]  # Второй уровень тейк-профита
    
    # Формирование сигнала
    signal = f"""
🟢 LONG 🔼

💵 {asset}

Цена входа:🔼 {long_entry_price:.5f}

🎯Take Profit 1️⃣: 📌 ➖ {take_profit_1:.5f}
🎯Take Profit 2️⃣: 📌 ➖ {take_profit_2:.5f}

⛔️STOP-DOBOR; 💥 ➖ {stop_loss:.5f}

🦠 риск; 🥵 ➖ {risk_percentage * 100:.2f}%
"""
    
    logging.info(f"Generated signal for {asset}: {signal}")
    return signal

# Отправка сигнала в Telegram
def send_signal(signal):
    for channel in channels:
        bot.send_message(chat_id=channel['chat_id'], text=signal, message_thread_id=channel['message_thread_id'])
    logging.info(f"Signal sent: {signal}")

# Основной цикл получения данных и отправки сигналов
def run_bot():
    logging.info("Bot is starting...")
    while True:
        try:
            for asset in assets['forex']:
                data = get_data(asset)
                if not data:  # Пропускаем, если данные не получены
                    continue
                    
                signal = generate_signal(data, asset)

                # Отправляем сигнал, если он сгенерирован
                if signal:
                    send_signal(signal)

            time.sleep(300)  # Пауза между запросами для всех активов (5 минут)
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(60)  # В случае ошибки делаем паузу

if __name__ == "__main__":
    run_bot()
