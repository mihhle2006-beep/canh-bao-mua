# -*- coding: utf-8 -*-
"""Chỉ báo: MACD, RSI, ATR, MA, SuperTrend, ADX, VWAP phiên, đỉnh/đáy theo MACD (giá đóng cửa, có xác nhận)."""
import numpy as np
import pandas as pd

from .cau_hinh import BO_QUA_DAU, MACD_CHAM, MACD_NHANH, MACD_TIN_HIEU, N_XAC_NHAN


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


def cat_len(a, b, n):
    """a vừa cắt lên b trong n nến gần nhất → số nến trước (0 = nến cuối), không có → None."""
    tren = (a > b).values
    for k in range(min(n, len(tren) - 1)):
        i = len(tren) - 1 - k
        if tren[i] and not tren[i - 1]:
            return k
    return None


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


def adx(df, n=14):
    """ADX Wilder → (ADX, +DI, −DI)."""
    h, l, c = df.high, df.low, df.close
    len_, xuong = h.diff(), -l.diff()
    pdm = np.where((len_ > xuong) & (len_ > 0), len_, 0.0)
    mdm = np.where((xuong > len_) & (xuong > 0), xuong, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * pd.Series(mdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi


def vwap_phien(df_phut):
    """VWAP của phiên hôm nay (ngày của nến phút cuối)."""
    if df_phut is None or not len(df_phut):
        return np.nan
    hom_nay = df_phut[df_phut.index.normalize() == df_phut.index[-1].normalize()]
    gia = (hom_nay.high + hom_nay.low + hom_nay.close) / 3
    kl = hom_nay.volume.sum()
    return float((gia * hom_nay.volume).sum() / kl) if kl > 0 else float(hom_nay.close.iloc[-1])


def dinh_day(d):
    """Đỉnh/đáy mỗi đoạn MACD (theo GIÁ ĐÓNG CỬA). Xác nhận khi đoạn đã kết thúc hoặc ≥ N_XAC_NHAN nến sau đó."""
    x = d.iloc[BO_QUA_DAU:]
    if len(x) < 5:
        return pd.DataFrame(columns=["time", "gia", "loai", "xac_nhan"])
    dau = np.sign(x.MACD).replace(0, np.nan).ffill().fillna(1)
    nhom = list(x.groupby((dau != dau.shift()).cumsum()))
    rows = []
    for k, (_, g) in enumerate(nhom):
        duong = dau.loc[g.index[0]] > 0
        t = g.close.idxmax() if duong else g.close.idxmin()
        sau = len(d) - 1 - d.index.get_loc(t)
        rows.append([t, float(g.close.loc[t]), "Đỉnh" if duong else "Đáy", k < len(nhom) - 1 or sau >= N_XAC_NHAN])
    return pd.DataFrame(rows, columns=["time", "gia", "loai", "xac_nhan"])
