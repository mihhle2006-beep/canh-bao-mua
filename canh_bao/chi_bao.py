# -*- coding: utf-8 -*-
"""Chỉ báo: MACD, RSI, ATR, MA, SuperTrend (giá đóng cửa)."""
import numpy as np
import pandas as pd

from .cau_hinh import MACD_CHAM, MACD_NHANH, MACD_TIN_HIEU


def chi_bao(df):
    d = df.copy()
    c = d.close
    d["MACD"] = c.ewm(span=MACD_NHANH, adjust=False).mean() - c.ewm(span=MACD_CHAM, adjust=False).mean()
    d["SIGNAL"] = d.MACD.ewm(span=MACD_TIN_HIEU, adjust=False).mean()
    delta = c.diff()
    tang = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    giam = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["RSI"] = (100 - 100 / (1 + tang / giam.replace(0, np.nan))).fillna(100)
    tr = pd.concat([d.high - d.low, (d.high - c.shift()).abs(), (d.low - c.shift()).abs()], axis=1).max(axis=1)
    d["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["VolMA20"] = d.volume.rolling(20, min_periods=5).mean()
    for n in (20, 50, 200):
        d[f"MA{n}"] = c.rolling(n, min_periods=n).mean()
    return d


def supertrend(df, n=10, k=3.5):
    """Trả (đường SuperTrend, hướng +1/−1) – như bộ lọc cổ phiếu."""
    h, l, c = df.high.values, df.low.values, df.close.values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values
    hl2 = (h + l) / 2
    tren, duoi = hl2 + k * atr, hl2 - k * atr
    tf, df_ = tren.copy(), duoi.copy()
    huong = np.ones(len(c), int)
    for i in range(1, len(c)):
        tf[i] = tren[i] if (tren[i] < tf[i - 1] or c[i - 1] > tf[i - 1]) else tf[i - 1]
        df_[i] = duoi[i] if (duoi[i] > df_[i - 1] or c[i - 1] < df_[i - 1]) else df_[i - 1]
        huong[i] = (-1 if c[i] < df_[i] else 1) if huong[i - 1] == 1 else (1 if c[i] > tf[i] else -1)
    return pd.Series(np.where(huong == 1, df_, tf), index=df.index), pd.Series(huong, index=df.index)


