# -*- coding: utf-8 -*-
"""Kiểm thử nhật ký & chấm điểm tín hiệu (không cần mạng)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import nhat_ky as N  # noqa: E402


def _gia(c, o=None, h=None, l=None, bat_dau="2026-09-01"):
    c = np.asarray(c, float)
    o = c if o is None else np.asarray(o, float)
    h = np.maximum(o, c) if h is None else np.asarray(h, float)
    l = np.minimum(o, c) if l is None else np.asarray(l, float)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1e6},
                        index=pd.bdate_range(bat_dau, periods=len(c)))


@pytest.fixture(autouse=True)
def _thu_muc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_mua_ngay_cham_muc_tieu():
    dn = _gia([100, 101, 103, 106, 111, 112])
    kq = N.cham_lenh_mua(dn, "2026-09-01", 100, 95, 110, 63, vao_mo_cua=False)
    assert kq["ket_qua"] == N.DUNG and kq["giai_thich"] == "chạm mục tiêu"
    assert kq["gia_ket_thuc"] == 111                                  # mở cửa gap qua mục tiêu → bán giá mở cửa
    assert kq["ket_qua_pct"] == pytest.approx(11 - N.chi_phi())


def test_cat_lo_ban_tre_do_t2():
    # phiên 1 sau mua đã thủng cắt lỗ nhưng chỉ bán được từ T+2 → bán giá mở cửa phiên 2
    dn = _gia([100, 93, 92, 92], o=[100, 99, 91, 92])
    kq = N.cham_lenh_mua(dn, "2026-09-01", 100, 95, 110, 63, vao_mo_cua=False)
    assert kq["ket_qua"] == N.SAI and "T+2" in kq["giai_thich"]
    assert kq["gia_ket_thuc"] == 91


def test_het_han_va_dang_cho():
    dn = _gia([100] + [101] * 10)
    assert N.cham_lenh_mua(dn, "2026-09-01", 100, 95, 120, 5, False)["ket_qua"] == N.DUNG    # +1% > phí 0,6%
    dn2 = _gia([100] + [100.3] * 10)
    assert N.cham_lenh_mua(dn2, "2026-09-01", 100, 95, 120, 5, False)["ket_qua"] == N.SAI    # lãi < phí
    assert N.cham_lenh_mua(dn, "2026-09-01", 100, 95, 120, 63, False)["ket_qua"] == N.CHO


def test_ptcp_vao_mo_cua_va_khoa_tran():
    # phiên sau tín hiệu khoá trần cả phiên → không mua được
    dn = _gia([100, 107, 108], o=[100, 107, 108], l=[100, 107, 107])
    assert N.cham_lenh_mua(dn, "2026-09-01", 100, 95, 115, 63, True)["ket_qua"] == N.BO_QUA


def test_dung_ngoai_dao_ket_qua(tmp_path):
    dn = _gia([100, 100, 104, 108, 112])
    r = pd.Series({"loai": "PTCP", "nhom": "ĐỨNG NGOÀI", "ngay": "2026-09-01", "gia": 100, "cat_lo": 95,
                   "muc_tieu": 110, "ky_han": 63})
    kq = N.cham_dong(r, dn)
    assert kq["ket_qua"] == N.SAI and kq["giai_thich"].startswith("bỏ lỡ")
    r["nhom"] = "MUA"
    assert N.cham_dong(r, dn)["ket_qua"] == N.DUNG


def test_ban():
    dn = _gia([100] + [95] * 25)
    assert N.cham_ban(dn, "2026-09-01", 100, 20)["ket_qua"] == N.DUNG
    dn = _gia([100] + [105] * 25)
    assert N.cham_ban(dn, "2026-09-01", 100, 20)["ket_qua"] == N.SAI
    assert N.cham_ban(dn, "2026-09-01", 100, 40)["ket_qua"] == N.CHO


def test_ghi_cap_nhat_thong_ke_va_rieng_tu():
    kq = {"ma": "GMD", "gia": 100.0, "cat_lo": 95.0, "muc_tieu": 110.0,
          "ptcp": {"khuyen_nghi": "MUA TỪNG PHẦN", "ngay_du_lieu": "2026-09-01", "gia": 100.0, "n_phien": 63}}
    assert N.ghi_mua_ngay(kq, "2026-09-01 10:30")
    assert not N.ghi_mua_ngay(kq, "2026-09-01 10:30")                  # trùng id → không ghi
    assert N.ghi_ptcp(kq, "2026-09-01 15:20")
    kq["ptcp"]["ngay_du_lieu"] = "2026-09-02"
    assert not N.ghi_ptcp(kq, "2026-09-02 15:20")                     # khuyến nghị không đổi → không ghi
    assert N.ghi_ban({"ma": "XYZ", "gia": 50.0}, {"muc": "CAT_LO"}, "2026-09-03 10:00")
    assert not N.ghi_ban({"ma": "XYZ", "gia": 50.0}, {"muc": "DOI_CAT_LO"}, "2026-09-03 10:00")
    assert N.ghi_ban({"ma": "XYZ", "gia": 50.0}, {"muc": "BAN_TUAN"}, "2026-09-04 10:00")   # mức mới của hệ thoát
    assert "XYZ" not in open(N.FILE_CONG_KHAI, encoding="utf-8").read()   # cảnh báo bán không lên file công khai
    assert "XYZ" in open(N.FILE_RIENG, encoding="utf-8").read()
    gia = {"GMD": _gia([100, 101, 104, 108, 111, 112]), "XYZ": _gia([50] + [48] * 25)}
    assert N.cap_nhat(gia.get) == 4
    tk = N.thong_ke(N.doc(N.FILE_CONG_KHAI))
    assert set(tk["Nhóm"]) == {"MUA NGAY", "ptcp MUA"} and (tk["Đúng"] == 1).all()
    assert any("đúng 1/1" in d for d in N.dong_tong_ket())
    assert os.path.exists(N.xuat_excel(rieng=True))


def test_nhap_lich_su_cu():
    pd.DataFrame([{"thoi_diem": "2026-09-01 10:30", "ma": "MWG", "gia": 60, "cat_lo": 57, "muc_tieu": 66, "rr": 2,
                   "kich_hoat": "x"}]).to_csv("lich_su_tin_hieu.csv", index=False)
    assert N.nhap_lich_su_cu() == 1
    assert N.nhap_lich_su_cu() == 0                                   # chỉ nhập lần đầu
