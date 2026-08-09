import math


def analyze_volume(df, period=20, candle_index=-2):
    """Hacmi, son N mumun ortalama hacmiyle karşılaştırır.

    Backtest sırasında VOLUME_MA önceden hesaplandıysa onu kullanır.
    Böylece her mumda rolling hesabını baştan yapmayız.
    """

    last_volume = df["Volume"].iloc[candle_index]

    if "VOLUME_MA" in df.columns:
        avg_volume = df["VOLUME_MA"].iloc[candle_index]
    else:
        avg_volume = (
            df["Volume"]
            .rolling(window=period)
            .mean()
            .iloc[candle_index]
        )

    if avg_volume is None or math.isnan(float(avg_volume)) or avg_volume <= 0:
        ratio = 0
    else:
        ratio = last_volume / avg_volume

    if ratio >= 1.5:
        status = "ÇOK YÜKSEK"
    elif ratio >= 1.1:
        status = "YÜKSEK"
    elif ratio >= 0.8:
        status = "NORMAL"
    else:
        status = "DÜŞÜK"

    return {
        "volume": last_volume,
        "average_volume": avg_volume,
        "ratio": ratio,
        "status": status,
    }
