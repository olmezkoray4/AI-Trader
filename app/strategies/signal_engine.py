def generate_signal(
    df,
    trend,
    volume_result,
    candle_index=-2
):
    score = 0
    reasons = []

    last = df.iloc[candle_index]

    # 1. TREND PUANI
    if "YÜKSELİŞ" in trend:
        score += 30
        reasons.append("EMA trendi yukarı")

    elif "DÜŞÜŞ" in trend:
        score -= 30
        reasons.append("EMA trendi aşağı")

    else:
        reasons.append("EMA trendi yatay")

    # 2. RSI PUANI
    rsi = last["RSI"]

    if 50 <= rsi < 70:
        score += 15
        reasons.append("RSI pozitif bölgede")

    elif 30 < rsi < 50:
        score -= 5
        reasons.append("RSI zayıf bölgede")

    elif rsi <= 30:
        score += 10
        reasons.append("RSI aşırı satım bölgesinde")

    elif rsi >= 70:
        score -= 10
        reasons.append("RSI aşırı alım bölgesinde")

    # 3. MACD PUANI
    macd = last["MACD"]
    macd_signal = last["MACD_SIGNAL"]
    histogram = last["MACD_HIST"]

    if macd > macd_signal and histogram > 0:
        score += 25
        reasons.append("MACD pozitif")

    elif macd < macd_signal and histogram < 0:
        score -= 25
        reasons.append("MACD negatif")

    else:
        reasons.append("MACD kararsız")

    # 4. HACİM PUANI
    volume_ratio = volume_result["ratio"]

    if volume_ratio >= 1.5:
        score += 20
        reasons.append("Hacim çok güçlü")

    elif volume_ratio >= 1.1:
        score += 10
        reasons.append("Hacim güçlü")

    elif volume_ratio < 0.8:
        score -= 15
        reasons.append("Hacim düşük")

    else:
        reasons.append("Hacim normal")

    # 5. NİHAİ KARAR
    trend_up = "YÜKSELİŞ" in trend
    trend_down = "DÜŞÜŞ" in trend

    # LONG işlemleri geçici olarak kapalı
    if score >= 60 and trend_up:
        decision = "BEKLE"

    elif score >= 35 and trend_up:
        decision = "BEKLE"

    # SHORT işlemleri açık
    elif score <= -60 and trend_down:
        decision = "GÜÇLÜ SAT"

    elif score <= -35 and trend_down:
        decision = "SAT"

    else:
        decision = "BEKLE"

    return {
        "score": score,
        "decision": decision,
        "reasons": reasons,
    }
    # SHORT kalite filtresi
    if trend_down:

    # Kötü kombinasyon:
    # RSI zayıf + MACD negatif + aşırı güçlü hacim
     if (
        30 < rsi < 50
        and macd < macd_signal
        and histogram < 0
        and volume_ratio >= 1.5
    ):
        decision = "BEKLE"

    # Daha güçlü SHORT adayı
    elif (
        rsi <= 30
        and macd < macd_signal
        and histogram < 0
        and 0.8 <= volume_ratio < 1.1
    ):
        decision = "SAT"

    else:
        decision = "BEKLE"