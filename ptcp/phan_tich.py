# -*- coding: utf-8 -*-
"""
GIỮ TƯƠNG THÍCH: phan_tich.py đã được tách thành 4 module nhỏ – import cũ `from ptcp.phan_tich import ...` vẫn chạy.
  thong_tin.py   – báo cáo CTCK, Phần A, kiểm tra dữ liệu, beta, cơ cấu CP, thông tin giao dịch, định giá
  muc_tieu.py    – cắt lỗ thống nhất, mục tiêu theo khung, vùng hội tụ, đề xuất mục tiêu
  kich_ban.py    – Phần D: kịch bản, xác suất, EV quyết định
  quyet_dinh.py  – trạng thái 3 khung, quản trị rủi ro, hàm quyết định duy nhất
"""
# flake8: noqa: F401
from .thong_tin import (
    CHU_GIAI_CP,
    bang_bao_cao_ctck,
    bien_dong_theo_khung,
    chuoi_tang_giam,
    co_cau_co_phieu,
    ctck_gan_nhat,
    danh_gia_dinh_gia,
    kiem_tra_du_lieu,
    phan_loai_phien,
    thong_tin_giao_dich,
    tinh_beta,
    von_hoa_chu,
)
from .muc_tieu import (
    DO_RONG_NEN_MAX,
    SO_NEN_GIA,
    _ung_vien_bo_sung,
    de_xuat_muc_tieu,
    tinh_cat_lo,
    tinh_muc_tieu,
    vung_hoi_tu,
)
from .kich_ban import (
    Y_NGHIA_KB,
    kich_ban_chinh,
    phan_tich_kich_ban,
    trang_thai_tuong_tu,
)
from .quyet_dinh import (
    danh_gia_co_ban,
    ket_luan_mua,
    quan_tri_rui_ro,
    quyet_dinh_cuoi,
)
