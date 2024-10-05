from telegram import Bot, Update
import time
from itertools import cycle
import pandas as pd
import requests
import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']
is_active = False  # Флаг активности

async def get_sma_data(from_symbol, to_symbol, api_key, interval='5min', time_period=10):
    """
    Получение данных SMA о валютной паре с Alpha Vantage API.
    """
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
        return df
    except KeyError:
        print("Ошибка в получении данных от API:", data)
        return None

def choose_time_frame(df):
    """
    Определение времени сделки на основе движения скользящей средней (SMA).
    """
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
    """
    Проверка движения скользящей средней для определения сигналов на покупку/продажу.
    Формирование сообщения о сигнале.
    """
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
        return signal_message
    elif current_sma < previous_data['SMA'] and last_signals.get(pair_symbol) != 'SHORT':
        last_signals[pair_symbol] = 'SHORT'
        signal_message = (f"🔥SHORT🔴🔽\n🔥#{pair_symbol}☝️\n"
                          f"⌛️Время сделки: {time_frame}\n"
                          f"💵Текущая цена:📉 {current_sma:.4f}")
        return signal_message
    return None

async def notify_signals(bot, signal_message, chat_id, message_thread_id=None):
    """
    Асинхронная функция отправки сигнала в Telegram через бота.
    """
    await bot.send_message(chat_id=chat_id, text=signal_message, message_thread_id=message_thread_id)

async def signal_loop(bot, last_signals):
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'

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

def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_active
    is_active = True
    update.message.reply_text('Бот запущен!')
    
def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_active
    is_active = False
    update.message.reply_text('Бот остановлен!')

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    bot = Bot(token=token)
    last_signals = {}

    # Создаем приложение с использованием нового синтаксиса
    application = Application.builder().token(token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    # Создаем асинхронную задачу для цикла сигналов
    loop = asyncio.get_event_loop()
    loop.create_task(signal_loop(bot, last_signals))

    # Запускаем бота
    await application.start()
    await application.updater.start_polling()

    # Ожидаем завершения
    await application.updater.idle()

if __name__ == '__main__':
    asyncio.run(main())
