from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from itertools import cycle
import pandas as pd
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']
is_active = False  # Флаг активности

async def get_sma_data(from_symbol, to_symbol, api_key, interval='5min', time_period=10):
    symbol = f"{from_symbol}{to_symbol}"
    url = f'https://www.alphavantage.co/query?function=SMA&symbol={symbol}&interval={interval}&time_period={time_period}&series_type=close&entitlement=realtime&apikey={api_key}'
    
    response = requests.get(url)
    data = response.json()

    try:
        time_series = data['Technical Analysis: SMA']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'SMA': 'SMA'})
        df['SMA'] = df['SMA'].astype(float)
        df = df.sort_index()
        logging.info(f"Данные SMA получены для пары {from_symbol}/{to_symbol}")
        return df
    except KeyError:
        logging.error(f"Ошибка в получении данных от API для пары {from_symbol}/{to_symbol}: {data}")
        return None

def choose_time_frame(df):
    last_crosses = df['SMA'].diff()
    last_cross_sign = last_crosses.apply(lambda x: 1 if x > 0 else -1)
    last_cross_index = (last_cross_sign != last_cross_sign.shift(1)).idxmax()
    candles_since_cross = len(df) - df.index.get_loc(last_cross_index)

    if candles_since_cross <= 2:
        return "1M"
    elif candles_since_cross <= 5:
        return "2M"
    else:
        return "5M"

def check_for_signal(df, from_symbol, to_symbol, last_signals):
    latest_data = df.iloc[-1]
    previous_data = df.iloc[-2]
    current_sma = latest_data['SMA']
    pair_symbol = f"{from_symbol}/{to_symbol}"
    time_frame = choose_time_frame(df)

    if current_sma > previous_data['SMA'] and last_signals.get(pair_symbol) != 'LONG':
        last_signals[pair_symbol] = 'LONG'
        signal_message = (f"🔥LONG🟢🔼\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📈 {current_sma:.4f}")
        logging.info(f"Сигнал на покупку для {pair_symbol}")
        return signal_message
    elif current_sma < previous_data['SMA'] and last_signals.get(pair_symbol) != 'SHORT':
        last_signals[pair_symbol] = 'SHORT'
        signal_message = (f"🔥SHORT🔴🔽\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📉 {current_sma:.4f}")
        logging.info(f"Сигнал на продажу для {pair_symbol}")
        return signal_message
    return None

async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    logging.info(f"Отправка сигнала в канал {chat_id}")
    await bot.send_message(chat_id=chat_id, text=signal_message, message_thread_id=message_thread_id)

async def signal_loop(bot, last_signals):
    channels_and_topics = [
        {'chat_id': '-1002243376132', 'message_thread_id': '2'},
        {'chat_id': '-1002290780268', 'message_thread_id': '4'},
    ]
    
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

    api_keys_cycle = cycle(API_KEYS)

    while True:
        if not is_active:
            await asyncio.sleep(5)
            continue

        for from_symbol, to_symbol in currency_pairs:
            api_key = next(api_keys_cycle)
            df_sma = await get_sma_data(from_symbol, to_symbol, api_key)

            if df_sma is not None:
                signal_message = check_for_signal(df_sma, from_symbol, to_symbol, last_signals)
                if signal_message:
                    for channel in channels_and_topics:
                        await notify_signals(
                            bot,
                            signal_message,
                            chat_id=channel['chat_id'],
                            message_thread_id=channel.get('message_thread_id')
                        )
            
            await asyncio.sleep(5)

def startbot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_active
    is_active = True
    logging.info("Бот запущен командой /startbot")
    update.message.reply_text('Бот запущен!')
    
def stopbot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_active
    is_active = False
    logging.info("Бот остановлен командой /stopbot")
    update.message.reply_text('Бот остановлен!')

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    bot = Bot(token=token)
    last_signals = {}

    # Создаем приложение с использованием нового синтаксиса
    application = Application.builder().token(token).build()

    # Инициализация приложения
    await application.initialize()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("startbot", startbot))
    application.add_handler(CommandHandler("stopbot", stopbot))

    # Запускаем бота
    logging.info("Запуск бота...")
    await application.start()

    # Запускаем цикл для сигналов
    await signal_loop(bot, last_signals)

    # Завершаем приложение
    await application.stop()

if __name__ == '__main__':
    asyncio.run(main())
