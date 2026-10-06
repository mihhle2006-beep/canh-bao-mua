# -*- coding: utf-8 -*-
"""Phần J – phân tích chuyên sâu 1 mã (không mạng)."""
import numpy as np
import pandas as pd
import pytest

from ptcp import du_lieu, chuyen_sau
from ptcp import du_lieu_co_ban  # noqa: E402
from ptcp.chi_bao import tinh_chi_bao


def bc(**k):
    d = {"nam": [2025, 2024, 2023, 2022], "doanh_thu": [1500, 1200, 1000, 900], "ln_gop": [450, 340, 270, 230],
         "lnst": [300, 220, 170, 140], "cfo": [350, 250, 200, 150], "cr": [2.2, 2.0, 1.8, 1.6],
         "icr": [12, 10, 9, 8], "de": [0.5, 0.6, 0.7, 0.8], "roe": [24, 22, 21, 20],
         "von_gop": [1000, 1000, 900, 900], "vay_no": [200, 250, 300, 300], "nguon": "TCBS"}
    d.update(k)
    return d


def test_phan_tich_du_5_bang(gia_ngay):
    d = tinh_chi_bao(gia_ngay)
    vni = gia_ngay * 50
    nhom = {"BBB": gia_ngay * 1.1, "CCC": gia_ngay * 0.9}
    tt = {"gt_tb20": 12.3, "beta": 1.1, "von_hoa": 5000.0, "so_huu_nn": 20.0, "nguon_beta": "tự tính"}
    cb = {"P/E": (9.5, "giá ÷ EPS"), "EPS 4 quý (đồng)": (3000.0, "LNST 4 quý ÷ CP"), "ROE %": (18.0, "VNDirect")}
    kq = chuyen_sau.phan_tich("AAA", d, vni, nhom, tt, cb, {}, bc(), {"BBB": bc(roe=[-5, -3, 10]), "CCC": None},
                             "Cảng biển")
    assert set(kq) >= {"J1", "J2", "J3", "J4", "J4_ket_luan", "J5", "fa", "ket_luan"}
    assert kq["J2"].columns.tolist()[:3] == ["Chỉ tiêu (giá trị tiền: tỷ đồng)", "2025", "2024"]
    assert kq["J4"].columns.tolist() == ["Khung", "AAA", "VN-Index", "BBB", "CCC"]
    j5 = kq["J5"].set_index("Tiêu chí")
    assert j5.loc["ROE", "AAA"] == "Rất tốt" and j5.loc["ROE", "BBB"] == "Nguy hiểm"
    assert "CCC" not in j5.columns                                   # không có BCTC → không so sánh
    j3 = kq["J3"].set_index("Chỉ tiêu")
    assert "MA20" in j3.index and not any("Tích lũy" in i or "nến" in i for i in j3.index)   # đã chuyển sang Phần B


def test_ngan_hang_bo_tieu_chi_khong_phu_hop():
    assert chuyen_sau.la_tai_chinh("VCB") and chuyen_sau.la_tai_chinh("XYZ", "Ngân hàng")
    assert not chuyen_sau.la_tai_chinh("GMD", "Cảng biển")


def test_bctc_nam_chon_nguon_day_du_nhat(monkeypatch):
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_BCTC_NAM", [
        ("TCBS", lambda s: (_ for _ in ()).throw(ValueError("HTTP 403"))),
        ("vnstock", lambda s: (_ for _ in ()).throw(SystemExit("Rate limit exceeded."))),   # không được làm dừng
        ("Yahoo", lambda s: bc())])
    kq = du_lieu.lay_bctc_nam("GMD", im_lang=True)
    assert kq["nguon"] == "Yahoo" and kq["roe"][0] == 24


def test_vnstock_systemexit_khong_dung_tai_gia(monkeypatch):
    """vnstock hết lượt (SystemExit) khi tải giá → thử nguồn sau, không dừng chương trình."""
    df = pd.DataFrame({"time": pd.bdate_range("2026-01-01", periods=5), "open": 10.0, "high": 11.0, "low": 9.0,
                       "close": 10.5, "volume": 1e5})
    out = du_lieu.thu_cac_nguon("NGÀY", [("vnstock", lambda: (_ for _ in ()).throw(SystemExit("Rate limit"))),
                                         ("CSV", lambda: df)], im_lang=True)
    assert len(out) == 5


def test_ket_luan_j4():
    j4 = pd.DataFrame({"Khung": ["1 ngày", "1 tuần", "2 tuần", "1 tháng", "3 tháng", "6 tháng", "9 tháng", "1 năm",
                                 "Từ đầu năm"],
                       "DHC": [-0.13, 0.0, 6.71, 7.59, 14.04, 24.81, 29.97, 30.71, 32.11],
                       "VN-Index": [-0.66, -2.66, -4.29, -4.92, -6.89, 2.04, -2.53, 4.64, -2.62],
                       "SGC": [0, 0.09, 2.33, 2.80, 4.64, 37.06, 45.89, 7.23, 35.39],
                       "HHP": [2.29, 1.13, 4.07, 10.15, 31.02, 52.5, 68.69, 92.56, 71.74],
                       "APG": [-1.86, -4.74, -8.26, -14.57, -18.85, -27.24, -59.62, -63.62, -59.62]})
    kl = chuyen_sau.ket_luan_j4("DHC", j4)
    assert "mạnh hơn rõ ở mọi khung" in kl[0] and "1 năm +26.1 điểm %" in kl[0]
    assert "giữ giá tốt" in kl[1]
    assert "xếp 2/4 theo 1 năm" in kl[2] and "HHP" in kl[2]


def test_nen_va_tich_luy_3_nen(gia_ngay):
    x = chuyen_sau.nen_va_tich_luy(gia_ngay, "Ngày")
    assert len(x["mo_hinh"]) == 3 and x["so_nen_tich_luy"] >= 0
    w = chuyen_sau.nen_va_tich_luy(gia_ngay.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min",
                                                                  "close": "last", "volume": "sum"}), "Tuần")
    assert w["mo_hinh"][0][0].startswith("tuần")


def test_ket_luan_chung_phan_j():
    kl = chuyen_sau.ket_luan_chung("DHC", ht=38.0, pe=8.5, pb=1.4, roe=18.0,
                                  fa={"diem": 80.0, "so_nguy_hiem": 0, "tom_tat": ""},
                                  bctc={"nam": [2025, 2024], "lnst": [300.0, 250.0]},
                                  ma={50: (36.0, 35.0), 200: (33.0, 32.5)}, rsi=58.0, rs52=(30.7, 4.6),
                                  kl_bien_dong=["So VN-Index: DHC mạnh hơn rõ ở mọi khung."], khuyen_nghi="CHƯA MUA")
    assert kl["nhan"] == "TÍCH CỰC" and kl["diem"] >= 5
    assert any("P/E 8.5 – rẻ" in x for x in kl["manh"]) and not kl["yeu"]
    assert "Phần C khuyến nghị CHƯA MUA" in kl["goi_y"] and kl["bien_dong"]
    xau = chuyen_sau.ket_luan_chung("XYZ", ht=10.0, pe=-5.0, pb=4.0, roe=-3.0,
                                   fa={"diem": 30.0, "so_nguy_hiem": 3, "tom_tat": "Nguy hiểm: ROE"},
                                   bctc=None, ma={50: (12.0, 12.5), 200: (14.0, 14.1)}, rsi=75.0, rs52=(-40.0, 5.0))
    assert xau["nhan"] == "TIÊU CỰC" and len(xau["yeu"]) >= 5
