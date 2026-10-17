# -*- coding: utf-8 -*-
"""
NGUỒN GIÁ NGÀY – mỗi nguồn là 1 hàm  f(ma, start, end, chi_so) -> DataFrame[time, open, high, low, close, volume]
và được đăng ký trong NGUON_GIA cùng ĐƠN VỊ giá nguồn trả về:
    1000  = nguồn trả nghìn đồng (giữ nguyên) | 1 = trả đồng (chia 1000) | None = tự nhận biết
Thêm nguồn mới: viết 1 hàm theo mẫu, thêm vào NGUON_GIA và tên vào cau_hinh.THU_TU_NGUON_GIA.

LƯU Ý: đây là API công khai/không chính thức của các công ty chứng khoán – có thể đổi hoặc chặn bất kỳ lúc nào.
Vì vậy chương trình luôn thử lần lượt và ghi lại nguồn nào chạy được (sheet "Nguon du lieu" trong Excel).
"""
import os
import threading
import time
from datetime import date

import numpy as np
import pandas as pd

from .. import cau_hinh as ch
from ..tien_ich import doc_so
from .http import CAU_DAO_GIA, NHAT_KY, lay_json, ts

_khoa_nguon = threading.Lock()
NGUON_DA_DUNG = {}           # mã → nguồn giá đã dùng (xuất cột "nguon_gia")


def _df_tu_tohlcv(j, cong_gio=True, ngay=True):
    """Định dạng phổ biến kiểu TradingView: {t:[], o:[], h:[], l:[], c:[], v:[]}."""
    if not j or not j.get("t"):
        raise ValueError("không có dữ liệu")
    t = pd.to_datetime(pd.Series(j["t"]).astype("int64"), unit="s")
    if cong_gio:
        t = t + pd.Timedelta(hours=7)                 # UTC → giờ Việt Nam
    if ngay:
        t = t.dt.normalize()
    return pd.DataFrame({"time": t.values, "open": j["o"], "high": j["h"], "low": j["l"],
                         "close": j["c"], "volume": j["v"]})


# ------------------------------------------------------------------ các nguồn
def tu_vndirect(ma, start, end, chi_so=False):
    j = lay_json("https://dchart-api.vndirect.com.vn/dchart/history",
                 params={"resolution": "D", "symbol": ma, "from": ts(start), "to": ts(end, 86400)})
    return _df_tu_tohlcv(j)


def tu_tcbs(ma, start, end, chi_so=False):
    j = lay_json("https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term",
                 params={"ticker": ma, "type": "index" if chi_so else "stock", "resolution": "D",
                         "from": ts(start), "to": ts(end, 86400)})
    data = j.get("data") or []
    if not data:
        raise ValueError("không có dữ liệu")
    df = pd.DataFrame(data).rename(columns={"tradingDate": "time"})
    df["time"] = pd.to_datetime(df["time"].astype(str).str[:10])
    return df[["time", "open", "high", "low", "close", "volume"]]


def tu_dnse(ma, start, end, chi_so=False):
    loai = "index" if chi_so else "stock"
    j = lay_json(f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{loai}",
                 params={"symbol": ma, "resolution": "1D", "from": ts(start), "to": ts(end, 86400)})
    return _df_tu_tohlcv(j)


def tu_vci(ma, start, end, chi_so=False):
    so_nen = max((pd.Timestamp(end) - pd.Timestamp(start)).days, 5) + 10
    h = {"Content-Type": "application/json", "Referer": "https://trading.vietcap.com.vn/",
         "Origin": "https://trading.vietcap.com.vn"}
    j = lay_json("https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart", headers=h,
                 json_body={"timeFrame": "ONE_DAY", "symbols": [ma], "to": ts(end, 86400), "countBack": so_nen})
    d = j[0] if isinstance(j, list) and j else None
    df = _df_tu_tohlcv(d)
    return df[df.time >= pd.Timestamp(start)]


def tu_ssi(ma, start, end, chi_so=False):
    """SSI iBoard (chưa kiểm chứng ổn định – định dạng có thể nằm trong khoá 'data')."""
    j = lay_json("https://iboard-api.ssi.com.vn/statistics/charts/history",
                 params={"resolution": "1D", "symbol": ma, "from": ts(start), "to": ts(end, 86400)})
    return _df_tu_tohlcv(j.get("data", j) if isinstance(j, dict) else None)


def _ma_yahoo(ma):
    """Mã Yahoo: HOSE '.VN', HNX '.HN' (ptcp.san; ptcp cũ → '.VN')."""
    try:
        from ptcp.san import ma_yahoo
        return ma_yahoo(ma)
    except ImportError:
        return f"{ma}.VN"


def tu_yahoo(ma, start, end, chi_so=False):
    """Yahoo Finance – nguồn quốc tế dự phòng khi các CTCK Việt Nam chặn. Mã HOSE dạng 'GMD.VN', HNX 'SHS.HN'."""
    if chi_so:
        raise ValueError("không hỗ trợ chỉ số")
    j = lay_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{_ma_yahoo(ma)}",
                 params={"period1": ts(start), "period2": ts(end, 86400), "interval": "1d"})
    r = (j.get("chart", {}).get("result") or [None])[0]
    if not r or not r.get("timestamp"):
        raise ValueError("không có dữ liệu")
    q = r["indicators"]["quote"][0]
    df = _df_tu_tohlcv({"t": r["timestamp"], "o": q["open"], "h": q["high"], "l": q["low"],
                        "c": q["close"], "v": q["volume"]})
    return df.dropna(subset=["close"])


# tên → (hàm, đơn vị giá CỔ PHIẾU nguồn trả về). Chỉ số (VNINDEX) luôn giữ nguyên.
NGUON_GIA = {
    "VNDirect": (tu_vndirect, 1000),
    "TCBS": (tu_tcbs, 1),
    "DNSE": (tu_dnse, 1000),
    "VCI": (tu_vci, 1),
    "SSI": (tu_ssi, None),
    "Yahoo": (tu_yahoo, 1),
    "vnstock": (lambda ma, start, end, chi_so=False: _vns().gia(ma, start, end, chi_so), None),
}


def _vns():
    from . import vnstock_nguon
    return vnstock_nguon


# ------------------------------------------------------------------ chuẩn hoá
def chuan_hoa(df):
    """time → index, sắp xếp, bỏ trùng/thiếu, ép kiểu số."""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["close"])
    for c in ("open", "high", "low"):
        df[c] = df[c].fillna(df["close"])
    df["volume"] = df["volume"].fillna(0)
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def ve_nghin_dong(df, don_vi):
    """Đưa giá cổ phiếu về nghìn đồng. don_vi=None → tự nhận biết (giá trung vị > 1.500 coi là đơn vị đồng)."""
    if don_vi is None:
        don_vi = 1 if df["close"].median() > 1500 else 1000
    if don_vi == 1:
        df = df.copy()
        for c in ("open", "high", "low", "close"):
            df[c] = df[c] / 1000
    return df


def kiem_tra_hop_le(df):
    """Loại dữ liệu hỏng: giá ≤ 0, high < low."""
    if df is None or df.empty:
        raise ValueError("rỗng")
    if (df["close"] <= 0).any():
        raise ValueError("có giá ≤ 0")
    if (df["high"] < df["low"]).mean() > 0.01:
        raise ValueError("high < low bất thường")
    return df


def tai_online(ma, start, end, chi_so=False, thu_tu=None):
    """Thử lần lượt các nguồn theo thứ tự; trả về (DataFrame chuẩn hoá, tên nguồn) hoặc (None, None)."""
    loi = []
    for ten in (thu_tu or ch.THU_TU_NGUON_GIA):
        if ten not in NGUON_GIA or CAU_DAO_GIA.bo_qua(ten):
            continue
        ham, don_vi = NGUON_GIA[ten]
        try:
            df = chuan_hoa(ham(ma, start, end, chi_so))
            if not chi_so:
                df = ve_nghin_dong(df, don_vi)
            kiem_tra_hop_le(df)
            NHAT_KY.ghi(f"Giá {ma}", ten, "OK", f"{len(df)} nến {df.index[0]:%d/%m/%Y}→{df.index[-1]:%d/%m/%Y}")
            CAU_DAO_GIA.ghi(ten, True)
            return df, ten
        except (Exception, SystemExit) as e:          # thư viện ngoài có thể gọi SystemExit (VD hết hạn mức)
            loi.append(ten)
            if "hạn mức" not in str(e) and "lượt" not in str(e):
                CAU_DAO_GIA.ghi(ten, False)
            NHAT_KY.ghi(f"Giá {ma}", ten, "Lỗi", str(e)[:80])
            time.sleep(0.2)
    return None, None


# ------------------------------------------------------------------ file CSV người dùng
def tu_csv(path):
    """CSV cột tiếng Anh/tiếng Việt, ngày ISO hoặc dd/mm/yyyy."""
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={
        "ngày": "time", "date": "time", "datetime": "time", "giá mở cửa": "open", "giá cao nhất": "high",
        "giá thấp nhất": "low", "giá đóng cửa": "close", "khối lượng": "volume", "price": "close", "vol.": "volume"})
    t = df["time"].astype(str).str.strip()
    if t.str.match(r"^\d{4}-").all():
        df["time"] = pd.to_datetime(t)
    else:
        try:
            df["time"] = pd.to_datetime(t, dayfirst=True, format="mixed")
        except (TypeError, ValueError):
            df["time"] = pd.to_datetime(t, dayfirst=True)
    for c in ("open", "high", "low", "close", "volume"):
        if c in df and not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = pd.to_numeric(df[c].map(doc_so), errors="coerce")
    for c in ("open", "high", "low"):
        if c not in df:
            df[c] = df["close"]
    if "volume" not in df:
        df["volume"] = 0
    return df


# ------------------------------------------------------------------ tải có bộ nhớ đệm
def tai_gia(ma, start, thu_muc_csv=None, dung_cache=True, thu_muc_cache=None):
    """
    Giá NGÀY 1 mã (nghìn đồng). Ưu tiên: thư mục CSV người dùng → bộ nhớ đệm + tải bổ sung → tải mới.
    Bộ nhớ đệm: lần sau chỉ tải từ phiên cuối đã lưu (lùi 7 ngày để cập nhật điều chỉnh giá).
    """
    if thu_muc_csv:
        f = os.path.join(thu_muc_csv, f"{ma}.csv")
        with _khoa_nguon:
            NGUON_DA_DUNG[ma] = "CSV"
        if not os.path.exists(f):
            return None
        return ve_nghin_dong(chuan_hoa(tu_csv(f)), None)
    thu_muc_cache = thu_muc_cache or ch.THU_MUC_CACHE
    hom_nay = str(date.today())
    f = os.path.join(thu_muc_cache, f"{ma}.csv")
    cu = None
    if dung_cache and os.path.exists(f):
        try:
            cu = chuan_hoa(tu_csv(f))
        except Exception:
            cu = None
    if cu is not None and len(cu) and cu.index[0] <= pd.Timestamp(start) + pd.Timedelta(days=10):
        tu = str((cu.index[-1] - pd.Timedelta(days=7)).date())
        moi, nguon = tai_online(ma, tu, hom_nay)
        df = cu if moi is None else pd.concat([cu[cu.index < moi.index[0]], moi])
        nguon = "cache" + (f" + {nguon}" if nguon else " (không cập nhật được)")
    else:
        df, nguon = tai_online(ma, start, hom_nay)
    with _khoa_nguon:
        NGUON_DA_DUNG[ma] = nguon or "—"
    if df is not None and dung_cache:
        os.makedirs(thu_muc_cache, exist_ok=True)
        df.reset_index().to_csv(f, index=False)
    return df


def tai_vnindex(start, csv=None):
    """VNINDEX ngày – tính Beta & sức mạnh tương đối."""
    if csv:
        NHAT_KY.ghi("VNINDEX", "CSV", "OK", csv)
        return chuan_hoa(tu_csv(csv))
    df, nguon = tai_online("VNINDEX", start, str(date.today()), chi_so=True,
                           thu_tu=[t for t in ch.THU_TU_NGUON_GIA if t != "Yahoo"])
    if df is None:
        print("  ⚠ Không tải được VNINDEX – Beta & sức mạnh tương đối sẽ để trống")
    else:
        print(f"  VNINDEX: {len(df)} phiên từ {nguon}")
    return df


def tinh_beta(df, vni, so_phien=126):
    """Beta = Cov(r_cp, r_vni) / Var(r_vni) theo lợi suất ngày, so_phien gần nhất – 126 phiên (6 tháng) như ptcp,
    khớp FireAnt / Vietstock. Bỏ phiên |lợi suất| > 16% (vượt biên độ mọi sàn → giá chưa điều chỉnh quyền)."""
    if vni is None:
        return np.nan
    r = pd.concat([df.close.pct_change(), vni.close.pct_change()], axis=1, join="inner").dropna()
    r = r[r.iloc[:, 0].abs() <= 0.16].tail(so_phien)
    if len(r) < 60:
        return np.nan
    return r.iloc[:, 0].cov(r.iloc[:, 1]) / r.iloc[:, 1].var()
