# -*- coding: utf-8 -*-
"""Bộ lọc quy_b: mã CHƯA có kết quả chiến lược thị trường (< 260 phiên / phần chiến lược lỗi) không được "đạt lọc" theo
kiểu thiếu dữ liệu (◐) rồi lên MUA theo điểm – phải là KHÔNG đạt (15/11/2026)."""
from bo_loc.chien_luoc import tai_tat_ca
from bo_loc.loc import danh_gia, nhan_dat


def test_quy_b_khong_co_chien_luoc_thi_khong_dat():
    cl = tai_tat_ca(thu_muc_rieng=None)["quy_b"]
    m = {"gtgd20": 50.0, "gia": 20.0, "ma50": 18.0, "ma200": 15.0, "rs3t": 10.0, "vol_ratio": 2.0, "cach_dinh52": -3.0}
    _, _, _, dat, thieu, thieu_dl = danh_gia({**m, "cl_tt": None}, cl, nghiem_ngat=False)
    assert not dat and nhan_dat(dat, thieu_dl) == "" and any("nhóm MUA" in x for x in thieu)
    _, _, _, dat, _, thieu_dl = danh_gia({**m, "cl_tt": {"nhom": "MUA_MOI"}}, cl, nghiem_ngat=False)
    assert dat and nhan_dat(dat, thieu_dl) == "✔"
    _, _, _, dat, _, _ = danh_gia({**m, "cl_tt": {"nhom": "NGOAI_TOP"}}, cl, nghiem_ngat=False)
    assert not dat
