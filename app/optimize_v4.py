from itertools import product
from math import isfinite

from app.backtest.trailing_breakout_engine import run_trailing_breakout_backtest
from app.data.historical_data import get_historical_klines
from app.indicators.adx import calculate_adx
from app.indicators.atr import calculate_atr
from app.indicators.ema import calculate_ema


INITIAL_BALANCE = 10000
TOTAL_LIMIT = 20000
INTERVAL = "1h"
FIXED_END_TIME = "2026-08-09 13:59:59.999+00:00"

TRAIN_RATIO = 0.60
VALIDATION_RATIO = 0.20


print()
print("=" * 104)
print("AI-TRADER V4 - 1H BREAKOUT + ATR TRAILING STOP")
print("=" * 104)
print("Amaç: 5m gürültüsünden uzaklaşıp daha uzun geçmişte trendleri trailing stop ile test etmek.")
print()


# =====================================================
# FIXED 1H DATASET
# =====================================================

df = get_historical_klines(
    symbol="BTCUSDT",
    interval=INTERVAL,
    total_limit=TOTAL_LIMIT,
    end_time=FIXED_END_TIME,
    only_closed=True,
)

if len(df) < 10000:
    raise RuntimeError("Yeterli 1h veri indirilemedi.")


# =====================================================
# INDICATORS - CALCULATED ONCE
# =====================================================

df["EMA50"] = calculate_ema(df, 50)
df["EMA200"] = calculate_ema(df, 200)
df["ATR"] = calculate_atr(df, 14)
df["ADX"], df["PLUS_DI"], df["MINUS_DI"] = calculate_adx(df, 14)

LOOKBACKS = [20, 40, 80]

for lookback in LOOKBACKS:
    # Shift(1) is critical: bar i can only compare against bars that closed
    # before bar i. The current bar is never part of its own breakout level.
    df[f"DONCHIAN_UPPER_{lookback}"] = (
        df["High"].rolling(window=lookback).max().shift(1)
    )
    df[f"DONCHIAN_LOWER_{lookback}"] = (
        df["Low"].rolling(window=lookback).min().shift(1)
    )

n = len(df)
train_end = int(n * TRAIN_RATIO)
validation_end = int(n * (TRAIN_RATIO + VALIDATION_RATIO))

print("Toplam mum            :", n)
print("Ilk tarih             :", df["OpenTime"].iloc[0])
print("Son tarih             :", df["OpenTime"].iloc[-1])
print("Train                 :", df["OpenTime"].iloc[0], "->", df["OpenTime"].iloc[train_end - 1])
print("Validation            :", df["OpenTime"].iloc[train_end], "->", df["OpenTime"].iloc[validation_end - 1])
print("Final Test            :", df["OpenTime"].iloc[validation_end], "->", df["OpenTime"].iloc[-1])
print()


# =====================================================
# CONFIGURATIONS
# =====================================================

SIDE_MODES = ["LONG_ONLY", "SHORT_ONLY", "BOTH"]
ADX_VALUES = [15.0, 20.0, 25.0]
INITIAL_ATR_VALUES = [2.0, 3.0]
TRAIL_ATR_VALUES = [2.0, 3.0, 4.0]

configs = []

for side_mode, lookback, adx_min, initial_atr, trail_atr in product(
    SIDE_MODES,
    LOOKBACKS,
    ADX_VALUES,
    INITIAL_ATR_VALUES,
    TRAIL_ATR_VALUES,
):
    configs.append(
        {
            "side_mode": side_mode,
            "lookback": lookback,
            "adx_min": adx_min,
            "initial_atr_mult": initial_atr,
            "trail_atr_mult": trail_atr,
        }
    )

print("Toplam V4 kombinasyon :", len(configs))
print()


def run_segment(params, start_index, end_index):
    return run_trailing_breakout_backtest(
        df=df,
        lookback=params["lookback"],
        adx_min=params["adx_min"],
        initial_atr_mult=params["initial_atr_mult"],
        trail_atr_mult=params["trail_atr_mult"],
        side_mode=params["side_mode"],
        initial_balance=INITIAL_BALANCE,
        risk_percent=1.0,
        max_leverage=1.0,
        max_hold_bars=24 * 30,
        commission_percent=0.04,
        slippage_percent=0.02,
        start_index=start_index,
        end_index=end_index,
    )


def stats(result):
    pf = result["profit_factor"]
    return {
        "trades": result["total_trades"],
        "pf": pf,
        "net": result["net_profit"],
        "dd": result["max_drawdown"],
        "wr": result["win_rate"],
        "long_trades": result["long_trades"],
        "long_net": result["long_net"],
        "short_trades": result["short_trades"],
        "short_net": result["short_net"],
    }


def pf_for_sort(value):
    if not isfinite(value):
        return 99.0
    return value


def robust_pf(train_pf, validation_pf):
    train_value = 3.0 if not isfinite(train_pf) else min(train_pf, 3.0)
    val_value = 3.0 if not isfinite(validation_pf) else min(validation_pf, 3.0)
    return min(train_value, val_value)


# =====================================================
# TRAIN - ALL CONFIGS
# =====================================================

train_results = []

for number, params in enumerate(configs, start=1):
    result = run_segment(params, start_index=200, end_index=train_end)
    train = stats(result)

    train_results.append({"params": params, "train": train})

    print(
        f"[{number:03d}/{len(configs)}] "
        f"{params['side_mode']:<10} LB={params['lookback']:<3} "
        f"ADX={params['adx_min']:<4.0f} IS={params['initial_atr_mult']:.1f} "
        f"TR={params['trail_atr_mult']:.1f} | "
        f"PF={train['pf']:.2f} Net={train['net']:.2f} "
        f"DD={train['dd']:.2f}% Islem={train['trades']}"
    )


# =====================================================
# SELECT TRAIN CANDIDATES
# =====================================================

eligible = [item for item in train_results if item["train"]["trades"] >= 25]

if not eligible:
    eligible = train_results

eligible.sort(
    key=lambda item: (
        pf_for_sort(item["train"]["pf"]),
        item["train"]["net"],
        -item["train"]["dd"],
        item["train"]["trades"],
    ),
    reverse=True,
)

top_train = eligible[:18]

print()
print("=" * 104)
print("EN IYI 18 TRAIN ADAYI -> VALIDATION")
print("=" * 104)

validated = []

for number, item in enumerate(top_train, start=1):
    params = item["params"]
    validation_result = run_segment(
        params,
        start_index=train_end,
        end_index=validation_end,
    )
    validation = stats(validation_result)

    score = robust_pf(item["train"]["pf"], validation["pf"])

    if validation["trades"] < 10:
        score -= 0.25

    validation_pass = (
        item["train"]["pf"] > 1.0
        and validation["pf"] > 1.0
        and item["train"]["trades"] >= 25
        and validation["trades"] >= 10
    )

    validated.append(
        {
            "params": params,
            "train": item["train"],
            "validation": validation,
            "robust_score": score,
            "validation_pass": validation_pass,
        }
    )

    print(
        f"[{number:02d}/{len(top_train)}] "
        f"{params['side_mode']:<10} LB={params['lookback']:<3} "
        f"ADX={params['adx_min']:<4.0f} IS={params['initial_atr_mult']:.1f} "
        f"TR={params['trail_atr_mult']:.1f} | "
        f"TRAIN PF={item['train']['pf']:.2f} Net={item['train']['net']:.2f} | "
        f"VAL PF={validation['pf']:.2f} Net={validation['net']:.2f} "
        f"Islem={validation['trades']} | "
        f"{'PASS' if validation_pass else 'FAIL'}"
    )

validated.sort(
    key=lambda item: (
        item["validation_pass"],
        item["robust_score"],
        pf_for_sort(item["validation"]["pf"]),
        item["validation"]["net"],
        -item["validation"]["dd"],
    ),
    reverse=True,
)


# =====================================================
# FINAL UNSEEN TEST - TOP 6 BY TRAIN+VALIDATION ONLY
# =====================================================

finalists = validated[:6]

print()
print("=" * 104)
print("FINAL GORULMEMIS TEST - ILK 6 ADAY")
print("=" * 104)

final_results = []

for rank, item in enumerate(finalists, start=1):
    params = item["params"]
    test_result = run_segment(
        params,
        start_index=validation_end,
        end_index=n,
    )
    test = stats(test_result)

    final_pass = (
        item["validation_pass"]
        and test["pf"] > 1.0
        and test["trades"] >= 10
    )

    final_results.append(
        {
            **item,
            "test": test,
            "final_pass": final_pass,
        }
    )

    print()
    print("SIRA           :", rank)
    print("Durum          :", "PASS" if final_pass else "FAIL")
    print("Taraf          :", params["side_mode"])
    print("Lookback       :", params["lookback"])
    print("ADX Min        :", params["adx_min"])
    print("Initial ATR    :", params["initial_atr_mult"])
    print("Trailing ATR   :", params["trail_atr_mult"])
    print("Robust Skor    :", round(item["robust_score"], 3))
    print(
        "TRAIN          :",
        f"PF {item['train']['pf']:.2f} | Net {item['train']['net']:.2f} | "
        f"DD {item['train']['dd']:.2f}% | Islem {item['train']['trades']}",
    )
    print(
        "VALIDATION     :",
        f"PF {item['validation']['pf']:.2f} | Net {item['validation']['net']:.2f} | "
        f"DD {item['validation']['dd']:.2f}% | Islem {item['validation']['trades']}",
    )
    print(
        "FINAL TEST     :",
        f"PF {test['pf']:.2f} | Net {test['net']:.2f} | "
        f"DD {test['dd']:.2f}% | Islem {test['trades']}",
    )
    print(
        "TEST LONG/SHORT:",
        f"LONG {test['long_trades']} islem / Net {test['long_net']:.2f} | "
        f"SHORT {test['short_trades']} islem / Net {test['short_net']:.2f}",
    )


print()
print("=" * 104)
print("V4 OZET")
print("=" * 104)
passed = [item for item in final_results if item["final_pass"]]
print("Final PASS aday sayisi:", len(passed))
print("Kural: Train + Validation + tamamen gorulmemis Final Test birlikte PF > 1 olmadan aday kabul edilmiyor.")
print("Bu backtest kar garantisi degildir. Maliyetler varsayimdir ve paper trading sonraki zorunlu asamadir.")
print("=" * 104)
