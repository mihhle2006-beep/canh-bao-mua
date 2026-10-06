# -*- coding: utf-8 -*-
"""Vẽ biểu đồ (matplotlib)."""
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
    DINH_DAY_THEO, KEO_DAI, MAU_MA, MA_DAI, MA_NGAN, SO_NEN_HIEN_THI,
)
from .in_an import (
    in_ra,
)
from .chi_bao import (
    _duong, them_ma,
)


# ==========================================================================
# KIỂU CHUNG [MỚI]: chú giải nền trắng đục, nhãn giá đặt NGOÀI vùng vẽ (không đè lên đường kẻ / nến)
# ==========================================================================
plt.rcParams.update({"legend.framealpha": 0.92, "legend.edgecolor": "0.8", "axes.spines.top": False,
                     "axes.titlepad": 10, "axes.titlecolor": "#1B5E20", "axes.edgecolor": "0.55",
                     "figure.facecolor": "white"})
_XANH_DAM, _XANH_NGOC = "#1B5E20", "#00897B"
_NEN_NHAN = dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.95, lw=0.7)


def nhan_muc_gia(a, muc, phia="phai", khoang=0.045, co_chu=8):
    """
    Ghi nhãn cho các đường giá ngang: muc = [(giá, chữ, màu, đậm)].
    Nhãn nằm NGOÀI trục (lề phải) hoặc sát mép trái bên trong, có khung trắng, tự giãn cách để không chồng nhau,
    nối về đúng mức giá bằng 1 nét mảnh → chữ không đè lên đường kẻ, nến hay nhau.
    """
    from matplotlib.transforms import blended_transform_factory
    ylo, yhi = a.get_ylim()
    gap = khoang * (yhi - ylo)
    ds = sorted([m for m in muc if m[0] is not None and m[0] == m[0] and ylo <= m[0] <= yhi], key=lambda t: t[0])
    if not ds:
        return
    vt = [m[0] for m in ds]
    for i in range(1, len(vt)):                       # đẩy lên cho đủ khoảng cách
        vt[i] = max(vt[i], vt[i - 1] + gap)
    tran = yhi - gap * 0.5
    if vt[-1] > tran:                                 # tràn trên → dồn xuống
        vt[-1] = tran
        for i in range(len(vt) - 2, -1, -1):
            vt[i] = min(vt[i], vt[i + 1] - gap)
    tr = blended_transform_factory(a.transAxes, a.transData)
    x_moc, x_chu, ha = (1.0, 1.012, "left") if phia == "phai" else (0.0, 0.008, "left")
    for (g, chu, mau, dam), y in zip(ds, vt):
        a.annotate(chu, xy=(x_moc, g), xycoords=tr, xytext=(x_chu, y), textcoords=tr, va="center", ha=ha,
                   fontsize=co_chu, color=mau, fontweight="bold" if dam else "normal",
                   bbox={**_NEN_NHAN, "edgecolor": mau}, annotation_clip=False, zorder=10,
                   arrowprops=dict(arrowstyle="-", color=mau, lw=0.6, shrinkA=0, shrinkB=0))


def _so_vn_bieu_do(fig):
    """Đổi mọi chữ số trên biểu đồ sang kiểu Việt Nam (1.234,5): chữ/chú giải/nhãn + trục số."""
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter, ScalarFormatter
    from .so import BAT_SO_VN, vn_hoa
    if not BAT_SO_VN:
        return
    for t in fig.findobj(Text):
        s = t.get_text()
        if s:
            t.set_text(vn_hoa(s))
    for ax in fig.axes:
        for truc in (ax.xaxis, ax.yaxis):
            if isinstance(truc.get_major_formatter(), ScalarFormatter):
                truc.set_major_formatter(FuncFormatter(lambda v, p: vn_hoa(format(v, ",.6g"))))


def _luu(fig, file_png, dpi=120):
    _so_vn_bieu_do(fig)
    fig.savefig(file_png, dpi=dpi, bbox_inches="tight", pad_inches=0.25)


# ==========================================================================
# 7. VẼ BIỂU ĐỒ CHO TỪNG KHUNG
# ==========================================================================
def ve_duong_ma(a, x, d, don_vi="phiên"):
    """Vẽ MA50 & MA200 (tính trên giá đóng cửa, đã tính từ TOÀN BỘ dữ liệu trước khi cắt khung hiển thị).
    d phải có sẵn cột MA50/MA200. Chú thích ghi giá trị MA hiện tại và giá đang trên/dưới MA."""
    ht = d.close.iloc[-1]
    for n in (MA_NGAN, MA_DAI):
        cot = f"MA{n}"
        if cot not in d or d[cot].notna().sum() == 0:
            continue
        gt = d[cot].iloc[-1]
        nhan = f"MA{n} ({n} {don_vi})"
        if gt == gt:
            nhan += f": {gt:,.2f} – giá {'TRÊN' if ht >= gt else 'DƯỚI'} ({(ht / gt - 1) * 100:+.1f}%)"
        a.plot(x, d[cot].values, color=MAU_MA[n], lw=1.4 if n == MA_DAI else 1.2, zorder=3, label=nhan)
    # Giao cắt vàng / tử thần trong khung đang vẽ
    if {f"MA{MA_NGAN}", f"MA{MA_DAI}"} <= set(d.columns):
        tren = (d[f"MA{MA_NGAN}"] > d[f"MA{MA_DAI}"]).astype(float).where(d[f"MA{MA_DAI}"].notna())
        doi = tren.diff()
        for i in np.where(doi.values == 1)[0]:
            a.scatter(x[i], d[f"MA{MA_NGAN}"].iloc[i], marker="*", s=140, color="gold", edgecolors="black", zorder=6)
        for i in np.where(doi.values == -1)[0]:
            a.scatter(x[i], d[f"MA{MA_NGAN}"].iloc[i], marker="X", s=90, color="black", zorder=6)


def _gia_dong_tai(d, x):
    """[MỚI] Giá ĐÓNG CỬA của nến tại vị trí x → điểm vẽ đỉnh/đáy luôn nằm trên thân nến, không chạm râu."""
    return d.close.values[np.asarray(x, int)]


def ve_zigzag_dong_cua(a, d, pv, ghi_nhan=True):
    """Vẽ đường nối đỉnh–đáy lên trục 'a' có trục x = 0..len(d)-1 (đỉnh/đáy tạm thời: vòng tròn rỗng).
    [SỬA] Mọi điểm nối là GIÁ ĐÓNG CỬA của nến đỉnh/đáy (không vẽ tới râu nến)."""
    if pv is None or not len(pv):
        return
    p = pv[pv.time >= d.index[0]]
    if not len(p):
        return
    x = d.index.get_indexer(p.time)
    p, x = p[x >= 0], x[x >= 0]
    if not len(x):
        return
    y = _gia_dong_tai(d, x)
    xn = p.xac_nhan.values
    a.plot(x[xn], y[xn], color=_XANH_NGOC, lw=1.6, marker="o", ms=4, zorder=4,
           label="Đường nối đỉnh–đáy xác nhận (giá đóng cửa)")
    if xn.any():          # nét chấm: từ đỉnh/đáy XÁC NHẬN cuối tới giá hiện tại
        a.plot([x[xn][-1], len(d) - 1], [y[xn][-1], d.close.iloc[-1]], color=_XANH_NGOC, lw=1, ls=":")
    if (~xn).any():
        a.scatter(x[~xn], y[~xn], facecolors="none", edgecolors=_XANH_NGOC, s=40, zorder=5,
                  label="Đỉnh/đáy tạm thời (chưa dùng)")
    if ghi_nhan:
        bd = d.close.max() - d.close.min()
        for xi, yi, (_, r) in zip(x, y, p.iterrows()):
            la_dinh = r.loai == "Đỉnh"
            a.annotate(f"{yi:,.2f}", (xi, yi + (0.025 if la_dinh else -0.025) * bd), ha="center",
                       va="bottom" if la_dinh else "top", fontsize=7, color="red" if la_dinh else "green",
                       bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.8),
                       zorder=6)


# ==========================================================================
# 7b. BIỂU ĐỒ NẾN THEO KHUNG
# ==========================================================================
def ve_khung(symbol, ten_khung, df, pv, xh, mt, file_png, stop=None):
    n_ht = SO_NEN_HIEN_THI[ten_khung]
    x0 = max(0, len(df) - n_ht)
    x_cuoi = len(df) - 1 + KEO_DAI[ten_khung]
    d = df.iloc[x0:]
    x = d.pos.values

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(16, 11), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1.1, 0.9]})

    tang = d.close >= d.open
    mau = np.where(tang, "#26a69a", "#ef5350")
    a1.vlines(x, d.low, d.high, color=mau, lw=0.8)
    a1.bar(x, (d.close - d.open).abs().clip(lower=d.close * 0.0005),
           bottom=np.minimum(d.open, d.close), color=mau, width=0.7)

    # [SỬA] Điểm đỉnh/đáy vẽ tại GIÁ ĐÓNG CỬA của nến đỉnh/đáy (gia_ve) → đường nối không chạm râu nến
    p = pv[pv.pos >= x0 - 1].copy()
    p["gia_ve"] = _gia_dong_tai(df, p.pos.values)
    kc_dt = (d.high.max() - d.low.min())
    a1.plot(x, d.close, color="black", lw=0.7, alpha=0.45, label="Giá đóng cửa")
    ve_duong_ma(a1, x, d, {"Tuần": "tuần", "Ngày": "phiên", "Giờ": "giờ"}[ten_khung])
    px = p[p.xac_nhan]
    a1.plot(px.pos, px.gia_ve, color=_XANH_NGOC, lw=1.8, alpha=0.9, zorder=4, marker="o", ms=3.5,
            label="Đỉnh–đáy XÁC NHẬN theo giá đóng cửa (MACD)")
    if len(p):
        a1.plot([p.pos.iloc[-1], d.pos.iloc[-1]], [p.gia_ve.iloc[-1], d.close.iloc[-1]],
                color=_XANH_NGOC, lw=1, ls=":", zorder=4)
    for _, r in p.iterrows():
        la_dinh = r.loai == "Đỉnh"
        # Ký hiệu ▼/▲ đặt NGOÀI râu nến (high/low) để không che nến; con số là giá đóng cửa
        neo = df.high.iloc[int(r.pos)] if la_dinh else df.low.iloc[int(r.pos)]
        a1.scatter(r.pos, neo + (0.02 if la_dinh else -0.02) * kc_dt, marker="v" if la_dinh else "^",
                   color="red" if la_dinh else "green", s=70, zorder=5,
                   edgecolors="black" if not r.xac_nhan else "none")
        a1.annotate(f"{r.gia_ve:,.2f}" + ("" if r.xac_nhan else " (tạm)"),
                    (r.pos, neo + (0.045 if la_dinh else -0.045) * kc_dt), ha="center",
                    va="bottom" if la_dinh else "top", fontsize=7, color="red" if la_dinh else "green",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.8),
                    zorder=6)

    for khoa, mau_l, ten in (("khang_cu", "red", "Kháng cự"), ("ho_tro", "green", "Hỗ trợ")):
        l = _duong(xh, khoa)
        if l:
            xs = np.array([l["x1"], x_cuoi])
            a1.plot(xs, l["y1"] + l["doc"] * (xs - l["x1"]), color=mau_l, lw=1.6,
                    ls="-" if l["xac_nhan"] else "--",
                    label=f"Đường {ten} ({l['so_cham']} lần chạm{', đã xác nhận' if l['xac_nhan'] else ''})")

    nhan_gia = []
    if mt is not None:
        ymax_ve = d.high.max() * 1.4
        for _, r in mt["top"].iterrows():
            if r["Giá mục tiêu"] > ymax_ve:
                continue
            chinh = mt["chinh"] is not None and r["Giá mục tiêu"] == mt["chinh"]["Giá mục tiêu"]
            a1.axhline(r["Giá mục tiêu"], color="darkgreen" if chinh else "olive",
                       ls="-" if chinh else ":", lw=1.6 if chinh else 1)
            ev = r["EV %"]
            nhan_gia.append((r["Giá mục tiêu"], f"{'★ ' if chinh else ''}{r['Giá mục tiêu']:,.2f} "
                             f"({r['Upside %']:+.1f}%, EV {ev:+.1f}%) – {r['Phương pháp']}",
                             "darkgreen" if chinh else "olive", chinh))
    if stop is not None and ten_khung != "Giờ":
        a1.axhline(stop["gia"], color="red", ls="--", lw=1)
        nhan_gia.append((stop["gia"], f"Cắt lỗ {stop['gia']:,.2f} ({stop['pct']:+.1f}%)", "red", True))

    a1.set_title(f"{symbol} – Biểu đồ {ten_khung.upper()} | Cấu trúc (đỉnh/đáy xác nhận): {xh['cau_truc']}",
                 fontsize=12)
    a1.legend(loc="best", fontsize=8)                     # tự chọn góc ít đè lên giá nhất
    a1.grid(alpha=0.25)
    a1.set_xlim(x0 - 1, x_cuoi + KEO_DAI[ten_khung] * 1.15)
    lo_, hi_ = a1.get_ylim()
    a1.set_ylim(lo_ - 0.04 * (hi_ - lo_), hi_ + 0.08 * (hi_ - lo_))   # chừa chỗ cho nhãn đỉnh/đáy ở mép
    nhan_muc_gia(a1, nhan_gia, co_chu=7)

    a2.bar(x, d.HIST, color=np.where(d.HIST >= 0, "#26a69a", "#ef5350"), width=0.8, alpha=0.6)
    a2.plot(x, d.MACD, color=_XANH_DAM, lw=1.2, label="MACD")
    a2.plot(x, d.SIGNAL, color="tab:orange", lw=1, label="Signal")
    a2.axhline(0, color="black", lw=1)
    a2.fill_between(x, 0, d.MACD, where=d.MACD > 0, color="green", alpha=0.07)
    a2.fill_between(x, 0, d.MACD, where=d.MACD < 0, color="red", alpha=0.07)
    m, s = d.MACD.values, d.SIGNAL.values
    for i in range(1, len(d)):
        if m[i] > s[i] and m[i - 1] <= s[i - 1] and m[i] < 0:
            a2.scatter(x[i], m[i], marker="^", color="green", s=35, zorder=5)
        if m[i] > 0 and m[i - 1] <= 0:
            a2.scatter(x[i], m[i], marker="o", color="darkgreen", s=35, zorder=5)
    a2.set_ylabel("MACD")
    a2.legend(loc="best", fontsize=8)
    a2.grid(alpha=0.25)

    # [MỚI] Khối lượng + OBV
    a3.bar(x, d.volume, color=mau, width=0.8, alpha=0.6)
    a3.plot(x, d.VolMA20, color="black", lw=1, label="KL TB20")
    a3.set_ylabel("Khối lượng")
    a3.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e6:,.1f}M"))
    a3b = a3.twinx()
    a3b.plot(x, d.OBV, color="tab:purple", lw=1.1, label="OBV")
    a3b.set_yticks([])
    h1, l1 = a3.get_legend_handles_labels()
    h2, l2 = a3b.get_legend_handles_labels()
    a3.legend(h1 + h2, l1 + l2, loc="best", fontsize=8)
    a3.grid(alpha=0.25)

    fmt_t = "%d/%m %Hh" if ten_khung == "Giờ" else "%m/%Y" if ten_khung == "Tuần" else "%d/%m/%y"
    buoc = max(1, len(d) // 10)
    a3.set_xticks(x[::buoc])
    a3.set_xticklabels([t.strftime(fmt_t) for t in d.index[::buoc]], rotation=30, fontsize=8)

    fig.text(0.01, 0.005, "▲ xanh: MACD cắt lên Signal dưới 0 (mua sớm)   ● xanh đậm: MACD cắt lên 0 (xác nhận)"
             f"   ★ vàng: MA{MA_NGAN} cắt lên MA{MA_DAI}   ✖ đen: cắt xuống"
             "   Đỉnh/đáy viền đen = tạm thời (không dùng)   Đường xu hướng nét đứt = < 3 lần chạm",
             fontsize=8, color="dimgray")
    plt.tight_layout()
    _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu biểu đồ {ten_khung}: {file_png}")
    return fig


def ve_kich_ban(symbol, df, kb, file_png, pv=None):
    """Biểu đồ: 120 phiên gần nhất + đường đi tới 3 kịch bản + vùng biên độ (σ EWMA)."""
    n, ht = kb["n"], df.close.iloc[-1]
    d = them_ma(df).tail(120)
    fig, a = plt.subplots(figsize=(15, 7))
    x0 = np.arange(len(d))
    a.plot(x0, d.close, color="black", lw=1.3, label="Giá đóng cửa")
    ve_duong_ma(a, x0, d)
    ve_zigzag_dong_cua(a, d, pv)
    xf = np.arange(len(d) - 1, len(d) - 1 + n + 1)
    s = kb["sigma_ewma_nam"] / 100 / np.sqrt(252)
    t = np.arange(n + 1)
    a.fill_between(xf, ht * np.exp(-1.96 * s * np.sqrt(t)), ht * np.exp(1.96 * s * np.sqrt(t)),
                   color="#E8F5E9", alpha=0.9, label="Biên độ 95% (σ EWMA)")
    a.fill_between(xf, ht * np.exp(-s * np.sqrt(t)), ht * np.exp(s * np.sqrt(t)),
                   color="#C8E6C9", alpha=0.9, label="Biên độ 68% (σ EWMA)")
    mau = {"TÍCH CỰC": "tab:green", "CƠ SỞ – đạt MT cơ sở": _XANH_NGOC,
           "CƠ SỞ – đi ngang": "tab:gray", "TIÊU CỰC": "tab:red"}
    for _, r in kb["bang"].iterrows():
        tg = r["Số phiên trung vị"] if r["Số phiên trung vị"] == r["Số phiên trung vị"] else n
        x1 = len(d) - 1 + min(tg, n)
        xs = f"{r['XS trộn %']:.0f}%" if r["XS trộn %"] == r["XS trộn %"] else "N/A"
        a.plot([len(d) - 1, x1], [ht, r["Giá mục tiêu"]], color=mau[r["Kịch bản"]], lw=2, ls="--")
        a.scatter([x1], [r["Giá mục tiêu"]], color=mau[r["Kịch bản"]], zorder=5)
        a.annotate(f"{r['Kịch bản']} {r['Giá mục tiêu']:,.2f}\nXS trộn {xs} · KTC {r['KTC 90% (trộn)']}",
                   (x1, r["Giá mục tiêu"]), xytext=(8, 0), textcoords="offset points", fontsize=8,
                   color=mau[r["Kịch bản"]], va="center", annotation_clip=False, zorder=10,
                   bbox={**_NEN_NHAN, "edgecolor": mau[r["Kịch bản"]]})
    nhan_gia = []
    for g, ten, c in ((kb["kc"], "Breakout", "darkorange"), (kb["hotro"], "Hỗ trợ", "teal"),
                      (kb["cat_lo"], "Cắt lỗ", "red")):
        a.axhline(g, color=c, ls=":", lw=1)
        nhan_gia.append((g, f"{ten} {g:,.2f}", c, False))
    a.axvline(len(d) - 1, color="black", lw=0.8)
    a.set_xlim(0, len(d) + n + n * 0.6)
    buoc = max(1, len(d) // 8)
    a.set_xticks(x0[::buoc]); a.set_xticklabels([t_.strftime("%d/%m/%y") for t_ in d.index[::buoc]], fontsize=8)
    a.set_ylabel("Giá (nghìn đồng)"); a.grid(alpha=0.3); a.legend(loc="best", fontsize=8)
    a.set_title(f"{symbol} – 3 kịch bản trong {n} phiên tới | EV quyết định {kb['ev_qd']:+.2f}% "
                f"(xác suất = tần suất lịch sử, không phải dự báo)", fontweight="bold")
    nhan_muc_gia(a, nhan_gia)
    plt.tight_layout(); _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu biểu đồ kịch bản: {file_png}")
    return fig


def ve_bieu_do_tang_giam(symbol, pct, bang_phien, bang_kb, ht, file_png):
    fig, ax = plt.subplots(1, 3, figsize=(19, 6))

    ax[0].hist(pct, bins=50, color="#66BB6A", edgecolor="white")
    ax[0].axvline(0, color="black")
    ax[0].axvline(pct.mean(), color="orange", ls="--", label=f"TB {pct.mean():+.2f}%")
    ax[0].set_title("Phân phối % thay đổi theo ngày"); ax[0].set_xlabel("%"); ax[0].legend()

    co = bang_phien[bang_phien["Số phiên"] > 0]
    mau = dict(zip(bang_phien["Trường hợp"],
                   ["#1a9850", "#91cf60", "#bdbdbd", "#fc8d59", "#d73027", "#7b3294", "#00acc1"]))
    tong = co["Số phiên"].sum()
    w_, _, chu = ax[1].pie(co["Số phiên"], colors=[mau[t] for t in co["Trường hợp"]], startangle=90,
                           autopct=lambda p_: f"{p_:.0f}%" if p_ >= 5 else "", pctdistance=0.78,
                           wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5),
                           textprops={"fontsize": 8, "color": "black"})
    ax[1].legend(w_, [f"{t} – {n / tong * 100:.1f}%" for t, n in zip(co["Trường hợp"], co["Số phiên"])],
                 loc="center left", bbox_to_anchor=(0.92, 0.5), fontsize=8, frameon=False)
    ax[1].set_title("Tỷ lệ các trường hợp phiên")

    mau_kb = ["gold" if "★" in t else "darkred" if "✘" in t else "mediumpurple" if "✎" in t else
              "darkgreen" if "◆" in t else
              ("tab:green" if v >= 0 else "tab:red")
              for t, v in zip(bang_kb["Kịch bản"], bang_kb["% thay đổi"])]
    x_min = min(bang_kb["Giá mới"].min(), ht) * 0.85
    ax[2].barh(bang_kb["Kịch bản"], bang_kb["Giá mới"] - x_min, left=x_min, color=mau_kb, height=0.7)
    ax[2].axvline(ht, color="black", ls="--", lw=1, label=f"Giá hiện tại {ht:,.2f}", zorder=1)
    x_max = bang_kb["Giá mới"].max()
    for i, (v, p) in enumerate(zip(bang_kb["Giá mới"], bang_kb["% thay đổi"])):
        ax[2].text(x_max * 1.02, i, f"{v:,.2f}  ({p:+.1f}%)", va="center", ha="left", fontsize=8,
                   color="tab:green" if p >= 0 else "tab:red")          # nhãn đặt ở CỘT RIÊNG bên phải
    ax[2].set_xlim(x_min, x_max * 1.22)
    ax[2].invert_yaxis(); ax[2].legend(fontsize=8, loc="lower right")
    ax[2].set_title("Giá theo kịch bản (nghìn đồng)"); ax[2].grid(axis="x", alpha=0.3)

    fig.suptitle(f"{symbol} – Phân tích % tăng/giảm & kịch bản giá", fontsize=14, color=_XANH_DAM)
    plt.tight_layout()
    _luu(fig, file_png, dpi=125)
    in_ra(f"  ✔ Đã lưu biểu đồ % tăng/giảm: {file_png}")
    return fig


def ve_quan_tri_rui_ro(symbol, df, dx, qr, file_png, pv=None, ctck=None):
    d = them_ma(df).tail(250)
    ht = d.close.iloc[-1]
    fig, a = plt.subplots(figsize=(15, 7))
    x = np.arange(len(d))
    a.plot(x, d.close, color="black", lw=1.2, label="Giá đóng cửa")
    ve_duong_ma(a, x, d)
    ve_zigzag_dong_cua(a, d, pv)
    a.axhspan(dx["san"], dx["tran"], color="green", alpha=0.08, label="Vùng mục tiêu hợp lý")
    nhan_gia = []
    if dx["mt_nhap"] and abs(dx["mt_nhap"] - dx["chon"]) > 1e-9:
        a.axhline(dx["mt_nhap"], color="mediumpurple", ls="--", lw=1.2)
        nhan_gia.append((dx["mt_nhap"], f"MT tự định {dx['mt_nhap']:,.2f}", "mediumpurple", False))
    a.axhline(dx["chon"], color="darkgreen", lw=2)
    nhan_gia.append((dx["chon"], f"★ MT đề xuất {dx['chon']:,.2f} ({dx['hanh_dong']})", "darkgreen", True))
    for (ten, g), c in zip(((("TP1", qr["tp"][0]), ("TP2", qr["tp"][1])) if not qr["phong_thu"] else ()),
                           ("tab:olive", "tab:olive")):
        a.axhline(g, color=c, ls=":", lw=1)
        nhan_gia.append((g, f"{ten} {g:,.2f}", c, False))
    for ten, g, c in (("Mua lại (≤ GTHL −10%)" if qr["phong_thu"] else "Mua tối đa (R/R≥2)", qr["gia_mua_rr2"], _XANH_NGOC),
                      ("Cảnh báo sớm", qr["canh_bao_som"], "orange"),
                      ("CẮT LỖ (thống nhất)", qr["lo_ap_dung"], "red")):
        if g is None or g != g:
            continue
        a.axhline(g, color=c, ls="--", lw=1.2)
        nhan_gia.append((g, f"{ten} {g:,.2f} ({(g / ht - 1) * 100:+.1f}%)", c, ten.startswith("CẮT")))
    for ct, (t, g, kn) in (ctck or {}).items():
        a.axhline(g, color="purple", ls=(0, (1, 3)), lw=1)
        nhan_gia.append((g, f"{ct} {g:,.1f} ({kn}, {t:%m/%Y})", "purple", False))
    a.axhspan(qr["lo_ap_dung"], ht, xmin=0.75, color="red", alpha=0.05)
    a.set_xlim(0, len(d) + 15)
    buoc = max(1, len(d) // 8)
    a.set_xticks(x[::buoc]); a.set_xticklabels([t.strftime("%d/%m/%y") for t in d.index[::buoc]], fontsize=8)
    a.set_ylabel("Giá (nghìn đồng)"); a.grid(alpha=0.3); a.legend(loc="best", fontsize=8)
    nhan = "kế hoạch PHÒNG THỦ" if qr["phong_thu"] else f"R/R {qr['rr']:.2f}"
    a.set_title(f"{symbol} – Mục tiêu đề xuất & các mức quản trị rủi ro ({nhan})", fontweight="bold")
    nhan_muc_gia(a, nhan_gia)
    plt.tight_layout(); _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu biểu đồ quản trị rủi ro: {file_png}")
    return fig


def ve_khoi_luong(symbol, d, kl, file_png):
    p = d.tail(kl["so_phien"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 6), sharey=True, gridspec_kw={"width_ratios": [3, 1]})
    a.plot(np.arange(len(p)), p.close, color="black", lw=1.2, label="Giá đóng cửa")
    nhan_gia = []
    for g, ten, c in ((kl["poc"], "POC", "tab:red"), (kl["vah"], "VAH", "tab:green"), (kl["val"], "VAL", "tab:green")):
        a.axhline(g, color=c, ls="--", lw=1)
        nhan_gia.append((g, f"{ten} {g:,.2f}", c, ten == "POC"))
    buoc = max(1, len(p) // 8)
    a.set_xticks(np.arange(len(p))[::buoc])
    a.set_xticklabels([t.strftime("%d/%m/%y") for t in p.index[::buoc]], fontsize=8)
    a.legend(loc="upper left", fontsize=8); a.grid(alpha=0.3); a.set_ylabel("Giá (nghìn đồng)")
    pr = kl["profile"]
    h = (pr["Giá giữa"].iloc[1] - pr["Giá giữa"].iloc[0]) * 0.9 if len(pr) > 1 else 1
    mau = ["tab:red" if abs(g - kl["poc"]) < 1e-9 else ("tab:green" if kl["val"] <= g <= kl["vah"] else "lightgray")
           for g in pr["Giá giữa"]]
    b.barh(pr["Giá giữa"], pr["Khối lượng"], height=h, color=mau)
    b.set_title("Volume profile"); b.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e6:,.0f}M"))
    fig.suptitle(f"{symbol} – Khối lượng theo vùng giá {kl['so_phien']} phiên", fontweight="bold", color=_XANH_DAM)
    nhan_muc_gia(a, nhan_gia, phia="trai")
    plt.tight_layout(); _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu biểu đồ khối lượng: {file_png}")
    return fig


def ve_boi_canh(symbol, df, vni, nhom, bc, file_png):
    fig, (a, b) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    goc = df.index[-1] - pd.Timedelta(days=370)
    cuoi = []
    for ten, s, kw in [(symbol, df.close, dict(color="black", lw=2))] + \
            ([("VNINDEX", vni.close, dict(color="#78909C", lw=1.6))] if vni is not None else []) + \
            [(m, d.close, dict(lw=0.9, alpha=0.7)) for m, d in (nhom or {}).items()]:
        s = s[(s.index >= goc) & (s.index <= df.index[-1])]
        if len(s) > 5:
            ln, = a.plot(s.index, s / s.iloc[0] * 100, label=ten, **kw)
            y = float(s.iloc[-1] / s.iloc[0] * 100)
            cuoi.append((y, f"{ten} {y - 100:+.0f}%", ln.get_color(), ten == symbol))
    a.axhline(100, color="gray", lw=0.8)
    a.set_ylabel("Chuẩn hoá = 100"); a.legend(fontsize=8, ncol=4, loc="upper left"); a.grid(alpha=0.3)
    nhan_muc_gia(a, cuoi, khoang=0.06)                     # % thay đổi 1 năm ghi ở lề phải, không đè đường
    import matplotlib.dates as mdates
    b.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    a.set_title(f"{symbol} so với VN-Index & nhóm ngành (1 năm)", fontweight="bold")
    if bc["rs"]:
        rs, ma = bc["rs"]["chuoi"], bc["rs"]["ma50"]
        m = rs.index >= goc
        b.plot(rs.index[m], rs[m], color="tab:purple", label=f"RS {symbol}/VN-Index")
        b.plot(ma.index[m], ma[m], color="orange", lw=1, label="RS MA50")
        b.legend(fontsize=8); b.grid(alpha=0.3); b.set_ylabel("RS")
    plt.tight_layout(); _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu biểu đồ bối cảnh thị trường: {file_png}")
    return fig


# ==========================================================================
# [MỚI] ẢNH TÓM TẮT 1 TRANG – biểu đồ giá + các mức + số liệu chính (dán vào báo cáo / gửi Zalo)
# ==========================================================================
def ve_tom_tat_1_trang(symbol, df, ngay, ht, qd, stop, qr, dx, kb, fj, file_png):
    from .so import vn_hoa
    d = them_ma(df).tail(140)
    fig = plt.figure(figsize=(16, 8.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.1, 1], wspace=0.32)
    a = fig.add_subplot(gs[0])
    x = np.arange(len(d))
    a.plot(x, d.close, color="black", lw=1.4, label="Giá đóng cửa")
    ve_duong_ma(a, x, d)
    vung_mua = (max(stop["gia"] * 1.01, min(ht, qr["gia_mua_rr2"]) * 0.97), min(ht, qr["gia_mua_rr2"]))
    a.axhspan(*vung_mua, color="#A5D6A7", alpha=0.45, label="Vùng mua")
    muc = [(dx["chon"], f"★ MT {dx['chon']:,.2f}", _XANH_DAM, True),
           (stop["gia"], f"CL {stop['gia']:,.2f}", "red", True)]
    if not qr["phong_thu"]:
        muc.append((qr["tp"][0], f"TP1 {qr['tp'][0]:,.2f}", "#7CB342", False))
    for g, _, c, dam in muc:
        a.axhline(g, color=c, ls="-" if dam else "--", lw=1.6 if dam else 1)
    lo_, hi_ = a.get_ylim()
    a.set_ylim(min(lo_, stop["gia"] * 0.97), max(hi_, dx["chon"] * 1.03))
    buoc = max(1, len(d) // 7)
    a.set_xticks(x[::buoc]); a.set_xticklabels([t.strftime("%d/%m") for t in d.index[::buoc]], fontsize=8)
    a.grid(alpha=0.25); a.legend(loc="best", fontsize=8)
    a.set_title(f"Giá 140 phiên gần nhất · vùng mua & các mức quản trị rủi ro", fontsize=11)
    nhan_muc_gia(a, [(g, vn_hoa(t), c, dam) for g, t, c, dam in muc])

    b = fig.add_subplot(gs[1]); b.axis("off")
    fa = (fj or {}).get("fa") or {}
    j4 = (fj or {}).get("J4")
    bd = ""
    if j4 is not None and symbol in j4 and "VN-Index" in j4:
        r = j4.set_index("Khung").loc["1 năm"]
        bd = f"{r[symbol]:+.1f}% (VN-Index {r['VN-Index']:+.1f}%)"
    dong = [("KHUYẾN NGHỊ", qd["khuyen_nghi"], qd.get("mau", _XANH_DAM)),
            ("Giá", f"{ht:,.2f} nghìn đồng", "black"),
            ("Vùng mua", f"{vung_mua[0]:,.2f} – {vung_mua[1]:,.2f}", _XANH_DAM),
            ("Cắt lỗ", f"{stop['gia']:,.2f} ({stop['pct']:+.1f}%)", "red"),
            ("MT đề xuất", f"{dx['chon']:,.2f} ({(dx['chon'] / ht - 1) * 100:+.1f}%)", _XANH_DAM),
            ("R/R · EV", f"{qr['rr']:.2f} · {kb['ev_qd']:+.2f}%", "black"),
            ("XS chạm cắt lỗ", f"{kb['xs_cham_stop']:.0f}% / {kb['n']} phiên", "black"),
            ("Tài chính 10 tiêu chí", (f"{fa['diem']:.0f}/100 · {fa['so_nguy_hiem']} nguy hiểm"
                                       if fa and fa.get("diem") == fa.get("diem") else "chưa có dữ liệu"), "black"),
            ("Biến động 1 năm", bd or "–", "black")]
    y = 0.97
    for nhan, gt, mau in dong:
        b.text(0.0, y, nhan, fontsize=10, color="#616161", transform=b.transAxes, va="top")
        b.text(0.0, y - 0.045, vn_hoa(str(gt)), fontsize=15 if nhan == "KHUYẾN NGHỊ" else 13, fontweight="bold",
               color=mau, transform=b.transAxes, va="top")
        y -= 0.108
    fig.suptitle(f"{symbol} – TÓM TẮT PHÂN TÍCH · phiên {ngay:%d/%m/%Y}", fontsize=16, fontweight="bold",
                 color=_XANH_DAM)
    fig.text(0.01, 0.005, "Công cụ tham khảo dựa trên dữ liệu quá khứ – không phải khuyến nghị đầu tư.",
             fontsize=8, color="#757575")
    _luu(fig, file_png)
    in_ra(f"  ✔ Đã lưu ảnh tóm tắt 1 trang: {file_png}")
    return fig
