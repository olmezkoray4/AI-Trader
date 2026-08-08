def calculate_macd(df, fast=12, slow=26, signal=9):
    close = df["Close"]

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram

