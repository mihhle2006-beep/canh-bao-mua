# -*- coding: utf-8 -*-
"""--chi_ma: chỉ xem vài mã, không ghi trạng thái / danh sách mua (không mạng)."""
import os
import sys
from unittest import mock

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytest.importorskip("ptcp.nhat_ky", reason="cần gói ptcp")
import chay  # noqa: E402
from canh_bao import chien_luoc_bot, tong_ket_cl  # noqa: E402


def test_chi_ma_khong_ghi_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ra = {"doc": {"ngay": "2026-10-07", "diem": 4, "so_chi_bao": 8}, "cl": 2, "thieu": ["XYZ"],
          "diem_mua": {"A0": pd.DataFrame([{"Mã": "HPG", "Trạng thái": "CHỜ tín hiệu"}])}}
    k = {"ma": "FPT", "nhom": "VAO_NUA", "tu": 100, "den": 103, "cl": 95, "mt1": 108, "mt3": 118,
         "ly_do": "tín hiệu MACD", "he_so_kl": 1}
    goi = {}

    def chay_cl(tai, bay_gio, ds_ma=None, ds_do_rong=None):
        goi["ds"] = ds_ma
        return ra, None
    with mock.patch.object(chien_luoc_bot, "chay_chien_luoc", chay_cl), \
            mock.patch.object(tong_ket_cl, "ds_khuyen_nghi", lambda r: [k]):
        assert chay.main(["--chi_ma", "fpt, hpg,XYZ", "--khong_gui"]) == 0
    out = capsys.readouterr().out
    assert goi["ds"] == ["FPT", "HPG", "XYZ"]
    assert "FPT | 100.00–103.00" in out and "HPG: chưa có tín hiệu" in out and "XYZ: thiếu dữ liệu" in out
    assert os.listdir(tmp_path) == []                       # không ghi trạng thái / nhật ký / trang
