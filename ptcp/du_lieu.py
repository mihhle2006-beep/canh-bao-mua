# -*- coding: utf-8 -*-
"""Lấy dữ liệu giá / thông tin doanh nghiệp: API, vnstock, CSV, cache, nhớ trong phiên."""
# flake8: noqa: F401
import sys
import os
import io
import re
import json
import time
import base64
import shutil
import zipfile
import builtins
import textwrap
import subprocess
import html as _html
from datetime import datetime, date

import requests
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
from numpy.lib.stride_tricks import sliding_window_view as _cua_so_truot
from . import cau_hinh as cfg
from .cau_hinh import (
    HEADERS, THOI_GIAN_CHO, THU_MUC_CACHE,
)
from .in_an import (
    _print_goc, in_ra, so_vn,
)


# ==========================================================================
# 1. LẤY DỮ LIỆU (Ngày & Giờ). Tuần được gộp từ dữ liệu ngày.
# ==========================================================================
def _ts(ngay_str, cong=0):
    return int(datetime.strptime(ngay_str, "%Y-%m-%d").timestamp()) + cong


def _goi_api(url, params=None, json_body=None, headers=None, so_lan=None, timeout=None):
    """
    [MỚI] Gọi API an toàn: thử lại có backoff, kiểm tra status_code & content-type TRƯỚC khi .json().
    Lỗi kiểu 'Expecting value: line 1 column 1' (API trả rỗng/HTML do đổi endpoint, thiếu header, bị chặn)
    được báo rõ nguyên nhân thay vì lỗi giải mã JSON.
    """
    so_lan = so_lan or cfg.SO_LAN_THU
    h = {**HEADERS, **(headers or {})}
    loi = None
    for k in range(so_lan):
        try:
            if json_body is not None:
                r = requests.post(url, json=json_body, headers=h, timeout=timeout or THOI_GIAN_CHO)
            else:
                r = requests.get(url, params=params, headers=h, timeout=timeout or THOI_GIAN_CHO)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            txt = r.text.strip()
            if not txt:
                raise ValueError("phản hồi rỗng")
            ct = r.headers.get("content-type", "").lower()
            if "json" not in ct and txt[:1] not in "{[":
                raise ValueError(f"không phải JSON ({ct.split(';')[0] or 'không rõ'}: {txt[:30]!r})")
            return r.json()
        except (requests.RequestException, ValueError) as e:
            loi = e
            ma = str(e)
            if ma.startswith("HTTP 4") and "429" not in ma:     # 4xx (trừ 429) – thử lại vô ích
                break
            if k < so_lan - 1:
                time.sleep(0.6 * 2 ** k)
    raise ValueError(str(loi)[:120])


def _tu_dang_tohlcv(j, chia_1000=False, ngay=True):
    """Chuẩn TradingView {t, o, h, l, c, v} → DataFrame."""
    if not isinstance(j, dict) or not j.get("t"):
        raise ValueError("không có dữ liệu")
    t = pd.to_datetime(pd.Series(j["t"]).astype("int64"), unit="s") + pd.Timedelta(hours=7)   # UTC → giờ VN
    if ngay:
        t = t.dt.normalize()
    df = pd.DataFrame({"time": t.values, "open": j["o"], "high": j["h"], "low": j["l"],
                       "close": j["c"], "volume": j.get("v", [0] * len(j["t"]))})
    if chia_1000:
        for c in ("open", "high", "low", "close"):
            df[c] = pd.to_numeric(df[c]) / 1000
    return df


def tu_vndirect(symbol, start, end, resolution="D"):
    """resolution: 'D' = ngày, '60' = giờ."""
    url = "https://dchart-api.vndirect.com.vn/dchart/history"
    p = {"resolution": resolution, "symbol": symbol, "from": _ts(start), "to": _ts(end, 86400)}
    return _tu_dang_tohlcv(_goi_api(url, params=p), ngay=resolution == "D")


def tu_vnd_finfo(symbol, start, end):
    """[MỚI] VNDirect finfo – giá ngày ĐÃ ĐIỀU CHỈNH (adOpen/adHigh/adLow/adClose)."""
    url = "https://finfo-api.vndirect.com.vn/v4/stock_prices"
    p = {"sort": "date", "q": f"code:{symbol}~date:gte:{start}~date:lte:{end}", "size": 9999, "page": 1}
    d = (_goi_api(url, params=p) or {}).get("data") or []
    if not d:
        raise ValueError("không có dữ liệu")
    x = pd.DataFrame(d)
    lay = lambda a, b: pd.to_numeric(x[a] if a in x else x[b], errors="coerce")
    return pd.DataFrame({"time": pd.to_datetime(x["date"]), "open": lay("adOpen", "open"),
                         "high": lay("adHigh", "high"), "low": lay("adLow", "low"),
                         "close": lay("adClose", "close"),
                         "volume": pd.to_numeric(x.get("nmVolume", x.get("accumulatedVol", 0)), errors="coerce")})


def tu_tcbs_ngay(symbol, start, end, loai="stock"):
    h = {"Origin": "https://tcinvest.tcbs.com.vn", "Referer": "https://tcinvest.tcbs.com.vn/"}
    p = {"ticker": symbol, "type": loai, "resolution": "D", "from": _ts(start), "to": _ts(end, 86400)}
    try:
        data = (_goi_api("https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term",
                         params=p, headers=h) or {}).get("data") or []
    except ValueError:
        data = []
    if not data:      # endpoint v2 (countBack) – dự phòng khi v1 đổi
        so_ngay = (pd.Timestamp(end) - pd.Timestamp(start)).days + 5
        p2 = {"ticker": symbol, "type": loai, "resolution": "D", "to": _ts(end, 86400), "countBack": so_ngay}
        data = (_goi_api("https://apipubaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term",
                         params=p2, headers=h) or {}).get("data") or []
    if not data:
        raise ValueError("không có dữ liệu")
    df = pd.DataFrame(data).rename(columns={"tradingDate": "time"})
    df["time"] = pd.to_datetime(df["time"].astype(str).str[:10])
    if loai == "stock":
        for c in ("open", "high", "low", "close"):
            df[c] = df[c] / 1000
    return df[df.time >= pd.Timestamp(start)][["time", "open", "high", "low", "close", "volume"]]


def tu_tcbs_gio(symbol, so_nen=800):
    url = "https://apipubaws.tcbs.com.vn/stock-insight/v2/stock/bars"
    p = {"ticker": symbol, "type": "stock", "resolution": "60", "to": int(time.time()), "countBack": so_nen}
    data = (_goi_api(url, params=p, headers={"Origin": "https://tcinvest.tcbs.com.vn"}) or {}).get("data") or []
    if not data:
        raise ValueError("không có dữ liệu")
    df = pd.DataFrame(data).rename(columns={"tradingDate": "time"})
    df["time"] = pd.to_datetime(df["time"].str[:19].str.replace("T", " "))
    for c in ("open", "high", "low", "close"):
        df[c] = df[c] / 1000
    return df[["time", "open", "high", "low", "close", "volume"]]


def tu_ssi(symbol, start, end, resolution="1D"):
    """[MỚI] SSI iBoard (API công khai không chính thức). resolution: '1D' | '60'."""
    url = "https://iboard-api.ssi.com.vn/statistics/charts/history"
    p = {"resolution": resolution, "symbol": symbol, "from": _ts(start), "to": _ts(end, 86400)}
    j = _goi_api(url, params=p, headers={"Origin": "https://iboard.ssi.com.vn",
                                         "Referer": "https://iboard.ssi.com.vn/"})
    return _tu_dang_tohlcv(j.get("data", j) if isinstance(j, dict) else j, ngay=resolution == "1D")


def tu_cafef(symbol, start, end):
    """[MỚI] CafeF – lịch sử giá ngày; OHLC được điều chỉnh theo tỷ lệ GiaDieuChinh / GiaDongCua."""
    url = "https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx"
    d_ = lambda s: datetime.strptime(s, "%Y-%m-%d").strftime("%m/%d/%Y")
    p = {"Symbol": symbol, "StartDate": d_(start), "EndDate": d_(end), "PageIndex": 1, "PageSize": 6000}
    j = _goi_api(url, params=p, headers={"Referer": "https://s.cafef.vn/"})
    rows = ((j or {}).get("Data") or {}).get("Data") or []
    if not rows:
        raise ValueError("không có dữ liệu")
    x = pd.DataFrame(rows)
    so = lambda c: pd.to_numeric(x[c], errors="coerce")
    he_so = (so("GiaDieuChinh") / so("GiaDongCua")).fillna(1.0) if "GiaDieuChinh" in x else 1.0
    return pd.DataFrame({"time": pd.to_datetime(x["Ngay"], dayfirst=True),
                         "open": so("GiaMoCua") * he_so, "high": so("GiaCaoNhat") * he_so,
                         "low": so("GiaThapNhat") * he_so, "close": so("GiaDongCua") * he_so,
                         "volume": so("KhoiLuongKhopLenh")})


# --------------------------------------------------------------------------
# NGUỒN BỔ SUNG: DNSE (Entrade) & VCI (Vietcap) – API công khai, CHƯA KIỂM CHỨNG chính thức
# --------------------------------------------------------------------------
DIA_CHI_NGUON = {
    "vnstock": "thư viện Python vnstock (nguồn VCI/TCBS)",
    "VNDirect": "dchart-api.vndirect.com.vn",
    "VND finfo": "finfo-api.vndirect.com.vn",
    "TCBS": "apipubaws.tcbs.com.vn",
    "SSI": "iboard-api.ssi.com.vn",
    "CafeF": "s.cafef.vn",
    "DNSE": "services.entrade.com.vn",
    "VCI": "trading.vietcap.com.vn",
    "Vietstock": "finance.vietstock.vn",
    "CSV": "file người dùng cung cấp",
    "Cache": f"thư mục {THU_MUC_CACHE}/ (lần chạy trước)",
    "CTCK": "báo cáo CTCK do người dùng nạp vào DU_LIEU_CTCK (tuỳ chọn)",
}


def tu_dnse(symbol, start, end, resolution="1D", loai="stock"):
    """DNSE/Entrade. resolution: '1D' ngày, '1H' giờ; loai: 'stock' | 'index'. Giá cổ phiếu: nghìn đồng."""
    url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{loai}"
    p = {"symbol": symbol, "resolution": resolution, "from": _ts(start), "to": _ts(end, 86400)}
    return _tu_dang_tohlcv(_goi_api(url, params=p), ngay=resolution == "1D")


def tu_vci(symbol, start, end, khung="ONE_DAY", la_chi_so=False):
    """VCI/Vietcap. khung: 'ONE_DAY' | 'ONE_HOUR'. Giá cổ phiếu trả về theo ĐỒNG → đổi sang nghìn đồng."""
    url = "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart"
    so_ngay = max((pd.Timestamp(end) - pd.Timestamp(start)).days, 5)
    so_nen = so_ngay + 10 if khung == "ONE_DAY" else min(so_ngay * 7, 5000)
    h = {"Content-Type": "application/json", "Referer": "https://trading.vietcap.com.vn/",
         "Origin": "https://trading.vietcap.com.vn"}
    body = {"timeFrame": khung, "symbols": [symbol], "to": _ts(end, 86400), "countBack": so_nen}
    j = _goi_api(url, json_body=body, headers=h)
    d = j[0] if isinstance(j, list) and j else None
    df = _tu_dang_tohlcv(d, chia_1000=not la_chi_so, ngay=khung == "ONE_DAY")
    return df[df.time >= pd.Timestamp(start)]


_VNSTOCK = {"da_thu": False, "mod": None}


def tu_vnstock(symbol, start, end, interval="1D"):
    """
    [MỚI] Nguồn qua thư viện vnstock (cộng đồng bảo trì khi API thay đổi). Tự cài lần đầu nếu cfg.TU_CAI_VNSTOCK.
    Thử lần lượt nguồn VCI → TCBS bên trong vnstock. interval: '1D' | '1H'.
    """
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt (cfg.DUNG_VNSTOCK = False)")
    if _VNSTOCK["mod"] is None:
        if _VNSTOCK["da_thu"]:
            raise ValueError("không dùng được vnstock")
        _VNSTOCK["da_thu"] = True
        try:
            import vnstock as _vn                     # noqa: F401
        except ImportError:
            if not cfg.TU_CAI_VNSTOCK:
                raise ValueError("chưa cài vnstock")
            _print_goc("  (Cài thư viện vnstock lần đầu ...)")
            subprocess.call([sys.executable, "-m", "pip", "install", "vnstock", "-q"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                import vnstock as _vn                 # noqa: F401
            except ImportError:
                raise ValueError("cài vnstock thất bại")
        _VNSTOCK["mod"] = _vn
    vn = _VNSTOCK["mod"]
    loi = None
    for nguon in ("VCI", "TCBS"):
        try:
            if hasattr(vn, "Vnstock"):                                    # vnstock ≥ 3
                df = vn.Vnstock().stock(symbol=symbol, source=nguon).quote.history(
                    start=start, end=end, interval=interval)
            else:                                                         # vnstock 0.x (cũ)
                df = vn.stock_historical_data(symbol, start, end, "1D" if interval == "1D" else "1H")
            if df is not None and len(df):
                df = df.rename(columns=lambda c_: str(c_).lower()).rename(columns={"tradingdate": "time"})
                return df[["time", "open", "high", "low", "close", "volume"]]
        except Exception as e:
            loi = e
    raise ValueError(f"vnstock lỗi: {str(loi)[:60]}")


def cac_nguon_ngay(symbol, start, end):
    return [("vnstock", lambda: tu_vnstock(symbol, start, end, "1D")),
            ("VNDirect", lambda: tu_vndirect(symbol, start, end, "D")),
            ("VND finfo", lambda: tu_vnd_finfo(symbol, start, end)),
            ("TCBS", lambda: tu_tcbs_ngay(symbol, start, end)),
            ("SSI", lambda: tu_ssi(symbol, start, end, "1D")),
            ("CafeF", lambda: tu_cafef(symbol, start, end)),
            ("DNSE", lambda: tu_dnse(symbol, start, end, "1D")),
            ("VCI", lambda: tu_vci(symbol, start, end, "ONE_DAY"))]


def cac_nguon_gio(symbol, start, end):
    return [("vnstock", lambda: tu_vnstock(symbol, start, end, "1H")),
            ("VNDirect", lambda: tu_vndirect(symbol, start, end, "60")),
            ("TCBS", lambda: tu_tcbs_gio(symbol)),
            ("SSI", lambda: tu_ssi(symbol, start, end, "60")),
            ("DNSE", lambda: tu_dnse(symbol, start, end, "1H")),
            ("VCI", lambda: tu_vci(symbol, start, end, "ONE_HOUR"))]


# Nhật ký nguồn đã dùng → in mục "NGUỒN DỮ LIỆU" & sheet Excel "Nguon du lieu"
NHAT_KY_NGUON = []


NGUON_DA_DUNG = {}


CANH_BAO_DU_LIEU = []        # [MỚI] cảnh báo chất lượng dữ liệu → in ở tóm tắt & mục kiểm tra dữ liệu


def ghi_nguon(du_lieu, nguon, chi_tiet=""):
    NHAT_KY_NGUON.append({"Dữ liệu": du_lieu, "Nguồn": nguon, "Địa chỉ": DIA_CHI_NGUON.get(nguon, ""),
                          "Chi tiết": chi_tiet, "Thời điểm lấy": datetime.now().strftime("%d/%m/%Y %H:%M")})


def doi_chieu_nguon(symbol, df, nguon_chinh, so_phien=40):
    """Kiểm tra chéo giá đóng cửa với các nguồn khác trong ~so_phien phiên gần nhất."""
    end = str(date.today())
    start = str((df.index[-1] - pd.Timedelta(days=int(so_phien * 1.6))).date())
    rows = []
    for ten, ham in cac_nguon_ngay(symbol, start, end):
        if ten == nguon_chinh:
            continue
        try:
            khac = chuan_hoa(ham())
        except Exception as e:
            rows.append([ten, 0, np.nan, np.nan, f"không lấy được ({str(e)[:40]})"])
            continue
        ghep = pd.concat([df.close, khac.close], axis=1, join="inner").dropna().tail(so_phien)
        if ghep.empty:
            rows.append([ten, 0, np.nan, np.nan, "không có phiên trùng"])
            continue
        lech = (ghep.iloc[:, 1] / ghep.iloc[:, 0] - 1).abs() * 100
        danh_gia = "✔ khớp" if lech.max() <= 0.5 else (
            "◐ lệch nhẹ" if lech.max() <= 2 else "⚠ lệch lớn – kiểm tra điều chỉnh cổ tức/chia tách hoặc đơn vị giá")
        rows.append([ten, len(ghep), lech.mean(), lech.max(), danh_gia])
    return pd.DataFrame(rows, columns=["Nguồn đối chiếu", "Số phiên trùng", "Lệch TB %", "Lệch tối đa %", "Đánh giá"])


def tu_csv(path):
    """Đọc CSV (cột tiếng Anh hoặc tiếng Việt, ngày dạng ISO hoặc dd/mm/yyyy, có thể kèm giờ)."""
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={
        "ngày": "time", "date": "time", "datetime": "time", "giá mở cửa": "open",
        "giá cao nhất": "high", "giá thấp nhất": "low", "giá đóng cửa": "close",
        "khối lượng": "volume", "price": "close", "vol.": "volume"})
    t = df["time"].astype(str).str.strip()
    if t.str.match(r"^\d{4}-").all():
        df["time"] = pd.to_datetime(t)
    else:
        try:
            df["time"] = pd.to_datetime(t, dayfirst=True, format="mixed")
        except (TypeError, ValueError):
            df["time"] = pd.to_datetime(t, dayfirst=True)
    for c in ("open", "high", "low", "close", "volume"):
        if c in df and not pd.api.types.is_numeric_dtype(df[c]):   # pandas 3: chuỗi có dtype "str", không phải object
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    for c in ("open", "high", "low"):
        if c not in df:
            df[c] = df["close"]
    if "volume" not in df:
        df["volume"] = 0
    return df


def chuan_hoa(df, la_chi_so=False):
    """
    Chuẩn hoá: sắp xếp, bỏ trùng/rỗng, sửa high/low không hợp lệ.
    [MỚI] Tự nhận đơn vị: giá cổ phiếu theo ĐỒNG (trung vị > 1000) → đổi sang NGHÌN ĐỒNG.
    """
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
    if not la_chi_so and len(df) and df.close.median() > 1000:
        for c in ("open", "high", "low", "close"):
            df[c] = df[c] / 1000
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _file_cache(khoa):
    os.makedirs(THU_MUC_CACHE, exist_ok=True)
    return os.path.join(THU_MUC_CACHE, re.sub(r"[^\w\-]", "_", khoa) + ".csv")


def _luu_cache(df, khoa):
    try:
        df.to_csv(_file_cache(khoa))
    except Exception:
        pass


def _doc_cache(khoa):
    f = _file_cache(khoa)
    if not os.path.exists(f):
        return None
    try:
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        return df[["open", "high", "low", "close", "volume"]].astype(float)
    except Exception:
        return None


def thu_cac_nguon(ten, cac_nguon, khoa_cache=None, la_chi_so=False, im_lang=False):
    """
    Thử lần lượt từng nguồn dữ liệu, nguồn nào được thì dùng; ghi lại nguồn đã dùng & nguồn lỗi.
    [MỚI] Lấy được → lưu cache cục bộ; mọi nguồn lỗi → dùng cache (kèm cảnh báo ngày dữ liệu).
    """
    da_thu = []
    out = (lambda *a, **k: None) if im_lang else in_ra
    for ten_nguon, ham in cac_nguon:
        try:
            out(f"  Lấy dữ liệu {ten} từ {ten_nguon} ...", end=" ")
            df = chuan_hoa(ham(), la_chi_so)
            if df.empty:
                raise ValueError("rỗng")
            out(f"OK ({len(df)} nến)")
            NGUON_DA_DUNG[ten] = ten_nguon
            ghi_nguon(ten, ten_nguon, f"{len(df)} nến, {df.index[0]:%d/%m/%Y} → {df.index[-1]:%d/%m/%Y}"
                      + (f" | đã thử lỗi: {', '.join(da_thu)}" if da_thu else ""))
            if khoa_cache:
                _luu_cache(df, khoa_cache)
            return df
        except Exception as e:
            out(f"lỗi ({str(e)[:70]})")
            da_thu.append(f"{ten_nguon} ({str(e)[:30]})")
    if khoa_cache:
        df = _doc_cache(khoa_cache)
        if df is not None and len(df):
            msg = (f"Mọi nguồn {ten} đều lỗi → dùng CACHE cục bộ, dữ liệu đến {df.index[-1]:%d/%m/%Y} "
                   f"(có thể đã cũ)")
            in_ra(f"  ⚠ {msg}")
            CANH_BAO_DU_LIEU.append(msg)
            NGUON_DA_DUNG[ten] = "Cache"
            ghi_nguon(ten, "Cache", f"{len(df)} nến đến {df.index[-1]:%d/%m/%Y} | lỗi: {', '.join(da_thu)}")
            return df
    ghi_nguon(ten, "—", f"không lấy được từ: {', '.join(da_thu)}")
    return None


def gop_tuan(df_ngay):
    """Gộp nến ngày thành nến tuần (tuần kết thúc thứ Sáu). High tuần = max(high ngày) → nhất quán giữa khung."""
    w = df_ngay.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min",
                                       "close": "last", "volume": "sum"}).dropna()
    return w


def tai_vnindex(start, csv=None):
    """Dữ liệu VNINDEX ngày – dùng để tính Beta, so sánh hiệu suất & bối cảnh thị trường."""
    if csv:
        ghi_nguon("VNINDEX", "CSV", csv)
        return chuan_hoa(tu_csv(csv), la_chi_so=True)
    end = str(date.today())
    return thu_cac_nguon("VNINDEX", [
        ("vnstock", lambda: tu_vnstock("VNINDEX", start, end, "1D")),
        ("VNDirect", lambda: tu_vndirect("VNINDEX", start, end, "D")),
        ("TCBS", lambda: tu_tcbs_ngay("VNINDEX", start, end, loai="index")),
        ("SSI", lambda: tu_ssi("VNINDEX", start, end, "1D")),
        ("CafeF", lambda: tu_cafef("VNINDEX", start, end)),
        ("DNSE", lambda: tu_dnse("VNINDEX", start, end, "1D", "index")),
        ("VCI", lambda: tu_vci("VNINDEX", start, end, "ONE_DAY", la_chi_so=True))],
        khoa_cache="VNINDEX_ngay", la_chi_so=True)


def lay_thong_tin_dn(symbol):
    """Thử lấy số CP lưu hành, tỷ lệ sở hữu NN, sàn, ngành từ TCBS (có kiểm tra phản hồi trước khi đọc JSON)."""
    kq = {}
    try:
        j = _goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{symbol}/overview",
                     headers={"Origin": "https://tcinvest.tcbs.com.vn"})
        cp = j.get("outstandingShare")
        if cp:
            kq["so_cp"] = cp * 1e6 if cp < 1e5 else cp           # API thường trả theo triệu CP
        nn = j.get("foreignPercent")
        if nn is not None:
            kq["so_huu_nn"] = nn * 100 if nn <= 1 else nn       # có thể là tỷ lệ 0–1
        if j.get("exchange"):
            kq["san"] = j["exchange"]
        if j.get("industry"):
            kq["nganh"] = j["industry"]
        in_ra(f"  Lấy thông tin doanh nghiệp từ TCBS ... OK")
        ghi_nguon("Thông tin DN (số CP lưu hành, sở hữu NN, sàn, ngành)", "TCBS",
                  ", ".join(k for k in kq) or "không có trường nào")
    except Exception as e:
        in_ra(f"  Lấy thông tin doanh nghiệp từ TCBS ... lỗi ({str(e)[:70]})")
        ghi_nguon("Thông tin DN", "—", f"TCBS lỗi: {str(e)[:60]}")
    if "so_cp" not in kq:
        try:      # [MỚI] dự phòng: VNDirect finfo
            j = _goi_api("https://finfo-api.vndirect.com.vn/v4/stocks", params={"q": f"code:{symbol}"}, so_lan=1)
            d = (j.get("data") or [{}])[0]
            if d.get("floor"):
                kq.setdefault("san", d["floor"])
            if d.get("listedShare"):
                kq["so_cp"] = float(d["listedShare"])
            ghi_nguon("Thông tin DN (sàn, KL niêm yết)", "VND finfo", ", ".join(kq) or "—")
        except Exception:
            pass
    return kq


def lay_chi_so_co_ban(symbol):
    """[MỚI] P/E, P/B, ROE quý gần nhất từ TCBS (best-effort, có thể lỗi bất cứ lúc nào)."""
    try:
        j = _goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/financialratio",
                     params={"yearly": 0, "isAll": "false"}, so_lan=1,
                     headers={"Origin": "https://tcinvest.tcbs.com.vn"})
        rows = j if isinstance(j, list) else (j.get("data") or [])
        if not rows:
            return {}
        r = rows[0]
        roe = r.get("roe")
        kq = {"P/E": r.get("priceToEarning"), "P/B": r.get("priceToBook"),
              "ROE %": roe * 100 if roe is not None and abs(roe) < 2 else roe,
              "ky": f"Q{r.get('quarter')}/{r.get('year')}"}
        ghi_nguon("Chỉ số cơ bản (P/E, P/B, ROE)", "TCBS", kq["ky"])
        return {k: v for k, v in kq.items() if v is not None}
    except Exception as e:
        ghi_nguon("Chỉ số cơ bản", "—", f"TCBS lỗi: {str(e)[:60]}")
        return {}


def _so(x):
    """'414.064.000' / '414,064,000' / 414064000 → 414064000.0 (bỏ mọi ký tự không phải số)."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if x == x and x > 0 else None
    d = re.sub(r"[^\d]", "", str(x))
    return float(d) if d else None


def lay_cp_vietstock(symbol):
    """
    Lấy KL CP NIÊM YẾT, KL CP LƯU HÀNH và VỐN ĐIỀU LỆ từ Vietstock (finance.vietstock.vn).
      (1) API nội bộ /company/tradinginfo (cần cookie + __RequestVerificationToken của trang)
      (2) Dự phòng: đọc thẳng nhãn 'KL CP niêm yết' / 'KL CP lưu hành' / 'Vốn điều lệ' trên trang HTML
    Vietstock không có API công khai chính thức → có thể lỗi bất cứ lúc nào; khi lỗi hãy nhập tay.
    """
    kq, cach = {}, []
    ss = requests.Session()
    ss.headers.update({**HEADERS, "Referer": "https://finance.vietstock.vn/"})
    trang = ""
    for url in (f"https://finance.vietstock.vn/{symbol}/ho-so-doanh-nghiep.htm",
                f"https://finance.vietstock.vn/{symbol}.htm"):
        for _k in range(2):                       # [MỚI] thử lại 1 lần
            try:
                r = ss.get(url, timeout=THOI_GIAN_CHO)
                if r.ok and symbol.upper() in r.text.upper():
                    trang += _html.unescape(r.text)
                    break
            except Exception:
                pass
            time.sleep(1)
    if not trang:
        in_ra("  Lấy số CP từ Vietstock ... lỗi (không tải được trang)")
        ghi_nguon("Số CP (Vietstock)", "—", "không tải được trang Vietstock")
        return kq

    # (1) API tradinginfo
    tk = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', trang)
    if tk:
        try:
            rr = ss.post("https://finance.vietstock.vn/company/tradinginfo",
                         data={"code": symbol, "s": "0", "t": "", "__RequestVerificationToken": tk.group(1)},
                         timeout=THOI_GIAN_CHO)
            if rr.status_code != 200 or rr.text.strip()[:1] not in "{[":     # [MỚI] kiểm tra trước khi .json()
                raise ValueError(f"tradinginfo HTTP {rr.status_code} / không phải JSON")
            j = rr.json()
            j = j[0] if isinstance(j, list) and j else j
            thap = {str(k).lower(): v for k, v in (j or {}).items()}
            for khoa, ten in (("klcpny", "niem_yet"), ("klcplh", "luu_hanh")):
                if _so(thap.get(khoa)):
                    kq[ten] = _so(thap[khoa])
            if kq:
                cach.append("API tradinginfo")
        except Exception:
            pass

    # (2) Đọc nhãn trên trang
    chu = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", trang))
    mau = {"niem_yet": r"KL\s*CP\s*(?:đang\s*)?niêm\s*yết",
           "luu_hanh": r"KL\s*CP\s*(?:đang\s*)?lưu\s*hành",
           "von_dieu_le": r"Vốn\s*điều\s*lệ"}
    for ten, m in mau.items():
        if ten in kq:
            continue
        f = re.search(m + r"[^\d]{0,40}([\d][\d.,]{4,})", chu, re.I)
        if f and _so(f.group(1)):
            kq[ten] = _so(f.group(1))
            cach.append(f"nhãn '{ten}'")
    # Vốn điều lệ phải tính bằng đồng (≥ 1 tỷ) mới suy ra được số CP; loại các giá trị ghi theo tỷ/triệu
    if kq.get("von_dieu_le") and kq["von_dieu_le"] < 1e9:
        kq.pop("von_dieu_le")
    for k in ("niem_yet", "luu_hanh"):
        if kq.get(k) and kq[k] < 1e5:          # quá nhỏ → có thể là đơn vị triệu CP hoặc đọc nhầm
            kq.pop(k)
    in_ra(f"  Lấy số CP từ Vietstock ... {'OK' if kq else 'không đọc được số liệu'}")
    ghi_nguon("Số CP (Vietstock: niêm yết, lưu hành, VĐL)", "Vietstock" if kq else "—",
              (", ".join(f"{k}={so_vn(v)}" for k, v in kq.items()) + f" [{', '.join(cach)}]") if kq
              else "trang tải được nhưng không tìm thấy số liệu")
    return kq


# ==========================================================================
# 10E. [MỚI] PHẦN G – BỐI CẢNH THỊ TRƯỜNG: VN-INDEX, SỨC MẠNH TƯƠNG ĐỐI, NHÓM NGÀNH
# ==========================================================================
def tai_nhom_nganh(ds_ma, start):
    """Tải giá ngày các mã cùng ngành (thử nhanh 1 lần/nguồn, nhớ trong phiên, dùng cache khi lỗi)."""
    cu, cfg.SO_LAN_THU = cfg.SO_LAN_THU, 1
    kq = {}
    try:
        for ma in ds_ma:
            in_ra(f"  Tải {ma} ...", end=" ")
            df = _tai_ngay(ma, start, f"Nhóm ngành {ma}", im_lang=True)
            in_ra("OK" if df is not None else "lỗi")
            if df is not None and len(df) > 60:
                kq[ma] = df
    finally:
        cfg.SO_LAN_THU = cu
    return kq


_BO_NHO = {}                 # [MỚI] nhớ dữ liệu giá đã tải trong phiên Colab (dùng lại khi quét nhiều mã)


def _tai_ngay(ma, start, ten, im_lang=False):
    """[MỚI] Tải giá ngày có nhớ trong phiên (quét nhiều mã / nhóm ngành không tải lại)."""
    k = (ma, start)
    if k in _BO_NHO:
        df, nguon = _BO_NHO[k]
        NGUON_DA_DUNG[ten] = nguon
        ghi_nguon(ten, nguon, f"dùng lại dữ liệu đã tải trong phiên ({len(df)} nến)")
        return df.copy()
    df = thu_cac_nguon(ten, cac_nguon_ngay(ma, start, str(date.today())), khoa_cache=f"{ma}_ngay",
                       im_lang=im_lang)
    if df is not None:
        _BO_NHO[k] = (df, NGUON_DA_DUNG.get(ten, "?"))
    return df
