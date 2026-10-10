# -*- coding: utf-8 -*-
"""Bảng trạng thái của bot: hệ thống CHỜ BÁN (thủng cắt lỗ / hết hạn) → 'BÁN phiên tới' → không vào nhóm mua."""
import numpy as np

from canh_bao.chien_luoc_bot import _bang_diem_mua


def _vt(**k):
    return {"Cắt lỗ phiên tới": 36.55, "Tầng": 1, "Ngày mua": "2026-07-31", "Giá mua": 32.0, "Lãi hiện tại %": 14.0,
            "Lãi (R)": 2.0, "KL (phần vốn)": 1.0, "Số lần nhồi": 0, "Bán phiên tới (MA10 tuần)": False,
            "Đang chờ bán": False, **k}


def test_cho_ban():
    x = {"c": np.array([36.5]), "atr": np.array([0.8])}
    r = _bang_diem_mua({"vi_the": _vt(**{"Đang chờ bán": True, "Lý do chờ bán": "hết hạn"}), "cho_vao": None}, x, 1.0)
    assert r["Trạng thái"] == "ĐANG GIỮ → BÁN phiên tới (hết hạn)"
    r = _bang_diem_mua({"vi_the": _vt(**{"Bán phiên tới (MA10 tuần)": True}), "cho_vao": None}, x, 1.0)
    assert "đóng cửa tuần < MA10 tuần" in r["Trạng thái"]
    assert _bang_diem_mua({"vi_the": _vt(), "cho_vao": None}, x, 1.0)["Trạng thái"] == "ĐANG GIỮ"
    from ptcp.chien_luoc import phan_loai
    assert phan_loai("ĐANG GIỮ → BÁN phiên tới (hết hạn)", 40.0, 36.55, 2.0) == "BAN"
