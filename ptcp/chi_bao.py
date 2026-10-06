# -*- coding: utf-8 -*-
"""Chỉ báo kỹ thuật, đỉnh/đáy MACD, đường xu hướng, chấm điểm tín hiệu."""
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
    BO_QUA_DAU, DINH_DAY_THEO, EWMA_LAMBDA, MACD_CHAM, MACD_NHANH, MACD_TIN_HIEU,
    MAX_CACH_DUONG_XH, MA_DAI, MA_NGAN, NGUONG_GAN_HO_TRO, N_XAC_NHAN, SAI_SO_CHAM,
    SO_CHAM_XAC_NHAN, SO_NEN_GAN,
)


# ==========================================================================
# 2. CHỈ BÁO
# ==========================================================================
def tinh_chi_bao(df):
    df = df.copy()
    c = df.close
    df["MACD"] = c.ewm(span=MACD_NHANH, adjust=False).mean() - c.ewm(span=MACD_CHAM, adjust=False).mean()
    df["SIGNAL"] = df.MACD.ewm(span=MACD_TIN_HIEU, adjust=False).mean()
    df["HIST"] = df.MACD - df.SIGNAL

    delta = c.diff()
    tang = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    giam = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI"] = 100 - 100 / (1 + tang / giam.replace(0, np.nan))

    tr = pd.concat([df.high - df.low, (df.high - c.shift()).abs(),
                    (df.low - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["VolMA20"] = df.volume.rolling(20, min_periods=5).mean()
    # [MỚI] OBV – dòng tiền tích luỹ theo khối lượng
    df["OBV"] = (np.sign(c.diff()).fillna(0) * df.volume).cumsum()
    df["OBV_MA20"] = df.OBV.rolling(20, min_periods=5).mean()
    df[f"MA{MA_NGAN}"] = c.rolling(MA_NGAN, min_periods=MA_NGAN).mean()
    df[f"MA{MA_DAI}"] = c.rolling(MA_DAI, min_periods=MA_DAI).mean()
    df["pos"] = np.arange(len(df))          # vị trí nến (dùng để vẽ & tính đường thẳng)
    return df


def sigma_ewma(close, lam=EWMA_LAMBDA):
    """[MỚI] Độ lệch chuẩn lợi suất log NGÀY theo EWMA (phản ánh biến động hiện tại nhanh hơn σ phẳng)."""
    r = np.log(close).diff().dropna()
    if len(r) < 20:
        return float(r.std())
    return float(np.sqrt((r ** 2).ewm(alpha=1 - lam, adjust=False).mean().iloc[-1]))


# ==========================================================================
# 3. XÁC ĐỊNH ĐỈNH / ĐÁY THEO MACD
# ==========================================================================
def tim_dinh_day(df, ten_khung="Ngày"):
    """
    Trả về DataFrame các đỉnh/đáy, mỗi dòng ứng với 1 đoạn MACD:
      time, pos, gia, loai ('Đỉnh'/'Đáy'), macd_cuc_tri, xac_nhan, tu, den, trang_thai
    [SỬA] Đỉnh/đáy XÁC NHẬN khi: đoạn MACD đã kết thúc, HOẶC đã có ≥ N_XAC_NHAN nến sau nó mà không bị phá.
          Đỉnh/đáy nằm ở chính nến hiện tại (hay vài nến gần nhất) là TẠM THỜI → không dùng cho đường xu hướng,
          so sánh đáy/đỉnh, mục tiêu hay cắt lỗ (tránh lỗi 'hỗ trợ cách 0.0%' luôn đúng).
    """
    n_xn = N_XAC_NHAN.get(ten_khung, 5)
    d = df.iloc[BO_QUA_DAU:]
    dau = np.sign(d.MACD).replace(0, np.nan).ffill().fillna(1)
    ma_doan = (dau != dau.shift()).cumsum()
    nhom = list(d.groupby(ma_doan))
    x_cuoi = len(df) - 1

    rows = []
    for k, (_, g) in enumerate(nhom):
        duong = dau.loc[g.index[0]] > 0
        cot_dinh = g.close if DINH_DAY_THEO == "close" else g.high
        cot_day = g.close if DINH_DAY_THEO == "close" else g.low
        if duong:
            t = cot_dinh.idxmax()
            gia, loai, cuc_tri = cot_dinh.max(), "Đỉnh", g.MACD.max()
        else:
            t = cot_day.idxmin()
            gia, loai, cuc_tri = cot_day.min(), "Đáy", g.MACD.min()
        pos = int(df.pos[t])
        doan_xong = k < len(nhom) - 1
        du_nen = (x_cuoi - pos) >= n_xn
        xac_nhan = bool(doan_xong or du_nen)
        trang_thai = ("xác nhận" if doan_xong else f"xác nhận (≥{n_xn} nến chưa bị phá)") if xac_nhan else "tạm thời"
        rows.append([t, pos, gia, loai, cuc_tri, xac_nhan, g.index[0], g.index[-1], trang_thai])
    return pd.DataFrame(rows, columns=["time", "pos", "gia", "loai", "macd_cuc_tri",
                                       "xac_nhan", "tu", "den", "trang_thai"])


# ==========================================================================
# 4. ĐƯỜNG XU HƯỚNG (nối 2 đỉnh & 2 đáy ĐÃ XÁC NHẬN gần nhất)
# ==========================================================================
def _so_lan_cham(df, x1, y1, doc, cot):
    """Số lần (cụm nến cách nhau ≥ 3 nến) giá chạm đường thẳng trong sai số SAI_SO_CHAM %."""
    xs = np.arange(int(x1), len(df))
    gia_duong = y1 + doc * (xs - x1)
    v = df[cot].values[int(x1):]
    hop_le = gia_duong > 0
    cham = np.zeros(len(xs), bool)
    cham[hop_le] = np.abs(v[hop_le] / gia_duong[hop_le] - 1) * 100 <= SAI_SO_CHAM
    idx = np.where(cham)[0]
    return int(1 + np.sum(np.diff(idx) >= 3)) if len(idx) else 0


def duong_xu_huong(df, pv):
    """
    [SỬA] Chỉ dùng đỉnh/đáy ĐÃ XÁC NHẬN. Mỗi đường có thêm:
      so_cham  – số lần giá chạm đường (≥ SO_CHAM_XAC_NHAN = đường đã xác nhận)
      cach     – % khoảng cách tới giá hiện tại; > MAX_CACH_DUONG_XH → hop_le = False (không dùng làm mốc hành động)
    """
    ket_qua = {}
    x_nay = len(df) - 1
    ht = df.close.iloc[-1]
    pvx = pv[pv.xac_nhan]
    for loai, khoa in (("Đỉnh", "khang_cu"), ("Đáy", "ho_tro")):
        p = pvx[pvx.loai == loai].tail(2)
        if len(p) < 2:
            continue
        (x1, x2), (y1, y2) = p.pos.values, p.gia.values
        if x2 == x1:
            continue
        doc = (y2 - y1) / (x2 - x1)
        gia_nay = y1 + doc * (x_nay - x1)
        if gia_nay <= 0:
            continue
        cot = "close" if DINH_DAY_THEO == "close" else ("high" if loai == "Đỉnh" else "low")
        so_cham = _so_lan_cham(df, x1, y1, doc, cot)
        cach = abs(gia_nay / ht - 1) * 100
        ket_qua[khoa] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "doc": doc, "gia_nay": gia_nay,
                         "gia_truoc": y1 + doc * (x_nay - 1 - x1), "so_cham": so_cham, "cach": cach,
                         "hop_le": cach <= MAX_CACH_DUONG_XH, "xac_nhan": so_cham >= SO_CHAM_XAC_NHAN}

    # Phân loại cấu trúc xu hướng – CHỈ từ đỉnh/đáy đã xác nhận
    dinh, day_ = pvx[pvx.loai == "Đỉnh"].tail(2), pvx[pvx.loai == "Đáy"].tail(2)
    if len(dinh) == 2 and len(day_) == 2:
        dinh_cao_hon = dinh.gia.iloc[1] > dinh.gia.iloc[0]
        day_cao_hon = day_.gia.iloc[1] > day_.gia.iloc[0]
        if dinh_cao_hon and day_cao_hon:
            cau_truc = "TĂNG (đỉnh sau cao hơn, đáy sau cao hơn)"
        elif not dinh_cao_hon and not day_cao_hon:
            cau_truc = "GIẢM (đỉnh sau thấp hơn, đáy sau thấp hơn)"
        elif dinh_cao_hon and not day_cao_hon:
            cau_truc = "MỞ RỘNG (biên độ dao động nới rộng)"
        else:
            cau_truc = "TÍCH LŨY TAM GIÁC (biên độ thu hẹp)"
    else:
        cau_truc = "Chưa đủ đỉnh/đáy xác nhận để xác định"
    ket_qua["cau_truc"] = cau_truc

    # Ghi chú về đỉnh/đáy tạm thời (chỉ để tham khảo, không chấm điểm)
    ghi_chu = ""
    tam = pv[~pv.xac_nhan]
    if len(tam):
        r = tam.iloc[-1]
        cung_loai = pvx[pvx.loai == r.loai]
        if len(cung_loai):
            truoc = cung_loai.gia.iloc[-1]
            if r.loai == "Đáy" and r.gia < truoc:
                ghi_chu = f"Đang hình thành đáy THẤP HƠN ({r.gia:,.2f} < {truoc:,.2f}) – tạm thời, chưa xác nhận"
            elif r.loai == "Đỉnh" and r.gia > truoc:
                ghi_chu = f"Đang hình thành đỉnh CAO HƠN ({r.gia:,.2f} > {truoc:,.2f}) – tạm thời, chưa xác nhận"
    ket_qua["ghi_chu_tam"] = ghi_chu
    return ket_qua


def _duong(xh, khoa):
    """Đường xu hướng dùng được cho quyết định (đủ gần giá); None nếu không có/quá xa."""
    l = xh.get(khoa)
    return l if l and l.get("hop_le") else None


# ==========================================================================
# 6. TÍN HIỆU MUA / BÁN TRÊN TỪNG KHUNG
# ==========================================================================
def _cat_len(a, b, n):
    """a vừa cắt lên b trong n nến gần nhất? Trả về số nến trước (0 = nến hiện tại) hoặc None."""
    tren = (a > b).values
    for k in range(n):
        i = len(tren) - 1 - k
        if i >= 1 and tren[i] and not tren[i - 1]:
            return k
    return None


def phan_tich_tin_hieu(df, pv, xh, ten_khung):
    """
    Trả về: danh sách (ký hiệu, nội dung, điểm), tổng điểm, các cờ quan trọng.
    [SỬA] Tín hiệu ĐẢO CHIỀU (gần hỗ trợ, RSI quá bán, phân kỳ dương) chỉ được cộng điểm khi đã có XÁC NHẬN
          (MACD cắt lên Signal / cắt lên 0, hoặc giá phá đỉnh nhỏ 5 nến) – nếu không, 0 điểm (tránh "bắt dao rơi").
          Cấu trúc đỉnh/đáy chỉ dùng đỉnh/đáy đã xác nhận. Thêm xác nhận khối lượng (KL/TB20, OBV).
    """
    n = SO_NEN_GAN[ten_khung]
    L = df.iloc[-1]
    ds, co = [], {}

    def them(diem, nd):
        ds.append(("▲" if diem > 0 else "▼" if diem < 0 else "•", nd, diem))

    them(1 if L.MACD > 0 else -1, f"MACD {'trên' if L.MACD > 0 else 'dưới'} mốc 0 "
         f"({'xu hướng tăng' if L.MACD > 0 else 'xu hướng giảm'})")
    them(1 if L.MACD > L.SIGNAL else -1,
         f"MACD {'trên' if L.MACD > L.SIGNAL else 'dưới'} đường tín hiệu")

    k = _cat_len(df.MACD, df.SIGNAL, n)
    co["cat_len_signal"] = k is not None
    if k is not None:
        vi_tri = "DƯỚI mốc 0 → tín hiệu mua sớm" if df.MACD.iloc[-1 - k] < 0 else "trên mốc 0 → tiếp diễn tăng"
        them(2, f"MACD vừa cắt lên đường tín hiệu {k} nến trước ({vi_tri})")
    k0 = _cat_len(df.MACD, pd.Series(0, index=df.index), n)
    co["cat_len_0"] = k0 is not None
    if k0 is not None:
        them(2, f"MACD vừa cắt lên mốc 0 {k0} nến trước → xác nhận xu hướng tăng")
    kx = _cat_len(df.SIGNAL, df.MACD, n)
    if kx is not None:
        them(-2, f"MACD vừa cắt xuống đường tín hiệu {kx} nến trước")

    dinh_nho = df.high.shift(1).rolling(5, min_periods=3).max()
    co["pha_dinh_nho"] = bool((df.close > dinh_nho).iloc[-n:].any())
    xn = co["cat_len_signal"] or co["cat_len_0"] or co["pha_dinh_nho"]
    co["xac_nhan_dao_chieu"] = xn
    chua_xn = " – CHƯA có xác nhận đảo chiều (MACD cắt lên / phá đỉnh nhỏ) → 0 điểm, tránh bắt dao rơi"

    pvx = pv[pv.xac_nhan]
    day_ = pvx[pvx.loai == "Đáy"].tail(2)
    co["xu_huong_giam"] = bool(L.MACD < 0 or "GIẢM" in xh.get("cau_truc", ""))
    if len(day_) == 2:
        if day_.gia.iloc[1] > day_.gia.iloc[0]:
            them(1, f"Đáy sau ({day_.gia.iloc[1]:,.2f}) cao hơn đáy trước ({day_.gia.iloc[0]:,.2f}) [đã xác nhận]")
        else:
            them(-1, f"Đáy sau ({day_.gia.iloc[1]:,.2f}) thấp hơn đáy trước ({day_.gia.iloc[0]:,.2f}) [đã xác nhận]")
            co["xu_huong_giam"] = True
        if day_.gia.iloc[1] < day_.gia.iloc[0] and day_.macd_cuc_tri.iloc[1] > day_.macd_cuc_tri.iloc[0]:
            if xn:
                them(2, "PHÂN KỲ DƯƠNG đã xác nhận: giá đáy thấp hơn, MACD đáy cao hơn + MACD/giá đã quay lên")
            else:
                them(0, "Phân kỳ dương (giá đáy thấp hơn, MACD đáy cao hơn)" + chua_xn)
            co["phan_ky_duong"] = True
    if xh.get("ghi_chu_tam"):
        them(0, xh["ghi_chu_tam"])
    dinh = pvx[pvx.loai == "Đỉnh"].tail(2)
    if len(dinh) == 2 and dinh.gia.iloc[1] > dinh.gia.iloc[0] and \
            dinh.macd_cuc_tri.iloc[1] < dinh.macd_cuc_tri.iloc[0]:
        them(-2, "PHÂN KỲ ÂM: giá tạo đỉnh cao hơn nhưng MACD tạo đỉnh thấp hơn → lực mua suy yếu")

    ht = L.close
    ht_line, kc_line = _duong(xh, "ho_tro"), _duong(xh, "khang_cu")
    co["gan_ho_tro"] = co["thung_ho_tro"] = co["pha_khang_cu"] = False
    if ht_line:
        lech = (ht / ht_line["gia_nay"] - 1) * 100
        if lech < -1:
            them(-2, f"Giá đã THỦNG đường hỗ trợ ({ht_line['gia_nay']:,.2f})")
            co["thung_ho_tro"] = True
        elif lech <= NGUONG_GAN_HO_TRO:
            co["gan_ho_tro"] = True
            nd = f"Giá gần đường hỗ trợ ({ht_line['gia_nay']:,.2f}, cách {lech:.1f}%, {ht_line['so_cham']} lần chạm)"
            them(1, nd + " → vùng mua đã xác nhận") if xn else them(0, nd + chua_xn)
    for khoa, ten in (("ho_tro", "hỗ trợ"), ("khang_cu", "kháng cự")):
        l = xh.get(khoa)
        if l and not l["hop_le"]:
            them(0, f"Đường {ten} {l['gia_nay']:,.2f} cách giá {l['cach']:.0f}% (> {MAX_CACH_DUONG_XH:.0f}%) → bỏ qua")
    vol_ok = bool(L.VolMA20 > 0 and L.volume > 1.5 * L.VolMA20)
    if kc_line:
        if ht > kc_line["gia_nay"] and df.close.iloc[-2] <= kc_line["gia_truoc"]:
            them(2 if vol_ok else 0, f"Giá PHÁ đường kháng cự ({kc_line['gia_nay']:,.2f})"
                 + (" kèm KL ≥ 1.5× TB20 → breakout xác nhận" if vol_ok else " – KL chưa xác nhận (0 điểm)"))
            co["pha_khang_cu"] = vol_ok
        elif ht > kc_line["gia_nay"]:
            them(1, f"Giá đang nằm trên đường kháng cự cũ ({kc_line['gia_nay']:,.2f})")

    if L.RSI > 70:
        them(-1, f"RSI = {L.RSI:.0f}: quá mua, tránh mua đuổi")
    elif L.RSI < 30:
        them(1, f"RSI = {L.RSI:.0f}: quá bán, đã có xác nhận hồi phục") if xn else \
            them(0, f"RSI = {L.RSI:.0f}: quá bán" + chua_xn)

    # Khối lượng & OBV
    if len(df) > 25 and "OBV" in df:
        d_gia = df.close.iloc[-1] / df.close.iloc[-21] - 1
        d_obv = df.OBV.iloc[-1] - df.OBV.iloc[-21]
        if d_gia > 0 and d_obv < 0:
            them(-1, "Phân kỳ OBV: giá tăng 20 nến nhưng OBV giảm → dòng tiền không xác nhận")
        elif d_gia < 0 and d_obv > 0:
            them(0, "OBV tăng dù giá giảm 20 nến → có dấu hiệu gom hàng (cần giá xác nhận)")
        elif d_gia > 0 and d_obv > 0 and L.OBV >= df.OBV.iloc[-20:].max():
            them(1, "OBV lập đỉnh 20 nến cùng chiều giá → dòng tiền xác nhận")

    tong = sum(d for _, _, d in ds)
    return ds, tong, co


def them_ma(df):
    """Thêm cột MA50/MA200 cho DataFrame giá (dùng cho biểu đồ đường giá ngày)."""
    df = df.copy()
    for n in (MA_NGAN, MA_DAI):
        df[f"MA{n}"] = df.close.rolling(n, min_periods=n).mean()
    return df
