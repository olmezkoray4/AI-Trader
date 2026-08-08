import requests
import pandas as pd


def get_klines(symbol="BTCUSDT", interval="1m", limit=100):
    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "OpenTime", "Open", "High", "Low", "Close",
        "Volume", "CloseTime", "QuoteVolume",
        "Trades", "TakerBase", "TakerQuote", "Ignore"
    ])

    df = df[["OpenTime", "Open", "High", "Low", "Close", "Volume"]]

    df["Open"] = df["Open"].astype(float)
    df["High"] = df["High"].astype(float)
    df["Low"] = df["Low"].astype(float)
    df["Close"] = df["Close"].astype(float)
    df["Volume"] = df["Volume"].astype(float)

    return df


if __name__ == "__main__":
    df = get_klines()

    print(df.tail())
    