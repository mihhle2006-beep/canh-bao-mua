# -*- coding: utf-8 -*-
"""Kế hoạch vị thế từ GIÁ MUA (ptcp.ke_hoach) – dùng chung cho chay.py và danh mục."""
import numpy as np
import pandas as pd
import pytest

from ptcp.ke_hoach import ke_hoach_tu_gia_mua, dong_ke_hoach, bang_ke_hoach
from tests.conftest import tao_gia


@pytest.fixture(scope="module")
def du_lieu():
    df = tao_gia(seed=11, xu_huong=0.0008)
    vni = tao_gia(seed=12, sigma=0.011, gia_dau=1000)
    return df, vni


def test_cat_lo_goc_va_muc_tieu_luc_mua_ky_thuat(du_lieu):
    df, vni = du_lieu
    nm = df.index[-120]
    gv = float(df.close.loc[nm])
    kh = ke_hoach_tu_gia_mua(df, gv, nm.strftime("%d/%m/%Y"), vni)
    assert kh["cat_lo_goc"] < gv and kh["R"] == pytest.approx(gv - kh["cat_lo_goc"])
    assert "muc_tieu_2R" not in kh                                    # không còn mục tiêu theo bội số R
    assert kh["muc_tieu_de_xuat"] > gv
    b = kh["bang_muc_tieu_luc_mua"]
    assert len(b) and (b["Giá mục tiêu"] > gv).all() and "EV %" in b
    assert kh["cat_lo_hien_tai"] >= kh["cat_lo_goc"]                  # chỉ dời lên
    assert kh["cat_lo_hien_tai"] <= kh["gia_hien_tai"] - kh["atr"] + 1e-9
    # cắt lỗ gốc & mục tiêu lúc mua chỉ dùng dữ liệu đến ngày mua: đổi giá SAU ngày mua không làm đổi
    df2 = df.copy()
    df2.loc[df2.index > nm, ["open", "high", "low", "close"]] *= 1.5
    kh2 = ke_hoach_tu_gia_mua(df2, gv, nm, vni)
    assert kh2["cat_lo_goc"] == pytest.approx(kh["cat_lo_goc"])
    assert kh2["muc_tieu_de_xuat"] == pytest.approx(kh["muc_tieu_de_xuat"])


def test_quy_tac_muc_tieu_bo_sung():
    from ptcp.chi_bao import tinh_chi_bao, tim_dinh_day
    from ptcp.phan_tich import _ung_vien_bo_sung
    df = tao_gia(seed=5, cuoi_giam=True)                              # vừa có nhịp giảm → Fibo hồi phục
    d = tinh_chi_bao(df)
    pvx = tim_dinh_day(d, "Ngày").query("xac_nhan")
    ten = [t for t, _ in _ung_vien_bo_sung(d, pvx, "Ngày", float(d.close.iloc[-1]))]
    assert any(t.startswith("Fibo hồi phục") for t in ten)
    assert any(t.startswith(("MA50", "MA200", "POC", "VAH", "Đỉnh 52")) for t in ten)
    # nền giá hẹp rồi bứt lên nửa trên → đo biên độ nền
    idx = pd.bdate_range(end="2026-10-02", periods=200)
    c = np.r_[np.linspace(10, 20, 150), 20 + np.sin(np.arange(45)) * 0.8, np.full(5, 20.7)]
    nen = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6}, index=idx)
    dn = tinh_chi_bao(nen)
    ten = [t for t, _ in _ung_vien_bo_sung(dn, tim_dinh_day(dn, "Ngày").query("xac_nhan"), "Ngày", 20.7)]
    assert any(t.startswith("Đo biên độ nền giá") for t in ten)


def test_so_voi_vnindex_tu_ngay_mua(du_lieu):
    df, vni = du_lieu
    nm = df.index[-200]
    kh = ke_hoach_tu_gia_mua(df, float(df.close.loc[nm]), nm, vni)
    v = kh["so_vni"]
    ky_vong = (vni.close.iloc[-1] / vni.close.asof(nm) - 1) * 100
    assert v["vni_pct"] == pytest.approx(ky_vong)
    assert v["chenh_lech"] == pytest.approx(kh["lai_lo_pct"] - ky_vong)
    assert any("VN-Index từ ngày mua" in d for d in dong_ke_hoach(kh))
    assert len(bang_ke_hoach(kh)) > 15


def test_khong_ngay_mua_van_co_ke_hoach(du_lieu):
    df, _ = du_lieu
    kh = ke_hoach_tu_gia_mua(df, float(df.close.iloc[-1]) * 0.9, None, None)
    assert kh["ngay_mua"] is None and kh["so_vni"] == {} and kh["cat_lo_goc"] > 0
    assert ke_hoach_tu_gia_mua(df, None) is None
