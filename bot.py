import os
import time
import ccxt
import pandas as pd
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("خطا: توکن یا چت‌آیدی تلگرام تنظیم نشده است.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    max_length = 4000
    if len(message) > max_length:
        parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
    else:
        parts = [message]
        
    for part in parts:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": part,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                print(f"خطا در ارسال پیام به تلگرام: {response.text}")
        except Exception as e:
            print(f"خطای ارتباط با تلگرام: {e}")
        time.sleep(0.5)

def check_ema_signals():
    try:
        exchange = ccxt.lbank({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap'
            }
        })
        
        exchange.load_markets()
        symbols = [symbol for symbol in exchange.symbols if '/USDT' in symbol]
        
        print(f"تعداد کل نمادهای فیوچرز یافت شده: {len(symbols)}")
        
        if not symbols:
            print("هیچ نماد فیوچرز USDT یافت نشد.")
            send_telegram_message("⚠️ ربات هشدار: هیچ نماد فیوچرز USDT برای اسکن یافت نشد!")
            return

        signals_found = []
        checked_count = 0

        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=250)
                if len(ohlcv) < 200:
                    continue
                
                checked_count += 1
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['EMA_100'] = df['close'].ewm(span=100, adjust=False).mean()
                df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
                
                current_candle = df.iloc[-1]
                prev_candle = df.iloc[-2]
                
                symbol_messages = []
                
                # بررسی مستقل EMA 100 برای کندل جاری
                if current_candle['low'] <= current_candle['EMA_100'] <= current_candle['high']:
                    symbol_messages.append(f"• کندل جاری: برخورد با EMA 100 📉 (کف: {current_candle['low']}, سقف: {current_candle['high']} | EMA: {current_candle['EMA_100']:.4f})")
                
                # بررسی مستقل EMA 200 برای کندل جاری
                if current_candle['low'] <= current_candle['EMA_200'] <= current_candle['high']:
                    symbol_messages.append(f"• کندل جاری: برخورد با EMA 200 📉 (کف: {current_candle['low']}, سقف: {current_candle['HIGH'] if 'HIGH' in current_candle else current_candle['high']}, EMA: {current_candle['EMA_200']:.4f})")

                # بررسی مستقل EMA 100 برای کندل قبلی
                if prev_candle['low'] <= prev_candle['EMA_100'] <= prev_candle['high']:
                    symbol_messages.append(f"• کندل قبلی: برخورد با EMA 100 📉 (کف: {prev_candle['low']}, سقف: {prev_candle['high']} | EMA: {prev_candle['EMA_100']:.4f})")
                
                # بررسی مستقل EMA 200 برای کندل قبلی
                if prev_candle['low'] <= prev_candle['EMA_200'] <= prev_candle['high']:
                    symbol_messages.append(f"• کندل قبلی: برخورد با EMA 200 📉 (کف: {prev_candle['low']}, سقف: {prev_candle['high']} | EMA: {prev_candle['EMA_200']:.4f})")
                
                if symbol_messages:
                    details_str = "\n".join(symbol_messages)
                    signals_found.append(f"🔹 *{symbol}*\n{details_str}")
                
                time.sleep(exchange.rateLimit / 1000)
            except Exception as e:
                continue

        print(f"تعداد ارزهایی که با موفقیت اسکن شدند: {checked_count}")

        if signals_found:
            header = "🚨 **گزارش سیگنال‌های برخورد با EMA (فیوچرز LBank)** 🚨\n\n" + "\n\n".join(signals_found)
            send_telegram_message(header)
        else:
            status_message = f"🤖 **گزارش ربات LBank**\n\nبازار ۴ ساعته اسکن شد.\nتعداد کل ارزهای بررسی‌شده: {checked_count}\nوضعیت: هیچ برخوردی با EMA 100 یا EMA 200 یافت نشد."
            send_telegram_message(status_message)

    except Exception as e:
        print(f"خطای کلی در اجرای ربات: {e}")

if __name__ == "__main__":
    check_ema_signals()
