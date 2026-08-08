def calculate_trade_levels(
    decision,
    last_close,
    last_atr,
    min_stop_percent=0.3,
    atr_multiplier=2.0,
    reward_multiplier=1.5
):
    decision = decision.upper()

    # ATR'ye göre stop mesafesi
    atr_stop_distance = last_atr * atr_multiplier

    # Fiyata göre minimum stop mesafesi
    minimum_stop_distance = last_close * (min_stop_percent / 100)

    # İki stop mesafesinden daha büyük olanı kullan
    stop_distance = max(
        atr_stop_distance,
        minimum_stop_distance
    )

    # Take Profit mesafesi
    take_profit_distance = stop_distance * reward_multiplier

    # LONG işlemi
    if decision in ["AL", "GÜÇLÜ AL"]:
        stop_loss = last_close - stop_distance
        take_profit = last_close + take_profit_distance

        return {
            "side": "LONG",
            "entry": last_close,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_distance": stop_distance,
            "risk_reward": reward_multiplier,
        }

    # SHORT işlemi
    elif decision in ["SAT", "GÜÇLÜ SAT"]:
        stop_loss = last_close + stop_distance
        take_profit = last_close - take_profit_distance

        return {
            "side": "SHORT",
            "entry": last_close,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_distance": stop_distance,
            "risk_reward": reward_multiplier,
        }

    # BEKLE sinyali
    return None