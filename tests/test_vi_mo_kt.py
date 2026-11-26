# -*- coding: utf-8 -*-
"""Vĩ mô theo chủ đề (thi_truong/vi_mo_kt): kỳ trước / cùng kỳ, lũy kế năm, ghi chú, nhịp kinh tế, lịch, nối CPI – không mạng."""
import numpy as np
import pandas as pd

from thi_truong import vi_mo_kt as KT

SPEC = {x[0]: x for x in KT.CHI_TIEU}


def _thang(vals, tu="2024-01-01"):
    return pd.Series(vals, index=pd.date_range(tu, periods=len(vals), freq="MS"), dtype=float)


def test_so_vn_va_nhan_ky():
    assert KT.so_vn(1234.5, 2) == "1.234,50" and KT.so_vn(None) == "–"
    assert KT.nhan_ky("2026-09-01", "Q") == "Q3/2026" and KT.nhan_ky("2026-10-01", "M") == "T10/2026"
    assert KT.nhan_ky("2026-10-01", "M", luy_ke=True) == "10T/2026" and KT.nhan_ky("2025-12-31", "Y") == "2025"


def test_chi_tieu_thang_ky_truoc_cung_ky_va_tb12():
    s = _thang([4.0 + i * 0.1 for i in range(24)])                # 2024-01 … 2025-12
    r = KT.chi_tieu(SPEC["vn_cpi_loi"], s, "nguồn", "2026-01-10")
    assert r["ky"] == "T12/2025" and r["gt"] == 6.3 and r["kt"] == 0.1 and r["ck"] == 1.2
    assert r["ghi"].startswith("Trên TB 12 tháng") and r["tot"] == -1        # lạm phát lõi tăng là xấu
    assert len(r["sp"]) == 24 and r["cu"] is False and r["kieu"] == "pt"


def test_muc_tieu_gdp_cpi():
    q = pd.Series([8.0, 9.95], index=pd.to_datetime(["2026-06-01", "2026-09-01"]))
    g = KT.chi_tieu(SPEC["vn_gdp"], q, "", "2026-11-26")
    assert g["ghi"] == "Dưới mục tiêu 10%" and g["tot"] == -1 and g["ky"] == "Q3/2026"
    c = KT.chi_tieu(SPEC["vn_cpi"], _thang([4.0, 5.09], "2026-09-01"), "", "2026-11-26")
    assert c["ghi"] == "Vượt mục tiêu 4,5%" and c["tot"] == -1


def test_luy_ke_nam_fdi():
    # cộng dồn từ đầu năm: tháng 1 tụt về đầu kỳ – kỳ trước bỏ, cùng kỳ theo tháng
    s = _thang([2.0 * m for m in range(1, 13)] + [1.5 * m for m in range(1, 11)], "2025-01-01")
    r = KT.chi_tieu(SPEC["vn_fdi"], s, "", "2026-11-26")
    assert r["ky"] == "10T/2026" and r["ck"] == round((15.0 / 20.0 - 1) * 100, 2) and r["ghi"].startswith("T10: 1,50")
    j = KT.chi_tieu(SPEC["vn_fdi"], s.loc[:"2026-01-01"], "", "2026-02-20")
    assert j["kt"] is None and j["ghi"].startswith("T1: 1,50")


def test_can_can_thuong_mai_chuoi_xuat_sieu():
    r = KT.chi_tieu(SPEC["vn_bot"], _thang([-1.0, 0.5, 1.2, 3.0]), "", "2024-05-10")
    assert r["ghi"] == "Xuất siêu · 3 tháng" and r["kieu"] == "d" and r["kt"] == 1.8


def test_chuoi_ngay_va_cung_ky():
    idx = pd.bdate_range("2024-01-01", "2026-11-25")
    s = pd.Series(np.linspace(24000, 26000, len(idx)), idx)
    r = KT.chi_tieu(SPEC["usdvnd"], s, "", "2026-11-26")
    assert r["ky"] == "25/11/2026" and r["ghi"].startswith("1 năm:") and 50 <= len(r["sp"]) <= 54
    q = s[s.index <= pd.Timestamp("2025-11-25")].iloc[-1]
    assert r["ck"] == round((s.iloc[-1] / q - 1) * 100, 2)


def test_so_cung_ky_theo_ngay():
    s = _thang([100.0 + i for i in range(30)])
    y = KT.so_cung_ky_pt(s)
    assert y.index[0] == pd.Timestamp("2025-01-01") and abs(y.iloc[0] - 12.0) < 1e-9


def test_mo_rong_cpi_noi_thang_moi_khi_kiem_khop():
    th = pd.date_range("2023-01-01", "2026-10-01", freq="MS")
    rng = np.random.default_rng(1)
    mm = pd.Series(rng.normal(0.3, 0.3, len(th)).round(2), th)
    lv = (1 + mm / 100).cumprod()
    yy_day = ((lv / lv.shift(12) - 1) * 100).dropna()
    yy = yy_day.iloc[:-1].round(2)                                 # tháng cuối chưa có (TradingView trễ 1 tháng)
    out, n, lech = KT.mo_rong_cpi(yy, mm)
    assert n == 1 and lech is not None and lech <= 0.1 and abs(out.iloc[-1] - yy_day.iloc[-1]) < 0.05
    sai = yy.copy()
    sai.iloc[-3] += 1.0                                            # nguồn lệch → không nối
    assert KT.mo_rong_cpi(sai, mm)[1] == 0


def test_nhip_muc_theo_huong():
    th = pd.date_range("2019-01-01", "2026-10-01", freq="MS")
    on = pd.Series(5.0 + np.sin(np.arange(len(th))), th)
    tang = on.copy()
    tang.iloc[-1] = 20.0                                           # lạm phát vọt → "xấu hơn nhiều"; SXCN vọt → "tốt hơn nhiều"
    kq = KT.nhip({"vn_cpi": tang, "vn_sxcn": tang})
    d = {x["k"]: x for x in kq["dong"]}
    assert len(kq["thang"]) == 18 and kq["thang"][-1] == "2026-10"
    assert d["vn_cpi"]["o"][-1] == -2 and d["vn_sxcn"]["o"][-1] == 2


def test_lich_cong_bo():
    l = KT.lich("2026-11-26", so=10)
    ten = [(x["ngay"], x["ten"]) for x in l]
    assert ("2026-12-06", "Số liệu T11/2026") in ten and ("2026-12-09", "Fed công bố lãi suất (FOMC)") in ten
    assert ("2027-01-06", "GDP Q4/2026") in ten and l == sorted(l, key=lambda x: x["ngay"])
    assert next(x for x in l if x["ngay"] == "2026-12-06")["thu"] == "CN"


def test_vua_co_so_chi_tinh_ky_moi():
    hang = [{"k": "vn_cpi", "ts": "M", "ky": "T10/2026", "ten": "Lạm phát", "gt": 5.09, "le": 2, "dv": "%"},
            {"k": "vn_sxcn", "ts": "M", "ky": "T10/2026", "ten": "SXCN", "gt": 15.0, "le": 2, "dv": "%"}]
    dem, vua = KT.vua_co_so({}, hang, "2026-11-26")
    assert vua == [] and dem["vn_cpi"]["thay"] == ""              # lần đầu không tính
    cu = {"vn_cpi": {"ky": "T9/2026", "thay": "2026-10-20"}, "vn_sxcn": {"ky": "T10/2026", "thay": "2026-11-06"}}
    dem, vua = KT.vua_co_so(cu, hang, "2026-11-26")
    assert [v["k"] for v in vua] == ["vn_cpi"] and dem["vn_cpi"]["thay"] == "2026-11-26" and vua[0]["gt"] == "5,09%"


def test_dung_kt_day_du():
    th = pd.date_range("2019-01-01", "2026-10-01", freq="MS")
    ch = {"vn_cpi": pd.Series(4.0 + 0.01 * np.arange(len(th)), th),
          "vn_bot": pd.Series(np.r_[np.full(len(th) - 1, 1e9), 7.31e9], th),
          "vn_fdi": pd.Series([d.month * 2.4e9 for d in th], th),
          "vn_gdp": pd.Series([6.0, 9.95], index=pd.to_datetime(["2025-09-01", "2026-09-01"])),
          "us_gdp": pd.Series([2.0, 2.1], index=pd.to_datetime(["2026-06-01", "2026-09-01"]))}
    kt, ls, dem = KT.dung_kt(ch, {"vn_cpi": "nguồn CPI"}, pd.Timestamp("2026-11-26"), {})
    h = {r["k"]: r for r in kt["ct"]}
    assert h["vn_bot"]["gt"] == 7.31 and h["vn_bot"]["dv"] == "tỷ USD"       # chia đơn vị
    assert kt["tq"][:2] == ["vn_gdp", "vn_cpi"] and {c["k"] for c in kt["chu_de"]} >= {"tq", "gia", "the_gioi", "hh"}
    chu = "".join(t for t, _ in kt["diem_nhan"])
    assert "Lạm phát 4,93%" in chu and "Xuất siêu" in chu and "lớn nhất" in chu and "GDP Q3/2026" in chu
    assert any(m["tieu"] == "Giá cả" for m in kt["ban_tin"]["muc"]) and set(ls) == set(h)
    assert all(ls[k][i][0] < ls[k][i + 1][0] for k in ls for i in range(len(ls[k]) - 1))
