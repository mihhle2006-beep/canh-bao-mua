# -*- coding: utf-8 -*-
"""Giao dịch giả lập & trang tổng hợp – không cần mạng, không cần ptcp (hệ thoát được giả lập)."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import giao_dich_ao as GA  # noqa: E402
from canh_bao import trang_tong_hop as TH  # noqa: E402

NGAY = pd.bdate_range("2026-10-01", periods=8)


def _df(o, h, l, c):
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1e6}, index=NGAY[:len(o)])


def _giu(*_):
    return {"muc": "GIU"}


@pytest.fixture
def tt():
    return GA.moi(NGAY[0], von_trieu=1000)                           # 1 tỷ = 1.000.000 nghìn đồng


def test_mua_gia_mo_cua_trong_vung(tt):
    df = _df([10, 10.2, 10.3], [10.1, 10.5, 10.6], [9.9, 10.0, 10.1], [10, 10.4, 10.5])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.5,
                          "hieu_luc": NGAY[1]}], None)
    sk, dong, von = GA.xu_ly_phien(tt, NGAY[1], {"AAA": df}, _giu)
    v = tt["vi_the"]["AAA"]
    assert v["gia_mua"] == 10.2 and v["so_cp"] % 100 == 0
    # rủi ro 1% NAV ÷ (10,2 − 9,5) = 14.285 CP → trần 20% NAV = 19.607 CP → 14.200 CP
    assert v["so_cp"] == 14200
    assert tt["lenh_cho"] == [] and not dong
    assert tt["tien"] == pytest.approx(1_000_000 - 14200 * 10.2 * (1 + C.PHI_MUA_AO_PCT / 100))  # trừ phí mua
    assert von["nav"] == pytest.approx(tt["tien"] + 14200 * 10.4, abs=0.1)                      # định giá đóng cửa


def test_bo_khi_mo_cua_vuot_vung_va_huy_lenh_qua_han(tt):
    df = _df([10, 10.6, 10.7], [10.1, 10.8, 10.8], [9.9, 10.5, 10.6], [10, 10.7, 10.7])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.5, "hieu_luc": NGAY[1]}],
                    None)
    sk, _, _ = GA.xu_ly_phien(tt, NGAY[1], {"AAA": df}, _giu)
    assert "AAA" not in tt["vi_the"] and any("BỎ AAA" in x for x in sk)


def test_khoa_tran_khong_mua_duoc(tt):
    df = _df([10, 10.7], [10.1, 10.7], [9.9, 10.7], [10, 10.7])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 11, "cl": 9.5, "hieu_luc": NGAY[1]}],
                    None)
    sk, _, _ = GA.xu_ly_phien(tt, NGAY[1], {"AAA": df}, _giu)
    assert "AAA" not in tt["vi_the"] and any("khoá trần" in x for x in sk)


def test_vao_nua_mua_nua_khoi_luong(tt):
    df = _df([10, 10.0], [10.1, 10.2], [9.9, 9.9], [10, 10.1])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "VAO_NUA", "tu": 9.8, "den": 10.3, "cl": 9.0, "hieu_luc": NGAY[1]}],
                    None)
    GA.xu_ly_phien(tt, NGAY[1], {"AAA": df}, _giu)
    assert tt["vi_the"]["AAA"]["so_cp"] == 5000                       # 10.000 CP × ½


def test_cat_lo_ton_trong_t2_va_an_gap(tt):
    # mua phiên 1 ở 10; phiên 2 thủng cắt lỗ nhưng chưa đủ T+2; phiên 3 mở cửa gap dưới cắt lỗ → bán giá mở cửa
    df = _df([10, 10, 9.6, 9.2], [10.1, 10.1, 9.7, 9.3], [9.9, 9.9, 9.3, 9.0], [10, 10, 9.4, 9.1])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.5, "hieu_luc": NGAY[1]}],
                    None)
    for s in NGAY[1:3]:
        GA.xu_ly_phien(tt, s, {"AAA": df}, _giu)
    assert "AAA" in tt["vi_the"]                                      # phiên 2: T+1 – chưa bán được
    _, dong, _ = GA.xu_ly_phien(tt, NGAY[3], {"AAA": df}, _giu)
    assert "AAA" not in tt["vi_the"] and dong[0]["gia_ban"] == 9.2 and dong[0]["lai_pct"] < -8


def test_he_thoat_doi_cat_lo_len_va_ban_mo_cua_phien_sau(tt):
    df = _df([10, 10, 10.5, 11, 11.5, 11.2], [10.1, 10.6, 11, 11.6, 11.6, 11.3], [9.9, 9.9, 10.4, 10.9, 11.1, 11.0],
             [10, 10.5, 10.9, 11.5, 11.2, 11.1])
    GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.5, "hieu_luc": NGAY[1]}],
                    None)
    goi = []

    def he_thoat(vt, kq, dn, bay_gio):
        goi.append((vt["gia_von"], dn.index[-1]))
        if dn.index[-1] == NGAY[4]:
            return {"muc": "BAN_TUAN", "cat_lo": 10.6, "tang": 2}
        return {"muc": "DOI_CAT_LO", "cat_lo": 10.2, "tang": 1}

    for s in NGAY[1:5]:
        GA.xu_ly_phien(tt, s, {"AAA": df}, he_thoat)
    assert tt["vi_the"]["AAA"]["cat_lo"] == 10.6 and tt["ban_cho"]["AAA"] == "gãy MA10 tuần"
    assert goi[0] == (10, NGAY[1])                                    # hệ thoát chỉ thấy phiên đã đóng tới hôm đó
    _, dong, _ = GA.xu_ly_phien(tt, NGAY[5], {"AAA": df}, he_thoat)
    assert dong[0]["gia_ban"] == 11.2 and dong[0]["ly_do"] == "gãy MA10 tuần" and dong[0]["lai_pct"] > 10


def test_khong_mua_trung_ma_dang_giu(tt):
    tt["vi_the"]["AAA"] = {"ngay_mua": "2026-10-01", "gia_mua": 10, "so_cp": 100, "cat_lo_goc": 9, "cat_lo": 9}
    n = GA.dat_lenh_cho(tt, [{"ma": "AAA", "nhom": "MUA_MOI"}, {"ma": "BBB", "nhom": "CHO"},
                             {"ma": "CCC", "nhom": "VAO_NHU_MOI", "tu": 1, "den": 2, "cl": 0.5}], NGAY[2])
    assert n == 1 and tt["lenh_cho"][0]["ma"] == "CCC" and tt["lenh_cho"][0]["hieu_luc"] == "2026-10-05"


def _ra(n):
    vni = _df(*[[1000 + i for i in range(8)]] * 4)
    aaa = _df([10] * 8, [10.2] * 8, [9.9] * 8, [10 + 0.1 * i for i in range(8)])
    return {"vni_df": vni.iloc[:n], "gia_ngay": {"AAA": aaa.iloc[:n]}, "doc": {"ngay": NGAY[n - 1]}}


def test_chay_qua_nhieu_lan_khong_xu_ly_lai(tmp_path):
    p = {k: str(tmp_path / f) for k, f in (("path", "a.json"), ("path_lenh", "l.csv"), ("path_von", "v.csv"))}
    kn = [{"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.5, "den": 10.5, "cl": 9.0, "hieu_luc": None}]
    tt, sk = GA.chay(_ra(2), kn, "2026-10-02 15:20", _giu, **p)
    assert tt["bat_dau"] == "2026-10-02" and not tt["vi_the"] and tt["lenh_cho"][0]["hieu_luc"] == "2026-10-05"
    tt, sk = GA.chay(_ra(3), kn, "2026-10-05 15:20", _giu, **p)
    assert "AAA" in tt["vi_the"] and len(sk) == 1
    tt, sk = GA.chay(_ra(3), kn, "2026-10-05 15:40", _giu, **p)      # chạy lại cùng ngày: không mua thêm
    assert sk == [] and len(tt["vi_the"]) == 1
    tt, _ = GA.chay(_ra(5), [], "2026-10-07 15:20", _giu, **p)         # bỏ lỡ 1 ngày: xử lý bù 2 phiên
    von = pd.read_csv(p["path_von"])
    assert list(von.ngay) == ["2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"]
    x = GA.thong_ke(tt, GA.doc_csv(p["path_lenh"], GA.COT_LENH), von)
    assert x["so_phien"] == 3 and x["vni_pct"] > 0 and x["lai_pct"] > 0
    t = GA.tin(tt, [], GA.doc_csv(p["path_lenh"], GA.COT_LENH), von)
    assert "GIAO DỊCH GIẢ LẬP" in t and f"Còn {C.SO_PHIEN_GIA_LAP_TOI_THIEU - 3} phiên" in t


# ------------------------------------------------------------------ trang tổng hợp
def test_do_chinh_xac():
    nk = pd.DataFrame({"loai": ["PTCP"] * 4 + ["MUA_NGAY"], "nhom": ["MUA", "MUA", "MUA", "ĐỨNG NGOÀI", "MUA"],
                       "ket_qua": ["ĐÚNG", "SAI", "ĐANG CHỜ", "ĐÚNG", "BỎ QUA"],
                       "ket_qua_pct": [5.0, -3.0, np.nan, -2.0, np.nan]})
    b = TH.do_chinh_xac(nk).set_index(["Loại", "Nhóm"])
    r = b.loc[("PTCP", "MUA")]
    assert (r["Tổng"], r["Đúng"], r["Sai"], r["Đang chờ"], r["Đúng %"], r["TB lãi/lỗ %"]) == (3, 1, 1, 1, 50, 1)
    assert np.isnan(b.loc[("MUA_NGAY", "MUA"), "Đúng %"])


def test_trang_cong_khai_khong_lo_danh_muc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with open(C.FILE_TRANG_THAI_CL, "w", encoding="utf-8") as f:
        json.dump({"thi_truong": {"ngay": "2026-10-07", "diem": 5, "so_chi_bao": 8, "vni": 1712.3, "cl": 2,
                                  "ten_cl": "CL2", "ty_trong": {"A0": .7, "B": 0, "VNI": .3}, "dieu_kien_doi": "",
                                  "di_ngang": {"dang": False, "bien": 15.2}, "chi_bao": [
                                      {"ten": "VNI > MA200", "dat": True, "chi_tiet": ""}]},
                   "khuyen_nghi": [{"ma": "FPT", "nhom": "MUA_MOI", "gia": 120, "tu": 118, "den": 121, "cl": 112,
                                    "mt1": 128, "mt3": 144, "ly_do": "MACD <ngày> cắt lên"}],
                   "ds_mua": {"hieu_luc": "2026-10-08"}}, f)
    tt = GA.moi(NGAY[0])
    GA.ghi(tt)
    p = TH.tao(bay_gio="2026-10-07 15:20")
    s = open(p, encoding="utf-8").read()
    assert p == C.FILE_TRANG and "FPT" in s and "1.712,30" in s and "&lt;ngày&gt;" in s
    assert "Danh mục thật" not in s
    vt = {"ma": "XYZ", "so_cp": 1000, "gia_von": 20}
    p2 = TH.tao(giu=[(vt, {"gia": 22, "lai_lo_pct": 10, "cat_lo": 19, "muc": "GIU"}, {"du": True})])
    s2 = open(p2, encoding="utf-8").read()
    assert p2 == TH.FILE_RIENG and "XYZ" in s2 and "Danh mục thật" in s2
    assert "XYZ" not in open(p, encoding="utf-8").read()


def test_luu_thi_truong(tmp_path):
    path = str(tmp_path / "cl.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"cl": 1, "ds_mua": {"ma": []}}, f)
    ra = {"doc": {"ngay": pd.Timestamp("2026-10-07"), "diem": 3, "so_chi_bao": 8, "dieu_kien_doi": "cần +2",
                  "bang": pd.DataFrame({"Chỉ báo": ["A", "B"], "Đạt": [np.True_, False], "Chi tiết": ["x", ""]})},
          "vni": np.float64(1700.5), "cl": 1, "ten_cl": {1: "CL1 an toàn", 2: "CL2"},
          "ty_trong": {"A0": .5, "B": .5, "VNI": 0}, "di_ngang": None}
    TH.luu_thi_truong(ra, "2026-10-07 15:20", [{"ma": "AAA", "nhom": "CHO", "gia": np.float64(1.5),
                                               "hieu_luc": pd.Timestamp("2026-10-08"), "khoi_luong": "bỏ"}], path)
    d = json.load(open(path, encoding="utf-8"))
    assert d["cl"] == 1 and "ds_mua" in d                              # giữ khoá cũ
    assert d["thi_truong"]["chi_bao"][0] == {"ten": "A", "dat": True, "chi_tiet": "x"}
    assert d["khuyen_nghi"] == [{"ma": "AAA", "nhom": "CHO", "gia": 1.5, "hieu_luc": "2026-10-08"}]
