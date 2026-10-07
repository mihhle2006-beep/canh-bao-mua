# -*- coding: utf-8 -*-
"""Trang tổng hợp – không cần mạng, không cần ptcp."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import trang_tong_hop as TH  # noqa: E402


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
    p = TH.tao(bay_gio="2026-10-07 15:20")
    s = open(p, encoding="utf-8").read()
    assert p == C.FILE_TRANG and "FPT" in s and "1.712,30" in s and "&lt;ngày&gt;" in s
    assert "Danh mục thật" not in s and "giả lập" not in s
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
