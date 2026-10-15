# -*- coding: utf-8 -*-
"""
LÕI TÍNH TOÁN = ptcp (không còn bản sao). bo_loc.loi.<x> trỏ thẳng tới ptcp.<x>: chỉ báo, đỉnh/đáy theo GIÁ ĐÓNG CỬA,
đường xu hướng, cắt lỗ thống nhất, mục tiêu, chiến lược thị trường, hệ thoát → bộ lọc, ptcp, canh-bao-mua luôn cùng
một logic; sửa ptcp (repo danh-muc) là bộ lọc dùng ngay. Nạp ptcp: bo_loc/_ptcp.py.
"""
from .._ptcp import bi_danh

for _ten in ("cau_hinh", "chi_bao", "thong_ke", "in_an", "mau", "so", "he_thoat", "chien_luoc", "bo_sung"):
    bi_danh(f"{__name__}.{_ten}", f"ptcp.{_ten}")
bi_danh(f"{__name__}.phan_tich", "ptcp.muc_tieu")              # cắt lỗ / mục tiêu (trước ở loi/phan_tich.py)

from ptcp.chi_bao import duong_xu_huong, phan_tich_tin_hieu, tim_dinh_day, tinh_chi_bao  # noqa: E402,F401
from ptcp.muc_tieu import tinh_cat_lo, tinh_muc_tieu  # noqa: E402,F401

PHIEN_NGAN_HAN = 63        # = ptcp n_phien mặc định (mục tiêu khung ngày)
PHIEN_TRUNG_HAN = 252      # = ptcp ky_han mặc định (mục tiêu khung tuần)
