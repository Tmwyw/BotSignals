import os
from PIL import Image, ImageDraw, ImageFont
import asyncio
from telegram import Bot
from itertools import cycle
import pandas as pd
import requests
import random
import time

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

# Хранение последних сигналов с информацией о последней цене и времени отправки
last_signals = {}

# Тайм лимит для отправки сигналов (10 минут = 600 секунд)
time_limit = 600  # Время в секундах между отправкой сигналов для одной валютной пары
price_threshold_percentage = 0.002  # Порог изменения цены 0.5%

# Приоритет таймфреймов (вес для каждого таймфрейма)
timeframes = {'1M': 1, '2M': 1.5, '3M': 2, '5M': 2.5}

from PIL import Image, ImageDraw, ImageFont

from PIL import Image, ImageDraw, ImageFont

from PIL import Image, ImageDraw, ImageFont
import os

def generate_image(from_symbol, to_symbol, signal_type):
    width, height = 600, 300
    image = Image.new('RGB', (width, height), color=(245, 245, 220))  # Бежевый фон
    draw = ImageDraw.Draw(image)

    # Путь к файлу шрифта
    font_path = os.path.join('fonts', 'arial_black.ttf')

    # Загружаем шрифт
    try:
        font_large = ImageFont.truetype(font_path, 1000)
        font_small = ImageFont.truetype(font_path, 800)
    except OSError:
        print("Не удалось загрузить шрифт. Используем шрифт по умолчанию.")
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Текст для изображения
    text_large = f"Сигнал: {signal_type}"
    text_small = f"{from_symbol}/{to_symbol}"

    # Определение цвета для LONG/SHORT
    if signal_type == 'LONG':
        text_color = (0, 255, 0)  # Зеленый для LONG
    else:
        text_color = (255, 0, 0)  # Красный для SHORT

    # Получаем размеры текста
    text_large_bbox = draw.textbbox((0, 0), text_large, font=font_large)
    text_large_width = text_large_bbox[2] - text_large_bbox[0]
    text_large_height = text_large_bbox[3] - text_large_bbox[1]

    text_small_bbox = draw.textbbox((0, 0), text_small, font=font_small)
    text_small_width = text_small_bbox[2] - text_small_bbox[0]
    text_small_height = text_small_bbox[3] - text_small_bbox[1]

    # Координаты для размещения текста по центру
    text_large_x = (width - text_large_width) // 2
    text_large_y = (height - text_large_height) // 2 - 50

    text_small_x = (width - text_small_width) // 2
    text_small_y = text_large_y + text_large_height + 20

    # Рисуем текст на изображении
    draw.text((text_large_x, text_large_y), text_large, font=font_large, fill=(0, 0, 0))
    draw.text((text_small_x, text_small_y), text_small, font=font_small, fill=(0, 0, 0))

    # Сохранение изображения
    image_path = f"{from_symbol}_{to_symbol}_{signal_type}.png"
    image.save(image_path)

    return image_path



async def get_currency_data(from_symbol, to_symbol, api_key):
    url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&entitlement=realtime&apikey={api_key}'
    response = requests.get(url)
    data = response.json()

    try:
        time_series = data['Time Series FX (Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.rename(columns={'4. close': 'Close'})
        df['Close'] = df['Close'].astype(float)
        df = df.sort_index()
        print(f"📥 ДАННЫЕ ПОЛУЧЕНЫ 📥 для {from_symbol}/{to_symbol}")
        return df
    except KeyError:
        print(f"Ошибка в получении данных от API ключа {api_key}: {data}")
        return None

def calculate_moving_averages(df, timeframe):
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

    df['Short_MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long_MA'] = df['Close'].rolling(window=long_window).mean()
    
    print(f"⚙️ СКОЛЬЗЯЩИЕ РАССЧИТАНЫ ⚙️ для {timeframe}")
    return df

def check_for_signal(df, from_symbol, to_symbol, timeframe):
    latest_data = df.iloc[-1]
    current_price = latest_data['Close']

    short_ma = latest_data['Short_MA']
    long_ma = latest_data['Long_MA']
    pair_symbol = f"{from_symbol}/{to_symbol}"

    risk_assessment = random.choice([1, 2])
    risk_message = f"☑️ Присвоена оценка риска - {risk_assessment}️⃣"

    if short_ma > long_ma:
        signal_message = (f"📊 Данные получены:\n"
                          f"⚙️ Скользящие рассчитаны\n"
                          f"(S/MA: {short_ma:.4f}, L/MA: {long_ma:.4f})\n"
                          f"{risk_message}\n"
                          f"➖➖➖➖➖➖➖➖➖➖\n"
                          f"💰{pair_symbol}💰\n\n"
                          f"🟢LONG🟢\n\n"
                          f"⌛️ВРЕМЯ СДЕЛКИ: {timeframe}")
        image_path = generate_image(from_symbol, to_symbol, 'LONG')
        return 'LONG', current_price, signal_message, abs(short_ma - long_ma) * timeframes[timeframe], image_path
    elif short_ma < long_ma:
        signal_message = (f"📊 Данные получены:\n"
                          f"⚙️ Скользящие рассчитаны\n"
                          f"(S/MA: {short_ma:.4f}, L/MA: {long_ma:.4f})\n"
                          f"{risk_message}\n"
                          f"➖➖➖➖➖➖➖➖➖➖\n"
                          f"💰{pair_symbol}💰\n\n"
                          f"🔴SHORT🔴\n\n"
                          f"⌛️ВРЕМЯ СДЕЛКИ: {timeframe}")
        image_path = generate_image(from_symbol, to_symbol, 'SHORT')
        return 'SHORT', current_price, signal_message, abs(short_ma - long_ma) * timeframes[timeframe], image_path
    return None, None, None, None, None

def mirror_signal(signal_type):
    """Функция для зеркалирования сигнала"""
    if signal_type == 'LONG':
        return 'SHORT'
    elif signal_type == 'SHORT':
        return 'LONG'

async def notify_signals(bot, signal_message, image_path, chat_id, message_thread_id=None):
    try:
        print(f"Отправка сообщения в чат {chat_id} с топиком {message_thread_id}")
        print(f"Сообщение: {signal_message}")
        
        await bot.send_photo(chat_id=chat_id, photo=open(image_path, 'rb'), caption=signal_message, message_thread_id=message_thread_id)
        await asyncio.sleep(1)  # Задержка перед следующим запросом
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

async def main():
    token = '7449818362:AAHrejKv90PyRkrgMTdZvHzT9p44ePlZYcg'
    bot = Bot(token=token)

    channels_and_topics = [
        {'chat_id': '-1002243376132', 'message_thread_id': '2'},  # Основной канал
        {'chat_id': '-1002290780268', 'message_thread_id': '4'},  # Зеркальный канал
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

            df = await get_currency_data(from_symbol, to_symbol, api_key)

            if df is not None:
                best_signal = None
                best_score = -1

                for timeframe in timeframes:
                    df_with_ma = calculate_moving_averages(df, timeframe)

                    signal_type, current_price, signal_message, score, image_path = check_for_signal(df_with_ma, from_symbol, to_symbol, timeframe)

                    if signal_message and score > best_score:
                        best_signal = (signal_type, current_price, signal_message, image_path)
                        best_score = score

                if best_signal:
                    signal_type, current_price, signal_message, image_path = best_signal
                    signal_key = (from_symbol, to_symbol)

                    last_signal = last_signals.get(signal_key, {'price': None, 'time': 0})

                    price_change = abs((current_price - last_signal['price']) / last_signal['price']) if last_signal['price'] else None
                    time_since_last_signal = time.time() - last_signal['time']

                    if (last_signal['price'] is None or price_change >= price_threshold_percentage) and time_since_last_signal >= time_limit:
                        last_signals[signal_key] = {'price': current_price, 'signal_type': signal_type, 'time': time.time()}

                        # Отправляем сигнал в основной канал
                        await notify_signals(
                            bot,
                            signal_message,
                            image_path,
                            chat_id=channels_and_topics[0]['chat_id'],
                            message_thread_id=channels_and_topics[0].get('message_thread_id')
                        )
                        
                        # Зеркальный сигнал для второго канала
                        mirrored_signal_type = mirror_signal(signal_type)
                        mirrored_image_path = generate_image(from_symbol, to_symbol, mirrored_signal_type)
                        mirrored_signal_message = signal_message.replace(signal_type, mirrored_signal_type)

                        # Отправляем зеркальный сигнал во второй канал
                        await notify_signals(
                            bot,
                            mirrored_signal_message,
                            mirrored_image_path,
                            chat_id=channels_and_topics[1]['chat_id'],
                            message_thread_id=channels_and_topics[1].get('message_thread_id')
                        )

                        print(f"Отправлен сигнал {signal_type} для {from_symbol}/{to_symbol}, цена: {current_price}")
                    else:
                        print(f"Изменение цены для {from_symbol}/{to_symbol} недостаточно для отправки сигнала")

            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
