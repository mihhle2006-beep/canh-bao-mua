# -*- coding: utf-8 -*-
"""
CẢNH BÁO MUA TRONG PHIÊN (mỗi 15 phút) – ĐỒNG BỘ với chiến lược thị trường.

  Chỉ quét các mã trong nhóm 🟢 / ✅ / 🟡 của tin tổng kết gần nhất (trang_thai_chien_luoc.json → ds_mua), đúng phiên
  hiệu lực, đúng vùng mua & cắt lỗ của tin đó. Tiêu chí 15' = ptcp/diem_vao_15p.py (cùng hàm với backtest):
    [Ngày – chiến lược] nhóm mua + lý do (đã đạt từ tối qua)
    [Vùng]  giá trong vùng mua · mở cửa ≤ đến · chưa rơi < từ
    [15']   MACD 15' cắt lên Signal (≤ 3 nến) HOẶC phá đỉnh 20 nến kèm KL ≥ 1,5× · giá ≥ VWAP · RSI 15' ≤ 75
    [Giờ]   MACD giờ > Signal (chỉ khi cách vào là 15P+GIO)
  Cách vào (ATO / 15P / 15P+ATC / LO …) lấy theo backtest (tong_ket_cl.cach_vao).
Tin: 🟢 MUA NGAY (đủ tiêu chí) · ⏰ MUA ATC (hết phiên chưa có điểm vào, giá còn trong vùng) · 🚫 BỎ (vô hiệu).
"""
import json

import numpy as np
import pandas as pd

from . import cau_hinh as C

TEN_NHOM = {"MUA_MOI": "MUA MỚI", "VAO_NHU_MOI": "VÀO NHƯ LỆNH MỚI", "VAO_NUA": "VÀO ½ KL"}


def _f(x, le=2):
    return "–" if x is None or x != x else f"{x:,.{le}f}"


def doc_ds_mua(bay_gio, path=None):
    """Danh sách mua có hiệu lực ĐÚNG phiên hôm nay (list dict) – rỗng nếu tin tổng kết là của phiên khác."""
    try:
        with open(path or C.FILE_TRANG_THAI_CL, encoding="utf-8") as f:
            ds = json.load(f).get("ds_mua") or {}
    except (OSError, ValueError):
        return []
    if ds.get("hieu_luc") != f"{pd.Timestamp(bay_gio):%Y-%m-%d}":
        return []
    return ds.get("ma") or []


NGUONG_THANG_GIA = 0.03                         # đóng cửa phiên trước lệch giá của tin > 3% → nguồn đã điều chỉnh quyền
_MUC_GIA = ("gia", "tu", "den", "cl", "R", "mt1", "mt3", "atr")


def quy_thang_gia(z, dp, bay_gio):
    """
    Nguồn giá điều chỉnh quyền (chia / tách cổ phiếu) SAU tin tổng kết → vùng / cắt lỗ tính trên giá cũ lệch thang
    nến 15'. Đóng cửa phiên trước trong dp lệch 'gia' (đóng cửa lúc tổng kết) > 3% → nhân mọi mức giá cùng hệ số.
    VD HDB 08/10/2026: tin ghi giá 28,00 vùng 27,45–28,70; tối đó VNDirect chia cả chuỗi 1,3 → 21,54.
    """
    g = z.get("gia")
    truoc = dp[dp.index.normalize() < pd.Timestamp(bay_gio).normalize()] if dp is not None else None
    if not g or truoc is None or not len(truoc):
        return z
    f = float(truoc.close.iloc[-1]) / float(g)
    if abs(f - 1) <= NGUONG_THANG_GIA or not 0.2 < f < 5:
        return z
    moi = {k: z[k] * f for k in _MUC_GIA if isinstance(z.get(k), (int, float)) and z[k] == z[k]}
    return {**z, **moi, "he_so_quyen": f}


def danh_gia(z, dp, bay_gio, bien_the):
    """z: 1 dòng ds_mua; dp: nến 15' (nhiều phiên, đã bỏ nến chưa đóng). → dict kết quả phiên hôm nay."""
    from ptcp.diem_vao_15p import chi_bao_15p, danh_gia_phien, macd_gio, tieu_chi_nen
    t = pd.Timestamp(bay_gio)
    z = quy_thang_gia(z, dp, t)
    kq = {**z, "ly_do_ngay": z.get("ly_do", ""), "trang_thai": "CHỜ", "ly_do": "chưa có dữ liệu 15' hôm nay", "gia_nay": np.nan, "tieu_chi": [],
          "gia_mua": np.nan, "thoi_diem": None}
    if dp is None or not len(dp):
        return kq
    d = chi_bao_15p(dp)
    hom_nay = d[d.index.normalize() == t.normalize()]
    if not len(hom_nay):
        return kq
    g = macd_gio(dp)[hom_nay.index]
    het = t >= t.normalize() + pd.Timedelta(C.GIO_ATC + ":00")
    r = danh_gia_phien(hom_nay, z["tu"], z["den"], bien_the, g, het_phien=het)
    L = hom_nay.iloc[-1]
    tc = r["tieu_chi"] or tieu_chi_nen(L, z["tu"], z["den"], bool(g.iloc[-1]) if "GIO" in bien_the else None)
    kq.update({"trang_thai": r["trang_thai"], "ly_do": r["ly_do"], "gia_nay": float(L.close), "tieu_chi": tc,
               "gia_mua": r["gia"], "thoi_diem": r["thoi_diem"], "atc": "ATC" in r["ly_do"]})
    return kq


def muc_sau_mua(kq):
    """Cắt lỗ & mục tiêu theo GIÁ MUA THẬT: MUA MỚI tính lại 2×ATR (≤ 7%); vào trễ giữ cắt lỗ hệ thống."""
    gia = kq["gia_mua"] if kq["gia_mua"] == kq["gia_mua"] else kq["gia_nay"]
    cl = kq.get("cl")
    if kq.get("nhom") == "MUA_MOI" and kq.get("atr") and kq["atr"] == kq["atr"]:
        try:
            from ptcp.he_thoat import stop_chuan
            cl = stop_chuan(gia, kq["atr"])
        except ImportError:
            pass
    if not (cl and cl == cl and cl < gia):
        return gia, cl, np.nan, np.nan
    R = gia - cl
    return gia, cl, gia + R, gia + 3 * R


def dong_bang(kq):
    """1 dòng log (công khai) – bảng 15' của mã trong danh sách mua."""
    ky = {True: "✔", False: "✘"}
    tc = " | ".join(f"{t[0].split(' (')[0].replace('Kích hoạt 15', '15')} {ky[bool(t[1])]}" for t in kq["tieu_chi"])
    return (f"  {kq['ma']:<5} {_f(kq['gia_nay']):>8}  {TEN_NHOM.get(kq['nhom'], kq['nhom']):<16} vùng "
            f"{_f(kq['tu'])}–{_f(kq['den'])} | {tc or '–'} → {kq['trang_thai']}: {kq['ly_do']}")


def _gon(tc):
    """Tiêu chí 15' rút gọn cho tin: 'MACD 15' cắt lên ✔ · ≥ VWAP 13,53 ✔ · RSI 57 ✔'."""
    ky = {True: "✔", False: "✘"}
    out = []
    for ten, dat, ct in tc:
        if ten.startswith("Giá trong vùng"):
            continue
        if ten.startswith("Kích hoạt"):
            out.append(f"{ct if dat else 'chưa kích hoạt'} {ky[bool(dat)]}")
        elif "VWAP" in ten:
            out.append(f"≥ {ct} {ky[bool(dat)]}")
        elif ten.startswith("RSI"):
            out.append(f"RSI {ct} {ky[bool(dat)]}")
        else:
            out.append(f"{ten} {ky[bool(dat)]}")
    return " · ".join(out)


def tin_mua(kq, bay_gio, bien_the, dang_giu=None):
    gia, cl, mt1, mt3 = muc_sau_mua(kq)
    dau = "⏰ MUA ATC" if kq.get("atc") else "🟢 MUA NGAY"
    nen = f" · nến {pd.Timestamp(kq['thoi_diem']):%H:%M}" if kq.get("thoi_diem") is not None and not kq.get("atc") else ""
    d = [f"{dau} – {kq['ma']} {_f(gia)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})",
         f"{TEN_NHOM.get(kq['nhom'], kq['nhom'])} | vùng {_f(kq['tu'])}–{_f(kq['den'])} | CL {_f(cl)}"
         + (f" ({(cl / gia - 1) * 100:+.1f}%)" if cl == cl and gia else "") + f" | MT {_f(mt1)} → {_f(mt3)}",
         f"Đạt điểm mua: [Ngày] {kq.get('ly_do_ngay', '')} ✔ · [Vùng] trong vùng ✔",
         (f"  [15'{nen}] {_gon(kq['tieu_chi'])}" if kq["tieu_chi"] and not kq.get("atc") else f"  {kq['ly_do']}"),
         _khoi_luong(kq, gia, cl)]
    if kq.get("he_so_quyen"):
        d.append(f"(Giá đã điều chỉnh quyền – vùng / CL của tin tổng kết quy đổi × {kq['he_so_quyen']:.3f}; "
                 "kiểm tra lại giá trên bảng điện)")
    if dang_giu:
        d.append("💼 Mã đang có trong danh mục – xem điều kiện MUA THÊM trong tin tổng kết, không mua trùng.")
    d.append(f"(Cách vào {bien_the} · đã mua → ghi gia_von, cat_lo_goc = CL, ngay_mua vào danh mục)")
    return "\n".join(d)


def _khoi_luong(kq, gia, cl):
    from .tong_ket_cl import dong_khoi_luong
    atr = kq.get("atr")
    return dong_khoi_luong(gia, cl, atr if atr is not None else np.nan, kq.get("nhom") == "VAO_NUA")


def tin_bo(kq, bay_gio):
    return (f"🚫 BỎ {kq['ma']} phiên {pd.Timestamp(bay_gio):%d/%m} – {kq['ly_do']}\n"
            f"(vùng mua {_f(kq['tu'])}–{_f(kq['den'])}; chờ bản tin tổng kết mới)")


def can_bao(ma, trang_thai_moi, bay_gio, luu, ly_do=""):
    """
    Báo 1 lần / mã / phiên: MUA, hoặc BỎ khi VÔ HIỆU thật (mở cửa vượt vùng / thủng vùng trước khi mua) – hết phiên
    mà giá ngoài vùng thì chỉ ghi vào bảng 15', không nhắn. luu: dict trạng thái (cập nhật tại chỗ).
    """
    ngay = f"{pd.Timestamp(bay_gio):%Y-%m-%d}"
    cu = luu.get(ma, {})
    da = cu.get("da_bao", []) if cu.get("ngay") == ngay else []
    luu[ma] = {"ngay": ngay, "trang_thai": trang_thai_moi, "da_bao": da}
    if trang_thai_moi == "BỎ" and not any(x in ly_do for x in ("không đuổi", "trước khi mua", "thủng vùng")):
        return False
    if trang_thai_moi in ("MUA", "BỎ") and trang_thai_moi not in da and "MUA" not in da:
        luu[ma]["da_bao"] = da + [trang_thai_moi]
        return True
    return False
