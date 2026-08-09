from math import inf

from app.risk.costs import calculate_trade_costs
from app.risk.position_sizing import calculate_position_size


def run_trailing_breakout_backtest(
    df,
    lookback=40,
    adx_min=20.0,
    initial_atr_mult=2.5,
    trail_atr_mult=3.0,
    side_mode="BOTH",
    initial_balance=10000,
    risk_percent=1.0,
    max_leverage=1.0,
    max_hold_bars=720,
    commission_percent=0.04,
    slippage_percent=0.02,
    start_index=200,
    end_index=None,
):
    """Backtest a Donchian breakout with an ATR trailing stop.

    Signal is formed at bar i close and entry occurs at bar i+1 open.
    The trailing stop is updated only after the current bar has been checked,
    so the newly calculated stop can only become active on the next bar.
    This avoids same-bar lookahead from using a bar's high/low to create and
    trigger a stop simultaneously.
    """
    upper_col = f"DONCHIAN_UPPER_{lookback}"
    lower_col = f"DONCHIAN_LOWER_{lookback}"

    required = {
        "Open",
        "High",
        "Low",
        "Close",
        "ATR",
        "ADX",
        "PLUS_DI",
        "MINUS_DI",
        "EMA50",
        "EMA200",
        upper_col,
        lower_col,
    }

    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Eksik kolonlar: {missing}")

    opens = df["Open"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    closes = df["Close"].to_numpy(dtype=float)
    atrs = df["ATR"].to_numpy(dtype=float)
    adxs = df["ADX"].to_numpy(dtype=float)
    plus_dis = df["PLUS_DI"].to_numpy(dtype=float)
    minus_dis = df["MINUS_DI"].to_numpy(dtype=float)
    ema50s = df["EMA50"].to_numpy(dtype=float)
    ema200s = df["EMA200"].to_numpy(dtype=float)
    uppers = df[upper_col].to_numpy(dtype=float)
    lowers = df[lower_col].to_numpy(dtype=float)

    data_end = len(df) if end_index is None else min(int(end_index), len(df))
    i = max(int(start_index), 200, lookback + 1)

    balance = float(initial_balance)
    peak_balance = float(initial_balance)
    max_drawdown = 0.0

    trades = []
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    long_trades = 0
    long_net = 0.0
    short_trades = 0
    short_net = 0.0

    allow_long = side_mode in ("LONG_ONLY", "BOTH")
    allow_short = side_mode in ("SHORT_ONLY", "BOTH")

    while i < data_end - 1 and balance > 0:
        if not (
            atrs[i] > 0
            and adxs[i] >= adx_min
            and uppers[i] == uppers[i]
            and lowers[i] == lowers[i]
        ):
            i += 1
            continue

        long_signal = (
            allow_long
            and closes[i] > uppers[i]
            and ema50s[i] > ema200s[i]
            and plus_dis[i] > minus_dis[i]
        )

        short_signal = (
            allow_short
            and closes[i] < lowers[i]
            and ema50s[i] < ema200s[i]
            and minus_dis[i] > plus_dis[i]
        )

        if not long_signal and not short_signal:
            i += 1
            continue

        side = "LONG" if long_signal else "SHORT"
        entry_index = i + 1

        if entry_index >= data_end:
            break

        entry = opens[entry_index]
        initial_stop_distance = atrs[i] * initial_atr_mult

        if entry <= 0 or initial_stop_distance <= 0:
            i += 1
            continue

        if side == "LONG":
            stop = entry - initial_stop_distance
        else:
            stop = entry + initial_stop_distance

        position = calculate_position_size(
            account_balance=balance,
            risk_percent=risk_percent,
            entry_price=entry,
            stop_loss=stop,
            max_leverage=max_leverage,
        )

        if position is None or position["quantity"] <= 0:
            i += 1
            continue

        quantity = float(position["quantity"])
        entry_costs = calculate_trade_costs(
            position_value=float(position["position_value"]),
            commission_percent=commission_percent,
            slippage_percent=slippage_percent,
        )

        current_stop = float(stop)
        extreme = float(entry)
        exit_price = None
        exit_index = None
        exit_reason = None

        last_bar = min(entry_index + max_hold_bars - 1, data_end - 1)

        for j in range(entry_index, last_bar + 1):
            # First check the stop that was already known before this bar.
            if side == "LONG":
                if opens[j] <= current_stop:
                    exit_price = opens[j]
                    exit_index = j
                    exit_reason = "GAP_STOP"
                    break

                if lows[j] <= current_stop:
                    exit_price = current_stop
                    exit_index = j
                    exit_reason = "TRAILING_STOP"
                    break

                # Update only after this bar survives the old stop.
                extreme = max(extreme, highs[j])
                candidate_stop = extreme - (atrs[j] * trail_atr_mult)
                current_stop = max(current_stop, candidate_stop)

            else:
                if opens[j] >= current_stop:
                    exit_price = opens[j]
                    exit_index = j
                    exit_reason = "GAP_STOP"
                    break

                if highs[j] >= current_stop:
                    exit_price = current_stop
                    exit_index = j
                    exit_reason = "TRAILING_STOP"
                    break

                extreme = min(extreme, lows[j])
                candidate_stop = extreme + (atrs[j] * trail_atr_mult)
                current_stop = min(current_stop, candidate_stop)

        if exit_price is None:
            exit_index = last_bar
            exit_price = closes[exit_index]
            exit_reason = "TIME_EXIT"

        if side == "LONG":
            gross_pnl = (exit_price - entry) * quantity
        else:
            gross_pnl = (entry - exit_price) * quantity

        exit_costs = calculate_trade_costs(
            position_value=abs(quantity * exit_price),
            commission_percent=commission_percent,
            slippage_percent=slippage_percent,
        )

        total_cost = entry_costs["total_cost"] + exit_costs["total_cost"]
        net_pnl = gross_pnl - total_cost
        balance += net_pnl

        if net_pnl > 0:
            wins += 1
            gross_profit += net_pnl
        else:
            losses += 1
            gross_loss += abs(net_pnl)

        if side == "LONG":
            long_trades += 1
            long_net += net_pnl
        else:
            short_trades += 1
            short_net += net_pnl

        peak_balance = max(peak_balance, balance)
        if peak_balance > 0:
            drawdown = ((peak_balance - balance) / peak_balance) * 100
            max_drawdown = max(max_drawdown, drawdown)

        trades.append(
            {
                "signal_index": i,
                "entry_index": entry_index,
                "exit_index": exit_index,
                "side": side,
                "entry": entry,
                "exit": exit_price,
                "initial_stop": stop,
                "final_stop": current_stop,
                "exit_reason": exit_reason,
                "quantity": quantity,
                "gross_pnl": gross_pnl,
                "cost": total_cost,
                "net_pnl": net_pnl,
                "balance": balance,
            }
        )

        # Only one position can be open at a time.
        i = exit_index + 1

    total_trades = len(trades)
    win_rate = (wins / total_trades) * 100 if total_trades else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = inf
    else:
        profit_factor = 0.0

    return {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "net_profit": balance - initial_balance,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "long_trades": long_trades,
        "long_net": long_net,
        "short_trades": short_trades,
        "short_net": short_net,
        "trades": trades,
    }
