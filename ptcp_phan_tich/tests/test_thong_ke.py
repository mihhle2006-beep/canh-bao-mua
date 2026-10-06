# -*- coding: utf-8 -*-
"""Mô phỏng theo luật giao dịch VN: mua giá mở cửa, T+2, khoá sàn, gap; walk-forward; bootstrap."""
import numpy as np
import pandas as pd
import pytest

from ptcp import thong_ke as tk, cau_hinh as cfg


def _df(gia, mo=None, cao=None, thap=None):
    gia = np.asarray(gia, float)
    mo = gia if mo is None else np.asarray(mo, float)
    cao = np.maximum(gia, mo) if cao is None else np.asarray(cao, float)
    thap = np.minimum(gia, mo) if thap is None else np.asarray(thap, float)
    return pd.DataFrame({"open": mo, "high": cao, "low": thap, "close": gia, "volume": 1.0},
                        index=pd.bdate_range("2026-01-01", periods=len(gia)))


def test_mua_gia_mo_cua_phien_sau():
    df = _df([10, 10, 10, 10, 10, 10], mo=[10, 11, 10, 10, 10, 10])
    s = tk._mo_phong(df, 3)
    assert s.r_end.iloc[0] == pytest.approx((10 / 11 - 1) * 100)      # vào ở 11 (mở cửa phiên sau)


def test_cat_lo_cham_truoc_T2_thi_ban_o_gia_mo_cua_T2():
    # phiên mua (T) giá thấp nhất chạm cắt lỗ -5%, nhưng chỉ bán được từ T+2 ở giá mở cửa 9.8
    gia = [10, 10, 9.9, 9.8, 9.8, 9.8]
    df = _df(gia, mo=[10, 10, 9.9, 9.8, 9.8, 9.8], thap=[10, 9.4, 9.9, 9.8, 9.8, 9.8])
    s = tk._mo_phong(df, 4, duoi=-5)
    assert s.kq.iloc[0] == "duoi"
    assert s.r_exit.iloc[0] == pytest.approx((9.8 / 10 - 1) * 100)   # không phải đúng -5%
    assert s.t.iloc[0] == cfg.T_CONG + 1


def test_khoa_san_doi_sang_phien_sau():
    cfg.NGUONG_TRAN_SAN = 6.7
    # T+2 đóng cửa ở giá sàn (= giá thấp nhất) → không bán được, bán ở mở cửa T+3
    gia = [10, 10, 9.9, 9.2, 9.0, 9.0]
    df = _df(gia, mo=[10, 10, 9.9, 9.6, 8.9, 9.0], thap=[10, 9.95, 9.85, 9.2, 8.9, 9.0])
    s = tk._mo_phong(df, 4, duoi=-5)
    assert s.kq.iloc[0] == "duoi" and s.r_exit.iloc[0] == pytest.approx((8.9 / 10 - 1) * 100)


def test_gap_qua_muc_tieu_ban_o_gia_mo_cua():
    gia = [10, 10, 10, 12, 12, 12]
    df = _df(gia, mo=[10, 10, 10, 12, 12, 12])
    s = tk._mo_phong(df, 4, tren=10)
    assert s.kq.iloc[0] == "tren" and s.r_exit.iloc[0] == pytest.approx(20.0)


def test_phien_khoa_tran_khong_mua_duoc():
    cfg.NGUONG_TRAN_SAN = 6.7
    gia = [10, 10.7, 10.7, 10.7, 10.7, 10.7]
    df = _df(gia, mo=[10, 10.7, 10.7, 10.7, 10.7, 10.7], thap=[10, 10.7, 10.7, 10.7, 10.7, 10.7])
    assert not tk._mo_phong(df, 3).hop_le.iloc[0]


def test_ev_tru_phi_va_truot_gia(gia_ngay):
    s = tk._mo_phong(gia_ngay, 20)
    k = tk._tong_hop(s, kieu="all", n=20, tong=len(gia_ngay), ci=False)
    tho = s.r_exit[s.hop_le].mean()
    assert k["ev"] == pytest.approx(tho - tk._chi_phi())


def test_so_mau_hieu_dung_nho_hon_nhieu_so_mau(gia_ngay):
    s = tk._mo_phong(gia_ngay, 63, tren=15, duoi=-7)
    k = tk._tong_hop(s, n=63, tong=len(gia_ngay))
    assert k["n_hieu_dung"] < k["so_mau"] / 3
    lo, hi = k["ci_ev"]
    assert lo <= k["ev"] <= hi


def test_walk_forward_thien_lech_khong_am(gia_ngay):
    ht = gia_ngay.close.iloc[-1]
    wf = tk.kiem_dinh_walk_forward(gia_ngay, ht, [ht * 1.05, ht * 1.1, ht * 1.2], ht * 0.93, 63)
    assert wf is not None and wf["lech"] >= 0 and len(wf["bang"]) >= 2


def test_gop_nganh_tang_mau_hieu_dung(gia_ngay):
    from tests.conftest import tao_gia
    ht = gia_ngay.close.iloc[-1]
    rieng = tk._tong_hop(tk._mo_phong(gia_ngay, 63, tren=15, duoi=-7, giua=7), n=63, tong=len(gia_ngay))
    gop, ct = tk.mo_phong_gop_nganh({"A": tao_gia(seed=21), "B": tao_gia(seed=22)}, gia_ngay, ht,
                                    ht * 1.15, ht * 0.93, ht * 1.07, 63)
    assert gop["n_hieu_dung"] > rieng["n_hieu_dung"] * 2 and len(ct) == 3
