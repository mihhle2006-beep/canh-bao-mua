# -*- coding: utf-8 -*-
import pandas as pd

from canh_bao import vi_the

CSV = """﻿ma,so_cp,gia_von,ngay_mua,hanh_dong,cat_lo_de_xuat,gia_hien_tai,lai_lo_pct,ly_do,cap_nhat
HPG,100,24.55,,GIỮ CÓ ĐIỀU KIỆN,19.36,20.10,-18.1,x,10/10/2026
VIB,219,13.8,,GIỮ,12.92,13.65,-1.1,x,10/10/2026
VIB,210,17,,GIỮ,12.80,13.65,-19.7,x,10/10/2026
HPA,50,39.85,,KIỂM TRA,,,,x,
EVF,0,14.2,,,,,,,
"""


def test_doc_va_gop():
    v = vi_the.phan_tich_csv_cu(CSV.lstrip("﻿"))
    assert set(v) == {"HPG", "VIB", "HPA"}                                   # so_cp 0 bỏ
    assert v["VIB"]["so_cp"] == 429 and abs(v["VIB"]["gia_von"] - 15.366) < 0.01 and v["VIB"]["cat_lo"] == 12.92
    assert v["HPA"]["cat_lo"] is None and v["HPG"]["cu"]


def test_danh_gia_va_tin():
    v = vi_the.phan_tich_csv_cu(CSV.lstrip("﻿"))["HPG"]
    assert vi_the.danh_gia_ban_cu(v, 20.10)["muc"] == "GIU"
    assert vi_the.danh_gia_ban_cu(v, 19.50)["muc"] == "GAN_CAT_LO"
    kb = vi_the.danh_gia_ban_cu(v, 19.30)
    assert kb["muc"] == "CAT_LO"
    tin = vi_the.tin_ban_cu(v, kb, pd.Timestamp("2026-10-12 10:15"))
    assert "HPG (danh mục cũ)" in tin and "Bán toàn bộ 100 CP" in tin and "danh_muc_cu.csv" in tin
    tt = {}
    assert vi_the.can_bao_ban("CU:HPG", "CAT_LO", "2026-10-12 10:15", tt)
    assert not vi_the.can_bao_ban("CU:HPG", "CAT_LO", "2026-10-12 10:30", tt)  # cùng mức cùng ngày: không lặp
