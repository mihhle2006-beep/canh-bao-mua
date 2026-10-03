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
    a.plot(x[xn], y[xn], color="royalblue", lw=1.6, marker="o", ms=4, zorder=4,
           label="Đường nối đỉnh–đáy xác nhận (giá đóng cửa)")
    if xn.any():          # nét chấm: từ đỉnh/đáy XÁC NHẬN cuối tới giá hiện tại
        a.plot([x[xn][-1], len(d) - 1], [y[xn][-1], d.close.iloc[-1]], color="royalblue", lw=1, ls=":")
    if (~xn).any():
        a.scatter(x[~xn], y[~xn], facecolors="none", edgecolors="royalblue", s=40, zorder=5,
                  label="Đỉnh/đáy tạm thời (chưa dùng)")
    if ghi_nhan:
        bd = d.close.max() - d.close.min()
        for xi, yi, (_, r) in zip(x, y, p.iterrows()):
            la_dinh = r.loai == "Đỉnh"
            a.annotate(f"{yi:,.2f}", (xi, yi + (0.025 if la_dinh else -0.025) * bd), ha="center",
                       va="bottom" if la_dinh else "top", fontsize=7, color="red" if la_dinh else "green")


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
    a1.plot(px.pos, px.gia_ve, color="royalblue", lw=1.8, alpha=0.9, zorder=4, marker="o", ms=3.5,
            label="Đỉnh–đáy XÁC NHẬN theo giá đóng cửa (MACD)")
    if len(p):
        a1.plot([p.pos.iloc[-1], d.pos.iloc[-1]], [p.gia_ve.iloc[-1], d.close.iloc[-1]],
                color="royalblue", lw=1, ls=":", zorder=4)
    for _, r in p.iterrows():
        la_dinh = r.loai == "Đỉnh"
        # Ký hiệu ▼/▲ đặt NGOÀI râu nến (high/low) để không che nến; con số là giá đóng cửa
        neo = df.high.iloc[int(r.pos)] if la_dinh else df.low.iloc[int(r.pos)]
        a1.scatter(r.pos, neo + (0.02 if la_dinh else -0.02) * kc_dt, marker="v" if la_dinh else "^",
                   color="red" if la_dinh else "green", s=70, zorder=5,
                   edgecolors="black" if not r.xac_nhan else "none")
        a1.annotate(f"{r.gia_ve:,.2f}" + ("" if r.xac_nhan else "\n(tạm)"),
                    (r.pos, neo + (0.045 if la_dinh else -0.045) * kc_dt), ha="center",
                    va="bottom" if la_dinh else "top", fontsize=7,
                    color="red" if la_dinh else "green")

    for khoa, mau_l, ten in (("khang_cu", "red", "Kháng cự"), ("ho_tro", "green", "Hỗ trợ")):
        l = _duong(xh, khoa)
        if l:
            xs = np.array([l["x1"], x_cuoi])
            a1.plot(xs, l["y1"] + l["doc"] * (xs - l["x1"]), color=mau_l, lw=1.6,
                    ls="-" if l["xac_nhan"] else "--",
                    label=f"Đường {ten} ({l['so_cham']} lần chạm{', đã xác nhận' if l['xac_nhan'] else ''})")

    if mt is not None:
        ymax_ve = d.high.max() * 1.4
        for _, r in mt["top"].iterrows():
            if r["Giá mục tiêu"] > ymax_ve:
                continue
            chinh = mt["chinh"] is not None and r["Giá mục tiêu"] == mt["chinh"]["Giá mục tiêu"]
            a1.axhline(r["Giá mục tiêu"], color="darkgreen" if chinh else "olive",
                       ls="-" if chinh else ":", lw=1.6 if chinh else 1)
            ev = r["EV %"]
            a1.text(x_cuoi, r["Giá mục tiêu"], f" {'★ ' if chinh else ''}{r['Giá mục tiêu']:,.2f} "
                    f"({r['Upside %']:+.1f}%, EV {ev:+.1f}%) {r['Phương pháp']}", fontsize=7, va="center",
                    color="darkgreen" if chinh else "olive", fontweight="bold" if chinh else "normal")
    if stop is not None and ten_khung != "Giờ":
        a1.axhline(stop["gia"], color="red", ls="--", lw=1)
        a1.text(x_cuoi, stop["gia"], f" Cắt lỗ thống nhất {stop['gia']:,.2f} ({stop['pct']:+.1f}%)",
                fontsize=7, va="center", color="red")

    a1.set_title(f"{symbol} – Biểu đồ {ten_khung.upper()} | Cấu trúc (đỉnh/đáy xác nhận): {xh['cau_truc']}",
                 fontsize=12)
    a1.legend(loc="upper left", fontsize=8)
    a1.grid(alpha=0.25)
    a1.set_xlim(x0 - 1, x_cuoi + (KEO_DAI[ten_khung] * 2.2))

    a2.bar(x, d.HIST, color=np.where(d.HIST >= 0, "#26a69a", "#ef5350"), width=0.8, alpha=0.6)
    a2.plot(x, d.MACD, color="tab:blue", lw=1.2, label="MACD")
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
    a2.legend(loc="upper left", fontsize=8)
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
    a3.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
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
    plt.savefig(file_png, dpi=120)
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
                   color="lightgray", alpha=0.5, label="Biên độ 95% (σ EWMA)")
    a.fill_between(xf, ht * np.exp(-s * np.sqrt(t)), ht * np.exp(s * np.sqrt(t)),
                   color="silver", alpha=0.6, label="Biên độ 68% (σ EWMA)")
    mau = {"TÍCH CỰC": "tab:green", "CƠ SỞ – đạt MT cơ sở": "tab:blue",
           "CƠ SỞ – đi ngang": "tab:gray", "TIÊU CỰC": "tab:red"}
    for _, r in kb["bang"].iterrows():
        tg = r["Số phiên trung vị"] if r["Số phiên trung vị"] == r["Số phiên trung vị"] else n
        x1 = len(d) - 1 + min(tg, n)
        xs = f"{r['XS trộn %']:.0f}%" if r["XS trộn %"] == r["XS trộn %"] else "N/A"
        a.plot([len(d) - 1, x1], [ht, r["Giá mục tiêu"]], color=mau[r["Kịch bản"]], lw=2, ls="--")
        a.scatter([x1], [r["Giá mục tiêu"]], color=mau[r["Kịch bản"]], zorder=5)
        a.annotate(f"{r['Kịch bản']} {r['Giá mục tiêu']:,.2f} (XS trộn {xs}, KTC {r['KTC 90% (trộn)']})",
                   (x1, r["Giá mục tiêu"]), xytext=(6, 0), textcoords="offset points", fontsize=8,
                   color=mau[r["Kịch bản"]], va="center")
    for g, ten, c in ((kb["kc"], "Breakout", "darkorange"), (kb["hotro"], "Hỗ trợ", "teal"),
                      (kb["cat_lo"], "Cắt lỗ", "red")):
        a.axhline(g, color=c, ls=":", lw=1)
        a.text(0, g, f" {ten} {g:,.2f}", color=c, fontsize=8, va="bottom")
    a.axvline(len(d) - 1, color="black", lw=0.8)
    a.set_xlim(0, len(d) + n + n * 0.6)
    buoc = max(1, len(d) // 8)
    a.set_xticks(x0[::buoc]); a.set_xticklabels([t_.strftime("%d/%m/%y") for t_ in d.index[::buoc]], fontsize=8)
    a.set_ylabel("Giá (nghìn đồng)"); a.grid(alpha=0.3); a.legend(loc="upper left", fontsize=8)
    a.set_title(f"{symbol} – 3 kịch bản trong {n} phiên tới | EV quyết định {kb['ev_qd']:+.2f}% "
                f"(xác suất = tần suất lịch sử, không phải dự báo)", fontweight="bold")
    plt.tight_layout(); plt.savefig(file_png, dpi=120)
    in_ra(f"  ✔ Đã lưu biểu đồ kịch bản: {file_png}")
    return fig


def ve_bieu_do_tang_giam(symbol, pct, bang_phien, bang_kb, ht, file_png):
    fig, ax = plt.subplots(1, 3, figsize=(19, 6))

    ax[0].hist(pct, bins=50, color="steelblue", edgecolor="white")
    ax[0].axvline(0, color="black")
    ax[0].axvline(pct.mean(), color="orange", ls="--", label=f"TB {pct.mean():+.2f}%")
    ax[0].set_title("Phân phối % thay đổi theo ngày"); ax[0].set_xlabel("%"); ax[0].legend()

    co = bang_phien[bang_phien["Số phiên"] > 0]
    mau = dict(zip(bang_phien["Trường hợp"],
                   ["#1a9850", "#91cf60", "#bdbdbd", "#fc8d59", "#d73027", "#7b3294", "#00acc1"]))
    ax[1].pie(co["Số phiên"], labels=co["Trường hợp"], colors=[mau[t] for t in co["Trường hợp"]],
              autopct="%1.1f%%", startangle=90, textprops={"fontsize": 8})
    ax[1].set_title("Tỷ lệ các trường hợp phiên")

    mau_kb = ["gold" if "★" in t else "darkred" if "✘" in t else "mediumpurple" if "✎" in t else
              "darkgreen" if "◆" in t else
              ("tab:green" if v >= 0 else "tab:red")
              for t, v in zip(bang_kb["Kịch bản"], bang_kb["% thay đổi"])]
    ax[2].barh(bang_kb["Kịch bản"], bang_kb["Giá mới"], color=mau_kb)
    ax[2].axvline(ht, color="black", ls="--", label=f"Giá hiện tại {ht:,.2f}")
    for i, (v, p) in enumerate(zip(bang_kb["Giá mới"], bang_kb["% thay đổi"])):
        ax[2].text(v, i, f" {v:,.2f} ({p:+.1f}%)", va="center", fontsize=8)
    ax[2].set_xlim(0, bang_kb["Giá mới"].max() * 1.25)
    ax[2].invert_yaxis(); ax[2].legend(fontsize=8); ax[2].set_title("Giá theo kịch bản (nghìn đồng)")

    fig.suptitle(f"{symbol} – Phân tích % tăng/giảm & kịch bản giá", fontsize=14)
    plt.tight_layout()
    plt.savefig(file_png, dpi=125)
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
    x_end = len(d) + 40
    a.axhspan(dx["san"], dx["tran"], color="green", alpha=0.08, label="Vùng mục tiêu hợp lý")
    nen = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1)
    if dx["mt_nhap"] and abs(dx["mt_nhap"] - dx["chon"]) > 1e-9:
        a.axhline(dx["mt_nhap"], color="mediumpurple", ls="--", lw=1.2)
        a.text(x_end, dx["mt_nhap"], f" MT tự định {dx['mt_nhap']:,.2f}", color="mediumpurple", fontsize=8, va="center", bbox=nen)
    a.axhline(dx["chon"], color="darkgreen", lw=2)
    a.text(x_end, dx["chon"], f" ★ MT đề xuất {dx['chon']:,.2f} ({dx['hanh_dong']})", color="darkgreen",
           fontsize=9, fontweight="bold", va="center", bbox=nen)
    for (ten, g), c in zip(((("TP1", qr["tp"][0]), ("TP2", qr["tp"][1])) if not qr["phong_thu"] else ()),
                           ("tab:olive", "tab:olive")):
        a.axhline(g, color=c, ls=":", lw=1)
        a.text(x_end, g, f" {ten} {g:,.2f}", color=c, fontsize=8, va="center", bbox=nen)
    for ten, g, c in (("Mua lại (≤ GTHL −10%)" if qr["phong_thu"] else "Mua tối đa (R/R≥2)", qr["gia_mua_rr2"], "tab:blue"),
                      ("Cảnh báo sớm", qr["canh_bao_som"], "orange"),
                      ("CẮT LỖ (thống nhất)", qr["lo_ap_dung"], "red")):
        if g is None or g != g:
            continue
        a.axhline(g, color=c, ls="--", lw=1.2)
        a.text(x_end, g, f" {ten} {g:,.2f} ({(g / ht - 1) * 100:+.1f}%)", color=c, fontsize=8, va="center", bbox=nen)
    for ct, (t, g, kn) in (ctck or {}).items():
        a.axhline(g, color="purple", ls=(0, (1, 3)), lw=1)
        a.text(x_end + 30, g, f" {ct} {g:,.1f} ({kn}, {t:%m/%Y})", color="purple", fontsize=7, va="bottom", bbox=nen)
    a.axhspan(qr["lo_ap_dung"], ht, xmin=0.75, color="red", alpha=0.05)
    a.set_xlim(0, x_end + 60)
    buoc = max(1, len(d) // 8)
    a.set_xticks(x[::buoc]); a.set_xticklabels([t.strftime("%d/%m/%y") for t in d.index[::buoc]], fontsize=8)
    a.set_ylabel("Giá (nghìn đồng)"); a.grid(alpha=0.3); a.legend(loc="upper left", fontsize=8)
    nhan = "kế hoạch PHÒNG THỦ" if qr["phong_thu"] else f"R/R {qr['rr']:.2f}"
    a.set_title(f"{symbol} – Mục tiêu đề xuất & các mức quản trị rủi ro ({nhan})", fontweight="bold")
    plt.tight_layout(); plt.savefig(file_png, dpi=120)
    in_ra(f"  ✔ Đã lưu biểu đồ quản trị rủi ro: {file_png}")
    return fig


def ve_khoi_luong(symbol, d, kl, file_png):
    p = d.tail(kl["so_phien"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 6), sharey=True, gridspec_kw={"width_ratios": [3, 1]})
    a.plot(np.arange(len(p)), p.close, color="black", lw=1.2, label="Giá đóng cửa")
    for g, ten, c in ((kl["poc"], "POC", "tab:red"), (kl["vah"], "VAH", "tab:green"), (kl["val"], "VAL", "tab:green")):
        a.axhline(g, color=c, ls="--", lw=1)
        a.text(0, g, f" {ten} {g:,.2f}", color=c, fontsize=8, va="bottom")
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
    fig.suptitle(f"{symbol} – Khối lượng theo vùng giá {kl['so_phien']} phiên", fontweight="bold")
    plt.tight_layout(); plt.savefig(file_png, dpi=120)
    in_ra(f"  ✔ Đã lưu biểu đồ khối lượng: {file_png}")
    return fig


def ve_boi_canh(symbol, df, vni, nhom, bc, file_png):
    fig, (a, b) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    goc = df.index[-1] - pd.Timedelta(days=370)
    for ten, s, kw in [(symbol, df.close, dict(color="black", lw=2))] + \
            ([("VNINDEX", vni.close, dict(color="tab:blue", lw=1.6))] if vni is not None else []) + \
            [(m, d.close, dict(lw=0.9, alpha=0.7)) for m, d in (nhom or {}).items()]:
        s = s[(s.index >= goc) & (s.index <= df.index[-1])]
        if len(s) > 5:
            a.plot(s.index, s / s.iloc[0] * 100, label=ten, **kw)
    a.axhline(100, color="gray", lw=0.8)
    a.set_ylabel("Chuẩn hoá = 100"); a.legend(fontsize=8, ncol=4); a.grid(alpha=0.3)
    a.set_title(f"{symbol} so với VN-Index & nhóm ngành (1 năm)", fontweight="bold")
    if bc["rs"]:
        rs, ma = bc["rs"]["chuoi"], bc["rs"]["ma50"]
        m = rs.index >= goc
        b.plot(rs.index[m], rs[m], color="tab:purple", label=f"RS {symbol}/VN-Index")
        b.plot(ma.index[m], ma[m], color="orange", lw=1, label="RS MA50")
        b.legend(fontsize=8); b.grid(alpha=0.3); b.set_ylabel("RS")
    plt.tight_layout(); plt.savefig(file_png, dpi=120)
    in_ra(f"  ✔ Đã lưu biểu đồ bối cảnh thị trường: {file_png}")
    return fig
