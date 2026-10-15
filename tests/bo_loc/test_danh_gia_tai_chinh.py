# -*- coding: utf-8 -*-
"""Kiểm thử bộ 10 tiêu chí phân tích tài chính (5 mức)."""
import numpy as np
import pytest

from bo_loc import danh_gia_tai_chinh as fa
from bo_loc import bon_bang as kf
from bo_loc.nguon import bctc_nam
from bo_loc.tieu_chi import kiem_tra


def bc(**k):
    """BCTC 4 năm (mới nhất trước) của một doanh nghiệp tốt; ghi đè chỉ tiêu bằng tham số."""
    d = {"nam": [2025, 2024, 2023, 2022], "doanh_thu": [1500, 1200, 1000, 900], "ln_gop": [450, 340, 270, 230],
         "lnst": [300, 220, 170, 140], "cfo": [350, 250, 200, 150], "cr": [2.2, 2.0, 1.8, 1.6],
         "icr": [12, 10, 9, 8], "de": [0.5, 0.6, 0.7, 0.8], "roe": [24, 22, 21, 20],
         "von_gop": [1000, 1000, 900, 900], "vay_no": [200, 250, 300, 300]}
    d.update(k)
    return d


def test_doanh_nghiep_tot_dat_muc_cao():
    kq = fa.danh_gia(bc(), gia=50)
    ct = {k: m for k, (m, _) in kq["chi_tiet"].items()}
    assert ct["Tăng trưởng doanh thu"] == 4          # tăng liên tiếp, TB < 20%/năm
    assert ct["Biên lãi gộp"] == 5                   # dương, tăng dần, TB ≥ 25%
    assert ct["Chất lượng dòng tiền"] == 5           # dương 3 năm & ≥ LNST
    assert ct["Khả năng thanh toán"] == 5            # > 1,5 liên tục và tăng dần
    assert ct["Áp lực nợ vay"] == 4                  # EBIT/lãi vay > 5
    assert ct["Cấu trúc vốn"] == 4                   # giảm liên tiếp, < 1
    assert ct["ROE"] == 5                            # tăng liên tiếp, min > 20%
    assert ct["Phát hành tăng vốn"] == 4             # giá > 5, ×1,1 & EPS tăng
    assert ct["Kế hoạch kinh doanh"] is None and kq["so_nguy_hiem"] == 0 and kq["diem"] > 75


@pytest.mark.parametrize("ham,du_lieu,muc", [
    (fa.tang_truong_doanh_thu, bc(doanh_thu=[700, 800, 900, 1000], ln_gop=[-10, 50, 60, 70]), 1),
    (fa.tang_truong_doanh_thu, bc(doanh_thu=[700, 800, 900, 1000]), 2),
    (fa.tang_truong_doanh_thu, bc(doanh_thu=[2000, 1500, 1200, 1000]), 5),   # +20/25/33%… gia tốc? → kiểm dưới
    (fa.tang_truong_loi_nhuan, bc(lnst=[-50, 100, 150, 200]), 1),
    (fa.tang_truong_loi_nhuan, bc(lnst=[100, -20, 150, 120]), 2),
    (fa.chat_luong_dong_tien, bc(cfo=[-1, -2, -3]), 1),
    (fa.chat_luong_dong_tien, bc(cfo=[-1, 20, 30]), 2),
    (fa.kha_nang_thanh_toan, bc(cr=[0.4, 0.6, 0.8]), 1),
    (fa.kha_nang_thanh_toan, bc(cr=[0.65, 1.0, 1.2]), 2),
    (fa.ap_luc_no_vay, bc(icr=[0.3, 0.4, 0.2]), 1),
    (fa.ap_luc_no_vay, bc(vay_no=[0, 0, 0]), 5),
    (fa.cau_truc_von, bc(de=[3.5, 2.5, 1.5]), 1),
    (fa.cau_truc_von, bc(de=[2.3, 2.5, 2.6]), 2),
    (fa.cau_truc_von, bc(de=[0.1, 0.3, 0.2]), 5),
    (fa.roe_3_nam, bc(roe=[-5, -2, 10]), 1),
    (fa.roe_3_nam, bc(roe=[15, 18, 22]), 2),                                 # giảm liên tiếp
    (fa.bien_lai_gop, bc(ln_gop=[100, -10, 50]), 2),
])
def test_muc_danh_gia(ham, du_lieu, muc):
    assert ham(du_lieu)[0] == muc


def test_gia_toc_doanh_thu():
    # tăng 33%, 25%, 20% (mới nhất trước) → gia tốc tăng, TB > 20% → Rất tốt
    assert fa.tang_truong_doanh_thu(bc(doanh_thu=[2000, 1500, 1200, 1000]))[0] == 5
    # tăng 10%, 20%, 30% → giảm tốc → Tốt
    assert fa.tang_truong_doanh_thu(bc(doanh_thu=[1716, 1560, 1300, 1000]))[0] == 4


def test_phat_hanh_tang_von_qua_nong():
    assert fa.phat_hanh_tang_von(bc(von_gop=[3000, 1500, 1200, 1000]), gia=4)[0] == 1     # giá < 5, ×3 trong 3 năm
    assert fa.phat_hanh_tang_von(bc(von_gop=[2600, 1500, 1200, 1000]), gia=20)[0] == 2    # ×2,6 trong 3 năm
    assert fa.phat_hanh_tang_von(bc(von_gop=[3100, 2000, 1500, 1200, 1000]), gia=20)[0] == 1   # ×3,1 trong 4 năm


def test_ngan_hang_bo_chi_tieu_khong_phu_hop_va_thieu_du_lieu():
    kq = fa.danh_gia(bc(), gia=30, la_tai_chinh=True)
    assert kq["chi_tiet"]["Cấu trúc vốn"][0] is None and "ngân hàng" in kq["chi_tiet"]["Cấu trúc vốn"][1]
    assert np.isnan(fa.danh_gia(None)["diem"])


def test_tieu_chi_loc_va_bang_ket_qua():
    kq = fa.danh_gia(bc(roe=[-5, -2, 10], lnst=[-50, -20, 150, 200]), gia=20)
    m = {"fa_diem": kq["diem"], "fa_nguy_hiem": kq["so_nguy_hiem"]}
    assert kq["so_nguy_hiem"] >= 2 and kiem_tra("fa_khong_nguy_hiem", m, None) is False
    assert kiem_tra("fa_khong_nguy_hiem", {"fa_diem": np.nan, "fa_nguy_hiem": np.nan}, None) is None
    tot = fa.danh_gia(bc(), gia=50)
    ds = [{"Mã": "AAA", "gia": 50.0, "fa_chi_tiet": tot["chi_tiet"], "fa_diem": tot["diem"], "fa_nguon": "Yahoo (BCTC 2025)"},
          {"Mã": "BBB", "gia": 20.0, "fa_chi_tiet": kq["chi_tiet"], "fa_diem": kq["diem"], "fa_nguon": "TCBS (BCTC 2025)"}]
    b = kf.lap_4_bang(ds)["PHÂN TÍCH TÀI CHÍNH"]
    assert list(b.columns) == ["CHỈ TIÊU", "AAA", "BBB"] and b.iloc[8]["AAA"] == "Rất tốt" and b.iloc[8]["BBB"] == "Nguy hiểm"


def test_doc_bctc_nam_tcbs(monkeypatch, tmp_path):
    def gia_lap(url, params=None, **k):
        nam = [2025, 2024, 2023, 2022]
        if "financialratio" in url:
            return [{"year": y, "currentPayment": 1.6, "ebitOnInterest": 9, "payableOnEquity": 0.6, "roe": 0.2}
                    for y in nam]
        if "incomestatement" in url:
            return [{"year": y, "revenue": 1000 + i, "grossProfit": 300, "shareHolderIncome": 150} for i, y in enumerate(nam)]
        if "cashflow" in url:
            return [{"year": y, "fromSale": 200} for y in nam]
        return [{"year": y, "capital": 1000, "shortDebt": 50, "longDebt": 0} for y in nam]
    from ptcp import du_lieu as ptcp_dl                       # đọc nguồn = ptcp (một nguồn logic)
    monkeypatch.setattr(ptcp_dl, "_goi_api", gia_lap)
    kq = bctc_nam.lay_bctc_nam("GMD", dung_cache=True, thu_muc_cache=str(tmp_path), thu_tu=("TCBS",))
    assert kq["nguon"] == "TCBS" and kq["nam"][0] == 2025 and kq["roe"][0] == pytest.approx(20)
    assert kq["vay_no"][0] == 50 and (tmp_path / "GMD_nam.json").exists()
