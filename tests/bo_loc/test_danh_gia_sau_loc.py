# -*- coding: utf-8 -*-
"""Kiểm thử B2–B6: khối lượng theo rủi ro, hành động, so sánh trung vị NHÓM."""
import numpy as np
import pandas as pd
import pytest

from bo_loc import cau_hinh as ch
from bo_loc import danh_gia_sau_loc as dg


def _m(**k):
    m = {"gia": 100.0, "atr": 2.0, "cat_lo": 95.0, "gia_mt": 120.0, "ma20": 98.0, "klgd20": 1_000_000}
    m.update(k)
    return m


def test_ke_hoach_khoi_luong_theo_rui_ro():
    kh = dg.ke_hoach_giao_dich(_m(), von_trieu=1000, rui_ro_pct=0.5)
    # cắt lỗ = cắt lỗ thống nhất của lõi ptcp (95) → rủi ro 5 nghìn/CP; 0,5% × 1 tỷ = 5 triệu → 1.000 CP
    assert kh["cat_lo_kh"] == 95 and kh["so_cp_kh"] == 1000
    assert kh["rr_kh"] == pytest.approx(4)
    assert kh["so_cp_kh"] % 100 == 0
    assert kh["rang_buoc_kl"] == "rủi ro/lệnh"


def test_ke_hoach_bi_chan_boi_ty_trong_toi_da():
    kh = dg.ke_hoach_giao_dich(_m(atr=0.2, cat_lo=np.nan), von_trieu=1000, rui_ro_pct=5)
    assert kh["ty_trong_kh"] <= ch.TY_TRONG_MAX + 1e-9
    assert "tỷ trọng" in kh["rang_buoc_kl"]


@pytest.mark.parametrize("dat,gan,diem,rr,nang,nhe,mong_doi", [
    (True, False, 80, 3, [], [], "MUA"),
    (True, False, 80, 3, [], ["RSI 78 – quá mua"], "MUA KHI CHỈNH VỀ VÙNG MUA"),
    (True, False, 60, 3, [], [], "MUA THĂM DÒ (½ vị thế)"),
    (False, True, 60, 3, [], [], "THEO DÕI"),
    (True, False, 90, 3, ["Dưới SuperTrend"], [], "THEO DÕI – có cờ đỏ"),
    (False, False, 90, 3, [], [], "LOẠI"),
])
def test_xep_loai_hanh_dong(dat, gan, diem, rr, nang, nhe, mong_doi):
    assert dg.xep_loai_hanh_dong(dat, gan, diem, rr, nang, nhe) == mong_doi


def test_so_sanh_trung_vi_theo_nhom_khong_phai_toan_bo():
    e = pd.DataFrame({"Mã": list("ABCDEF"), "Nhóm": ["cang"] * 3 + ["ngan_hang"] * 3,
                      "pe": [10, 20, 30, 5, 6, 7], "pb": [1, 2, 3, 1, 1, 1], "roe": [10, 12, 14, 18, 20, 22]})
    r = dg.so_sanh_trong_nhom(e).set_index("Mã")
    assert r.loc["B", "P/E so TV nhóm"] == pytest.approx(1.0)     # trung vị nhóm cảng = 20
    assert r.loc["E", "P/E so TV nhóm"] == pytest.approx(1.0)     # trung vị nhóm ngân hàng = 6
    assert r.loc["A", "ROE − TV nhóm"] == pytest.approx(-2)
    assert r.loc["A", "Cơ sở so sánh"] == "nhóm cang"


def test_nhom_qua_it_ma_so_voi_toan_bo():
    e = pd.DataFrame({"Mã": list("ABC"), "Nhóm": ["x", "y", "z"], "pe": [10, 20, 30], "pb": [1, 2, 3],
                      "roe": [1, 2, 3]})
    r = dg.so_sanh_trong_nhom(e).set_index("Mã")
    assert r.loc["A", "P/E so TV nhóm"] == pytest.approx(0.5)
    assert (r["Cơ sở so sánh"] == "toàn bộ mã quét").all()


def test_diem_tong_bo_qua_tru_cot_thieu():
    assert dg.diem_tong({"Xu hướng": 100, "Động lượng": np.nan, "Định giá": 0, "Chất lượng": np.nan,
                         "Rủi ro": np.nan}) == pytest.approx(100 * 0.30 / 0.45)
    assert np.isnan(dg.diem_tong({}))


def test_gia_lo_mot_phan_ba_duoi_vung():
    from bo_loc.danh_gia_sau_loc import _gia_lo
    assert _gia_lo(44.5, 46.75) == 45.25 and _gia_lo(10.0, 10.5) == 10.15
