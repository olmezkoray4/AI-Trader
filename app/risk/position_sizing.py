def calculate_position_size(
    account_balance,
    risk_percent,
    entry_price,
    stop_loss,
    max_leverage=1
):
    risk_amount = account_balance * (risk_percent / 100)

    stop_distance = abs(entry_price - stop_loss)

    if stop_distance == 0:
        return None

    # Risk bazlı pozisyon
    risk_based_quantity = risk_amount / stop_distance
    risk_based_value = risk_based_quantity * entry_price

    # Maksimum izin verilen pozisyon
    max_position_value = account_balance * max_leverage

    # Gerçek kullanılacak pozisyon
    position_value = min(
        risk_based_value,
        max_position_value
    )

    quantity = position_value / entry_price

    # Gerçekte stop olursa kaybedilecek tutar
    actual_risk = quantity * stop_distance

    return {
        "requested_risk": risk_amount,
        "actual_risk": actual_risk,
        "stop_distance": stop_distance,
        "quantity": quantity,
        "position_value": position_value,
        "max_position_value": max_position_value,
    }