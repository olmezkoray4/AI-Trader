import time
from datetime import datetime
from binance_client import get_btc_price

last_price = None

while True:
    try:
        price = float(get_btc_price())

        if last_price is None:
            direction = "-"
        elif price > last_price:
            direction = "▲"
        elif price < last_price:
            direction = "▼"
        else:
            direction = "="

        now = datetime.now().strftime("%H:%M:%S")

        print(f"{now} | BTCUSDT | {price:,.2f} | {direction}")

        last_price = price

        time.sleep(1)

    except Exception as e:
        print("Hata:", e)
        time.sleep(5)
        