# -*- coding: utf-8 -*-
"""Backtest phương pháp trên nhiều mã (CSV giả lập, không mạng)."""
import os

from ptcp import backtest_phuong_phap
from tests.conftest import tao_gia


def test_backtest_phuong_phap_nhieu_ma(tmp_path):
    csv = {}
    for i, s in enumerate((3, 5, 7, 11, 13, 17)):
        p = tmp_path / f"m{i}.csv"
        tao_gia(seed=s).rename_axis("date").reset_index().to_csv(p, index=False)
        csv[f"M{i}"] = str(p)
    csv["LOI"] = str(tmp_path / "khong_co.csv")
    os.chdir(tmp_path)
    kq = backtest_phuong_phap(list(csv), csv=csv, in_ket_qua=False)
    assert "LOI" in kq["loi"] and len(kq["ds_ma"]) == 6
    b = kq["bang"]
    assert len(b) == 13 and set(b["Xếp hạng"]) <= {"MẠNH", "KHÁ", "YẾU", "KHÔNG CÓ LỢI THẾ"}
    assert (b["KTC90 thấp %"] <= b["TB/lệnh %"] + 1e-9).all() and (b["KTC90 cao %"] >= b["TB/lệnh %"] - 1e-9).all()
    assert b["Đạt (4 phép)"].is_monotonic_decreasing
    assert kq["ket_luan"] and os.path.exists(kq["file_excel"])
    assert set(kq["lenh"]["Mã"]) <= set(kq["ds_ma"])
