# -*- coding: utf-8 -*-
"""Kiểm thử các cải tiến: nhật ký khuyến nghị, EV theo tín hiệu, lọc cơ bản, cách thoát lệnh, backtest point-in-time."""
import os

import numpy as np
import pandas as pd
import pytest

from tests.conftest import tao_gia
from ptcp import cau_hinh as cfg
from ptcp import nhat_ky as N
from ptcp.chi_bao import tinh_chi_bao
from ptcp.du_lieu import gop_tuan


def _gia(c, o=None, h=None, l=None, bat_dau="2026-09-01"):
    c = np.asarray(c, float)
    o = c if o is None else np.asarray(o, float)
    h = np.maximum(o, c) if h is None else np.asarray(h, float)
    l = np.minimum(o, c) if l is None else np.asarray(l, float)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1e6},
                        index=pd.bdate_range(bat_dau, periods=len(c)))


# ------------------------------------------------------------------ 1. nhật ký & chấm điểm
def test_cham_muc_tieu_cat_lo_t2_khoa_tran():
    kq = N.cham_lenh_mua(_gia([100, 101, 103, 106, 111, 112]), "2026-09-01", 100, 95, 110, 63, vao_mo_cua=False)
    assert kq["ket_qua"] == N.DUNG and kq["gia_ket_thuc"] == 111           # gap qua mục tiêu → giá mở cửa
    kq = N.cham_lenh_mua(_gia([100, 93, 92, 92], o=[100, 99, 91, 92]), "2026-09-01", 100, 95, 110, 63, False)
    assert kq["ket_qua"] == N.SAI and "T+2" in kq["giai_thich"]
    tran = _gia([100, 107, 108], l=[100, 107, 107])
    assert N.cham_lenh_mua(tran, "2026-09-01", 100, 95, 115, 63, True)["ket_qua"] == N.BO_QUA
    assert N.cham_lenh_mua(_gia([100] + [101] * 10), "2026-09-01", 100, 95, 120, 63, False)["ket_qua"] == N.CHO


def test_dung_ngoai_dao_ket_qua_va_ban():
    dn = _gia([100, 100, 104, 108, 112])
    r = pd.Series({"loai": "PTCP", "nhom": "ĐỨNG NGOÀI", "ngay": "2026-09-01", "gia": 100, "cat_lo": 95,
                   "muc_tieu": 110, "ky_han": 63, "san": "HOSE"})
    assert N.cham_dong(r, dn)["ket_qua"] == N.SAI                          # bỏ lỡ
    assert N.cham_dong(r.replace("ĐỨNG NGOÀI", "MUA"), dn)["ket_qua"] == N.DUNG
    assert N.cham_ban(_gia([100] + [95] * 25), "2026-09-01", 100, 20)["ket_qua"] == N.DUNG


def test_ghi_khi_doi_khuyen_nghi_va_cham_lai():
    df = tao_gia(n=300, seed=1)
    ngay_cu = df.index[-80]
    assert N.ghi_khuyen_nghi("ABC", ngay_cu, df.close[ngay_cu], "MUA TỪNG PHẦN", df.close[ngay_cu] * 0.93,
                             df.close[ngay_cu] * 1.08, 63)
    assert not N.ghi_khuyen_nghi("ABC", df.index[-70], 1, "MUA TỪNG PHẦN", 0.9, 1.1, 63)   # không đổi → không ghi
    kq = N.ghi_va_cham_ma("ABC", df, "CHƯA MUA", df.close.iloc[-1], df.close.iloc[-1] * 0.93, df.close.iloc[-1] * 1.1, 63)
    assert kq["moi"] and len(kq["bang"]) == 2
    assert kq["bang"]["ket_qua"].iloc[0] in (N.DUNG, N.SAI, N.CHO, N.BO_QUA)
    assert os.path.exists(cfg.FILE_NHAT_KY) and len(N.thong_ke(kq["bang"]))


def test_duong_dan_tu_chon_drive(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "FILE_NHAT_KY", None)
    monkeypatch.setattr(N, "THU_MUC_DRIVE", str(tmp_path))
    assert N.duong_dan() == os.path.join(str(tmp_path), "ptcp", "nhat_ky_ptcp.csv")
    monkeypatch.setattr(N, "THU_MUC_DRIVE", str(tmp_path / "khong_co"))
    assert N.duong_dan() == "nhat_ky_ptcp.csv"


# ------------------------------------------------------------------ 3. EV theo trạng thái tín hiệu
def test_trang_thai_tuong_tu_co_dieu_kien_tin_hieu():
    from ptcp.kich_ban import mat_na_tin_hieu, trang_thai_tuong_tu
    df = tao_gia()
    d, w = tinh_chi_bao(df), tinh_chi_bao(gop_tuan(df))
    m = mat_na_tin_hieu(d, w)
    assert m.dtype == bool and 0 < m.mean() < 0.6
    mask, mo_ta, co = trang_thai_tuong_tu(d, w)
    assert "tín hiệu vào lệnh" in mo_ta and isinstance(co, bool)


# ------------------------------------------------------------------ 7. lọc cơ bản
def test_loc_co_ban_ha_khuyen_nghi():
    from ptcp.quyet_dinh import danh_gia_co_ban, quyet_dinh_cuoi
    tg = {"tuan_ok": True, "tuan_rat_tot": True, "ngay_ok": True, "gio_ok": True, "diem_trong_so": 3}
    kb, qr, dx, st = {"ev_qd": 3.0}, {"rr": 3.0, "phong_thu": False, "gia_mua_rr2": 10}, {"chon": 12}, \
        {"gia": 9.0, "pct": -10.0}
    assert quyet_dinh_cuoi(tg, kb, qr, dx, 10, st)["khuyen_nghi"].startswith("MUA")
    lo = danh_gia_co_ban({"LNST 4 quý (tỷ đồng)": -50.0})
    assert quyet_dinh_cuoi(tg, kb, qr, dx, 10, st, cbl=lo)["khuyen_nghi"] == "THEO DÕI"
    giam = danh_gia_co_ban({"LNST 4 quý (tỷ đồng)": 50.0, "Tăng trưởng LNST 4Q %": -45.0})
    assert giam["ha"] == "THEO DÕI"
    roe = danh_gia_co_ban({"LNST 4 quý (tỷ đồng)": 50.0, "ROE %": 2.0})
    assert quyet_dinh_cuoi(tg, kb, qr, dx, 10, st, cbl=roe)["khuyen_nghi"] == "MUA TỪNG PHẦN"
    assert danh_gia_co_ban({})["ha"] is None                                # thiếu dữ liệu → không chặn


def test_tang_truong_lnst_8_quy(monkeypatch):
    from ptcp import du_lieu_co_ban as cb
    ds = [(f"Q{q}/{y}", v) for (y, q), v in zip([(2026, 2), (2026, 1), (2025, 4), (2025, 3), (2025, 2), (2025, 1),
                                                  (2024, 4), (2024, 3)], [10, 10, 10, 10, 20, 20, 20, 20])]
    monkeypatch.setattr(cb, "NGUON_CO_BAN", [("A", lambda s: {"P/B": 1.0, "ky": ""})])
    monkeypatch.setattr(cb, "NGUON_LNST", [("X", lambda s: ds)])
    kq = cb.lay_chi_so_co_ban("ABC", gia=10, so_cp_luu_hanh=1e8)
    assert kq["Tăng trưởng LNST 4Q %"] == pytest.approx(-50.0)


# ------------------------------------------------------------------ 8. cách thoát lệnh
def test_backtest_cac_cach_thoat():
    from ptcp.bo_sung import backtest_quy_tac
    df = tao_gia(seed=5)
    d, w = tinh_chi_bao(df), tinh_chi_bao(gop_tuan(df))
    kq = {k: backtest_quy_tac(d, w, 63, thoat=k) for k in ("co_dinh", "dong", "tung_phan")}
    assert kq["co_dinh"]["so_lenh"] > 0
    goc = ("cắt lỗ", "cắt lỗ động", "chốt lời", "hết hạn", "chốt 1 phần + hết hạn")   # + hậu tố gia hạn / trễ T+2
    assert all(any(str(x).startswith(g) for g in goc) for b in kq.values() for x in b["bang"]["Lý do thoát"])
    assert not (kq["dong"]["bang"]["Lý do thoát"] == "chốt lời").any()       # cắt lỗ động không chốt cứng


# ------------------------------------------------------------------ 2 & 5. backtest point-in-time + độ nhạy
def test_backtest_khuyen_nghi_point_in_time(tmp_path):
    from ptcp import backtest_khuyen_nghi
    os.chdir(tmp_path)
    df, vni = tao_gia(n=800, seed=5), tao_gia(n=800, seed=9, gia_dau=1000, sigma=0.01)
    kq = backtest_khuyen_nghi("TEST", df_ngay=df, vni=vni, buoc=40, in_ket_qua=False)
    b = kq["bang"]
    assert len(b) >= 5 and set(b["nhom"]) <= {"MUA", "CHỜ", "ĐỨNG NGOÀI"}
    assert (pd.to_datetime(b["ngay"]) <= df.index[-2]).all()
    dn = kq["do_nhay"]
    assert len(dn) == 24 and (dn["Đang dùng"] == "◄").sum() == 1
    assert os.path.exists(kq["file_excel"])
