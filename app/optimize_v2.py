from itertools import product

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


INITIAL_BALANCE = 10000
TOTAL_LIMIT = 30000
TRAIN_RATIO = 0.70


print()
print("=" * 88)
print("AI-TRADER V2 OTOMATIK OPTIMIZER")
print("=" * 88)
print("Tek veri seti indirilecek, sonra tum kombinasyonlar ayni veri uzerinde test edilecek.")
print()


# =====================================================
# DATA - ONCE
# =====================================================

df = get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=TOTAL_LIMIT,
)


# =====================================================
# INDICATORS - ONCE
# =====================================================

df["EMA20"] = calculate_ema(df, 20)
df["EMA50"] = calculate_ema(df, 50)
df["EMA200"] = calculate_ema(df, 200)
df["RSI"] = calculate_rsi(df, 14)
df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = calculate_macd(df)
df["ATR"] = calculate_atr(df, 14)
df["ADX"], df["PLUS_DI"], df["MINUS_DI"] = calculate_adx(df, 14)
df["VOLUME_MA"] = df["Volume"].rolling(window=20).mean()

train_end = int(len(df) * TRAIN_RATIO)

print("Train mum sayisi     :", train_end)
print("Validation mum sayisi:", len(df) - train_end)
print("Train bitis tarihi   :", df["OpenTime"].iloc[train_end - 1])
print("Validation baslangic :", df["OpenTime"].iloc[train_end])
print()


# =====================================================
# HELPERS
# =====================================================

def make_strategy(params):
    def strategy(current_df):
        regime_result = detect_market_regime(
            current_df,
            candle_index=-1,
            adx_trend_threshold=params["adx_threshold"],
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
            min_score=params["min_score"],
            allow_long=params["allow_long"],
            allow_short=True,
        )

    return strategy


def run_segment(params, start_index, end_index):
    return run_backtest(
        df=df,
        signal_function=make_strategy(params),
        initial_balance=INITIAL_BALANCE,
        risk_percent=1.0,
        max_leverage=1,
        max_hold_bars=72,
        min_stop_percent=0.25,
        atr_multiplier=2.0,
        reward_multiplier=params["reward_multiplier"],
        commission_percent=0.04,
        slippage_percent=0.02,
        charge_exit_costs=True,
        start_index=start_index,
        end_index=end_index,
    )


def summarize_result(result):
    return {
        "trades": result["total_trades"],
        "pf": result["profit_factor"],
        "net": result["net_profit"],
        "dd": result["max_drawdown"],
        "wr": result["win_rate"],
    }


# =====================================================
# GRID - 54 CONFIGURATIONS
# =====================================================

side_modes = [
    ("SHORT_ONLY", False),
    ("BOTH", True),
]
min_scores = [70, 80, 90]
adx_thresholds = [20.0, 25.0, 30.0]
reward_multipliers = [1.5, 2.0, 2.5]

combinations = list(
    product(
        side_modes,
        min_scores,
        adx_thresholds,
        reward_multipliers,
    )
)

print("Toplam kombinasyon:", len(combinations))
print()

train_candidates = []

for number, combination in enumerate(combinations, start=1):
    (side_name, allow_long), min_score, adx_threshold, reward_multiplier = combination

    params = {
        "side": side_name,
        "allow_long": allow_long,
        "min_score": min_score,
        "adx_threshold": adx_threshold,
        "reward_multiplier": reward_multiplier,
    }

    result = run_segment(
        params=params,
        start_index=200,
        end_index=train_end,
    )

    stats = summarize_result(result)

    train_candidates.append(
        {
            "params": params,
            "train": stats,
        }
    )

    print(
        f"[{number:02d}/{len(combinations)}] "
        f"{side_name:<10} "
        f"score={min_score:<3} "
        f"ADX={adx_threshold:<4.0f} "
        f"RR={reward_multiplier:<3.1f} | "
        f"islem={stats['trades']:<4} "
        f"PF={stats['pf']:.2f} "
        f"Net={stats['net']:.2f} "
        f"DD={stats['dd']:.2f}%"
    )


# Avoid ranking tiny samples above meaningful samples.
eligible = [
    item for item in train_candidates
    if item["train"]["trades"] >= 15
]

if not eligible:
    eligible = train_candidates

eligible.sort(
    key=lambda item: (
        item["train"]["pf"],
        item["train"]["net"],
        -item["train"]["dd"],
        item["train"]["trades"],
    ),
    reverse=True,
)

# Only the strongest train candidates get validation testing.
top_train = eligible[:12]

print()
print("=" * 88)
print("EN IYI 12 TRAIN ADAYI -> VALIDATION TESTI")
print("=" * 88)

validated = []

for number, item in enumerate(top_train, start=1):
    params = item["params"]

    validation_result = run_segment(
        params=params,
        start_index=train_end,
        end_index=len(df),
    )

    validation = summarize_result(validation_result)

    # Robustness is deliberately conservative: the weaker PF wins.
    # Very small validation samples are penalized.
    minimum_pf = min(item["train"]["pf"], validation["pf"])
    sample_penalty = 0.35 if validation["trades"] < 8 else 0.0
    robust_score = minimum_pf - sample_penalty

    validated.append(
        {
            "params": params,
            "train": item["train"],
            "validation": validation,
            "robust_score": robust_score,
        }
    )

    print(
        f"[{number:02d}/12] "
        f"{params['side']:<10} "
        f"score={params['min_score']:<3} "
        f"ADX={params['adx_threshold']:<4.0f} "
        f"RR={params['reward_multiplier']:<3.1f} | "
        f"TRAIN PF={item['train']['pf']:.2f} Net={item['train']['net']:.2f} | "
        f"VAL PF={validation['pf']:.2f} Net={validation['net']:.2f} "
        f"Islem={validation['trades']}"
    )

validated.sort(
    key=lambda item: (
        item["robust_score"],
        item["validation"]["pf"],
        item["validation"]["net"],
        -item["validation"]["dd"],
    ),
    reverse=True,
)


print()
print("=" * 88)
print("ROBUST SIRALAMA - ILK 10")
print("=" * 88)

for rank, item in enumerate(validated[:10], start=1):
    params = item["params"]
    train = item["train"]
    val = item["validation"]

    print()
    print("SIRA           :", rank)
    print("Taraf          :", params["side"])
    print("Min Score      :", params["min_score"])
    print("ADX Esigi      :", params["adx_threshold"])
    print("Risk/Reward    :", params["reward_multiplier"])
    print("Robust Skor    :", round(item["robust_score"], 3))
    print("TRAIN          :", f"PF {train['pf']:.2f} | Net {train['net']:.2f} | DD {train['dd']:.2f}% | Islem {train['trades']}")
    print("VALIDATION     :", f"PF {val['pf']:.2f} | Net {val['net']:.2f} | DD {val['dd']:.2f}% | Islem {val['trades']}")

print()
print("=" * 88)
print("NOT: Bu optimizer karlilik garantisi vermez. Ayni veride parametre secmek overfit riski tasir.")
print("Sonraki asama, en iyi adaylari daha uzun ve gorulmemis veri uzerinde test etmektir.")
print("=" * 88)
