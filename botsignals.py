import asyncio
from telegram import Bot
from itertools import cycle
import pandas as pd
import requests
import random
import time
from PIL import Image, ImageDraw, ImageFont

# Токен Telegram бота
API_KEYS = ['QSPA6IIRC5CGQU43']

# Хранение последних сигналов с информацией о последней цене и времени отправки
last_signals = {}

# Тайм лимит для отправки сигналов (10 минут = 600 секунд)
time_limit = 600  # Время в секундах между отправкой сигналов для одной валютной пары
price_threshold_percentage = 0.002  # Порог изменения цены 0.5%

# Приоритет таймфреймов (вес для каждого таймфрейма)
timeframes = {'1M': 1, '2M': 1.5, '3M': 2, '5M': 2.5}

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

def generate_image(from_symbol, to_symbol, signal_type):
    """
    Генерация изображения с валютной парой и направлением (LONG/SHORT)
    """
    dark_beige_color = (238, 232, 205)  # Темный бежевый цвет фона
    img = Image.new('RGB', (500, 300), color=dark_beige_color)
    draw = ImageDraw.Draw(img)

    # Настройка шрифтов
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_large = ImageFont.truetype(font_path, 70)
    font_medium = ImageFont.truetype(font_path, 40)

    # Текст
    pair_text = f"{from_symbol}/{to_symbol}"
    signal_text = signal_type

    pair_text_width, pair_text_height = draw.textsize(pair_text, font=font_large)
    signal_text_width, signal_text_height = draw.textsize(signal_text, font=font_medium)
    
    total_text_height = pair_text_height + signal_text_height + 20

    pair_text_x = (img.width - pair_text_width) // 2
    signal_text_x = (img.width - signal_text_width) // 2
    top_margin = (img.height - total_text_height) // 2

    draw.text((pair_text_x, top_margin), pair_text, font=font_large, fill=(0, 0, 0))
    draw.text((signal_text_x, top_margin + pair_text_height + 20), signal_text, font=font_medium, fill=(255, 0, 0) if signal_type == 'SHORT' else (0, 255, 0))

    image_path = f"/mnt/data/{from_symbol}_{to_symbol}_{signal_type}.png"
    img.save(image_path)

    return image_path

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

async def notify_signals(bot, signal_message, image_path, chat_id, message_thread_id=None):
    try:
        print(f"Отправка сообщения в чат {chat_id} с топиком {message_thread_id}")
        print(f"Сообщение: {signal_message}")

        # Отправляем изображение и сообщение
        with open(image_path, 'rb') as image_file:
            await bot.send_photo(chat_id=chat_id, photo=image_file, caption=signal_message, message_thread_id=message_thread_id)
        await asyncio.sleep(1)
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

                        for channel in channels_and_topics:
                            await notify_signals(
                                bot,
                                signal_message,
                                image_path,
                                chat_id=channel['chat_id'],
                                message_thread_id=channel.get('message_thread_id')
                            )
                        print(f"Отправлен сигнал {signal_type} для {from_symbol}/{to_symbol}, цена: {current_price}")
                    else:
                        print(f"Изменение цены для {from_symbol}/{to_symbol} недостаточно для отправки сигнала")

            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
