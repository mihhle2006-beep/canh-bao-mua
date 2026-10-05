# -*- coding: utf-8 -*-
"""
TRÌNH BÀY TIN TELEGRAM – tông xanh lá, số kiểu Việt Nam:
  • vn_hoa      : 1,234.56 → 1.234,56 (đổi 1 lần ở đầu ra)
  • dinh_dang_html : tin chữ → HTML Telegram (tiêu đề đậm, nhãn đậm, ghi chú nghiêng, khối số liệu căn cột)
  • ve_bieu_do_ma  : ảnh nhỏ 6 tháng giá + MA20/50 + mục tiêu / cắt lỗ (+ giá vốn nếu đang giữ) – gửi kèm tin
  • ve_bang_tong_ket: ảnh bảng tổng kết cuối ngày (mỗi mã 1 dòng, tô màu theo trạng thái)
Ảnh lưu ở thư mục tạm, KHÔNG commit lên repo công khai.
"""
import html
import os
import re
import tempfile

import pandas as pd

_RE_SO = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)(?![\w]|[.,]\d)")
_DOI = str.maketrans(",.", ".,")
XANH_DAM, XANH, XANH_NHAT = "#1B5E20", "#2E7D32", "#E8F5E9"
THU_MUC_ANH = os.path.join(tempfile.gettempdir(), "canh_bao_anh")


def vn_hoa(chu):
    """'1,234.56' → '1.234,56' ; '+5.0%' → '+5,0%' (không đụng ngày 02/10, giờ 10:30, phiên bản)."""
    if not isinstance(chu, str) or not chu or os.environ.get("SO_KIEU_QUOC_TE"):
        return chu
    return _RE_SO.sub(lambda m: m.group().translate(_DOI), chu)


# ---------------------------------------------------------------- HTML cho Telegram
_NHAN_DAM = ("Kích hoạt:", "Thị trường:", "Sự kiện:", "Xác suất lịch sử", "3 kịch bản", "Lý do:", "Đang giữ",
             "Cắt lỗ đã đặt", "ptcp", "💼", "🎯", "➜")


def dinh_dang_html(noi_dung):
    """Tin chữ → HTML (parse_mode=HTML): dòng 1 đậm, '■ MÃ' đậm, nhãn trước ':' đậm, dòng '(…)' nghiêng."""
    ra = []
    for i, d in enumerate(noi_dung.split("\n")):
        e = html.escape(d, quote=False)
        if i == 0 and d.strip():
            ra.append(f"<b>{e}</b>")
        elif d.startswith("■ "):
            phan = e.split(" – ", 1)
            ra.append(f"<b>{phan[0]}</b>" + (f" – {phan[1]}" if len(phan) > 1 else ""))
        elif d.strip().startswith("(") and d.strip().endswith(")"):
            ra.append(f"<i>{e}</i>")
        elif any(d.strip().startswith(n) for n in _NHAN_DAM) and ":" in e:
            nhan, _, phan_sau = e.partition(":")
            ra.append(f"<b>{nhan}:</b>{phan_sau}")
        elif d.isupper() and d.strip():
            ra.append(f"<b>{e}</b>")
        else:
            ra.append(e)
    return "\n".join(ra)


# ---------------------------------------------------------------- biểu đồ nhỏ cho 1 mã
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": XANH_DAM,
                         "axes.titleweight": "bold", "font.size": 9})
    return plt


def _bo_emoji(chu):
    """Phông biểu đồ không có emoji màu → bỏ ký tự ngoài BMP (🟢🔴…) khỏi chữ trên ảnh."""
    return re.sub(r"[\U00010000-\U0010FFFF]\s?", "", str(chu or "")).strip()


def _so(x, le=2):
    return "–" if x is None or x != x else vn_hoa(f"{x:,.{le}f}")


def ve_bieu_do_ma(ma, dn, gia, muc_tieu=None, cat_lo=None, gia_von=None, tieu_de="", so_phien=126):
    """Ảnh PNG nhỏ (~1000×560) – trả đường dẫn hoặc None nếu lỗi."""
    try:
        plt = _plt()
        from matplotlib.transforms import blended_transform_factory
        d = dn.tail(so_phien)
        fig, a = plt.subplots(figsize=(8.5, 4.6), dpi=120)
        a.plot(d.index, d.close, color="black", lw=1.4, label="Giá")
        a.plot(d.index, dn.close.rolling(20).mean().tail(so_phien), color="#F9A825", lw=1, label="MA20")
        a.plot(d.index, dn.close.rolling(50).mean().tail(so_phien), color="#6D4C41", lw=1, label="MA50")
        muc = [(muc_tieu, "Mục tiêu", XANH, "-"), (cat_lo, "Cắt lỗ", "#C62828", "--"),
               (gia_von, "Giá vốn", "#1565C0", ":")]
        muc = [(g, t, c, ls) for g, t, c, ls in muc if g is not None and g == g]
        for g, _, c, ls in muc:
            a.axhline(g, color=c, ls=ls, lw=1.2)
        if muc_tieu and cat_lo and muc_tieu == muc_tieu and cat_lo == cat_lo:
            a.axhspan(cat_lo, muc_tieu, color=XANH_NHAT, alpha=0.6, zorder=0)
        a.scatter([d.index[-1]], [gia], color=XANH, s=40, zorder=5)
        lo, hi = a.get_ylim()
        a.set_ylim(lo - 0.03 * (hi - lo), hi + 0.05 * (hi - lo))
        lo, hi = a.get_ylim()
        gap, tr = 0.07 * (hi - lo), blended_transform_factory(a.transAxes, a.transData)
        ds = sorted([(g, f"{t} {_so(g)} ({(g / gia - 1) * 100:+.1f}%)", c)
                     for g, t, c, _ in muc] + [(gia, f"Giá {_so(gia)}", "black")], key=lambda x: x[0])
        vt = [x[0] for x in ds]
        for k in range(1, len(vt)):
            vt[k] = max(vt[k], vt[k - 1] + gap)
        for (g, chu, c), y in zip(ds, vt):
            a.annotate(vn_hoa(chu), xy=(1.0, g), xycoords=tr, xytext=(1.015, y), textcoords=tr, va="center",
                       fontsize=8, color=c, annotation_clip=False,
                       bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=c, lw=0.6),
                       arrowprops=dict(arrowstyle="-", color=c, lw=0.6))
        import matplotlib.dates as mdates
        a.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        a.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: vn_hoa(f"{v:,.2f}")))
        a.grid(alpha=0.3)
        a.legend(loc="best", fontsize=7, framealpha=0.9)
        a.set_title(_bo_emoji(tieu_de) or ma, loc="left")
        os.makedirs(THU_MUC_ANH, exist_ok=True)
        f = os.path.join(THU_MUC_ANH, f"{ma}_{pd.Timestamp.now():%H%M%S%f}.png")
        fig.savefig(f, bbox_inches="tight", pad_inches=0.2)
        plt.close(fig)
        return f
    except Exception as e:                         # ảnh lỗi không được làm hỏng tin cảnh báo
        print(f"(không vẽ được ảnh {ma}: {str(e)[:60]})")
        return None


# ---------------------------------------------------------------- ảnh bảng tổng kết
MAU_TRANG_THAI = [("MUA NGAY", "#C8E6C9"), ("GẦN", "#FFF9C4"), ("THEO DÕI", "#E3F2FD"), ("CHƯA", "#F5F5F5")]


def ve_bang_tong_ket(dong, tieu_de):
    """dong: list dict {Mã, Giá, Trạng thái, Khung, Mục tiêu, Cắt lỗ, R/R, ptcp} → ảnh PNG bảng."""
    if not dong:
        return None
    try:
        plt = _plt()
        df = pd.DataFrame(dong)
        o = [[vn_hoa(str(v)) for v in r] for r in df.values.tolist()]
        cao = 0.55 + 0.42 * (len(df) + 1)
        rong = max(9.5, 1.15 * len(df.columns) + 2)
        fig, a = plt.subplots(figsize=(rong, cao), dpi=130)
        a.axis("off")
        t = a.table(cellText=o, colLabels=list(df.columns), loc="upper center", cellLoc="center")
        t.auto_set_font_size(False)
        t.set_fontsize(8.5)
        t.scale(1, 1.45)
        for (r, c), o_ in t.get_celld().items():
            o_.set_edgecolor("#C8E6C9")
            if r == 0:
                o_.set_facecolor(XANH_DAM)
                o_.set_text_props(color="white", fontweight="bold")
                continue
            tt = str(df.iloc[r - 1].get("Trạng thái", "")).upper()
            mau = next((m for k, m in MAU_TRANG_THAI if k in tt), "white" if r % 2 else XANH_NHAT)
            o_.set_facecolor(mau)
            if c == 0:
                o_.set_text_props(fontweight="bold")
        t.auto_set_column_width(list(range(len(df.columns))))
        a.set_title(_bo_emoji(vn_hoa(tieu_de)), loc="left", fontsize=11)
        os.makedirs(THU_MUC_ANH, exist_ok=True)
        f = os.path.join(THU_MUC_ANH, f"tong_ket_{pd.Timestamp.now():%H%M%S%f}.png")
        fig.savefig(f, bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        return f
    except Exception as e:
        print(f"(không vẽ được ảnh tổng kết: {str(e)[:60]})")
        return None


def dong_bang_tong_ket(kq):
    """1 dòng của bảng tổng kết từ kết quả phan_tich_ma."""
    ky = {True: "✔", False: "✘", None: "–"}
    g = kq.get("gia")
    mt, cl = kq.get("muc_tieu"), kq.get("cat_lo")
    pt = kq.get("ptcp") or {}
    r = {"Mã": kq["ma"], "Giá": _so(g), "Trạng thái": kq.get("trang_thai", "")}
    for k in kq.get("khung", []):
        r[k["khung"]] = ky[k["dat"]]
    r.update({"Mục tiêu": f"{_so(mt)} ({(mt / g - 1) * 100:+.1f}%)" if mt and mt == mt and g else "–",
              "Cắt lỗ": f"{_so(cl)} ({(cl / g - 1) * 100:+.1f}%)" if cl and cl == cl and g else "–",
              "R/R": _so(kq.get("rr"), 1), "ptcp": pt.get("khuyen_nghi", "–")})
    return r

