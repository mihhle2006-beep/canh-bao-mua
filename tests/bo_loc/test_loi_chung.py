# -*- coding: utf-8 -*-
"""Bộ lọc dùng CHUNG lõi ptcp: cùng dữ liệu → cùng đỉnh/đáy, cắt lỗ, mục tiêu khung ngày như ptcp."""
import filecmp
import os

import pytest

from bo_loc import loi
from bo_loc.phan_tich.chi_so import tinh_chi_so

PTCP = os.environ.get("PTCP_DIR", "/tmp/pt2/ptcp_phan_tich/ptcp")


def test_cat_lo_va_muc_tieu_theo_chien_luoc_thi_truong(gia_tang):
    """Cắt lỗ = chuẩn hệ thoát (2×ATR, ≤ 7%, ≥ 1,5×ATR); mục tiêu = mốc 1R / 3R; upside tới 3R."""
    from bo_loc.loi.he_thoat import stop_chuan
    m = tinh_chi_so("AAA", gia_tang)
    d = loi.tinh_chi_bao(gia_tang)
    g = d.close.iloc[-1]
    cl = stop_chuan(g, d.ATR.iloc[-1])
    assert m["cat_lo"] == pytest.approx(cl) and m["gia_mt"] == pytest.approx(2 * g - cl)
    assert m["gia_mt_3r"] == pytest.approx(4 * g - 3 * cl) and m["upside"] == pytest.approx(3 * (g - cl) / g * 100)
    assert m["rr"] == 3.0 and "hệ thoát" in m["cat_lo_theo"]
    from bo_loc.chien_luoc_tt import ap_vao_chi_so
    ap_vao_chi_so(m, {"nhom": "VAO_NUA", "ten_nhom": "🟡 VÀO ½", "cl": g * 0.95})
    assert m["cat_lo"] == pytest.approx(g * 0.95) and m["gia_mt_3r"] == pytest.approx(g * 1.15)
    assert m["khuyen_nghi"] == "🟡 VÀO ½" and m["cat_lo_theo"] == "cắt lỗ hệ thống đang chạy"


def test_dinh_day_theo_gia_dong_cua(gia_tang):
    m = tinh_chi_so("AAA", gia_tang)
    d52 = gia_tang[gia_tang.index > gia_tang.index[-1] - __import__("pandas").Timedelta(weeks=52)]
    assert m["cao52"] == pytest.approx(d52.close.max())          # như ptcp (DINH_DAY_THEO = "close")


@pytest.mark.skipif(not os.path.isdir(PTCP), reason="không có thư mục ptcp để so")
@pytest.mark.parametrize("f", ["chi_bao.py", "thong_ke.py", "cau_hinh.py", "he_thoat.py", "chien_luoc.py"])
def test_loi_la_ban_sao_nguyen_van_ptcp(f):
    assert filecmp.cmp(os.path.join(os.path.dirname(loi.__file__), f), os.path.join(PTCP, f), shallow=False)
