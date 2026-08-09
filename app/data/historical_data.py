import time

import pandas as pd
import requests


def _to_milliseconds(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")

    return int(timestamp.timestamp() * 1000)


def get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=10000,
    end_time=None,
    only_closed=True,
):
    """Download Binance spot klines backwards from an optional fixed end time.

    end_time can be a UTC datetime string, pandas Timestamp, or milliseconds.
    Leaving it as None preserves the old behaviour and downloads the latest data.
    A fixed end_time makes repeated backtests reproducible.
    """
    url = "https://api.binance.com/api/v3/klines"

    all_data = []
    request_end_time = _to_milliseconds(end_time)

    while len(all_data) < total_limit:
        remaining = total_limit - len(all_data)
        request_limit = min(1000, remaining)

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": request_limit,
        }

        if request_end_time is not None:
            params["endTime"] = request_end_time

        response = requests.get(
            url,
            params=params,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()

        if not data:
            break

        all_data = data + all_data
        request_end_time = data[0][0] - 1

        print(
            f"Veri indiriliyor: "
            f"{len(all_data)} / {total_limit}"
        )

        time.sleep(0.15)

    columns = [
        "OpenTime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "CloseTime",
        "QuoteVolume",
        "Trades",
        "TakerBase",
        "TakerQuote",
        "Ignore",
    ]

    df = pd.DataFrame(all_data, columns=columns)

    if df.empty:
        return df

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["CloseTime"] = pd.to_numeric(df["CloseTime"], errors="coerce")

    if only_closed:
        now_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
        df = df[df["CloseTime"] < now_ms]

    df = df[
        [
            "OpenTime",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "CloseTime",
        ]
    ].copy()

    df["OpenTime"] = pd.to_datetime(
        df["OpenTime"],
        unit="ms",
        utc=True,
    ).dt.tz_localize(None)

    df["CloseTime"] = pd.to_datetime(
        df["CloseTime"],
        unit="ms",
        utc=True,
    ).dt.tz_localize(None)

    df = df.dropna(
        subset=["Open", "High", "Low", "Close", "Volume"]
    )

    df = df.drop_duplicates(subset="OpenTime")
    df = df.sort_values("OpenTime")
    df = df.tail(total_limit)
    df = df.reset_index(drop=True)

    print()
    print("Toplam mum:", len(df))

    if not df.empty:
        print("İlk tarih :", df["OpenTime"].iloc[0])
        print("Son tarih :", df["OpenTime"].iloc[-1])

    print()

    return df
