# -*- coding: utf-8 -*-
"""Tab Vĩ mô (Bảng thị trường): dựng JSON từ chuỗi giả – không mạng."""
from datetime import datetime

import numpy as np
import pandas as pd

from thi_truong import vi_mo_web as V


def _gia(n, g0, tu="2019-01-01", seed=0, f="B"):     # 2000 phiên từ 2019 → cuối ~ 08/2026
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
         "vn_10n": _gia(2000, 3.0, seed=3), "us_10n": _gia(2000, 4.0, seed=4), "us_thuc10": _gia(2000, 1.5, seed=5),
         "hh_bac": _gia(2000, 20.0, seed=6), "hh_brent": _gia(2000, 80.0, seed=7), "hh_wti": _gia(2000, 75.0, seed=8),
         "hh_dong": _gia(2000, 4.0, seed=9), "hh_cao_su": _gia(2000, 170.0, seed=10),
         "hh_than": _gia(300, 100.0, tu="2024-01-01", seed=11),                       # nguồn ngừng cập nhật → "cu"
         "vn_gdp": pd.Series([6.9, 7.1, 8.2], index=pd.to_datetime(["2026-03-01", "2026-06-01", "2026-09-01"])),
         "vn_xk": pd.Series([3.5e10, 3.7e10], index=pd.to_datetime(["2026-09-01", "2026-10-01"])),
         "vn_fdi": pd.Series([2.13e10, 2.36e10, 2.762e10, 1.68e9, 2.107e10, 2.408e10],          # cộng dồn năm: tụt về tháng 1
                             index=pd.to_datetime(["2025-10-01", "2025-11-01", "2025-12-01", "2026-01-01", "2026-09-01",
                                                   "2026-10-01"])),
         "us_cpi": pd.Series([3.0, 3.2, 2.9], index=pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01"])),
         "us_vix": _gia(2000, 18.0, seed=12)}
    N = {"xau": "Stooq", "sjc": "vang.today", "vn_10n": "HNX từ 2014", "hh_bac": "TradingView OANDA:XAGUSD"}
    th = pd.date_range("2018-01-01", "2026-10-01", freq="MS")
    rng = np.random.default_rng(42)
    for k, mu in (("vn_cpi", 3.5), ("vn_cpi_loi", 3.0), ("vn_sxcn", 8.0), ("vn_banle", 9.0), ("vn_lnh", 4.0), ("vn_dh", 4.5)):
        S["kt_" + k] = pd.Series(mu + rng.normal(0, 1, len(th)).cumsum() * 0.2, th)
    for k, mu in (("vn_xk", 35e9), ("vn_khach", 1.2e6), ("vn_dtnh", 85e9)):
        S["kt_" + k] = pd.Series(mu * (1 + rng.normal(0, 0.05, len(th)).cumsum() * 0.1), th)
    S["kt_vn_bot"] = pd.Series(rng.normal(1e9, 2e9, len(th)), th)
    S["kt_vn_fdi"] = pd.Series([d.month * 2.2e9 for d in th], th)
    q = pd.date_range("2018-03-01", "2026-09-01", freq="3MS")
    S["kt_vn_gdp"] = pd.Series(6.5 + rng.normal(0, 0.5, len(q)), q)
    S["kt_us_gdp"] = pd.Series(2.0 + rng.normal(0, 0.5, len(q)), q)
    S["kt_vn_10n"] = S["vn_10n"]
    S["kt_usdvnd"] = S["usdvnd"]
    S["kt_vn_gdp_usd"] = pd.Series([3e11 + i * 2e10 for i in range(10)], pd.date_range("2016-12-31", periods=10, freq="YE"))
    for k in [x for x in S if x.startswith("kt_")]:
        N[k] = "nguồn mẫu"
    P = {"gia_ngay": 3600.0, "gia_ngay_luc": datetime(2026, 11, 25, 21, 50, tzinfo=V.VN), "so_cheo": {"bac": (700, 0.95, 1.0)},
         "vcb": {"mua": 25610.0, "ck": 25640.0, "ban": 26020.0},
         "song": {"url": "https://api.gold-api.com/price/XAU", "kieu": "gold_api", "gia": 3600.0},
         "tin": [{"t": "NHNN giữ nguyên lãi suất điều hành", "u": "https://cafef.vn/a.chn", "d": "2026-11-25 10:15"}],
         "nso_moi": {"u": "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-thang-muoi/", "ky": "2026-10"}}
    S["td_tang"] = pd.Series([9.0, 10.19], index=pd.to_datetime(["2026-07-01", "2026-08-01"]))
    S["nso_vang_yoy"] = pd.Series([40.0, 48.3], index=pd.to_datetime(["2026-09-01", "2026-10-01"]))
    S["kt_vn_tin_dung"], S["kt_vn_vang_cs"] = S["td_tang"], S["nso_vang_yoy"]
    N["kt_vn_tin_dung"] = N["kt_vn_vang_cs"] = "nguồn mẫu"
    return S, N, P


def test_dung_json_the_chuoi_nen():
    S, N, P = _mau()
    kq = V.dung(S, N, P, bay_gio=datetime(2026, 11, 25, 22, 0, tzinfo=V.VN))
    the = {t["k"]: t for t in kq["the"]}
    assert the["xau"]["gia"] == 3600.0 and the["xau"]["luc"] == "21:50 25/11"          # giá ngay trên thẻ
    c = S["xau_nen"]["close"]                                                          # % theo chuỗi ngày, không trộn giá ngay
    assert the["xau"]["doi"] == round((c.iloc[-1] / c.iloc[-2] - 1) * 100, 2)
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


def test_hang_hoa_bang_the_va_chuoi():
    S, N, P = _mau()
    cuoi = S["hh_bac"].index[-1] + pd.Timedelta(days=2)                               # "hôm nay" = 2 ngày sau giá cuối
    kq = V.dung(S, N, P, bay_gio=datetime(cuoi.year, cuoi.month, cuoi.day, 22, 0, tzinfo=V.VN))
    bang = {r["k"]: r for r in kq["hang_hoa"]}
    assert list(bang) == [k for k, *_ in V.HANG_HOA if "hh_" + k in S]                 # đúng thứ tự HANG_HOA
    b = bang["bac"]
    x = S["hh_bac"]
    assert b["gia"] == round(x.iloc[-1], 3 if x.iloc[-1] < 20 else 2) and b["d1"] == round((x.iloc[-1] / x.iloc[-2] - 1) * 100, 2)
    d = x.index[-1]
    assert b["y1"] == round((x.iloc[-1] / x[x.index <= d - pd.DateOffset(years=1)].iloc[-1] - 1) * 100, 2)
    assert b["ytd"] == round((x.iloc[-1] / x[x.index <= pd.Timestamp(d.year - 1, 12, 31)].iloc[-1] - 1) * 100, 2)
    assert b["cheo"] == [700, 0.95, 1.0] and b["nguon"] == "TradingView OANDA:XAGUSD" and b["nhom"] == "kl"
    assert bang["than"]["cu"] is True and bang["bac"]["cu"] is False
    assert "PLX" in bang["brent"]["lq"] and kq["nhom_hh"]["nl"] == "Năng lượng"
    the = {t["k"]: t for t in kq["the"]}
    assert the["bac"]["nhom"] == "hh" and the["brent"]["nhom"] == "hh" and "bac" not in kq["chuoi"]   # chuỗi chỉ ở hang_hoa.json
    assert set(kq["hh_chuoi"]) == set(bang)
    for c in kq["hh_chuoi"].values():
        ng = [r[0] for r in c]
        assert ng == sorted(ng) and len(set(ng)) == len(ng)
    assert the["vn_gdp"]["gia"] == 8.2 and the["vn_gdp"]["doi"] == 1.1 and the["vn_gdp"]["ky"] == "quý trước"
    assert the["vn_gdp"]["ky_so"] == "quý 3/2026" and the["us_cpi"]["ky_so"] == "tháng 10/2026" and "ky_so" not in the["bac"]
    assert the["vn_xk"]["gia"] == 37.0 and the["vn_xk"]["dv"] == "tỷ USD"                # USD → tỷ USD
    assert the["us_cpi"]["doi"] == -0.3 and the["us_cpi"]["kieu_doi"] == "đ"
    assert the["vn_fdi"]["ky"] == "cùng kỳ năm trước" and the["vn_fdi"]["doi"] == round((24.08 / 21.3 - 1) * 100, 2)   # 10/2026 vs 10/2025
    assert the["vn_fdi"]["ky_so"] == "tháng 10/2026"


def test_bien_dong_moc_va_thieu():
    s = pd.Series([100.0, 110.0], index=pd.to_datetime(["2026-11-24", "2026-11-25"]))
    r = V.bien_dong(s)
    assert r["d1"] == 10.0 and r["m1"] is None and r["y1"] is None and r["ngay"] == "2026-11-25"
    assert V.bien_dong(s.iloc[:1])["d1"] is None


def test_so_cheo_hai_nguon():
    a = _gia(800, 100.0, seed=1)
    m, tq, lech = V.so_cheo(a, a * 1.01)
    assert m >= 700 and tq == 1.0 and abs(lech - 0.99) < 0.02
    assert V.so_cheo(a.iloc[:10], a.iloc[:10])[1] is None


def test_ngay_nen_tradingview_theo_phien():
    """Nến ngày TradingView đánh dấu GIỜ MỞ phiên (UTC) → ngày giao dịch (lai_suat.TV_BU_GIO, kiểm vi_mo_nguon 25/11/2026)."""
    from thi_truong import lai_suat as LS

    def tho(*ts):
        return "".join('{"i":%d,"v":[%s,1,2,0.5,%d]}' % (i, pd.Timestamp(t, tz="UTC").timestamp(), i + 1) for i, t in enumerate(ts))
    for mo, ngay in [("2026-11-24 22:00", "2026-11-25"),          # vàng / dầu / CME mở tối hôm trước
                     ("2026-11-24 21:00", "2026-11-25"),          # OANDA giờ hè
                     ("2026-11-24 10:15", "2026-11-25"),          # SGX phiên T+1
                     ("2026-11-24 12:00", "2026-11-25"),          # SGX quặng sắt
                     ("2026-11-25 08:00", "2026-11-25"),          # London
                     ("2026-11-25 00:00", "2026-11-25")]:         # BTC / ECONOMICS
        d, loi = LS.doc_nen(tho(mo))
        assert loi == "" and f"{d.index[0]:%Y-%m-%d}" == ngay, mo
    d, _ = LS.doc_nen(tho("2026-09-01 00:00", "2026-09-30 22:00"), thang=True)         # tháng → ngày 1
    assert list(d.index) == [pd.Timestamp("2026-09-01"), pd.Timestamp("2026-10-01")]
    d, _ = LS.doc_nen(tho("2026-11-24 22:00"), giu_gio=True)                           # nến giờ giữ mốc UTC
    assert d.index[0] == pd.Timestamp("2026-11-24 22:00")


def test_yahoo_ngay_theo_gio_san(monkeypatch):
    """VND=X (múi London): nửa đêm giờ hè = 23 h UTC hôm trước – ngày phải theo giờ sàn, không lùi 1 ngày."""
    import sys
    import types
    idx = pd.DatetimeIndex(["2026-07-01 00:00", "2026-07-02 00:00"]).tz_localize("Europe/London")
    df = pd.DataFrame({"Open": [1.0, 2.0], "High": [1.0, 2.0], "Low": [1.0, 2.0], "Close": [1.0, 2.0]}, index=idx)
    gia = types.SimpleNamespace(Ticker=lambda ma: types.SimpleNamespace(history=lambda **k: df.copy()))
    monkeypatch.setitem(sys.modules, "yfinance", gia)
    assert [f"{d:%Y-%m-%d}" for d in V._yf("VND=X").index] == ["2026-07-01", "2026-07-02"]
    assert V._yf("VND=X", khung="60m", ky="1mo").index[0] == pd.Timestamp("2026-06-30 23:00")


def test_noi_nso_chi_them_thang_moi_cho_xuat_nhap_khau(capsys):
    th = pd.date_range("2026-01-01", "2026-07-01", freq="MS")
    S = {"kt_vn_xk": pd.Series(40e9, th), "kt_vn_nk": pd.Series(38e9, th), "kt_vn_cpi": pd.Series(4.0, th),
         "kt_vn_bot": pd.Series(2e9, th)}
    N = {"kt_vn_xk": "TradingView"}
    df = pd.DataFrame({"xk": [41.0, 50.0, 52.0], "nk": [39.0, 45.0, float("nan")], "cpi_yoy": [4.01, 4.5, 4.6],
                       "can_can": [2.0, 5.0, float("nan")]},
                      index=pd.to_datetime(["2026-07-01", "2026-08-01", "2026-09-01"]))
    V.noi_nso(S, N, {"nso": df})
    xk = S["kt_vn_xk"]
    assert xk.loc["2026-07-01"] == 40e9 and xk.loc["2026-09-01"] == 52e9 and len(xk) == 9      # tháng trùng giữ TradingView
    assert len(S["kt_vn_nk"]) == 8 and "2 tháng mới: Cục Thống kê" in N["kt_vn_xk"]
    assert S["kt_vn_bot"].loc["2026-08-01"] == 5e9 and len(S["kt_vn_bot"]) == 8
    out = capsys.readouterr().out
    assert "kiểm Cục Thống kê ↔ TradingView xk: 1 tháng trùng · lệch lớn nhất 1.000" in out and "cpi_yoy: 1 tháng" in out
    V.noi_nso(S, N, {})                                                                         # không có báo cáo → không đổi
    assert len(S["kt_vn_xk"]) == 9


def test_dung_kt_co_tin_va_bao_cao():
    S, N, P = _mau()
    kq = V.dung(S, N, P, bay_gio=datetime(2026, 11, 25, 22, 0, tzinfo=V.VN))
    assert kq["kt"]["tin"][0]["u"].startswith("https://") and kq["kt"]["bao_cao"]["ten"].endswith("tháng 10/2026")
    h = {r["k"]: r for r in kq["kt"]["ct"]}
    assert h["vn_tin_dung"]["gt"] == 10.19 and h["vn_tin_dung"]["cd"] == "tien_te" and "vn_tin_dung" in kq["kt"]["tq"]
    assert h["vn_vang_cs"]["kt"] == 8.3


def test_hh_theo_ma_tach_ma_tu_cot_lq():
    from thi_truong.vi_mo_web import hh_theo_ma
    bang = [{"k": "hrc", "ten": "Thép HRC", "dv": "USD/tấn", "gia": 900, "ngay": "2026-11-25", "d1": 1.2, "m1": -3, "ytd": 5, "y1": 8,
             "lq": "thép: HPG, HSG, NKG"},
            {"k": "duong", "ten": "Đường", "dv": "c/lb", "gia": 18, "ngay": "2026-11-25", "d1": 0, "m1": 1, "ytd": 2, "y1": 3,
             "lq": "SBT, LSS, QNS – backtest (2012–2026) vẫn kém VN-Index"},
            {"k": "nhom", "ten": "Nhôm", "dv": "USD/tấn", "gia": 2500, "ngay": "2026-11-25", "lq": "nhôm định hình"},
            {"k": "quang", "ten": "Quặng sắt", "dv": "USD/tấn", "gia": 90, "ngay": "2026-11-25", "lq": "thép: HPG, HPG"}]
    d = pd.date_range("2025-06-01", "2026-11-25", freq="D")
    chuoi = {"hrc": [[f"{x:%Y-%m-%d}", 800 + i] for i, x in enumerate(d)]}
    m = hh_theo_ma(bang, chuoi)
    assert set(m) == {"HPG", "HSG", "NKG", "SBT", "LSS", "QNS"}                  # "VN" (2 chữ), nhôm (không mã) bỏ
    assert [x["k"] for x in m["HPG"]] == ["hrc", "quang"]                        # không lặp HPG 2 lần cùng hàng hoá
    sp = m["HPG"][0]["sp"]
    assert 52 <= len(sp) <= 54 and sp[-1] == 800 + len(d) - 1 and m["SBT"][0]["sp"] == []
