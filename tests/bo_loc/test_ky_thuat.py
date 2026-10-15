# -*- coding: utf-8 -*-
"""Kiểm thử lõi kỹ thuật: chỉ báo, SuperTrend, ADX, đỉnh/đáy, mục tiêu."""
import pytest
import numpy as np
import pandas as pd

from bo_loc.phan_tich import ky_thuat as kt


def test_chi_bao_co_du_cot_va_rsi_trong_0_100(gia_tang):
    d = kt.tinh_chi_bao(gia_tang)
    for c in ("MACD", "SIGNAL", "HIST", "RSI", "ATR", "VolMA20", "pos"):
        assert c in d
    rsi = d.RSI.dropna()
    assert ((rsi >= 0) & (rsi <= 100)).all()
    assert (d.ATR.dropna() > 0).all()


def test_macd_dung_cong_thuc(gia_tang):
    d = kt.tinh_chi_bao(gia_tang)
    c = gia_tang.close
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    assert np.allclose(d.MACD.values, macd.values)
    assert np.allclose(d.HIST.values, (d.MACD - d.SIGNAL).values)


def test_supertrend_theo_xu_huong(gia_tang, gia_giam):
    _, huong_t = kt.supertrend(gia_tang, 10, 3.5)
    _, huong_g = kt.supertrend(gia_giam, 10, 3.5)
    assert huong_t.tail(200).mean() > huong_g.tail(200).mean()
    assert set(np.unique(huong_t)) <= {-1.0, 1.0}


def test_adx_trong_khoang(gia_tang):
    adx, _, _ = kt.tinh_adx(gia_tang)
    v = adx.dropna()
    assert ((v >= 0) & (v <= 100)).all()


def test_adx_xu_huong_tang_deu():
    c = pd.Series(np.linspace(50, 100, 200), index=pd.bdate_range("2025-01-01", periods=200))
    df = pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1e6})
    adx, pdi, mdi = kt.tinh_adx(df)
    assert pdi.iloc[-1] > mdi.iloc[-1] and adx.iloc[-1] > 25          # +DI trội, xu hướng mạnh


def test_gop_tuan_dong_cua_bang_phien_cuoi_tuan(gia_tang):
    w = kt.gop_tuan(gia_tang)
    tuan = w.index[-2]
    ngay_trong_tuan = gia_tang[(gia_tang.index > tuan - pd.Timedelta(days=7)) & (gia_tang.index <= tuan)]
    assert w.loc[tuan, "close"] == ngay_trong_tuan.close.iloc[-1]
    assert w.loc[tuan, "high"] == ngay_trong_tuan.high.max()
    assert w.loc[tuan, "volume"] == pytest.approx(ngay_trong_tuan.volume.sum(), rel=1e-12)   # pandas 3: sai số cộng dồn


def test_dinh_day_xen_ke_va_xac_nhan(gia_tang):
    d = kt.tinh_chi_bao(gia_tang)
    pv = kt.tim_dinh_day(d)
    assert len(pv) > 4
    assert all(a != b for a, b in zip(pv.loai, pv.loai.iloc[1:]))     # Đỉnh/Đáy xen kẽ
    assert not pv.xac_nhan.iloc[-1] and pv.xac_nhan.iloc[:-1].all()   # chỉ đoạn cuối chưa xác nhận


def test_muc_tieu_tren_gia_cat_lo_duoi_gia(gia_tang):
    d = kt.tinh_chi_bao(gia_tang)
    pv = kt.tim_dinh_day(d)
    xh = kt.duong_xu_huong(d, pv)
    mt = kt.tinh_muc_tieu(d, pv, xh, "Ngày")
    gia = d.close.iloc[-1]
    assert mt["cat_lo"] < gia
    if len(mt["bang"]):
        assert (mt["bang"]["Giá mục tiêu"] > gia).all()


def test_tin_hieu_tra_ve_diem(gia_tang):
    d = kt.tinh_chi_bao(gia_tang)
    pv = kt.tim_dinh_day(d)
    ds, tong, co = kt.phan_tich_tin_hieu(d, pv, kt.duong_xu_huong(d, pv), "Ngày")
    assert tong == sum(x[2] for x in ds)
    assert {"cat_len_signal", "thung_ho_tro"} <= set(co)


def test_xep_loai_khuyen_nghi():
    assert kt.xep_loai_khuyen_nghi(20)[0] == "MUA"
    assert kt.xep_loai_khuyen_nghi(0)[0] == "NẮM GIỮ"
    assert kt.xep_loai_khuyen_nghi(-30)[0] == "BÁN"
    assert kt.xep_loai_khuyen_nghi(np.nan)[0] == "N/A"
