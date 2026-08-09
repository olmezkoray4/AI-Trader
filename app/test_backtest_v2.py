from app.data.historical_data import get_historical_klines
from app.indicators.ema import calculate_ema
from app.indicators.rsi import calculate_rsi
from app.indicators.macd import calculate_macd
from app.indicators.atr import calculate_atr
from app.indicators.adx import calculate_adx
from app.indicators.volume import analyze_volume
from app.strategies.regime_detector import detect_market_regime
from app.strategies.signal_engine_v2 import generate_signal_v2
from app.backtest.backtest_engine import run_backtest


# =====================================================
# DATA
# =====================================================

df = get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=10000,
)


# =====================================================
# INDICATORS - CALCULATED ONCE
# =====================================================

df["EMA20"] = calculate_ema(df, 20)
df["EMA50"] = calculate_ema(df, 50)
df["EMA200"] = calculate_ema(df, 200)
df["RSI"] = calculate_rsi(df, 14)
df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)
df["ATR"] = calculate_atr(df, 14)
df["ADX"], df["PLUS_DI"], df["MINUS_DI"] = calculate_adx(df, 14)
df["VOLUME_MA"] = df["Volume"].rolling(window=20).mean()


# =====================================================
# V2 STRATEGY
# =====================================================

def strategy_v2(current_df):
    regime_result = detect_market_regime(
        current_df,
        candle_index=-1,
        adx_trend_threshold=25.0,
        adx_range_threshold=18.0,
    )

    volume_result = analyze_volume(
        current_df,
        period=20,
        candle_index=-1,
    )

    return generate_signal_v2(
        current_df,
        regime_result,
        volume_result,
        candle_index=-1,
        min_score=70,
    )


# =====================================================
# BACKTEST
# =====================================================

result = run_backtest(
    df=df,
    signal_function=strategy_v2,
    initial_balance=10000,
    risk_percent=1.0,
    max_leverage=1,
    max_hold_bars=72,
    min_stop_percent=0.25,
    atr_multiplier=2.0,
    reward_multiplier=2.0,
    commission_percent=0.04,
    slippage_percent=0.02,
    charge_exit_costs=True,
)


# =====================================================
# RESULTS
# =====================================================

print()
print("=" * 72)
print("AI-TRADER V2 - REGIME BACKTEST")
print("=" * 72)
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

print()
print("LONG")
print("İşlem          :", result["long_trades"])
print("Win Rate       :", round(result["long_win_rate"], 2), "%")
print("Profit Factor  :", round(result["long_profit_factor"], 2))
print("Net Sonuç      :", round(result["long_net"], 2))

print()
print("SHORT")
print("İşlem          :", result["short_trades"])
print("Win Rate       :", round(result["short_win_rate"], 2), "%")
print("Profit Factor  :", round(result["short_profit_factor"], 2))
print("Net Sonuç      :", round(result["short_net"], 2))
print("=" * 72)
