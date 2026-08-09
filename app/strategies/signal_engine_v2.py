def generate_signal_v2(
    df,
    regime_result,
    volume_result,
    candle_index=-1,
    min_score=70,
    allow_long=True,
    allow_short=True,
    atr_min_percent=0.05,
    atr_max_percent=0.90,
    ema_spread_min_percent=0.03,
    volume_min_ratio=0.80,
    volume_max_ratio=1.80,
    long_rsi_min=48,
    long_rsi_max=68,
    short_rsi_min=32,
    short_rsi_max=52,
):
    """Regime-aware trend-following signal engine.

    Parameters are explicit so the optimizer can test configurations without
    rewriting strategy code. The function only uses data available up to the
    selected candle.
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

    if close <= 0:
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

    if atr_percent < atr_min_percent or atr_percent > atr_max_percent:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": [f"ATR filtresi: {atr_percent:.3f}%"],
        }

    if ema_spread_percent < ema_spread_min_percent:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": ["EMA yayılımı çok düşük"],
        }

    if volume_ratio > volume_max_ratio:
        return {
            "score": 0,
            "decision": "BEKLE",
            "reasons": [f"Aşırı hacim filtresi: {volume_ratio:.2f}x"],
        }

    # -----------------------------------------------------
    # TREND UP -> LONG
    # -----------------------------------------------------
    if regime == "TREND_UP":
        if not allow_long:
            return {
                "score": 0,
                "decision": "BEKLE",
                "reasons": ["LONG devre dışı"],
            }

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

        if long_rsi_min <= rsi <= long_rsi_max:
            score += 15
            reasons.append("RSI trend bölgesinde")

        if histogram > 0:
            score += 15
            reasons.append("MACD histogram pozitif")

            if histogram >= previous_histogram:
                score += 10
                reasons.append("MACD momentumu güçleniyor")

        if volume_min_ratio <= volume_ratio <= volume_max_ratio:
            score += 10
            reasons.append("Hacim yeterli")

        decision = "AL" if score >= min_score else "BEKLE"

    # -----------------------------------------------------
    # TREND DOWN -> SHORT
    # -----------------------------------------------------
    else:
        if not allow_short:
            return {
                "score": 0,
                "decision": "BEKLE",
                "reasons": ["SHORT devre dışı"],
            }

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

        if short_rsi_min <= rsi <= short_rsi_max:
            score += 15
            reasons.append("RSI düşüş trend bölgesinde")

        if histogram < 0:
            score += 15
            reasons.append("MACD histogram negatif")

            if histogram <= previous_histogram:
                score += 10
                reasons.append("MACD düşüş momentumu güçleniyor")

        if volume_min_ratio <= volume_ratio <= volume_max_ratio:
            score += 10
            reasons.append("Hacim yeterli")

        decision = "SAT" if score >= min_score else "BEKLE"

    return {
        "score": score,
        "decision": decision,
        "reasons": reasons,
    }
