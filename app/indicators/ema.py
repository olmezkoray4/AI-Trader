import pandas as pd


def calculate_ema(df, period=20):
    """
    EMA (Exponential Moving Average) hesaplar.
    """

    ema = df["Close"].ewm(span=period, adjust=False).mean()

    return ema
