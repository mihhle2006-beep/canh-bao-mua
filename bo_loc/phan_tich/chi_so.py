# -*- coding: utf-8 -*-
"""Tính toàn bộ chỉ tiêu (kỹ thuật + cơ bản) cho 1 mã → dict m dùng cho lọc & đánh giá."""
import numpy as np
import pandas as pd

from .. import cau_hinh as ch
from ..nguon import co_ban
from ..nguon.gia import tinh_beta
from ..tien_ich import co
from . import ky_thuat as kt
from .. import loi        # lõi dùng chung với ptcp: chỉ báo, đỉnh/đáy theo giá đóng cửa, tín hiệu
from ..loi.he_thoat import stop_chuan   # cắt lỗ chuẩn của hệ thoát T2-3R-ma10 (chiến lược thị trường)


def tinh_chi_so(ma, df, vni=None, cb=None, nhom="", nguon_gia=""):
    """
    Đỉnh/đáy, đường xu hướng, tín hiệu dùng lõi ptcp (bo_loc/loi).
    CẮT LỖ & MỤC TIÊU = giá trị của CHIẾN LƯỢC THỊ TRƯỜNG (cùng bot canh-bao-mua):
      cắt lỗ chuẩn hệ thoát = max(giá − 2×ATR, giá − 7%), tối thiểu 1,5×ATR;  R = giá − cắt lỗ
      mục tiêu tạm thời 1R (gia_mt) và 3R (gia_mt_3r) – mốc dời cắt lỗ, KHÔNG chốt cứng; upside = % tới mốc 3R.
    Sau khi chạy chiến lược cho cả rổ, cli ghi đè bằng cắt lỗ / mốc của hệ thống cho từng mã (chien_luoc_tt.ap_vao_chi_so).
    """
    d = loi.tinh_chi_bao(df)
    for n in (20, 50, 100, 200):
        d[f"MA{n}"] = d.close.rolling(n).mean()
    pv = loi.tim_dinh_day(d, "Ngày")
    xh = loi.duong_xu_huong(d, pv)
    _, diem_d, co_ = loi.phan_tich_tin_hieu(d, pv, xh, "Ngày")

    w = loi.tinh_chi_bao(kt.gop_tuan(df))
    pv_w = loi.tim_dinh_day(w, "Tuần")
    xh_w = loi.duong_xu_huong(w, pv_w)

    L, Lw = d.iloc[-1], w.iloc[-1]
    gia = L.close
    d52 = d[d.index > d.index[-1] - pd.Timedelta(weeks=52)]

    cat_lo = float(stop_chuan(gia, L.ATR)) if co(L.ATR) else gia * 0.93
    R = gia - cat_lo
    gia_mt, gia_mt_3r = gia + R, gia + 3 * R
    upside = (gia_mt_3r / gia - 1) * 100
    rr = 3.0                                    # tới mốc 3R (theo định nghĩa)

    rs3t = np.nan
    if vni is not None and len(d) > 63:
        v = vni.close[vni.index <= d.index[-1]]
        if len(v) > 63:
            rs3t = (gia / d.close.iloc[-64] - 1) * 100 - (v.iloc[-1] / v.iloc[-64] - 1) * 100

    day_ = pv[pv.loai == "Đáy"].tail(2)
    adx, pdi, mdi = kt.tinh_adx(d, 14)
    st, st_dir = kt.supertrend(d, *ch.SUPERTREND)
    d["ST"], d["ST_dir"] = st, st_dir
    cbt = co_ban.tinh_chi_so(cb or {}, gia)

    def bien_dong(so_phien):
        return gia / d.close.iloc[-1 - so_phien] - 1 if len(d) > so_phien else np.nan

    truoc_nam = d.close[d.index.year < d.index[-1].year]
    huong_ma = lambda c: ("Tăng" if d[c].iloc[-1] > d[c].iloc[-6] else "Giảm") if len(d) > 106 else ""
    rsi_s = d.RSI.tail(6)
    c52 = d52.close
    cao52, thap52 = (c52.max(), c52.min()) if loi.chi_bao.DINH_DAY_THEO == "close" else (d52.high.max(), d52.low.min())
    return {
        "Mã": ma, "gia": gia, "ngay": d.index[-1],
        "gtgd20": (d.volume * d.close * 1000).tail(20).mean() / 1e9,
        "vol_ratio": L.volume / L.VolMA20 if L.VolMA20 > 0 else np.nan,
        "ma20": L.MA20, "ma50": L.MA50, "ma200": L.MA200, "rsi": L.RSI,
        "macd_d": L.MACD, "sig_d": L.SIGNAL, "macd_w": Lw.MACD, "sig_w": Lw.SIGNAL,
        "cat_len_d": bool(co_.get("cat_len_signal") or co_.get("cat_len_0")),
        "phan_ky_duong": bool(co_.get("phan_ky_duong")),
        "thung_ho_tro": bool(co_.get("thung_ho_tro")),
        "day_cao_hon": bool(len(day_) == 2 and day_.gia.iloc[1] > day_.gia.iloc[0]),
        "cau_truc_d": xh["cau_truc"], "cau_truc_w": xh_w["cau_truc"],
        "diem_ngay": diem_d,
        "cao52": cao52, "thap52": thap52,
        "cach_dinh52": (gia / cao52 - 1) * 100,
        "tren_day52": (gia / thap52 - 1) * 100,
        "vi_tri52": (gia - thap52) / (cao52 - thap52) * 100 if cao52 > thap52 else 50.0,
        "ret1t": (gia / d.close.iloc[-22] - 1) * 100 if len(d) > 22 else np.nan,
        "ret3t": (gia / d.close.iloc[-64] - 1) * 100 if len(d) > 64 else np.nan,
        "rs3t": rs3t, "beta": tinh_beta(d, vni),
        "gia_mt": gia_mt, "gia_mt_3r": gia_mt_3r, "pp_mt": "mốc 1R / 3R (hệ thoát – không chốt cứng)",
        "upside": upside, "cat_lo": cat_lo, "rr": rr, "kc_cat_lo_pct": R / gia * 100,
        "cat_lo_theo": "chuẩn hệ thoát (2×ATR, ≤ 7%, ≥ 1,5×ATR)",
        "ev_mt": np.nan,
        "khuyen_nghi": "",                       # = nhóm chiến lược thị trường (ghi sau khi chạy chiến lược)
        "klgd20": d.volume.tail(20).mean(),
        "adx": adx.iloc[-1], "pdi": pdi.iloc[-1], "mdi": mdi.iloc[-1],
        "ma20_doc": d.MA20.iloc[-1] - d.MA20.iloc[-6] if len(d) > 6 else np.nan,
        "dinh20": d.high.iloc[-21:-1].max(),
        "st": st.iloc[-1], "st_dir": st_dir.iloc[-1],
        "atr": L.ATR, "atr_pct": L.ATR / gia * 100,
        "bien_dong": d.close.pct_change().tail(60).std() * np.sqrt(252) * 100,
        "mdd52": ((c52 / c52.cummax()) - 1).min() * 100,
        "cach_ma20": (gia / L.MA20 - 1) * 100 if co(L.MA20) and L.MA20 > 0 else np.nan,
        **cbt,
        # ---- thêm cho 4 bảng kết quả & chiến lược rủi ro cao
        "kl_phien": float(L.volume), "klgd3t": d.volume.tail(63).mean(), "ma100": d.MA100.iloc[-1],
        "ma20_huong": huong_ma("MA20"), "ma50_huong": huong_ma("MA50"), "ma100_huong": huong_ma("MA100"),
        "mo_hinh_nen": kt.mo_hinh_nen(d),
        "bd_1n": bien_dong(1), "bd_1t": bien_dong(5), "bd_2t": bien_dong(10), "bd_1th": bien_dong(21),
        "bd_3th": bien_dong(63), "bd_6th": bien_dong(126), "bd_9th": bien_dong(189), "bd_1nam": bien_dong(252),
        "bd_ytd": gia / truoc_nam.iloc[-1] - 1 if len(truoc_nam) else np.nan,
        "rsi_vuot_30": bool((rsi_s.iloc[:-1] < 30).any() and rsi_s.iloc[-1] >= 30),
        "tich_luy_phien": kt.so_phien_tich_luy(df),
        "tlv": kt.tich_luy_va_vuot(df),                       # theo ngưỡng mặc định 20 phiên, KL ×5, giá +5%
        "nguon_gia": nguon_gia, "nhom": nhom,
        "_d": d,
    }
