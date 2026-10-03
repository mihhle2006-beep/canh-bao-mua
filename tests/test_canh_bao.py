# -*- coding: utf-8 -*-
"""Kiểm thử không cần mạng: python -m pytest -q"""
import os
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chay  # noqa: E402
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import danh_gia, du_lieu, thong_bao, tieu_chi  # noqa: E402

BAY_GIO = pd.Timestamp("2026-10-02 10:50")          # thứ Sáu, trong phiên sáng
PT_TOT = {"ngay_du_lieu": "2026-10-01", "khuyen_nghi": "MUA TỪNG PHẦN", "hanh_dong": "", "ev": 2.5,
          "xs_muc_tieu": 55.0, "xs_cat_lo": 30.0, "cat_lo": None, "muc_tieu": None, "chan_su_kien": False,
          "su_kien": [], "canh_bao_su_kien": [], "vni_xau": False, "rs_yeu": False, "he_so": 1.0}


def _ohlcv(idx, c, kl=2e6, seed=0):
    rng = np.random.default_rng(seed)
    c = np.asarray(c, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + rng.uniform(0, .004, len(c))),
                         "low": np.minimum(o, c) * (1 - rng.uniform(0, .004, len(c))), "close": c,
                         "volume": np.full(len(c), kl)}, index=idx)


def ngay_tang(n=900, seed=4):
    """Tăng tốc 80 phiên cuối, nghỉ 4 phiên rồi bật lên → tuần & ngày đều đạt (dữ liệu tất định theo seed)."""
    idx = pd.bdate_range(end=BAY_GIO.normalize(), periods=n)
    rng = np.random.default_rng(seed)
    r = 0.0008 + 0.01 * rng.standard_normal(n)
    r[-80:] = 0.003 + 0.012 * rng.standard_normal(80)
    r[-8:-4] = -0.003
    r[-4:] = 0.008
    return _ohlcv(idx, 30 * np.exp(np.cumsum(r)), kl=3e6, seed=seed)


def ngay_giam(n=900, seed=2):
    """Giảm ngày càng mạnh 150 phiên cuối → MACD tuần dưới Signal."""
    idx = pd.bdate_range(end=BAY_GIO.normalize(), periods=n)
    r = 0.0005 + 0.004 * np.random.default_rng(seed).standard_normal(n)
    r[-150:] = -0.004 + 0.003 * np.random.default_rng(seed + 1).standard_normal(150)
    return _ohlcv(idx, 60 * np.exp(np.cumsum(r)), seed=seed)


def phien(ngay, phut):
    """Các mốc nến trong phiên (giờ VN) của 1 ngày, khung 'phut' phút."""
    out = []
    for bd, kt in C.PHIEN:
        t, het = ngay + pd.Timedelta(bd + ":00"), ngay + pd.Timedelta(kt + ":00")
        while t < het:
            out.append(t)
            t += pd.Timedelta(minutes=phut)
    return out


def trong_ngay(phut, so_ngay, gia_cuoi, den=BAY_GIO, tang_cuoi=True):
    ngay = pd.bdate_range(end=den.normalize(), periods=so_ngay)
    idx = [t for d in ngay for t in phien(d, phut) if t + pd.Timedelta(minutes=phut) <= den or d < den.normalize()]
    n = len(idx)
    c = gia_cuoi * np.exp(np.linspace(-0.04, 0, n))
    if tang_cuoi:                                                       # giảm nhẹ rồi bật mạnh 2 nến cuối
        c[-25:-2] = c[-26] * np.exp(np.linspace(0, -0.02, 23))
        c[-2:] = c[-3] * np.array([1.004, 1.012])
    df = _ohlcv(pd.DatetimeIndex(idx), c, kl=2e5)
    df.iloc[-1, df.columns.get_loc("volume")] = 6e5
    return df


@pytest.fixture
def du_lieu_tot():
    dn = ngay_tang()
    g = float(dn.close.iloc[-1])
    vni = _ohlcv(pd.bdate_range(end=BAY_GIO.normalize(), periods=900),
                 1000 * np.exp(np.linspace(0, 0.3, 900)), kl=1e9)
    return dn, trong_ngay(60, 120, g), trong_ngay(int(C.KHUNG_PHUT), 25, g), vni


# ------------------------------------------------------------------ dữ liệu / nến
def test_bo_nen_chua_dong():
    idx = pd.DatetimeIndex(["2026-10-02 10:15", "2026-10-02 10:30"])
    df = _ohlcv(idx, [10, 11])
    assert len(du_lieu.bo_nen_chua_dong(df, "15", "2026-10-02 10:40")) == 1          # nến 10:30 chưa đóng
    assert len(du_lieu.bo_nen_chua_dong(df, "15", "2026-10-02 10:46")) == 2
    h = _ohlcv(pd.DatetimeIndex(["2026-10-02 10:00", "2026-10-02 11:00"]), [10, 11])
    assert len(du_lieu.bo_nen_chua_dong(h, "60", "2026-10-02 11:35")) == 2           # đóng lúc nghỉ trưa 11:30


def test_tuan_bo_tuan_dang_chay():
    dn = ngay_tang()
    assert du_lieu.gop_tuan(dn, "2026-10-01 10:00").index[-1] < pd.Timestamp("2026-10-02")
    assert du_lieu.gop_tuan(dn, "2026-10-02 15:30").index[-1] == pd.Timestamp("2026-10-02")


def test_trong_phien():
    assert du_lieu.trong_phien("2026-10-02 10:00") and du_lieu.trong_phien("2026-10-02 14:30")
    assert not du_lieu.trong_phien("2026-10-02 12:00") and not du_lieu.trong_phien("2026-10-03 10:00")


# ------------------------------------------------------------------ tiêu chí từng khung
def test_khung_tuan_va_ngay():
    assert tieu_chi.khung_tuan(du_lieu.gop_tuan(ngay_tang(), BAY_GIO))["dat"]
    assert not tieu_chi.khung_tuan(du_lieu.gop_tuan(ngay_giam(), BAY_GIO))["dat"]
    kn = tieu_chi.khung_ngay(ngay_tang())
    assert kn["dat"], kn["truot"]
    assert not tieu_chi.khung_ngay(ngay_giam())["dat"]
    ten = [m["ten"] for m in kn["muc"]]
    assert any("SuperTrend" in t for t in ten) and any("GTGD" in t for t in ten)


def test_khung_gio_phut(du_lieu_tot):
    _, dh, dp, _ = du_lieu_tot
    assert tieu_chi.khung_gio(dh)["dat"]
    kp = tieu_chi.khung_phut(dp)
    assert kp["dat"], kp["truot"]
    assert "phá đỉnh" in kp["kich_hoat"] or "cắt lên" in kp["kich_hoat"]


def test_muc_gia(du_lieu_tot):
    kn = tieu_chi.khung_ngay(du_lieu_tot[0])
    lo, mt, nguon, rr = tieu_chi.muc_gia(kn)
    assert lo < kn["gia"] < mt and kn["gia"] - lo >= C.STOP_ATR_MIN * kn["atr"] - 1e-9 and rr > 0


# ------------------------------------------------------------------ ghép trạng thái
def test_mua_ngay_khi_du_4_khung(du_lieu_tot):
    dn, dh, dp, vni = du_lieu_tot
    tt = tieu_chi.thi_truong(vni, BAY_GIO)
    with mock.patch.object(C, "RR_TOI_THIEU", 0.1):
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, BAY_GIO)
        assert kq["trang_thai"] == "MUA NGAY", kq["ly_do"]
        kq2 = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, "2026-10-02 15:30")
        assert kq2["trang_thai"] == "ĐẠT CUỐI PHIÊN"


def test_tuan_phu_quyet():
    dn = ngay_giam()
    g = float(dn.close.iloc[-1])
    kq = danh_gia.phan_tich_ma("BBB", dn, trong_ngay(60, 120, g), trong_ngay(15, 25, g), None,
                               {"tot": None, "nhan": ""}, BAY_GIO)
    assert kq["trang_thai"] == "ĐỨNG NGOÀI" and not kq["mua_ngay"]


def test_rr_thap_khong_mua(du_lieu_tot):
    dn, dh, dp, vni = du_lieu_tot
    with mock.patch.object(C, "RR_TOI_THIEU", 99):
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, {"tot": True, "nhan": ""}, BAY_GIO)
    assert kq["trang_thai"].startswith("ĐỦ TÍN HIỆU – R/R")


# ------------------------------------------------------------------ thông báo
def test_chong_bao_trung():
    st = {}
    assert thong_bao.can_bao("AAA", True, "2026-10-02 10:00", st)
    assert not thong_bao.can_bao("AAA", True, "2026-10-02 10:15", st)          # vẫn đạt → không báo lại
    assert not thong_bao.can_bao("AAA", False, "2026-10-02 10:30", st)
    assert thong_bao.can_bao("AAA", True, "2026-10-02 10:45", st)               # mất rồi đạt lại → báo
    assert thong_bao.can_bao("AAA", True, "2026-10-05 09:15", st)               # ngày mới → báo


def test_chay_mo_phong(du_lieu_tot, tmp_path, capsys):
    dn, dh, dp, vni = du_lieu_tot
    os.chdir(tmp_path)

    def tai_gia(ma, khung="D", *a, **k):
        if ma == "VNINDEX":
            return vni
        return {"D": dn, "60": dh}.get(khung, dp)
    with mock.patch.object(chay, "tai", side_effect=tai_gia), mock.patch.object(C, "RR_TOI_THIEU", 0.1), \
            mock.patch.object(chay, "phan_tich_ngay", return_value=PT_TOT), mock.patch.object(chay, "gui") as g:
        assert chay.main(["--ma", "AAA", "--gio", "2026-10-02 10:50"]) == 0
        assert g.call_count == 1 and "MUA NGAY – AAA" in g.call_args[0][0]
        chay.main(["--ma", "AAA", "--gio", "2026-10-02 10:50"])                 # chạy lại: không báo trùng
        assert g.call_count == 1
        chay.main(["--ma", "AAA", "--gio", "2026-10-02 15:30"])                 # tổng kết
        assert g.call_count == 2 and "TỔNG KẾT" in g.call_args[0][0]
    assert os.path.exists("lich_su_tin_hieu.csv")
    assert chay.main(["--gio", "2026-10-02 12:00"]) == 0                       # nghỉ trưa → không làm gì


# ------------------------------------------------------------------ phần lấy từ bộ ptcp
def test_cong_ptcp(du_lieu_tot):
    dn, dh, dp, vni = du_lieu_tot
    tt = {"tot": True, "nhan": ""}
    with mock.patch.object(C, "RR_TOI_THIEU", 0.1):
        g = float(dp.close.iloc[-1])
        pt = dict(PT_TOT, cat_lo=g * 0.93, muc_tieu=g * 1.2, moc_muc_tieu="Đỉnh cũ", atr=g * 0.02)
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, BAY_GIO, pt)
        assert kq["trang_thai"] == "MUA NGAY"
        assert kq["cat_lo"] == pytest.approx(g * 0.93) and kq["muc_tieu"] == pytest.approx(g * 1.2)
        assert "ptcp" in kq["nguon_mt"] and "ptcp (2026-10-01): MUA TỪNG PHẦN" in thong_bao.tin_mua_ngay(kq, BAY_GIO)
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, BAY_GIO, dict(pt, ev=-0.5))
        assert kq["trang_thai"] == "ĐỦ TÍN HIỆU – EV THẤP"
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, BAY_GIO,
                                   dict(pt, chan_su_kien=True, su_kien=["Công bố KQKD 06/10/2026 (còn 2 phiên)"]))
        assert kq["trang_thai"] == "CHỜ SAU SỰ KIỆN"
        with mock.patch.object(C, "YEU_CAU_PTCP_MUA", True):
            kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, tt, BAY_GIO, dict(pt, khuyen_nghi="CHƯA MUA"))
            assert kq["trang_thai"] == "ĐỦ TÍN HIỆU – ptcp CHƯA MUA"


def test_ptcp_that_va_cache(tmp_path, monkeypatch):
    """Chạy ĐÚNG ptcp.main trên dữ liệu CSV giả lập; lần 2 đọc cache."""
    monkeypatch.chdir(tmp_path)
    from canh_bao import ptcp_ngay
    dn = ngay_tang()
    dn.rename_axis("date").reset_index().to_csv("aaa.csv", index=False)
    v = _ohlcv(dn.index, 1000 * np.exp(np.linspace(0, 0.3, len(dn))), kl=1e9)
    v.rename_axis("date").reset_index().to_csv("vni.csv", index=False)
    pt = ptcp_ngay.phan_tich_ngay("AAA", BAY_GIO, csv_ngay="aaa.csv", csv_vni="vni.csv", san="HOSE")
    assert pt and pt["khuyen_nghi"] and pt["cat_lo"] < pt["gia"] and "ev" in pt
    assert [k["ten"] for k in pt["kich_ban"]] == ["TÍCH CỰC", "CƠ SỞ", "TIÊU CỰC"]
    assert sum(k["xs"] for k in pt["kich_ban"]) == pytest.approx(100, abs=1)
    with mock.patch("ptcp.main", side_effect=AssertionError("không được gọi lại")):
        assert ptcp_ngay.phan_tich_ngay("AAA", BAY_GIO) == pt


def test_xac_suat_va_kich_ban(du_lieu_tot):
    dn, dh, dp, vni = du_lieu_tot
    g = float(dp.close.iloc[-1])
    kb = [{"ten": "TÍCH CỰC", "gia": g * 1.15, "xs": 30.0, "phien": 20, "dieu_kien": "vượt đỉnh", "chi_tiet": []},
          {"ten": "CƠ SỞ", "gia": g * 1.05, "xs": 25.0, "phien": 30, "dieu_kien": "",
           "chi_tiet": ["đạt MT cơ sở 15%", "đi ngang 10%"]},
          {"ten": "TIÊU CỰC", "gia": g * 0.9, "xs": 45.0, "phien": 10, "dieu_kien": "thủng cắt lỗ", "chi_tiet": []}]
    pt = dict(PT_TOT, cat_lo=g * 0.93, muc_tieu=g * 1.2, moc_muc_tieu="Đỉnh cũ", atr=g * 0.02, kich_ban=kb)
    with mock.patch.object(C, "RR_TOI_THIEU", 0.1):
        kq = danh_gia.phan_tich_ma("AAA", dn, dh, dp, vni, {"tot": True, "nhan": ""}, BAY_GIO, pt)
    x = kq["xac_suat"]
    assert x and x["muc_tieu"] + x["cat_lo"] + x["ngang"] == pytest.approx(100)
    tin = thong_bao.tin_mua_ngay(kq, BAY_GIO)
    for chu in ("🎯 Mục tiêu", "Chạm MỤC TIÊU trước", "Chạm CẮT LỖ trước", "3 kịch bản", "🟢 TÍCH CỰC", "🔴 TIÊU CỰC"):
        assert chu in tin
    assert "Chạm MỤC TIÊU trước" in thong_bao.tin_tong_ket([kq], {"nhan": "VN-Index"}, BAY_GIO)
