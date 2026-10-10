# -*- coding: utf-8 -*-
"""
BIỂU ĐỒ MỐC GIÁ gửi kèm tín hiệu (MUA NGAY · MUA MỚI · VÀO NHƯ LỆNH MỚI · VÀO ½ · cảnh báo BÁN).

Mốc (R = điểm mua − cắt lỗ; đúng hệ thoát T2-3R-ma10 của bot). KHÔNG chốt lời / cắt lỗ 1 phần – backtest 2019–26
chốt ⅓ / ½ ở 3R kém hơn giữ cả lệnh → các mốc đó ghi "GIỮ lại":
  3R   GIỮ lại (không chốt 1 phần) – từ đây chuyển khung tuần: bán khi tuần đóng cửa < MA10 tuần
  2R   Chốt lời (bán hết) nếu đã qua 3R rồi rơi về sàn 2R
  1R   Mua thêm ½ (chỉ khi có tín hiệu mới – đã backtest: có lợi) · dời cắt lỗ về hoà vốn
  Điểm mua – mua toàn bộ (đủ KL) / mua 1 phần (½ KL với nhóm VÀO ½), vùng mua tô màu
  ½ đường xuống cắt lỗ: vẫn GIỮ lại – chỉ bán khi chạm cắt lỗ
  Cắt lỗ toàn bộ – cắt lỗ hệ thoát
Ảnh lưu thư mục tạm (không commit); ảnh vị thế thật chỉ gửi riêng tư rồi xoá.
"""
import os
import re
import tempfile

import numpy as np
import pandas as pd

from . import cau_hinh as C

MAU = {"cl": "#c62828", "cl_phan": "#ef6c00", "mua": "#1565c0", "them": "#5e35b1", "tp1": "#2e7d32", "tp2": "#1b5e20",
       "gia": "#212121", "vung": "#bbdefb"}


def _f(x, n=2):
    return "–" if x is None or x != x else f"{x:,.{n}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def cac_moc(gia, cl, nhom="MUA_MOI"):
    """→ [(giá, nhãn, khoá màu, nét đứt?)] từ trên xuống; [] nếu thiếu cắt lỗ hợp lệ."""
    if not (gia == gia and cl == cl and cl is not None and 0 < cl < gia):
        return []
    R = gia - cl
    mua = "Mua 1 phần (½ KL)" if nhom == "VAO_NUA" else "Mua toàn bộ (đủ KL)"
    return [(gia + 3 * R, f"3R {_f(gia + 3 * R)} – GIỮ lại (không chốt 1 phần), bán khi tuần < MA10", "tp1", True),
            (gia + 2 * R, f"2R {_f(gia + 2 * R)} – chốt lời hết nếu đã qua 3R rồi rơi về", "tp2", True),
            (gia + R, f"1R {_f(gia + R)} – mua thêm ½ (nếu có tín hiệu mới) · dời CL hoà vốn", "them", True),
            (gia, f"{mua} – {_f(gia)}", "mua", False),
            (gia - R / 2, f"{_f(gia - R / 2)} – vẫn GIỮ lại, chỉ bán khi chạm cắt lỗ", "cl_phan", True),
            (cl, f"Cắt lỗ toàn bộ – {_f(cl)} ({(cl / gia - 1) * 100:+.1f}%)", "cl", False)]


def _gian_nhan(ys, lo, hi, khoang=0.055):
    """Dời nhãn cho khỏi chồng (giữ thứ tự), khoảng cách tối thiểu = khoang × biên độ trục."""
    gap = (hi - lo) * khoang
    order = np.argsort(ys)
    out = np.array(ys, float)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def ve(ma, dn, moc, tieu_de, file_png=None, vung=None, gia_nay=None, ngay_mua=None, n=120):
    """dn: giá ngày (open/high/low/close) · moc: cac_moc() · vung: (từ, đến) vùng mua → đường dẫn PNG (None nếu lỗi)."""
    if dn is None or not len(dn) or not moc:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = dn.tail(n)
    x = np.arange(len(d))
    fig, a = plt.subplots(figsize=(9.5, 5.6), dpi=110)
    fig.subplots_adjust(left=0.07, right=0.60, top=0.90, bottom=0.10)
    a.fill_between(x, d["low"].values, d["high"].values, color="#9e9e9e", alpha=0.25, lw=0)
    a.plot(x, d["close"].values, color=MAU["gia"], lw=1.4)
    gia_cuoi = gia_nay if gia_nay is not None and gia_nay == gia_nay else float(d["close"].iloc[-1])
    ys = [m[0] for m in moc] + [gia_cuoi, float(d["low"].min()), float(d["high"].max())]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.06
    a.set_ylim(lo - pad, hi + pad)
    a.set_xlim(0, len(d) + 3)
    if vung and all(v == v and v is not None for v in vung):
        a.axhspan(min(vung), max(vung), color=MAU["vung"], alpha=0.55, lw=0, label="vùng mua")
    nhan_y = _gian_nhan([m[0] for m in moc], lo - pad, hi + pad)
    for (y, nhan, k, dut), ty in zip(moc, nhan_y):
        a.axhline(y, color=MAU[k], lw=1.6 if not dut else 1.2, ls="--" if dut else "-")
        a.annotate(nhan, xy=(len(d) + 3, y), xytext=(len(d) + 6, ty), textcoords="data", annotation_clip=False,
                   va="center", fontsize=8.5, color=MAU[k], fontweight="bold" if not dut else "normal",
                   arrowprops=dict(arrowstyle="-", color=MAU[k], lw=0.6))
    a.scatter([len(d) - 1], [gia_cuoi], color=MAU["gia"], zorder=5, s=28)
    a.annotate(f"giá {_f(gia_cuoi)}", (len(d) - 1, gia_cuoi), xytext=(-8, 8), textcoords="offset points",
               ha="right", fontsize=8.5, color=MAU["gia"])
    if ngay_mua is not None:
        try:
            i = d.index.get_indexer([pd.Timestamp(ngay_mua)], method="bfill")[0]
            if i >= 0:
                a.axvline(i, color=MAU["mua"], lw=0.8, ls=":")
        except (TypeError, ValueError):
            pass
    tick = np.linspace(0, len(d) - 1, 5).astype(int)
    a.set_xticks(tick)
    a.set_xticklabels([f"{d.index[i]:%d/%m/%y}" for i in tick], fontsize=8)
    a.tick_params(axis="y", labelsize=8)
    a.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _f(v)))
    a.grid(alpha=0.25)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
    tieu_de = re.sub(r"[^\u0000-\u24FF]", "", tieu_de).strip(" –")          # bỏ emoji (font không có)
    a.set_title(tieu_de, fontsize=11, loc="left", fontweight="bold", color="#1b5e20")
    file_png = file_png or os.path.join(tempfile.gettempdir(), f"moc_{ma}_{abs(hash(tieu_de)) % 10**8}.png")
    fig.savefig(file_png)
    plt.close(fig)
    return file_png


def ve_an_toan(*a, **k):
    """Vẽ lỗi → None (không làm hỏng tin)."""
    if not getattr(C, "GUI_ANH", True):
        return None
    try:
        return ve(*a, **k)
    except Exception as e:
        print(f"⚠ Biểu đồ mốc lỗi: {type(e).__name__}: {str(e)[:120]}")
        return None


def moc_vi_the(gia_von, R, cat_lo_hien_tai):
    """Mốc cho vị thế đang giữ: theo giá vốn & 1R lúc mua; cắt lỗ = cắt lỗ hiệu lực hiện tại."""
    if not (gia_von and R and R == R and R > 0):
        return []
    m = [x for x in cac_moc(gia_von, gia_von - R) if x[2] != "cl"]
    m = [x for x in m if x[2] != "mua"] + [(gia_von, f"Giá vốn – {_f(gia_von)}", "mua", False)]
    if cat_lo_hien_tai and cat_lo_hien_tai == cat_lo_hien_tai:
        m = [x for x in m if x[0] > cat_lo_hien_tai or x[2] == "mua"]       # mốc dưới cắt lỗ không còn ý nghĩa
        m.append((cat_lo_hien_tai, f"Cắt lỗ hiện tại – {_f(cat_lo_hien_tai)}", "cl", False))
    return sorted(m, key=lambda x: -x[0])
