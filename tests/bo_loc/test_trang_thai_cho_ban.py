# -*- coding: utf-8 -*-
import numpy as np

from bo_loc.chien_luoc_tt import _dong_diem_mua


def test_cho_ban():
    vt = {"Cắt lỗ phiên tới": 36.55, "Tầng": 1, "Ngày mua": "2026-07-31", "Giá mua": 32.0, "Lãi (R)": 2.0,
          "Bán phiên tới (MA10 tuần)": False, "Đang chờ bán": True, "Lý do chờ bán": "cắt lỗ động"}
    x = {"c": np.array([36.5]), "atr": np.array([0.8])}
    assert _dong_diem_mua({"vi_the": vt, "cho_vao": None}, x)["Trạng thái"] == "ĐANG GIỮ → BÁN phiên tới (cắt lỗ động)"
