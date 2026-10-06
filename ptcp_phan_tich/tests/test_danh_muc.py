# -*- coding: utf-8 -*-
"""Kiểm thử phần DANH MỤC (dmuc) – phân tích từng mã đi qua ptcp.main; không cần mạng."""
import contextlib
import io
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from tests.conftest import tao_gia
from dmuc import cau_noi, chuong_trinh, danh_muc, markowitz, tien_ich


# ---------------------------------------------------------------- đọc số, đơn vị, nhật ký
def test_doc_so_kieu_viet_nam():
    assert tien_ich.doc_so("1.234,5") == 1234.5
    assert tien_ich.doc_so("1,234.5") == 1234.5
    assert tien_ich.doc_so("70,5") == 70.5
    assert tien_ich.doc_so("106.249.620", True) == 106249620
    assert tien_ich.doc_so("abc") is None


def test_sua_don_vi_gia():
    assert cau_noi._sua_don_vi(73900, "x")[0] == pytest.approx(73.9)
    assert cau_noi._sua_don_vi(73.9, "x")[0] == 73.9
    assert tien_ich.quy_doi_gia(0.0739, 46)[0] == pytest.approx(73.9)


def test_nhat_ky_gia_von_co_tuc(tmp_path):
    f = tmp_path / "nk.csv"
    f.write_text("ngay,ma,loai,so_cp,gia,phi\n01/01/2026,AAA,mua,100,10,0\n01/02/2026,AAA,mua,100,20,0\n"
                 "01/03/2026,AAA,co_tuc_cp,20,,\n01/04/2026,AAA,ban,110,25,0\n01/05/2026,AAA,co_tuc_tien,,1,\n",
                 encoding="utf-8")
    v = danh_muc.doc_nhat_ky(str(f))["AAA"]
    assert v["so_cp"] == pytest.approx(110)
    assert v["gia_von"] == pytest.approx(3000 / 220)
    assert v["co_tuc"] == pytest.approx(110 * 1000)
    with open(f, "a", encoding="utf-8") as g:
        g.write("01/06/2026,AAA,ban,500,25,0\n")
    with pytest.raises(SystemExit):
        danh_muc.doc_nhat_ky(str(f))


# ---------------------------------------------------------------- cắt lỗ/mục tiêu đã đặt, số lượng
def _r(ht, cat_lo, mt=None):
    return {"ht": ht, "so_cp": 100, "gia_von": 50.0, "cat_lo": cat_lo, "mt_ngay": mt or ht * 1.2, "mt_nhap": None}


def test_cat_lo_neo_chi_doi_len_va_kich_hoat():
    info, tt = danh_muc.cap_nhat_muc_dat(_r(50, 46), {}, None)
    _, tt = danh_muc.cap_nhat_muc_dat(_r(55, 51), {}, tt)
    assert tt["cat_lo"] == 51
    _, tt = danh_muc.cap_nhat_muc_dat(_r(52, 48), {}, tt)
    assert tt["cat_lo"] == 51                                   # không dời xuống
    assert danh_muc.cap_nhat_muc_dat(_r(70, 60, mt=80), {}, tt)[0]["cham_mt"]
    info, _ = danh_muc.cap_nhat_muc_dat(_r(50.5, 46.9), {}, tt)
    assert info["cham_cl"]
    r = {**_r(50.5, 46.9), "du_lieu_cu": False, "tg": {"tuan_ok": True}, "upside_dg": np.nan,
         "cau_truc_tuan": "", "quyet_dinh": "THEO DÕI"}
    assert danh_muc.goi_y_hanh_dong(r, info, 10, 1e6).startswith("CẮT LỖ")


def test_lo_le_khi_von_nho():
    n, ghi = danh_muc.so_luong_goi_y({"ht": 77.0, "cat_lo": 71.6}, 11e6, 8e6, 1e6)
    assert 0 < n < 100 and "LÔ LẺ" in ghi
    assert danh_muc.so_luong_goi_y({"ht": 77.0, "cat_lo": 71.6}, 2e9, 1e9, 1e9)[0] % 100 == 0


# ---------------------------------------------------------------- tích hợp ptcp → danh mục
@pytest.fixture(scope="module")
def ds_kq(tmp_path_factory):
    p = tmp_path_factory.mktemp("dm")
    ket_thuc = pd.offsets.BDay().rollback(pd.Timestamp.today().normalize() - pd.Timedelta(days=1))
    vni = tao_gia(seed=9, sigma=0.011, gia_dau=1000)
    vni.index = pd.bdate_range(end=ket_thuc, periods=len(vni))
    vni.rename_axis("date").reset_index().to_csv(p / "vni.csv", index=False)
    ds_vao = [{"ma": "AAA", "so_cp": 100, "gia_von": 20.0}, {"ma": "BBB", "so_cp": 0},
              {"ma": "CCC", "so_cp": 0}, {"ma": "NEW", "so_cp": 50, "gia_von": 20000}]   # giá vốn nhập theo đồng
    kq = []
    for i, d in enumerate(ds_vao):
        g = tao_gia(seed=20 + i, n=1500 if d["ma"] != "NEW" else 200)
        g.index = pd.bdate_range(end=ket_thuc, periods=len(g))
        g.rename_axis("date").reset_index().to_csv(p / f"{d['ma']}.csv", index=False)
        d.update(csv_ngay=str(p / f"{d['ma']}.csv"), san="HOSE", kl_ph=1e8, so_huu_nn=10.0)
        kq.append(cau_noi.phan_tich_ma(d, "2019-01-01", str(p / "vni.csv"), 63, str(p / d["ma"]), xuat_file=False))
    return ds_vao, kq, vni


def test_cau_noi_nhat_quan_voi_ptcp(ds_kq):
    _, kq, _ = ds_kq
    for r in kq:
        assert r["cat_lo"] == r["stop"]["gia"] < r["ht"]
        assert r["quyet_dinh"] in ("MUA", "MUA TỪNG PHẦN", "CHỜ ĐIỂM VÀO", "CHỜ GIÁ TỐT HƠN", "THEO DÕI",
                                   "CHƯA MUA", "KHÔNG MUA MỚI", "CHỜ SAU SỰ KIỆN")
    assert kq[3]["gia_von"] == pytest.approx(20.0)              # 20000 đ → 20 nghìn
    assert any("ĐỒNG" in c for c in kq[3]["canh_bao"])


def test_tien_mat_trong_ty_trong(ds_kq):
    ds_vao, kq, vni = ds_kq
    dm, _ = danh_muc.phan_tich_danh_muc(kq, ds_vao, vni, 0.04, 10e6, {}, {"xau": False}, 50.0)
    t = dm["tong"]
    assert dm["bang"]["Tỷ trọng TS %"].sum() + t["Tiền mặt (đ)"] / t["Tổng tài sản (đ)"] * 100 == pytest.approx(100)


def test_markowitz_giu_ma_bi_loai_va_tien_mat(ds_kq):
    ds_vao, kq, vni = ds_kq
    dm, _ = danh_muc.phan_tich_danh_muc(kq, ds_vao, vni, 0.04, 10e6, {}, {"xau": False}, 60.0)
    mk = markowitz.toi_uu_markowitz(kq, dm, 0.04, 10e6, giu_tien_mat=60.0)
    assert "NEW" not in mk["ma"]
    for kh in mk["ke_hoach"].values():
        k = kh.set_index("Mã")
        assert k.at["NEW", "Mua(+)/Bán(−) CP"] == 0
        assert k["Tỷ trọng mục tiêu % TS"].sum() == pytest.approx(40, abs=0.5)
    assert np.all(np.linalg.eigvalsh(mk["cov"]) > 0)


# ---------------------------------------------------------------- tham số
def test_tham_so_go_sai_bao_loi():
    with mock.patch("sys.stderr"), pytest.raises(SystemExit):
        chuong_trinh.doc_tham_so(["--tienmat", "5"])


def test_hoi_nguoi_dung():
    a = chuong_trinh.doc_tham_so(["--tien_mat", "8"])
    with mock.patch.dict(sys.modules, {"ipykernel": mock.MagicMock()}), \
            mock.patch("builtins.input", side_effect=["50", "2"]), contextlib.redirect_stdout(io.StringIO()):
        a = chuong_trinh.hoi_nguoi_dung(a)
    assert (a.tien_mat, a.giu_tien_mat, a.chon) == (8, 50, "max_sharpe")


# ---------------------------------------------------------------- so sánh VN-Index, 5 năm Markowitz
from dmuc import so_sanh  # noqa: E402


def _chuoi(gia, ngay_cuoi="2026-10-02"):
    idx = pd.bdate_range(end=ngay_cuoi, periods=len(gia))
    return pd.DataFrame({"close": np.asarray(gia, float)}, index=idx)


def test_so_vni_cung_dong_tien_mua_ban():
    g = np.r_[np.full(100, 10.0), np.full(100, 20.0)]           # cổ phiếu ×2
    v = np.r_[np.full(100, 1000.0), np.full(100, 1500.0)]       # VN-Index ×1.5
    df, vni = _chuoi(g), _chuoi(v)
    r = {"symbol": "AAA", "so_cp": 50, "ht": 20.0, "gia_von": 10.0, "df": df}
    dt = [(df.index[10], "mua", 100, 10.0, 0.0), (df.index[150], "ban", 50, 20.0, 0.0)]
    b, thieu = so_sanh.so_sanh_tu_ngay_mua([r], [{"ma": "AAA", "dong_tien": dt}], vni)
    x = b.iloc[0]
    assert x["Lợi suất %"] == pytest.approx(100)                  # mua 1tr → còn 1tr + bán 1tr
    assert x["VN-Index cùng dòng tiền %"] == pytest.approx(50)
    assert x["Chênh lệch (điểm %)"] == pytest.approx(50)
    assert not thieu


def test_so_vni_theo_ky_va_thieu_ngay_mua():
    g = np.linspace(10, 20, 300)
    df, vni = _chuoi(g), _chuoi(g * 100)                         # đi cùng nhau → chênh 0
    r = {"symbol": "AAA", "so_cp": 100, "ht": 20.0, "gia_von": 12.0, "df": df}
    b = so_sanh.so_sanh_theo_ky([r], 1e6, vni)
    assert b["Chênh lệch CP − VNI (điểm %)"].abs().max() < 1e-9
    _, thieu = so_sanh.so_sanh_tu_ngay_mua([r], [{"ma": "AAA"}], vni)
    assert thieu == ["AAA"]
    nx = so_sanh.nhan_xet(b, pd.DataFrame(), thieu, [r], 1.0, 50)
    assert any("ngay_mua" in c for c in nx) and any("1 năm" in c for c in nx)


def test_markowitz_dung_5_nam(ds_kq):
    ds_vao, kq, vni = ds_kq
    dm, _ = danh_muc.phan_tich_danh_muc(kq, ds_vao, vni, 0.04, 10e6, {}, {"xau": False}, 50.0)
    mk = markowitz.toi_uu_markowitz(kq, dm, 0.04, 10e6)
    assert mk["so_tuan"] >= markowitz.MKW_SO_TUAN_TOI_THIEU >= 255
    assert "nhan_xet" in dm and len(dm["so_sanh_ky"])


# ---------------------------------------------------------------- thị trường → tiền mặt tự động
from dmuc import thi_truong  # noqa: E402


def _vni(huong, n=600, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-10-02", periods=n)
    r = np.r_[np.full(n - 150, 0.0008), np.full(150, huong)] + rng.normal(0, 0.003, n)
    c = 1000 * np.exp(np.cumsum(r))
    return pd.DataFrame({"open": c, "high": c * 1.006, "low": c * 0.994, "close": c,
                         "volume": np.full(n, 1e8)}, index=idx)


def test_thi_truong_tang_giam_va_tien_mat():
    tang = thi_truong.danh_gia_thi_truong(_vni(0.002))
    giam = thi_truong.danh_gia_thi_truong(_vni(-0.004))
    assert tang["trang_thai"] == "TĂNG" and tang["giu_tien_mat"] == 0
    assert giam["trang_thai"] == "GIẢM" and giam["giu_tien_mat"] == 50 and giam["xau"]
    assert len(giam["bang"]) == 6
    assert thi_truong.danh_gia_thi_truong(None)["giu_tien_mat"] is None


def test_supertrend_dao_chieu():
    _, h = thi_truong.supertrend(_vni(-0.004))
    assert h.iloc[-1] == -1
    _, h = thi_truong.supertrend(_vni(0.002))
    assert h.iloc[-1] == 1


def test_tien_mat_mac_dinh_la_tu_dong():
    assert chuong_trinh.doc_tham_so([]).giu_tien_mat is None
    assert chuong_trinh.doc_tham_so(["--giu_tien_mat", "30"]).giu_tien_mat == 30



# ---------------------------------------------------------------- điều chỉnh cắt lỗ / chốt lời, ghi lại CSV
from dmuc import dieu_chinh  # noqa: E402


def _ma_giu(ht, gv=50.0, cl0=46.0, cat_lo_kt=None, mt=70.0, tuan_ok=True, tuan_rat_tot=False, ngay_mua=None):
    idx = pd.bdate_range(end="2026-10-02", periods=60)
    c = np.linspace(gv, ht, 60)
    df = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c}, index=idx)
    r = {"symbol": "AAA", "so_cp": 100, "ht": ht, "gia_von": gv, "df": df, "cat_lo": cat_lo_kt or ht * 0.93,
         "mt_ngay": ht * 1.15, "tg": {"tuan_ok": tuan_ok, "tuan_rat_tot": tuan_rat_tot}}
    md = {"cat_lo_moi": cl0, "muc_tieu_moi": mt, "cat_lo_ban_dau": cl0, "cat_lo_dat": cl0, "muc_tieu_dat": mt,
          "cham_cl": ht <= cl0, "cham_mt": False, "ngay_mua": ngay_mua, "nguon_ngay_mua": "danh mục"}
    return r, md


def test_hoa_von_va_khoa_lai():
    r, md = _ma_giu(ht=54.5, cat_lo_kt=40)                      # lãi > 1R (R = 4) → hoà vốn
    x = dieu_chinh._de_xuat_giu(r, md)
    assert x["Cắt lỗ đề xuất"] >= 50 and "hoà vốn" in x["Lý do cắt lỗ"]
    r, md = _ma_giu(ht=58.5, cat_lo_kt=40)                      # lãi > 2R → khoá 1R = 54
    x = dieu_chinh._de_xuat_giu(r, md)
    assert x["Cắt lỗ đề xuất"] == pytest.approx(54) and "khoá" in x["Lý do cắt lỗ"]


def test_cat_lo_khong_bao_gio_ha():
    r, md = _ma_giu(ht=48, cl0=46, cat_lo_kt=44)
    assert dieu_chinh._de_xuat_giu(r, md)["Cắt lỗ đề xuất"] == 46


def test_chot_loi_sat_muc_tieu_va_ha_khi_tuan_yeu():
    r, md = _ma_giu(ht=69, mt=70)
    assert "chuẩn bị chốt" in dieu_chinh._de_xuat_giu(r, md)["Lý do chốt lời"]
    r, md = _ma_giu(ht=52, mt=70, tuan_ok=False)                 # kháng cự gần 59.8 < 70
    x = dieu_chinh._de_xuat_giu(r, md)
    assert "HẠ" in x["Lý do chốt lời"] and x["Chốt lời đề xuất"] < 70


def test_ghi_lai_csv_giu_cot_cu(tmp_path):
    f = tmp_path / "danh_muc.csv"
    f.write_text("ma,so_cp,gia_von,gia_muc_tieu,csv_ngay\naaa,100,50,80,x.csv\nBBB,,,,\n", encoding="utf-8")
    r, md = _ma_giu(ht=58.5, cat_lo_kt=40, ngay_mua="2026-08-01")
    giu = dieu_chinh._de_xuat_giu(r, md)
    td = {**giu, "Mã": "BBB", "Trạng thái": "Theo dõi", "Giá mua đề xuất": 30.0, "Cắt lỗ đề xuất": 28.0,
          "Chốt lời đề xuất": 36.0, "Ghi chú": "CHỜ ĐIỂM VÀO"}
    assert dieu_chinh.cap_nhat_csv(str(f), pd.DataFrame([giu, td]))
    d = pd.read_csv(f, dtype=str, keep_default_na=False)
    assert list(d.columns[:5]) == ["ma", "so_cp", "gia_von", "gia_muc_tieu", "csv_ngay"]
    a, b = d.iloc[0], d.iloc[1]
    assert a["csv_ngay"] == "x.csv" and a["ngay_mua"] == "01/08/2026"
    assert float(a["cat_lo_dat"]) == pytest.approx(giu["Cắt lỗ đề xuất"], abs=0.01)
    assert giu["Cắt lỗ đề xuất"] >= 54                                   # Chandelier / khoá 1R
    assert b["gia_mua_de_xuat"] == "30.00" and b["cat_lo_dat"] == "" and "CHỜ" in b["de_xuat"]
    assert (tmp_path / "danh_muc.csv.bak").exists()
    ds = danh_muc.doc_danh_muc(str(f))                         # file sau khi ghi vẫn đọc lại được
    assert ds[0]["cat_lo_dat"] == pytest.approx(float(a["cat_lo_dat"])) and ds[0]["ngay_mua"] == pd.Timestamp("2026-08-01")


def test_nhat_ky_ngay_mua_chinh_xac(tmp_path):
    f = tmp_path / "nk.csv"
    f.write_text("ngay,ma,loai,so_cp,gia,phi\n05/01/2026,AAA,mua,100,10,0\n10/02/2026,AAA,ban,100,12,0\n"
                 "15/03/2026,AAA,mua,50,11,0\n20/03/2026,AAA,mua,50,11.5,0\n", encoding="utf-8")
    ds = danh_muc.gop_nhat_ky([{"ma": "AAA"}], danh_muc.doc_nhat_ky(str(f)))
    assert ds[0]["ngay_mua"] == pd.Timestamp("2026-03-15") and ds[0]["nguon_ngay_mua"] == "nhật ký"
