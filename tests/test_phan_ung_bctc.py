# -*- coding: utf-8 -*-
"""thi_truong/phan_ung_bctc.py – phản ứng giá sau BCTC (ngày biết chắc = min(ngày công bố, hết quý + 30)) + PEAD."""
import json
from datetime import date, timedelta

from thi_truong import phan_ung_bctc as P


def _chuoi(n=900, tu="2022-01-03"):
    d, t = [], date.fromisoformat(tu)
    while len(d) < n:
        if t.weekday() < 5:
            d.append(t.isoformat())
        t += timedelta(days=1)
    return d, [10.0 * (1 + 0.001 * i) for i in range(n)]


def _kho(ky_ln, ncb=None):
    return {"ky": {"kd": {k: {"isa20": v * 1e9} for k, v in ky_ln.items()}}, "ngay_cb": {"kd": ncb or {}}}


def test_ngay_biet_chac_va_lai_sau():
    d, c = _chuoi()
    ln = {f"{y}-Q{q}": 100 + 10 * (y - 2020) + q for y in range(2020, 2025) for q in range(1, 5)}
    kho = _kho(ln, {"2023-Q1": "2023-04-25", "2023-Q2": "2023-08-29"})     # Q2: bản soát xét muộn → dùng hạn 30/07
    pu = {x[0]: x for x in P.phan_ung(kho, d, c, tu_nam=2023)}
    assert pu["2023-Q1"][1] == "2023-04-25" and pu["2023-Q2"][1] == "2023-07-30" and pu["2023-Q3"][1] == "2023-10-30"
    E = next(i for i, x in enumerate(d) if x > "2023-04-25")
    assert abs(pu["2023-Q1"][7] - (c[E + 20] / c[E] - 1)) < 1e-4 and abs(pu["2023-Q1"][5] - (c[E] / c[E - 2] - 1)) < 1e-4
    assert pu["2023-Q1"][2] == 131.0 and abs(pu["2023-Q1"][3] - (131 / 121 - 1)) < 1e-4
    assert pu["2023-Q1"][4] is None                                       # chênh cùng kỳ không đổi → độ lệch 0 → không có SUE
    assert all(x[1] > "2023" for x in pu.values())


def test_chuoi_gia_noi_gia_dai():
    gd = {"d0": "2021-01-04", "g": [0, 1, 1], "c": [5.0, 5.5, 6.0]}
    d, c = P.chuoi_gia({"d": ["2021-01-06", "2021-01-07"], "c": [12.0, 13.0]}, gd)
    assert d == ["2021-01-04", "2021-01-05", "2021-01-06", "2021-01-07"] and c == [10.0, 11.0, 12.0, 13.0]


def test_pead_chuoi_in():
    d, c = _chuoi()
    vni = [1000.0] * len(d)
    ds = {}
    for m in range(30):                                                   # SUE cao ↔ giá tăng nhanh hơn
        cm = [10.0 * (1 + 0.0002 * m * i) for i in range(len(d))]
        pu = [[f"2023-Q{q}", f"2023-{3 * q:02d}-28", 1.0, 0.1 * m, float(m), 0.0, 0, 0, 0, 0] for q in (1, 2, 3)]
        ds[f"M{m:02d}"] = (pu, d, cm)
    s = P.pead(ds, d, vni)
    dong = [x for x in s.splitlines() if "SUE" in x and "20 phiên" in x][0]
    assert "3/3 quý > 0" in dong and "IC +1.000" in dong
    json.dumps(s)
