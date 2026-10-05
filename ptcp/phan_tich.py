# -*- coding: utf-8 -*-
"""Cắt lỗ thống nhất, mục tiêu, kịch bản, đề xuất mục tiêu, quản trị rủi ro, hàm quyết định duy nhất."""
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
    SO_MUC_TIEU, SO_PHIEN_SU_KIEN, STOP_ATR_MAX, STOP_ATR_MIN, TRONG_SO_GOP_NGANH, TRONG_SO_KHUNG,
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


def ctck_gan_nhat(symbol, so_thang=12):
    """Giá mục tiêu MỚI NHẤT của mỗi CTCK trong 'so_thang' tháng gần đây → dùng làm đồng thuận."""
    d = DU_LIEU_CTCK.get(symbol)
    if not d:
        return {}
    moc = pd.Timestamp(date.today()) - pd.DateOffset(months=so_thang)
    kq = {}
    for ngay, ct, kn, mt, gia, ten in d["bao_cao"]:
        t = pd.to_datetime(ngay, dayfirst=True)
        if mt and t >= moc and (ct not in kq or t >= kq[ct][0]):
            kq[ct] = (t, mt, kn)
    return kq


def bang_bao_cao_ctck(symbol, ht):
    d = DU_LIEU_CTCK.get(symbol)
    if not d:
        return None
    rows = []
    for ngay, ct, kn, mt, gia, ten in d["bao_cao"]:
        rows.append([ngay, ct, kn, mt, gia, (mt / gia - 1) * 100 if mt and gia else np.nan,
                     (mt / ht - 1) * 100 if mt else np.nan, ten])
    return pd.DataFrame(rows, columns=["Ngày", "CTCK", "Khuyến nghị", "Giá MT", "Giá lúc công bố",
                                       "Upside lúc công bố %", "Upside so giá hiện tại %", "Báo cáo"])


def tinh_cat_lo(d_ngay, pv_ngay, ht):
    """
    [MỚI] CẮT LỖ THỐNG NHẤT – một quy tắc duy nhất dùng cho phần C, D, E và khuyến nghị cuối:
      cắt lỗ = max(đáy ngày ĐÃ XÁC NHẬN gần nhất dưới giá − 0.5×ATR ; giá − 2×ATR ; giá × (1 − 7%))
      khoảng cách < 1.5×ATR → nới ra giá − 1.5×ATR (tránh bị nhiễu quét).
    """
    atr = float(d_ngay.ATR.iloc[-1])
    day_xn = pv_ngay[(pv_ngay.loai == "Đáy") & pv_ngay.xac_nhan & (pv_ngay.gia < ht)]
    lo_day = day_xn.gia.iloc[-1] - BUFFER_ATR * atr if len(day_xn) else np.nan
    lo_atr = ht - STOP_ATR_MAX * atr
    lo_cung = ht * (1 - LO_CUNG_PCT / 100)
    ung = [x for x in (lo_day, lo_atr) if x == x]
    gia = max(max(ung), lo_cung)
    tp = "đáy ngày − 0.5×ATR" if (lo_day == lo_day and gia == lo_day) else (
        f"giá − {STOP_ATR_MAX:g}×ATR" if gia == lo_atr else f"cắt lỗ cứng −{LO_CUNG_PCT:g}%")
    canh_bao = []
    if ht - gia < STOP_ATR_MIN * atr:
        gia = ht - STOP_ATR_MIN * atr
        tp = f"nới ra giá − {STOP_ATR_MIN:g}×ATR (mốc kỹ thuật quá sát)"
        if gia < lo_cung:
            canh_bao.append(f"Biến động cao: {STOP_ATR_MIN:g}×ATR = {(ht - gia) / ht * 100:.1f}% > cắt lỗ cứng "
                            f"{LO_CUNG_PCT:g}% → cần giảm khối lượng.")
    return {"gia": gia, "pct": (gia / ht - 1) * 100, "atr": atr, "lo_day": lo_day, "lo_atr": lo_atr,
            "lo_cung": lo_cung, "theo": tp, "canh_bao": canh_bao,
            "quy_tac": (f"max(đáy ngày xác nhận − {BUFFER_ATR:g}×ATR; giá − {STOP_ATR_MAX:g}×ATR; "
                        f"giá −{LO_CUNG_PCT:g}%), tối thiểu {STOP_ATR_MIN:g}×ATR")}


# ==========================================================================
# 5. GIÁ MỤC TIÊU THEO TỪNG KHUNG
# ==========================================================================
SO_NEN_GIA = {"Ngày": 40, "Tuần": 20, "Giờ": 60}     # số nến xét nền giá (measured move)
DO_RONG_NEN_MAX = 20.0                               # % – nền giá hẹp hơn mức này mới coi là nền tích luỹ


def _ung_vien_bo_sung(df, pvx, ten_khung, ht):
    """
    [MỚI] Quy tắc kỹ thuật bổ sung tạo mục tiêu (chỉ lấy mức > giá hiện tại 0.5%):
      1. Fibo HỒI PHỤC 0.382 / 0.5 / 0.618 của nhịp giảm gần nhất (đỉnh xác nhận → đáy thấp nhất sau đó), khi giá
         đang dưới đỉnh đó – mục tiêu cho nhịp hồi trong/xuất phát từ xu hướng giảm.
      2. Đo biên độ NỀN GIÁ: nền tích luỹ (biên độ ≤ 20%) trong 40 phiên / 20 tuần trước đó → mục tiêu = đỉnh nền
         + chiều cao nền (chỉ khi giá đã vượt nửa trên của nền).
      3. MA50 / MA200 (khung ngày) đang nằm TRÊN giá → kháng cự động.
      4. Vùng giá trị khối lượng (khung ngày, 120 phiên): VAH và POC nằm trên giá → vùng cung lớn.
      5. Đỉnh 52 tuần (khung ngày) nằm trên giá.
    """
    out = []
    # 1. Fibo hồi phục của nhịp giảm gần nhất
    dinh = pvx[pvx.loai == "Đỉnh"]
    if len(dinh):
        P = dinh.iloc[-1]
        sau = df[df.index >= P.time]
        if len(sau) > 2:
            day_min = float(sau.close.min() if DINH_DAY_THEO == "close" else sau.low.min())
            if P.gia > day_min * 1.05 and ht < P.gia:
                for k in (0.382, 0.5, 0.618):
                    g = day_min + k * (P.gia - day_min)
                    if g > ht * 1.005:
                        out.append([f"Fibo hồi phục {k:g} (nhịp {P.gia:,.2f} → {day_min:,.2f})", g])
    # 2. Đo biên độ nền giá
    n = SO_NEN_GIA.get(ten_khung, 40)
    if len(df) > n + 5:
        nen = df.close.iloc[-n - 5:-5]
        dinh_nen, day_nen = float(nen.max()), float(nen.min())
        cao = dinh_nen - day_nen
        if day_nen > 0 and cao / day_nen * 100 <= DO_RONG_NEN_MAX and ht >= day_nen + 0.5 * cao:
            g = dinh_nen + cao
            if g > ht * 1.005:
                out.append([f"Đo biên độ nền giá {day_nen:,.2f}–{dinh_nen:,.2f} ({n} {ten_khung.lower()})", g])
    if ten_khung == "Ngày":
        # 3. MA50 / MA200 phía trên
        for ma in ("MA50", "MA200"):
            if ma in df and df[ma].iloc[-1] == df[ma].iloc[-1] and df[ma].iloc[-1] > ht * 1.005:
                out.append([f"{ma} phía trên giá (kháng cự động)", float(df[ma].iloc[-1])])
        # 4. Vùng giá trị khối lượng
        try:
            from .bo_sung import phan_tich_khoi_luong
            kl = phan_tich_khoi_luong(df)
            for ten, g in (("POC – vùng khớp nhiều nhất", kl["poc"]), ("VAH – cạnh trên vùng giá trị KL", kl["vah"])):
                if g > ht * 1.005:
                    out.append([f"{ten} (120 phiên)", float(g)])
        except Exception:
            pass
        # 5. Đỉnh 52 tuần
        d52 = df[df.index > df.index[-1] - pd.Timedelta(weeks=52)]
        cao52 = float(d52.close.max() if DINH_DAY_THEO == "close" else d52.high.max())
        if cao52 > ht * 1.005:
            out.append(["Đỉnh 52 tuần", cao52])
    return out


def tinh_muc_tieu(df, pv, xh, ten_khung, df_ngay, stop, H):
    """
    Ứng viên: đỉnh cũ đã xác nhận, đường kháng cự (nếu đủ gần), AB=CD / Fibo 1.272 / 1.618 từ đỉnh/đáy xác nhận.
    [MỚI] Bổ sung quy tắc kỹ thuật (xem _ung_vien_bo_sung): Fibo HỒI PHỤC 0.382/0.5/0.618 của nhịp giảm gần nhất,
          đo biên độ NỀN GIÁ (measured move), MA50/MA200 phía trên giá, vùng giá trị khối lượng (VAH/POC),
          đỉnh 52 tuần. Mọi ứng viên vẫn được chấm CHUNG một cách (XS chạm trước cắt lỗ, EV) và chọn như cũ.
    [SỬA] Mỗi mục tiêu được chấm bằng mô phỏng lịch sử trên dữ liệu NGÀY trong H phiên với CẮT LỖ THỐNG NHẤT:
          XS chạm trước cắt lỗ (trộn), số phiên trung vị, EV = XS × lãi − XS cắt lỗ × lỗ + đi ngang (sau phí).
          Chỉ giữ SO_MUC_TIEU = 3 mục tiêu EV cao nhất; mục tiêu chính = EV cao nhất trong các mốc có
          upside ≥ 3% VÀ XS chạm trước cắt lỗ ≥ XS_TOI_THIEU_MT (khả thi), nếu không có thì mốc XS cao nhất.
    """
    ht = df.close.iloc[-1]
    pvx = pv[pv.xac_nhan]
    ung_vien = []

    dinh_tren = pvx[(pvx.loai == "Đỉnh") & (pvx.gia > ht * 1.005)].sort_values("gia")
    da_lay = []
    for _, r in dinh_tren.iterrows():
        if da_lay and r.gia < da_lay[-1] * 1.02:
            continue
        da_lay.append(r.gia)
        ung_vien.append([f"Đỉnh cũ {r.time:%d/%m/%Y}", r.gia])
        if len(da_lay) == 4:
            break

    kc = _duong(xh, "khang_cu")
    if kc and kc["gia_nay"] > ht * 1.005:
        ung_vien.append([f"Đường kháng cự ({kc['so_cham']} lần chạm)", kc["gia_nay"]])

    co_song = None
    loai = pvx.loai.tolist()
    for i in range(len(pvx) - 1, 1, -1):
        if loai[i] == "Đáy" and loai[i - 1] == "Đỉnh" and loai[i - 2] == "Đáy":
            T0, P0, T1 = pvx.gia.iloc[i - 2], pvx.gia.iloc[i - 1], pvx.gia.iloc[i]
            if P0 > T0:
                co_song = (T0, P0, T1)
                for k, ten in ((1.0, "Sóng tương đương AB=CD"), (1.272, "Fibo mở rộng 1.272"),
                               (1.618, "Fibo mở rộng 1.618")):
                    g = T1 + k * (P0 - T0)
                    if g > ht * 1.005:
                        ung_vien.append([ten, g])
            break
    ung_vien += _ung_vien_bo_sung(df, pvx, ten_khung, ht)
    if not ung_vien:
        ung_vien.append([f"Biến động: giá + 3×ATR {ten_khung.lower()}", ht + 3 * float(df.ATR.iloc[-1])])

    bang = pd.DataFrame(ung_vien, columns=["Phương pháp", "Giá mục tiêu"]).sort_values("Giá mục tiêu")
    bang = bang[~(bang["Giá mục tiêu"].pct_change().abs() < 0.005)].reset_index(drop=True)
    bang["Upside %"] = (bang["Giá mục tiêu"] / ht - 1) * 100
    g_stop = stop["gia"]
    dg = [danh_gia_muc(df_ngay, ht, g, g_stop, H) for g in bang["Giá mục tiêu"]]
    bang[f"XS chạm trước cắt lỗ ({H} phiên) %"] = [x[0] for x in dg]
    bang["Số phiên trung vị"] = [x[1] for x in dg]
    bang["EV %"] = [x[2] for x in dg]
    bang["R/R"] = (bang["Giá mục tiêu"] - ht) / (ht - g_stop) if ht > g_stop else np.nan
    bang.insert(0, "Khung", ten_khung)

    cot_xs = f"XS chạm trước cắt lỗ ({H} phiên) %"
    du_xa = bang[bang["Upside %"] >= UPSIDE_TOI_THIEU]
    kha_thi = du_xa[du_xa[cot_xs] >= XS_TOI_THIEU_MT]
    if len(kha_thi):
        chinh = kha_thi.loc[kha_thi["EV %"].fillna(-1e9).idxmax()]
        cach_chon = f"EV cao nhất trong các mốc có XS ≥ {XS_TOI_THIEU_MT:g}%"
    elif len(du_xa):
        chinh = du_xa.loc[du_xa[cot_xs].fillna(-1).idxmax()]
        cach_chon = f"không mốc nào đạt XS ≥ {XS_TOI_THIEU_MT:g}% → chọn mốc XS cao nhất"
    else:
        chinh = bang.iloc[0] if len(bang) else None
        cach_chon = "mốc gần nhất"
    # 3 mốc hiển thị: ưu tiên mốc KHẢ THI (XS ≥ ngưỡng) rồi EV; luôn gồm mục tiêu chính
    thu_tu = bang.assign(_kt=bang[cot_xs].fillna(0) >= XS_TOI_THIEU_MT, _ev=bang["EV %"].fillna(-1e9)) \
        .sort_values(["_kt", "_ev"], ascending=False).index.tolist()
    if chinh is not None and chinh.name in thu_tu:
        thu_tu.remove(chinh.name)
        thu_tu.insert(0, chinh.name)
    top = bang.loc[thu_tu[:SO_MUC_TIEU]].sort_values("Giá mục tiêu")
    return {"bang": bang, "top": top, "chinh": chinh, "song": co_song, "H": H, "cach_chon": cach_chon,
            "rr": ((chinh["Giá mục tiêu"] - ht) / (ht - g_stop)) if chinh is not None and ht > g_stop else np.nan}


def vung_hoi_tu(bang_ngay, bang_tuan):
    """Tìm các mục tiêu ngày & tuần lệch nhau ≤ NGUONG_HOI_TU %."""
    kq = []
    if bang_ngay is None or bang_tuan is None or not len(bang_ngay) or not len(bang_tuan):
        return kq
    for _, a in bang_ngay.iterrows():
        for _, b in bang_tuan.iterrows():
            lech = abs(a["Giá mục tiêu"] / b["Giá mục tiêu"] - 1) * 100
            if lech <= NGUONG_HOI_TU:
                kq.append((min(a["Giá mục tiêu"], b["Giá mục tiêu"]),
                           max(a["Giá mục tiêu"], b["Giá mục tiêu"]),
                           a["Phương pháp"], b["Phương pháp"]))
    return kq


def ket_luan_mua(kq):
    """
    Trạng thái 3 khung theo nguyên tắc: Tuần định hướng (QUYỀN PHỦ QUYẾT) → Ngày tìm vùng mua → Giờ điểm vào.
    [SỬA] Chỉ trả về trạng thái; khuyến nghị cuối được quyết định DUY NHẤT bởi quyet_dinh_cuoi().
    """
    L_t = kq["Tuần"]["df"].iloc[-1]
    tuan_ok = bool(L_t.MACD > L_t.SIGNAL)
    co_ngay = kq["Ngày"]["co"]
    ngay_ok = bool(kq["Ngày"]["diem"] >= 2 and not co_ngay["thung_ho_tro"]
                   and (co_ngay["xac_nhan_dao_chieu"] or not co_ngay["xu_huong_giam"]))
    co_gio = kq["Giờ"]["co"] if "Giờ" in kq else None
    gio_ok = None if co_gio is None else bool(co_gio["cat_len_signal"] or co_gio["cat_len_0"]
                                              or co_gio["pha_khang_cu"] or co_gio["pha_dinh_nho"])
    tong_ts = sum(TRONG_SO_KHUNG[k] for k in kq)
    diem_ts = sum(TRONG_SO_KHUNG[k] * kq[k]["diem"] for k in kq) / tong_ts
    return {"tuan_ok": tuan_ok, "tuan_rat_tot": tuan_ok and L_t.MACD > 0, "ngay_ok": ngay_ok,
            "gio_ok": gio_ok, "diem_trong_so": diem_ts}


def quyet_dinh_cuoi(tg, kb, qr, dx, ht, stop, ttr=None):
    """
    [MỚI] HÀM QUYẾT ĐỊNH DUY NHẤT – mọi phần khác (tóm tắt, phần C, thông tin giao dịch, Excel, HTML) chỉ đọc
    kết quả này. Thứ tự kiểm tra (điều kiện trước có quyền phủ quyết điều kiện sau):
      1. Mục tiêu đề xuất ≤ giá  → KHÔNG MUA MỚI
      2. Tuần MACD ≤ Signal       → CHƯA MUA (đúng quy tắc vào lệnh của chính công cụ)
      3. EV (sau phí) < EV_NGUONG → CHƯA MUA (không có lợi thế thống kê)
      4. Ngày chưa có điểm mua    → THEO DÕI
      5. R/R < RR_NGUONG          → CHỜ GIÁ TỐT HƠN (chỉ mua ≤ giá R/R 2)
      6. Giờ chưa có tín hiệu     → CHỜ ĐIỂM VÀO  (không có dữ liệu giờ → MUA TỪNG PHẦN)
      7. Đạt tất cả               → MUA
    [MỚI] Sau đó điều chỉnh theo bối cảnh (danh_gia_thi_truong):
      8. Sự kiện (KQKD/GDKHQ) trong 5 phiên → CHỜ SAU SỰ KIỆN
      9. VN-Index xấu VÀ RS ở đáy 1 năm     → THEO DÕI
     10. Một trong hai xấu                  → MUA TỪNG PHẦN (khối lượng × hệ số)
    """
    ttr = ttr or {"vni_xau": False, "rs_yeu": False, "chan": False, "su_kien": [], "he_so": 1.0,
                  "co_vni": False, "co_rs": False}
    ev, rr = kb["ev_qd"], qr["rr"]
    ok_ev = bool(ev == ev and ev >= EV_NGUONG)
    ok_rr = bool(rr == rr and rr >= RR_NGUONG)
    kiem_tra = [
        ("Tuần: MACD > Signal (quyền phủ quyết)", tg["tuan_ok"]),
        (f"Lợi suất kỳ vọng sau phí ≥ {EV_NGUONG:g}% (hiện {fmt(ev, 2, True)}%)", ok_ev),
        ("Ngày: có điểm mua đã xác nhận", tg["ngay_ok"]),
        (f"R/R ≥ {RR_NGUONG:g} (hiện {fmt(rr)})", ok_rr),
        ("Giờ: có tín hiệu vào lệnh", tg["gio_ok"]),
        ("Mục tiêu đề xuất > giá hiện tại", not qr["phong_thu"]),
        ("Thị trường: VN-Index trên MA200 & MACD tuần > Signal", (not ttr["vni_xau"]) if ttr["co_vni"] else None),
        ("Sức mạnh tương đối: RS không ở đáy 1 năm", (not ttr["rs_yeu"]) if ttr["co_rs"] else None),
        (f"Không có KQKD / GDKHQ trong {SO_PHIEN_SU_KIEN} phiên tới", not ttr["chan"]),
    ]
    if qr["phong_thu"]:
        kn, hd = "KHÔNG MUA MỚI", (f"Mục tiêu đề xuất {fmt(dx['chon'])} ≤ giá hiện tại → không mở vị thế; "
                                   f"chỉ mua lại ở ≤ {fmt(qr['gia_mua_rr2'])}.")
    elif not tg["tuan_ok"]:
        kn, hd = "CHƯA MUA", ("Khung TUẦN phủ quyết: MACD tuần dưới Signal. Đứng ngoài, chờ MACD tuần cắt lên "
                              "Signal rồi xét lại khung ngày.")
    elif not ok_ev:
        kn, hd = "CHƯA MUA", (f"Không có lợi thế thống kê: EV {fmt(ev, 2, True)}% < {EV_NGUONG:g}% với cắt lỗ "
                              f"{fmt(stop['gia'])} – xác suất chạm cắt lỗ trước mục tiêu quá cao.")
    elif not tg["ngay_ok"]:
        kn, hd = "THEO DÕI", ("Tuần ủng hộ, EV dương nhưng khung ngày chưa có điểm mua đã xác nhận. Chờ MACD ngày "
                              "cắt lên Signal / giá phá đỉnh nhỏ gần hỗ trợ.")
    elif not ok_rr:
        kn, hd = "CHỜ GIÁ TỐT HƠN", f"R/R {fmt(rr)} < {RR_NGUONG:g}: chỉ mua ở ≤ {fmt(qr['gia_mua_rr2'])}."
    elif tg["gio_ok"] is None:
        kn, hd = "MUA TỪNG PHẦN", "Đủ điều kiện tuần, ngày, EV, R/R; thiếu dữ liệu giờ → giải ngân từng phần."
    elif not tg["gio_ok"]:
        kn, hd = "CHỜ ĐIỂM VÀO", ("Đủ điều kiện tuần, ngày, EV, R/R. Chờ trên biểu đồ GIỜ: MACD giờ cắt lên Signal "
                                  "hoặc giá phá đỉnh nhỏ / kháng cự giờ.")
    else:
        kn = "MUA" + (" – ĐỦ ĐIỀU KIỆN 3 KHUNG" if tg["tuan_rat_tot"] else "")
        hd = f"Giải ngân theo khối lượng ở phần E2; cắt lỗ {fmt(stop['gia'])} ({fmt(stop['pct'], 1, True)}%)."
    if kn.startswith("MUA"):
        if ttr["chan"]:
            kn, hd = "CHỜ SAU SỰ KIỆN", (f"Đủ điều kiện kỹ thuật nhưng sắp có {', '.join(ttr['su_kien'])} → không mở "
                                         f"vị thế trước sự kiện (gap giá dễ quét cắt lỗ).")
        elif ttr["vni_xau"] and ttr["rs_yeu"]:
            kn, hd = "THEO DÕI", "Đủ điều kiện kỹ thuật nhưng VN-Index xấu VÀ RS ở đáy 1 năm → chưa mở vị thế."
        elif ttr["vni_xau"] or ttr["rs_yeu"]:
            ly = "VN-Index xấu" if ttr["vni_xau"] else "RS ở đáy 1 năm"
            kn = "MUA TỪNG PHẦN"
            hd = f"{ly} → chỉ giải ngân {ttr['he_so'] * 100:.0f}% khối lượng tính theo rủi ro. " + hd
    mua = kn.startswith("MUA")
    if ht <= stop["gia"]:
        dang_giu = "BÁN – giá đã ở/dưới mức cắt lỗ."
    elif qr["phong_thu"]:
        dang_giu = f"Giảm tỷ trọng khi hồi; bán hết nếu đóng cửa dưới {fmt(stop['gia'])}."
    elif mua:
        dang_giu = f"Giữ / có thể gia tăng; cắt lỗ {fmt(stop['gia'])}."
    else:
        dang_giu = f"Giữ, KHÔNG mua thêm; cắt lỗ {fmt(stop['gia'])} ({fmt(stop['pct'], 1, True)}%)."
    mau = "#2e7d32" if mua else ("#f9a825" if kn in ("THEO DÕI", "CHỜ ĐIỂM VÀO", "CHỜ GIÁ TỐT HƠN",
                                                      "CHỜ SAU SỰ KIỆN") else "#c62828")
    return {"khuyen_nghi": kn, "hanh_dong": hd, "kiem_tra": kiem_tra, "dang_giu": dang_giu, "mau": mau,
            "mua": mua, "ly_do": [t for t, ok in kiem_tra if ok is False]}


# ==========================================================================
# 9. PHẦN A – PHÂN TÍCH % TĂNG / GIẢM GIÁ
# ==========================================================================
def bien_dong_theo_khung(df):
    """% thay đổi giá, đỉnh và đáy trong từng khung thời gian (dữ liệu ngày)."""
    gia, ht = df.close, df.close.iloc[-1]
    rows = []
    for ten, n in KHUNG_TG.items():
        if len(gia) > n:
            doan = gia.iloc[-n - 1:]
            rows.append([ten, doan.iloc[0], (ht / doan.iloc[0] - 1) * 100, doan.max(), doan.min()])
    nam_nay = gia[gia.index.year == gia.index[-1].year]
    truoc = gia[gia.index < nam_nay.index[0]]
    goc = truoc.iloc[-1] if len(truoc) else nam_nay.iloc[0]
    rows.append(["Từ đầu năm", goc, (ht / goc - 1) * 100, nam_nay.max(), nam_nay.min()])
    return pd.DataFrame(rows, columns=["Khung", "Giá gốc", "% thay đổi", "Cao nhất", "Thấp nhất"])


def chuoi_tang_giam(pct):
    """Chuỗi phiên tăng/giảm liên tiếp dài nhất và chuỗi hiện tại."""
    dau = np.sign(pct)
    g = dau.groupby((dau != dau.shift()).cumsum()).agg(["first", "size"])
    xu = {1: "tăng", -1: "giảm"}.get(int(g.iloc[-1]["first"]), "đứng giá")
    max_tang = int(g[g["first"] > 0]["size"].max()) if (g["first"] > 0).any() else 0
    max_giam = int(g[g["first"] < 0]["size"].max()) if (g["first"] < 0).any() else 0
    return max_tang, max_giam, xu, int(g.iloc[-1]["size"])


def phan_loai_phien(df, nguong=None):
    """
    Đếm số phiên rơi vào từng trường hợp tăng/giảm.
    [SỬA] Tách riêng TRẦN và SÀN (bản cũ gộp nên 'TB % thay đổi' vô nghĩa); ngưỡng theo sàn niêm yết.
    """
    nguong = nguong or cfg.NGUONG_TRAN_SAN
    pct = df.close.pct_change().dropna() * 100
    tran, san = pct >= nguong, pct <= -nguong
    ts = tran | san
    rows = []
    for ten, lo, hi in NHOM_PHIEN:
        m = (pct > lo) & (pct <= hi) & ~ts
        rows.append([ten, int(m.sum()), m.mean() * 100, pct[m].mean() if m.any() else 0])
    rows.append([f"Tăng trần (≥ +{nguong:g}%)", int(tran.sum()), tran.mean() * 100,
                 pct[tran].mean() if tran.any() else 0])
    rows.append([f"Giảm sàn (≤ −{nguong:g}%)", int(san.sum()), san.mean() * 100,
                 pct[san].mean() if san.any() else 0])
    return pd.DataFrame(rows, columns=["Trường hợp", "Số phiên", "Tỷ lệ %", "TB % thay đổi"]), pct


def kiem_tra_du_lieu(df_ngay, df_gio, pv_ngay, pv_tuan, bien_do):
    """
    [MỚI] Kiểm tra nhất quán dữ liệu:
      (1) Đỉnh/đáy tuần phải bao trùm đỉnh/đáy ngày trong cùng tuần (CHỈ khi DINH_DAY_THEO = "high_low";
          theo giá đóng cửa thì đỉnh tuần = đóng cửa thứ Sáu, có thể thấp hơn đỉnh ngày giữa tuần – không phải lỗi).
      (2) Phiên biến động vượt biên độ sàn + 0.5% → nghi giá CHƯA điều chỉnh cổ tức/chia tách.
      (3) Giá đóng cửa khung giờ lệch khung ngày > 2% → hai nguồn khác cơ sở điều chỉnh.
    """
    ds = []
    for _, w in (pv_tuan[pv_tuan.xac_nhan].iterrows() if DINH_DAY_THEO != "close" else ()):
        ket_tuan = w.time.normalize()      # nhãn nến tuần = thứ Sáu
        trong = pv_ngay[(pv_ngay.time > ket_tuan - pd.Timedelta(days=7)) & (pv_ngay.time <= ket_tuan)
                        & (pv_ngay.loai == w.loai)]
        for _, d in trong.iterrows():
            sai = d.gia > w.gia * 1.001 if w.loai == "Đỉnh" else d.gia < w.gia * 0.999
            if sai:
                ds.append(f"{w.loai} tuần {w.time:%d/%m/%Y} = {w.gia:,.2f} nhưng {w.loai.lower()} ngày "
                          f"{d.time:%d/%m/%Y} = {d.gia:,.2f} → khác cơ sở giá (DINH_DAY_THEO='{DINH_DAY_THEO}').")
    pct = df_ngay.close.pct_change().dropna() * 100
    vuot = pct[pct.abs() > bien_do + 0.5]
    if len(vuot):
        mau = ", ".join(f"{t:%d/%m/%Y} ({v:+.1f}%)" for t, v in vuot.tail(5).items())
        ds.append(f"{len(vuot)} phiên biến động vượt biên độ ±{bien_do:g}% (gần nhất: {mau}) → có thể giá CHƯA "
                  f"điều chỉnh cổ tức/chia tách, hoặc sai sàn niêm yết. Đối chiếu nguồn ở cuối báo cáo.")
    if df_gio is not None and len(df_gio):
        ngay_cuoi = df_gio.index[-1].normalize()
        if ngay_cuoi in df_ngay.index:
            lech = (df_gio.close.iloc[-1] / df_ngay.close.loc[ngay_cuoi] - 1) * 100
            if abs(lech) > 2:
                ds.append(f"Giá giờ cuối ({df_gio.close.iloc[-1]:,.2f}) lệch giá ngày ({df_ngay.close.loc[ngay_cuoi]:,.2f})"
                          f" {lech:+.1f}% → khung giờ có thể chưa điều chỉnh.")
    return ds


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


def trang_thai_tuong_tu(d_ngay, d_tuan):
    """
    [MỚI] Mặt nạ các phiên quá khứ có TRẠNG THÁI TƯƠNG TỰ hiện tại (để tính xác suất CÓ ĐIỀU KIỆN):
      • MACD tuần (tuần gần nhất đã đóng cửa) cùng phía mốc 0 với hiện tại
      • MACD ngày cùng phía đường Signal
      • RSI ngày cùng nhóm (< 35 | 35–65 | > 65)
      • Cùng trạng thái 'gần đáy 1 năm' (giá ≤ đáy 252 phiên + 10%)
    Thiếu mẫu (< SO_MAU_DK_MIN) → nới lần lượt từ điều kiện cuối lên.
    """
    mt = d_tuan.MACD.reindex(d_ngay.index, method="ffill")
    tuan_am = (mt < 0).values
    ngay_tren = (d_ngay.MACD > d_ngay.SIGNAL).values
    rsi = d_ngay.RSI.values
    nhom_rsi = np.where(rsi < 35, 0, np.where(rsi > 65, 2, 1))
    day1n = d_ngay.low.rolling(252, min_periods=60).min()
    gan_day = (d_ngay.close <= day1n * 1.10).values
    L = -1
    dk = [("MACD tuần " + ("< 0" if tuan_am[L] else "≥ 0"), tuan_am == tuan_am[L]),
          ("MACD ngày " + ("> Signal" if ngay_tren[L] else "≤ Signal"), ngay_tren == ngay_tren[L]),
          (f"RSI ngày nhóm {['< 35', '35–65', '> 65'][nhom_rsi[L]]}", nhom_rsi == nhom_rsi[L]),
          ("gần đáy 1 năm" if gan_day[L] else "không gần đáy 1 năm", gan_day == gan_day[L])]
    hop_le = ~np.isnan(mt.values)
    for k in range(len(dk), 0, -1):
        m = hop_le.copy()
        for _, v in dk[:k]:
            m &= v
        if m[:-1].sum() >= SO_MAU_DK_MIN * 3:
            return m, " & ".join(t for t, _ in dk[:k])
    return None, "không đủ mẫu"


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
    ev_truoc = min(ev_co_so, ev_dk) if dk_du and ev_dk == ev_dk else ev_co_so
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
            "ev_truoc_wf": ev_truoc, "lech_wf": lech_wf, "dk_mo_ta": dk[1] if dk else "—", "dk_du": bool(dk_du),
            "p_thang": ms["tron"]["tren"] + ms["tron"]["giua"] if ms["tron"]["so_mau"] else np.nan,
            "hien_tai": hien_tai, "thong_ke": thong_ke, "canh_bao_kb": canh_bao_kb, "n_phien": n_phien,
            "bien_do": bien_do, "sigma_nam": sigma * np.sqrt(252) * 100,
            "sigma_ewma_nam": s_ewma * np.sqrt(252) * 100, "kc": kc, "hotro": hotro, "cat_lo": cat_lo,
            "mt_cs": mt_cs, "mt_tc": mt_tc, "gia_tc": gia_tieu_cuc, "hotro_that": hotro_that, "so_mau": ms["all"]["so_mau"],
            "so_mau1": ms["1y"]["so_mau"], "n": n_phien, "xs_cham_stop": xs_cham_stop, "t_cham_stop": t_cham_stop,
            "rr": (mt_tc - ht) / (ht - cat_lo) if ht > cat_lo else np.nan,
            "do_lech_ngay": float(df_ngay.close.pct_change().tail(252).std() * 100)}


def tinh_beta(df, vni, so_phien=252):
    """Beta = Cov(r_cp, r_vni) / Var(r_vni), lợi suất ngày trong 52 tuần gần nhất."""
    if vni is None:
        return np.nan
    r = pd.concat([df.close.pct_change(), vni.close.pct_change()], axis=1, join="inner").dropna()
    r = r.tail(so_phien)
    if len(r) < 60:
        return np.nan
    return r.iloc[:, 0].cov(r.iloc[:, 1]) / r.iloc[:, 1].var()


CHU_GIAI_CP = [
    "KL CP ĐÃ PHÁT HÀNH : toàn bộ cổ phiếu công ty đã phát hành (= vốn điều lệ / 10.000đ)",
    "KL CP NIÊM YẾT     : số CP được giao dịch trên sàn; có thể NHỎ HƠN số đã phát hành khi CP mới "
    "(ESOP, riêng lẻ, trả cổ tức...) chưa niêm yết bổ sung",
    "KL CP LƯU HÀNH     : = Đã phát hành − Cổ phiếu quỹ → dùng để tính VỐN HOÁ và EPS",
]


def co_cau_co_phieu(kl_phat_hanh, kl_niem_yet, cp_quy, ung_vien=None, nhan_nhap="Nhập tay", lech_pct=0.5):
    """
    Phân biệt 3 khái niệm (theo quy định Việt Nam) – xem CHU_GIAI_CP.
    ung_vien = {"luu_hanh": {nguồn: số}, "niem_yet": {nguồn: số}, "phat_hanh": {nguồn: số}} từ lay_thong_tin_dn.
    Ưu tiên: NHẬP TAY (BCTC/BCTN/HOSE-HNX) > nguồn online theo thứ tự trong dict (TCBS → VNDirect → Yahoo).
    Đối chiếu chéo mọi nguồn, cảnh báo khi lệch > lech_pct %.
    """
    uv = ung_vien or {}
    lh_uv, ny_uv, ph_uv = uv.get("luu_hanh", {}), uv.get("niem_yet", {}), uv.get("phat_hanh", {})
    dau = lambda d: next(iter(d.items()), (None, None))
    canh_bao, nguon = [], {}

    # KL phát hành & niêm yết
    if kl_phat_hanh:
        nguon["phat_hanh"] = nhan_nhap
    elif ph_uv:
        nguon["phat_hanh"], kl_phat_hanh = dau(ph_uv)
    if kl_niem_yet:
        nguon["niem_yet"] = nhan_nhap
    elif ny_uv:
        nguon["niem_yet"], kl_niem_yet = dau(ny_uv)

    # CP quỹ
    if cp_quy is not None:
        nguon["cp_quy"] = nhan_nhap
    elif kl_phat_hanh and lh_uv and not kl_phat_hanh == 0:
        n_lh, v_lh = dau(lh_uv)
        cp_quy = max(kl_phat_hanh - v_lh, 0)
        nguon["cp_quy"] = f"Suy ra: phát hành − lưu hành ({n_lh})"
    else:
        cp_quy = 0
        nguon["cp_quy"] = "Mặc định 0 (chưa có dữ liệu)"

    # KL lưu hành – dùng để tính VỐN HOÁ & EPS
    if kl_phat_hanh and nguon.get("phat_hanh") == nhan_nhap:
        kl_luu_hanh = kl_phat_hanh - cp_quy
        nguon["luu_hanh"] = "Tính = phát hành − CP quỹ"
    elif lh_uv:
        nguon["luu_hanh"], kl_luu_hanh = dau(lh_uv)
        if not kl_phat_hanh:
            kl_phat_hanh = kl_luu_hanh + cp_quy
            nguon["phat_hanh"] = f"Suy ra = lưu hành ({nguon['luu_hanh']}) + CP quỹ"
    elif kl_phat_hanh:
        kl_luu_hanh = kl_phat_hanh - cp_quy
        nguon["luu_hanh"] = "Tính = phát hành − CP quỹ"
    elif kl_niem_yet:
        kl_luu_hanh = kl_niem_yet - cp_quy
        nguon["luu_hanh"] = f"Tạm = niêm yết ({nguon['niem_yet']}) − CP quỹ"
        canh_bao.append("Không có số CP lưu hành từ nguồn nào → tạm dùng KL niêm yết − CP quỹ; kiểm tra lại với BCTC.")
    else:
        kl_luu_hanh = None
        nguon["luu_hanh"] = "—"
    nguon.setdefault("phat_hanh", "—")
    nguon.setdefault("niem_yet", "—")
    # Chưa biết CP quỹ mà KL niêm yết > KL lưu hành → phần chênh nhiều khả năng là CP quỹ
    if (nguon["cp_quy"].startswith("Mặc định") and kl_niem_yet and kl_luu_hanh and kl_niem_yet > kl_luu_hanh
            and nguon["phat_hanh"] != nhan_nhap):
        cp_quy = kl_niem_yet - kl_luu_hanh
        nguon["cp_quy"] = f"Suy ra: niêm yết ({nguon['niem_yet']}) − lưu hành ({nguon['luu_hanh']})"
        kl_phat_hanh = kl_luu_hanh + cp_quy
        nguon["phat_hanh"] = "Suy ra = lưu hành + CP quỹ"
        canh_bao.append("CP quỹ SUY RA = KL niêm yết − KL lưu hành (giả định toàn bộ CP đã niêm yết) – kiểm tra "
                        "mục 'Cổ phiếu quỹ' trên BCTC.")

    if not kl_niem_yet and kl_phat_hanh:
        kl_niem_yet = kl_phat_hanh
        nguon["niem_yet"] = "Giả định = KL phát hành"
        canh_bao.append("Không có KL niêm yết → tạm giả định bằng KL đã phát hành.")

    chua_niem_yet = None
    if kl_phat_hanh and kl_niem_yet:
        chua_niem_yet = kl_phat_hanh - kl_niem_yet
        if chua_niem_yet > 0:
            canh_bao.append(f"Có {so_vn(chua_niem_yet)} CP đã phát hành nhưng CHƯA niêm yết "
                            f"(chờ niêm yết bổ sung / bị hạn chế chuyển nhượng).")
        elif chua_niem_yet < 0:
            canh_bao.append("KL niêm yết LỚN HƠN KL phát hành – số liệu một nguồn có thể chưa cập nhật, hãy kiểm tra.")
    if cp_quy:
        canh_bao.append(f"Công ty có {so_vn(cp_quy)} cổ phiếu quỹ → không tính vào vốn hoá & EPS.")

    # Bảng đối chiếu: mỗi nguồn 1 cột
    ds_nguon = list(dict.fromkeys(list(lh_uv) + list(ny_uv) + list(ph_uv)))
    dong = []
    for ten, gt, d in (("KL CP đã phát hành", kl_phat_hanh, ph_uv), ("KL CP niêm yết", kl_niem_yet, ny_uv),
                       ("Cổ phiếu quỹ", cp_quy, {}), ("KL CP lưu hành", kl_luu_hanh, lh_uv)):
        khoa = {"KL CP đã phát hành": "phat_hanh", "KL CP niêm yết": "niem_yet", "Cổ phiếu quỹ": "cp_quy",
                "KL CP lưu hành": "luu_hanh"}[ten]
        r = {"Chỉ tiêu": ten, "Dùng trong báo cáo": gt, "Nguồn": nguon.get(khoa, "—")}
        for n in ds_nguon:
            r[n] = d.get(n, np.nan)
        cac = [v for v in d.values() if v]
        r["Lệch tối đa %"] = (max(cac) / min(cac) - 1) * 100 if len(cac) >= 2 else np.nan
        if gt and cac:
            r["Lệch tối đa %"] = max(r["Lệch tối đa %"] if r["Lệch tối đa %"] == r["Lệch tối đa %"] else 0,
                                     max(abs(gt / v - 1) * 100 for v in cac))
        dong.append(r)
        if r["Lệch tối đa %"] == r["Lệch tối đa %"] and r["Lệch tối đa %"] > lech_pct:
            canh_bao.append(f"{ten} lệch tới {so_vn(r['Lệch tối đa %'], 2)}% giữa các nguồn ("
                            + ", ".join(f"{n} {so_vn(v)}" for n, v in d.items()) + ") – có thể do phát hành mới "
                            "/ CP quỹ / nguồn chưa cập nhật; nên đối chiếu BCTC.")
    bang = pd.DataFrame(dong)
    return {"kl_phat_hanh": kl_phat_hanh, "kl_niem_yet": kl_niem_yet, "cp_quy": cp_quy,
            "kl_luu_hanh": kl_luu_hanh, "chua_niem_yet": chua_niem_yet, "canh_bao_cp": canh_bao,
            "doi_chieu_cp": bang}


def thong_tin_giao_dich(df, vni, cc, so_huu_nn, beta_nhap=None):
    """Tổng hợp các chỉ tiêu giao dịch giống phần 'Thông tin giao dịch' trên báo cáo phân tích."""
    ht = df.close.iloc[-1]
    d52 = df[df.index > df.index[-1] - pd.Timedelta(weeks=52)]
    cao52, thap52 = d52.high.max(), d52.low.min()
    tt = {
        "ngay": df.index[-1],
        "gia": ht,
        "cao52": cao52, "ngay_cao52": d52.high.idxmax(),
        "thap52": thap52, "ngay_thap52": d52.low.idxmin(),
        "cach_dinh52": (ht / cao52 - 1) * 100,
        "cach_day52": (ht / thap52 - 1) * 100,
        **cc,
        # Vốn hoá = Giá × KL CP LƯU HÀNH (không tính cổ phiếu quỹ)
        "von_hoa": ht * 1000 * cc["kl_luu_hanh"] / 1e9 if cc["kl_luu_hanh"] else np.nan,   # tỷ đồng
        "beta": beta_nhap if beta_nhap is not None else tinh_beta(df, vni),
        "so_huu_nn": so_huu_nn,
        "kl_tb20": df.volume.tail(20).mean(),
        "kl_tb52t": d52.volume.mean(),
        "gt_tb20": (df.volume * df.close * 1000).tail(20).mean() / 1e9,   # tỷ đồng
    }
    # Hiệu suất so với VNINDEX
    hs = []
    for ten, n in KHUNG_TG.items():
        if len(df) > n:
            r_cp = (ht / df.close.iloc[-n - 1] - 1) * 100
            r_vn = np.nan
            if vni is not None and len(vni) > n:
                v = vni.close[vni.index <= df.index[-1]]
                r_vn = (v.iloc[-1] / v.iloc[-n - 1] - 1) * 100
            hs.append([ten, r_cp, r_vn, r_cp - r_vn if not np.isnan(r_vn) else np.nan])
    tt["hieu_suat"] = pd.DataFrame(hs, columns=["Khung", "Cổ phiếu %", "VNINDEX %", "Chênh lệch %"])
    return tt


def von_hoa_chu(ty):
    """Viết vốn hoá dạng '3,8 nghìn tỷ đồng' hoặc '850 tỷ đồng'."""
    if ty is None or np.isnan(ty):
        return "N/A"
    return f"{so_vn(ty / 1000, 1)} nghìn tỷ đồng" if ty >= 1000 else f"{so_vn(ty, 0)} tỷ đồng"


def danh_gia_dinh_gia(upside):
    """
    [SỬA] Mô tả mức hấp dẫn về ĐỊNH GIÁ theo upside của mục tiêu đề xuất. KHÔNG phải khuyến nghị hành động
    (khuyến nghị hành động duy nhất đến từ quyet_dinh_cuoi) → tránh 2 kết luận trái nhau như bản cũ.
    """
    if upside is None or np.isnan(upside):
        return "N/A"
    if upside >= 15:
        return "Hấp dẫn (upside ≥ 15%)"
    if upside >= 5:
        return "Khá (upside 5–15%)"
    if upside >= -5:
        return "Trung tính (±5%)"
    if upside >= -15:
        return "Kém (−15% … −5%)"
    return "Đắt (upside < −15%)"


def de_xuat_muc_tieu(df_ngay, kq, ht, mt_nhap, hoi_tu, ky_han, mt_ctck=None):
    """
    E1 – Đối chiếu mục tiêu tự định với vùng mục tiêu hợp lý [SÀN, TRẦN] trong 'ky_han' phiên:
      SÀN  = upside mà ≥ XS_SAN % giai đoạn lịch sử đã chạm  (mục tiêu thấp hơn = quá thận trọng)
      TRẦN = upside mà chỉ XS_TRAN % giai đoạn chạm, không vượt biên 95% (cao hơn = khó đạt)
    [SỬA] Mọi xác suất ở E1 dùng NHẤT QUÁN xác suất TRỘN (trọng số giảm dần theo tuổi, bán rã XS_BAN_RA phiên)
          – cùng cơ sở với phần D – thay vì toàn bộ lịch sử trọng số đều. Biên 95% dùng σ EWMA.
    """
    H = ky_han
    s_ewma = sigma_ewma(df_ngay.close)
    bien95 = (np.exp(1.96 * s_ewma * np.sqrt(H)) - 1) * 100
    up = _upside_toi_da(df_ngay, H)
    w = _trong_so_gan_day(len(up), len(df_ngay)) if len(up) else np.array([])
    if len(up) >= 60:
        san_up = _phan_vi_trong_so(up.values, w, 100 - XS_SAN)
        tran_up = _phan_vi_trong_so(up.values, w, 100 - XS_TRAN)
        cach = (f"phân phối mức tăng tối đa của {len(up)} giai đoạn {H} phiên, trọng số TRỘN "
                f"(bán rã {XS_BAN_RA} phiên)")
    else:
        san_up = (np.exp(0.5 * s_ewma * np.sqrt(H)) - 1) * 100
        tran_up = (np.exp(1.5 * s_ewma * np.sqrt(H)) - 1) * 100
        cach = f"biến động EWMA (thiếu dữ liệu cho kỳ hạn {H} phiên)"
    san_up = max(san_up, 3.0)
    tran_up = min(tran_up, bien95)
    if tran_up <= san_up * 1.05:
        tran_up = san_up * 1.5
    san, tran = ht * (1 + san_up / 100), ht * (1 + tran_up / 100)
    xs_cham = lambda g: _tb_trong_so(up.values >= (g / ht - 1) * 100, w) * 100 if len(up) else np.nan
    xs_cham_deu = lambda g: float((up >= (g / ht - 1) * 100).mean() * 100) if len(up) else np.nan

    uv = []
    for ten in ("Ngày", "Tuần"):
        b = kq[ten]["mt"]["bang"]
        for _, r in b.iterrows():
            uv.append([f"{ten}: {r['Phương pháp']}", r["Giá mục tiêu"]])
    for lo, hi, a_, b_ in hoi_tu:
        uv.append([f"Vùng hội tụ ngày–tuần ({a_} / {b_})", (lo + hi) / 2])
    if mt_ctck:
        uv.append([f"Đồng thuận CTCK (trung vị {len(mt_ctck)} báo cáo)", float(np.median(mt_ctck))])
    bang = pd.DataFrame(uv, columns=["Mốc", "Giá"]).drop_duplicates("Giá") if uv else \
        pd.DataFrame(columns=["Mốc", "Giá"])
    if len(bang):
        bang["Upside %"] = (bang["Giá"] / ht - 1) * 100
        bang[f"XS chạm {H} phiên – trộn %"] = bang["Giá"].map(xs_cham)
        bang[f"XS chạm {H} phiên – toàn bộ %"] = bang["Giá"].map(xs_cham_deu)
        bang["Trong vùng hợp lý"] = np.where(bang["Giá"].between(san, tran), "✔",
                                             np.where(bang["Giá"] < san, "thấp", "cao"))
        bang = bang.sort_values("Giá").reset_index(drop=True)
    trong = bang[bang["Trong vùng hợp lý"] == "✔"] if len(bang) else bang
    uu_tien_hoi_tu = trong[trong["Mốc"].str.startswith("Vùng hội tụ")] if len(trong) else trong

    canh_bao = []
    if not mt_nhap:
        if len(uu_tien_hoi_tu):
            chon, moc = uu_tien_hoi_tu.iloc[0]["Giá"], uu_tien_hoi_tu.iloc[0]["Mốc"]
        elif len(trong):
            r = trong.iloc[(trong["Giá"] - (san + tran) / 2).abs().argmin()]
            chon, moc = r["Giá"], r["Mốc"]
        else:
            chon, moc = (san + tran) / 2, "Giữa vùng hợp lý"
        hanh_dong, ly_do = "ĐỀ XUẤT", f"Chưa có mục tiêu tự định → chọn mốc {moc}."
    elif mt_nhap <= ht:
        chon, moc, hanh_dong = mt_nhap, "Giữ mục tiêu tự định", "GIỮ (định giá ≤ thị giá)"
        ly_do = ("Mục tiêu tự định thấp hơn/bằng giá hiện tại → định giá cơ bản cho thấy cổ phiếu đã phản ánh đủ "
                 "giá trị. Công cụ KHÔNG tự nâng mục tiêu vì làm vậy sẽ đảo khuyến nghị.")
        canh_bao.append("Định giá cơ bản < giá thị trường: xem lại giả định (WACC, g, lợi nhuận dự phóng) "
                        "hoặc chấp nhận khuyến nghị giảm tỷ trọng.")
    elif mt_nhap < san:
        cao_hon = trong[trong["Giá"] >= san] if len(trong) else trong
        chon, moc = (cao_hon.iloc[0]["Giá"], cao_hon.iloc[0]["Mốc"]) if len(cao_hon) else (san, "Sàn vùng hợp lý")
        hanh_dong = "NÂNG"
        ly_do = (f"Mục tiêu tự định {mt_nhap:,.2f} ({(mt_nhap / ht - 1) * 100:+.1f}%) thấp hơn SÀN {san:,.2f}: "
                 f"{xs_cham(mt_nhap):.0f}% giai đoạn {H} phiên (trộn) đã chạm mức này → quá thận trọng. "
                 f"Nâng lên mốc gần nhất trong vùng: {moc}.")
    elif mt_nhap > tran:
        thap_hon = trong[trong["Giá"] <= tran] if len(trong) else trong
        chon, moc = (thap_hon.iloc[-1]["Giá"], thap_hon.iloc[-1]["Mốc"]) if len(thap_hon) else (tran, "Trần vùng hợp lý")
        hanh_dong = "HẠ"
        ly_do = (f"Mục tiêu tự định {mt_nhap:,.2f} ({(mt_nhap / ht - 1) * 100:+.1f}%) cao hơn TRẦN {tran:,.2f}: "
                 f"chỉ {xs_cham(mt_nhap):.0f}% giai đoạn {H} phiên (trộn) chạm được → khó đạt nếu không có chất "
                 f"xúc tác lớn. Hạ xuống mốc cao nhất trong vùng: {moc}. Giữ {mt_nhap:,.2f} làm mục tiêu mở rộng.")
    else:
        chon, moc, hanh_dong = mt_nhap, "Giữ mục tiêu tự định", "GIỮ"
        ly_do = (f"Mục tiêu tự định nằm trong vùng hợp lý {san:,.2f} – {tran:,.2f} "
                 f"({xs_cham(mt_nhap):.0f}% giai đoạn đã chạm, trộn).")
        kc_sat = bang[(bang["Giá"] < mt_nhap) & (bang["Giá"] >= mt_nhap * 0.97)] if len(bang) else bang
        if len(kc_sat):
            canh_bao.append(f"Có mốc kỹ thuật {kc_sat.iloc[-1]['Giá']:,.2f} ({kc_sat.iloc[-1]['Mốc']}) ngay dưới mục tiêu"
                            f" → nên chốt lời một phần tại đó.")
    if xs_cham(chon) == xs_cham(chon) and xs_cham_deu(chon) - xs_cham(chon) > 15:
        canh_bao.append(f"XS chạm mục tiêu theo giai đoạn gần đây ({xs_cham(chon):.0f}%) thấp hơn nhiều so với toàn "
                        f"lịch sử ({xs_cham_deu(chon):.0f}%) → hành vi giá gần đây kém hơn; thận trọng.")
    if mt_ctck:
        lo_c, hi_c = min(mt_ctck), max(mt_ctck)
        vi_tri = "nằm trong" if lo_c <= chon <= hi_c else ("thấp hơn" if chon < lo_c else "cao hơn")
        canh_bao.append(f"Mục tiêu đề xuất {vi_tri} khoảng mục tiêu CTCK {lo_c:,.2f} – {hi_c:,.2f} "
                        f"(trung vị {np.median(mt_ctck):,.2f}).")
    return {"san": san, "tran": tran, "chon": chon, "moc": moc, "hanh_dong": hanh_dong, "ly_do": ly_do,
            "bang": bang, "xs_chon": xs_cham(chon), "xs_chon_deu": xs_cham_deu(chon),
            "xs_nhap": xs_cham(mt_nhap) if mt_nhap else np.nan,
            "ky_han": H, "cach": cach, "canh_bao": canh_bao, "mt_nhap": mt_nhap, "ctck": mt_ctck}


def quan_tri_rui_ro(df_ngay, kq, ht, dx, stop, tt, kb, gia_von, so_cp, von_trieu, rui_ro_pct, he_so_tt=1.0):
    """
    E2 – Các mức quản trị rủi ro gắn với mục tiêu đề xuất.
    [SỬA] Chỉ còn MỘT mức cắt lỗ (cắt lỗ thống nhất); các thành phần (đáy ngày, ATR, cứng) chỉ in ở dòng giải thích.
          Bỏ 'cắt lỗ trung hạn theo đáy tuần' (−60…−70%, R/R ≈ 0.1 – không có giá trị hành động).
          Khối lượng mua = vốn × % rủi ro ÷ (giá vào − cắt lỗ), giới hạn bởi trần tỷ trọng.
    """
    d = kq["Ngày"]["df"]
    atr = float(d.ATR.iloc[-1])
    mt = dx["chon"]
    lo_ap_dung = stop["gia"]
    ho_tro = _duong(kq["Ngày"]["xh"], "ho_tro")
    ung = [x for x in ((ho_tro["gia_nay"] if ho_tro else None), ht - atr) if x and lo_ap_dung * 1.01 < x < ht]
    canh_bao_som = max(ung) if ung else None

    mt_ngay = kq["Ngày"]["mt"]["chinh"]
    tp1 = mt_ngay["Giá mục tiêu"] if mt_ngay is not None else None
    if not tp1 or tp1 >= mt * 0.97 or tp1 <= ht:
        tp1 = ht + (mt - ht) / 3
    tp2 = (tp1 + mt) / 2
    chandelier = d.high.tail(22).max() - 3 * atr
    nhan_ts = ("ĐÃ BỊ XUYÊN – giá đã giảm > 3×ATR từ đỉnh 22 phiên" if chandelier >= ht else None)

    rr = (mt - ht) / (ht - lo_ap_dung) if ht > lo_ap_dung else np.nan
    gia_mua_rr2 = (mt + RR_NGUONG * lo_ap_dung) / (1 + RR_NGUONG)
    gia_mua_rr3 = (mt + 3 * lo_ap_dung) / 4

    phong_thu = mt <= ht
    if phong_thu:
        kc_ngay = _duong(kq["Ngày"]["xh"], "khang_cu")
        ban_hoi = tp1 if tp1 and tp1 > ht else (kc_ngay["gia_nay"] if kc_ngay and kc_ngay["gia_nay"] > ht else ht + atr)
        rr = np.nan
        gia_mua_rr2 = mt * 0.9
        muc = [
            ["Bán giảm tỷ trọng khi hồi (MT/kháng cự ngày)", ban_hoi, "Bán 50% vị thế nếu giá hồi lên đây"],
            ["Cảnh báo sớm", canh_bao_som, "Đóng cửa dưới → bán thêm, chỉ giữ tối đa 1/4"],
            ["CẮT LỖ (thống nhất)", lo_ap_dung, "Đóng cửa dưới → BÁN toàn bộ"],
            ["GIÁ TRỊ HỢP LÝ (mục tiêu tự định)", mt, "Mức định giá cơ bản"],
            ["Giá mua lại (biên an toàn 10%)", gia_mua_rr2, "Chỉ mở vị thế mới ở ≤ mức này"],
            ["Trailing stop (đỉnh 22 phiên − 3×ATR)", chandelier, nhan_ts or "Bảo vệ lãi phần đang giữ"],
        ]
    else:
        muc = [
            ["Chốt lời 3 – MỤC TIÊU ĐỀ XUẤT", mt, "Bán 40% còn lại (hoặc giữ nếu trailing stop chưa bị chạm)"],
            ["Chốt lời 2", tp2, "Bán 30%; dời cắt lỗ lên TP1"],
            ["Chốt lời 1", tp1, "Bán 30%; dời cắt lỗ về hoà vốn (giá mua)"],
            [f"Giá mua tối đa để R/R ≥ {RR_NGUONG:g}", gia_mua_rr2, "Không mua cao hơn mức này"],
            ["Giá mua lý tưởng (R/R ≥ 3)", gia_mua_rr3, "Vùng gom ưu tiên"],
            ["Cảnh báo sớm (không phải cắt lỗ)", canh_bao_som, "Đóng cửa dưới → giảm 1/3 tỷ trọng, không mua thêm"],
            ["CẮT LỖ (thống nhất)", lo_ap_dung, "Đóng cửa dưới → BÁN toàn bộ phần còn lại"],
            ["Trailing stop (đỉnh 22 phiên − 3×ATR)", chandelier, nhan_ts or "Dùng sau khi đạt TP1, cập nhật mỗi phiên"],
        ]
    bang = pd.DataFrame(muc, columns=["Mức", "Giá", "Hành động"]).dropna(subset=["Giá"])
    bang["% so giá hiện tại"] = (bang["Giá"] / ht - 1) * 100
    bang = bang[["Mức", "Giá", "% so giá hiện tại", "Hành động"]]

    kl_tb20 = tt["kl_tb20"]
    vt = {}
    rui_ro_1cp = (ht - lo_ap_dung) * 1000

    def _kich_thuoc(von):
        tien_rui_ro = von * rui_ro_pct / 100 * he_so_tt          # [MỚI] × hệ số theo thị trường
        cp_theo_rr = tien_rui_ro / rui_ro_1cp if rui_ro_1cp > 0 else 0
        cp_theo_tt = von * TY_TRONG_MAX / 100 / (ht * 1000)
        return tien_rui_ro, cp_theo_rr, cp_theo_tt, int(min(cp_theo_rr, cp_theo_tt) // 100 * 100)

    if von_trieu and phong_thu:
        vt["Gợi ý mở vị thế mới"] = f"KHÔNG mở mới – chờ giá ≤ {gia_mua_rr2:,.2f} (giá trị hợp lý − 10%)."
    elif von_trieu:
        von = von_trieu * 1e6
        tien_rui_ro, cp_theo_rr, cp_theo_tt, cp_max = _kich_thuoc(von)
        vt = {"Tổng vốn (đồng)": von, f"Rủi ro tối đa/lệnh ({rui_ro_pct:g}% vốn, đồng)": tien_rui_ro,
              "Rủi ro trên 1 CP đến cắt lỗ (đồng)": rui_ro_1cp,
              "KL theo giới hạn rủi ro = vốn × %RR ÷ (giá − cắt lỗ)": int(cp_theo_rr // 100 * 100),
              f"KL theo trần tỷ trọng {TY_TRONG_MAX:.0f}%": int(cp_theo_tt // 100 * 100),
              "Hệ số khối lượng theo thị trường": he_so_tt,
              "KL MUA TỐI ĐA (lô 100)": cp_max, "Giá trị mua tối đa (đồng)": cp_max * ht * 1000,
              "Tỷ trọng / vốn %": cp_max * ht * 1000 / von * 100,
              "Lỗ nếu chạm cắt lỗ (đồng)": cp_max * rui_ro_1cp,
              "Lãi nếu đạt mục tiêu (đồng)": cp_max * (mt - ht) * 1000}
        vt["Số phiên để thoát hàng"] = cp_max / (kl_tb20 * TY_LE_THANH_KHOAN / 100) if kl_tb20 else np.nan
    if so_cp:
        gv = gia_von or ht
        vt["Vị thế đang giữ (CP)"] = so_cp
        vt["Lãi/lỗ hiện tại (đồng)"] = (ht - gv) * so_cp * 1000
        vt["Lỗ thêm nếu chạm cắt lỗ (đồng)"] = (lo_ap_dung - ht) * so_cp * 1000
        vt["Lãi/lỗ so giá vốn tại cắt lỗ (đồng)"] = (lo_ap_dung - gv) * so_cp * 1000
        vt["Số phiên để thoát vị thế đang giữ"] = so_cp / (kl_tb20 * TY_LE_THANH_KHOAN / 100) if kl_tb20 else np.nan
        if gia_von and ht > gia_von * 1.05 and lo_ap_dung < gia_von:
            vt["Gợi ý"] = f"Đang lãi > 5%: có thể nâng cắt lỗ lên giá vốn {gia_von:,.2f} (hoà vốn)."
    vi_du = None
    if not von_trieu and not phong_thu and rui_ro_1cp > 0:
        _, _, _, cp100 = _kich_thuoc(100e6)
        vi_du = (f"Ví dụ vốn 100 triệu, rủi ro {rui_ro_pct:g}%/lệnh: KL = 100,000,000 × {rui_ro_pct:g}% ÷ "
                 f"{rui_ro_1cp:,.0f}đ = {100e6 * rui_ro_pct / 100 / rui_ro_1cp:,.0f} CP → tối đa {cp100:,} CP "
                 f"(sau trần tỷ trọng {TY_TRONG_MAX:.0f}%).")

    r1 = df_ngay.close.pct_change().dropna().tail(252) * 100
    r5 = (df_ngay.close.pct_change(5).dropna().tail(252)) * 100
    c52 = df_ngay.close.tail(252)
    mdd = ((c52 / c52.cummax()) - 1).min() * 100
    beta = tt.get("beta")
    tk = {"VaR 95% 1 phiên %": np.percentile(r1, 5) if len(r1) > 30 else np.nan,
          "VaR 95% 1 tuần %": np.percentile(r5, 5) if len(r5) > 30 else np.nan,
          "Sụt giảm tối đa 52 tuần (MDD) %": mdd,
          "ATR ngày (nghìn đồng)": atr, "ATR / giá %": atr / ht * 100,
          "Nếu VNINDEX −10% → cổ phiếu dự kiến %": -10 * beta if beta is not None and beta == beta else np.nan,
          "R/R (mục tiêu đề xuất / cắt lỗ)": rr}
    t_xem_lai = kb["bang"].loc[kb["bang"]["Kịch bản"] == "CƠ SỞ – đạt MT cơ sở", "Số phiên trung vị"]
    t_xem_lai = float(t_xem_lai.iloc[0]) if len(t_xem_lai) and t_xem_lai.iloc[0] == t_xem_lai.iloc[0] else 42.0
    tk["Cắt lỗ thời gian (phiên)"] = round(t_xem_lai * 1.5)
    return {"bang": bang, "vi_the": vt, "thong_ke": tk, "lo_ap_dung": lo_ap_dung, "tp": (tp1, tp2, mt),
            "canh_bao_som": canh_bao_som, "rr": rr, "gia_mua_rr2": gia_mua_rr2, "trailing": chandelier,
            "phong_thu": phong_thu, "vi_du": vi_du}
