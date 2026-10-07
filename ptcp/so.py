# -*- coding: utf-8 -*-
"""
CÁCH GHI SỐ THỐNG NHẤT – kiểu Việt Nam: dấu CHẤM phân cách nghìn, dấu PHẨY thập phân (34.500 ; 1,05).
Bên trong chương trình mọi số đều định dạng kiểu quốc tế (34,500 ; 1.05); chỉ đổi 1 lần ở ĐẦU RA
(màn hình, file .txt/.html, ô chữ trong Excel, tin Telegram) bằng vn_hoa() → không bao giờ đổi 2 lần.
Đổi dấu là thay 1 ký tự bằng 1 ký tự → bảng đã căn cột vẫn thẳng hàng.
Số dạng % và "lần": tối đa 4 chữ số thập phân, bỏ số 0 thừa (so4).
"""
import os
import re

BAT_SO_VN = os.environ.get("PTCP_SO_KIEU_QUOC_TE", "") == ""        # đặt SO_KIEU_QUOC_TE=1 để giữ 1,234.56
_RE_SO = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)(?![\w]|[.,]\d)")
_DOI = str.maketrans(",.", ".,")


def vn_hoa(chu):
    """'1,234.56' → '1.234,56' ; '+5.0%' → '+5,0%' ; không đụng ngày 02/10/2026, giờ 10:30, mã VN30, phiên bản 4.0.9."""
    if not BAT_SO_VN or not isinstance(chu, str) or not chu:
        return chu
    return _RE_SO.sub(lambda m: m.group().translate(_DOI), chu)


def so4(x, dau=False):
    """% và 'lần': tối đa 4 chữ số thập phân, bỏ 0 thừa (kiểu quốc tế – vn_hoa đổi ở đầu ra). NaN → '–'."""
    try:
        if x is None or x != x:
            return "–"
        s = f"{float(x):,.4f}".rstrip("0").rstrip(".")
        if s in ("-0", "+0"):
            s = "0"
        return ("+" + s) if dau and float(x) > 0 else s
    except (TypeError, ValueError):
        return str(x)


def la_cot_ty_le(ten):
    """Cột dạng % hoặc 'lần' (P/E, P/B, R/R, Beta, ×…)."""
    t = str(ten)
    return "%" in t or "lần" in t.lower() or "×" in t or t.strip() in ("P/E", "P/B", "R/R", "Beta", "BETA")
