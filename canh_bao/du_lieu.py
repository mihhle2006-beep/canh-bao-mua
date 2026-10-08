# -*- coding: utf-8 -*-
"""
DỮ LIỆU GIÁ: VNDirect → DNSE → SSI iBoard → VCI → Yahoo (tự chuyển nguồn; nguồn nào không hỗ trợ khung đó thì bỏ qua),
thử lại khi lỗi, cache cục bộ khi mọi nguồn lỗi. Không dùng vnstock / Vietstock.
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


SSI_KHUNG = {"D": "1D", "60": "60", "30": "30", "15": "15", "5": "5"}
VCI_KHUNG = {"D": "ONE_DAY", "60": "ONE_HOUR"}          # phút: VCI chỉ có 1 phút → bỏ qua cho gọn


def tu_ssi(ma, tu, den, khung, chi_so=False):
    j = _get("https://iboard-api.ssi.com.vn/statistics/charts/history",
             {"resolution": SSI_KHUNG[khung], "symbol": ma, "from": tu, "to": den})
    return _tu_unix(j.get("data", j) if isinstance(j, dict) else None, khung)


def tu_vci(ma, tu, den, khung, chi_so=False):
    if khung not in VCI_KHUNG:
        raise ValueError("không hỗ trợ khung này")
    so_nen = max((den - tu) // 86400, 5) * (1 if khung == "D" else 7) + 10
    r = requests.post("https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart",
                      json={"timeFrame": VCI_KHUNG[khung], "symbols": [ma], "to": den, "countBack": int(so_nen)},
                      headers={**HEADERS, "Content-Type": "application/json",
                               "Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"},
                      timeout=20)
    if r.status_code != 200:
        raise ValueError(f"HTTP {r.status_code}")
    j = r.json()
    df = _tu_unix(j[0] if isinstance(j, list) and j else None, khung)
    return df[df.time >= pd.Timestamp(tu, unit="s")]


def tu_yahoo(ma, tu, den, khung, chi_so=False):
    if chi_so or khung != "D":
        raise ValueError("chỉ hỗ trợ giá ngày cổ phiếu")
    j = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ma}.VN",
             {"period1": tu, "period2": den, "interval": "1d"}, so_lan=2)
    r = (j.get("chart", {}).get("result") or [None])[0]
    if not r or not r.get("timestamp"):
        raise ValueError("không có dữ liệu")
    q = r["indicators"]["quote"][0]
    return _tu_unix({"t": r["timestamp"], "o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"],
                     "v": q["volume"]}, khung)


def cac_nguon(ma, tu, den, khung, chi_so=False):
    return [("VNDirect", lambda: tu_vndirect(ma, tu, den, khung)),
            ("DNSE", lambda: tu_dnse(ma, tu, den, khung, chi_so)),
            ("SSI", lambda: tu_ssi(ma, tu, den, khung, chi_so)),
            ("VCI", lambda: tu_vci(ma, tu, den, khung, chi_so)),
            ("Yahoo", lambda: tu_yahoo(ma, tu, den, khung, chi_so))]


NGUON_DA_DUNG = {}           # (mã, khung) → nguồn – in ra để biết nguồn nào đang sống


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


BIEN_DO_NEN_NGO = 0.16      # > biên độ tối đa mọi sàn (HOSE 7%, HNX 10%, UPCoM 15%)


def nen_cuoi_ngo(df):
    """
    Nến NGÀY cuối lệch > 16% so với phiên trước CỦA CHÍNH NGUỒN ĐÓ (hơn biên độ mọi sàn: HOSE 7%, HNX 10%, UPCoM 15%)
    → nguồn điều chỉnh DỞ DANG (VD VNDirect 08/10/2026: HDB 28,10 → 21,54 = 28,0 ÷ 1,3 – mới chia phiên cuối cho đợt
    chia cổ phiếu, các phiên trước chưa chia; nguồn khác 28,00). Ngày GDKHQ thật mọi nguồn chưa điều chỉnh đều lệch
    như nhau → tai() vẫn dùng (xem tai).
    """
    if df is None or len(df) < 2:
        return False
    truoc = float(df.close.iloc[-2])
    return bool(truoc > 0 and abs(float(df.close.iloc[-1]) / truoc - 1) > BIEN_DO_NEN_NGO)


def tai(ma, khung="D", tu_ngay="2019-01-01", chi_so=False):
    """
    Tải nến; mọi nguồn lỗi → dùng cache (in cảnh báo). Trả DataFrame hoặc None.
    Nến ngày cuối lệch bất thường (nen_cuoi_ngo) → thử nguồn sau (ưu tiên nguồn liền mạch); nguồn nào cũng lệch như
    nhau → đó là biến động thật (GDKHQ chưa điều chỉnh) → dùng nguồn đầu, đủ nến.
    """
    den = int(time.time()) + 86400
    if SO_NGAY_LAY.get(khung):
        tu = int(time.time()) - SO_NGAY_LAY[khung] * 86400
    else:
        tu = int(pd.Timestamp(tu_ngay).timestamp())
    loi, du_phong = [], None
    for ten, ham in cac_nguon(ma, tu, den, khung, chi_so):
        try:
            df = chuan_hoa(ham(), chi_so)
            if df.empty:
                raise ValueError("rỗng")
            if not chi_so and khung == "D" and nen_cuoi_ngo(df):
                du_phong = du_phong if du_phong is not None else (ten, df)
                raise ValueError(f"nến {df.index[-1]:%d/%m} lệch bất thường ({df.close.iloc[-2]:g} → "
                                 f"{df.close.iloc[-1]:g}) – điều chỉnh dở dang?")
            NGUON_DA_DUNG[(ma, khung)] = ten
            try:
                df.to_csv(_cache(f"{ma}_{khung}"))
            except OSError:
                pass
            return df
        except Exception as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    if du_phong is not None:
        ten, df = du_phong
        NGUON_DA_DUNG[(ma, khung)] = ten
        print(f"  ⚠ {ma} {khung}: mọi nguồn đều lệch mạnh phiên cuối ({'; '.join(loi)}) → biến động thật, dùng {ten}")
        return df
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


def tai_lich_su_phut(ma, tu_ngay, khung="15", cua_so=30, nghi=0.3):
    """
    Nến phút DÀI (cho backtest 15'): tải lùi từng cửa sổ `cua_so` ngày từ hôm nay về tu_ngay, gộp & cache
    (cache_gia/<MÃ>_<khung>_lich_su.csv – lần sau chỉ tải phần mới). Nguồn nào giới hạn bao xa thì lấy tới đó
    (3 cửa sổ rỗng liên tiếp → dừng). Trả DataFrame hoặc None.
    """
    path = _cache(f"{ma}_{khung}_lich_su")
    cu = None
    if os.path.exists(path):
        try:
            cu = pd.read_csv(path, index_col=0, parse_dates=True).astype(float)
        except (OSError, ValueError):
            cu = None
    den = int(time.time()) + 86400
    moc = pd.Timestamp(tu_ngay)
    if cu is not None and len(cu):
        moc = max(moc, cu.index[-1].normalize() - pd.Timedelta(days=2))
    phan, rong, t_den = [], 0, den
    while t_den > int(moc.timestamp()) and rong < 3:
        t_tu = max(t_den - cua_so * 86400, int(moc.timestamp()))
        df = None
        for ten, ham in cac_nguon(ma, t_tu, t_den, khung)[:3]:          # VNDirect, DNSE, SSI (có khung phút)
            try:
                df = chuan_hoa(ham())
                if len(df):
                    break
            except Exception:
                df = None
        if df is not None and len(df):
            phan.append(df)
            rong = 0
        else:
            rong += 1
        t_den = t_tu
        time.sleep(nghi)
    if cu is not None:
        phan.append(cu)
    if not phan:
        return None
    out = pd.concat(phan).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    try:
        out.to_csv(path)
    except OSError:
        pass
    return out
