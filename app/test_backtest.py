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
    # Backtest verisindeki son mum zaten kapanmıştır.
    # Bu yüzden candle_index=-1 kullanıyoruz.

    trend = detect_trend(
        current_df,
        candle_index=-1
    )

    volume_result = analyze_volume(
        current_df,
        candle_index=-1
    )

    result = generate_signal(
        current_df,
        trend,
        volume_result,
        candle_index=-1,
    )

    return result

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
# BACKTEST SONUÇLARI
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

print("=" * 70)


# =====================================================
# İŞLEM DETAYLARI
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
    pnl = trade["net_pnl"]

    if score not in exact_scores:
        exact_scores[score] = []

    exact_scores[score].append(pnl)


for score in sorted(exact_scores.keys(), reverse=True):

    pnls = exact_scores[score]

    total = len(pnls)

    wins = sum(
        1 for pnl in pnls
        if pnl > 0
    )

    losses = sum(
        1 for pnl in pnls
        if pnl <= 0
    )

    gross_profit = sum(
        pnl for pnl in pnls
        if pnl > 0
    )

    gross_loss = abs(
        sum(
            pnl for pnl in pnls
            if pnl < 0
        )
    )

    win_rate = (
        wins / total * 100
        if total > 0
        else 0
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0
    )

    net = sum(pnls)

    print()
    print("PUAN          :", score)
    print("İşlem         :", total)
    print("Kazanan       :", wins)
    print("Kaybeden      :", losses)
    print("Win Rate      :", round(win_rate, 2), "%")
    print("Profit Factor :", round(profit_factor, 2))
    print("Net Sonuç     :", round(net, 2))

print("=" * 70)

print()
print("=" * 70)
print("SHORT TAM PUAN ANALİZİ")
print("=" * 70)

exact_scores = {}

for trade in result["trades"]:

    if trade["side"] != "SHORT":
        continue

    score = trade["score"]
    pnl = trade["net_pnl"]

    if score not in exact_scores:
        exact_scores[score] = []

    exact_scores[score].append(pnl)


for score in sorted(exact_scores.keys(), reverse=True):

    pnls = exact_scores[score]

    total = len(pnls)

    wins = sum(
        1 for pnl in pnls
        if pnl > 0
    )

    losses = sum(
        1 for pnl in pnls
        if pnl <= 0
    )

    gross_profit = sum(
        pnl for pnl in pnls
        if pnl > 0
    )

    gross_loss = sum(
        abs(pnl) for pnl in pnls
        if pnl < 0
    )

    win_rate = (
        wins / total * 100
        if total > 0
        else 0
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0
    )

    net_result = sum(pnls)

    print()
    print("PUAN          :", score)
    print("İşlem         :", total)
    print("Kazanan       :", wins)
    print("Kaybeden      :", losses)
    print("Win Rate      :", round(win_rate, 2), "%")
    print("Profit Factor :", round(profit_factor, 2))
    print("Net Sonuç     :", round(net_result, 2))

print("=" * 70)

print()
print("=" * 80)
print("-40 VE -45 SHORT SİNYAL ANALİZİ")
print("=" * 80)

for trade in result["trades"]:

    if trade["side"] != "SHORT":
        continue

    if trade["score"] not in [-40, -45]:
        continue

    print()
    print("PUAN   :", trade["score"])
    print("SONUÇ  :", trade["exit_reason"])
    print("NET PNL:", round(trade["net_pnl"], 2))

    print("NEDENLER:")

    for reason in trade["reasons"]:
        print(" -", reason)

    print("-" * 50)