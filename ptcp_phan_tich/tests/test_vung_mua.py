# -*- coding: utf-8 -*-
"""Vùng mua điều chỉnh, backtest vùng mua & kết luận Phần I (không mạng)."""
import numpy as np
import pytest

from ptcp.bao_cao import ket_luan_backtest
from ptcp.chi_bao import tinh_chi_bao
from ptcp.du_lieu import gop_tuan
from ptcp.vung_mua import _chuan_bi, backtest_vung_mua, tinh_vung, vung_mua_hien_tai
from tests.conftest import tao_gia


def _du_lieu(seed=7, n=1500):
    d = tinh_chi_bao(tao_gia(seed=seed, n=n))
    w = tinh_chi_bao(gop_tuan(d[["open", "high", "low", "close", "volume"]]))
    return d, w


def test_vung_khong_nhin_truoc():
    d, w = _du_lieu()
    x_day_du = _chuan_bi(d, w)
    for i in (400, 800, 1200):
        cat = d.iloc[:i + 1]
        x_cat = _chuan_bi(tinh_chi_bao(cat[["open", "high", "low", "close", "volume"]].copy()),
                          tinh_chi_bao(gop_tuan(cat[["open", "high", "low", "close", "volume"]])))
        a, b = tinh_vung(x_day_du, i), tinh_vung(x_cat, i)
        assert (a is None) == (b is None)
        if a:
            assert a["lo"] == pytest.approx(b["lo"]) and a["hi"] == pytest.approx(b["hi"])


def test_vung_nam_duoi_va_gan_gia():
    d, w = _du_lieu()
    x = _chuan_bi(d, w)
    so = 0
    for i in range(300, len(d), 37):
        v = tinh_vung(x, i)
        if v is None:
            continue
        so += 1
        assert v["lo"] <= v["hi"] and v["stop"] < v["lo"]
        assert v["hi"] <= x["c"][i] + 0.3 * x["atr"][i] + 0.2 * x["atr"][i] + 1e-9
        assert v["lo"] >= x["c"][i] * 0.85 - 0.2 * x["atr"][i] - 1e-9
        assert v["so_loai"] >= 2
    assert so > 0


@pytest.mark.parametrize("thoat", ["co_dinh", "dong", "tung_phan"])
def test_backtest_vung_mua(thoat):
    d, w = _du_lieu()
    r = backtest_vung_mua(d, w, 63, thoat)
    v, m = r["vung"], r["mua_ngay"]
    assert v["so_thiet_lap"] >= v["so_ve_vung"] >= v["so_lenh"]
    assert m["so_lenh"] > 0
    if v["so_lenh"]:
        b = v["bang"]
        assert (b["Ngày bán"] >= b["Ngày mua"]).all()
        assert 0 <= v["xs_1R"] <= 100


def test_vung_mua_hien_tai_trang_thai():
    d, w = _du_lieu(seed=11)
    vm = vung_mua_hien_tai(d, w)
    if vm is not None:
        assert vm["trang_thai"] and vm["stop"] < vm["lo"]


def _b(tb, pf, n, tong, mdd, thang=31.0, bh=1.5):
    return {"so_lenh": n, "tb": tb, "pf": pf, "tong": tong, "mdd": mdd, "ty_le_thang": thang, "buy_hold": bh,
            "tb_thang": 9.0, "tb_thua": -7.0, "giu_tb": 11, "so_nam": 7.5}


def test_ket_luan_kieu_gmd_khong_con_cau_chua_du():
    bt = _b(-2.10, 0.57, 26, -47.4, -53.5)
    bt0 = _b(-1.62, 0.65, 52, -64.0, -65.1)
    thoat = {"dong": _b(-0.87, 0.80, 26, -28.2, -53.0, 39), "tung_phan": _b(-0.92, 0.78, 26, -26.5, -45.3, 43)}
    vm = {k: {"vung": _b(-0.5, 0.9, 8, -5.0, -15.0), "mua_ngay": _b(-1.5, 0.7, 40, -40.0, -50.0)}
          for k in ("co_dinh", "dong", "tung_phan")}
    kl = ket_luan_backtest(bt, bt0, thoat, vm)
    txt = " ".join(kl["dong"])
    assert "chưa đủ" not in txt
    assert "KHÔNG có lợi thế" in kl["dong"][0]
    assert "điểm VÀO" in txt                       # cắt lỗ động giảm lỗ nhưng không làm quy tắc có lãi
    assert kl["dong"][-1].startswith(("ĐỨNG NGOÀI", "KHÔNG giao dịch"))
    assert not kl["co_loi_the"]


def test_ket_luan_chon_to_hop_co_loi_the():
    bt = _b(-0.5, 0.9, 30, -10, -30)
    vm = {"co_dinh": {"vung": _b(3.0, 2.0, 12, 40, -12, 50), "mua_ngay": _b(0.2, 1.05, 40, 5, -40)}}
    kl = ket_luan_backtest(bt, bt, {}, vm)
    assert kl["co_loi_the"] and kl["dong"][-1].startswith("ÁP DỤNG: Chờ về vùng mua")


def test_gia_han_lenh_giu_lenh_lai_va_ban_lenh_khong_chay():
    """Tới hạn: lãi ≥ 1R → giữ quá hạn (siết); lãi < 1R → bán đúng phiên hạn như cũ."""
    from ptcp import cau_hinh as cfg
    from ptcp.bo_sung import mo_phong_thoat
    n = 200
    o = h = l = c = None
    # chuỗi tăng đều: lệnh lãi lớn, không chạm cắt lỗ
    c = np.linspace(10, 30, n)
    o, h, l = c, c * 1.005, c * 0.995
    khoa = np.zeros(n, bool)
    cu = cfg.GIA_HAN_LENH
    try:
        cfg.GIA_HAN_LENH = False
        j0, _, ly0 = mo_phong_thoat(0, 10.0, 9.0, 99, o, h, l, c, 0.3, khoa, 63, "dong")
        cfg.GIA_HAN_LENH = True
        j1, ra1, ly1 = mo_phong_thoat(0, 10.0, 9.0, 99, o, h, l, c, 0.3, khoa, 63, "dong")
        j2, _, _ = mo_phong_thoat(0, 10.0, 9.0, 99, o, h, l, c, 0.3, khoa, 63, "dong_63")
    finally:
        cfg.GIA_HAN_LENH = cu
    assert j0 == 63 and j2 == 63 and ly0 == "hết hạn"
    assert j1 > 63 and ra1 > c[63]
    # đi ngang: lãi < 1R tới hạn → bán đúng phiên 63
    c2 = np.full(n, 10.2)
    j3, _, ly3 = mo_phong_thoat(0, 10.0, 9.0, 99, c2, c2 * 1.002, c2 * 0.998, c2, 0.3, khoa, 63, "dong")
    assert j3 == 63 and "lãi <" in ly3


def test_ke_hoach_ghi_han_lenh():
    from ptcp.ke_hoach import ke_hoach_tu_gia_mua
    d = tao_gia(seed=3)
    nm = d.index[-100]
    kh = ke_hoach_tu_gia_mua(d, float(d.close.loc[nm]), nm, H=63)
    assert kh["so_phien_giu"] == 99 and kh["han_lenh"]
