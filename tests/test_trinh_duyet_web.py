# -*- coding: utf-8 -*-
"""KIỂM THỬ TRÌNH DUYỆT THẬT (14/11/2026): mở trang Tra cứu mã / Biểu đồ (docs/ma) và Bảng thị trường (trang_bang) trong
Chromium với dữ liệu mẫu (mã giả AAA / BBB – tests/mau_web + giá sinh bằng đúng hàm của workflow), khổ máy tính và điện
thoại → không được có lỗi JavaScript / trang trắng. Test đọc mã nguồn (test_*_web.py) không bắt được lỗi chạy thật.
Cần Node + Playwright (kiem_thu.yml cài; máy không có → bỏ qua)."""
import json
import os
import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAU = os.path.join(GOC, "tests", "mau_web")
CHAY = os.path.join(GOC, "tests", "trinh_duyet_web.mjs")


def _co_playwright():
    if not shutil.which("node"):
        return False
    r = subprocess.run(["node", "-e", "require('playwright')"], capture_output=True, cwd=GOC)
    return r.returncode == 0


pytestmark = pytest.mark.skipif(not _co_playwright(), reason="cần Node + Playwright (kiem_thu.yml cài)")


def _gia(ma, gia0, n=320, seed=1):
    """Lịch sử ngày giả (price-history Vietcap) → gia/<MÃ>.json bằng tra_cuu_dn.gon_gia như workflow."""
    from thi_truong.tra_cuu_dn import gon_gia
    rng = np.random.default_rng(seed)
    ngay = pd.bdate_range(end="2026-11-13", periods=n)
    c = gia0 * np.exp(np.cumsum(rng.normal(0.0005, 0.018, n)))
    ds = []
    for d, x in zip(ngay, c):
        o = x * (1 + rng.normal(0, 0.006))
        ds.append({"tradingDate": f"{d:%Y-%m-%d}T00:00:00", "openPrice": o, "highestPrice": max(o, x) * 1.01,
                   "lowestPrice": min(o, x) * 0.99, "closePrice": x, "totalMatchVolume": int(rng.integers(1e5, 3e6)),
                   "totalValue": x * 1e6, "foreignBuyValueTotal": 2e9, "foreignSellValueTotal": 1.5e9,
                   "foreignOwnedPercentage": 0.2})
    return {**gon_gia(ds[::-1]), "cap_nhat": "2026-11-13"}


def _du_lieu_bang(tmp_path, monkeypatch):
    """du_lieu.json của Bảng thị trường dựng bằng dung.chup trên nguồn giả (như test_thi_truong)."""
    from thi_truong import dung, nguon, tinh
    from tests.test_thi_truong import MAU_VIC, _nen_phut
    n1 = _nen_phut(["2026-11-11", "2026-11-12", "2026-11-13"], [12e6, 15e6, 14e6])
    cb = {"tao_luc": "2026-11-12 19:07", "nganh": {"VIC": "Bất động sản", "AAA": "Ngân hàng"}, "ten": {"VIC": "VinGroup"},
          "vu": ["VIC", "AAA"], "td": {"VIC": ["2026-11-12", 1.6]},
          "ls": {"VIC": {"day_du": {"ngay": "2026-11-12", "c": [230000.0] * 60, "cao250": 260000.0, "thap250": 150000.0,
                                    "kl20": 1.5e6, "gt20": 350.0, "nn": [-0.1, -0.5, 0.2]}, "bo_cuoi": None}},
          "nn_san": [("2026-11-12", -65.5), ("2026-11-11", -502.2)], "td_san": [("2026-11-12", 286.8)],
          "ho_so": tinh.ho_so_thanh_khoan(n1, truoc_ngay="2026-11-13"), "vni_ngay": [["2026-11-12", 1733.02]],
          "nhom": {"VN30": ["VIC"], "HNX30": []}}
    aaa = {"listingInfo": {"symbol": "AAA", "refPrice": 10000, "ceiling": 10700, "floor": 9300, "board": "HNX",
                           "type": "STOCK", "listedShare": 1e8},
           "matchPrice": {"matchPrice": 9900, "accumulatedValue": 5000, "accumulatedVolume": 5e5}}
    monkeypatch.setattr(nguon, "nen", lambda ma, khung="ONE_MINUTE", so_nen=400, timeout=30: n1)
    monkeypatch.setattr(nguon, "chi_so", lambda ds=nguon.CHI_SO: [
        {"symbol": "VNINDEX", "price": 1740.36, "refPrice": 1733.02, "change": 7.34, "changePercent": 0.42,
         "totalValue": 9915511.4, "totalStockIncrease": 147, "totalStockDecline": 161, "totalStockNoChange": 54},
        {"symbol": "VN30", "price": 1866.08, "refPrice": 1862.07, "change": 4.01, "changePercent": 0.22,
         "totalValue": 4776040.1}])
    monkeypatch.setattr(nguon, "tat_ca_ma", lambda: [{"symbol": "VIC", "board": "HSX", "type": "STOCK"},
                                                     {"symbol": "AAA", "board": "HNX", "type": "STOCK"}])
    monkeypatch.setattr(nguon, "bang_gia", lambda ds, lo=400: [x for x in (MAU_VIC, aaa) if x["listingInfo"]["symbol"] in ds])
    monkeypatch.setattr(nguon, "tac_dong", lambda *a: {"topUp": [{"symbol": "VIC", "impact": 5.77}], "topDown": []})
    monkeypatch.setattr(nguon, "buoc_gia", lambda ma: [{"accumulatedBuyVolume": 3, "accumulatedSellVolume": 1}])
    cl = tmp_path / "chien_luoc.json"
    cl.write_text(json.dumps({"ds_mua": {"hieu_luc": "2026-11-14", "ma": [
        {"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.38, "mt1": 10.62, "mt3": 11.85, "ly_do": "MACD"}]}}),
        encoding="utf-8")
    monkeypatch.setattr(dung, "FILE_CHIEN_LUOC", str(cl))
    monkeypatch.delenv("MA_GIU_FILE", raising=False)
    ra = tmp_path / "du_lieu.json"
    dung.chup(cb, str(ra), luc=pd.Timestamp("2026-11-13 16:00"), in_tien_do=lambda *a: None)
    return ra


def _site(tmp_path, monkeypatch):
    site = tmp_path / "site"
    shutil.copytree(os.path.join(GOC, "docs", "ma"), site / "ma", ignore=shutil.ignore_patterns("du_lieu"))
    dl = site / "ma" / "du_lieu"
    shutil.copytree(MAU, dl)
    (dl / "gia").mkdir()
    for ma, g0, s in (("AAA", 25000.0, 1), ("BBB", 60000.0, 2)):
        (dl / "gia" / f"{ma}.json").write_text(json.dumps(_gia(ma, g0, seed=s)), encoding="utf-8")
    bang = _du_lieu_bang(tmp_path, monkeypatch)
    (site / "thi_truong").mkdir()
    shutil.copy(bang, site / "thi_truong" / "du_lieu.json")
    (site / "bang").mkdir()
    shutil.copy(os.path.join(GOC, "trang_bang", "index.html"), site / "bang" / "index.html")
    shutil.copy(bang, site / "bang" / "du_lieu.json")
    return site


TRANG = [
    "ma/index.html||cho:500",                                   # trang đầu Tra cứu mã
    "ma/index.html#AAA|#noi-dung|sk",                           # tổng quan mã (biểu đồ nến) + rê / chạm bong bóng sự kiện
    "ma/index.html#AAA/tai-chinh|#noi-dung",
    "ma/index.html#AAA/dinh-gia|#noi-dung",
    "ma/index.html#AAA/lich-su|#noi-dung",
    "ma/index.html#bieu-do/AAA||cho:800",                       # biểu đồ toàn màn hình
    "ma/index.html#loc||cho:500",
    "bang/index.html||cho:800",                                 # Bảng thị trường
]


def test_trang_web_chay_khong_loi_js(tmp_path, monkeypatch):
    site = _site(tmp_path, monkeypatch)
    r = subprocess.run(["node", CHAY, str(site), *TRANG], capture_output=True, text=True, timeout=600, cwd=GOC)
    try:
        kq = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        pytest.fail(f"không chạy được trình duyệt: {r.stderr[-1500:]}")
    loi = {f"{x['trang']} [{x['kho']}]": x["loi"] for x in kq if x["loi"]}
    assert not loi, "lỗi khi mở trang trong trình duyệt:\n" + json.dumps(loi, ensure_ascii=False, indent=1)
    assert len(kq) == 2 * len(TRANG)
