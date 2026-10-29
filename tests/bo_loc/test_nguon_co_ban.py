# -*- coding: utf-8 -*-
"""Kiểm thử dữ liệu cơ bản: gộp nhiều nguồn, ưu tiên file, đối chiếu chéo, P/E theo giá hiện tại, cache."""
import numpy as np
import pytest

from bo_loc import cau_hinh as ch
from bo_loc.nguon import co_ban


def test_gop_uu_tien_file_roi_tcbs_roi_vndirect():
    online = {"VNDirect": {"pe": 15.0, "roe": 14.0, "von_hoa": 30000},
              "TCBS": {"pe": 15.5, "pb": 2.1}}
    kq = co_ban.gop(online, {"roe": 13.0}, thu_tu=["TCBS", "VNDirect"])   # thứ tự ưu tiên truyền vào
    assert kq["pe"] == 15.5            # TCBS ưu tiên hơn VNDirect
    assert kq["roe"] == 13.0           # file ưu tiên nhất
    assert kq["von_hoa"] == 30000      # nguồn sau bù chỗ thiếu
    assert "roe←file" in kq["nguon_chi_tieu"] and "pe←TCBS" in kq["nguon_chi_tieu"]
    assert kq["canh_bao_du_lieu"] == ""


def test_canh_bao_khi_cac_nguon_lech(monkeypatch):
    monkeypatch.setattr(ch, "LECH_CANH_BAO_PCT", 20)
    kq = co_ban.gop({"TCBS": {"eps_ttm": 3000.0}, "VNDirect": {"eps_ttm": 4000.0}})
    assert "eps_ttm" in kq["canh_bao_du_lieu"]


def test_khong_bao_lech_pe_pb_do_khac_ngay_gia():
    """P/E, P/B của mỗi nguồn tính theo giá một ngày khác nhau → không phải lỗi dữ liệu."""
    kq = co_ban.gop({"VNDirect": {"pe": 10.0, "pb": 1.5, "eps_ttm": 4000.0},
                     "Yahoo": {"pe": 13.0, "pb": 2.0, "eps_ttm": 4100.0}})
    assert kq["canh_bao_du_lieu"] == ""


def test_roe_so_theo_diem_phan_tram():
    assert co_ban.gop({"VNDirect": {"roe": 18.0}, "Yahoo": {"roe": 22.5}})["canh_bao_du_lieu"] == ""   # +4,5 điểm
    assert "roe" in co_ban.gop({"VNDirect": {"roe": 12.0}, "Yahoo": {"roe": 19.0}})["canh_bao_du_lieu"]


def test_pe_tinh_lai_theo_gia_hien_tai(monkeypatch):
    monkeypatch.setattr(ch, "PE_THEO_GIA_HIEN_TAI", True)
    cb = {"pe": 12.0, "eps_ttm": 5000, "eps_nam": 4000, "bvps": 40000, "so_cp": 4e8}
    t = co_ban.tinh_chi_so(cb, 78.7)
    assert t["pe"] == pytest.approx(78700 / 5000)          # ưu tiên EPS 4 quý
    assert t["pe_nguon"] == 12.0 and "EPS 4 quý" in t["pe_cach_tinh"]
    assert t["pb"] == pytest.approx(78700 / 40000)
    assert t["von_hoa"] == pytest.approx(78700 * 4e8 / 1e9)
    t2 = co_ban.tinh_chi_so({"eps_nam": 4000}, 80)
    assert t2["pe"] == pytest.approx(20) and "EPS năm" in t2["pe_cach_tinh"]


def test_giu_pe_nguon_khi_khong_co_eps():
    t = co_ban.tinh_chi_so({"pe": 12.0}, 78.7)
    assert t["pe"] == 12.0 and t["pe_cach_tinh"] == "nguồn"
    assert np.isnan(co_ban.tinh_chi_so({}, 50)["pe"])


def test_tang_truong_eps_am_sang_duong():
    t = co_ban.tinh_chi_so({"eps_nam": 1000, "eps_nam_truoc": -500, "eps_quy": 300, "eps_quy_cung_ky": 200}, 50)
    assert t["eps_g_nam"] == 100.0 and t["eps_g_quy"] == pytest.approx(50)


def test_tcbs_tu_tinh_eps_ttm(monkeypatch):
    def gia_lap(url, params=None, **k):
        if url.endswith("/overview"):
            return {"outstandingShare": 400, "exchange": "HOSE", "industry": "Cảng", "foreignPercent": 0.4}
        if "financialratio" in url and params["yearly"] == 0:
            return [{"priceToEarning": 14, "priceToBook": 2, "roe": 0.15, "roa": 0.1, "earningPerShare": 1200,
                     "equityOnTotalAsset": 0.7}] + [{"earningPerShare": 1000}] * 4
        if "financialratio" in url:
            return [{"earningPerShare": 4500}, {"earningPerShare": 4000}]
        if "incomestatement" in url:
            return [{"year": 2026, "quarter": q, "revenue": 1000, "grossProfit": 400, "shareHolderIncome": 500}
                    for q in (2, 1)] + [{"year": 2025, "quarter": q, "revenue": 900, "grossProfit": 330,
                                         "shareHolderIncome": 450} for q in (4, 3, 2)]
        raise ValueError("không giả lập")

    monkeypatch.setattr(co_ban, "lay_json", gia_lap)
    kq = co_ban.tu_tcbs("GMD")
    assert kq["so_cp"] == 400e6 and kq["roe"] == 15 and kq["no_phai_tra_tts"] == pytest.approx(30)
    assert kq["ln_4q_ty"] == pytest.approx(500 * 2 + 450 * 2)
    assert kq["ky_lnst"] == "Q2/2026+Q1/2026+Q4/2025+Q3/2025"
    assert kq["eps_nam"] == 4500
    assert kq["ln_g_quy"] == pytest.approx((500 / 450 - 1) * 100)


def test_vndirect_moi_chi_so_mot_lan_goi(monkeypatch):
    goi = []
    gia_tri = {"PRICE_TO_EARNINGS": 16.2, "PRICE_TO_BOOK": 2.4, "EPS_TR": 4850, "ROAE_TR_AVG5Q": 0.142,
               "ROAA_TR_AVG5Q": 0.091}

    def gia_lap(url, params=None, **k):
        assert "api-finfo.vndirect.com.vn/v4/ratios" in url and params["sort"] == "reportDate:desc"
        ma_cs = params["q"].split("ratioCode:")[1]
        goi.append(ma_cs)
        return {"data": [{"code": "GMD", "ratioCode": ma_cs, "value": gia_tri[ma_cs], "reportDate": "2026-06-30"}]}

    monkeypatch.setattr(co_ban, "lay_json", gia_lap)
    kq = co_ban.tu_vndirect("GMD")
    assert sorted(goi) == sorted(gia_tri)                       # mỗi chỉ số 1 request riêng
    assert kq["pe"] == 16.2 and kq["eps_ttm"] == 4850 and kq["roe"] == pytest.approx(14.2)
    assert kq["ky_eps"] == "2026-06-30"


def test_vndirect_bo_dong_tra_sai_chi_so(monkeypatch):
    monkeypatch.setattr(co_ban, "lay_json", lambda *a, **k: {"data": [{"code": "GMD", "ratioCode": "KHAC",
                                                                       "value": 99}]})
    assert co_ban.tu_vndirect("GMD") == {}


def test_pe_theo_eps_cot_loi_va_eps_am():
    t = co_ban.tinh_chi_so({"eps_ttm": 6000, "eps_cot_loi": 4500, "pe": 13}, 78.7)
    assert t["pe"] == pytest.approx(78700 / 4500) and "cốt lõi" in t["pe_cach_tinh"]
    t2 = co_ban.tinh_chi_so({"eps_ttm": -300, "pe": 50}, 20)
    assert t2["pe"] < 0 and "âm" in t2["pe_cach_tinh"]
    from bo_loc.tieu_chi import kiem_tra
    assert kiem_tra("pe_max", {"pe": t2["pe"]}, 15) is False     # lỗ → trượt tiêu chí, không phải "thiếu dữ liệu"


def test_lay_online_luu_dem(tmp_path, monkeypatch):
    dem = {"n": 0}

    def nguon(ma):
        dem["n"] += 1
        return {"pe": 10.0}

    monkeypatch.setattr(co_ban, "NGUON_CO_BAN", {"X": nguon})
    a = co_ban.lay_online("ABC", True, str(tmp_path), ["X"])
    b = co_ban.lay_online("ABC", True, str(tmp_path), ["X"])
    assert a == b == {"X": {"pe": 10.0}} and dem["n"] == 1


def test_doc_file_va_tao_mau(tmp_path):
    p = tmp_path / "mau.csv"
    co_ban.tao_mau(["GMD", "VSC"], str(p))
    assert p.exists() and (tmp_path / "mau_huong_dan.txt").exists()
    f = tmp_path / "cb.csv"
    f.write_text("ma,pe,roe,ghi_chu\ngmd,\"15,5\",14,CafeF 01/10/2026\nVSC,,12,\n", encoding="utf-8")
    d = co_ban.doc_file(str(f))
    assert d["GMD"] == {"pe": 15.5, "roe": 14.0, "ghi_chu": "CafeF 01/10/2026"}
    assert "pe" not in d["VSC"]


@pytest.mark.parametrize("chuoi,so", [("78,700", 78700), ("15,5", 15.5), ("1.234,5", 1234.5),
                                      ("1,234.5", 1234.5), ("12%", 12), ("-3,25", -3.25), ("", None)])
def test_doc_so_kieu_viet_nam(chuoi, so):
    assert co_ban._so(chuoi) == (pytest.approx(so) if so is not None else None)


def test_doc_yahoo_info():
    kq = co_ban.doc_yahoo_info({"trailingPE": 17.5, "priceToBook": 2.3, "returnOnEquity": 0.142,
                                "trailingEps": 4500, "financialCurrency": "VND", "earningsQuarterlyGrowth": -0.1})
    assert kq == {"pe": 17.5, "pb": 2.3, "roe": pytest.approx(14.2), "eps_ttm": 4500, "ln_g_quy": pytest.approx(-10)}
    assert "eps_ttm" not in co_ban.doc_yahoo_info({"trailingEps": 1.2, "financialCurrency": "USD"})


def test_ngat_nguon_chet_sau_5_lan(tmp_path, monkeypatch):
    from bo_loc.nguon.http import CAU_DAO_CO_BAN
    CAU_DAO_CO_BAN.xoa()
    goi = {"chet": 0, "song": 0}

    def chet(ma):
        goi["chet"] += 1
        raise ValueError("timeout")

    def song(ma):
        goi["song"] += 1
        return {"pe": 10.0}

    monkeypatch.setattr(co_ban, "NGUON_CO_BAN", {"Chet": chet, "Song": song})
    for i in range(12):
        co_ban.lay_online(f"M{i}", False, str(tmp_path), ["Chet", "Song"])
    assert goi["chet"] == 5 and goi["song"] == 12
    assert CAU_DAO_CO_BAN.da_ngat() == ["Chet"]
    CAU_DAO_CO_BAN.xoa()


def test_pe_bang_gia_chia_lnst_4_quy_tren_cp_luu_hanh():
    """P/E = Thị giá / EPS ; EPS = LNST 4 quý gần nhất / số CP lưu hành (ưu tiên hơn EPS nguồn)."""
    cb = {"ln_4q_ty": 2200.0, "so_cp": 440e6, "ky_lnst": "Q2/2026+Q1/2026+Q4/2025+Q3/2025",
          "eps_ttm": 9999.0, "pe": 12.0}
    t = co_ban.tinh_chi_so(cb, 78.7)
    assert t["eps_dung"] == pytest.approx(5000)
    assert t["pe"] == pytest.approx(78700 / 5000) and "LNST 4 quý" in t["pe_cach_tinh"]
    t2 = co_ban.tinh_chi_so({"eps_ttm": 4000.0}, 80)                 # thiếu LNST/số CP → EPS nguồn
    assert t2["pe"] == pytest.approx(20) and "nguồn" in t2["pe_cach_tinh"]


def test_lnst_4q_tu_bang_yahoo():
    import pandas as pd
    cot = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"])
    df = pd.DataFrame([[800e9, 450e9, 500e9, 450e9, 300e9]], index=["Net Income Common Stockholders"], columns=cot)
    assert co_ban.lnst_4q_tu_bang_yahoo(df) == (pytest.approx(2200), "Q2/2026+Q1/2026+Q4/2025+Q3/2025")
    hong = df.drop(columns=pd.Timestamp("2025-12-31"))                # thiếu 1 quý → không dùng
    assert co_ban.lnst_4q_tu_bang_yahoo(hong)[0] is None


def test_canh_bao_so_cp_lech_tren_1pct():
    kq = co_ban.gop({"TCBS": {"so_cp": 414e6}, "Yahoo": {"so_cp": 420e6}})
    assert "so_cp" in kq["canh_bao_du_lieu"]
    assert co_ban.gop({"TCBS": {"so_cp": 414e6}, "Yahoo": {"so_cp": 415e6}})["canh_bao_du_lieu"] == ""


def test_nguon_thieu_thu_vien_bo_qua_khong_ghi_loi(monkeypatch, tmp_path):
    """Bot không cài vnstock / yfinance → không gọi 2 nguồn đó, nhật ký không đầy 'Lỗi' (vnstock 0/103, — 0/98)."""
    from bo_loc.nguon.http import NHAT_KY
    co_ban._ghi_cache("VPB", str(tmp_path), {"VNDirect": {"pe": 6.1, "eps_ttm": 3758.0}})
    goi = []
    that = co_ban.importlib.util.find_spec
    monkeypatch.setattr(co_ban.importlib.util, "find_spec",
                        lambda ten, *a: None if ten in ("vnstock", "yfinance") else that(ten, *a))
    for ten, tv in (("vnstock", "vnstock"), ("Yahoo", "yfinance")):
        ham = lambda ma, t=ten: goi.append(t)                                # noqa: E731
        ham.thu_vien = tv
        monkeypatch.setitem(co_ban.NGUON_CO_BAN, ten, ham)
    NHAT_KY.xoa()
    assert co_ban.lay_online("VPB", dung_cache=True, thu_muc_cache=str(tmp_path)) == {"VNDirect": {"pe": 6.1,
                                                                                                    "eps_ttm": 3758.0}}
    assert not goi and set(NHAT_KY.bang()["Nguồn"]) == {"cache"}


def test_cache_thieu_lnst_tu_bo_sung_va_pe_theo_lnst(monkeypatch, tmp_path):
    """Lưu đệm chỉ có VNDirect + Yahoo (thiếu LNST 4 quý) → tự lấy thêm LNST → P/E = giá ÷ (LNST 4Q ÷ CP)."""
    co_ban._ghi_cache("VPB", str(tmp_path), {"VNDirect": {"pe": 6.1, "pb": 1.28, "eps_ttm": 3758.0},
                                              "Yahoo": {"so_cp": 10e9, "bvps": 22476.0, "pb": 1.02}})
    monkeypatch.setitem(co_ban.NGUON_CO_BAN, "vnstock",
                        lambda ma: {"ln_4q_ty": 28193.0, "ky_lnst": "Q2/2026+Q1/2026+Q4/2025+Q3/2025"})
    online = co_ban.lay_online("VPB", dung_cache=True, thu_muc_cache=str(tmp_path))
    assert online["vnstock"]["ln_4q_ty"] == 28193.0
    assert "vnstock" in co_ban._doc_cache("VPB", str(tmp_path))            # đã ghi lại lưu đệm
    m = co_ban.tinh_chi_so(co_ban.gop(online), 23.0)
    assert m["eps_dung"] == pytest.approx(2819.3) and m["pe"] == pytest.approx(23000 / 2819.3, rel=1e-4)
    assert "LNST 4 quý" in m["pe_cach_tinh"]
    assert m["pb"] == pytest.approx(23000 / 22476) and "Yahoo" in m["pb_cach_tinh"]   # giá hiện tại ÷ BVPS


def test_pb_tu_tinh_khi_khong_nguon_nao_co_pb():
    m = co_ban.tinh_chi_so({"bvps": 20000.0}, 23.0)
    assert m["pb"] == pytest.approx(1.15) and m["pb_cach_tinh"].startswith("P/B = giá ÷ BVPS")


def test_pe_pb_theo_gia_hien_tai_khop_ctck():
    """Số thật 07/10/2026 – CTCK: MWG P/E 11,45, P/B 3,16 · DHC P/E 7,64, P/B 1,67."""
    mwg = co_ban.gop({"VNDirect": {"pe": 11.51, "pb": 3.32, "eps_ttm": 6712.39},
                      "vnstock": {"ln_4q_ty": 9856.63, "ky_lnst": "Q2/2026+Q1/2026+Q4/2025+Q3/2025"},
                      "Yahoo": {"so_cp": 1468423529.0, "bvps": 24297.82, "pb": 3.16}})
    m = co_ban.tinh_chi_so(mwg, 76.9)
    assert round(m["pe"], 2) == 11.46 and round(m["pb"], 2) == 3.16


def test_luu_y_ghi_ro_chi_tieu_lech():
    from bo_loc.danh_gia_sau_loc import co_do
    _, nhe = co_do({"canh_bao_du_lieu": "roe: VNDirect 12.00, Yahoo 19.00 | so_cp: TCBS 414,000,000.00, Yahoo 420,000,000.00"},
                   {})
    assert "Nguồn dữ liệu lệch nhau ở ROE, số CP – kiểm tra lại số liệu" in nhe


def test_so_cp_bvps_uu_tien_yahoo_tru_cp_quy():
    """KDC 07/10/2026: Yahoo VCSH mẹ ÷ BVPS = 276,3 tr CP (đã trừ CP quỹ) → P/E ≈ CTCK 25,07."""
    import pandas as pd
    q = pd.DataFrame({pd.Timestamp("2026-06-30"): [5878105524971.0]}, index=["Stockholders Equity"])
    t = type("T", (), {"quarterly_balance_sheet": q})()
    cp = co_ban.cp_luu_hanh_yahoo(t, {"bookValue": 21270.871, "financialCurrency": "VND"})
    kq = co_ban.gop({"VNDirect": {"pe": 25.13, "pb": 2.43, "eps_ttm": 1927.9},
                     "TCBS": {"so_cp": 289806316.0, "bvps": 20000.0},
                     "vnstock": {"ln_4q_ty": 558.708, "ky_lnst": "Q2/2026+Q1/2026+Q4/2025+Q3/2025"},
                     "Yahoo": {"so_cp": cp, "bvps": 21270.871}}, thu_tu=["VNDirect", "vnstock", "TCBS", "Yahoo"])
    assert kq["so_cp"] == cp and kq["bvps"] == 21270.871
    m = co_ban.tinh_chi_so(kq, 50.8)
    assert abs(m["pe"] - 25.07) / 25.07 < 0.01 and round(m["pb"], 2) == 2.39
