# -*- coding: utf-8 -*-
"""Mô phỏng lịch sử theo luật giao dịch VN, tổng hợp xác suất/EV, bootstrap, walk-forward, gộp ngành."""
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
    BOOTSTRAP_B, MUA_GIA_MO_CUA, N_HIEU_DUNG_MIN, PHI_GD_KHU_HOI, TRUOT_GIA_PCT, T_CONG,
    WF_SO_KHOI, XS_BAN_RA, XS_CUA_SO, XS_TOI_THIEU_MT,
)


# ==========================================================================
# 4b. [MỚI] CÔNG CỤ THỐNG KÊ: mô phỏng mua giả định, trọng số gần đây, mẫu hiệu dụng, block bootstrap
# ==========================================================================
def _trong_so_gan_day(N, tong):
    """Trọng số điểm mua i (0..N−1) trong chuỗi dài 'tong' phiên: giảm 1/2 sau mỗi XS_BAN_RA phiên tuổi."""
    tuoi = (tong - 1) - np.arange(N)
    return 0.5 ** (tuoi / XS_BAN_RA)


def _tb_trong_so(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    return float((x * w).sum() / w.sum()) if w.sum() > 0 else np.nan


def _phan_vi_trong_so(x, w, q):
    x, w = np.asarray(x, float), np.asarray(w, float)
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q / 100, cw, x))


def _bootstrap_khoi(X, w, b, B=BOOTSTRAP_B, seed=7):
    """
    Block bootstrap (khối chồng lấn dài b phiên) cho trung bình có trọng số của các cột X (N × k).
    Giữ được tương quan do các giai đoạn mua giả định CHỒNG LẤN → khoảng tin cậy trung thực hơn.
    """
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    N = len(X)
    b = int(max(1, min(b, N)))
    rng = np.random.default_rng(seed)
    k = int(np.ceil(N / b))
    starts = rng.integers(0, N - b + 1, size=(B, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(B, -1)[:, :N]
    wi = w[idx]
    return (X[idx] * wi[..., None]).sum(1) / wi.sum(1)[:, None]


def _chi_phi():
    """% chi phí khứ hồi: phí + thuế + trượt giá 2 chiều."""
    return PHI_GD_KHU_HOI + 2 * TRUOT_GIA_PCT


def _co_khoa(df, nguong=None):
    """
    [MỚI] Phiên bị KHOÁ biên độ (so với đóng cửa phiên trước):
      tran_khoa: cả phiên ở giá trần (giá thấp nhất ≥ trần) → không mua được
      san_khoa : đóng cửa ở giá sàn và bằng giá thấp nhất → coi như trắng bên mua, không bán được
    """
    thr = (nguong or cfg.NGUONG_TRAN_SAN) / 100
    c, l = df.close.values, df.low.values
    c_truoc = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        tran = l >= c_truoc * (1 + thr)
        san = (c <= c_truoc * (1 - thr)) & (c <= l * 1.0005)
    return np.nan_to_num(tran).astype(bool), np.nan_to_num(san).astype(bool)


def _mo_phong(df, n, tren=None, duoi=None, giua=None):
    """
    Mô phỏng theo lịch sử (vector hoá) – [SỬA] theo LUẬT GIAO DỊCH VIỆT NAM:
      • Quyết định ở giá đóng cửa phiên i; các mốc (cắt lỗ/mục tiêu) tính theo % so với giá đóng cửa đó.
      • MUA ở giá MỞ CỬA phiên i+1 (có gap); phiên i+1 khoá TRẦN cả phiên → không mua được (bỏ mẫu).
      • Cổ phiếu về tài khoản T+2: chỉ BÁN được từ phiên thứ T_CONG sau ngày mua.
        Cắt lỗ bị chạm khi chưa bán được → bán ở giá mở cửa phiên đầu tiên được phép bán.
      • Phiên đóng cửa ở giá SÀN (trắng bên mua) → không bán được, dời sang phiên sau.
      • Gap: chạm cắt lỗ → bán ở min(cắt lỗ, giá mở cửa); chạm mục tiêu → max(mục tiêu, giá mở cửa).
      • Cắt lỗ phát sinh trước hoặc cùng lúc mục tiêu → ưu tiên cắt lỗ (thận trọng).
    Trả về DataFrame theo điểm mua: kq, t (số phiên tới khi thoát), r_end, r_exit (% thực nhận so với giá mua),
    hop_le (mua được hay không).
    """
    c, o, h, l = (df[k].values for k in ("close", "open", "high", "low"))
    N = len(c) - n
    if N <= 0:
        return None
    tran_khoa, san_khoa = _co_khoa(df)
    O = _cua_so_truot(o[1:], n)[:N]
    Hh = _cua_so_truot(h[1:], n)[:N]
    Ll = _cua_so_truot(l[1:], n)[:N]
    SK = _cua_so_truot(san_khoa[1:], n)[:N]
    ref = c[:N]
    e = O[:, 0] if MUA_GIA_MO_CUA else ref
    k = np.arange(n)[None, :]
    hang = np.arange(N)

    def dau_tien(m):
        return np.where(m.any(1), m.argmax(1), n)

    def lay(M, idx):
        return M[hang, np.minimum(idx, n - 1)]

    if duoi is not None:
        g_d = ref * (1 + duoi / 100)
        ks = dau_tien(Ll <= g_d[:, None])
        ke = dau_tien((k >= np.maximum(ks, T_CONG)[:, None]) & ~SK)
        gia_d = np.where(ke == ks, np.minimum(g_d, lay(O, ke)), lay(O, ke))
        gia_d = np.where(ke >= n, c[n:n + N], gia_d)          # không bán được trong cửa sổ → đóng cửa cuối kỳ
    else:
        ks = ke = np.full(N, n)
        gia_d = np.full(N, np.nan)
    if tren is not None:
        g_t = ref * (1 + tren / 100)
        kt = dau_tien((Hh >= g_t[:, None]) & (k >= T_CONG))
        gia_t = np.maximum(g_t, lay(O, kt))
    else:
        kt, gia_t = np.full(N, n), np.full(N, np.nan)
    if giua is not None:
        g_g = ref * (1 + giua / 100)
        kg = dau_tien((Hh >= g_g[:, None]) & (k >= T_CONG))
        gia_g = np.maximum(g_g, lay(O, kg))
    else:
        kg, gia_g = np.full(N, n), np.full(N, np.nan)

    kq = np.full(N, "ngang", dtype=object)
    m_d = (ks < n) & (ks <= kt)
    m_t = (kt < n) & ~m_d
    m_g = ~m_d & ~m_t & (kg < n)
    kq[m_d], kq[m_t], kq[m_g] = "duoi", "tren", "giua"
    c_end = c[n:n + N]
    gia_ra = np.where(m_d, gia_d, np.where(m_t, gia_t, np.where(m_g, gia_g, c_end)))
    t = np.where(m_d, np.minimum(ke, n - 1) + 1, np.where(m_t, kt + 1, np.where(m_g, kg + 1, n)))
    return pd.DataFrame({"kq": kq, "t": t, "r_end": c_end / e * 100 - 100, "r_exit": gia_ra / e * 100 - 100,
                         "hop_le": ~tran_khoa[1:N + 1]}, index=df.index[:N])


def _tong_hop(sim, r_thoat=None, kieu="tron", mask=None, tong=None, n=63, cua_so=XS_CUA_SO, ci=True):
    """
    Tổng hợp kết quả mô phỏng thành xác suất / thời gian / lợi suất kỳ vọng (EV, đã trừ phí + trượt giá).
      kieu = 'all' | '1y' | 'tron' (trọng số giảm dần theo tuổi; dùng cột 'w' nếu có – mô phỏng gộp ngành)
             | 'dk' (chỉ phiên có trạng thái tương tự hiện tại)
      [SỬA] Lợi suất mỗi mẫu = lợi suất THỰC NHẬN (r_exit) theo luật T+2, khoá sàn, gap – không còn giả định
            luôn thoát đúng giá cắt lỗ / mục tiêu.
    Kèm số mẫu hiệu dụng (Kish ÷ độ dài TB giai đoạn) và KTC 90% bằng block bootstrap.
    """
    if sim is None:
        return None
    N = len(sim)
    tong = tong or (N + n)
    m = sim.hop_le.values.copy() if "hop_le" in sim else np.ones(N, bool)
    if kieu == "1y":
        m &= np.arange(N) >= tong - cua_so
    if mask is not None:
        m &= np.asarray(mask, bool)[:N]
    if m.sum() < 20:
        return None
    if kieu == "tron":
        w = sim.w.values if "w" in sim else _trong_so_gan_day(N, tong)
    else:
        w = np.ones(N)
    s, ww = sim[m], w[m]
    kq = s.kq.values
    r_i = s.r_exit.values
    ket = {"so_mau": int(m.sum())}
    cot = ["tren", "giua", "ngang", "duoi"]
    I = np.column_stack([(kq == k).astype(float) for k in cot] + [r_i])
    tb = (I * ww[:, None]).sum(0) / ww.sum()
    for j, k in enumerate(cot):
        ket[k] = tb[j] * 100
        tt = s.t.values[kq == k]
        ket[f"t_{k}"] = float(np.median(tt)) if len(tt) else np.nan
        ket[f"r_{k}"] = _tb_trong_so(r_i[kq == k], ww[kq == k]) if (kq == k).any() else np.nan
    ket["ev"] = tb[-1] - _chi_phi()
    kish = ww.sum() ** 2 / (ww ** 2).sum()
    ket["n_hieu_dung"] = float(kish / max(1.0, s.t.mean()))
    ket["tin_cay_thap"] = ket["n_hieu_dung"] < N_HIEU_DUNG_MIN
    if ci:
        bs = _bootstrap_khoi(I, ww, b=max(1, int(round(s.t.mean()))))
        lo, hi = np.percentile(bs, 5, axis=0), np.percentile(bs, 95, axis=0)
        for j, k in enumerate(cot):
            ket[f"ci_{k}"] = (lo[j] * 100, hi[j] * 100)
        ket["ci_ev"] = (lo[-1] - _chi_phi(), hi[-1] - _chi_phi())
    return ket


def danh_gia_muc(df_ngay, ht, muc, stop, H):
    """XS (trộn) chạm mục tiêu TRƯỚC cắt lỗ trong H phiên, số phiên trung vị, EV % (sau phí, theo luật T+2)."""
    p = lambda g: (g / ht - 1) * 100
    sim = _mo_phong(df_ngay, H, tren=p(muc), duoi=p(stop))
    kq = _tong_hop(sim, None, "tron", tong=len(df_ngay), n=H, ci=False)
    if kq is None:
        return np.nan, np.nan, np.nan, np.nan
    return kq["tren"], kq["t_tren"], kq["ev"], kq["duoi"]


def kiem_dinh_walk_forward(df_ngay, ht, cac_muc, stop, H, so_khoi=WF_SO_KHOI):
    """
    [MỚI] KIỂM ĐỊNH NGOÀI MẪU cho bước CHỌN MỤC TIÊU (khử thiên lệch "tự chấm bài mình"):
      Chia các điểm mua giả định theo thời gian thành so_khoi khối. Với mỗi khối f ≥ 2:
        – chọn mốc theo đúng quy tắc của công cụ (EV cao nhất trong các mốc có XS ≥ XS_TOI_THIEU_MT)
          CHỈ dùng dữ liệu TRƯỚC khối f, có khoảng đệm H phiên (tránh rò rỉ do giai đoạn chồng lấn);
        – đo EV thực tế của mốc đã chọn trên khối f.
      EV walk-forward = trung bình EV ngoài mẫu.  Thiên lệch chọn = EV trong mẫu − EV walk-forward (≥ 0)
      → được TRỪ vào EV dùng để quyết định.
    """
    p = lambda g: (g / ht - 1) * 100
    cac_muc = [g for g in cac_muc if g and g > ht]
    if len(cac_muc) < 1:
        return None
    sims = [_mo_phong(df_ngay, H, tren=p(g), duoi=p(stop)) for g in cac_muc]
    if any(s is None for s in sims):
        return None
    N = len(sims[0])
    ok = sims[0].hop_le.values
    R = np.column_stack([s.r_exit.values for s in sims]) - _chi_phi()
    HIT = np.column_stack([(s.kq.values == "tren") for s in sims]).astype(float)

    def chon(mask):
        xs, ev = HIT[mask].mean(0) * 100, R[mask].mean(0)
        kt = xs >= XS_TOI_THIEU_MT
        return int(np.argmax(np.where(kt, ev, -1e9))) if kt.any() else int(np.argmax(xs))

    bien = np.linspace(0, N, so_khoi + 1).astype(int)
    vt = np.arange(N)
    rows = []
    for f in range(1, so_khoi):
        a, b = bien[f], bien[f + 1]
        tr = (vt < a - H) & ok
        te = (vt >= a) & (vt < b) & ok
        if tr.sum() < 60 or te.sum() < 20:
            continue
        j = chon(tr)
        ev_te = R[te].mean(0)
        rows.append([f"{df_ngay.index[a]:%m/%Y} – {df_ngay.index[b - 1]:%m/%Y}", cac_muc[j],
                     R[tr][:, j].mean(), ev_te[j], cac_muc[int(np.argmax(ev_te))], ev_te.max(), int(te.sum())])
    if not rows:
        return None
    bang = pd.DataFrame(rows, columns=["Khối kiểm tra", "Mốc được chọn (dữ liệu trước đó)", "EV trong mẫu %",
                                       "EV ngoài mẫu %", "Mốc tốt nhất (nhìn lại)", "EV tốt nhất nhìn lại %",
                                       "Số mẫu"])
    ev_wf = float(np.average(bang["EV ngoài mẫu %"], weights=bang["Số mẫu"]))
    j_all = chon(ok)
    ev_is = float(R[ok][:, j_all].mean())
    return {"bang": bang, "ev_wf": ev_wf, "ev_is": ev_is, "muc_is": cac_muc[j_all],
            "lech": max(0.0, ev_is - ev_wf), "H": H}


def mo_phong_gop_nganh(nhom, df_ngay, ht, tren, duoi, giua, n):
    """
    [MỚI] Gộp các mã cùng ngành vào mô phỏng để tăng số mẫu hiệu dụng. Các mốc % của kế hoạch được CHUẨN HOÁ
    theo biến động: mốc % của mã khác = mốc % của mã phân tích × (σ mã khác / σ mã phân tích), σ = 1 năm.
    Mỗi mã có trọng số giảm dần theo tuổi riêng; kết quả gồm cả chính mã đang phân tích.
    """
    s0 = np.log(df_ngay.close).diff().tail(252).std()
    p = lambda g: (g / ht - 1) * 100
    phan, chi_tiet = [], []
    for ma, d in [("(mã phân tích)", df_ngay)] + list((nhom or {}).items()):
        if d is None or len(d) < n + 120:
            continue
        k = float(np.clip(np.log(d.close).diff().tail(252).std() / s0, 0.5, 2.0)) if s0 > 0 else 1.0
        sim = _mo_phong(d, n, tren=p(tren) * k, duoi=p(duoi) * k, giua=p(giua) * k)
        if sim is None:
            continue
        sim = sim.assign(w=_trong_so_gan_day(len(sim), len(d)), ma=ma)
        phan.append(sim)
        chi_tiet.append([ma, len(sim), k])
    if len(phan) < 2:
        return None, chi_tiet
    gop = pd.concat(phan, ignore_index=True)
    return _tong_hop(gop, None, "tron", tong=len(gop) + n, n=n), chi_tiet


# ==========================================================================
# 10. PHẦN D – KỊCH BẢN GIÁ (gắn với mục tiêu & cắt lỗ thống nhất)
# ==========================================================================
def _xs_cham_mot_phia(df, p, n, cua_so=None, tron=False, mask=None):
    """% giai đoạn n phiên có giá CAO (p ≥ 0) / THẤP (p < 0) chạm mức p%, và số phiên trung vị để chạm.
    cua_so: chỉ xét điểm bắt đầu trong 'cua_so' phiên gần nhất; tron: trọng số giảm dần theo tuổi."""
    c = df.close.values
    ref = df.high.values if p >= 0 else df.low.values
    N = len(c) - n
    i0 = max(0, len(c) - cua_so) if cua_so else 0
    if N - i0 < (20 if cua_so else 30):
        return np.nan, np.nan
    W = _cua_so_truot(ref[1:], n)[i0:N] / c[i0:N, None] * 100 - 100
    hit = (W >= p) if p >= 0 else (W <= p)
    co = hit.any(1)
    t = hit.argmax(1) + 1
    w = _trong_so_gan_day(N, len(c))[i0:] if tron else np.ones(N - i0)
    if mask is not None:
        w = w * np.asarray(mask, float)[i0:N]
        if (w > 0).sum() < 20:
            return np.nan, np.nan
    return _tb_trong_so(co, w) * 100, (float(np.median(t[co & (w > 0)])) if (co & (w > 0)).any() else np.nan)


# ==========================================================================
# 10C. PHẦN E – ĐỀ XUẤT GIÁ MỤC TIÊU & QUẢN TRỊ RỦI RO
# ==========================================================================
def _upside_toi_da(df, H):
    """Với mỗi phiên quá khứ i: % tăng tối đa (giá CAO) đạt được trong H phiên kế tiếp."""
    fwd = df.high.iloc[::-1].rolling(H, min_periods=H).max().iloc[::-1].shift(-1)
    return ((fwd / df.close - 1) * 100).dropna()
