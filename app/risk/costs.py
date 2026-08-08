def calculate_trade_costs(
    position_value,
    commission_percent=0.1,
    slippage_percent=0.05
):
    commission = position_value * (commission_percent / 100)
    slippage = position_value * (slippage_percent / 100)

    total_cost = commission + slippage

    return {
        "commission": commission,
        "slippage": slippage,
        "total_cost": total_cost,
    }