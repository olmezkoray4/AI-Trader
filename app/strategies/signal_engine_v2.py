def generate_signal_v2(
    df,
    regime_result,
    volume_result,
    candle_index=-1,
    min_score=70,
):
    """Regime-aware trend-following signal engine.

    V2 deliberately avoids trading RANGE/TRANSITION regimes and requires
    agreement between trend strength, EMA slope, RSI, MACD and volume.
    """
    reasons = []
    score = 0

    if len(df) < 5:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": ["Yetersiz veri"],
        }

    last = df.iloc[candle_index]

    # Use earlier closed bars only.
    absolute_index = len(df) + candle_index if candle_index < 0 else candle_index
    previous_index = max(0, absolute_index - 1)
    slope_index = max(0, absolute_index - 3)

    previous = df.iloc[previous_index]
    slope_reference = df.iloc[slope_index]

    close = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema20_old = float(slope_reference["EMA20"])
    rsi = float(last["RSI"])
    histogram = float(last["MACD_HIST"])
    previous_histogram = float(previous["MACD_HIST"])

    regime = regime_result["regime"]
    adx = float(regime_result["adx"])
    plus_di = float(regime_result["plus_di"])
    minus_di = float(regime_result["minus_di"])
    atr_percent = float(regime_result["atr_percent"])
    ema_spread_percent = float(regime_result["ema_spread_percent"])
    volume_ratio = float(volume_result["ratio"])

    if close == 0:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": ["Geçersiz fiyat"],
        }

    ema20_slope_percent = ((ema20 - ema20_old) / close) * 100

    # -----------------------------------------------------
    # REJİM / VOLATİLİTE FİLTRELERİ
    # -----------------------------------------------------
    if regime not in ("TREND_UP", "TREND_DOWN"):
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": [f"Rejim uygun değil: {regime}"],
        }

    # Extremely quiet or abnormally volatile 5m periods are skipped.
    if atr_percent < 0.05 or atr_percent > 0.90:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": [f"ATR filtresi: {atr_percent:.3f}%"],
        }

    # EMA20/EMA50 are too close: trend structure is weak.
    if ema_spread_percent < 0.03:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": ["EMA yayılımı çok düşük"],
        }

    # Avoid entering directly into exceptional volume spikes.
    if volume_ratio > 1.80:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": [f"Aşırı hacim filtresi: {volume_ratio:.2f}x"],
        }

    # -----------------------------------------------------
    # TREND UP -> LONG
    # -----------------------------------------------------
    if regime == "TREND_UP":
        reasons.append("Rejim: güçlü yükseliş")

        if adx >= 25:
            score += 20
            reasons.append("ADX trendi doğruluyor")

        if plus_di > minus_di:
            score += 15
            reasons.append("+DI üstün")

        if ema20_slope_percent > 0:
            score += 15
            reasons.append("EMA20 eğimi yukarı")

        if 48 <= rsi <= 68:
            score += 15
            reasons.append("RSI trend bölgesinde")

        if histogram > 0:
            score += 15
            reasons.append("MACD histogram pozitif")

            if histogram >= previous_histogram:
                score += 10
                reasons.append("MACD momentumu güçleniyor")

        if 0.80 <= volume_ratio <= 1.80:
            score += 10
            reasons.append("Hacim yeterli")

        decision = "AL" if score >= min_score else "BEKLE"

    # -----------------------------------------------------
    # TREND DOWN -> SHORT
    # -----------------------------------------------------
    else:
        reasons.append("Rejim: güçlü düşüş")

        if adx >= 25:
            score += 20
            reasons.append("ADX trendi doğruluyor")

        if minus_di > plus_di:
            score += 15
            reasons.append("-DI üstün")

        if ema20_slope_percent < 0:
            score += 15
            reasons.append("EMA20 eğimi aşağı")

        # Do not chase heavily oversold candles.
        if 32 <= rsi <= 52:
            score += 15
            reasons.append("RSI düşüş trend bölgesinde")

        if histogram < 0:
            score += 15
            reasons.append("MACD histogram negatif")

            if histogram <= previous_histogram:
                score += 10
                reasons.append("MACD düşüş momentumu güçleniyor")

        if 0.80 <= volume_ratio <= 1.80:
            score += 10
            reasons.append("Hacim yeterli")

        decision = "SAT" if score >= min_score else "BEKLE"

    return {
        "score": score,
        "decision": decision,
        "reasons": reasons,
    }
