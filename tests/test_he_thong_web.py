# -*- coding: utf-8 -*-
"""thi_truong/he_thong_web.py – dữ liệu hệ thống cho mục "Đọc biểu đồ": ngưỡng luật đọc từ cau_hinh.py, bảng điều kiện từng mã,
lịch sử tín hiệu bot (lich_su_danh_gia.csv) theo mã."""
import json

from thi_truong import he_thong_web as H


def test_nguong_doc_tu_cau_hinh_thieu_thi_mac_dinh(tmp_path):
    p = tmp_path / "cau_hinh.py"
    p.write_text("import os\nQUY_TOP_GTGD = 80\nQUY_RS3T_NONG = 85.5   # ghi chú\n  QUY_MANH_TK = 9\n")
    ng = H.nguong(str(p))
    assert ng["QUY_TOP_GTGD"] == 80 and isinstance(ng["QUY_TOP_GTGD"], int) and ng["QUY_RS3T_NONG"] == 85.5
    assert ng["QUY_MANH_TK"] == H.NGUONG_MAC["QUY_MANH_TK"]                   # thụt lề (trong hàm / khối) → không lấy
    assert H.nguong(str(tmp_path / "khong_co.py")) == H.NGUONG_MAC


def test_he_thong_va_lich_su_tin_hieu(tmp_path):
    loc = {"ngay_gia": "2026-11-06", "ro_tuan": {"ngay_chot": "2026-10-30", "ma": ["BBB", "AAA"]}, "hang_gtgd": {"AAA": 2, "BBB": 1, "CCC": 150},
           "gtgd": {"AAA": 300.5}, "hang_rs3t": {"AAA": 95}, "bien_dong_hang": {"AAA": 0.2}, "dinh_gia": {"AAA": -25.0}}
    d = H.he_thong(loc, H.NGUONG_MAC, {"phien": "2026-11-06", "ma": {"AAA": ["quy_b"]}})
    assert set(d["ma"]) == {"AAA", "BBB", "CCC"} and len(d["cot"]) == len(d["ma"]["AAA"])
    r = dict(zip(d["cot"], d["ma"]["AAA"]))
    assert r["hang_ro_tuan"] == 2 and r["hang_rs3t"] == 95 and r["dinh_gia"] == -25.0 and r["tk_tang"] is None
    assert d["ma"]["CCC"][0] is None and d["bo_loc"] == {"AAA": ["quy_b"]} and d["ro_ngay_chot"] == "2026-10-30"
    csv = tmp_path / "ls.csv"
    csv.write_text("﻿id,ngay,ma,loai,nhom,ket_qua,gia,so_tk\n1,2026-11-02,aaa,MUA_NGAY,MUA,ĐÚNG,10,999\n2,2026-10-01,AAA,CHIEN_LUOC,MUA,SAI,9,1\n"
                   "3,2026-10-05,,X,MUA,SAI,1,1\n", encoding="utf-8")
    th = H.lich_su_tin_hieu(str(csv))
    assert list(th) == ["AAA"] and [z["ngay"] for z in th["AAA"]] == ["2026-10-01", "2026-11-02"]
    assert "so_tk" not in th["AAA"][0] and th["AAA"][1]["ket_qua"] == "ĐÚNG"                # chỉ cột cần, không cột lạ
    out = tmp_path / "ra"
    assert H.main(["--ra", str(out), "--loc", str(tmp_path / "x.json"), "--lich_su", str(csv), "--bo_loc", str(tmp_path / "y.json")]) == 0
    assert json.loads((out / "tin_hieu" / "AAA.json").read_text())[0]["ngay"] == "2026-10-01"
    assert json.loads((out / "he_thong.json").read_text())["ma"] == {}
