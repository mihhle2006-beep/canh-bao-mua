# -*- coding: utf-8 -*-
"""Logic quyết định: một nguồn khuyến nghị, tuần phủ quyết, ngưỡng EV/R-R, thị trường & sự kiện, cắt lỗ."""
import pandas as pd
import pytest

from ptcp import phan_tich as pt, chi_bao as cb, cau_hinh as cfg

TG_TOT = {"tuan_ok": True, "tuan_rat_tot": True, "ngay_ok": True, "gio_ok": True}
KB, QR, DX, ST = {"ev_qd": 3.0}, {"rr": 3.0, "phong_thu": False, "gia_mua_rr2": 10}, {"chon": 12}, \
    {"gia": 9.0, "pct": -7.0}
XAU = dict(vni_xau=False, rs_yeu=False, chan=False, su_kien=[], he_so=1.0, co_vni=True, co_rs=True)


def qd(tg=TG_TOT, kb=KB, qr=QR, ttr=None):
    return pt.quyet_dinh_cuoi(tg, kb, qr, DX, 10.0, ST, ttr)


def test_du_dieu_kien_thi_mua():
    assert qd()["mua"]


def test_tuan_phu_quyet():
    k = qd(tg={**TG_TOT, "tuan_ok": False})
    assert k["khuyen_nghi"] == "CHƯA MUA" and not k["mua"]


@pytest.mark.parametrize("ev", [0.5, -2.0, float("nan")])
def test_ev_thap_khong_mua(ev):
    assert qd(kb={"ev_qd": ev})["khuyen_nghi"] == "CHƯA MUA"


def test_rr_thap_cho_gia():
    assert qd(qr={**QR, "rr": 1.2})["khuyen_nghi"] == "CHỜ GIÁ TỐT HƠN"


def test_muc_tieu_duoi_gia_khong_mua_moi():
    assert qd(qr={**QR, "phong_thu": True})["khuyen_nghi"] == "KHÔNG MUA MỚI"


@pytest.mark.parametrize("ttr, ky_vong", [
    ({**XAU, "vni_xau": True, "he_so": .5}, "MUA TỪNG PHẦN"),
    ({**XAU, "vni_xau": True, "rs_yeu": True, "he_so": .25}, "THEO DÕI"),
    ({**XAU, "chan": True, "su_kien": ["Công bố KQKD"]}, "CHỜ SAU SỰ KIỆN"),
])
def test_boi_canh_thi_truong_va_su_kien(ttr, ky_vong):
    assert qd(ttr=ttr)["khuyen_nghi"] == ky_vong


def test_cat_lo_thong_nhat_trong_gioi_han(gia_ngay):
    d = cb.tinh_chi_bao(gia_ngay)
    pv = cb.tim_dinh_day(d, "Ngày")
    ht = d.close.iloc[-1]
    st = pt.tinh_cat_lo(d, pv, ht)
    atr = d.ATR.iloc[-1]
    assert st["gia"] < ht
    assert ht - st["gia"] >= cfg.STOP_ATR_MIN * atr - 1e-9
    assert st["gia"] >= min(ht * (1 - cfg.LO_CUNG_PCT / 100), ht - cfg.STOP_ATR_MIN * atr) - 1e-9


def test_dinh_day_nen_hien_tai_la_tam_thoi():
    from tests.conftest import tao_gia
    d = cb.tinh_chi_bao(tao_gia(seed=5, cuoi_giam=True))
    pv = cb.tim_dinh_day(d, "Ngày")
    cuoi = pv.iloc[-1]
    assert cuoi.loai == "Đáy" and cuoi.pos == len(d) - 1 and not cuoi.xac_nhan
    xh = cb.duong_xu_huong(d, pv)
    if "ho_tro" in xh:      # hỗ trợ không còn tự neo vào giá hiện tại (lỗi 'cách 0.0%')
        assert abs(xh["ho_tro"]["gia_nay"] / d.close.iloc[-1] - 1) > 0.005


def test_phan_loai_phien_tach_tran_san(gia_ngay):
    b, _ = pt.phan_loai_phien(gia_ngay, 6.7)
    ten = " ".join(b["Trường hợp"])
    assert "Tăng trần" in ten and "Giảm sàn" in ten
