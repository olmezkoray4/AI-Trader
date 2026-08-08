import requests


def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

    response = requests.get(url)

    data = response.json()


    return data["price"]


if __name__ == "__main__":
    print("BTC Fiyatı:", get_btc_price())
    