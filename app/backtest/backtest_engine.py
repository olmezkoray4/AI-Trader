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
):
    balance = initial_balance
    peak_balance = initial_balance

    trades = []

    # =====================================================
    # GENEL İSTATİSTİKLER
    # =====================================================

    wins = 0
    losses = 0

    gross_profit = 0
    gross_loss = 0

    take_profit_count = 0
    stop_loss_count = 0
    time_exit_count = 0

    max_drawdown = 0

    # =====================================================
    # LONG İSTATİSTİKLERİ
    # =====================================================

    long_trades = 0
    long_wins = 0
    long_losses = 0

    long_profit = 0
    long_loss = 0

    # =====================================================
    # SHORT İSTATİSTİKLERİ
    # =====================================================

    short_trades = 0
    short_wins = 0
    short_losses = 0

    short_profit = 0
    short_loss = 0

    # EMA200 için yeterli geçmiş veri
    i = 200

    while i < len(df) - 2:

        # =====================================================
        # SİNYAL OLUŞTUR
        # =====================================================

        current_df = df.iloc[: i + 1].copy()

        signal_result = signal_function(current_df)

        decision = signal_result["decision"]
        signal_score = signal_result["score"]
        signal_reasons = signal_result.get("reasons", [])

        if decision == "BEKLE":
            i += 1
            continue

        # =====================================================
        # GİRİŞ
        # =====================================================
        # Sinyal i mumunun kapanışında oluşur.
        # İşleme sonraki mumun OPEN fiyatından girilir.
        # =====================================================

        entry_index = i + 1

        if entry_index >= len(df):
            break

        entry = df["Open"].iloc[entry_index]

        # Sinyal anında bilinen ATR
        atr = df["ATR"].iloc[i]

        trade_levels = calculate_trade_levels(
            decision,
            entry,
            atr,
        )

        if trade_levels is None:
            i += 1
            continue

        # =====================================================
        # POZİSYON BÜYÜKLÜĞÜ
        # =====================================================

        position = calculate_position_size(
            account_balance=balance,
            risk_percent=risk_percent,
            entry_price=trade_levels["entry"],
            stop_loss=trade_levels["stop_loss"],
            max_leverage=max_leverage,
        )

        if position is None:
            i += 1
            continue

        # =====================================================
        # İŞLEM MALİYETLERİ
        # =====================================================

        costs = calculate_trade_costs(
            position_value=position["position_value"],
            commission_percent=0.04,
            slippage_percent=0.02,
        )

        side = trade_levels["side"]
        stop_loss = trade_levels["stop_loss"]
        take_profit = trade_levels["take_profit"]
        quantity = position["quantity"]

        exit_price = None
        exit_reason = None
        exit_index = None

        # =====================================================
        # MAKSİMUM İŞLEM SÜRESİ
        # =====================================================

        last_bar = min(
            entry_index + max_hold_bars - 1,
            len(df) - 1,
        )

        # =====================================================
        # SONRAKİ MUMLARI KONTROL ET
        # =====================================================

        for j in range(entry_index, last_bar + 1):

            high = df["High"].iloc[j]
            low = df["Low"].iloc[j]

            # =================================================
            # LONG
            # =================================================

            if side == "LONG":

                stop_hit = low <= stop_loss
                target_hit = high >= take_profit

                # Aynı mumda hem SL hem TP varsa,
                # güvenli tarafta kalıp STOP kabul ediyoruz.
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

            # =================================================
            # SHORT
            # =================================================

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

        # =====================================================
        # SL / TP GELMEDİYSE TIME EXIT
        # =====================================================

        if exit_price is None:
            exit_index = last_bar
            exit_price = df["Close"].iloc[exit_index]
            exit_reason = "TIME EXIT"

        # =====================================================
        # BRÜT KÂR / ZARAR
        # =====================================================

        if side == "LONG":
            gross_pnl = (
                exit_price - entry
            ) * quantity

        else:
            gross_pnl = (
                entry - exit_price
            ) * quantity

        # =====================================================
        # NET KÂR / ZARAR
        # =====================================================

        net_pnl = (
            gross_pnl
            - costs["total_cost"]
        )

        # =====================================================
        # ÇIKIŞ NEDENLERİ
        # =====================================================

        if exit_reason == "TAKE PROFIT":
            take_profit_count += 1

        elif exit_reason == "STOP LOSS":
            stop_loss_count += 1

        elif exit_reason == "TIME EXIT":
            time_exit_count += 1

        # =====================================================
        # LONG / SHORT İSTATİSTİKLERİ
        # =====================================================

        if side == "LONG":

            long_trades += 1

            if net_pnl > 0:
                long_wins += 1
                long_profit += net_pnl

            else:
                long_losses += 1
                long_loss += abs(net_pnl)

        elif side == "SHORT":

            short_trades += 1

            if net_pnl > 0:
                short_wins += 1
                short_profit += net_pnl

            else:
                short_losses += 1
                short_loss += abs(net_pnl)

        # =====================================================
        # BAKİYE
        # =====================================================

        balance += net_pnl

        # =====================================================
        # GENEL KAZANAN / KAYBEDEN
        # =====================================================

        if net_pnl > 0:
            wins += 1
            gross_profit += net_pnl

        else:
            losses += 1
            gross_loss += abs(net_pnl)

        # =====================================================
        # DRAWDOWN
        # =====================================================

        if balance > peak_balance:
            peak_balance = balance

        if peak_balance > 0:
            drawdown = (
                (peak_balance - balance)
                / peak_balance
            ) * 100
        else:
            drawdown = 0

        if drawdown > max_drawdown:
            max_drawdown = drawdown

        # =====================================================
        # İŞLEMİ KAYDET
        # =====================================================

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

                "gross_pnl": gross_pnl,
                "cost": costs["total_cost"],
                "net_pnl": net_pnl,

                "balance": balance,
            }
        )

        # =====================================================
        # AYNI ANDA TEK İŞLEM
        # =====================================================

        i = exit_index + 1

    # =========================================================
    # GENEL BACKTEST SONUÇLARI
    # =========================================================

    total_trades = len(trades)

    if total_trades > 0:
        win_rate = (
            wins / total_trades
        ) * 100
    else:
        win_rate = 0

    if gross_loss > 0:
        profit_factor = (
            gross_profit / gross_loss
        )
    else:
        profit_factor = 0

    net_profit = (
        balance - initial_balance
    )

    # =========================================================
    # LONG SONUÇLARI
    # =========================================================

    if long_trades > 0:
        long_win_rate = (
            long_wins / long_trades
        ) * 100
    else:
        long_win_rate = 0

    if long_loss > 0:
        long_profit_factor = (
            long_profit / long_loss
        )
    else:
        long_profit_factor = 0

    long_net = (
        long_profit - long_loss
    )

    # =========================================================
    # SHORT SONUÇLARI
    # =========================================================

    if short_trades > 0:
        short_win_rate = (
            short_wins / short_trades
        ) * 100
    else:
        short_win_rate = 0

    if short_loss > 0:
        short_profit_factor = (
            short_profit / short_loss
        )
    else:
        short_profit_factor = 0

    short_net = (
        short_profit - short_loss
    )

    # =========================================================
    # RETURN
    # =========================================================

    return {
        # Genel
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

        # LONG
        "long_trades": long_trades,
        "long_wins": long_wins,
        "long_losses": long_losses,
        "long_win_rate": long_win_rate,
        "long_profit_factor": long_profit_factor,
        "long_net": long_net,

        # SHORT
        "short_trades": short_trades,
        "short_wins": short_wins,
        "short_losses": short_losses,
        "short_win_rate": short_win_rate,
        "short_profit_factor": short_profit_factor,
        "short_net": short_net,

        # İşlem listesi
        "trades": trades,
    }