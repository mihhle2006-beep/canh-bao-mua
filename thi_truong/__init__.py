# -*- coding: utf-8 -*-
"""
BẢNG THỊ TRƯỜNG (trang web docs/thi_truong/ – GitHub Pages): tổng quan chỉ số, VN-Index trong phiên, bản đồ nhiệt HOSE
theo ngành, thống kê phiên (độ rộng, thanh khoản & dự kiến, khối ngoại, tự doanh), tác động lên VN-Index và bộ LỌC MÃ
(biến động, dòng tiền, khối ngoại, kỹ thuật). Chỉ dữ liệu THỊ TRƯỜNG công khai – không đọc / ghi danh mục.

  python -m thi_truong --chuan_bi        # sau phiên: lịch sử 260 phiên, khối ngoại / tự doanh, ngành, hồ sơ thanh khoản
  python -m thi_truong                   # trong phiên (5'): bảng giá + chỉ số + nến 1' → docs/thi_truong/du_lieu.json
"""


def ma_them(duong=None):
    """Mã thêm ngoài ds.json (thi_truong/ma_them.txt): bỏ dòng '#', tách dấu phẩy / khoảng trắng, chữ hoa, không trùng."""
    import os
    import re
    try:
        txt = open(duong or os.path.join(os.path.dirname(__file__), "ma_them.txt"), encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for m in re.split(r"[,\s]+", "\n".join(d for d in txt.splitlines() if not d.lstrip().startswith("#"))):
        m = m.strip().upper()
        if m.isalnum() and 3 <= len(m) <= 8 and m not in out:
            out.append(m)
    return out
