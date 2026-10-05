# -*- coding: utf-8 -*-
"""Lấy dữ liệu giá / thông tin doanh nghiệp / chỉ số cơ bản: API công khai, CSV, cache, nhớ trong phiên."""
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


def _tim_so(d, *khoa):
    for k in khoa:
        v = d.get(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return None


def lay_thong_tin_dn(symbol):
    """
    Thông tin DN & SỐ CỔ PHIẾU từ NHIỀU nguồn (không dùng Vietstock) để đối chiếu chéo:
      • TCBS overview  : CP lưu hành, sở hữu NN, sàn, ngành
      • VNDirect finfo : KL niêm yết, sàn
      • Yahoo (yfinance): CP lưu hành, vốn hoá (dùng kiểm tra chéo vốn hoá tự tính)
    Trả về: san, nganh, so_huu_nn, so_cp (lưu hành – nguồn ưu tiên), ung_vien_cp = {"luu_hanh": {nguồn: số},
    "niem_yet": {nguồn: số}}, von_hoa_yahoo (tỷ đồng).
    """
    kq = {"ung_vien_cp": {"luu_hanh": {}, "niem_yet": {}}}
    uv = kq["ung_vien_cp"]
    # 1. TCBS
    try:
        j = _goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{symbol}/overview",
                     headers={"Origin": "https://tcinvest.tcbs.com.vn"}, so_lan=1)
        cp = _tim_so(j, "outstandingShare")
        if cp:
            uv["luu_hanh"]["TCBS"] = cp * 1e6 if cp < 1e5 else cp           # API thường trả theo triệu CP
        ph = _tim_so(j, "issueShare")
        if ph:
            uv.setdefault("phat_hanh", {})["TCBS"] = ph * 1e6 if ph < 1e5 else ph
        nn = j.get("foreignPercent")
        if nn is not None:
            kq["so_huu_nn"] = nn * 100 if nn <= 1 else nn
        if j.get("exchange"):
            kq["san"] = j["exchange"]
        if j.get("industry"):
            kq["nganh"] = j["industry"]
        ghi_nguon("Thông tin DN (CP lưu hành, sở hữu NN, sàn, ngành)", "TCBS", "OK")
    except Exception as e:
        ghi_nguon("Thông tin DN", "—", f"TCBS lỗi: {str(e)[:60]}")
    # 2. VNDirect finfo
    try:
        j = _goi_finfo("/v4/stocks", {"q": f"code:{symbol}"}, so_lan=1)
        d = next((x for x in (j.get("data") or []) if str(x.get("code", "")).upper() == symbol), {})
        if d.get("floor"):
            kq.setdefault("san", d["floor"])
        ny = _tim_so(d, "listedShare", "listedQuantity", "listedVolume")
        if ny:
            uv["niem_yet"]["VNDirect"] = ny
        lh = _tim_so(d, "outstandingShare", "outstandingShares")
        if lh:
            uv["luu_hanh"]["VNDirect"] = lh
        ghi_nguon("Thông tin DN (sàn, KL niêm yết)", "VND finfo", "OK" if (ny or lh) else "không có trường số CP")
    except Exception as e:
        ghi_nguon("Thông tin DN", "—", f"VND finfo lỗi: {str(e)[:60]}")
    # 3. vnstock (KBS/VCI) – số CP lưu hành trong bảng chỉ số
    if cfg.DUNG_VNSTOCK:
        try:
            from . import vnstock_nguon
            d = vnstock_nguon.co_ban(symbol)
            _VNSTOCK_CB[symbol] = d                       # dùng lại cho chỉ số cơ bản → đỡ tốn lượt gọi
            if d.get("so_cp"):
                uv["luu_hanh"]["vnstock"] = d["so_cp"]
            ghi_nguon("Thông tin DN (CP lưu hành)", "vnstock", "OK" if d.get("so_cp") else "không có số CP")
        except (Exception, SystemExit) as e:
            ghi_nguon("Thông tin DN", "—", f"vnstock lỗi: {str(e)[:60]}")
    # 4. Yahoo
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.VN").info or {}
        cp = _tim_so(info, "sharesOutstanding", "impliedSharesOutstanding")
        if cp:
            uv["luu_hanh"]["Yahoo"] = cp
        if _tim_so(info, "marketCap") and info.get("currency") in (None, "VND"):
            kq["von_hoa_yahoo"] = info["marketCap"] / 1e9
        ghi_nguon("Thông tin DN (CP lưu hành, vốn hoá)", "Yahoo", "OK" if cp else "không có số CP")
    except Exception as e:
        ghi_nguon("Thông tin DN", "—", f"Yahoo lỗi: {str(e)[:60]}")
    for ten in cfg.THU_TU_NGUON_SO_CP:                    # nguồn ưu tiên cho CP lưu hành
        if ten in uv["luu_hanh"]:
            kq["so_cp"], kq["nguon_so_cp"] = uv["luu_hanh"][ten], ten
            break
    tom = ", ".join(f"{n} {so_vn(v)}" for n, v in uv["luu_hanh"].items()) or "không nguồn nào có"
    in_ra(f"  Số CP lưu hành theo các nguồn: {tom}")
    return kq


# --------------------------------------------------------------------------
# CHỈ SỐ CƠ BẢN: VNDirect (api-finfo) → TCBS → Yahoo. P/E TÍNH LẠI = giá hiện tại ÷ EPS 4 quý gần nhất.
# VNDirect /v4/ratios: tham số q + sort=reportDate:desc, MỖI chỉ số gọi riêng 1 lần (gộp nhiều mã → bị trộn).
# --------------------------------------------------------------------------
_MA_VND = {"PRICE_TO_EARNINGS": "P/E", "PRICE_TO_BOOK": "P/B", "EPS_TR": "EPS 4Q", "ROAE_TR_AVG5Q": "ROE %"}


def _ty_le(v):
    return v * 100 if v is not None and abs(v) < 2 else v


def _co_ban_vndirect(symbol):
    kq, ky = {}, ""
    for ma_cs, khoa in _MA_VND.items():
        try:
            j = _goi_finfo("/v4/ratios", {"q": f"code:{symbol}~ratioCode:{ma_cs}", "sort": "reportDate:desc",
                                          "size": 1}, so_lan=1)
            d = (j.get("data") or [None])[0]
            if d and str(d.get("ratioCode", ma_cs)) == ma_cs and str(d.get("code", symbol)).upper() == symbol:
                v = d.get("value")
                if v is not None:
                    kq[khoa] = float(v)
                    if khoa == "EPS 4Q" and d.get("reportDate"):
                        ky = str(d["reportDate"])[:10]
        except Exception:
            continue
    if "ROE %" in kq:
        kq["ROE %"] = _ty_le(kq["ROE %"])
    if kq:
        kq["ky"] = f"EPS kỳ {ky}" if ky else "mới nhất"
    return kq


def _co_ban_tcbs(symbol):
    j = _goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/financialratio",
                 params={"yearly": 0, "isAll": "false"}, so_lan=1,
                 headers={"Origin": "https://tcinvest.tcbs.com.vn"})
    rows = j if isinstance(j, list) else (j.get("data") or [])
    if not rows:
        return {}
    r = rows[0]
    kq = {"P/E": r.get("priceToEarning"), "P/B": r.get("priceToBook"), "ROE %": _ty_le(r.get("roe")),
          "EPS 4Q": r.get("earningPerShare"), "ky": f"Q{r.get('quarter')}/{r.get('year')}"}
    return {k: v for k, v in kq.items() if v is not None}


def _co_ban_yahoo(symbol):
    try:
        import yfinance as yf
    except ImportError:
        raise ValueError("chưa cài yfinance")
    info = yf.Ticker(f"{symbol}.VN").info or {}
    kq = {"P/E": info.get("trailingPE"), "P/B": info.get("priceToBook"),
          "ROE %": _ty_le(info.get("returnOnEquity")),
          "EPS 4Q": info.get("trailingEps") if info.get("financialCurrency") in (None, "VND") else None,
          "ky": "TTM"}
    return {k: v for k, v in kq.items() if v is not None}


_VNSTOCK_CB = {}             # kết quả vnstock đã lấy trong phiên (dùng chung giữa các bước)


def _co_ban_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    d = _VNSTOCK_CB.get(symbol) or vnstock_nguon.co_ban(symbol)
    _VNSTOCK_CB[symbol] = d
    kq = {"P/E": d.get("pe"), "P/B": d.get("pb"), "ROE %": d.get("roe"), "EPS 4Q": d.get("eps_ttm"),
          "ky": d.get("ky_lnst", "mới nhất")}
    return {k: v for k, v in kq.items() if v is not None}


NGUON_CO_BAN = [("VNDirect", _co_ban_vndirect), ("vnstock", _co_ban_vnstock), ("TCBS", _co_ban_tcbs),
                ("Yahoo", _co_ban_yahoo)]


# --------------------------------------------------------------------------
# LNST 4 QUÝ GẦN NHẤT (tỷ đồng) – để tự tính EPS = LNST 4 quý ÷ số CP lưu hành
# Ưu tiên LNST thuộc cổ đông công ty mẹ (đúng cách tính EPS theo VAS); không có thì LNST hợp nhất.
# --------------------------------------------------------------------------
def _lnst_tcbs(symbol):
    j = _goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/incomestatement",
                 params={"yearly": 0, "isAll": "true"}, so_lan=1, headers={"Origin": "https://tcinvest.tcbs.com.vn"})
    rows = j if isinstance(j, list) else (j.get("data") or [])
    rows = sorted([r for r in rows if r.get("year") and r.get("quarter")],
                  key=lambda r: (r["year"], r["quarter"]), reverse=True)[:4]
    ds = []
    for r in rows:
        v = r.get("shareHolderIncome", r.get("postTaxProfit"))
        if v is None:
            return None
        ds.append((f"Q{r['quarter']}/{r['year']}", float(v)))           # TCBS: tỷ đồng
    return ds


def _lnst_yahoo(symbol):
    import yfinance as yf
    t = yf.Ticker(f"{symbol}.VN")
    if (t.info or {}).get("financialCurrency") not in (None, "VND"):
        raise ValueError("đơn vị tiền không phải VND")
    df = t.quarterly_income_stmt
    hang = next((h for h in ("Net Income Common Stockholders", "Net Income",
                             "Net Income From Continuing Operation Net Minority Interest") if h in df.index), None)
    if hang is None:
        return None
    s = df.loc[hang].dropna().sort_index(ascending=False)[:4]
    return [(f"Q{(c.month - 1) // 3 + 1}/{c.year}", float(v) / 1e9) for c, v in s.items()]   # đồng → tỷ


def _lnst_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    d = _VNSTOCK_CB.get(symbol, {})
    return vnstock_nguon.lnst_quy(symbol, d.get("so_cp"), d.get("eps_ttm"))


NGUON_LNST = [("TCBS", _lnst_tcbs), ("vnstock", _lnst_vnstock), ("Yahoo", _lnst_yahoo)]


def _bon_quy_lien_tiep(ds):
    """Đúng 4 quý liên tiếp, mới nhất trước (Q2/2026, Q1/2026, Q4/2025, Q3/2025)."""
    if not ds or len(ds) < 4:
        return False
    so = [int(k.split("/")[1]) * 4 + int(k[1]) for k, _ in ds[:4]]
    return all(a - b == 1 for a, b in zip(so, so[1:]))


def lay_lnst_4_quy(symbol):
    """→ (tổng LNST 4 quý tỷ đồng, [(kỳ, LNST)], nguồn) hoặc (None, [], lý do)."""
    loi = []
    for ten, ham in NGUON_LNST:
        try:
            ds = ham(symbol)
            if _bon_quy_lien_tiep(ds):
                return sum(v for _, v in ds[:4]), ds[:4], ten
            loi.append(f"{ten}: không đủ 4 quý liên tiếp")
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    return None, [], "; ".join(loi)


# --------------------------------------------------------------------------
# BCTC THEO NĂM (≥ 3–4 năm) – cho bộ 10 tiêu chí phân tích tài chính kiểu FiinGroup (Phần J5)
# Nguồn: TCBS → vnstock → Yahoo. Chuẩn hoá: list MỚI NHẤT TRƯỚC (None = thiếu).
# --------------------------------------------------------------------------
KHOA_BCTC = ("doanh_thu", "ln_gop", "lnst", "cfo", "cr", "icr", "de", "roe", "von_gop", "vay_no")


def _bctc_tcbs(symbol):
    goc = "https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance"
    bang = {}
    for ten in ("financialratio", "incomestatement", "cashflow", "balancesheet"):
        try:
            j = _goi_api(f"{goc}/{symbol}/{ten}", params={"yearly": 1, "isAll": "true"}, so_lan=1,
                         headers={"Origin": "https://tcinvest.tcbs.com.vn"})
            bang[ten] = {int(r["year"]): r for r in (j if isinstance(j, list) else []) if r.get("year")}
        except Exception:
            bang[ten] = {}
    nam = sorted(set().union(*[set(b) for b in bang.values()]), reverse=True)[:5]
    if len(nam) < 3:
        raise ValueError("TCBS: không đủ 3 năm BCTC")
    kq = {"nam": nam, **{k: [None] * len(nam) for k in KHOA_BCTC}}
    for i, y in enumerate(nam):
        r, kd, lc, cd = (bang[t].get(y, {}) for t in ("financialratio", "incomestatement", "cashflow", "balancesheet"))
        kq["doanh_thu"][i], kq["ln_gop"][i] = _so(kd.get("revenue")), _so(kd.get("grossProfit"))
        kq["lnst"][i] = _so(kd.get("shareHolderIncome", kd.get("postTaxProfit")))
        kq["cfo"][i], kq["cr"][i] = _so(lc.get("fromSale")), _so(r.get("currentPayment"))
        kq["icr"][i] = _so(r.get("ebitOnInterest"))
        kq["de"][i] = _so(r.get("payableOnEquity", r.get("debtOnEquity")))
        kq["roe"][i] = _ty_le(_so(r.get("roe")))
        kq["von_gop"][i] = _so(cd.get("capital"))
        vay = [_so(cd.get(k)) for k in ("shortDebt", "longDebt")]
        kq["vay_no"][i] = sum(v for v in vay if v is not None) if any(v is not None for v in vay) else None
    return kq


def _bctc_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    return vnstock_nguon.bctc_nam(symbol)


def _bctc_yahoo(symbol):
    import yfinance as yf
    t = yf.Ticker(f"{symbol}.VN")
    kd, cd, lc = t.income_stmt, t.balance_sheet, t.cashflow
    if kd is None or kd.empty:
        raise ValueError("Yahoo: không có BCTC năm")
    cot = sorted(kd.columns, reverse=True)[:5]
    kq = {"nam": [c.year for c in cot], **{k: [None] * len(cot) for k in KHOA_BCTC}}

    def h(df, *ten):
        return next((df.loc[x] for x in ten if df is not None and x in df.index), None)

    ty = lambda s_, c: (float(s_[c]) / 1e9 if s_ is not None and c in s_.index and s_[c] == s_[c] else None)
    dt, lg, ln = h(kd, "Total Revenue"), h(kd, "Gross Profit"), h(kd, "Net Income Common Stockholders", "Net Income")
    ebit, lv = h(kd, "EBIT"), h(kd, "Interest Expense")
    tsnh, nnh = h(cd, "Current Assets"), h(cd, "Current Liabilities")
    no, vcsh = h(cd, "Total Liabilities Net Minority Interest"), h(cd, "Stockholders Equity")
    vg, vay, cfo = h(cd, "Common Stock", "Capital Stock"), h(cd, "Total Debt"), h(lc, "Operating Cash Flow")
    for i, c in enumerate(cot):
        kq["doanh_thu"][i], kq["ln_gop"][i], kq["lnst"][i] = ty(dt, c), ty(lg, c), ty(ln, c)
        kq["cfo"][i], kq["von_gop"][i], kq["vay_no"][i] = ty(cfo, c), ty(vg, c), ty(vay, c)
        a, b = ty(tsnh, c), ty(nnh, c)
        kq["cr"][i] = a / b if a is not None and b else None
        e, l_ = ty(ebit, c), ty(lv, c)
        kq["icr"][i] = e / abs(l_) if e is not None and l_ else None
        n, v = ty(no, c), ty(vcsh, c)
        kq["de"][i] = n / v if n is not None and v and v > 0 else None
        kq["roe"][i] = kq["lnst"][i] / v * 100 if kq["lnst"][i] is not None and v and v > 0 else None
    return kq


NGUON_BCTC_NAM = [("TCBS", _bctc_tcbs), ("vnstock", _bctc_vnstock), ("Yahoo", _bctc_yahoo)]


def lay_bctc_nam(symbol, im_lang=False):
    """BCTC năm của 1 mã → dict (kèm 'nguon') hoặc None. Lấy nguồn có nhiều ô dữ liệu nhất."""
    tot, diem_tot, loi = None, 0, []
    for ten, ham in NGUON_BCTC_NAM:
        try:
            kq = ham(symbol)
            diem = sum(v is not None for k in KHOA_BCTC for v in kq[k][:4])
            if diem > diem_tot:
                tot, diem_tot = dict(kq, nguon=ten), diem
            if diem >= 30:
                break
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    if not im_lang:
        ghi_nguon(f"BCTC năm {symbol} (10 tiêu chí)", tot["nguon"] if tot else "—",
                  f"{len(tot['nam'])} năm, {diem_tot} ô dữ liệu" if tot else "; ".join(loi)[:120])
    return tot


def lay_chi_so_co_ban(symbol, gia=None, so_cp_luu_hanh=None, lnst_4q=None):
    """
    P/E, P/B, ROE, EPS. P/B & ROE: VNDirect → TCBS → Yahoo (nguồn sau bù chỗ thiếu).
    P/E = Thị giá (gia, nghìn đồng) / EPS, với EPS = LNST 4 quý gần nhất / số CP lưu hành – TỰ TÍNH:
      LNST 4 quý: tham số lnst_4q (tỷ đồng, nhập từ BCTC) → TCBS → Yahoo
      Số CP lưu hành: so_cp_luu_hanh (cơ cấu cổ phiếu của báo cáo: phát hành − CP quỹ)
    Không đủ dữ liệu tự tính → dùng EPS 4 quý của nguồn (VNDirect EPS_TR...), ghi rõ cách tính.
    """
    kq, nguon, loi = {}, [], []
    for ten, ham in NGUON_CO_BAN:
        if all(k in kq for k in ("P/E", "P/B", "ROE %", "EPS 4Q")):
            break
        try:
            d = ham(symbol)
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
            continue
        moi = [k for k in d if k != "ky" and k not in kq]
        if moi:
            for k in moi:
                kq[k] = d[k]
            nguon.append(f"{ten} ({d.get('ky', '')})")
        else:
            loi.append(f"{ten}: không có số liệu")

    # ---- EPS tự tính = LNST 4 quý / CP lưu hành ----
    if lnst_4q is not None:
        tong, ds_quy, nguon_ln = float(lnst_4q), [], "nhập tay (BCTC)"
    elif so_cp_luu_hanh:
        tong, ds_quy, nguon_ln = lay_lnst_4_quy(symbol)
    else:
        tong, ds_quy, nguon_ln = None, [], "thiếu số CP lưu hành"
    if tong is not None and so_cp_luu_hanh:
        kq["EPS 4Q nguồn"] = kq.get("EPS 4Q")
        kq["LNST 4 quý (tỷ đồng)"] = tong
        kq["EPS 4Q"] = tong * 1e9 / so_cp_luu_hanh
        kq["cach_tinh_eps"] = (f"LNST 4 quý {'+'.join(k for k, _ in ds_quy) or ''} = {tong:,.1f} tỷ ({nguon_ln}) "
                               f"÷ {so_cp_luu_hanh:,.0f} CP lưu hành")
        nguon.append(f"LNST {nguon_ln}")
    elif kq.get("EPS 4Q") is not None:
        kq["cach_tinh_eps"] = "EPS 4 quý do nguồn công bố (chưa tự tính được: " + str(nguon_ln)[:60] + ")"

    if not nguon:
        ghi_nguon("Chỉ số cơ bản", "—", "; ".join(loi)[:120])
        return {}
    if gia and kq.get("EPS 4Q"):
        kq["P/E nguồn"] = kq.get("P/E")
        kq["P/E"] = gia * 1000 / kq["EPS 4Q"]          # EPS âm → P/E âm (doanh nghiệp lỗ)
        kq["cach_tinh_pe"] = f"P/E = {gia:,.2f} nghìn ÷ EPS {kq['EPS 4Q']:,.0f} đ"
    kq["nguon"] = " + ".join(nguon)
    kq["ky"] = nguon[0].split("(", 1)[-1].rstrip(")")
    ghi_nguon("Chỉ số cơ bản (P/E, P/B, ROE, EPS)", nguon[0].split(" (")[0],
              kq["nguon"] + (f" | {kq['cach_tinh_eps']}" if kq.get("cach_tinh_eps") else ""))
    return kq


def _so(x):
    """'414.064.000' / '414,064,000' / 414064000 → 414064000.0 (bỏ mọi ký tự không phải số)."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if x == x and x > 0 else None
    d = re.sub(r"[^\d]", "", str(x))
    return float(d) if d else None


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
