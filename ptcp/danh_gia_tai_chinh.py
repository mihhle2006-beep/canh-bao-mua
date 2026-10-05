# -*- coding: utf-8 -*-
"""
PHÂN TÍCH TÀI CHÍNH 10 TIÊU CHÍ – theo phương pháp luận FiinGroup/FiinTrade (bản v1.0), 5 mức:
  5 Rất tốt (Excellent) · 4 Tốt (Good) · 3 Trung bình (Neutral) · 2 Cảnh báo (Be Alert) · 1 Nguy hiểm (Watch out)
Dữ liệu: BCTC 3–4 năm gần nhất (nguon/bctc_nam.py), danh sách MỚI NHẤT TRƯỚC. Xét điều kiện từ mức xấu → tốt
đúng thứ tự trong tài liệu; thiếu dữ liệu → None ("không đủ dữ liệu").
Ngân hàng / chứng khoán / bảo hiểm: không có biên gộp, thanh toán hiện thời, cơ cấu nợ kiểu DN sản xuất → None.
Tiêu chí 10 (kế hoạch kinh doanh) cần số kế hoạch ĐHCĐ – nguồn miễn phí không có → để None.
"""
import numpy as np

TEN_MUC = {5: "Rất tốt", 4: "Tốt", 3: "Trung bình", 2: "Cảnh báo", 1: "Nguy hiểm"}
DIEM_MUC = {5: 100, 4: 75, 3: 50, 2: 25, 1: 0}
TIEU_CHI_FA = ["Phát hành tăng vốn", "Tăng trưởng doanh thu", "Biên lãi gộp", "Tăng trưởng lợi nhuận",
               "Chất lượng dòng tiền", "Khả năng thanh toán", "Áp lực nợ vay", "Cấu trúc vốn", "ROE",
               "Kế hoạch kinh doanh"]


def _ds(bc, k, n):
    """n giá trị mới nhất (đủ cả n và không None) hoặc None."""
    v = (bc or {}).get(k) or []
    v = v[:n]
    return v if len(v) == n and all(x is not None and x == x for x in v) else None


def _tang(a, b):
    """Tăng trưởng a so với b, chịu được b âm."""
    return (a - b) / abs(b) if b else np.nan


def _tang_lien_tuc(v):            # v mới nhất trước → v[0] > v[1] > v[2] ...
    return all(x > y for x, y in zip(v, v[1:]))


def _giam_lien_tuc(v):
    return all(x < y for x, y in zip(v, v[1:]))


def _chuoi_tang_truong(bc, k):
    """3 tốc độ tăng trưởng gần nhất (cần 4 năm); chỉ có 3 năm → 2 tốc độ."""
    v = _ds(bc, k, 4) or _ds(bc, k, 3)
    if not v:
        return None, None
    return v, [_tang(a, b) for a, b in zip(v, v[1:])]


# ---------------------------------------------------------------- 10 tiêu chí
def phat_hanh_tang_von(bc, gia):
    vg = (bc or {}).get("von_gop") or []
    if len(vg) < 4 or any(x is None or x <= 0 for x in vg[:4]):
        return None, "thiếu vốn góp 4 năm"
    x3 = vg[0] / vg[3]
    x4 = vg[0] / vg[4] if len(vg) > 4 and vg[4] else np.nan
    gia_thap = gia is not None and gia < 5                       # thị giá dưới 5.000 đ
    mo_ta = f"vốn góp ×{x3:.2f} trong 3 năm" + (f", ×{x4:.2f} trong 4 năm" if x4 == x4 else "")
    if (gia_thap and x3 > 2) or (x4 == x4 and x4 > 3):
        return 1, mo_ta
    if (gia_thap and x3 > 1.001) or x3 > 2.5:
        return 2, mo_ta
    ln = _ds(bc, "lnst", 4)
    eps_tang = ln is not None and _tang_lien_tuc([l / v for l, v in zip(ln, vg[:4])])
    if not gia_thap and x3 < 2 and eps_tang:
        return 4, mo_ta + ", EPS tăng liên tục"
    return 3, mo_ta


def tang_truong_doanh_thu(bc):
    v, g = _chuoi_tang_truong(bc, "doanh_thu")
    if not g:
        return None, "thiếu doanh thu 3 năm"
    tb = float(np.mean(g)) * 100
    lg = _ds(bc, "ln_gop", 1)
    mo_ta = f"tăng trưởng TB {tb:+.1f}%/năm"
    if all(x < 0 for x in g):
        return (1 if lg and lg[0] < 0 else 2), "doanh thu giảm liên tiếp, " + mo_ta
    if all(x > 0 for x in g):
        if tb > 20 and _tang_lien_tuc(g):
            return 5, "tăng liên tiếp với gia tốc tăng, " + mo_ta
        return 4, "tăng liên tiếp, " + mo_ta
    return 3, "biến động thất thường, " + mo_ta


def bien_lai_gop(bc):
    dt, lg = _ds(bc, "doanh_thu", 3), _ds(bc, "ln_gop", 3)
    if not dt or not lg or any(x <= 0 for x in dt):
        return None, "không áp dụng / thiếu dữ liệu"
    m = [g / d for g, d in zip(lg, dt)]
    tb = float(np.mean(m)) * 100
    mo_ta = f"biên gộp TB {tb:.1f}% (gần nhất {m[0] * 100:.1f}%)"
    if _giam_lien_tuc(m) and m[0] < 0:
        return 1, mo_ta
    if any(x < 0 for x in m):
        return 2, mo_ta
    if _tang_lien_tuc(m):
        return (5 if tb >= 25 else 4), "tăng dần, " + mo_ta
    return 3, mo_ta


def tang_truong_loi_nhuan(bc):
    v, g = _chuoi_tang_truong(bc, "lnst")
    if not g:
        return None, "thiếu lợi nhuận 3 năm"
    tb = float(np.nanmean(g)) * 100
    mo_ta = f"tăng trưởng TB {tb:+.1f}%/năm"
    if all(x < 0 for x in g) and v[0] < 0:
        return 1, "lợi nhuận giảm liên tiếp, gần nhất lỗ"
    if any(x < 0 for x in v[:3]):
        return 2, "có thua lỗ trong 3 năm gần nhất"
    if all(x > 0 for x in g):
        if _tang_lien_tuc(g):
            return 5, "tăng liên tục với gia tốc tăng, " + mo_ta
        if tb >= 10:
            return 4, "tăng liên tục, " + mo_ta
    return 3, ("lợi nhuận năm gần nhất giảm, " if g[0] < 0 else "") + mo_ta


def chat_luong_dong_tien(bc):
    cf = _ds(bc, "cfo", 3)
    if not cf:
        return None, "thiếu dòng tiền 3 năm"
    if all(x < 0 for x in cf):
        return 1, "dòng tiền kinh doanh âm 3 năm liên tiếp"
    if cf[0] < 0:
        return 2, "dòng tiền kinh doanh âm năm gần nhất"
    if all(x > 0 for x in cf):
        ln = _ds(bc, "lnst", 1)
        if ln and cf[0] >= ln[0]:
            return 5, "dương 3 năm liên tiếp và ≥ lợi nhuận năm gần nhất"
        return 4, "dương 3 năm liên tiếp"
    return 3, "dương năm gần nhất"


def kha_nang_thanh_toan(bc):
    cr = _ds(bc, "cr", 3)
    if not cr:
        return None, "không áp dụng / thiếu dữ liệu"
    mo_ta = f"thanh toán hiện thời {cr[0]:.2f}"
    if cr[0] < 0.5 and _giam_lien_tuc(cr):
        return 1, mo_ta + ", giảm liên tục"
    if cr[0] < 0.7:
        return 2, mo_ta
    if all(x > 1.5 for x in cr):
        return (5 if _tang_lien_tuc(cr) else 4), mo_ta + ", > 1,5 liên tục 3 năm"
    return 3, mo_ta


def ap_luc_no_vay(bc):
    vay = _ds(bc, "vay_no", 3)
    if vay and all(x == 0 for x in vay):
        return 5, "không vay nợ tài chính 3 năm liên tiếp"
    icr = _ds(bc, "icr", 3)
    if not icr:
        return None, "thiếu EBIT/lãi vay"
    mo_ta = f"EBIT/lãi vay {icr[0]:.1f} lần"
    if all(x < 0.5 for x in icr):
        return 1, mo_ta + " (< 0,5 cả 3 năm)"
    if icr[0] < 1:
        return 2, mo_ta
    return (4 if icr[0] > 5 else 3), mo_ta


def cau_truc_von(bc):
    de = _ds(bc, "de", 3)
    if not de:
        return None, "không áp dụng / thiếu dữ liệu"
    mo_ta = f"Nợ/VCSH {de[0]:.2f} lần"
    if _tang_lien_tuc(de) and de[0] > 3:
        return 1, mo_ta + ", tăng liên tiếp"
    if (_tang_lien_tuc(de) and de[0] > 1) or de[0] > 2:
        return 2, mo_ta
    if de[0] < 0.2:
        return 5, mo_ta
    if _giam_lien_tuc(de) and de[0] < 1:
        return 4, mo_ta + ", giảm liên tiếp"
    return 3, mo_ta


def roe_3_nam(bc):
    r = _ds(bc, "roe", 3)
    if not r:
        return None, "thiếu ROE 3 năm"
    tb = float(np.mean(r))
    mo_ta = f"ROE TB {tb:.1f}% (gần nhất {r[0]:.1f}%)"
    am = sum(x < 0 for x in r)
    if am >= 2:
        return 1, mo_ta
    if am == 1 or _giam_lien_tuc(r):
        return 2, mo_ta + (", giảm liên tiếp" if am == 0 else "")
    if _tang_lien_tuc(r) and min(r) > 20:
        return 5, mo_ta + ", tăng liên tiếp"
    if tb > 20 or (_tang_lien_tuc(r) and tb > 10):
        return 4, mo_ta
    return 3, mo_ta


def ke_hoach_kinh_doanh(bc):
    return None, "chưa có dữ liệu kế hoạch ĐHCĐ (nguồn miễn phí không cung cấp)"


# ---------------------------------------------------------------- tổng hợp
def danh_gia(bc, gia=None, la_tai_chinh=False):
    """
    bc: BCTC năm; gia: nghìn đồng; la_tai_chinh: ngân hàng/CK/bảo hiểm (bỏ biên gộp, thanh toán, nợ).
    → {"chi_tiet": {tiêu chí: (mức, giải thích)}, "diem": 0–100, "so_nguy_hiem", "so_canh_bao", "tom_tat"}
    """
    ham = [lambda: phat_hanh_tang_von(bc, gia), lambda: tang_truong_doanh_thu(bc), lambda: bien_lai_gop(bc),
           lambda: tang_truong_loi_nhuan(bc), lambda: chat_luong_dong_tien(bc), lambda: kha_nang_thanh_toan(bc),
           lambda: ap_luc_no_vay(bc), lambda: cau_truc_von(bc), lambda: roe_3_nam(bc),
           lambda: ke_hoach_kinh_doanh(bc)]
    khong_ap_dung = {"Biên lãi gộp", "Khả năng thanh toán", "Áp lực nợ vay", "Cấu trúc vốn"} if la_tai_chinh else set()
    ct = {}
    for ten, h in zip(TIEU_CHI_FA, ham):
        if ten in khong_ap_dung:
            ct[ten] = (None, "không áp dụng cho ngân hàng/CK/bảo hiểm")
            continue
        try:
            ct[ten] = h() if bc else (None, "không có BCTC năm")
        except Exception as e:
            ct[ten] = (None, f"lỗi tính: {str(e)[:40]}")
    muc = [m for m, _ in ct.values() if m]
    nguy = [t for t, (m, _) in ct.items() if m == 1]
    canh = [t for t, (m, _) in ct.items() if m == 2]
    return {"chi_tiet": ct, "diem": float(np.mean([DIEM_MUC[m] for m in muc])) if len(muc) >= 4 else np.nan,
            "so_danh_gia": len(muc), "so_nguy_hiem": len(nguy), "so_canh_bao": len(canh),
            "tom_tat": "; ".join([f"Nguy hiểm: {', '.join(nguy)}"] * bool(nguy) + [f"Cảnh báo: {', '.join(canh)}"] * bool(canh)),
            "nguon": (bc or {}).get("nguon", ""), "nam": ((bc or {}).get("nam") or [None])[0]}
