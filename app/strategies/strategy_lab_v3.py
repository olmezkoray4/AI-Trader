def _result(decision="BEKLE", score=0, reasons=None):
    return {
        "score": score,
        "decision": decision,
        "reasons": reasons or [],
    }


def generate_breakout_signal(
    df,
    candle_index=-1,
    lookback=40,
    adx_min=20.0,
    volume_min=0.90,
    allow_long=True,
    allow_short=True,
):
    """Donchian-style close breakout using only earlier candles."""
    absolute_index = len(df) + candle_index if candle_index < 0 else candle_index

    if absolute_index < max(lookback, 200):
        return _result(reasons=["Yetersiz veri"])

    last = df.iloc[absolute_index]
    history = df.iloc[absolute_index - lookback:absolute_index]

    upper = float(history["High"].max())
    lower = float(history["Low"].min())

    close = float(last["Close"])
    ema50 = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    adx = float(last["ADX"])
    plus_di = float(last["PLUS_DI"])
    minus_di = float(last["MINUS_DI"])
    histogram = float(last["MACD_HIST"])

    volume_ma = float(last["VOLUME_MA"])
    volume_ratio = float(last["Volume"]) / volume_ma if volume_ma > 0 else 0.0

    if adx < adx_min:
        return _result(reasons=[f"ADX düşük: {adx:.1f}"])

    if volume_ratio < volume_min:
        return _result(reasons=[f"Hacim düşük: {volume_ratio:.2f}x"])

    long_setup = (
        allow_long
        and close > upper
        and ema50 > ema200
        and plus_di > minus_di
        and histogram > 0
    )

    short_setup = (
        allow_short
        and close < lower
        and ema50 < ema200
        and minus_di > plus_di
        and histogram < 0
    )

    if long_setup:
        return _result(
            decision="AL",
            score=100,
            reasons=[
                f"{lookback} mum yukarı breakout",
                "EMA50 > EMA200",
                "+DI üstün",
                "MACD pozitif",
                f"Hacim {volume_ratio:.2f}x",
            ],
        )

    if short_setup:
        return _result(
            decision="SAT",
            score=-100,
            reasons=[
                f"{lookback} mum aşağı breakout",
                "EMA50 < EMA200",
                "-DI üstün",
                "MACD negatif",
                f"Hacim {volume_ratio:.2f}x",
            ],
        )

    return _result(reasons=["Breakout yok"])


def generate_pullback_signal(
    df,
    candle_index=-1,
    adx_min=20.0,
    ema_tolerance_percent=0.20,
    allow_long=True,
    allow_short=True,
):
    """Trend pullback entry around EMA20 with momentum confirmation."""
    absolute_index = len(df) + candle_index if candle_index < 0 else candle_index

    if absolute_index < 200:
        return _result(reasons=["Yetersiz veri"])

    last = df.iloc[absolute_index]
    previous = df.iloc[absolute_index - 1]

    close = float(last["Close"])
    high = float(last["High"])
    low = float(last["Low"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    ema200 = float(last["EMA200"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    plus_di = float(last["PLUS_DI"])
    minus_di = float(last["MINUS_DI"])
    hist = float(last["MACD_HIST"])
    previous_hist = float(previous["MACD_HIST"])

    tolerance = close * (ema_tolerance_percent / 100.0)

    if adx < adx_min:
        return _result(reasons=[f"ADX düşük: {adx:.1f}"])

    long_trend = ema20 > ema50 > ema200 and plus_di > minus_di
    short_trend = ema20 < ema50 < ema200 and minus_di > plus_di

    long_pullback = (
        allow_long
        and long_trend
        and low <= ema20 + tolerance
        and close >= ema20
        and 42 <= rsi <= 62
        and hist > 0
        and hist >= previous_hist
    )

    short_pullback = (
        allow_short
        and short_trend
        and high >= ema20 - tolerance
        and close <= ema20
        and 38 <= rsi <= 58
        and hist < 0
        and hist <= previous_hist
    )

    if long_pullback:
        return _result(
            decision="AL",
            score=100,
            reasons=[
                "Yükseliş trendinde EMA20 pullback",
                "RSI dengeli",
                "MACD momentumu toparlanıyor",
            ],
        )

    if short_pullback:
        return _result(
            decision="SAT",
            score=-100,
            reasons=[
                "Düşüş trendinde EMA20 pullback",
                "RSI dengeli",
                "MACD düşüş momentumu güçleniyor",
            ],
        )

    return _result(reasons=["Pullback koşulu yok"])


def generate_mean_reversion_signal(
    df,
    candle_index=-1,
    adx_max=18.0,
    bb_std_multiplier=2.0,
    rsi_extreme=30,
    allow_long=True,
    allow_short=True,
):
    """Range-only Bollinger/RSI mean-reversion entry."""
    absolute_index = len(df) + candle_index if candle_index < 0 else candle_index

    if absolute_index < 200:
        return _result(reasons=["Yetersiz veri"])

    last = df.iloc[absolute_index]
    previous = df.iloc[absolute_index - 1]

    close = float(last["Close"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    middle = float(last["BB_MID"])
    std = float(last["BB_STD"])
    hist = float(last["MACD_HIST"])
    previous_hist = float(previous["MACD_HIST"])

    if std <= 0:
        return _result(reasons=["Bollinger verisi yetersiz"])

    if adx > adx_max:
        return _result(reasons=[f"Range değil, ADX {adx:.1f}"])

    upper = middle + (std * bb_std_multiplier)
    lower = middle - (std * bb_std_multiplier)

    long_setup = (
        allow_long
        and close < lower
        and rsi <= rsi_extreme
        and hist >= previous_hist
    )

    short_setup = (
        allow_short
        and close > upper
        and rsi >= (100 - rsi_extreme)
        and hist <= previous_hist
    )

    if long_setup:
        return _result(
            decision="AL",
            score=100,
            reasons=[
                "Range rejiminde alt Bollinger taşması",
                f"RSI aşırı satım: {rsi:.1f}",
                "MACD kötüleşmiyor",
            ],
        )

    if short_setup:
        return _result(
            decision="SAT",
            score=-100,
            reasons=[
                "Range rejiminde üst Bollinger taşması",
                f"RSI aşırı alım: {rsi:.1f}",
                "MACD güçlenmiyor",
            ],
        )

    return _result(reasons=["Mean-reversion koşulu yok"])
