# -*- coding: utf-8 -*-
"""
BỘ LỌC CỔ PHIẾU (gói module). Chạy:  python -m bo_loc --nhom cang_bien
Cấu trúc:
  cau_hinh.py        mọi ngưỡng/hằng số
  danh_sach_ma.py    nhóm mã, ngưỡng riêng theo nhóm/mã, danh sách HOSE
  nguon/             dữ liệu: gia.py (7 nguồn giá), co_ban.py (nhiều nguồn cơ bản + gộp/đối chiếu), http.py
  phan_tich/         ky_thuat.py (chỉ báo, đỉnh đáy, mục tiêu), chi_so.py (chỉ tiêu 1 mã)
  tieu_chi.py        danh mục tiêu chí
  chien_luoc/        MỖI CHIẾN LƯỢC 1 FILE (thêm/sửa chiến lược ở đây)
  loc.py             B1 lọc & xếp hạng
  danh_gia_sau_loc.py B2–B6 chấm điểm, cờ đỏ, kế hoạch, hành động, so sánh nhóm
  lich_su.py, xuat.py, cli.py
"""
__version__ = "beta 1.1"
