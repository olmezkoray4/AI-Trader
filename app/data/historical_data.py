import time
import requests
import pandas as pd


def get_historical_klines(
    symbol="BTCUSDT",
    interval="5m",
    total_limit=10000,
):
    url = "https://api.binance.com/api/v3/klines"

    all_data = []
    end_time = None

    while len(all_data) < total_limit:

        remaining = total_limit - len(all_data)
        request_limit = min(1000, remaining)

        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": request_limit,
        }

        if end_time is not None:
            params["endTime"] = end_time

        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            break

        all_data = data + all_data

        # Bir sonraki istekte daha eski mumlara git
        end_time = data[0][0] - 1

        print(
            f"Veri indiriliyor: "
            f"{len(all_data)} / {total_limit}"
        )

        time.sleep(0.2)

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

    df = pd.DataFrame(
        all_data,
        columns=columns,
    )

    df = df[
        [
            "OpenTime",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]
    ]

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    for column in numeric_columns:
        df[column] = df[column].astype(float)

    df["OpenTime"] = pd.to_datetime(
        df["OpenTime"],
        unit="ms",
    )

    df = df.drop_duplicates(
        subset="OpenTime"
    )

    df = df.sort_values(
        "OpenTime"
    )

    df = df.reset_index(drop=True)

    print()
    print("Toplam mum:", len(df))
    print("İlk tarih :", df["OpenTime"].iloc[0])
    print("Son tarih :", df["OpenTime"].iloc[-1])
    print()

    return df