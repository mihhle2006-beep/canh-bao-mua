# -*- coding: utf-8 -*-
import os

import numpy as np
import pandas as pd

from canh_bao import bieu_do_moc as B


def test_cac_moc():
    m = B.cac_moc(100.0, 95.0, "VAO_NUA")
    gia = [x[0] for x in m]
    assert gia == [115.0, 110.0, 105.0, 100.0, 97.5, 95.0]
    nhan = " | ".join(x[1] for x in m)
    assert "GIỮ lại" in nhan and "Mua 1 phần (½ KL)" in nhan and "Cắt lỗ toàn bộ" in nhan
    assert "Mua toàn bộ (đủ KL)" in B.cac_moc(100.0, 95.0)[3][1]
    assert B.cac_moc(100.0, 101.0) == [] and B.cac_moc(100.0, float("nan")) == []
    v = B.moc_vi_the(100.0, 5.0, 104.0)
    assert ("Cắt lỗ hiện tại" in v[-1][1] or v[-1][0] == 97.5) and any("Giá vốn" in x[1] for x in v)


def test_ve(tmp_path):
    idx = pd.bdate_range(end="2026-10-09", periods=150)
    c = np.linspace(90, 101, 150)
    dn = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c}, index=idx)
    p = B.ve("ABC", dn, B.cac_moc(100.0, 95.0), "ABC – 🟢 MUA MỚI 100,00", str(tmp_path / "a.png"), vung=(98, 101),
             ngay_mua="2026-09-01")
    assert p and os.path.getsize(p) > 10_000
    assert B.ve_an_toan("ABC", None, [], "x") is None
