# -*- coding: utf-8 -*-
"""Xuất giá ra Excel (thi_truong/xuat_excel_gia): sheet, ngày mới nhất trên, công thức kèm giá trị, giá tuần, tốc độ."""
import time
import warnings

import numpy as np
import pandas as pd
import pytest

from thi_truong import xuat_excel_gia as X

openpyxl = pytest.importorskip("openpyxl")
pytest.importorskip("xlsxwriter")


def _gop(ma=("BBB", "AAA"), n=300):
    rng = np.random.default_rng(1)
    ds = []
    for k, m in enumerate(ma):
        ngay = pd.bdate_range(end="2026-11-27", periods=n - 20 * k)          # mã sau lên sàn muộn hơn
        c = 20 * np.exp(np.cumsum(rng.normal(0, 0.02, len(ngay))))
        ds.append(pd.DataFrame({"ma": m, "ngay": ngay, "open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                                "volume": rng.integers(1e5, 1e6, len(ngay)).astype(float)}))
    return pd.concat(ds)


def _doc(f, gia_tri=True):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return openpyxl.load_workbook(f, data_only=gia_tri)


def test_cau_truc_va_gia_tri(tmp_path):
    g = _gop()
    f = X.ghi_excel(g, str(tmp_path / "gia.xlsx"), "2026-11-27")
    wb, ct = _doc(f), _doc(f, False)
    assert wb.sheetnames == ["Tổng quan", "Thông tin giá", "% thay đổi (Tuần)", "BBB", "AAA"]   # giữ thứ tự mã nhập
    b = g[g.ma == "BBB"].reset_index(drop=True)
    ws = wb["BBB"]
    assert ws["A5"].value == pd.Timestamp("2026-11-27") and ws["A6"].value < ws["A5"].value     # mới nhất trên
    assert abs(ws["E5"].value - b.close.iloc[-1]) < 1e-9
    assert abs(ws["G5"].value - (b.close.iloc[-1] / b.close.iloc[-2] - 1)) < 1e-12         # giá trị kèm công thức
    assert ct["BBB"]["G5"].value.startswith("=IFERROR(E5/E6-1")
    tq = wb["Tổng quan"]
    assert tq["A5"].value == "BBB" and abs(tq["F5"].value - (b.close.iloc[-1] / b.close.iloc[-6] - 1)) < 1e-12
    assert tq["B6"].value == g[g.ma == "AAA"].ngay.min() and tq["D6"].value == 280
    t = wb["Thông tin giá"]
    assert [c.value for c in t[4]][:3] == ["Ngày (cuối tuần)", "BBB", "AAA"] and t["A5"].value == pd.Timestamp("2026-11-27")
    tuan = b.set_index("ngay").close.resample("W-FRI").last()
    assert abs(t["B6"].value - tuan.iloc[-2]) < 1e-9
    p = wb["% thay đổi (Tuần)"]
    assert abs(p["B5"].value - (tuan.iloc[-1] / tuan.iloc[-2] - 1)) < 1e-12


def test_tuan_do_dang_lay_ngay_cuoi():
    g = _gop(("AAA",), 30)
    g = g[g.ngay <= "2026-11-25"]                                    # thứ Tư – tuần chưa hết
    assert X.tuan(g).index[0] == pd.Timestamp("2026-11-25")


def test_nhanh(tmp_path):
    g = _gop(tuple(f"M{i:02d}" for i in range(20)), 3000)              # 20 mã × ~3.000 phiên
    t0 = time.time()
    X.ghi_excel(g, str(tmp_path / "lon.xlsx"))
    assert time.time() - t0 < 30
