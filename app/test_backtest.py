from app.data.historical_data import get_historical_klines
from app.indicators.ema import calculate_ema
from app.indicators.rsi import calculate_rsi
from app.indicators.macd import calculate_macd
from app.indicators.atr import calculate_atr
from app.indicators.trend import detect_trend
from app.indicators.volume import analyze_volume
from app.strategies.signal_engine import generate_signal
from app.backtest.backtest_engine import run_backtest


# =====================================================
# GEÇMİŞ VERİ
# =====================================================

df = get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=10000,
)


# =====================================================
# İNDİKATÖRLER
# =====================================================

df["EMA20"] = calculate_ema(df, 20)
df["EMA50"] = calculate_ema(df, 50)
df["EMA200"] = calculate_ema(df, 200)
df["RSI"] = calculate_rsi(df, 14)
df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)
df["ATR"] = calculate_atr(df, 14)


# =====================================================
# STRATEJİ
# =====================================================

def strategy(current_df):
    # Backtest verisindeki son mum kapanmış kabul edilir.
    trend = detect_trend(current_df, candle_index=-1)
    volume_result = analyze_volume(current_df, candle_index=-1)

    return generate_signal(
        current_df,
        trend,
        volume_result,
        candle_index=-1,
    )


# =====================================================
# BACKTEST
# =====================================================

result = run_backtest(
    df=df,
    signal_function=strategy,
    initial_balance=10000,
    risk_percent=1,
    max_leverage=1,
    max_hold_bars=48,
)


# =====================================================
# GENEL SONUÇLAR
# =====================================================

print()
print("=" * 70)
print("BACKTEST SONUCU")
print("=" * 70)
print("Başlangıç      :", round(result["initial_balance"], 2))
print("Final Bakiye   :", round(result["final_balance"], 2))
print("Net Sonuç      :", round(result["net_profit"], 2))
print("Toplam İşlem   :", result["total_trades"])
print("Kazanan        :", result["wins"])
print("Kaybeden       :", result["losses"])
print("Win Rate       :", round(result["win_rate"], 2), "%")
print("Profit Factor  :", round(result["profit_factor"], 2))
print("Max Drawdown   :", round(result["max_drawdown"], 2), "%")
print("Take Profit    :", result["take_profit_count"])
print("Stop Loss      :", result["stop_loss_count"])
print("Time Exit      :", result["time_exit_count"])


# =====================================================
# LONG / SHORT ANALİZİ
# =====================================================

print()
print("=" * 70)
print("LONG / SHORT ANALİZİ")
print("=" * 70)

print("LONG")
print("İşlem          :", result["long_trades"])
print("Kazanan        :", result["long_wins"])
print("Kaybeden       :", result["long_losses"])
print("Win Rate       :", round(result["long_win_rate"], 2), "%")
print("Profit Factor  :", round(result["long_profit_factor"], 2))
print("Net Sonuç      :", round(result["long_net"], 2))

print()
print("SHORT")
print("İşlem          :", result["short_trades"])
print("Kazanan        :", result["short_wins"])
print("Kaybeden       :", result["short_losses"])
print("Win Rate       :", round(result["short_win_rate"], 2), "%")
print("Profit Factor  :", round(result["short_profit_factor"], 2))
print("Net Sonuç      :", round(result["short_net"], 2))


# =====================================================
# SHORT TAM PUAN ANALİZİ
# =====================================================

print()
print("=" * 70)
print("SHORT TAM PUAN ANALİZİ")
print("=" * 70)

exact_scores = {}

for trade in result["trades"]:
    if trade["side"] != "SHORT":
        continue

    score = trade["score"]
    exact_scores.setdefault(score, []).append(trade["net_pnl"])

for score in sorted(exact_scores.keys(), reverse=True):
    pnls = exact_scores[score]
    total = len(pnls)
    wins = sum(1 for pnl in pnls if pnl > 0)
    losses = sum(1 for pnl in pnls if pnl <= 0)
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = sum(abs(pnl) for pnl in pnls if pnl < 0)
    win_rate = wins / total * 100 if total else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    net_result = sum(pnls)

    print()
    print("PUAN          :", score)
    print("İşlem         :", total)
    print("Kazanan       :", wins)
    print("Kaybeden      :", losses)
    print("Win Rate      :", round(win_rate, 2), "%")
    print("Profit Factor :", round(profit_factor, 2))
    print("Net Sonuç     :", round(net_result, 2))


# =====================================================
# FİLTRELENEN / TERCİH EDİLEN SHORT KOMBİNASYONLARI
# =====================================================

print()
print("=" * 80)
print("SHORT KALİTE FİLTRESİ ANALİZİ")
print("=" * 80)

for trade in result["trades"]:
    reasons = trade.get("reasons", [])

    if any("SHORT kalite filtresi" in reason for reason in reasons):
        print()
        print("PUAN   :", trade["score"])
        print("SONUÇ  :", trade["exit_reason"])
        print("NET PNL:", round(trade["net_pnl"], 2))
        print("NEDENLER:")
        for reason in reasons:
            print(" -", reason)
        print("-" * 50)
