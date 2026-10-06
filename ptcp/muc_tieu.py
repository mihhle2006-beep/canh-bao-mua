# -*- coding: utf-8 -*-
"""Cắt lỗ thống nhất, giá mục tiêu theo khung, vùng hội tụ, đề xuất mục tiêu (E1)."""
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
