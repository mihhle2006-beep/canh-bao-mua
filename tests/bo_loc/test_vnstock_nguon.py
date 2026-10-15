# -*- coding: utf-8 -*-
"""Kiểm thử bộ chuyển đổi vnstock bằng thư viện GIẢ (không cần cài vnstock, không gọi mạng)."""
import importlib.machinery
import sys
import types

import pandas as pd
import pytest

from bo_loc.nguon import vnstock_nguon as vn


def _ky_dong():
    """Kiểu VCI: kỳ theo DÒNG, cột 2 tầng."""
    cot = pd.MultiIndex.from_tuples([("Meta", "yearReport"), ("Meta", "lengthReport"),
                                     ("Chỉ tiêu định giá", "P/E"), ("Chỉ tiêu định giá", "P/B"),
                                     ("Chỉ tiêu định giá", "EPS (VND)"), ("Chỉ tiêu định giá", "Outstanding Share (Mil. Shares)"),
                                     ("Chỉ tiêu khả năng sinh lợi", "ROE (%)"), ("Chỉ tiêu thanh khoản", "Current Ratio")])
    return pd.DataFrame([[2026, 1, 15.0, 2.0, 4800, 414, 0.14, 1.6],
                         [2026, 2, 16.0, 2.1, 5000, 414, 0.15, 1.7]], columns=cot)


def _kd_cot_ky():
    """Kiểu KBS: kỳ theo CỘT, chỉ tiêu theo dòng (đơn vị đồng)."""
    return pd.DataFrame({"item": ["Doanh thu thuần", "Lợi nhuận gộp", "Lợi nhuận sau thuế của cổ đông công ty mẹ"],
                         "2026-Q2": [1.5e12, 4e11, 8e11], "2026-Q1": [1.2e12, 3e11, 4.5e11],
                         "2025-Q4": [1.3e12, 3.2e11, 5e11], "2025-Q3": [1.1e12, 2.8e11, 4.5e11]})


def test_chuan_hoa_bang_hai_kieu():
    a = vn.chuan_hoa_bang(_ky_dong())
    assert a["_ky"].iloc[0] == (2026, 2) and vn.tim_cot(a, "p/e") is not None
    b = vn.chuan_hoa_bang(_kd_cot_ky())
    assert list(b["_ky"]) == [(2026, 2), (2026, 1), (2025, 4), (2025, 3)]
    assert vn.tim_cot(b, "công ty mẹ") is not None


@pytest.fixture
def vnstock_gia(monkeypatch):
    m = types.ModuleType("vnstock")
    m.__spec__ = importlib.machinery.ModuleSpec("vnstock", None)

    class Finance:
        def __init__(self, symbol, source):
            self.source = source

        def ratio(self, period="quarter", **k):
            if self.source == "KBS":
                raise ValueError("KBS lỗi giả lập")
            return _ky_dong()

        def income_statement(self, period="quarter", **k):
            return _kd_cot_ky()

    class Quote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval="1D"):
            return pd.DataFrame({"time": ["2026-10-01", "2026-10-02"], "open": [78.0, 79], "high": [80.0, 81],
                                 "low": [77.0, 78], "close": [79.0, 80], "volume": [1e6, 2e6]})

    m.Finance, m.Quote = Finance, Quote
    monkeypatch.setitem(sys.modules, "vnstock", m)
    return m


def test_co_ban_tu_vnstock(vnstock_gia):
    kq = vn.co_ban("GMD")                                 # KBS lỗi → tự chuyển VCI
    assert not {"pe", "pb", "roe", "eps_ttm", "bvps", "so_cp"} & set(kq)    # chỉ số VCI sai → không lấy
    assert kq["ln_4q_ty"] == pytest.approx(2200)          # 2,2 nghìn tỷ đồng → tỷ (khớp EPS 5.000 ≈ 2.200 tỷ / 414 tr CP)
    assert kq["ky_lnst"] == "Q2/2026+Q1/2026+Q4/2025+Q3/2025" and kq["dt_4q_ty"] == pytest.approx(5100)


def test_gia_tu_vnstock(vnstock_gia):
    df = vn.gia("GMD", "2026-10-01", "2026-10-02")
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"] and len(df) == 2


def test_khong_cai_thi_bao_loi_em(monkeypatch):
    monkeypatch.setattr(vn, "co_vnstock", lambda: False)
    with pytest.raises(ValueError, match="chưa cài"):
        vn.co_ban("GMD")
    monkeypatch.setitem(vn._TRANG_THAI, "da_thu_cai", False)
    assert vn.dam_bao_cai() is False                      # không phải Colab → không tự cài


@pytest.fixture
def sach_han_muc(monkeypatch):
    monkeypatch.setitem(vn._TRANG_THAI, "nghi_den", 0.0)
    monkeypatch.setitem(vn._TRANG_THAI, "da_bao", False)
    vn._MOC_GOI.clear()
    yield
    vn._MOC_GOI.clear()


def test_systemexit_cua_vnstock_thanh_loi_thuong_va_tam_nghi(sach_han_muc):
    def het_luot():
        raise SystemExit("Rate limit exceeded.")
    with pytest.raises(vn.HetLuot):
        vn._goi(het_luot)
    with pytest.raises(vn.HetLuot, match="tạm nghỉ"):                # các lần sau: không gọi vnstock nữa
        vn._goi(lambda: 1)


def test_tu_gioi_han_luot_moi_phut(sach_han_muc, monkeypatch):
    monkeypatch.setattr(vn, "LUOT_MOI_PHUT", 3)
    assert [vn._goi(lambda: i) for i in range(3)] == [0, 1, 2]
    with pytest.raises(vn.HetLuot, match="lượt/phút"):
        vn._goi(lambda: 99)


def test_het_han_muc_chuyen_sang_nguon_khac(sach_han_muc, monkeypatch):
    """vnstock gọi SystemExit giữa chừng → bộ lọc KHÔNG dừng, lấy giá từ nguồn sau."""
    from bo_loc.nguon import gia
    from tests.bo_loc.conftest import tao_gia

    def vnstock_het_luot(*a, **k):
        return vn._goi(lambda: (_ for _ in ()).throw(SystemExit("Rate limit exceeded.")))

    goc = tao_gia(n=60)
    monkeypatch.setattr(gia, "NGUON_GIA", {"vnstock": (vnstock_het_luot, None),
                                           "Yahoo": (lambda *a, **k: goc.reset_index(), 1000)})
    df, nguon = gia.tai_online("GMD", "2025-01-01", "2026-12-31", thu_tu=["vnstock", "Yahoo"])
    assert nguon == "Yahoo" and len(df) == 60


def test_tai_song_song_khong_chet_vi_systemexit():
    from bo_loc.cli import _tai_song_song

    def ham(m):
        if m == "B":
            raise SystemExit("Rate limit exceeded.")
        return m.lower()
    assert _tai_song_song(ham, ["A", "B", "C"], "thử") == {"A": "a", "B": None, "C": "c"}


def test_che_do_cho_thay_vi_doi_nguon(sach_han_muc, monkeypatch):
    ngu = []
    monkeypatch.setattr(vn.time, "sleep", lambda s: ngu.append(s))
    monkeypatch.setattr(vn, "LUOT_MOI_PHUT", 2)
    monkeypatch.setattr(vn, "CHO_KHI_HET_LUOT", True)
    assert [vn._goi(lambda: i) for i in range(3)] == [0, 1, 2]          # lượt 3 không lỗi mà chờ
    assert ngu and 0 < ngu[0] <= 61
    lan = {"n": 0}

    def het_roi_duoc():
        lan["n"] += 1
        if lan["n"] == 1:
            raise SystemExit("Rate limit exceeded.")
        return "ok"
    assert vn._goi(het_roi_duoc) == "ok" and 65 in ngu                 # bị chặn → chờ 65 giây rồi thử lại
