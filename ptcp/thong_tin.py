# -*- coding: utf-8 -*-
"""Thông tin chung: báo cáo CTCK, Phần A (% tăng/giảm), kiểm tra dữ liệu, beta, cơ cấu cổ phiếu, thông tin giao dịch, định giá."""
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
