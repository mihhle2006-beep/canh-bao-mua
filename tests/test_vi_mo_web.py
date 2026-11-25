# -*- coding: utf-8 -*-
"""Tab Vĩ mô (Bảng thị trường): dựng JSON từ chuỗi giả – không mạng."""
from datetime import datetime

import numpy as np
import pandas as pd

from thi_truong import vi_mo_web as V


def _gia(n, g0, tu="2019-01-01", seed=0, f="B"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(tu, periods=n, freq=f)
    return pd.Series(g0 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), idx)


def _mau():
    c = _gia(2000, 1300.0)
    xd = pd.DataFrame({"open": c * 0.999, "high": c * 1.01, "low": c * 0.99, "close": c})
    gio = pd.DataFrame({"open": [3500.0] * 5, "high": [3510.0] * 5, "low": [3490.0] * 5, "close": [3505.0] * 5},
                       index=pd.date_range("2026-11-24", periods=5, freq="h"))
    sjc_b = _gia(300, 130.0, tu="2025-12-01", f="D")
    S = {"xau_nen": xd, "xau_gio": gio, "sjc": pd.DataFrame({"mua": sjc_b - 3, "ban": sjc_b}),
         "nhan": pd.DataFrame({"mua": sjc_b - 5, "ban": sjc_b - 2}),
         "usdvnd": pd.Series(25000.0, index=c.index), "dxy": _gia(2000, 100.0, seed=2),
         "vn_dh": pd.Series([6.0, 5.0, 4.5], index=pd.to_datetime(["2020-01-01", "2023-01-01", "2023-06-01"])),
         "vn_10n": _gia(2000, 3.0, seed=3), "us_10n": _gia(2000, 4.0, seed=4), "us_thuc10": _gia(2000, 1.5, seed=5)}
    N = {"xau": "Stooq", "sjc": "vang.today", "vn_10n": "HNX từ 2014"}
    P = {"gia_ngay": 3600.0, "gia_ngay_luc": datetime(2026, 11, 25, 21, 50, tzinfo=V.VN),
         "vcb": {"mua": 25610.0, "ck": 25640.0, "ban": 26020.0},
         "song": {"url": "https://api.gold-api.com/price/XAU", "kieu": "gold_api", "gia": 3600.0}}
    return S, N, P


def test_dung_json_the_chuoi_nen():
    S, N, P = _mau()
    kq = V.dung(S, N, P, bay_gio=datetime(2026, 11, 25, 22, 0, tzinfo=V.VN))
    the = {t["k"]: t for t in kq["the"]}
    assert the["xau"]["gia"] == 3600.0 and the["xau"]["luc"] == "21:50 25/11"          # giá ngay trên thẻ
    assert {"sjc_ban", "nhan_ban", "tg_vnd", "chenh", "usdvnd", "dxy", "vn_dh", "vn_10n", "us_10n", "us_thuc10",
            "vcb"} <= set(the)
    tg = kq["chuoi"]["tg_vnd"]["d"][-1][1]
    assert abs(tg - S["xau_nen"]["close"].iloc[-1] * 25000 * V.LUONG_OZ / 1e6) < 0.01   # quy đổi tr.đ/lượng
    assert the["chenh"]["kieu_doi"] == "đ" and the["vn_dh"]["gia"] == 4.5 and the["vn_dh"]["doi"] == -0.5
    d = kq["chuoi"]["xau"]["d"]
    assert d[0][0] < d[-1][0] and len(d) < 2000                                         # cũ gộp tuần → nhẹ
    for c in kq["chuoi"].values():                                                       # biểu đồ: ngày tăng dần, không trùng
        ng = [r[0] for r in c["d"]]
        assert ng == sorted(ng) and len(set(ng)) == len(ng), c["ten"]
    ng = [r[0] for r in kq["xau_nen"]]
    assert ng == sorted(ng) and len(set(ng)) == len(ng)
    assert all(len(r) == 5 for r in kq["xau_nen"]) and len(kq["xau_gio"]) == 5
    assert kq["song"]["kieu"] == "gold_api" and "không phải tín hiệu" in kq["ghi_chu"]
    assert "sjc_mua" in kq["chuoi"] and kq["chuoi"]["vn_10n"]["nguon"] == "HNX từ 2014"


def test_dung_thieu_nguon_van_chay():
    kq = V.dung({}, {}, {}, bay_gio=datetime(2026, 11, 25, tzinfo=V.VN))
    assert kq["the"] == [] and kq["chuoi"] == {} and kq["xau_nen"] == [] and kq["song"] is None


def test_kiem_song_chi_nhan_nguon_cho_phep_cors():
    class R:
        def __init__(self, h, j):
            self.headers, self._j = h, j

        def json(self):
            return self._j

    def lay(url, **k):
        if "gold-api" in url:
            return R({"Access-Control-Allow-Origin": "https://khac.example"}, {"price": 3600})
        return R({"Access-Control-Allow-Origin": "*"},
                 [{"spreadProfilePrices": [{"bid": 3599.0, "ask": 3601.0}], "ts": 1}])
    s = V.kiem_song(lay)
    assert s["kieu"] == "swissquote" and s["gia"] == 3600.0
    assert V.kiem_song(lambda url, **k: R({}, {})) is None
