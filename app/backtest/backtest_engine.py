from app.risk.risk_manager import calculate_trade_levels
from app.risk.position_sizing import calculate_position_size
from app.risk.costs import calculate_trade_costs


def run_backtest(
    df,
    signal_function,
    initial_balance=10000,
    risk_percent=1,
    max_leverage=1,
    max_hold_bars=60,
    min_stop_percent=0.3,
    atr_multiplier=2.0,
    reward_multiplier=1.5,
    commission_percent=0.04,
    slippage_percent=0.02,
    charge_exit_costs=True,
):
    """Run a one-position-at-a-time OHLC backtest.

    The signal is generated at the close of bar i and the entry is executed at
    the next bar's open. Costs are charged on both entry and exit by default.
    Commission/slippage values are assumptions for testing, not exchange fees.
    """
    balance = float(initial_balance)
    peak_balance = float(initial_balance)
    trades = []

    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    take_profit_count = 0
    stop_loss_count = 0
    time_exit_count = 0
    max_drawdown = 0.0

    long_trades = 0
    long_wins = 0
    long_losses = 0
    long_profit = 0.0
    long_loss = 0.0

    short_trades = 0
    short_wins = 0
    short_losses = 0
    short_profit = 0.0
    short_loss = 0.0

    # EMA200 and other long lookbacks need warm-up history.
    i = 200

    while i < len(df) - 2 and balance > 0:
        current_df = df.iloc[: i + 1].copy()
        signal_result = signal_function(current_df)

        decision = signal_result.get("decision", "BEKLE")
        signal_score = signal_result.get("score", 0)
        signal_reasons = signal_result.get("reasons", [])

        if decision == "BEKLE":
            i += 1
            continue

        # Signal is known only after bar i closes. Enter at next bar open.
        entry_index = i + 1
        if entry_index >= len(df):
            break

        entry = float(df["Open"].iloc[entry_index])
        atr = float(df["ATR"].iloc[i])

        if atr <= 0:
            i += 1
            continue

        trade_levels = calculate_trade_levels(
            decision,
            entry,
            atr,
            min_stop_percent=min_stop_percent,
            atr_multiplier=atr_multiplier,
            reward_multiplier=reward_multiplier,
        )

        if trade_levels is None:
            i += 1
            continue

        position = calculate_position_size(
            account_balance=balance,
            risk_percent=risk_percent,
            entry_price=trade_levels["entry"],
            stop_loss=trade_levels["stop_loss"],
            max_leverage=max_leverage,
        )

        if position is None or position["quantity"] <= 0:
            i += 1
            continue

        side = trade_levels["side"]
        stop_loss = float(trade_levels["stop_loss"])
        take_profit = float(trade_levels["take_profit"])
        quantity = float(position["quantity"])

        entry_costs = calculate_trade_costs(
            position_value=float(position["position_value"]),
            commission_percent=commission_percent,
            slippage_percent=slippage_percent,
        )

        exit_price = None
        exit_reason = None
        exit_index = None

        last_bar = min(
            entry_index + max_hold_bars - 1,
            len(df) - 1,
        )

        for j in range(entry_index, last_bar + 1):
            high = float(df["High"].iloc[j])
            low = float(df["Low"].iloc[j])

            if side == "LONG":
                stop_hit = low <= stop_loss
                target_hit = high >= take_profit

                # OHLC cannot tell which was hit first. Use conservative stop.
                if stop_hit and target_hit:
                    exit_price = stop_loss
                    exit_reason = "STOP LOSS"
                    exit_index = j
                    break
                if stop_hit:
                    exit_price = stop_loss
                    exit_reason = "STOP LOSS"
                    exit_index = j
                    break
                if target_hit:
                    exit_price = take_profit
                    exit_reason = "TAKE PROFIT"
                    exit_index = j
                    break

            elif side == "SHORT":
                stop_hit = high >= stop_loss
                target_hit = low <= take_profit

                if stop_hit and target_hit:
                    exit_price = stop_loss
                    exit_reason = "STOP LOSS"
                    exit_index = j
                    break
                if stop_hit:
                    exit_price = stop_loss
                    exit_reason = "STOP LOSS"
                    exit_index = j
                    break
                if target_hit:
                    exit_price = take_profit
                    exit_reason = "TAKE PROFIT"
                    exit_index = j
                    break

        if exit_price is None:
            exit_index = last_bar
            exit_price = float(df["Close"].iloc[exit_index])
            exit_reason = "TIME EXIT"

        if side == "LONG":
            gross_pnl = (exit_price - entry) * quantity
        else:
            gross_pnl = (entry - exit_price) * quantity

        if charge_exit_costs:
            exit_costs = calculate_trade_costs(
                position_value=abs(quantity * exit_price),
                commission_percent=commission_percent,
                slippage_percent=slippage_percent,
            )
        else:
            exit_costs = {
                "commission": 0.0,
                "slippage": 0.0,
                "total_cost": 0.0,
            }

        total_cost = entry_costs["total_cost"] + exit_costs["total_cost"]
        net_pnl = gross_pnl - total_cost

        if exit_reason == "TAKE PROFIT":
            take_profit_count += 1
        elif exit_reason == "STOP LOSS":
            stop_loss_count += 1
        elif exit_reason == "TIME EXIT":
            time_exit_count += 1

        if side == "LONG":
            long_trades += 1
            if net_pnl > 0:
                long_wins += 1
                long_profit += net_pnl
            else:
                long_losses += 1
                long_loss += abs(net_pnl)
        else:
            short_trades += 1
            if net_pnl > 0:
                short_wins += 1
                short_profit += net_pnl
            else:
                short_losses += 1
                short_loss += abs(net_pnl)

        balance += net_pnl

        if net_pnl > 0:
            wins += 1
            gross_profit += net_pnl
        else:
            losses += 1
            gross_loss += abs(net_pnl)

        peak_balance = max(peak_balance, balance)
        drawdown = (
            ((peak_balance - balance) / peak_balance) * 100
            if peak_balance > 0
            else 0.0
        )
        max_drawdown = max(max_drawdown, drawdown)

        trades.append(
            {
                "signal_index": i,
                "entry_index": entry_index,
                "exit_index": exit_index,
                "decision": decision,
                "score": signal_score,
                "reasons": list(signal_reasons),
                "side": side,
                "entry": entry,
                "exit": exit_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_reason": exit_reason,
                "quantity": quantity,
                "requested_risk": position.get("requested_risk"),
                "actual_risk": position.get("actual_risk"),
                "gross_pnl": gross_pnl,
                "entry_cost": entry_costs["total_cost"],
                "exit_cost": exit_costs["total_cost"],
                "cost": total_cost,
                "net_pnl": net_pnl,
                "balance": balance,
            }
        )

        # One open position at a time.
        i = exit_index + 1

    total_trades = len(trades)
    win_rate = (wins / total_trades) * 100 if total_trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    net_profit = balance - initial_balance

    long_win_rate = (long_wins / long_trades) * 100 if long_trades else 0.0
    long_profit_factor = long_profit / long_loss if long_loss > 0 else 0.0
    long_net = long_profit - long_loss

    short_win_rate = (short_wins / short_trades) * 100 if short_trades else 0.0
    short_profit_factor = short_profit / short_loss if short_loss > 0 else 0.0
    short_net = short_profit - short_loss

    return {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "net_profit": net_profit,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "take_profit_count": take_profit_count,
        "stop_loss_count": stop_loss_count,
        "time_exit_count": time_exit_count,
        "long_trades": long_trades,
        "long_wins": long_wins,
        "long_losses": long_losses,
        "long_win_rate": long_win_rate,
        "long_profit_factor": long_profit_factor,
        "long_net": long_net,
        "short_trades": short_trades,
        "short_wins": short_wins,
        "short_losses": short_losses,
        "short_win_rate": short_win_rate,
        "short_profit_factor": short_profit_factor,
        "short_net": short_net,
        "trades": trades,
    }
