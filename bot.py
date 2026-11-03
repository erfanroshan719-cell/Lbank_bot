import os
import time
import ccxt
import pandas as pd
import requests

# اطلاعات از GitHub Secrets خوانده می‌شود
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("خطا: توکن یا چت‌آیدی تلگرام تنظیم نشده است.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"خطا در ارسال پیام به تلگرام: {response.text}")
    except Exception as e:
        print(f"خطای ارتباط با تلگرام: {e}")

def check_ema_signals():
    try:
        exchange = ccxt.lbank({
            'enableRateLimit': True,
        })
        
        # بارگذاری بازار فیوچرز
        exchange.load_markets()
        symbols = [symbol for symbol in exchange.symbols if '/USDT:USDT' in symbol]
        
        if not symbols:
            print("هیچ نماد فیوچرز USDT یافت نشد.")
            return

        signals_found = []

        for symbol in symbols:
            try:
                # دریافت کندل‌های ۴ ساعته
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=250)
                if len(ohlcv) < 200:
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['EMA_100'] = df['close'].ewm(span=100, adjust=False).mean()
                df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
                
                # بررسی کندل بسته شده قبلی (اندیس ۲- از آخر)
                prev_candle = df.iloc[-2]
                low = prev_candle['low']
                ema100, ema200 = prev_candle['EMA_100'], prev_candle['EMA_200']
                
                touched_ema100 = (low <= ema100)
                touched_ema200 = (low <= ema200)
                
                msg_detail = ""
                if touched_ema100: msg_detail = f"برخورد با EMA 100 📉 (قیمت پایین: {low}, مقدار EMA: {ema100:.2f})"
                elif touched_ema200: msg_detail = f"برخورد با EMA 200 📉 (قیمت پایین: {low}, مقدار EMA: {ema200:.2f})"
                
                if msg_detail:
                    signals_found.append(f"🔹 *{symbol}*\n{msg_detail}")
                
                time.sleep(exchange.rateLimit / 1000)
            except Exception:
                continue

        if signals_found:
            header = "🚨 گزارش سیگنال‌های فیوچرز LBank 🚨\n\n" + "\n".join(signals_found)
            send_telegram_message(header)
        else:
            status_message = "🤖 **گزارش ربات LBank**\n\nبازار ۴ ساعته اسکن شد. در حال حاضر هیچ برخورد با EMA 100 یا EMA 200 یافت نشد."
            send_telegram_message(status_message)

    except Exception as e:
        print(f"خطا: {e}")

if __name__ == "__main__":
    check_ema_signals()
