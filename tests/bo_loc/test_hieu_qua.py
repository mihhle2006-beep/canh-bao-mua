# -*- coding: utf-8 -*-
"""bo_loc/hieu_qua.py – lịch sử mã MUA của bộ lọc & lãi sau N phiên so VN-Index (không mạng)."""
import pandas as pd

from bo_loc import hieu_qua as H


def test_ghi_lich_su_ghi_de_cung_phien(tmp_path):
    f = tmp_path / "ls.csv"
    assert H.ghi_lich_su({"phien": "2026-10-01", "ma": {"AAA": ["quy_b"], "BBB": ["quy_b", "xu_huong ½"]}}, f) == 3
    assert H.ghi_lich_su({"phien": "2026-10-01", "ma": {"AAA": ["quy_b"]}}, f) == 1          # chạy lại → ghi đè
    H.ghi_lich_su({"phien": "2026-10-02", "ma": {"CCC": ["xu_huong"]}}, f)
    ls = pd.read_csv(f, dtype=str)
    assert list(ls["ma"]) == ["AAA", "CCC"] and set(ls["phien"]) == {"2026-10-01", "2026-10-02"}


def test_danh_gia_va_bao_cao(tmp_path):
    i = pd.bdate_range("2026-01-01", periods=100)
    gia = {"VNINDEX": pd.Series(range(100, 200), i, dtype=float), "AAA": pd.Series([10.0] * 100, i),
           "BBB": pd.Series([10.0 * 1.01 ** k for k in range(100)], i)}
    ls = pd.DataFrame({"phien": [f"{i[0]:%Y-%m-%d}", f"{i[0]:%Y-%m-%d}", f"{i[90]:%Y-%m-%d}"], "ma": ["AAA", "BBB", "AAA"],
                       "chien_luoc": ["quy_b", "quy_b", "quy_b"]})
    kq = H.danh_gia(ls, lambda m, tu, chi_so=False: gia[m])
    assert kq.loc[0, "lãi 20p %"] == 0 and round(kq.loc[0, "vượt 20p %"], 1) == -20.0
    assert pd.isna(kq.loc[2, "lãi 20p %"])                                       # chưa đủ 20 phiên
    t = H.bao_cao(kq)
    assert "quy_b (3 lượt mã)" in t and "20 phiên (2 lượt)" in t and "50% lượt hơn VN-Index" in t
    assert H.can_gui("2026-11-03", tmp_path / "tt.json")
    H.da_gui("2026-11-03", tmp_path / "tt.json")
    assert not H.can_gui("2026-11-20", tmp_path / "tt.json") and H.can_gui("2026-12-01", tmp_path / "tt.json")
