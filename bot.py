import os
import ccxt
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

exchange = ccxt.lbank({
    'enableRateLimit': True,
})

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(message) > 3500:
        chunks = [message[i:i+3500] for i in range(0, len(message), 3500)]
    else:
        chunks = [message]
        
    for chunk in chunks:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': chunk
        }
        try:
            response = requests.post(url, json=payload)
            time.sleep(0.5)
        except Exception as e:
            print(f"خطا: {e}")

def check_ema_signals():
    print(f"[{datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M:%S')}] بررسی بازار فیوچرز LBank...")
    try:
        exchange.load_markets()
        symbols = []
        for symbol, market in exchange.markets.items():
            if market.get('linear', False) and market.get('quote') == 'USDT':
                symbols.append(symbol)
        
        if not symbols:
            symbols = [s for s in exchange.symbols if exchange.markets[s].get('swap', False)]

        signals_found = []
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=300)
                if len(ohlcv) < 200:
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['EMA_100'] = df['close'].ewm(span=100, adjust=False).mean()
                df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
                
                prev_candle = df.iloc[-2]
                high, low, close = prev_candle['high'], prev_candle['low'], prev_candle['close']
                ema100, ema200 = prev_candle['EMA_100'], prev_candle['EMA_200']
                
                touched_ema100 = (low <= ema100 <= high) or (abs(close - ema100) / ema100 < 0.001)
                touched_ema200 = (low <= ema200 <= high) or (abs(close - ema200) / ema200 < 0.001)
                
                msg_detail = ""
                if touched_ema100: msg_detail = "EMA 100"
                elif touched_ema200: msg_detail = "EMA 200"
                
                if msg_detail:
                    signals_found.append(f"🚨 {symbol} | برخورد با {msg_detail} | قیمت: {close}\n")
                    
                time.sleep(exchange.rateLimit / 1000)
            except:
                continue
                
        if signals_found:
            header = f"📊 گزارش سیگنال های فیوچرز LBank (تایم 4h)\nتعداد کل: {len(signals_found)}\n\n"
            send_telegram_message(header + "".join(signals_found))
    except Exception as e:
        print(f"خطا: {e}")

if name == "__main__":
    check_ema_signals()
