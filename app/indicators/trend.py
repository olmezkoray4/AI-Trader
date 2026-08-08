def detect_trend(df, candle_index=-2):
    ema20 = df["EMA20"].iloc[candle_index]
    ema50 = df["EMA50"].iloc[candle_index]
    ema200 = df["EMA200"].iloc[candle_index]

    if ema20 > ema50 > ema200:
        return "YÜKSELİŞ 📈"

    elif ema20 < ema50 < ema200:
        return "DÜŞÜŞ 📉"

    else:
        return "YATAY ➖"