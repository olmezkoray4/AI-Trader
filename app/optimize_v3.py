from itertools import product

from app.backtest.backtest_engine import run_backtest
from app.data.historical_data import get_historical_klines
from app.indicators.adx import calculate_adx
from app.indicators.atr import calculate_atr
from app.indicators.ema import calculate_ema
from app.indicators.macd import calculate_macd
from app.indicators.rsi import calculate_rsi
from app.strategies.strategy_lab_v3 import (
    generate_breakout_signal,
    generate_mean_reversion_signal,
    generate_pullback_signal,
)


INITIAL_BALANCE = 10000
TOTAL_LIMIT = 30000
TRAIN_RATIO = 0.70

# This endpoint freezes the same dataset you just tested:
# last 5m candle opens at 2026-08-09 12:40 UTC.
FIXED_END_TIME = "2026-08-09 12:44:59.999+00:00"


print()
print("=" * 96)
print("AI-TRADER V3 - MULTI STRATEGY LAB")
print("=" * 96)
print("Ayni sabit veri uzerinde BREAKOUT, PULLBACK ve MEAN_REVERSION test ediliyor.")
print()


# =====================================================
# FIXED DATASET
# =====================================================

df = get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=TOTAL_LIMIT,
    end_time=FIXED_END_TIME,
    only_closed=True,
)

if len(df) < 5000:
    raise RuntimeError("Yeterli veri indirilemedi.")


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
df["BB_MID"] = df["Close"].rolling(window=20).mean()
df["BB_STD"] = df["Close"].rolling(window=20).std(ddof=0)

train_end = int(len(df) * TRAIN_RATIO)

print("Toplam mum            :", len(df))
print("Train mum sayisi      :", train_end)
print("Validation mum sayisi :", len(df) - train_end)
print("Ilk tarih             :", df["OpenTime"].iloc[0])
print("Train bitis           :", df["OpenTime"].iloc[train_end - 1])
print("Validation baslangic  :", df["OpenTime"].iloc[train_end])
print("Son tarih             :", df["OpenTime"].iloc[-1])
print()


# =====================================================
# STRATEGY FACTORY
# =====================================================

def make_strategy(params):
    family = params["family"]

    if family == "BREAKOUT":
        def strategy(current_df):
            return generate_breakout_signal(
                current_df,
                candle_index=-1,
                lookback=params["lookback"],
                adx_min=params["adx"],
                volume_min=0.90,
                allow_long=params["allow_long"],
                allow_short=params["allow_short"],
            )

        return strategy

    if family == "PULLBACK":
        def strategy(current_df):
            return generate_pullback_signal(
                current_df,
                candle_index=-1,
                adx_min=params["adx"],
                ema_tolerance_percent=params["tolerance"],
                allow_long=params["allow_long"],
                allow_short=params["allow_short"],
            )

        return strategy

    if family == "MEAN_REVERSION":
        def strategy(current_df):
            return generate_mean_reversion_signal(
                current_df,
                candle_index=-1,
                adx_max=params["adx_max"],
                bb_std_multiplier=params["bb_std"],
                rsi_extreme=30,
                allow_long=params["allow_long"],
                allow_short=params["allow_short"],
            )

        return strategy

    raise ValueError(f"Bilinmeyen strateji ailesi: {family}")


def run_segment(params, start_index, end_index):
    return run_backtest(
        df=df,
        signal_function=make_strategy(params),
        initial_balance=INITIAL_BALANCE,
        risk_percent=1.0,
        max_leverage=1,
        max_hold_bars=params["max_hold_bars"],
        min_stop_percent=0.25,
        atr_multiplier=params["atr_multiplier"],
        reward_multiplier=params["rr"],
        commission_percent=0.04,
        slippage_percent=0.02,
        charge_exit_costs=True,
        start_index=start_index,
        end_index=end_index,
    )


def stats(result):
    return {
        "trades": result["total_trades"],
        "pf": result["profit_factor"],
        "net": result["net_profit"],
        "dd": result["max_drawdown"],
        "wr": result["win_rate"],
        "long_net": result["long_net"],
        "short_net": result["short_net"],
    }


def side_modes(names):
    mapping = {
        "SHORT_ONLY": (False, True),
        "LONG_ONLY": (True, False),
        "BOTH": (True, True),
    }

    return [(name, *mapping[name]) for name in names]


# =====================================================
# CONFIGURATIONS
# =====================================================

configs = []

# 16 breakout configurations
for side, allow_long, allow_short in side_modes(["SHORT_ONLY", "BOTH"]):
    for lookback, adx, rr in product([20, 40], [18.0, 25.0], [1.5, 2.0]):
        configs.append(
            {
                "family": "BREAKOUT",
                "side": side,
                "allow_long": allow_long,
                "allow_short": allow_short,
                "lookback": lookback,
                "adx": adx,
                "rr": rr,
                "atr_multiplier": 2.0,
                "max_hold_bars": 96,
            }
        )

# 16 trend-pullback configurations
for side, allow_long, allow_short in side_modes(["SHORT_ONLY", "BOTH"]):
    for tolerance, adx, rr in product([0.10, 0.25], [18.0, 25.0], [1.5, 2.0]):
        configs.append(
            {
                "family": "PULLBACK",
                "side": side,
                "allow_long": allow_long,
                "allow_short": allow_short,
                "tolerance": tolerance,
                "adx": adx,
                "rr": rr,
                "atr_multiplier": 1.75,
                "max_hold_bars": 72,
            }
        )

# 24 range mean-reversion configurations
for side, allow_long, allow_short in side_modes(["SHORT_ONLY", "LONG_ONLY", "BOTH"]):
    for bb_std, adx_max, rr in product([1.8, 2.2], [16.0, 20.0], [1.0, 1.5]):
        configs.append(
            {
                "family": "MEAN_REVERSION",
                "side": side,
                "allow_long": allow_long,
                "allow_short": allow_short,
                "bb_std": bb_std,
                "adx_max": adx_max,
                "rr": rr,
                "atr_multiplier": 1.5,
                "max_hold_bars": 36,
            }
        )

print("Toplam V3 kombinasyon:", len(configs))
print()


# =====================================================
# TRAIN
# =====================================================

train_results = []

for number, params in enumerate(configs, start=1):
    result = run_segment(
        params=params,
        start_index=200,
        end_index=train_end,
    )

    train = stats(result)

    train_results.append(
        {
            "params": params,
            "train": train,
        }
    )

    print(
        f"[{number:02d}/{len(configs)}] "
        f"{params['family']:<14} {params['side']:<10} "
        f"PF={train['pf']:.2f} Net={train['net']:.2f} "
        f"DD={train['dd']:.2f}% Islem={train['trades']}"
    )


# =====================================================
# SELECT TOP 6 FROM EACH FAMILY FOR VALIDATION
# =====================================================

selected = []

for family in ["BREAKOUT", "PULLBACK", "MEAN_REVERSION"]:
    family_items = [
        item for item in train_results
        if item["params"]["family"] == family
        and item["train"]["trades"] >= 20
    ]

    if not family_items:
        family_items = [
            item for item in train_results
            if item["params"]["family"] == family
        ]

    family_items.sort(
        key=lambda item: (
            item["train"]["pf"],
            item["train"]["net"],
            -item["train"]["dd"],
            item["train"]["trades"],
        ),
        reverse=True,
    )

    selected.extend(family_items[:6])


print()
print("=" * 96)
print("EN IYI AILE ADAYLARI -> VALIDATION")
print("=" * 96)

validated = []

for number, item in enumerate(selected, start=1):
    params = item["params"]

    validation_result = run_segment(
        params=params,
        start_index=train_end,
        end_index=len(df),
    )

    validation = stats(validation_result)

    minimum_pf = min(item["train"]["pf"], validation["pf"])
    sample_penalty = 0.25 if validation["trades"] < 15 else 0.0
    robust_score = minimum_pf - sample_penalty

    passed = (
        item["train"]["pf"] > 1.0
        and validation["pf"] > 1.0
        and item["train"]["trades"] >= 20
        and validation["trades"] >= 15
    )

    validated.append(
        {
            "params": params,
            "train": item["train"],
            "validation": validation,
            "robust_score": robust_score,
            "passed": passed,
        }
    )

    print(
        f"[{number:02d}/{len(selected)}] "
        f"{params['family']:<14} {params['side']:<10} | "
        f"TRAIN PF={item['train']['pf']:.2f} Net={item['train']['net']:.2f} | "
        f"VAL PF={validation['pf']:.2f} Net={validation['net']:.2f} "
        f"Islem={validation['trades']} | "
        f"{'PASS' if passed else 'FAIL'}"
    )


validated.sort(
    key=lambda item: (
        item["passed"],
        item["robust_score"],
        item["validation"]["pf"],
        item["validation"]["net"],
        -item["validation"]["dd"],
    ),
    reverse=True,
)


# =====================================================
# FAMILY SUMMARY
# =====================================================

print()
print("=" * 96)
print("STRATEJI AILE OZETI")
print("=" * 96)

for family in ["BREAKOUT", "PULLBACK", "MEAN_REVERSION"]:
    candidates = [
        item for item in validated
        if item["params"]["family"] == family
    ]

    if not candidates:
        print(f"{family:<14}: validation adayi yok")
        continue

    best = max(candidates, key=lambda item: item["robust_score"])

    print(
        f"{family:<14}: "
        f"Robust={best['robust_score']:.2f} | "
        f"TRAIN PF={best['train']['pf']:.2f} | "
        f"VAL PF={best['validation']['pf']:.2f} | "
        f"VAL Net={best['validation']['net']:.2f} | "
        f"{'PASS' if best['passed'] else 'FAIL'}"
    )


# =====================================================
# ROBUST TOP 10
# =====================================================

print()
print("=" * 96)
print("V3 ROBUST SIRALAMA - ILK 10")
print("=" * 96)

for rank, item in enumerate(validated[:10], start=1):
    params = item["params"]
    train = item["train"]
    val = item["validation"]

    variable_params = {
        key: value
        for key, value in params.items()
        if key not in {
            "family",
            "side",
            "allow_long",
            "allow_short",
            "atr_multiplier",
            "max_hold_bars",
        }
    }

    print()
    print("SIRA           :", rank)
    print("Durum          :", "PASS" if item["passed"] else "FAIL")
    print("Strateji       :", params["family"])
    print("Taraf          :", params["side"])
    print("Parametreler   :", variable_params)
    print("ATR Mult       :", params["atr_multiplier"])
    print("Max Hold       :", params["max_hold_bars"])
    print("Robust Skor    :", round(item["robust_score"], 3))
    print(
        "TRAIN          :",
        f"PF {train['pf']:.2f} | Net {train['net']:.2f} | "
        f"DD {train['dd']:.2f}% | Islem {train['trades']}",
    )
    print(
        "VALIDATION     :",
        f"PF {val['pf']:.2f} | Net {val['net']:.2f} | "
        f"DD {val['dd']:.2f}% | Islem {val['trades']}",
    )

print()
print("=" * 96)
print("KURAL: Train ve validation birlikte PF > 1 olmadan strateji kabul edilmiyor.")
print("Bu test de kar garantisi degildir; PASS adaylari daha sonra walk-forward testine girecek.")
print("=" * 96)
