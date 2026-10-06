# -*- coding: utf-8 -*-
"""Dữ liệu giả lập dùng chung cho các test (không cần mạng)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ptcp import cau_hinh as cfg  # noqa: E402

cfg.SO_LAN_THU = 1


@pytest.fixture(autouse=True)
def _nhat_ky_tam(tmp_path, monkeypatch):
    """Nhật ký khuyến nghị của test ghi vào thư mục tạm, không làm bẩn repo / Drive."""
    monkeypatch.setattr(cfg, "FILE_NHAT_KY", str(tmp_path / "nhat_ky_ptcp.csv"))


def tao_gia(n=1500, seed=3, xu_huong=0.0005, sigma=0.022, gia_dau=20.0, cuoi_giam=False):
    """Chuỗi OHLCV ngày giả lập (giá nghìn đồng)."""
    rng = np.random.default_rng(seed)
    d = pd.bdate_range(end="2026-10-02", periods=n)
    r = xu_huong + sigma * rng.standard_t(5, n) / 1.3
    r = np.clip(r, -0.069, 0.069)
    if cuoi_giam:
        r[-60:] = -0.008 + 0.01 * rng.standard_normal(60)
        r[-3:] = -0.03
    c = gia_dau * np.exp(np.cumsum(r))
    o = c * np.exp(rng.normal(0, 0.005, n))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.01, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.01, n)))
    v = (1e6 * np.exp(rng.normal(0, 0.4, n))).round()
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": v}, index=d)


@pytest.fixture(scope="session")
def gia_ngay():
    return tao_gia()


@pytest.fixture(scope="session")
def thu_muc_csv(tmp_path_factory):
    """Ghi CSV ngày (tăng & giảm sâu) + VNINDEX để chạy main() không cần mạng."""
    p = tmp_path_factory.mktemp("du_lieu")
    for ten, df in (("tang", tao_gia(seed=3)), ("giam", tao_gia(seed=5, cuoi_giam=True))):
        df.rename_axis("date").reset_index().to_csv(p / f"{ten}.csv", index=False)
    v = tao_gia(seed=9, sigma=0.011, gia_dau=1000)
    v.rename_axis("date").reset_index().to_csv(p / "vni.csv", index=False)
    return p
