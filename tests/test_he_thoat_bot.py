# -*- coding: utf-8 -*-
"""Kiểm thử cảnh báo BÁN theo hệ thoát mới + bản tin chiến lược CL1/CL2 (không cần mạng)."""
import json
import os
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytest.importorskip("ptcp.chien_luoc", reason="ptcp trong danh-muc chưa cập nhật (thiếu chien_luoc.py)")
if not hasattr(pytest.importorskip("ptcp.he_thoat"), "theo_doi_vi_the"):
    pytest.skip("ptcp trong danh-muc chưa cập nhật he_thoat.py (thiếu theo_doi_vi_the)", allow_module_level=True)
import chay  # noqa: E402
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import chien_luoc_bot, vi_the  # noqa: E402


def _gia(r, g0=50.0, end="2026-10-02", seed=0):
    """Giá ngày từ chuỗi lợi suất r (nến hẹp quanh đóng cửa)."""
    r = np.asarray(r, float)
    c = g0 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]]
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + rng.uniform(0, .004, len(c))),
                         "low": np.minimum(o, c) * (1 - rng.uniform(0, .004, len(c))), "close": c,
                         "volume": 1e6}, index=pd.bdate_range(end=end, periods=len(c)))


def _nen(n_truoc=300, sau=(), seed=1):
    rng = np.random.default_rng(seed)
    return _gia(np.r_[0.0003 + 0.012 * rng.standard_normal(n_truoc), np.asarray(sau, float)], seed=seed)


def _vt(dn, i_mua, cat_lo_goc=None, cat_lo_dat=None):
    gv = float(dn.close.iloc[i_mua])
    return {"ma": "AAA", "so_cp": 100, "gia_von": gv, "cat_lo": cat_lo_dat or cat_lo_goc, "cat_lo_goc": cat_lo_goc,
            "muc_tieu": gv * 1.1, "ngay_mua": f"{dn.index[i_mua]:%d/%m/%Y}"}


BAY_GIO = pd.Timestamp("2026-10-02 15:30")


def test_cat_lo_he_thoat():
    dn = _nen(sau=[0.0] * 5 + [-0.03] * 4)
    vt = _vt(dn, -10)
    kb = vi_the.danh_gia_ban(vt, {"gia": float(dn.close.iloc[-1])}, dn, BAY_GIO)
    assert kb["he_thoat"] and kb["muc"] == "CAT_LO" and kb["tang"] == 0
    assert kb["cat_lo"] < vt["gia_von"] and kb["R"] > 0


def test_doi_cat_lo_khi_qua_1R_va_khong_ha_cat_lo_da_dat():
    dn = _nen(sau=[0.0] * 3 + [0.012] * 25)
    vt = _vt(dn, -28, cat_lo_goc=None)
    gv = vt["gia_von"]
    vt["cat_lo"] = gv * 0.93
    kb = vi_the.danh_gia_ban(vt, {"gia": float(dn.close.iloc[-1])}, dn, BAY_GIO)
    assert kb["muc"] == "DOI_CAT_LO" and kb["tang"] >= 1
    assert kb["cat_lo_he_thong"] >= gv                         # ≥ 1R → không dưới hoà vốn
    vt["cat_lo"] = kb["cat_lo_he_thong"] * 1.01                # đã đặt cao hơn hệ thống → giữ mức đã đặt, không báo dời
    kb2 = vi_the.danh_gia_ban(vt, {"gia": float(dn.close.iloc[-1])}, dn, BAY_GIO)
    assert kb2["muc"] == "GIU" and kb2["cat_lo"] == pytest.approx(vt["cat_lo"])


def test_ban_tuan_khi_gay_ma10_tuan():
    dn = _nen(sau=[0.0] * 2 + [0.02] * 60 + [-0.012] * 25)
    vt = _vt(dn, -87, cat_lo_goc=None)
    gia = float(dn.close.iloc[-1])
    kb = vi_the.danh_gia_ban(dict(vt, cat_lo=None), {"gia": gia}, dn, BAY_GIO)
    assert kb["tang"] == 2
    assert kb["muc"] in ("BAN_TUAN", "CAT_LO")
    ht = vi_the._he_thoat(vt, dn, BAY_GIO)
    assert ht["ban_tuan"]


def test_het_han_63_phien():
    dn = _nen(sau=[0.0005, -0.0005] * 40)
    vt = _vt(dn, -80)
    kb = vi_the.danh_gia_ban(dict(vt, cat_lo=vt["gia_von"] * 0.8), {"gia": float(dn.close.iloc[-1])}, dn, BAY_GIO)
    assert kb["muc"] == "HET_HAN"


def test_tin_ban_va_tong_ket_co_he_thoat():
    dn = _nen(sau=[0.0] * 5 + [-0.03] * 4)
    vt = _vt(dn, -10)
    kq = {"ma": "AAA", "gia": float(dn.close.iloc[-1])}
    kb = vi_the.danh_gia_ban(vt, kq, dn, BAY_GIO)
    tin = vi_the.tin_ban(vt, kb, kq, BAY_GIO)
    assert "CẮT LỖ – AAA" in tin
    assert "AAA" in vi_the.dong_tong_ket(vt, kb)


def test_khong_dung_nen_dang_chay():
    dn = _nen(sau=[0.0] * 10)
    trong = vi_the._phien_da_dong(dn, pd.Timestamp(f"{dn.index[-1]:%Y-%m-%d} 10:30"))
    assert len(trong) == len(dn) - 1
    assert len(vi_the._phien_da_dong(dn, pd.Timestamp(f"{dn.index[-1]:%Y-%m-%d} 15:20"))) == len(dn)


def test_tat_he_thoat_ve_cach_cu():
    dn = _nen(sau=[0.0] * 10)
    vt = _vt(dn, -5)
    with mock.patch.object(C, "DUNG_HE_THOAT", False):
        kb = vi_the.danh_gia_ban(vt, {"gia": vt["muc_tieu"] + 1, "khung": []}, dn, BAY_GIO)
    assert kb["muc"] == "CHOT_LOI" and not kb["he_thoat"]
    kb = vi_the.danh_gia_ban(dict(vt, gia_von=None), {"gia": 1.0, "khung": []}, dn, BAY_GIO)   # thiếu giá vốn
    assert not kb["he_thoat"]


# ------------------------------------------------------------------ bản tin chiến lược
def _gia_dai(seed, trend=0.0004, n=1500, end="2026-10-02"):
    rng = np.random.default_rng(seed)
    return _gia(trend + 0.018 * rng.standard_normal(n), g0=20 + seed % 30, end=end, seed=seed)


def _tai(ma, tu, chi_so=False):
    return _gia_dai(7 if chi_so else sum(map(ord, ma)), 0.0003 if chi_so else 0.0005)


DS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]


def test_chay_chien_luoc_va_ban_tin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(C, "NGAY_BAT_DAU_CL", "2021-01-01")
    ra, loi = chien_luoc_bot.chay_chien_luoc(_tai, BAY_GIO, ds_ma=DS)
    assert loi is None and ra["cl"] in (1, 2) and ra["so_ma"] == 6
    assert set(ra["diem_mua"]) == {"A0", "B"} and len(ra["diem_mua"]["A0"]) == 6
    pb = ra["phan_bo"]
    if len(pb):
        assert pb["Tỷ trọng mục tiêu % vốn"].sum() == pytest.approx(100)
    tin = chien_luoc_bot.ban_tin(ra, BAY_GIO)
    for chu in ("CHIẾN LƯỢC THEO THỊ TRƯỜNG", "① Thị trường:", "② Đang áp dụng: CL", "Chia vốn:", "Điều kiện đổi:",
                "③ Hành động phiên", "không phải danh mục thật"):
        assert chu in tin
    so_bo = tin.count("✘ bỏ nếu")
    assert tin.count("✔") + tin.count("✘") - so_bo == ra["doc"]["so_chi_bao"]
    hd = ra["hanh_dong"]
    for _, r in hd[hd["Nhóm"].isin(["MUA_MOI", "VAO_NHU_MOI", "VAO_NUA"])].iterrows():
        assert r["Cắt lỗ"] < r["Vùng mua từ"] <= r["Vùng mua đến"]
        assert f"MUA {chien_luoc_bot._f(r['Vùng mua từ'])}–{chien_luoc_bot._f(r['Vùng mua đến'])}" in tin


def test_thieu_du_lieu_va_dung_lai_du_lieu_san(monkeypatch):
    monkeypatch.setattr(C, "NGAY_BAT_DAU_CL", "2021-01-01")
    ra, loi = chien_luoc_bot.chay_chien_luoc(lambda ma, tu, chi_so=False: None, BAY_GIO, ds_ma=DS)
    assert ra is None and "VN-Index" in loi
    goi = []

    def tai(ma, tu, chi_so=False):
        goi.append(ma)
        return _tai(ma, tu, chi_so)
    san = {m: _tai(m, None) for m in DS}
    ra, loi = chien_luoc_bot.chay_chien_luoc(tai, BAY_GIO, du_lieu_san=san, vni=_tai("VNINDEX", None, True), ds_ma=DS)
    assert loi is None and goi == []                                  # đủ dài → không tải lại
    ngan = {m: d.iloc[-300:] for m, d in san.items()}                  # quá ngắn → tải lại
    chien_luoc_bot.chay_chien_luoc(tai, BAY_GIO, du_lieu_san=ngan, vni=_tai("VNINDEX", None, True), ds_ma=DS)
    assert sorted(goi) == sorted(DS)


def _ra_gia(cl, ngay="2026-10-02", lich=None):
    return {"cl": cl, "doc": {"diem": 5 if cl == 2 else 2, "ngay": pd.Timestamp(ngay)}, "lich": lich}


def test_kiem_tra_doi(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert chien_luoc_bot.kiem_tra_doi(_ra_gia(1), BAY_GIO) == (False, None)       # lần đầu, không đổi ở cuối tháng
    assert chien_luoc_bot.kiem_tra_doi(_ra_gia(1), BAY_GIO) == (False, 1)
    assert chien_luoc_bot.kiem_tra_doi(_ra_gia(2), BAY_GIO) == (True, 1)
    assert json.load(open(C.FILE_TRANG_THAI_CL, encoding="utf-8"))["cl"] == 2
    os.remove(C.FILE_TRANG_THAI_CL)                                                 # mất file trạng thái
    lich = pd.DataFrame([{"Phiên quyết định": pd.Timestamp("2026-09-30"), "Điểm": 6, "CL trước": 1,
                          "CL tháng sau": 2, "Đổi": True}])
    assert chien_luoc_bot.kiem_tra_doi(_ra_gia(2, "2026-09-30", lich), BAY_GIO) == (True, 1)


def test_tin_doi():
    from ptcp.chien_luoc import TEN_CL, TY_TRONG
    ra = {"cl": 2, "doc": {"diem": 6, "so_chi_bao": 8, "ngay": pd.Timestamp("2026-09-30")}, "ten_cl": TEN_CL,
          "ty_trong": TY_TRONG[2], "ty_trong_cl": TY_TRONG, "nguong": (5, 2)}
    t = chien_luoc_bot.tin_doi(ra, 1)
    assert "ĐỔI CHIẾN LƯỢC: CL1 → CL2" in t and "VN-Index 30%" in t and "trước: A0 50%" in t


def test_nhom_hanh_dong_cho_nguoi_chua_mua():
    from ptcp.chien_luoc import hanh_dong
    a0 = pd.DataFrame([
        {"Mã": "MOI", "Trạng thái": "MUA phiên tới (giá mở cửa) – Tín hiệu", "Giá đóng cửa": 100, "Cắt lỗ dự kiến": 94},
        {"Mã": "SOM", "Trạng thái": "ĐANG GIỮ", "Giá đóng cửa": 100, "Cắt lỗ phiên tới": 96, "Lãi (R)": 0.4},
        {"Mã": "VUA", "Trạng thái": "ĐANG GIỮ", "Giá đóng cửa": 100, "Cắt lỗ phiên tới": 95, "Lãi (R)": 1.5},
        {"Mã": "XA", "Trạng thái": "ĐANG GIỮ", "Giá đóng cửa": 100, "Cắt lỗ phiên tới": 95, "Lãi (R)": 3.0},
        {"Mã": "RONG", "Trạng thái": "ĐANG GIỮ", "Giá đóng cửa": 100, "Cắt lỗ phiên tới": 88, "Lãi (R)": 0.2},
        {"Mã": "BAN", "Trạng thái": "ĐANG GIỮ → BÁN phiên tới (đóng cửa tuần < MA10 tuần)", "Giá đóng cửa": 100,
         "Cắt lỗ phiên tới": 90, "Lãi (R)": 4.0},
        {"Mã": "CHO", "Trạng thái": "CHỜ tín hiệu", "Giá đóng cửa": 100}])
    b = pd.DataFrame([{"Mã": "VUA", "Trạng thái": "MUA phiên tới (giá mở cửa) – Tín hiệu", "Giá đóng cửa": 100,
                       "Cắt lỗ dự kiến": 94}])
    hd = hanh_dong({"A0": a0, "B": b}, {"A0": 0.7, "B": 0.0, "VNI": 0.3})       # CL2: B không tính
    nhom = dict(zip(hd["Mã"], hd["Nhóm"]))
    assert nhom == {"MOI": "MUA_MOI", "SOM": "VAO_NHU_MOI", "VUA": "VAO_NUA", "XA": "CHO", "RONG": "CHO", "BAN": "BAN"}
    r = hd.set_index("Mã")
    assert r.loc["SOM", "Mua tối đa"] == pytest.approx(min(103, 96 / 0.93))
    assert r.loc["XA", "Chờ giá"] == pytest.approx(95 / 0.95) and r.loc["VUA", "Khối lượng"] == "½"
    hd1 = hanh_dong({"A0": a0, "B": b}, {"A0": 0.5, "B": 0.5, "VNI": 0})        # CL1: B mua mới thắng ½ của A0
    r1 = hd1.set_index("Mã")
    assert r1.loc["VUA", "Nhóm"] == "MUA_MOI" and r1.loc["VUA", "Thành phần"] == "A0+B"
