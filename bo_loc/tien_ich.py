# -*- coding: utf-8 -*-
"""Hàm tiện ích nhỏ dùng chung."""
import numpy as np


def co(x):
    """Có giá trị (không None/NaN)."""
    if x is None:
        return False
    try:
        return not np.isnan(x)
    except TypeError:
        return True


def so_vn(x, le=0):
    """34500 → '34,500' (kiểu quốc tế bên trong; đổi sang 34.500 ở đầu ra bằng so.vn_hoa)."""
    if not co(x):
        return "N/A"
    return f"{x:,.{le}f}"


def bac(x, cac_bac, mac_dinh=0.0):
    """Chấm điểm theo bậc: [(ngưỡng, điểm), ...] xét lần lượt, x ≤ ngưỡng → điểm."""
    if not co(x):
        return np.nan
    for nguong, diem in cac_bac:
        if x <= nguong:
            return diem
    return mac_dinh


def trung_binh(ds):
    ds = [float(x) for x in ds if co(x)]
    return float(np.mean(ds)) if ds else np.nan


def dung(dk):
    """True/False → 100/0 ; None/NaN → NaN."""
    try:
        return np.nan if dk is None or (isinstance(dk, float) and np.isnan(dk)) else (100.0 if bool(dk) else 0.0)
    except Exception:
        return np.nan


def diem_tang_truong(g):
    return float(np.clip(50 + g, 0, 100)) if co(g) else np.nan


def doc_so(x):
    """Đọc số từ chuỗi kiểu Việt Nam/quốc tế: '78,700' → 78700 | '15,5' → 15.5 | '1.234,5' → 1234.5 |
    '1,234.5' → 1234.5 | '12%' → 12. Không đọc được → None."""
    try:
        if x is None:
            return None
        if not isinstance(x, str):
            v = float(x)
            return None if np.isnan(v) else v
        s = x.strip().replace(" ", "").replace("%", "").replace("\u00a0", "")
        if not s or s.lower() in ("nan", "none", "-", "--"):
            return None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
            s = s.replace(",", ".")                   # dấu phẩy thập phân kiểu Việt Nam
        else:
            s = s.replace(",", "")
        return float(s)
    except (TypeError, ValueError):
        return None
