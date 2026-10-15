# -*- coding: utf-8 -*-
"""Kiểm thử lớp dữ liệu giá: đổi đơn vị, tự chuyển nguồn, đọc CSV, bộ nhớ đệm, phân tích JSON từng nguồn."""
import pandas as pd
import pytest

from bo_loc import cau_hinh as ch
from bo_loc.nguon import gia
from bo_loc.nguon.http import NHAT_KY
from tests.bo_loc.conftest import tao_gia


def _raw(df):
    return df.reset_index()


def test_ve_nghin_dong():
    df = tao_gia(n=50)
    assert gia.ve_nghin_dong(df, 1000).close.equals(df.close)
    dong = df.copy()
    dong[["open", "high", "low", "close"]] *= 1000
    assert gia.ve_nghin_dong(dong, 1).close.round(6).equals(df.close.round(6))
    assert gia.ve_nghin_dong(dong, None).close.round(6).equals(df.close.round(6))   # tự nhận biết
    assert gia.ve_nghin_dong(df, None).close.equals(df.close)


def test_kiem_tra_hop_le_loai_gia_am():
    df = tao_gia(n=30)
    df.iloc[5, df.columns.get_loc("close")] = -1
    with pytest.raises(ValueError):
        gia.kiem_tra_hop_le(df)


def test_tu_chuyen_nguon_khi_loi(monkeypatch):
    goc = tao_gia(n=100)

    def hong(*a, **k):
        raise ValueError("HTTP 403")

    monkeypatch.setattr(gia, "NGUON_GIA", {"A": (hong, 1000), "B": (lambda *a: _raw(goc), 1000)})
    NHAT_KY.xoa()
    df, nguon = gia.tai_online("XYZ", "2020-01-01", "2030-01-01", thu_tu=["A", "B"])
    assert nguon == "B" and len(df) == 100
    nk = NHAT_KY.bang()
    assert list(nk["Kết quả"]) == ["Lỗi", "OK"]
    tk = NHAT_KY.thong_ke()
    assert tk.loc["A", "Thành công"] == 0 and tk.loc["B", "Thành công"] == 1


def test_tat_ca_nguon_loi_tra_none(monkeypatch):
    monkeypatch.setattr(gia, "NGUON_GIA", {"A": (lambda *a: (_ for _ in ()).throw(ValueError("x")), 1)})
    assert gia.tai_online("XYZ", "2020-01-01", "2030-01-01", thu_tu=["A"]) == (None, None)


def test_doc_csv_tieng_viet(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("Ngày,Giá đóng cửa,Khối lượng\n02/01/2025,\"78,700\",\"1,000\"\n03/01/2025,\"79,100\",\"2,000\"\n",
                 encoding="utf-8")
    df = gia.ve_nghin_dong(gia.chuan_hoa(gia.tu_csv(f)), None)
    assert df.index[0] == pd.Timestamp("2025-01-02")
    assert df.close.iloc[-1] == pytest.approx(79.1)
    assert df.volume.iloc[0] == 1000


def test_cache_chi_tai_bo_sung(tmp_path, monkeypatch):
    goc = tao_gia(n=300)
    goi = []

    def gia_gia(ma, start, end, chi_so=False):
        goi.append(start)
        return _raw(goc[goc.index >= pd.Timestamp(start)])

    monkeypatch.setattr(gia, "NGUON_GIA", {"F": (gia_gia, 1000)})
    monkeypatch.setattr(ch, "THU_TU_NGUON_GIA", ["F"])
    start = str(goc.index[0].date())
    df1 = gia.tai_gia("ABC", start, thu_muc_cache=str(tmp_path))
    df2 = gia.tai_gia("ABC", start, thu_muc_cache=str(tmp_path))
    assert len(df1) == len(df2) == 300
    assert pd.Timestamp(goi[1]) > goc.index[-30]                 # lần 2 chỉ tải ~7 ngày cuối
    assert gia.NGUON_DA_DUNG["ABC"].startswith("cache")


def test_phan_tich_json_yahoo(monkeypatch):
    j = {"chart": {"result": [{"timestamp": [1735776000, 1735862400],
                               "indicators": {"quote": [{"open": [78000, 79000], "high": [79500, 80000],
                                                         "low": [77500, 78500], "close": [79000, None],
                                                         "volume": [1e6, 2e6]}]}}]}}
    monkeypatch.setattr(gia, "lay_json", lambda *a, **k: j)
    df = gia.tu_yahoo("GMD", "2025-01-01", "2025-01-05")
    assert len(df) == 1 and df.close.iloc[0] == 79000                # bỏ nến thiếu giá


def test_phan_tich_json_vci_va_tcbs(monkeypatch):
    vci = [{"t": ["1735776000", "1735862400"], "o": [78000, 79000], "h": [79500, 80000], "l": [77500, 78500],
            "c": [79000, 79500], "v": [1e6, 2e6]}]
    monkeypatch.setattr(gia, "lay_json", lambda *a, **k: vci)
    assert len(gia.tu_vci("GMD", "2025-01-01", "2025-01-05")) == 2
    tcbs = {"data": [{"tradingDate": "2025-01-02T00:00:00", "open": 78000, "high": 79500, "low": 77500,
                      "close": 79000, "volume": 1e6}]}
    monkeypatch.setattr(gia, "lay_json", lambda *a, **k: tcbs)
    assert gia.tu_tcbs("GMD", "2025-01-01", "2025-01-05").close.iloc[0] == 79000


def test_beta_chuoi_giong_het_bang_1():
    df = tao_gia(n=300)
    assert gia.tinh_beta(df, df) == pytest.approx(1.0)
    assert pd.isna(gia.tinh_beta(df, None))
