import requests
import time
import logging
from telegram import Bot
import asyncio

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

# Генерация случайного сигнала
def generate_random_signal(asset):
    current_price = random.uniform(1.0, 2.0)  # Генерация случайной цены для примера
    direction = random.choice(['LONG', 'SHORT'])  # Случайный выбор направления
    
    # Расчет уровня стоп-лосса
    stop_loss = current_price - (current_price * 0.02) if direction == 'LONG' else current_price + (current_price * 0.02)
    
    # Расчет динамического риска
    dynamic_risk = risk_percentage * current_price
    
    # Формирование сигнала
    signal = f"""
🟢 {direction} 🔼

💵 {asset}

Цена входа:🔼 {current_price:.5f}

⛔️STOP-DOBOR; 💥 ➖ {stop_loss:.5f}

🦠 риск; 🥵 ➖ {dynamic_risk:.2f}%
"""
    logging.info(f"Generated random signal for {asset}: {signal}")
    return signal

# Отправка сигнала в Telegram
async def send_signal(signal):
    for channel in channels:
        await bot.send_message(chat_id=channel['chat_id'], text=signal, message_thread_id=channel['message_thread_id'])
    logging.info(f"Signal sent: {signal}")

# Основной цикл получения данных и отправки сигналов
async def run_bot():
    logging.info("Bot is starting...")
    while True:
        try:
            for asset in assets['forex']:
                data = get_data(asset)
                if not data:  # Пропускаем, если данные не получены
                    continue
                
                signal = generate_random_signal(asset)

                # Отправляем сигнал, если он сгенерирован
                await send_signal(signal)

            await asyncio.sleep(10)  # Пауза между запросами для всех активов (5 минут)
        except Exception as e:
            logging.error(f"Error: {e}")
            await asyncio.sleep(10)  # В случае ошибки делаем паузу

if __name__ == "__main__":
    asyncio.run(run_bot())
