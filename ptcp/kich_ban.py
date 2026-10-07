# -*- coding: utf-8 -*-
"""Phần D: kịch bản giá, xác suất lịch sử (toàn bộ / 1 năm / trộn / có điều kiện), EV quyết định."""
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
    BUFFER_ATR, DINH_DAY_THEO, DU_LIEU_CTCK, EV_NGUONG, EWMA_LAMBDA, KHUNG_TG,
    KICH_BAN, LO_CUNG_PCT, NGUONG_HOI_TU, NHOM_PHIEN, RR_NGUONG, SO_MAU_DK_MIN,
    SO_MUC_TIEU, SO_NEN_GAN, SO_PHIEN_SU_KIEN, N_HIEU_DUNG_MIN, STOP_ATR_MAX, STOP_ATR_MIN, TRONG_SO_GOP_NGANH, TRONG_SO_KHUNG,
    TY_LE_THANH_KHOAN, TY_TRONG_MAX, UPSIDE_TOI_THIEU, XS_BAN_RA, XS_CUA_SO, XS_SAN,
    XS_TOI_THIEU_MT, XS_TRAN,
)
from .in_an import (
    fmt, so_vn,
)
from .chi_bao import (
    _duong, sigma_ewma,
)
from .thong_ke import (
    _mo_phong, _phan_vi_trong_so, _tb_trong_so, _tong_hop, _trong_so_gan_day, _upside_toi_da,
    _xs_cham_mot_phia, danh_gia_muc, mo_phong_gop_nganh,
)



Y_NGHIA_KB = {
    "★ MT ngắn hạn (ngày)": "Mục tiêu khung ngày có EV cao nhất",
    "★ MT trung hạn (tuần)": "Mục tiêu khung tuần có EV cao nhất",
    "✎ MT tự nhập": "Giá mục tiêu bạn tự định giá",
    "◆ MT đề xuất": "Mục tiêu sau khi nâng/hạ cho khớp phân tích (phần E1)",
    "✘ Cắt lỗ": "Cắt lỗ THỐNG NHẤT (một quy tắc cho toàn báo cáo)",
}


def phan_tich_kich_ban(df, so_cp, gia_von, n_phien, them):
    """
    D1 – BẢNG MỨC GIÁ: 6 mức % cố định + các mức kỹ thuật (mục tiêu ngày/tuần, tự nhập, cắt lỗ).
      • XS đóng cửa: % giai đoạn n phiên trong quá khứ mà giá ĐÓNG CỬA cuối kỳ vượt (≥ / ≤) mức đó
      • XS chạm    : % giai đoạn n phiên mà giá CAO/THẤP trong phiên CHẠM mức đó ít nhất 1 lần
      • [MỚI] XS chạm (trộn): trọng số ưu tiên giai đoạn gần đây – số dùng cho quyết định
    """
    ht = df.close.iloc[-1]
    gia_von = gia_von or ht
    ret = (df.close.shift(-n_phien) / df.close - 1).dropna() * 100
    ret1 = ret[ret.index >= df.index[-XS_CUA_SO]] if len(df) > XS_CUA_SO else ret

    ks = {ten: (p, "Mức % tham chiếu") for ten, p in KICH_BAN.items()}
    for ten, gia in them.items():
        if gia:
            ks[ten] = ((gia / ht - 1) * 100, Y_NGHIA_KB.get(ten, ""))

    rows = []
    for ten, (p, y_nghia) in sorted(ks.items(), key=lambda x: -x[1][0]):
        moi = ht * (1 + p / 100)
        xs = ((ret >= p) if p >= 0 else (ret <= p)).mean() * 100 if len(ret) else np.nan
        xs_cham, t_cham = _xs_cham_mot_phia(df, p, n_phien)
        xs1 = ((ret1 >= p) if p >= 0 else (ret1 <= p)).mean() * 100 if len(ret1) >= 20 else np.nan
        xs_cham1, _ = _xs_cham_mot_phia(df, p, n_phien, XS_CUA_SO)
        xs_tron, _ = _xs_cham_mot_phia(df, p, n_phien, tron=True)
        rows.append([ten, y_nghia, p, moi, xs, xs_cham, xs1, xs_cham1, xs_tron, t_cham,
                     (moi - gia_von) * so_cp * 1000, (moi / gia_von - 1) * 100])
    return pd.DataFrame(rows, columns=["Kịch bản", "Ý nghĩa", "% thay đổi", "Giá mới",
                                       f"XS đóng cửa sau {n_phien} phiên %", f"XS chạm trong {n_phien} phiên %",
                                       "XS đóng cửa – 1 năm %", "XS chạm – 1 năm %", "XS chạm – trộn %",
                                       "Số phiên TB để chạm", "Lãi/Lỗ (đồng)", "% so giá vốn"])


def mat_na_tin_hieu(d_ngay, d_tuan, so_nen=None):
    """
    Phiên quá khứ có TÍN HIỆU VÀO LỆNH giống quy tắc của công cụ (không nhìn trước):
      MACD TUẦN (tuần đã đóng) > Signal  VÀ  trong `so_nen` phiên gần nhất MACD ngày cắt lên Signal / cắt lên 0
      hoặc giá đóng cửa phá đỉnh 5 phiên trước đó.
    """
    so_nen = so_nen or SO_NEN_GAN["Ngày"]
    tuan_ok = (d_tuan.MACD > d_tuan.SIGNAL).astype(float).reindex(d_ngay.index, method="ffill").fillna(0).values > 0
    m, s, c = d_ngay.MACD.values, d_ngay.SIGNAL.values, d_ngay.close.values
    cat = np.r_[False, ((m[1:] > s[1:]) & (m[:-1] <= s[:-1])) | ((m[1:] > 0) & (m[:-1] <= 0))]
    dinh5 = pd.Series(d_ngay.high.values).shift(1).rolling(5).max().values
    with np.errstate(invalid="ignore"):
        pha = c > dinh5
    gan = pd.Series(cat | pha).rolling(so_nen, min_periods=1).max().values > 0
    return tuan_ok & gan


def trang_thai_tuong_tu(d_ngay, d_tuan):
    """
    Mặt nạ các phiên quá khứ có TRẠNG THÁI TƯƠNG TỰ hiện tại (để tính xác suất / EV CÓ ĐIỀU KIỆN):
      • [MỚI] Cùng trạng thái TÍN HIỆU VÀO LỆNH (mat_na_tin_hieu) – điều kiện quan trọng nhất, giữ đến cuối
      • MACD tuần (tuần gần nhất đã đóng cửa) cùng phía mốc 0 với hiện tại
      • MACD ngày cùng phía đường Signal
      • RSI ngày cùng nhóm (< 35 | 35–65 | > 65)
      • Cùng trạng thái 'gần đáy 1 năm' (giá ≤ đáy 252 phiên + 10%)
    Thiếu mẫu (< SO_MAU_DK_MIN) → nới lần lượt từ điều kiện cuối lên.
    Trả (mặt nạ, mô tả, có_tín_hiệu_hôm_nay).
    """
    mt = d_tuan.MACD.reindex(d_ngay.index, method="ffill")
    tin_hieu = mat_na_tin_hieu(d_ngay, d_tuan)
    tuan_am = (mt < 0).values
    ngay_tren = (d_ngay.MACD > d_ngay.SIGNAL).values
    rsi = d_ngay.RSI.values
    nhom_rsi = np.where(rsi < 35, 0, np.where(rsi > 65, 2, 1))
    day1n = d_ngay.low.rolling(252, min_periods=60).min()
    gan_day = (d_ngay.close <= day1n * 1.10).values
    L = -1
    dk = [("CÓ tín hiệu vào lệnh" if tin_hieu[L] else "KHÔNG có tín hiệu vào lệnh", tin_hieu == tin_hieu[L]),
          ("MACD tuần " + ("< 0" if tuan_am[L] else "≥ 0"), tuan_am == tuan_am[L]),
          ("MACD ngày " + ("> Signal" if ngay_tren[L] else "≤ Signal"), ngay_tren == ngay_tren[L]),
          (f"RSI ngày nhóm {['< 35', '35–65', '> 65'][nhom_rsi[L]]}", nhom_rsi == nhom_rsi[L]),
          ("gần đáy 1 năm" if gan_day[L] else "không gần đáy 1 năm", gan_day == gan_day[L])]
    hop_le = ~np.isnan(mt.values)
    for k in range(len(dk), 0, -1):
        m = hop_le.copy()
        for _, v in dk[:k]:
            m &= v
        if m[:-1].sum() >= SO_MAU_DK_MIN * 3:
            return m, " & ".join(t for t, _ in dk[:k]), bool(tin_hieu[L])
    return None, "không đủ mẫu", bool(tin_hieu[L])


def kich_ban_chinh(df_ngay, kq, ht, stop, mt_chinh, mt_nhap, so_cp, gia_von, n_phien, dk=None, wf=None, nhom=None):
    """
    D2 – 3 KỊCH BẢN CHÍNH loại trừ lẫn nhau:
      TÍCH CỰC : chạm mục tiêu trung hạn TRƯỚC khi chạm cắt lỗ   ([SỬA] mục tiêu luôn > mốc breakout)
      CƠ SỞ    : không chạm cả hai (đạt MT cơ sở / đi ngang)
      TIÊU CỰC : chạm cắt lỗ TRƯỚC  ([SỬA] giá đích = hỗ trợ kế tiếp / biên 1σ EWMA, không lấy đáy nhiều năm trước)
    Xác suất = tần suất lịch sử: toàn bộ | 1 năm | TRỘN (ưu tiên gần đây) | CÓ ĐIỀU KIỆN (trạng thái tương tự).
    EV dùng để quyết định = min(EV trộn, EV có điều kiện nếu đủ mẫu) – nguyên tắc thận trọng.
    """
    gia_von_ = gia_von or ht
    d = kq["Ngày"]["df"]
    L = d.iloc[-1]
    atr = float(L.ATR)
    xh, pv = kq["Ngày"]["xh"], kq["Ngày"]["pv"]
    pvx = pv[pv.xac_nhan]
    cat_lo = stop["gia"]
    sigma = np.log(df_ngay.close).diff().tail(252).std()
    s_ewma = sigma_ewma(df_ngay.close)
    bd = s_ewma * np.sqrt(n_phien) * 100                       # 1σ (EWMA) trong n phiên, %

    # Mốc breakout (kháng cự): đường kháng cự hợp lệ → đỉnh xác nhận gần nhất phía trên → +1σ
    kc_l = _duong(xh, "khang_cu")
    dinh_tren = pvx[(pvx.loai == "Đỉnh") & (pvx.gia > ht * 1.005)]
    if kc_l and kc_l["gia_nay"] > ht * 1.005:
        kc, nguon_kc = kc_l["gia_nay"], "đường kháng cự ngày"
    elif len(dinh_tren):
        kc, nguon_kc = dinh_tren.gia.min(), "đỉnh ngày xác nhận gần nhất"
    else:
        kc, nguon_kc = ht * (1 + bd / 100), "giá + 1σ EWMA"
    # Hỗ trợ: đường hỗ trợ hợp lệ / đáy xác nhận nằm giữa cắt lỗ và giá
    ht_l = _duong(xh, "ho_tro")
    day_giua = pvx[(pvx.loai == "Đáy") & (pvx.gia < ht) & (pvx.gia > cat_lo)]
    hotro_that = True
    if ht_l and cat_lo < ht_l["gia_nay"] < ht:
        hotro = ht_l["gia_nay"]
    elif len(day_giua):
        hotro = day_giua.gia.max()
    else:
        hotro, hotro_that = cat_lo + BUFFER_ATR * atr, False     # không có hỗ trợ xác nhận giữa cắt lỗ và giá
    hotro = min(hotro, ht * 0.999)

    bang_ngay = kq["Ngày"]["mt"]["bang"]
    nguong_cs = ht * (1 + max(3.0, 0.5 * bd) / 100)
    ds_cs = sorted(x for x in [mt_chinh.get("Ngày")] + list(bang_ngay["Giá mục tiêu"]) if x and x >= nguong_cs)
    mt_cs = (mt_chinh["Ngày"] if mt_chinh.get("Ngày") in ds_cs else (ds_cs[0] if ds_cs else nguong_cs))
    # MT tích cực phải > mốc breakout và > MT cơ sở
    san_tc = max(mt_cs, kc) * 1.02
    ung_vien_tc = [x for x in (mt_chinh.get("Tuần"), mt_nhap) if x and x > san_tc]
    for b in (bang_ngay, kq["Tuần"]["mt"]["bang"]):
        ung_vien_tc += [x for x in b["Giá mục tiêu"] if x > san_tc]
    if mt_chinh.get("Tuần") in ung_vien_tc:
        mt_tc, nguon_tc = mt_chinh["Tuần"], "MT trung hạn khung tuần"
    elif ung_vien_tc:
        mt_tc, nguon_tc = min(ung_vien_tc), "mốc kỹ thuật gần nhất trên breakout"
    else:
        mt_tc = kc + max(kc - hotro, 2 * atr)
        nguon_tc = "đo độ rộng vùng: kháng cự + (kháng cự − hỗ trợ)"
    if mt_cs >= mt_tc:
        mt_cs = (ht + mt_tc) / 2

    # Giá đích kịch bản tiêu cực: hỗ trợ xác nhận kế tiếp dưới cắt lỗ, nhưng không sâu hơn biên −1σ EWMA
    day_duoi = pvx[(pvx.loai == "Đáy") & (pvx.gia < cat_lo * 0.995)]
    bien_vol = min(ht * np.exp(-s_ewma * np.sqrt(n_phien)), cat_lo - atr)
    if len(day_duoi) and day_duoi.gia.max() >= bien_vol:
        gia_tieu_cuc, nguon_tieu_cuc = day_duoi.gia.max(), "đáy ngày xác nhận kế tiếp"
    else:
        gia_tieu_cuc, nguon_tieu_cuc = bien_vol, f"biên −1σ EWMA {n_phien} phiên / cắt lỗ − 1×ATR"

    p = lambda g: (g / ht - 1) * 100
    r_thoat = {"tren": p(mt_tc), "giua": p(mt_cs), "duoi": p(cat_lo)}
    sim = _mo_phong(df_ngay, n_phien, tren=p(mt_tc), duoi=p(cat_lo), giua=p(mt_cs))
    tong = len(df_ngay)
    rong = {k: np.nan for k in ("tren", "giua", "ngang", "duoi", "t_tren", "t_giua", "t_ngang", "t_duoi",
                                "r_ngang", "ev", "n_hieu_dung")}
    rong.update(so_mau=0, tin_cay_thap=True)
    ms = {}
    for kieu in ("all", "1y", "tron", "dk"):
        if kieu == "dk" and (dk is None or dk[0] is None):
            ms[kieu] = dict(rong)
            continue
        r = _tong_hop(sim, r_thoat, kieu, mask=dk[0] if kieu == "dk" else None, tong=tong, n=n_phien)
        ms[kieu] = r if r is not None else dict(rong)

    vol20 = L.VolMA20 if not np.isnan(L.VolMA20) else df_ngay.volume.tail(20).mean()
    lai = lambda g: (g - gia_von_) * so_cp * 1000
    g_ngang = ht * (1 + (ms["tron"]["r_ngang"] if ms["tron"]["r_ngang"] == ms["tron"]["r_ngang"] else 0) / 100)

    kb = [
        {"Kịch bản": "TÍCH CỰC", "k": "tren", "Giá mục tiêu": mt_tc,
         "Điều kiện kích hoạt": f"Đóng cửa vượt {nguon_kc} {kc:,.2f} với KL ≥ 1.5× TB20 (≈ {1.5 * vol20:,.0f} CP)",
         "Tín hiệu xác nhận": "MACD ngày > Signal và > 0; MACD tuần trên Signal; RSI ngày 55–70; OBV lập đỉnh mới",
         "Đang nắm giữ": f"Giữ; dời cắt lỗ lên {max(kc - atr, cat_lo):,.2f}; chốt 1/3 tại {mt_cs:,.2f}, "
                         f"phần còn lại tại {mt_tc:,.2f}",
         "Chưa có cổ phiếu": f"Mua khi breakout {kc:,.2f} được xác nhận, hoặc canh nhịp kéo ngược về {kc:,.2f}",
         "Ghi chú mốc": f"MT = {nguon_tc} (luôn > mốc breakout {kc:,.2f})"},
        {"Kịch bản": "CƠ SỞ – đạt MT cơ sở", "k": "giua", "Giá mục tiêu": mt_cs,
         "Điều kiện kích hoạt": f"Giá giữ trên hỗ trợ {hotro:,.2f}, hồi lên {mt_cs:,.2f} nhưng chưa tới MT tích cực",
         "Tín hiệu xác nhận": "MACD ngày cắt lên Signal; KL quanh TB20; RSI 45–60",
         "Đang nắm giữ": f"Chốt lời từng phần quanh {mt_cs:,.2f}; giữ cắt lỗ {cat_lo:,.2f}",
         "Chưa có cổ phiếu": (f"Mua gần hỗ trợ {hotro:,.2f} – {hotro * 1.03:,.2f} KHI có xác nhận đảo chiều"
                              if hotro_that else "Chưa có hỗ trợ xác nhận gần giá → chờ nhịp chỉnh tạo đáy mới"),
         "Ghi chú mốc": "MT ngắn hạn khung ngày"},
        {"Kịch bản": "CƠ SỞ – đi ngang", "k": "ngang", "Giá mục tiêu": g_ngang,
         "Điều kiện kích hoạt": f"Giá dao động trong hộp {cat_lo:,.2f} – {mt_cs:,.2f} suốt {n_phien} phiên",
         "Tín hiệu xác nhận": "MACD ngày quanh 0, Histogram nhỏ; KL thấp hơn TB20",
         "Đang nắm giữ": "Giữ, không gia tăng; xem lại sau mỗi tuần",
         "Chưa có cổ phiếu": "Đứng ngoài hoặc mua tỷ trọng nhỏ ở đáy hộp",
         "Ghi chú mốc": "lợi suất bình quân (trộn) của nhóm đi ngang"},
        {"Kịch bản": "TIÊU CỰC", "k": "duoi", "Giá mục tiêu": gia_tieu_cuc,
         "Điều kiện kích hoạt": f"Đóng cửa dưới cắt lỗ {cat_lo:,.2f}" + (f" (thủng hỗ trợ {hotro:,.2f})" if hotro_that else ""),
         "Tín hiệu xác nhận": "MACD ngày cắt xuống Signal dưới 0; MACD tuần cắt xuống Signal; KL bán tăng",
         "Đang nắm giữ": f"BÁN tại {cat_lo:,.2f} ({p(cat_lo):+.1f}%); nếu không cắt lỗ, giá có thể về "
                         f"{gia_tieu_cuc:,.2f} ({p(gia_tieu_cuc):+.1f}%)",
         "Chưa có cổ phiếu": f"Đứng ngoài; chờ đáy mới quanh {gia_tieu_cuc:,.2f} + tín hiệu đảo chiều đã xác nhận",
         "Ghi chú mốc": f"giá đích = {nguon_tieu_cuc}; thời gian = số phiên trung vị tới khi chạm CẮT LỖ"},
    ]
    for r in kb:
        k = r["k"]
        r["% so giá hiện tại"] = p(r["Giá mục tiêu"])
        r["XS toàn bộ %"] = ms["all"][k]
        r["XS 1 năm %"] = ms["1y"][k]
        r["XS trộn %"] = ms["tron"][k]
        ci = ms["tron"].get(f"ci_{k}")
        r["KTC 90% (trộn)"] = f"{ci[0]:.0f}–{ci[1]:.0f}%" if ci else "–"
        r["XS có điều kiện %"] = ms["dk"][k]
        r["Số phiên trung vị"] = ms["tron"][f"t_{k}"] if k != "ngang" else float(n_phien)
        r["Lãi/Lỗ vị thế (đồng)"] = lai(cat_lo if k == "duoi" else r["Giá mục tiêu"])
    bang = pd.DataFrame(kb).drop(columns=["k"])
    cot_dau = ["Kịch bản", "Giá mục tiêu", "% so giá hiện tại", "XS toàn bộ %", "XS 1 năm %", "XS trộn %",
               "KTC 90% (trộn)", "XS có điều kiện %", "Số phiên trung vị"]
    bang = bang[cot_dau + [c for c in bang.columns if c not in cot_dau]]

    ev_tron, ev_dk = ms["tron"]["ev"], ms["dk"]["ev"]
    dk_du = ms["dk"]["so_mau"] and ms["dk"]["n_hieu_dung"] == ms["dk"]["n_hieu_dung"] \
        and ms["dk"]["n_hieu_dung"] >= 3
    # [MỚI] EV quyết định = (co về ngành) → min với có điều kiện → trừ thiên lệch chọn mục tiêu (walk-forward)
    gop, gop_ct = mo_phong_gop_nganh(nhom, df_ngay, ht, mt_tc, cat_lo, mt_cs, n_phien) if nhom else (None, [])
    ev_gop = gop["ev"] if gop else np.nan
    ev_co_so = (1 - TRONG_SO_GOP_NGANH) * ev_tron + TRONG_SO_GOP_NGANH * ev_gop if ev_gop == ev_gop else ev_tron
    # [SỬA] EV có điều kiện (cùng trạng thái TÍN HIỆU) là thước đo chính; co về EV cơ sở theo số mẫu hiệu dụng
    #       (ít mẫu → gần EV cơ sở). CACH_TINH_EV = "than_trong" → giữ cách cũ: min(cơ sở, có điều kiện).
    w_dk = 0.0
    if dk_du and ev_dk == ev_dk:
        if cfg.CACH_TINH_EV == "than_trong":
            ev_truoc = min(ev_co_so, ev_dk)
        else:
            nh = ms["dk"]["n_hieu_dung"]
            w_dk = nh / (nh + N_HIEU_DUNG_MIN)
            ev_truoc = w_dk * ev_dk + (1 - w_dk) * ev_co_so
    else:
        ev_truoc = ev_co_so
    loi_the = ev_dk - ev_tron if dk_du and ev_dk == ev_dk and ev_tron == ev_tron else np.nan
    lech_wf = wf["lech"] if wf else 0.0
    ev_qd = ev_truoc - lech_wf
    xs_cham_stop, t_cham_stop = _xs_cham_mot_phia(df_ngay, p(cat_lo), n_phien, tron=True)

    if ht >= kc:
        hien_tai = "TÍCH CỰC (giá đã vượt mốc breakout)"
    elif ht <= hotro * 1.005:
        hien_tai = "TIÊU CỰC (giá đang ở/dưới hỗ trợ ngày)"
    elif L.MACD > L.SIGNAL:
        hien_tai = "CƠ SỞ, nghiêng TÍCH CỰC (MACD ngày trên Signal)"
    else:
        hien_tai = "CƠ SỞ, nghiêng TIÊU CỰC (MACD ngày dưới Signal)"

    # [MỚI] Thống kê nghiêng về kịch bản nào (xác suất TRỘN) – tách bạch với đà kỹ thuật ở trên
    xs = ms["tron"]
    xs_cs = sum(x for x in (xs.get("giua"), xs.get("ngang")) if x == x and x is not None)
    nhom_xs = [("TÍCH CỰC", xs.get("tren")), ("CƠ SỞ", xs_cs), ("TIÊU CỰC", xs.get("duoi"))]
    nhom_xs = [(t, x) for t, x in nhom_xs if x is not None and x == x]
    thong_ke = ""
    canh_bao_kb = []
    if nhom_xs:
        ten_max, x_max = max(nhom_xs, key=lambda t: t[1])
        chi_tiet = {"TÍCH CỰC": f"chạm {mt_tc:,.2f} ({p(mt_tc):+.1f}%) trước khi chạm cắt lỗ",
                    "CƠ SỞ": f"không chạm cắt lỗ lẫn MT tích cực (dao động {cat_lo:,.2f} – {mt_tc:,.2f})",
                    "TIÊU CỰC": f"chạm cắt lỗ {cat_lo:,.2f} ({p(cat_lo):+.1f}%) trước khi lên {mt_tc:,.2f} "
                                f"({p(mt_tc):+.1f}%)"}[ten_max]
        thong_ke = f"nghiêng {ten_max} – {x_max:.0f}% {chi_tiet}"
        x_duoi = xs.get("duoi")
        if x_duoi is not None and x_duoi == x_duoi and x_duoi >= 50 and abs(p(cat_lo)) < bd:
            canh_bao_kb.append(
                f"Cắt lỗ chỉ cách giá {abs(p(cat_lo)):.1f}% – nhỏ hơn biến động thường thấy trong {n_phien} phiên "
                f"(±{bd:.1f}%) → dễ bị quét; cân nhắc nới cắt lỗ / giảm khối lượng, hoặc chờ giá về gần hỗ trợ "
                f"{hotro:,.2f} rồi mới mua")
        if ten_max == "TIÊU CỰC" and "TÍCH CỰC" in hien_tai:
            canh_bao_kb.append("Đà kỹ thuật ngắn hạn tốt nhưng thống kê bất lợi → ưu tiên quản trị rủi ro hơn "
                               "là mua đuổi")

    # D3 – biên độ: σ phẳng 1 năm, σ EWMA, phân vị thực nghiệm lợi suất n phiên (trọng số gần đây)
    rn = np.log(df_ngay.close.shift(-n_phien) / df_ngay.close).dropna().values
    wn = _trong_so_gan_day(len(rn), tong)
    pv_tn = {q: np.exp(_phan_vi_trong_so(rn, wn, q)) for q in (2.5, 16, 84, 97.5)} if len(rn) > 60 else {}
    rows = []
    for ten, s in ((f"σ phẳng 1 năm ({sigma * np.sqrt(252) * 100:.1f}%/năm)", sigma),
                   (f"σ EWMA λ={EWMA_LAMBDA} ({s_ewma * np.sqrt(252) * 100:.1f}%/năm) – DÙNG", s_ewma)):
        rows.append([ten + " – 68%", ht * np.exp(-s * np.sqrt(n_phien)), ht * np.exp(s * np.sqrt(n_phien))])
        rows.append([ten + " – 95%", ht * np.exp(-1.96 * s * np.sqrt(n_phien)), ht * np.exp(1.96 * s * np.sqrt(n_phien))])
    if pv_tn:
        rows.append(["Phân vị thực nghiệm (trộn) – 68%", ht * pv_tn[16], ht * pv_tn[84]])
        rows.append(["Phân vị thực nghiệm (trộn) – 95%", ht * pv_tn[2.5], ht * pv_tn[97.5]])
    bien_do = pd.DataFrame(rows, columns=["Phương pháp – độ tin cậy", "Cận dưới", "Cận trên"])
    bien_do["Cận dưới %"] = (bien_do["Cận dưới"] / ht - 1) * 100
    bien_do["Cận trên %"] = (bien_do["Cận trên"] / ht - 1) * 100

    return {"bang": bang, "ms": ms, "ev": ms["all"]["ev"], "ev1": ms["1y"]["ev"], "ev_tron": ev_tron,
            "ev_dk": ev_dk, "ev_qd": ev_qd, "ev_gop": ev_gop, "gop": gop, "gop_ct": gop_ct, "ev_co_so": ev_co_so,
            "ev_truoc_wf": ev_truoc, "lech_wf": lech_wf, "w_dk": w_dk, "loi_the_tin_hieu": loi_the,
            "co_tin_hieu": bool(dk[2]) if dk and len(dk) > 2 else None, "dk_mo_ta": dk[1] if dk else "—", "dk_du": bool(dk_du),
            "p_thang": ms["tron"]["tren"] + ms["tron"]["giua"] if ms["tron"]["so_mau"] else np.nan,
            "hien_tai": hien_tai, "thong_ke": thong_ke, "canh_bao_kb": canh_bao_kb, "n_phien": n_phien,
            "bien_do": bien_do, "sigma_nam": sigma * np.sqrt(252) * 100,
            "sigma_ewma_nam": s_ewma * np.sqrt(252) * 100, "kc": kc, "hotro": hotro, "cat_lo": cat_lo,
            "mt_cs": mt_cs, "mt_tc": mt_tc, "gia_tc": gia_tieu_cuc, "hotro_that": hotro_that, "so_mau": ms["all"]["so_mau"],
            "so_mau1": ms["1y"]["so_mau"], "n": n_phien, "xs_cham_stop": xs_cham_stop, "t_cham_stop": t_cham_stop,
            "rr": (mt_tc - ht) / (ht - cat_lo) if ht > cat_lo else np.nan,
            "do_lech_ngay": float(df_ngay.close.pct_change().tail(252).std() * 100)}
