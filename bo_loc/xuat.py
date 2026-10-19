# -*- coding: utf-8 -*-
"""XUẤT KẾT QUẢ: in bảng, biểu đồ PNG, file Excel (kèm sheet nguồn dữ liệu & cảnh báo dữ liệu)."""
import sys

import matplotlib

if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")                     # chạy dòng lệnh/GitHub Actions: không cần màn hình
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import cau_hinh as ch  # noqa: E402
from .bang import ve_bang  # noqa: E402
from .tien_ich import co  # noqa: E402

COT_HIEN_THI = {"Mã": "Mã", "nhom": "Nhóm", "Đạt lọc": "Đạt", "gia": "Giá", "Điểm %": "Điểm %",
                "von_hoa": "Vốn hoá tỷ", "klgd20": "KLGD TB20", "pe": "P/E", "pb": "P/B", "roe": "ROE %",
                "ty_suat_co_tuc": "Cổ tức %", "vi_tri52": "Vị trí 52T %", "upside": "Upside 3R %",
                "khuyen_nghi": "Nhóm chiến lược"}

COT_XUAT = ["Mã", "nhom", "Đạt lọc", "Điểm", "Điểm %", "Thiếu", "gia", "khuyen_nghi", "cat_lo", "kc_cat_lo_pct", "gia_mt", "gia_mt_3r", "pp_mt", "upside",
            "rsi", "ma50", "ma200", "cau_truc_d", "cau_truc_w", "ret1t", "ret3t", "rs3t",
            "cach_dinh52", "tren_day52", "vi_tri52", "cao52", "thap52", "gtgd20", "klgd20", "vol_ratio", "beta",
            "st", "st_dir", "adx", "pdi", "mdi", "von_hoa", "so_cp", "pe", "pe_nguon", "pe_cach_tinh", "eps_dung", "ln_4q_ty", "ky_lnst", "eps_cot_loi", "ky_eps", "pb", "pb_cach_tinh", "nguon_so_cp",
            "so_nguon_so_cp", "cat_lo_theo", "ev_mt",
            "pb_nguon", "roe", "roa", "eps_ttm", "eps_nam", "eps_g_nam", "eps_quy", "eps_g_quy", "no_vay_tts",
            "no_phai_tra_tts", "fcf", "tt_hien_thoi", "tt_nhanh", "kiem_toan_5nam", "so_nam_co_tuc",
            "co_tuc_tien_mat_cp", "ty_suat_co_tuc", "atr", "atr_pct", "bien_dong", "mdd52", "cach_ma20",
            "dt_g_quy", "ln_g_quy", "bien_gop", "bien_gop_ck", "so_huu_nn", "free_float", "kiem_toan_ngoai_tru",
            "san", "nganh", "Thiếu dữ liệu", "nguon_gia", "nguon_co_ban", "nguon_chi_tieu", "canh_bao_du_lieu",
            "ghi_chu"]

# Tiêu đề cột hiển thị trong ket_qua_loc.xlsx (tên kỹ thuật có "_" → tiếng Việt); cột không có ở đây: "_" → " "
TEN_COT_EXCEL = {
    "khuyen_nghi": "Nhóm chiến lược", "cat_lo": "Cắt lỗ", "kc_cat_lo_pct": "Cách cắt lỗ %", "gia_mt": "Mục tiêu 1R",
    "gia_mt_3r": "Mục tiêu 3R", "MT 3R": "Mục tiêu 3R", "pp_mt": "Cách tính mục tiêu", "cau_truc_d": "Cấu trúc ngày",
    "cau_truc_w": "Cấu trúc tuần", "cach_dinh52": "Cách đỉnh 52T %", "tren_day52": "Trên đáy 52T %",
    "vi_tri52": "Vị trí 52T %", "vol_ratio": "Khối lượng so TB20 (lần)", "st_dir": "Hướng SuperTrend",
    "von_hoa": "Vốn hoá tỷ", "so_cp": "Số CP lưu hành", "pe_nguon": "Nguồn P/E", "pe_cach_tinh": "Cách tính P/E",
    "eps_dung": "EPS dùng", "ln_4q_ty": "LNST 4 quý (tỷ)", "ky_lnst": "Kỳ LNST", "eps_cot_loi": "EPS cốt lõi",
    "ky_eps": "Kỳ EPS", "pb_cach_tinh": "Cách tính P/B", "nguon_so_cp": "Nguồn số CP", "so_nguon_so_cp": "Số nguồn số CP",
    "cat_lo_theo": "Cắt lỗ theo", "ev_mt": "EV mục tiêu", "pb_nguon": "Nguồn P/B", "eps_ttm": "EPS TTM",
    "eps_nam": "EPS năm", "eps_g_nam": "Tăng EPS năm %", "eps_quy": "EPS quý", "eps_g_quy": "Tăng EPS quý %",
    "no_vay_tts": "Nợ vay / tổng tài sản %", "no_phai_tra_tts": "Nợ phải trả / tổng tài sản %",
    "tt_hien_thoi": "Thanh toán hiện thời", "tt_nhanh": "Thanh toán nhanh", "kiem_toan_5nam": "Kiểm toán 5 năm",
    "so_nam_co_tuc": "Số năm trả cổ tức", "co_tuc_tien_mat_cp": "Cổ tức tiền mặt / CP", "ty_suat_co_tuc": "Cổ tức %",
    "atr_pct": "ATR %", "bien_dong": "Biến động %", "cach_ma20": "Cách MA20 %", "dt_g_quy": "Tăng doanh thu quý %",
    "ln_g_quy": "Tăng lợi nhuận quý %", "bien_gop": "Biên gộp %", "bien_gop_ck": "Biên gộp cùng kỳ %",
    "so_huu_nn": "Sở hữu nước ngoài %", "free_float": "Free float %", "kiem_toan_ngoai_tru": "Kiểm toán ngoại trừ",
    "nguon_gia": "Nguồn giá", "nguon_co_ban": "Nguồn cơ bản", "nguon_chi_tieu": "Nguồn chỉ tiêu",
    "canh_bao_du_lieu": "Cảnh báo dữ liệu", "ghi_chu": "Ghi chú",
    "vung_mua": "Vùng mua", "vung_cho": "Vùng chờ", "cat_lo_kh": "Cắt lỗ kế hoạch", "kc_cat_lo": "Cách cắt lỗ %",
    "muc_tieu_kh": "Mục tiêu kế hoạch", "muc_tieu_3r": "Mục tiêu 3R", "nguon_mt": "Nguồn mục tiêu",
    "rr_kh": "R/R kế hoạch", "so_cp_kh": "Số CP kế hoạch", "gia_tri_kh": "Giá trị kế hoạch (tr)",
    "ty_trong_kh": "Tỷ trọng kế hoạch %", "rang_buoc_kl": "Ràng buộc khối lượng", "so_phien_mua": "Số phiên mua",
    "nhom_cl": "Mã nhóm chiến lược", "ten_nhom_cl": "Nhóm chiến lược", "dat_diem_mua": "Đạt điểm mua",
    "vo_hieu": "Vô hiệu khi", "gia_lo": "Đặt LO"}


def tieu_de(chu, ky="═"):
    from .mau import xanh, xanh_nhat
    print("\n" + xanh_nhat(ky * 100) + "\n " + xanh(chu) + "\n" + xanh_nhat(ky * 100))


def in_ket_qua(b, dat, top):
    """BƯỚC 1 – chỉ in các cột có dữ liệu (bỏ cột cơ bản khi không tải dữ liệu cơ bản)."""
    so_du = (dat["Đạt lọc"] == "✔").sum()
    print(f"  Đạt: {len(dat)}/{len(b)} mã ({so_du} đủ dữ liệu ✔, {len(dat) - so_du} thiếu dữ liệu ◐)")
    if len(dat):
        cot_cb = [c for c in dat.columns if c.startswith("Cơ bản đạt")]
        cot = [c for c in COT_HIEN_THI if c in dat.columns and dat[c].notna().any()
               and not (dat[c].astype(str).isin(["", "nan"])).all()] + cot_cb
        t = dat.head(top)[cot].rename(columns=COT_HIEN_THI)
        print(ve_bang(t, dinh_dang={"KLGD TB20": "{:,.0f}", "Vốn hoá tỷ": "{:,.0f}", "Điểm %": "{:.0f}",
                                    "Vị trí 52T %": "{:.0f}", "Upside %": "{:+.1f}", "R/R": "{:.1f}",
                                    "ROE %": "{:.1f}", "Cổ tức %": "{:.1f}"}))
    else:
        print("  Không có mã nào đạt – xem danh sách 'gần đạt' bên dưới hoặc nới tiêu chí.")


def in_danh_gia(e, top):
    """BƯỚC 2–5 – bảng điểm gọn; kế hoạch chi tiết nằm ở KẾT LUẬN và sheet Excel."""
    print("  Điểm 0–100 từng trụ cột: XH xu hướng · ĐL động lượng · ĐG định giá · CL chất lượng · "
          "RR rủi ro (cao = ít rủi ro)")
    t = e.head(top)[["Mã", "Đạt lọc", "Xu hướng", "Động lượng", "Định giá", "Chất lượng", "Rủi ro", "Điểm tổng",
                     "Hành động"]].rename(columns={"Đạt lọc": "Lọc", "Xu hướng": "XH", "Động lượng": "ĐL",
                                                   "Định giá": "ĐG", "Chất lượng": "CL", "Rủi ro": "RR",
                                                   "Điểm tổng": "Tổng"})
    t["Lọc"] = t["Lọc"].replace("", "·")
    print(ve_bang(t, dinh_dang={c: "{:.0f}" for c in ("XH", "ĐL", "ĐG", "CL", "RR", "Tổng")}, bo_cot_trong=False))
    if len(e) <= 30 and e["pe"].notna().any():
        print("\n  So sánh trong nhóm (P/E, P/B: số lần trung vị; ROE: chênh điểm % so trung vị)")
        print(ve_bang(e[["Mã", "Nhóm", "pe", "P/E so TV nhóm", "pb", "P/B so TV nhóm", "roe", "ROE − TV nhóm",
                         "Cơ sở so sánh"]].rename(columns={"pe": "P/E", "pb": "P/B", "roe": "ROE %"}),
                      dinh_dang={"P/E so TV nhóm": "{:.2f}×", "P/B so TV nhóm": "{:.2f}×",
                                 "ROE − TV nhóm": "{:+.1f}", "ROE %": "{:.1f}"}))


plt.rcParams.update({"legend.framealpha": 0.92, "legend.edgecolor": "0.8", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titlepad": 10, "axes.titlecolor": "#1B5E20",
                     "axes.titleweight": "bold", "axes.edgecolor": "0.55"})
_XANH_DAM = "#1B5E20"
_NEN = dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.92, lw=0.6)


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
    plt.close(fig)


def nhan_muc_gia(a, muc, khoang=0.07, co_chu=7):
    """Nhãn các đường giá ngang đặt ở LỀ PHẢI ngoài vùng vẽ, có khung, tự giãn cách → không đè đường/nhau."""
    from matplotlib.transforms import blended_transform_factory
    ylo, yhi = a.get_ylim()
    gap = khoang * (yhi - ylo)
    ds = sorted([m for m in muc if co(m[0]) and ylo <= m[0] <= yhi], key=lambda t: t[0])
    if not ds:
        return
    vt = [m[0] for m in ds]
    for k in range(1, len(vt)):
        vt[k] = max(vt[k], vt[k - 1] + gap)
    if vt[-1] > yhi - gap * 0.5:
        vt[-1] = yhi - gap * 0.5
        for k in range(len(vt) - 2, -1, -1):
            vt[k] = min(vt[k], vt[k + 1] - gap)
    tr = blended_transform_factory(a.transAxes, a.transData)
    for (g, chu, mau), y in zip(ds, vt):
        a.annotate(chu, xy=(1.0, g), xycoords=tr, xytext=(1.015, y), textcoords=tr, va="center", ha="left",
                   fontsize=co_chu, color=mau, bbox={**_NEN, "edgecolor": mau}, annotation_clip=False,
                   arrowprops=dict(arrowstyle="-", color=mau, lw=0.6, shrinkA=0, shrinkB=0))


def _nhan_diem_khong_chong(a, x, y, nhan, mau, co_chu=8):
    """Ghi tên mã cạnh điểm; điểm trùng toạ độ gộp 1 nhãn ('SCS, DDD'), điểm sát nhau so le trên/dưới."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if not len(x):
        return
    dx = (np.nanmax(x) - np.nanmin(x)) or 1
    dy = (np.nanmax(y) - np.nanmin(y)) or 1
    nhom, da = [], set()
    for k in range(len(x)):
        if k in da or not (co(x[k]) and co(y[k])):
            continue
        cung = [j for j in range(len(x)) if j not in da and co(x[j]) and co(y[j])
                and abs(x[j] - x[k]) < 0.01 * dx and abs(y[j] - y[k]) < 0.01 * dy]
        da.update(cung)
        nhom.append((x[k], y[k], ", ".join(nhan[j] for j in cung), mau[k]))
    nhom.sort(key=lambda t: (t[1], t[0]))
    lech = []
    for k, (xi, yi, chu, mi) in enumerate(nhom):
        gan = [o for (xo, yo, o) in lech if abs(xo - xi) < 0.08 * dx and abs(yo - yi) < 0.06 * dy]
        oy = 6 + 10 * len(gan) if len(gan) % 2 == 0 else -12 - 10 * (len(gan) - 1)
        lech.append((xi, yi, oy))
        a.annotate(chu, (xi, yi), xytext=(6, oy), textcoords="offset points", fontsize=co_chu, color=mi,
                   bbox=_NEN, arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5) if abs(oy) > 8 else None)


def _bo_bieu_tuong(chu):
    """Bỏ emoji đầu chuỗi (🟢 MUA MỚI → MUA MỚI) – phông biểu đồ không có glyph emoji."""
    return "".join(c for c in str(chu) if ord(c) < 0x2190 or 0x1EA0 <= ord(c) <= 0x1EFF).strip()


def ve_tong_quan(b, ten_cl, file_png, top):
    fig, ax = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={"width_ratios": [1.15, 1]})
    a = ax[0]
    dat = b["Đạt lọc"].isin(["✔", "◐"])
    x_ = b["kc_cat_lo_pct"] if "kc_cat_lo_pct" in b else (b["gia"] - b["cat_lo"]) / b["gia"] * 100
    a.scatter(x_[~dat], b.loc[~dat, "Điểm %"], c="lightgray", s=40, label="Không đạt", zorder=3)
    sc = a.scatter(x_[dat], b.loc[dat, "Điểm %"], c=b.loc[dat, "Điểm %"], cmap="YlGn",
                   vmin=0, vmax=100, s=120, edgecolors="black", label="Đạt lọc", zorder=4)
    hien = b if len(b) <= 40 else b[dat]
    _nhan_diem_khong_chong(a, x_[hien.index], hien["Điểm %"], list(hien["Mã"]),
                           ["black" if x in ("✔", "◐") else "gray" for x in hien["Đạt lọc"]])
    fig.colorbar(sc, ax=a, label="Điểm %", fraction=0.04, pad=0.02)
    a.axvline(7, color="#a3261f", ls=":", lw=1)
    a.annotate("mốc 7% (vượt khi 1,5·ATR > 7%)", (7, 1.0), xycoords=("data", "axes fraction"), xytext=(3, -12),
               textcoords="offset points", fontsize=8, color="#a3261f")
    a.margins(0.08)
    a.set_xlabel("Rủi ro tới cắt lỗ của chiến lược (%)")
    a.set_ylabel("Điểm lọc (%)")
    a.set_title("Điểm lọc vs rủi ro – góc trên trái là tốt nhất")
    a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, fontsize=9, frameon=False)
    a.grid(alpha=0.3)

    a = ax[1]
    t = b.head(top).iloc[::-1]
    mau = ["#2E7D32" if x == "✔" else ("#C0CA33" if x == "◐" else "#C8E6C9") for x in t["Đạt lọc"]]
    a.barh(t["Mã"], t["Điểm %"], color=mau, height=0.7)
    x_max = max(float(t["Điểm %"].max()), 10)
    for k, (d_, u) in enumerate(zip(t["Điểm %"], t.get("khuyen_nghi", pd.Series("", index=t.index)))):
        a.text(x_max * 1.04, k, f"{d_:.0f}%" + (f"   {_bo_bieu_tuong(u)}" if isinstance(u, str) and u else ""), va="center",
               fontsize=8, color="0.25")                       # cột nhãn riêng, không đè thanh
    a.set_xlim(0, x_max * 1.45)
    a.set_xlabel("Điểm lọc (% điểm tối đa) · nhãn bên phải: điểm + nhóm chiến lược")
    a.set_title(f"Xếp hạng top {min(top, len(b))}")
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(color="#2E7D32", label="Đạt lọc"), Patch(color="#C0CA33", label="Đạt, thiếu dữ liệu"),
                      Patch(color="#C8E6C9", label="Chưa đạt")],
             loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3, fontsize=9, frameon=False)
    a.grid(alpha=0.3, axis="x")
    fig.suptitle(f"BỘ LỌC CỔ PHIẾU – CHIẾN LƯỢC {ten_cl}", fontsize=14, fontweight="bold", color=_XANH_DAM)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    _luu(fig, file_png)
    print(f"  ✔ Biểu đồ tổng quan: {file_png}")


def ve_bieu_do_nho(ds_m, b, file_png):
    import matplotlib.dates as mdates
    chon = [r for r in b["Mã"] if r in ds_m][:ch.SO_BIEU_DO_NHO]
    if not chon:
        return
    n, cot = len(chon), 3
    hang = int(np.ceil(n / cot))
    fig, ax = plt.subplots(hang, cot, figsize=(19, 4.4 * hang), squeeze=False)
    for i, ma in enumerate(chon):
        m = ds_m[ma]
        d = m["_d"].tail(250)
        a = ax[i // cot][i % cot]
        a.plot(d.index, d.close, color="black", lw=1.1, label="Giá")
        a.plot(d.index, d.MA50, color="tab:orange", lw=0.9, label="MA50")
        a.plot(d.index, d.MA200, color="tab:purple", lw=0.9, label="MA200")
        a.plot(d.index, d.ST.where(d.ST_dir > 0), color="tab:green", lw=1.3, label="SuperTrend tăng")
        a.plot(d.index, d.ST.where(d.ST_dir < 0), color="tab:red", lw=1.3, label="SuperTrend giảm")
        muc = []
        if co(m["gia_mt"]):
            a.axhline(m["gia_mt"], color="green", ls="--", lw=1)
            muc.append((m["gia_mt"], f"1R {m['gia_mt']:,.2f}", "green"))
        if co(m.get("gia_mt_3r")):
            a.axhline(m["gia_mt_3r"], color="darkgreen", ls=":", lw=1)
            muc.append((m["gia_mt_3r"], f"3R {m['gia_mt_3r']:,.2f}", "darkgreen"))
        if co(m["cat_lo"]):
            a.axhline(m["cat_lo"], color="red", ls="--", lw=1)
            muc.append((m["cat_lo"], f"Cắt lỗ {m['cat_lo']:,.2f}", "red"))
        lo_, hi_ = a.get_ylim()
        a.set_ylim(lo_ - 0.03 * (hi_ - lo_), hi_ + 0.06 * (hi_ - lo_))
        nhan_muc_gia(a, muc)
        tieu_de = f"{ma}  ·  giá {m['gia']:,.2f}"
        if co(m["cat_lo"]):
            tieu_de += f"  ·  cắt lỗ {(m['cat_lo'] / m['gia'] - 1) * 100:+.1f}%"
        if isinstance(m.get("khuyen_nghi"), str) and m["khuyen_nghi"]:
            tieu_de += f"  ·  {_bo_bieu_tuong(m['khuyen_nghi'])}"
        a.set_title(tieu_de, fontsize=10, fontweight="bold", loc="left")
        a.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
        a.tick_params(labelsize=7)
        a.grid(alpha=0.3)
    for j in range(n, hang * cot):
        ax[j // cot][j % cot].axis("off")
    h, l = ax[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, 0.955), frameon=False)
    fig.suptitle("Biểu đồ các mã xếp hạng cao  (xanh: mốc 1R / 3R · đỏ: cắt lỗ – theo chiến lược thị trường)", fontsize=13,
                 fontweight="bold", color=_XANH_DAM)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _luu(fig, file_png, dpi=110)
    print(f"  ✔ Biểu đồ các mã: {file_png}")


def ve_danh_gia(e, file_png, top):
    t = e.head(top).iloc[::-1]
    if t.empty:
        return
    cao = max(4.0, 0.48 * len(t) + 2.6)
    fig, a = plt.subplots(figsize=(14, cao))
    trai = np.zeros(len(t))
    mau = {"Xu hướng": "#1B5E20", "Động lượng": "#43A047", "Định giá": "#C0CA33",
           "Chất lượng": "#00897B", "Rủi ro": "#90A4AE"}
    for k, w in ch.TRONG_SO.items():
        v = t[k].fillna(0).values * w
        a.barh(t["Mã"], v, left=trai, color=mau[k], label=f"{k} ({w:.0%})", height=0.7, edgecolor="white", lw=0.5)
        trai += v
    x_nhan = max(float(trai.max()), ch.NGUONG_HANH_DONG["mua"]) + 4
    for k, (d_, hd) in enumerate(zip(t["Điểm tổng"], t["Hành động"])):
        a.text(x_nhan, k, (f"{d_:.0f}" if co(d_) else "–").rjust(3) + f"   {hd}", va="center", fontsize=9,
               color="tab:green" if hd.startswith("MUA") else "0.25")
    theo_cl = "nhom_cl" in t.columns and t["nhom_cl"].notna().any()   # hành động theo chiến lược thị trường
    for nguong, ten, mau_ in (() if theo_cl else ((ch.NGUONG_HANH_DONG["tham_do"], "thăm dò", "orange"),
                                                  (ch.NGUONG_HANH_DONG["mua"], "mua", "green"))):
        a.axvline(nguong, color=mau_, ls=":", lw=1)
        a.annotate(f"{ten} ≥ {nguong}", (nguong, 1.0), xycoords=("data", "axes fraction"), xytext=(0, 4),
                   textcoords="offset points", ha="center", fontsize=7, color=mau_)
    a.set_xlim(0, x_nhan + 26)
    a.set_xlabel("Đóng góp vào điểm tổng (trọng số × điểm trụ cột)")
    a.set_title("ĐÁNH GIÁ SAU LỌC – điểm 5 trụ cột (xếp hạng) · hành động theo chiến lược thị trường" if theo_cl
                else "ĐÁNH GIÁ SAU LỌC – điểm 5 trụ cột & hành động gợi ý", pad=18)
    h, l = a.get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=5, fontsize=9, frameon=False)
    a.grid(alpha=0.3, axis="x")
    fig.tight_layout(rect=[0, 0.55 / cao, 1, 1])          # chừa 0,75 inch dưới cho chú thích – không đè nhãn trục
    _luu(fig, file_png, dpi=110)
    print(f"  ✔ Biểu đồ đánh giá: {file_png}")


def xuat_excel(path, b, dat, tieu_chi_cot, bang_tieu_chi, loi, loai_som, e, tham_so, thay_doi, nhat_ky,
               thong_ke_nguon, ket_luan=None):
    cot = [c for c in COT_XUAT if c in b.columns] + tieu_chi_cot
    try:
        with pd.ExcelWriter(path) as w:
            if ket_luan is not None and len(ket_luan):
                ket_luan.to_excel(w, sheet_name="Ket luan", index=False)
            (dat if len(dat) else b.head(0))[cot].to_excel(w, sheet_name="Dat loc", index=False)
            b[cot].to_excel(w, sheet_name="Tat ca", index=False)
            from .bon_bang import TEN_LOAI_TC
            bang_tieu_chi.replace(TEN_LOAI_TC).to_excel(w, sheet_name="Tieu chi", index=False)
            if loi:
                pd.DataFrame(loi, columns=["Mã", "Lý do"]).to_excel(w, sheet_name="Bo qua", index=False)
            if loai_som:
                pd.DataFrame(loai_som, columns=["Mã", "Lý do"]).to_excel(
                    w, sheet_name="Loai so bo (thanh khoan)", index=False)
            if e is not None:
                e.to_excel(w, sheet_name="Danh gia sau loc", index=False)
                tham_so.to_excel(w, sheet_name="Tham so danh gia", index=False)
            thay_doi.to_excel(w, sheet_name="Thay doi", index=False)
            cb = b[b.get("canh_bao_du_lieu", pd.Series("", index=b.index)).fillna("") != ""]
            if len(cb):
                cb[["Mã", "canh_bao_du_lieu", "nguon_chi_tieu"]].to_excel(w, sheet_name="Canh bao du lieu",
                                                                          index=False)
            if len(thong_ke_nguon):
                thong_ke_nguon.reset_index().to_excel(w, sheet_name="Suc khoe nguon", index=False)
            nhat_ky.to_excel(w, sheet_name="Nguon du lieu", index=False)
        trang_tri_excel(path)
        print(f"  ✔ Excel tổng hợp: {path}")
        return True
    except PermissionError:
        print("  ⚠ Không ghi được Excel – hãy đóng file cũ rồi chạy lại.")
        return False


MAU_KET_LUAN = {"[NÊN MUA]": "FFC8E6C9", "[MUA CÓ ĐIỀU KIỆN]": "FFFFF9C4", "[THEO DÕI]": "FFE3F2FD", "[LOẠI]": "FFF5F5F5"}


def trang_tri_excel(path):
    """Trang trí file Excel tổng hợp theo tông XANH LÁ: tiêu đề, xen kẽ, độ rộng, cố định & lọc, tô màu kết luận."""
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    from openpyxl.formatting.rule import ColorScaleRule, DataBarRule

    from .mau import XANH_DAM_HEX, XANH_HEX, XANH_NHAT_HEX
    from .so import la_cot_ty_le, vn_hoa
    try:
        wb = load_workbook(path)
    except Exception:
        return
    nen_td, nen_xen = PatternFill("solid", fgColor="FF" + XANH_DAM_HEX), PatternFill("solid", fgColor="FF" + XANH_NHAT_HEX)
    vien = Border(bottom=Side(style="thin", color="FFC8E6C9"))
    for ws in wb.worksheets:
        ws.sheet_properties.tabColor = XANH_HEX if ws.title in ("Ket luan", "Dat loc", "Danh gia sau loc") else "A5D6A7"
        if ws.max_row < 1 or ws.max_column < 1:
            continue
        cot_ket_luan = None
        for o in ws[1]:
            o.fill, o.font = nen_td, Font(bold=True, color="FFFFFFFF")
            o.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if o.value == "Kết luận":
                cot_ket_luan = o.column
        ws.row_dimensions[1].height = 30
        for r in range(2, ws.max_row + 1):
            mau_dong = None
            if cot_ket_luan:
                mau_dong = MAU_KET_LUAN.get(str(ws.cell(r, cot_ket_luan).value))
            for c in range(1, ws.max_column + 1):
                o = ws.cell(r, c)
                o.border = vien
                if mau_dong:
                    o.fill = PatternFill("solid", fgColor=mau_dong)
                elif r % 2 == 1:
                    o.fill = nen_xen
                if isinstance(o.value, str):
                    o.value = vn_hoa(o.value)
                elif isinstance(o.value, float):
                    o.number_format = ("0.####" if la_cot_ty_le(ws.cell(1, c).value)
                                       else "#,##0.00" if abs(o.value) < 1e6 else "#,##0")
        for c in range(1, ws.max_column + 1):
            dai = max(len(str(ws.cell(r, c).value or "")) for r in range(1, min(ws.max_row, 300) + 1))
            ws.column_dimensions[get_column_letter(c)].width = max(8, min(dai + 2, 55))
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
        for c in range(1, ws.max_column + 1):
            ten = str(ws.cell(1, c).value)
            vung = f"{get_column_letter(c)}2:{get_column_letter(c)}{ws.max_row}"
            if ws.max_row < 2:
                continue
            if ten in ("Điểm %", "Điểm tổng", "Điểm lọc %"):
                ws.conditional_formatting.add(vung, DataBarRule(start_type="num", start_value=0, end_type="num",
                                                                end_value=100, color="FF66BB6A", showValue=True))
            elif ten in ("upside", "Upside %", "Mục tiêu %", "ret1t", "ret3t", "rs3t"):
                ws.conditional_formatting.add(vung, ColorScaleRule(
                    start_type="min", start_color="FFEF9A9A", mid_type="num", mid_value=0, mid_color="FFFFFFFF",
                    end_type="max", end_color="FFA5D6A7"))
        for o in ws[1]:                    # đổi tên sau cùng: định dạng số ở trên vẫn dựa trên tên cột gốc
            if isinstance(o.value, str):
                o.value = TEN_COT_EXCEL.get(o.value, o.value.replace("_", " "))
    wb.save(path)
