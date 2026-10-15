# -*- coding: utf-8 -*-
"""Dữ liệu giả lập dùng chung cho test – KHÔNG gọi mạng."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("MPLBACKEND", "Agg")


def tao_gia(n=800, gia_dau=50.0, xu_huong=0.0008, bien_dong=0.015, seed=1, ket_thuc=None, kl=1_000_000):
    """Chuỗi OHLCV ngày làm việc, có sóng hình sin để tạo đỉnh/đáy rõ (giá: nghìn đồng)."""
    rng = np.random.default_rng(seed)
    ket_thuc = ket_thuc or pd.Timestamp.today().normalize() - pd.offsets.BDay(1)
    ngay = pd.bdate_range(end=ket_thuc, periods=n)
    r = xu_huong + bien_dong * rng.standard_normal(n) + 0.006 * np.sin(np.arange(n) / 9)
    close = gia_dau * np.exp(np.cumsum(r))
    mo = close * (1 + 0.003 * rng.standard_normal(n))
    cao = np.maximum(mo, close) * (1 + np.abs(0.006 * rng.standard_normal(n)))
    thap = np.minimum(mo, close) * (1 - np.abs(0.006 * rng.standard_normal(n)))
    vol = kl * (1 + 0.3 * np.abs(rng.standard_normal(n)))
    return pd.DataFrame({"open": mo, "high": cao, "low": thap, "close": close, "volume": vol},
                        index=pd.DatetimeIndex(ngay, name="time"))


@pytest.fixture
def gia_tang():
    return tao_gia(xu_huong=0.0015, seed=3)


@pytest.fixture
def gia_giam():
    return tao_gia(xu_huong=-0.0015, seed=4)


@pytest.fixture
def thu_muc_du_lieu(tmp_path):
    """Thư mục CSV giá 5 mã + VNINDEX + file cơ bản → chạy bộ lọc đầu-cuối offline."""
    d = tmp_path / "gia"
    d.mkdir()
    cau_hinh = {"AAA": (0.0015, 3), "BBB": (0.001, 5), "CCC": (-0.001, 7), "DDD": (0.0005, 9), "EEE": (0.002, 11)}
    for ma, (xh, sd) in cau_hinh.items():
        tao_gia(xu_huong=xh, seed=sd).reset_index().to_csv(d / f"{ma}.csv", index=False)
    vni = tao_gia(gia_dau=1200, xu_huong=0.0004, bien_dong=0.01, seed=99)
    vni.reset_index().to_csv(tmp_path / "vnindex.csv", index=False)
    pd.DataFrame({"ma": list(cau_hinh), "eps_ttm": [5000, 4000, -500, 3000, 6000],
                  "bvps": [30000, 25000, 20000, 18000, 40000], "roe": [18, 15, -2, 13, 20],
                  "roa": [9, 7, -1, 6, 11], "eps_nam": [4800, 3900, 100, 2900, 5500],
                  "eps_nam_truoc": [4000, 3500, 800, 3000, 5000], "eps_quy": [1300, 1000, -200, 700, 1600],
                  "eps_quy_cung_ky": [1100, 900, 300, 800, 1400], "no_phai_tra_tts": [40, 50, 70, 30, 45],
                  "so_cp": [1e8] * 5}).to_csv(tmp_path / "co_ban.csv", index=False)
    return tmp_path
