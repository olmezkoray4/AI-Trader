import numpy as np
import pandas as pd


def calculate_adx(df, period=14):
    """Return ADX, +DI and -DI using Wilder-style exponential smoothing."""
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0.0,
        ),
        index=df.index,
        dtype=float,
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0.0,
        ),
        index=df.index,
        dtype=float,
    )

    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    alpha = 1 / period

    atr = true_range.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=period,
    ).mean()

    smoothed_plus_dm = plus_dm.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=period,
    ).mean()

    smoothed_minus_dm = minus_dm.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=period,
    ).mean()

    plus_di = 100 * smoothed_plus_dm / atr.replace(0, np.nan)
    minus_di = 100 * smoothed_minus_dm / atr.replace(0, np.nan)

    di_sum = (plus_di + minus_di).replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / di_sum

    adx = dx.ewm(
        alpha=alpha,
        adjust=False,
        min_periods=period,
    ).mean()

    return adx, plus_di, minus_di
