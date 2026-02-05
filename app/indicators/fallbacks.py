import numpy as np
import pandas as pd
from types import SimpleNamespace

# Tracks which functions had to be shimmed
MISSING_TALIB_FUNCTIONS = []


def _ensure_float_array(data):
    try:
        arr = np.asarray(data, dtype=float)
    except Exception:
        arr = np.asarray(list(data), dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def _ensure_series(data):
    return pd.Series(_ensure_float_array(data))


def _register_talib_fallback(target_module, name, func):
    # Retrieve existing attribute from the target module
    existing = getattr(target_module, name, None)
    if callable(existing):
        return
    setattr(target_module, name, func)
    MISSING_TALIB_FUNCTIONS.append(name)


def _fallback_sma(data, timeperiod=30):
    series = _ensure_series(data)
    return (
        series.rolling(window=int(max(1, timeperiod)), min_periods=1).mean().to_numpy()
    )


def _fallback_rsi(data, timeperiod=14):
    period = int(max(1, timeperiod))
    series = _ensure_series(data)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0).to_numpy()


def _fallback_macd(data, fastperiod=12, slowperiod=26, signalperiod=9):
    fast = int(max(1, fastperiod))
    slow = int(max(fast + 1, slowperiod))
    signal = int(max(1, signalperiod))
    series = _ensure_series(data)
    fast_ema = series.ewm(span=fast, adjust=False).mean()
    slow_ema = series.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line.to_numpy(), signal_line.to_numpy(), hist.to_numpy()


def _fallback_stoch(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3):
    fast_k_period = int(max(1, fastk_period))
    slow_k_period = int(max(1, slowk_period))
    slow_d_period = int(max(1, slowd_period))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    lowest_low = low_s.rolling(window=fast_k_period, min_periods=1).min()
    highest_high = high_s.rolling(window=fast_k_period, min_periods=1).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    fast_k = ((close_s - lowest_low) / denom) * 100
    fast_k = fast_k.fillna(0)
    slow_k = fast_k.rolling(window=slow_k_period, min_periods=1).mean()
    slow_d = slow_k.rolling(window=slow_d_period, min_periods=1).mean()
    return slow_k.fillna(0).to_numpy(), slow_d.fillna(0).to_numpy()


def _fallback_true_range(high_s, low_s, close_s):
    prev_close = close_s.shift(1)
    ranges = pd.concat(
        [
            (high_s - low_s).abs(),
            (high_s - prev_close).abs(),
            (low_s - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _fallback_atr(high, low, close, timeperiod=14):
    period = int(max(1, timeperiod))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    tr = _fallback_true_range(high_s, low_s, close_s)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr.fillna(0).to_numpy()


def _fallback_adx(high, low, close, timeperiod=14):
    period = int(max(1, timeperiod))
    high_s = _ensure_series(high)
    low_s = _ensure_series(low)
    close_s = _ensure_series(close)
    up_move = high_s.diff()
    down_move = low_s.shift(1) - low_s
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = _fallback_true_range(high_s, low_s, close_s)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = (
        plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    ) * 100
    minus_di = (
        minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / atr.replace(0, np.nan)
    ) * 100
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx.fillna(0).to_numpy()


def _fallback_obv(close, volume):
    close_arr = _ensure_float_array(close)
    volume_arr = _ensure_float_array(volume)
    if close_arr.size == 0:
        return np.array([])
    obv = np.zeros_like(close_arr)
    for idx in range(1, len(close_arr)):
        if close_arr[idx] > close_arr[idx - 1]:
            obv[idx] = obv[idx - 1] + volume_arr[idx]
        elif close_arr[idx] < close_arr[idx - 1]:
            obv[idx] = obv[idx - 1] - volume_arr[idx]
        else:
            obv[idx] = obv[idx - 1]
    return obv


def _fallback_bbands(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0):
    period = int(max(1, timeperiod))
    series = _ensure_series(close)
    mid = series.rolling(window=period, min_periods=1).mean()
    std = series.rolling(window=period, min_periods=1).std(ddof=0).fillna(0)
    upper = mid + nbdevup * std
    lower = mid - nbdevdn * std
    return upper.to_numpy(), mid.to_numpy(), lower.to_numpy()


def _zero_pattern(*args, **kwargs):
    first = args[0] if args else []
    length = len(_ensure_float_array(first))
    return np.zeros(length)


def register_fallbacks(target_module):
    """Register all fallback functions on the target module."""
    _register_talib_fallback(target_module, "SMA", _fallback_sma)
    _register_talib_fallback(target_module, "RSI", _fallback_rsi)
    _register_talib_fallback(target_module, "MACD", _fallback_macd)
    _register_talib_fallback(target_module, "STOCH", _fallback_stoch)
    _register_talib_fallback(target_module, "ADX", _fallback_adx)
    _register_talib_fallback(target_module, "ATR", _fallback_atr)
    _register_talib_fallback(target_module, "OBV", _fallback_obv)
    _register_talib_fallback(target_module, "BBANDS", _fallback_bbands)

    for _pattern_name in [
        "CDLHAMMER",
        "CDLENGULFING",
        "CDLMORNINGSTAR",
        "CDLHANGINGMAN",
        "CDLEVENINGSTAR",
    ]:
        _register_talib_fallback(target_module, _pattern_name, _zero_pattern)
