# -*- coding: utf-8 -*-
"""Lấy dữ liệu GIÁ (ngày/giờ/VN-Index/nhóm ngành): API công khai, CSV, cache, nhớ trong phiên.
Thông tin doanh nghiệp & chỉ số cơ bản: du_lieu_co_ban.py (vẫn import được từ đây)."""
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


# VNDirect finfo: host đúng hiện nay là api-finfo (KHÔNG phải finfo-api) – giữ host cũ làm dự phòng
VND_FINFO_HOST = ("https://api-finfo.vndirect.com.vn", "https://finfo-api.vndirect.com.vn")


def _goi_finfo(duong_dan, params, so_lan=None):
    loi = None
    for host in VND_FINFO_HOST:
        try:
            return _goi_api(host + duong_dan, params=params, so_lan=so_lan)
        except ValueError as e:
            loi = e
    raise ValueError(str(loi)[:120])


def tu_vnd_finfo(symbol, start, end):
    """[MỚI] VNDirect finfo – giá ngày ĐÃ ĐIỀU CHỈNH (adOpen/adHigh/adLow/adClose)."""
    p = {"sort": "date", "q": f"code:{symbol}~date:gte:{start}~date:lte:{end}", "size": 9999, "page": 1}
    d = (_goi_finfo("/v4/stock_prices", p) or {}).get("data") or []
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
    "VNDirect": "dchart-api.vndirect.com.vn",
    "VND finfo": "api-finfo.vndirect.com.vn",
    "vnstock": "thư viện vnstock bản Cộng đồng (vnstocks.com) – KBS/VCI",
    "Yahoo": "query1.finance.yahoo.com / yfinance",
    "TCBS": "apipubaws.tcbs.com.vn",
    "SSI": "iboard-api.ssi.com.vn",
    "CafeF": "s.cafef.vn",
    "DNSE": "services.entrade.com.vn",
    "VCI": "trading.vietcap.com.vn",
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


def cac_nguon_ngay(symbol, start, end):
    return [("VNDirect", lambda: tu_vndirect(symbol, start, end, "D")),
            ("VND finfo", lambda: tu_vnd_finfo(symbol, start, end)),
            ("TCBS", lambda: tu_tcbs_ngay(symbol, start, end)),
            ("SSI", lambda: tu_ssi(symbol, start, end, "1D")),
            ("CafeF", lambda: tu_cafef(symbol, start, end)),
            ("DNSE", lambda: tu_dnse(symbol, start, end, "1D")),
            ("VCI", lambda: tu_vci(symbol, start, end, "ONE_DAY")),
            ("vnstock", lambda: tu_vnstock(symbol, start, end))]


def tu_vnstock(symbol, start, end):
    """Thư viện vnstock bản Cộng đồng (nguồn KBS → VCI bên trong; có giới hạn lượt gọi/phút)."""
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt (cfg.DUNG_VNSTOCK = False)")
    from . import vnstock_nguon
    return vnstock_nguon.gia(symbol, start, end)


def chuan_bi_vnstock():
    """Gọi đầu mỗi lần chạy: Colab → tự cài vnstock nếu thiếu; đặt chế độ chờ khi hết lượt theo cfg.CHO_VNSTOCK."""
    if not cfg.DUNG_VNSTOCK:
        return False
    from . import vnstock_nguon
    vnstock_nguon.CHO_KHI_HET_LUOT = bool(cfg.CHO_VNSTOCK)
    return vnstock_nguon.dam_bao_cai()


def cac_nguon_gio(symbol, start, end):
    return [("VNDirect", lambda: tu_vndirect(symbol, start, end, "60")),
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
        except (Exception, SystemExit) as e:         # vnstock hết lượt gọi SystemExit
            rows.append([ten, 0, np.nan, np.nan, f"không lấy được ({str(e)[:40]})"])
            continue
        ghep = pd.concat([df.close, khac.close], axis=1, join="inner").dropna().tail(so_phien)
        if ghep.empty:
            rows.append([ten, 0, np.nan, np.nan, "không có phiên trùng"])
            continue
        ty_le = ghep.iloc[:, 1] / ghep.iloc[:, 0]
        lech = (ty_le - 1).abs() * 100
        if lech.max() <= 0.5:
            danh_gia = "✔ khớp"
        elif ty_le.std() * 100 < 0.05 and len(ghep) >= 5:
            danh_gia = (f"◐ lệch KHÔNG ĐỔI {(ty_le.mean() - 1) * 100:+.2f}% mọi phiên → nguồn này dùng cách ĐIỀU CHỈNH "
                        f"giá khác (cổ tức/chia tách) – không phải sai ngày/đơn vị; báo cáo dùng {nguon_chinh}")
        elif lech.max() <= 2:
            danh_gia = "◐ lệch nhẹ"
        else:
            danh_gia = "⚠ lệch lớn – kiểm tra điều chỉnh cổ tức/chia tách hoặc đơn vị giá"
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
        except (Exception, SystemExit) as e:          # thư viện ngoài (vnstock) có thể gọi SystemExit khi hết lượt
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
        ("VNDirect", lambda: tu_vndirect("VNINDEX", start, end, "D")),
        ("TCBS", lambda: tu_tcbs_ngay("VNINDEX", start, end, loai="index")),
        ("SSI", lambda: tu_ssi("VNINDEX", start, end, "1D")),
        ("CafeF", lambda: tu_cafef("VNINDEX", start, end)),
        ("DNSE", lambda: tu_dnse("VNINDEX", start, end, "1D", "index")),
        ("VCI", lambda: tu_vci("VNINDEX", start, end, "ONE_DAY", la_chi_so=True)),
        ("vnstock", lambda: tu_vnstock("VNINDEX", start, end))],
        khoa_cache="VNINDEX_ngay", la_chi_so=True)


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


# Giữ tương thích: phần thông tin DN & chỉ số cơ bản nay ở du_lieu_co_ban.py
from .du_lieu_co_ban import (  # noqa: E402
    KHOA_BCTC, NGUON_BCTC_NAM, NGUON_CO_BAN, NGUON_LNST, lay_bctc_nam, lay_chi_so_co_ban, lay_lnst_4_quy,
    lay_thong_tin_dn,
)
