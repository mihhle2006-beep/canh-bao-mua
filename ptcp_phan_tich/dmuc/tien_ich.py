# -*- coding: utf-8 -*-
"""Tiện ích dùng chung: đọc số kiểu Việt Nam, quy đổi đơn vị giá, định dạng, ghi báo cáo."""
import io
import re

import numpy as np
import pandas as pd


def co(x):
    """True nếu x là số có thật (không None/NaN)."""
    return x is not None and not (isinstance(x, float) and np.isnan(x))


def doc_so(x, la_khoi_luong=False):
    """
    Đọc số từ ô CSV/Excel, chấp nhận kiểu Việt Nam và kiểu Anh:
      '1.234,5' → 1234.5 ; '1,234.5' → 1234.5 ; '70,5' → 70.5 ; '73.9' → 73.9
      khối lượng: '106.249.620' / '106,249,620' → 106249620
    Không đọc được → None (thay vì làm hỏng cả chương trình như bản cũ với '1.234,5').
    """
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace(" ", "").replace("\u00a0", "")
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    if "." in s and "," in s:                         # dấu xuất hiện SAU CÙNG là dấu thập phân
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if (la_khoi_luong or re.fullmatch(r"-?\d{1,3}(,\d{3}){2,}", s)) else s.replace(",", ".")
    elif "." in s and (la_khoi_luong or re.fullmatch(r"-?\d{1,3}(\.\d{3}){2,}", s)):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def quy_doi_gia(gia, gia_tham_chieu, ten=""):
    """
    Giá nhập phải theo NGHÌN ĐỒNG. Lệch > 20 lần so với giá thị trường → gần như chắc chắn nhầm đơn vị:
      73900 (đồng) → 73.9 ; 0.0739 → 73.9. Trả về (giá đã quy đổi, cảnh báo hoặc '').
    """
    if not co(gia) or not co(gia_tham_chieu) or gia <= 0 or gia_tham_chieu <= 0:
        return gia, ""
    if gia > 20 * gia_tham_chieu and 0.05 < gia / 1000 / gia_tham_chieu < 20:
        return gia / 1000, f"{ten}: {gia:,.2f} có vẻ nhập theo ĐỒNG → quy đổi thành {gia / 1000:,.2f} nghìn đồng"
    if gia < gia_tham_chieu / 20 and 0.05 < gia * 1000 / gia_tham_chieu < 20:
        return gia * 1000, f"{ten}: {gia:,.4f} quá nhỏ → quy đổi thành {gia * 1000:,.2f} nghìn đồng"
    return gia, ""


def so_vn(x, le=0):
    """Định dạng số thống nhất toàn báo cáo: 34,500.25 (dấu phẩy ngăn nghìn)."""
    if not co(x):
        return "N/A"
    return f"{x:,.{le}f}"


def fmt_pct(x, le=1):
    return "N/A" if not co(x) else f"{x:+.{le}f}%"


def in_bang(tieu_de, bang, ff=lambda x: f"{x:,.2f}"):
    print(f"\n{'-' * 90}\n {tieu_de}\n{'-' * 90}")
    if bang is None or not len(bang):
        print("  (không có dữ liệu)")
    else:
        print(bang.to_string(index=False, float_format=ff, na_rep="–"))


class Tee(io.TextIOBase):
    """Ghi đồng thời ra nhiều nơi (màn hình + file báo cáo)."""
    def __init__(self, *dich):
        self.dich = [d for d in dich if d is not None]

    def write(self, s):
        for d in self.dich:
            d.write(s)
        return len(s)

    def flush(self):
        for d in self.dich:
            d.flush()


def gio_viet_nam():
    """Giờ Việt Nam (không phụ thuộc múi giờ máy chạy – Colab là UTC)."""
    return (pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=7)).tz_localize(None)


def loi_suat_tuan(close):
    """Lợi suất tuần (giá đóng cửa cuối tuần) – dùng cho tương quan danh mục."""
    return close.resample("W-FRI").last().pct_change(fill_method=None).dropna()
