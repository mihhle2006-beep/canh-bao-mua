# -*- coding: utf-8 -*-
"""Dữ liệu: chuẩn hoá đơn vị, sửa high/low, đọc CSV, gộp tuần, phản hồi API không phải JSON."""
import numpy as np
import pandas as pd
import pytest

from ptcp import du_lieu
from ptcp import du_lieu_co_ban  # noqa: E402


def test_doi_don_vi_dong_sang_nghin_dong():
    df = pd.DataFrame({"time": pd.bdate_range("2026-01-01", periods=3), "open": [25000, 25100, 25200],
                       "high": [25500, 25600, 25700], "low": [24800, 24900, 25000],
                       "close": [25100, 25200, 25300], "volume": [1, 2, 3]})
    out = du_lieu.chuan_hoa(df)
    assert out.close.iloc[0] == pytest.approx(25.1)


def test_chi_so_khong_bi_chia_1000():
    df = pd.DataFrame({"time": pd.bdate_range("2026-01-01", periods=2), "open": [1250, 1260],
                       "high": [1255, 1265], "low": [1245, 1255], "close": [1250, 1260], "volume": [0, 0]})
    assert du_lieu.chuan_hoa(df, la_chi_so=True).close.iloc[0] == 1250


def test_sua_high_low_khong_hop_le():
    df = pd.DataFrame({"time": ["2026-01-02"], "open": [10.0], "high": [9.0], "low": [11.0], "close": [10.5],
                       "volume": [5]})
    r = du_lieu.chuan_hoa(df).iloc[0]
    assert r.high >= max(r.open, r.close) and r.low <= min(r.open, r.close)


def test_doc_csv_ngay_kieu_viet_nam(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text('Ngày,Giá đóng cửa,Khối lượng\n02/01/2026,"25,100",100\n05/01/2026,"25,300",200\n',
                 encoding="utf-8")
    df = du_lieu.chuan_hoa(du_lieu.tu_csv(f))
    assert df.index[0] == pd.Timestamp("2026-01-02") and len(df) == 2      # ngày dd/mm/yyyy
    assert df.close.iloc[0] == pytest.approx(25.1)                          # "25,100" đồng → 25.1 nghìn


def test_gop_tuan_high_la_max_ngay(gia_ngay):
    w = du_lieu.gop_tuan(gia_ngay)
    tuan = gia_ngay[(gia_ngay.index > w.index[-2]) & (gia_ngay.index <= w.index[-1])]
    assert w.high.iloc[-1] == pytest.approx(tuan.high.max())


def test_goi_api_bao_loi_ro_khi_tra_html(monkeypatch):
    class R:
        status_code, text, headers = 200, "<html>blocked</html>", {"content-type": "text/html"}
    monkeypatch.setattr(du_lieu.requests, "get", lambda *a, **k: R())
    with pytest.raises(ValueError, match="không phải JSON"):
        du_lieu._goi_api("http://x", so_lan=1)


def test_chi_so_co_ban_vndirect_va_pe_theo_gia(monkeypatch):
    goi = []
    gt = {"PRICE_TO_EARNINGS": 13.0, "PRICE_TO_BOOK": 2.4, "EPS_TR": 5000, "ROAE_TR_AVG5Q": 0.15}

    def gia_lap(url, params=None, **k):
        assert url.startswith("https://api-finfo.vndirect.com.vn/v4/ratios")
        ma = params["q"].split("ratioCode:")[1]
        goi.append(ma)
        return {"data": [{"code": "GMD", "ratioCode": ma, "value": gt[ma], "reportDate": "2026-06-30"}]}

    monkeypatch.setattr(du_lieu, "_goi_api", gia_lap)
    kq = du_lieu.lay_chi_so_co_ban("GMD", gia=78.7)
    assert sorted(goi) == sorted(gt)                                     # mỗi chỉ số 1 lần gọi
    assert kq["P/E"] == pytest.approx(78700 / 5000) and kq["P/E nguồn"] == 13.0
    assert kq["ROE %"] == pytest.approx(15) and kq["nguon"].startswith("VNDirect")


def test_chi_so_co_ban_nguon_sau_bu_cho_thieu(monkeypatch):
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_CO_BAN", [
        ("A", lambda s: {"P/E": 10.0, "ky": "Q2/2026"}),
        ("B", lambda s: (_ for _ in ()).throw(ValueError("HTTP 403"))),
        ("C", lambda s: {"P/E": 99.0, "P/B": 1.5, "ky": "TTM"})])
    kq = du_lieu.lay_chi_so_co_ban("XYZ")
    assert kq["P/E"] == 10.0 and kq["P/B"] == 1.5 and kq["nguon"] == "A (Q2/2026) + C (TTM)"


def test_chi_so_co_ban_eps_am_cho_pe_am(monkeypatch):
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_CO_BAN", [("A", lambda s: {"EPS 4Q": -500.0, "P/E": 30.0, "ky": ""})])
    assert du_lieu.lay_chi_so_co_ban("XYZ", gia=10)["P/E"] < 0


def test_nguon_vnstock_dung_sau_cac_api():
    ten = [t for t, _ in du_lieu.cac_nguon_ngay("AAA", "2026-01-01", "2026-02-01")]
    assert ten[-1] == "vnstock" and "Vietstock" not in ten                 # vnstock là nguồn dự phòng cuối
    assert not hasattr(du_lieu, "tu_vnstock_cu")


def test_khong_hoi_so_cp_va_chi_so_co_ban(monkeypatch):
    """Số CP, sở hữu NN, beta, P/B, ROE, margin: không bao giờ hỏi – chỉ nhận tham số truyền vào main()."""
    from ptcp import chuong_trinh as ct

    def cam_hoi(*a, **k):
        raise AssertionError("không được hỏi người dùng")

    monkeypatch.setattr("builtins.input", cam_hoi)
    monkeypatch.setitem(ct._CHAY, "tuong_tac", True)
    monkeypatch.setattr(ct, "_THAM_SO", {"pb": 1.8})
    assert ct.hoi("KL CP ĐÃ PHÁT HÀNH", None, float, khoa="kl_ph", chi_tham_so=True) is None
    assert ct.hoi("P/B (lần)", None, float, khoa="pb", chi_tham_so=True) == 1.8     # vẫn ghi đè được
    src = open(ct.__file__, encoding="utf-8").read()
    for khoa in ("kl_ph", "kl_ny", "cp_quy", "so_huu_nn", "beta", "pb", "roe", "margin"):
        assert f'khoa="{khoa}", chi_tham_so=True' in src, khoa


def test_eps_tu_tinh_lnst_4_quy_chia_cp_luu_hanh(monkeypatch):
    """P/E = Thị giá / EPS ; EPS = LNST 4 quý gần nhất / số CP lưu hành."""
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_CO_BAN", [("A", lambda s: {"P/E": 12.0, "EPS 4Q": 9999.0, "P/B": 2.0,
                                                                   "ky": "Q2/2026"})])
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_LNST", [
        ("Hong", lambda s: (_ for _ in ()).throw(ValueError("HTTP 403"))),
        ("B", lambda s: [("Q2/2026", 800.0), ("Q1/2026", 450.0), ("Q4/2025", 500.0), ("Q3/2025", 450.0)])])
    kq = du_lieu.lay_chi_so_co_ban("GMD", gia=78.7, so_cp_luu_hanh=440_000_000)
    eps = 2200 * 1e9 / 440_000_000                                       # = 5.000 đ
    assert kq["LNST 4 quý (tỷ đồng)"] == 2200 and kq["EPS 4Q"] == pytest.approx(eps)
    assert kq["P/E"] == pytest.approx(78700 / eps) and kq["P/E nguồn"] == 12.0
    assert kq["EPS 4Q nguồn"] == 9999.0 and "Q2/2026+Q1/2026+Q4/2025+Q3/2025" in kq["cach_tinh_eps"]


def test_lnst_nhap_tay_uu_tien(monkeypatch):
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_CO_BAN", [("A", lambda s: {"P/B": 2.0, "ky": ""})])
    monkeypatch.setattr(du_lieu_co_ban, "NGUON_LNST", [("X", lambda s: (_ for _ in ()).throw(AssertionError("không gọi")))])
    kq = du_lieu.lay_chi_so_co_ban("GMD", gia=50, so_cp_luu_hanh=1e8, lnst_4q=500)
    assert kq["EPS 4Q"] == pytest.approx(5000) and kq["P/E"] == pytest.approx(10)
    assert "nhập tay" in kq["cach_tinh_eps"]


def test_bon_quy_phai_lien_tiep():
    ok = [("Q1/2026", 1), ("Q4/2025", 1), ("Q3/2025", 1), ("Q2/2025", 1)]
    thieu = [("Q2/2026", 1), ("Q1/2026", 1), ("Q3/2025", 1), ("Q2/2025", 1)]       # thiếu Q4/2025
    assert du_lieu_co_ban._bon_quy_lien_tiep(ok) and not du_lieu_co_ban._bon_quy_lien_tiep(thieu)
    assert not du_lieu_co_ban._bon_quy_lien_tiep(ok[:3])


def test_khong_con_vietstock():
    assert not hasattr(du_lieu, "lay_cp_vietstock")
    assert "Vietstock" not in du_lieu.DIA_CHI_NGUON


def test_so_cp_nhieu_nguon_va_doi_chieu(monkeypatch):
    def gia_lap(url, params=None, **k):
        if "tcbs" in url:
            return {"outstandingShare": 414.06, "issueShare": 414.06, "foreignPercent": 0.41, "exchange": "HOSE"}
        return {"data": [{"code": "GMD", "floor": "HOSE", "listedShare": 414_064_000}]}

    monkeypatch.setattr(du_lieu, "_goi_api", gia_lap)
    info = du_lieu.lay_thong_tin_dn("GMD")
    assert info["so_cp"] == pytest.approx(414.06e6) and info["nguon_so_cp"] == "TCBS"
    assert info["ung_vien_cp"]["niem_yet"]["VNDirect"] == 414_064_000
    assert info["so_huu_nn"] == pytest.approx(41) and info["san"] == "HOSE"


def test_co_cau_co_phieu_uu_tien_va_canh_bao_lech():
    from ptcp.phan_tich import co_cau_co_phieu
    uv = {"luu_hanh": {"TCBS": 414_000_000, "Yahoo": 430_000_000}, "niem_yet": {"VNDirect": 414_064_000}}
    cc = co_cau_co_phieu(None, None, None, uv, lech_pct=0.5)
    assert cc["kl_luu_hanh"] == 414_000_000                                  # nguồn đầu (TCBS)
    assert any("lệch" in c for c in cc["canh_bao_cp"])                        # Yahoo lệch ~3,9%
    assert {"TCBS", "Yahoo", "VNDirect"} <= set(cc["doi_chieu_cp"].columns)
    tay = co_cau_co_phieu(414_064_000, None, 64_000, uv, nhan_nhap="BCTC")
    assert tay["kl_luu_hanh"] == 414_000_000 and tay["doi_chieu_cp"].iloc[3]["Nguồn"].startswith("Tính")


def test_suy_ra_cp_quy_tu_niem_yet_tru_luu_hanh():
    from ptcp.phan_tich import co_cau_co_phieu
    cc = co_cau_co_phieu(None, None, None, {"luu_hanh": {"TCBS": 100_000_000}, "niem_yet": {"VNDirect": 100_500_000}})
    assert cc["cp_quy"] == 500_000 and cc["kl_phat_hanh"] == 100_500_000 and cc["kl_luu_hanh"] == 100_000_000


def test_doi_chieu_nhan_dien_lech_khong_doi(monkeypatch):
    """Nguồn lệch đúng 1 hệ số ở mọi phiên → nhận diện là khác cách điều chỉnh giá, không phải lỗi."""
    idx = pd.bdate_range("2026-08-01", periods=45)
    goc = pd.DataFrame({"open": 10.0, "high": 11.0, "low": 9.0, "close": np.linspace(10, 12, 45), "volume": 1e5},
                       index=idx)
    lech = goc.reset_index().rename(columns={"index": "time"})
    lech["close"] = lech["close"] * 1.0263
    monkeypatch.setattr(du_lieu, "cac_nguon_ngay", lambda *a: [("A", lambda: goc.reset_index().rename(
        columns={"index": "time"})), ("B", lambda: lech), ("C", lambda: (_ for _ in ()).throw(SystemExit("hết lượt")))])
    b = du_lieu.doi_chieu_nguon("XYZ", goc, "A").set_index("Nguồn đối chiếu")
    assert "KHÔNG ĐỔI +2.63%" in b.loc["B", "Đánh giá"] and "không lấy được" in b.loc["C", "Đánh giá"]
