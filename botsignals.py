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
price_threshold_percentage = 0.002  # Порог изменения цены 0.2%

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


def generate_image_with_even_bigger_text(from_symbol, to_symbol, signal_type):
    # Создание изображения с бежевым фоном
    img = Image.new('RGB', (512, 256), color=(238, 224, 200))  # Бежевый цвет фона
    draw = ImageDraw.Draw(img)

    try:
        # Использование стандартных шрифтов для текста
        font_large = ImageFont.load_default()  # Стандартный шрифт
        font_small = ImageFont.load_default()
    except IOError:
        print("Ошибка загрузки шрифта.")
        return None

    # Тексты для пары валют и сигнала
    text_large = f"{from_symbol}/{to_symbol}"
    text_small = signal_type

    # Определение позиции текста для выравнивания по центру
    text_large_size = draw.textbbox((0, 0), text_large, font=font_large)
    text_small_size = draw.textbbox((0, 0), text_small, font=font_small)

    # Позиции для текста
    position_large = ((512 - text_large_size[2]) // 2, (256 - text_large_size[3]) // 2 - 50)
    position_small = ((512 - text_small_size[2]) // 2, (256 - text_small_size[3]) // 2 + 50)

    # Рисование текста
    draw.text(position_large, text_large, font=font_large, fill=(0, 0, 0))  # Чёрный текст
    draw.text(position_small, text_small, font=font_small, fill=(0, 255, 0) if signal_type == 'LONG' else (255, 0, 0))  # Зелёный для LONG, красный для SHORT

    # Проверка и создание директории для сохранения
    output_dir = "/mnt/data/"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Путь для сохранения изображения
    image_path = os.path.join(output_dir, "even_bigger_text_image.png")

    # Сохранение изображения
    img.save(image_path)

    return image_path

# Пример использования
image_path = generate_image_with_even_bigger_text("USD", "EUR", "LONG")
print(f"Изображение сохранено в: {image_path}")
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
        
        await bot.send_photo(chat_id=chat_id, photo=open(image_path, 'rb'), caption=signal_message, message_thread_id=message_thread_id)
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
