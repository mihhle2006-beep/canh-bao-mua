# -*- coding: utf-8 -*-
"""
DỮ LIỆU GIÁ: VNDirect → DNSE (tự chuyển nguồn), thử lại khi lỗi, cache cục bộ khi mọi nguồn lỗi.
  • Khung: ngày "D", giờ "60", phút "5"/"15"/"30". Giá cổ phiếu theo NGHÌN ĐỒNG (tự quy đổi nếu nguồn trả đồng).
  • bo_nen_chua_dong: bỏ nến đang chạy (chưa kết thúc) → tín hiệu không "nhấp nháy" trong lúc nến chưa đóng.
"""
import os
import re
import time
from datetime import date

import pandas as pd
import requests

from .cau_hinh import PHIEN, THU_MUC_CACHE

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36", "Accept": "application/json, text/plain, */*"}
SO_NGAY_LAY = {"D": None, "60": 150, "30": 60, "15": 40, "5": 15}
DNSE_KHUNG = {"D": "1D", "60": "1H", "30": "30", "15": "15", "5": "5"}


def gio_viet_nam():
    return (pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=7)).tz_localize(None)


def _get(url, params, so_lan=3):
    loi = None
    for k in range(so_lan):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            return r.json()
        except (requests.RequestException, ValueError) as e:
            loi = e
            time.sleep(0.6 * 2 ** k)
    raise ValueError(str(loi)[:80])


def _tu_unix(j, khung):
    if not isinstance(j, dict) or not j.get("t"):
        raise ValueError("không có dữ liệu")
    t = pd.to_datetime(pd.Series(j["t"]).astype("int64"), unit="s") + pd.Timedelta(hours=7)
    if khung == "D":
        t = t.dt.normalize()
    return pd.DataFrame({"time": t.values, "open": j["o"], "high": j["h"], "low": j["l"], "close": j["c"],
                         "volume": j.get("v", [0] * len(j["t"]))})


def tu_vndirect(ma, tu, den, khung):
    return _tu_unix(_get("https://dchart-api.vndirect.com.vn/dchart/history",
                         {"resolution": khung, "symbol": ma, "from": tu, "to": den}), khung)


def tu_dnse(ma, tu, den, khung, chi_so=False):
    url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{'index' if chi_so else 'stock'}"
    return _tu_unix(_get(url, {"symbol": ma, "resolution": DNSE_KHUNG[khung], "from": tu, "to": den}), khung)


def chuan_hoa(df, chi_so=False):
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"])
    df = df[df.close > 0]
    for c in ("open", "high", "low"):
        df[c] = df[c].where(df[c] > 0, df.close)
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    df["volume"] = df["volume"].fillna(0)
    if not chi_so and len(df) and df.close.median() > 1000:      # nguồn trả theo ĐỒNG
        df[["open", "high", "low", "close"]] /= 1000
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _cache(khoa):
    os.makedirs(THU_MUC_CACHE, exist_ok=True)
    return os.path.join(THU_MUC_CACHE, re.sub(r"[^\w\-]", "_", khoa) + ".csv")


def tai(ma, khung="D", tu_ngay="2021-01-01", chi_so=False):
    """Tải nến; mọi nguồn lỗi → dùng cache (in cảnh báo). Trả DataFrame hoặc None."""
    den = int(time.time()) + 86400
    if SO_NGAY_LAY.get(khung):
        tu = int(time.time()) - SO_NGAY_LAY[khung] * 86400
    else:
        tu = int(pd.Timestamp(tu_ngay).timestamp())
    loi = []
    for ten, ham in (("VNDirect", lambda: tu_vndirect(ma, tu, den, khung)),
                     ("DNSE", lambda: tu_dnse(ma, tu, den, khung, chi_so))):
        try:
            df = chuan_hoa(ham(), chi_so)
            if df.empty:
                raise ValueError("rỗng")
            try:
                df.to_csv(_cache(f"{ma}_{khung}"))
            except OSError:
                pass
            return df
        except Exception as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    if os.path.exists(_cache(f"{ma}_{khung}")):
        df = pd.read_csv(_cache(f"{ma}_{khung}"), index_col=0, parse_dates=True).astype(float)
        print(f"  ⚠ {ma} {khung}: mọi nguồn lỗi ({'; '.join(loi)}) → dùng cache đến {df.index[-1]}")
        return df
    print(f"  ✘ {ma} {khung}: không lấy được ({'; '.join(loi)})")
    return None


def gop_tuan(df_ngay, bay_gio=None):
    """Nến tuần (kết thúc thứ Sáu), BỎ tuần chưa kết thúc (trước 15h thứ Sáu)."""
    w = df_ngay.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min",
                                       "close": "last", "volume": "sum"}).dropna()
    bay_gio = pd.Timestamp(bay_gio) if bay_gio is not None else gio_viet_nam()
    if len(w) > 1 and bay_gio < w.index[-1].normalize() + pd.Timedelta(hours=15):
        w = w.iloc[:-1]
    return w


def _ket_thuc_phien(t):
    """Giờ kết thúc phiên (sáng/chiều) chứa thời điểm t."""
    for bd, kt in PHIEN:
        a = t.normalize() + pd.Timedelta(bd + ":00")
        b = t.normalize() + pd.Timedelta(kt + ":00")
        if a <= t < b:
            return b
    return None


def bo_nen_chua_dong(df, khung, bay_gio=None):
    """Bỏ nến phút/giờ CHƯA ĐÓNG: nến kết thúc = min(bắt đầu + độ dài, giờ nghỉ/đóng cửa của phiên đó)."""
    if df is None or not len(df) or khung == "D":
        return df
    bay_gio = pd.Timestamp(bay_gio) if bay_gio is not None else gio_viet_nam()
    dai = pd.Timedelta(minutes=int(khung))
    t = df.index[-1]
    het = t + dai
    kt = _ket_thuc_phien(t)
    if kt is not None:
        het = min(het, kt)
    return df.iloc[:-1] if bay_gio < het else df


def trong_phien(bay_gio=None):
    bay_gio = pd.Timestamp(bay_gio) if bay_gio is not None else gio_viet_nam()
    if bay_gio.weekday() >= 5:
        return False
    return _ket_thuc_phien(bay_gio) is not None


def hom_nay_co_giao_dich(df_ngay, bay_gio=None):
    """Ngày lễ / nghỉ: không có nến ngày của hôm nay (trong phiên các nguồn đã có nến ngày đang chạy)."""
    bay_gio = pd.Timestamp(bay_gio) if bay_gio is not None else gio_viet_nam()
    return df_ngay is not None and len(df_ngay) and df_ngay.index[-1].normalize() == bay_gio.normalize()


def ngay_hom_nay():
    return date.today()
