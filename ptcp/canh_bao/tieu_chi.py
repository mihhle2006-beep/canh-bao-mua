# -*- coding: utf-8 -*-
"""
TIÊU CHÍ THEO KHUNG – mỗi tiêu chí: {"ten", "dat" (True/False/None = thiếu dữ liệu), "chi_tiet", "loai"}.
  TUẦN : MACD tuần > Signal (phủ quyết) [+ MACD tuần > 0 tuỳ chọn]
  NGÀY : bắt buộc (chiến lược ky_thuat của bộ lọc) + ≥ DIEM_CONG_TOI_THIEU điểm cộng
  GIỜ  : MACD giờ > Signal VÀ (MACD giờ vừa cắt lên HOẶC giá vượt đỉnh 10 nến giờ)
  PHÚT : (MACD phút vừa cắt lên Signal HOẶC phá đỉnh 20 nến kèm KL đột biến) VÀ giá ≥ VWAP phiên VÀ RSI phút ≤ 75
"""
import numpy as np
import pandas as pd

from . import cau_hinh as C
from .chi_bao import adx, cat_len, chi_bao, dinh_day, supertrend, vwap_phien


def _tc(ten, dat, chi_tiet="", loai="bắt buộc"):
    return {"ten": ten, "dat": (None if dat is None else bool(dat)), "chi_tiet": chi_tiet, "loai": loai}


def _ket(khung, muc, diem_can=0):
    bb = [m for m in muc if m["loai"] == "bắt buộc"]
    cd = [m for m in muc if m["loai"] == "cộng điểm"]
    diem = sum(1 for m in cd if m["dat"])
    dat = all(m["dat"] for m in bb) and diem >= diem_can
    return {"khung": khung, "dat": bool(dat), "muc": muc, "diem": diem, "tong_diem": len(cd), "diem_can": diem_can,
            "truot": [m["ten"] for m in bb if not m["dat"]]}


def khung_tuan(w):
    if w is None or len(w) < 35:
        return _ket("Tuần", [_tc("Đủ dữ liệu tuần (≥ 35 tuần)", False)])
    L = chi_bao(w).iloc[-1]
    muc = [_tc("MACD tuần > Signal (tuần đã đóng)", L.MACD > L.SIGNAL, f"{L.MACD:.2f} vs {L.SIGNAL:.2f}"),
           _tc("MACD tuần > 0", L.MACD > 0, f"{L.MACD:.2f}",
               "bắt buộc" if C.TUAN_MACD_TREN_0_LA_BAT_BUOC else "cộng điểm")]
    return _ket("Tuần", muc)


def khung_ngay(dn, vni=None, nen_dang_chay=False):
    if dn is None or len(dn) < 210:
        return _ket("Ngày", [_tc("Đủ dữ liệu ngày (≥ 210 phiên)", False)])
    d = chi_bao(dn)
    L = d.iloc[-1]
    gia = float(L.close)
    dong = d.iloc[:-1] if nen_dang_chay and len(d) > 21 else d          # KL/GTGD: dùng phiên đã đóng
    kl20 = float(dong.volume.tail(20).mean())
    gtgd20 = float((dong.volume * dong.close * 1000).tail(20).mean() / 1e9)
    _, huong = supertrend(dn, *C.SUPERTREND)
    pv = dinh_day(d)
    pvx = pv[pv.xac_nhan]
    day_xn = pvx[(pvx.loai == "Đáy") & (pvx.time < d.index[-1])]
    ho_tro = float(day_xn.gia.iloc[-1]) if len(day_xn) else np.nan
    a, pdi, mdi = adx(dn)
    dinh2, day2 = pvx[pvx.loai == "Đỉnh"].tail(2), pvx[pvx.loai == "Đáy"].tail(2)
    cau_truc = (len(dinh2) == 2 and len(day2) == 2 and dinh2.gia.iloc[1] > dinh2.gia.iloc[0]
                and day2.gia.iloc[1] > day2.gia.iloc[0])
    dinh20 = float(d.close.iloc[-21:-1].max())
    d52 = d[d.index > d.index[-1] - pd.Timedelta(weeks=52)]
    cao52 = float(d52.close.max())
    vol_ratio = float(dong.volume.iloc[-1] / dong.VolMA20.iloc[-1]) if dong.VolMA20.iloc[-1] > 0 else np.nan
    rs = np.nan
    if vni is not None and len(vni) > 64:
        v = vni.close.reindex(d.index).ffill()
        if v.iloc[-64] > 0:
            rs = (gia / d.close.iloc[-64] - 1) * 100 - (v.iloc[-1] / v.iloc[-64] - 1) * 100
    k_cat = cat_len(d.MACD, d.SIGNAL, 5)
    muc = [
        _tc(f"GTGD TB20 ≥ {C.GTGD_MIN:g} tỷ", gtgd20 >= C.GTGD_MIN, f"{gtgd20:.1f} tỷ"),
        _tc(f"KLGD TB20 ≥ {C.KLGD_MIN:,}", kl20 >= C.KLGD_MIN, f"{kl20:,.0f} CP"),
        _tc(f"Giá trên SuperTrend{C.SUPERTREND}", huong.iloc[-1] > 0),
        _tc("Giá > MA50", gia > L.MA50, f"MA50 {L.MA50:,.2f}"),
        _tc("MA20 > MA50", L.MA20 > L.MA50, f"{L.MA20:,.2f} vs {L.MA50:,.2f}"),
        _tc("MACD ngày > Signal", L.MACD > L.SIGNAL, f"{L.MACD:.2f} vs {L.SIGNAL:.2f}"),
        _tc(f"RSI ngày {C.RSI_NGAY[0]}–{C.RSI_NGAY[1]}", C.RSI_NGAY[0] <= L.RSI <= C.RSI_NGAY[1], f"{L.RSI:.0f}"),
        _tc("Chưa thủng hỗ trợ (đáy xác nhận gần nhất)", None if np.isnan(ho_tro) else gia >= ho_tro,
            f"hỗ trợ {ho_tro:,.2f}" if ho_tro == ho_tro else "chưa có đáy xác nhận"),
        _tc("MA50 > MA200", L.MA50 > L.MA200 if L.MA200 == L.MA200 else None, loai="cộng điểm"),
        _tc("MA20 dốc lên (5 phiên)", d.MA20.iloc[-1] > d.MA20.iloc[-6], loai="cộng điểm"),
        _tc(f"ADX ≥ {C.ADX_MIN} & +DI > −DI", a.iloc[-1] >= C.ADX_MIN and pdi.iloc[-1] > mdi.iloc[-1],
            f"ADX {a.iloc[-1]:.0f}", "cộng điểm"),
        _tc("Cấu trúc tăng (đỉnh & đáy sau cao hơn)", cau_truc, loai="cộng điểm"),
        _tc("MACD ngày vừa cắt lên (5 phiên)", k_cat is not None,
            f"{k_cat} phiên trước" if k_cat is not None else "", "cộng điểm"),
        _tc("Đóng cửa vượt đỉnh 20 phiên", gia > dinh20, f"đỉnh 20 phiên {dinh20:,.2f}", "cộng điểm"),
        _tc(f"KL đột biến ≥ {C.VOL_DOT_BIEN:g}× TB20", vol_ratio >= C.VOL_DOT_BIEN if vol_ratio == vol_ratio else None,
            f"{vol_ratio:.1f}×" if vol_ratio == vol_ratio else "", "cộng điểm"),
        _tc("Mạnh hơn VN-Index 3 tháng", rs > 0 if rs == rs else None,
            f"{rs:+.1f} điểm %" if rs == rs else "thiếu VN-Index", "cộng điểm"),
        _tc(f"Cách đỉnh 52T ≤ {C.GAN_DINH52:g}%", (1 - gia / cao52) * 100 <= C.GAN_DINH52,
            f"đỉnh 52T {cao52:,.2f}", "cộng điểm"),
    ]
    kq = _ket("Ngày", muc, C.DIEM_CONG_TOI_THIEU)
    kq.update(gia=gia, atr=float(L.ATR), ho_tro=ho_tro, pv=pv, cao52=cao52, d=d)
    return kq


def khung_gio(dh):
    if dh is None or len(dh) < 40:
        return _ket("Giờ", [_tc("Đủ dữ liệu giờ (≥ 40 nến)", False)])
    d = chi_bao(dh)
    L = d.iloc[-1]
    n = C.SO_NEN_GIO_GAN
    k = cat_len(d.MACD, d.SIGNAL, n)
    vuot = L.close > d.close.iloc[-n - 1:-1].max()
    muc = [_tc("MACD giờ > Signal", L.MACD > L.SIGNAL, f"{L.MACD:.3f} vs {L.SIGNAL:.3f}"),
           _tc(f"MACD giờ vừa cắt lên HOẶC vượt đỉnh {n} nến giờ", k is not None or vuot,
               (f"cắt lên {k} nến trước" if k is not None else "") + (" | vượt đỉnh" if vuot else "")),
           _tc("RSI giờ < 80", L.RSI < 80, f"{L.RSI:.0f}", "cộng điểm")]
    kq = _ket("Giờ", muc)
    kq["nen"] = d.index[-1]
    return kq


def khung_phut(dp):
    ten_k = f"{C.KHUNG_PHUT} phút"
    if dp is None or len(dp) < 40:
        return _ket(ten_k, [_tc(f"Đủ dữ liệu {ten_k} (≥ 40 nến)", False)])
    d = chi_bao(dp)
    L = d.iloc[-1]
    k = cat_len(d.MACD, d.SIGNAL, C.SO_NEN_PHUT_GAN)
    dinh_n = d.close.iloc[-C.DINH_PHUT_N - 1:-1].max()
    vr = L.volume / L.VolMA20 if L.VolMA20 > 0 else 0
    pha_dinh = L.close > dinh_n and vr >= C.VOL_PHUT_DOT_BIEN
    vw = vwap_phien(dp)
    kich_hoat = []
    if k is not None:
        kich_hoat.append(f"MACD {ten_k} cắt lên Signal {k} nến trước")
    if pha_dinh:
        kich_hoat.append(f"phá đỉnh {C.DINH_PHUT_N} nến ({dinh_n:,.2f}) kèm KL {vr:.1f}×")
    muc = [_tc("Tín hiệu vào lệnh (MACD cắt lên / phá đỉnh kèm KL)", (k is not None and L.MACD > L.SIGNAL) or pha_dinh,
               " & ".join(kich_hoat)),
           _tc("Giá ≥ VWAP phiên", L.close >= vw, f"VWAP {vw:,.2f}"),
           _tc(f"RSI {ten_k} ≤ {C.RSI_PHUT_MAX}", L.RSI <= C.RSI_PHUT_MAX, f"{L.RSI:.0f}")]
    kq = _ket(ten_k, muc)
    kq.update(nen=d.index[-1], gia=float(L.close), vwap=vw, kich_hoat=" & ".join(kich_hoat))
    return kq


def muc_gia(kn):
    """Cắt lỗ thống nhất & mục tiêu từ khung ngày → (cắt lỗ, mục tiêu, nguồn mục tiêu, R/R)."""
    gia, atr, pv = kn["gia"], kn["atr"], kn["pv"]
    lo_day = kn["ho_tro"] - C.BUFFER_ATR * atr if kn["ho_tro"] == kn["ho_tro"] and kn["ho_tro"] < gia else np.nan
    lo = max(max(x for x in (lo_day, gia - C.STOP_ATR_MAX * atr) if x == x), gia * (1 - C.LO_CUNG_PCT / 100))
    if gia - lo < C.STOP_ATR_MIN * atr:
        lo = gia - C.STOP_ATR_MIN * atr
    d = kn["d"]
    tu = d.index[-min(len(d), 504)]
    dinh = pv[(pv.loai == "Đỉnh") & pv.xac_nhan & (pv.time >= tu) & (pv.gia >= gia * (1 + C.UPSIDE_TOI_THIEU / 100))]
    if len(dinh):
        mt, nguon = float(dinh.gia.min()), f"đỉnh cũ {dinh.loc[dinh.gia.idxmin(), 'time']:%d/%m/%Y}"
    elif kn["cao52"] >= gia * (1 + C.UPSIDE_TOI_THIEU / 100):
        mt, nguon = kn["cao52"], "đỉnh 52 tuần"
    else:
        mt, nguon = gia + 3 * atr, "giá + 3×ATR ngày (vùng giá mới)"
    return lo, mt, nguon, (mt - gia) / (gia - lo) if gia > lo else np.nan


def thi_truong(vni, bay_gio=None):
    """VN-Index: TỐT khi giá > MA50 VÀ MACD tuần (tuần đã đóng) > Signal."""
    from .du_lieu import gop_tuan
    if vni is None or len(vni) < 260:
        return {"tot": None, "nhan": "không có dữ liệu VN-Index"}
    d = chi_bao(vni).iloc[-1]
    w = chi_bao(gop_tuan(vni, bay_gio)).iloc[-1]
    tren, macd = d.close > d.MA50, w.MACD > w.SIGNAL
    return {"tot": bool(tren and macd), "gia": float(d.close),
            "nhan": f"VN-Index {d.close:,.2f} {'trên' if tren else 'dưới'} MA50, MACD tuần "
                    f"{'>' if macd else '≤'} Signal → {'TỐT' if tren and macd else 'XẤU'}"}
