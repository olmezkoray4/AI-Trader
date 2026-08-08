from app.data.market_data import get_klines
from app.indicators.ema import calculate_ema
from app.indicators.trend import detect_trend
from app.indicators.rsi import calculate_rsi
from app.indicators.macd import calculate_macd
from app.strategies.signal_engine import generate_signal
from app.indicators.volume import analyze_volume
from app.indicators.atr import calculate_atr
from app.risk.risk_manager import calculate_trade_levels
from app.risk.position_sizing import calculate_position_size
from app.risk.costs import calculate_trade_costs


# =====================================================
# PİYASA VERİSİ
# =====================================================

df = get_klines()


# =====================================================
# EMA
# =====================================================

df["EMA20"] = calculate_ema(df, 20)
df["EMA50"] = calculate_ema(df, 50)
df["EMA200"] = calculate_ema(df, 200)


# =====================================================
# RSI
# =====================================================

df["RSI"] = calculate_rsi(df, 14)


# =====================================================
# MACD
# =====================================================

df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)


# =====================================================
# ATR
# =====================================================

df["ATR"] = calculate_atr(df, 14)


# =====================================================
# SON 15 MUM
# =====================================================

print(
    df[
        [
            "Close",
            "EMA20",
            "EMA50",
            "EMA200",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
            "MACD_HIST",
            "ATR",
        ]
    ].tail(15)
)


# =====================================================
# TREND VE HACİM
# =====================================================

trend = detect_trend(df)
volume_result = analyze_volume(df)


# =====================================================
# SON KAPANMIŞ MUM DEĞERLERİ
# =====================================================

last_rsi = df["RSI"].iloc[-2]
last_macd = df["MACD"].iloc[-2]
last_macd_signal = df["MACD_SIGNAL"].iloc[-2]
last_hist = df["MACD_HIST"].iloc[-2]
last_atr = df["ATR"].iloc[-2]
last_close = df["Close"].iloc[-2]


# =====================================================
# MACD DURUMU
# =====================================================

if last_macd > last_macd_signal:
    macd_status = "POZİTİF"

elif last_macd < last_macd_signal:
    macd_status = "NEGATİF"

else:
    macd_status = "NÖTR"


# =====================================================
# RSI DURUMU
# =====================================================

if last_rsi >= 70:
    rsi_status = "AŞIRI ALIM"

elif last_rsi <= 30:
    rsi_status = "AŞIRI SATIM"

else:
    rsi_status = "NÖTR"


# =====================================================
# TEKNİK ANALİZ SONUCU
# =====================================================

print()
print("=" * 55)
print("PİYASA TRENDİ :", trend)
print("RSI            :", round(last_rsi, 2))
print("RSI DURUMU     :", rsi_status)
print("MACD           :", round(last_macd, 2))
print("MACD SIGNAL    :", round(last_macd_signal, 2))
print("MACD HISTOGRAM :", round(last_hist, 2))
print("MACD DURUMU    :", macd_status)
print("=" * 55)


# =====================================================
# HACİM
# =====================================================

print()
print("HACİM          :", round(volume_result["volume"], 2))
print("ORT. HACİM     :", round(volume_result["average_volume"], 2))
print("HACİM ORANI    :", round(volume_result["ratio"], 2))
print("HACİM DURUMU   :", volume_result["status"])


# =====================================================
# SİNYAL MOTORU
# =====================================================

result = generate_signal(
    df,
    trend,
    volume_result
)

print()
print("=" * 55)
print("SİNYAL         :", result["decision"])
print("PUAN           :", result["score"])
print("NEDENLER:")

for reason in result["reasons"]:
    print("-", reason)

print("=" * 55)


# =====================================================
# RİSK YÖNETİMİ
# =====================================================

trade = calculate_trade_levels(
    result["decision"],
    last_close,
    last_atr
)

print()
print("=" * 55)
print("RİSK YÖNETİMİ")

if trade is None:
    print("İŞLEM          : YOK")
    print("NEDEN          : Sinyal BEKLE")

else:
    position = calculate_position_size(
        account_balance=10000,
        risk_percent=1,
        entry_price=trade["entry"],
        stop_loss=trade["stop_loss"],
        max_leverage=1,
    )

    print("YÖN            :", trade["side"])
    print("GİRİŞ          :", round(trade["entry"], 2))
    print("STOP LOSS      :", round(trade["stop_loss"], 2))
    print("TAKE PROFIT    :", round(trade["take_profit"], 2))
    print("RİSK / ÖDÜL    : 1 :", trade["risk_reward"])

    if position is not None:
        costs = calculate_trade_costs(
            position_value=position["position_value"],
            commission_percent=0.1,
            slippage_percent=0.05,
        )

        print("HEDEF RİSK     :", round(position["requested_risk"], 2))
        print("GERÇEK RİSK    :", round(position["actual_risk"], 2))
        print("POZİSYON ADEDİ :", round(position["quantity"], 6))
        print("POZİSYON DEĞERİ:", round(position["position_value"], 2))
        print("MAKS. POZİSYON :", round(position["max_position_value"], 2))

        print()
        print("İŞLEM MALİYETLERİ")
        print("KOMİSYON       :", round(costs["commission"], 2))
        print("SLIPPAGE       :", round(costs["slippage"], 2))
        print("TOPLAM MALİYET :", round(costs["total_cost"], 2))

    else:
        print("POZİSYON       : HESAPLANAMADI")

print("=" * 55)