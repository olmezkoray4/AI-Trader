def detect_market_regime(df, candle_index=-1, adx_trend_threshold=25.0, adx_range_threshold=18.0):
    """Classify the current market into trend/range/transition regimes."""
    last = df.iloc[candle_index]

    close = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    adx = float(last["ADX"])
    plus_di = float(last["PLUS_DI"])
    minus_di = float(last["MINUS_DI"])
    atr = float(last["ATR"])

    atr_percent = (atr / close) * 100 if close else 0.0
    ema_spread_percent = (abs(ema20 - ema50) / close) * 100 if close else 0.0

    trend_up = (
        adx >= adx_trend_threshold
        and ema20 > ema50 > ema200
        and plus_di > minus_di
    )

    trend_down = (
        adx >= adx_trend_threshold
        and ema20 < ema50 < ema200
        and minus_di > plus_di
    )

    if trend_up:
        regime = "TREND_UP"
    elif trend_down:
        regime = "TREND_DOWN"
    elif adx < adx_range_threshold:
        regime = "RANGE"
    else:
        regime = "TRANSITION"

    return {
        "regime": regime,
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "atr_percent": atr_percent,
        "ema_spread_percent": ema_spread_percent,
    }
