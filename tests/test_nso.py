# -*- coding: utf-8 -*-
"""Cục Thống kê / NHNN / CafeF (thi_truong/nso): đọc số từ chữ báo cáo, kỳ từ đường dẫn, kiểm tự mâu thuẫn, nhớ báo cáo đã đọc,
bảng tín dụng, RSS – không mạng (mẫu câu theo báo cáo thật)."""
import math

import pandas as pd

from thi_truong import nso

BC = ("Chỉ số giá tiêu dùng (CPI) tháng Mười tăng 0,25% so với tháng trước; tăng 3,10% so với tháng 12/2025 và tăng 5,08% so với "
      "cùng kỳ năm trước. Bình quân 10 tháng năm 2026, CPI tăng 3,95% so với cùng kỳ năm trước; lạm phát cơ bản tăng 3,40%. "
      "Chỉ số giá vàng tháng Mười tăng 4,12% so với tháng trước; tăng 48,30% so với cùng kỳ năm trước. "
      "Chỉ số giá đô la Mỹ tháng Mười giảm 0,15% so với tháng trước; tăng 2,64% so với cùng kỳ năm trước. "
      "Chỉ số sản xuất toàn ngành công nghiệp (IIP) tháng Mười ước tính tăng 2,1% so với tháng trước và tăng 14,4% so với cùng kỳ. "
      "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Mười ước đạt 612,3 nghìn tỷ đồng, tăng 1,2% "
      "so với tháng trước và tăng 10,5% so với cùng kỳ. Kim ngạch xuất khẩu hàng hóa tháng Mười ước đạt 54,79 tỷ USD, tăng 3,0% so "
      "với tháng trước và tăng 26,0% so với cùng kỳ. Nhập khẩu hàng hóa tháng Mười ước đạt 47,48 tỷ USD, tăng 1,0% so với tháng "
      "trước và tăng 20,1% so với cùng kỳ. Cán cân thương mại hàng hóa tháng Mười ước tính xuất siêu 7,31 tỷ USD. "
      "Vốn đầu tư thực hiện từ nguồn ngân sách Nhà nước tháng Mười ước đạt 95,2 nghìn tỷ đồng, tăng 30,1% so với cùng kỳ. Tính chung "
      "10 tháng, vốn đầu tư thực hiện từ nguồn ngân sách Nhà nước ước đạt 650,4 nghìn tỷ đồng, bằng 62,3% kế hoạch năm. "
      "Trong tháng Mười, cả nước có hơn 18,9 nghìn doanh nghiệp thành lập mới, gần 9,2 nghìn doanh nghiệp quay trở lại hoạt động. "
      "Khách quốc tế đến nước ta tháng Mười đạt gần 1,99 triệu lượt. Tổng vốn đầu tư nước ngoài đăng ký vào Việt Nam tính đến "
      "ngày 31/10/2026 đạt 31,52 tỷ USD. Vốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam 10 tháng ước đạt 24,08 tỷ USD.")


def test_so_va_dau():
    assert nso.so("1.010,55") == 1010.55 and nso.dau("giảm", "0,15") == -0.15 and nso.dau("tăng", "3") == 3.0


def test_ky_tu_url_thang_va_quy():
    u = "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-va-10-thang-nam-2026/"
    assert nso.ky_tu_url(u) == (pd.Timestamp("2026-10-01"), False)
    u = "https://www.nso.gov.vn/bai-top/2026/01/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-hai-va-12-thang-nam-2025/"
    assert nso.ky_tu_url(u)[0] == pd.Timestamp("2025-12-01")       # báo cáo tháng 12 đăng đầu năm sau
    assert nso.ky_tu_url("https://www.nso.gov.vn/x/2026/10/thong-cao-kinh-te-xa-hoi-quy-iii-nam-2026/") == \
        (pd.Timestamp("2026-09-01"), True)
    assert nso.ky_tu_url("https://www.nso.gov.vn/tin-khac/") == (None, False)
    b = "https://www.nso.gov.vn/bai-top/"
    assert nso.ky_tu_url(b + "2026/02/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-mot-nam-2026/") == (pd.Timestamp("2026-01-01"), False)
    assert nso.ky_tu_url(b + "2026/07/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-ii-va-sau-thang-dau-nam-2026/") == \
        (pd.Timestamp("2026-06-01"), True)
    assert nso.ky_tu_url(b + "2026/06/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-nam-va-5-thang-dau-nam-2025-2/")[0] == \
        pd.Timestamp("2026-05-01")                                   # slug ghi nhầm năm → theo thư mục đăng
    assert nso.ky_tu_url(nso.DS + "page/7/?paged=2") == (None, False)


def test_doc_bao_cao_thang():
    d = nso.doc(BC)
    assert d["cpi_mom"] == 0.25 and d["cpi_ytd"] == 3.10 and d["cpi_yoy"] == 5.08 and d["cpi_bq"] == 3.95
    assert d["lp_cb_bq"] == 3.40 and d["vang_yoy"] == 48.30 and d["usd_mom"] == -0.15 and d["usd_yoy"] == 2.64
    assert d["iip_yoy"] == 14.4 and d["ban_le"] == 612.3 and d["ban_le_yoy"] == 10.5
    assert d["xk"] == 54.79 and d["xk_yoy"] == 26.0 and d["nk"] == 47.48 and d["can_can"] == 7.31
    assert d["nsnn"] == 95.2 and d["nsnn_lk"] == 650.4 and d["nsnn_kh"] == 62.3
    assert d["dn_moi"] == 18900 and d["dn_quay_lai"] == 9200 and d["khach"] == 1.99e6
    assert d["fdi_dk"] == 31.52 and d["fdi_th"] == 24.08
    q = nso.doc("GDP quý III/2026 ước tính tăng 9,95% so với cùng kỳ năm trước, trong đó khu vực nông, lâm nghiệp và thủy sản "
                "tăng 3,82%; khu vực công nghiệp và xây dựng tăng 12,10%; khu vực dịch vụ tăng 9,40%.")
    assert q == {"gdp_yoy": 9.95, "gdp_nn": 3.82, "gdp_cn": 12.10, "gdp_dv": 9.40}
    assert "cpi_yoy" not in nso.doc("Chỉ số giá tiêu dùng (CPI) tháng Mười tăng mạnh")      # không khớp → bỏ, không đoán
    # các kiểu câu thật đã gặp (2025–2026): tách câu, "tháng 4/2025", "tháng Mười Một", "; tăng", "so với tháng Năm"
    a = nso.doc("Chỉ số giá tiêu dùng (CPI) tháng 4/2025 tăng 0,07% so với tháng trước. CPI tháng Tư tăng 1,37% so với tháng 12/2024 "
                "và tăng 3,12% so với cùng kỳ năm trước. Bình quân bốn tháng đầu năm 2025, CPI tăng 3,2% so với cùng kỳ năm trước; "
                "lạm phát cơ bản tăng 3,05%. – Chỉ số giá vàng tháng 4/2025 tăng 10,54% so với tháng trước; tăng 37,14% so với cùng "
                "kỳ năm trước; tăng 22,43% so với tháng 12/2024; bình quân bốn tháng đầu năm 2025 tăng 32,85%. – Chỉ số giá đô la Mỹ "
                "tháng 4/2025 tăng 0,97% so với tháng trước; tăng 3,17% so với cùng kỳ năm trước; tăng 1,9% so với tháng 12/2024.")
    assert (a["cpi_mom"], a["cpi_ytd"], a["cpi_yoy"], a["cpi_bq"], a["lp_cb_bq"]) == (0.07, 1.37, 3.12, 3.2, 3.05)
    assert (a["vang_mom"], a["vang_yoy"], a["vang_ytd"], a["usd_yoy"], a["usd_ytd"]) == (10.54, 37.14, 22.43, 3.17, 1.9)
    b = nso.doc("Chỉ số giá tiêu dùng (CPI) tháng Mười Một tăng 0,45% so với tháng trước; tăng 3,28% so với tháng 12/2024; tăng "
                "3,58% so với cùng kỳ năm trước. Bình quân mười một tháng năm 2025, CPI tăng 3,29% so với cùng kỳ năm trước. "
                "Chỉ số giá vàng tháng Sáu giảm 8,46% so với tháng Năm; tăng 24,11% so với cùng kỳ năm trước; giảm 2,72% so với tháng "
                "12/2025; bình quân quý II/2026 tăng 36,84%. Theo số liệu sơ bộ, cán cân thương mại hàng hóa tháng Mười Một xuất siêu "
                "1,09 tỷ USD.")
    assert (b["cpi_yoy"], b["cpi_ytd"], b["cpi_bq"], b["vang_mom"], b["vang_yoy"], b["can_can"]) == (3.58, 3.28, 3.29, -8.46, 24.11, 1.09)
    nam = nso.doc(nso.chu("<p>Tổng mức bán lẻ hàng ho\u0301a và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Chín năm "
                          "2026 ước đạt 690,6\u200b nghìn tỷ&nbsp;đồng, tăng 1,7% so với tháng trước và tăng 14,1% so với cùng kỳ</p>"))
    assert nam == {"ban_le": 690.6, "ban_le_yoy": 14.1}              # "tháng Chín năm 2026", dấu tổ hợp, ký tự vô hình


def test_kiem_bo_so_mau_thuan():
    df = pd.DataFrame({"xk": [40.0, 41.0, 300.0, 42.0], "nk": [38.0, 30.0, 35.0, float("nan")],
                       "can_can": [2.0, 2.0, 1.0, 3.0], "gdp_nn": [3.1, 3.2, 3.3, 3.4], "dn_moi": [15000, 150000, 16000, 17000]},
                      index=pd.to_datetime(["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01"]))
    k = nso.kiem(df)
    assert k.loc["2026-06-01", "nk"] == 38.0 and math.isnan(k.loc["2026-07-01", "xk"])      # 41 − 30 ≠ 2 → bỏ cả 3
    assert math.isnan(k.loc["2026-07-01", "can_can"]) and math.isnan(k.loc["2026-08-01", "xk"])   # ngoài 5–150
    assert k.loc["2026-09-01", "nk"] == 39.0                                                  # bù = xuất − cán cân
    assert k.gdp_nn.dropna().index.month.tolist() == [6, 9] and math.isnan(k.loc["2026-07-01", "dn_moi"])


def test_tai_dem_chi_doc_bao_cao_moi():
    u10 = "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-va-10-thang-nam-2026/"
    u9 = "https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-chin-va-9-thang-nam-2026/"
    da = []

    def lay(u):
        da.append(u)
        if u == nso.DS:
            return f'<a href="{u10}">a</a> <a href="{u9}">b</a> <a href="{u10}">a</a>'
        if u == nso.DS + "?paged=2":
            return f'<a href="{u9}">b</a>'                           # không có báo cáo mới → dừng, không đọc trang 3'
        if u == u10:
            return f"<p>{BC}</p>"
        if u == u9:
            return "<p>Kim ngạch xuất khẩu hàng hóa tháng Chín ước đạt 50,0 tỷ USD.</p>"
        raise OSError("hết trang")

    df, dem = nso.tai_dem(lay, {}, trang=5)
    assert nso.DS + "?paged=3" not in da and set(dem) == {u10, u9} and dem[u10]["_ky"] == "2026-10" and df.loc["2026-09-01", "xk"] == 50.0
    assert df.loc["2026-10-01", "cpi_yoy"] == 5.08 and df.index.is_monotonic_increasing
    da.clear()
    df2, _ = nso.tai_dem(lay, dem, trang=1)
    assert da[0] == nso.DS and u10 not in da and df2.equals(df)      # báo cáo đã đọc không tải lại
    cu = {k: {**v, "_v": 1} for k, v in dem.items()}
    da.clear()
    nso.tai_dem(lay, cu, trang=1)
    assert u10 in da                                                 # đệm của bộ đọc cũ → đọc lại

    def loi(u):                                                      # trang chặn khi đọc lại → giữ bản đọc cũ
        if u == nso.DS:
            return f'<a href="{u10}">a</a> <a href="{u9}">b</a>'
        raise OSError("429")
    df3, dem3 = nso.tai_dem(loi, cu, trang=1)
    assert set(dem3) == {u10, u9} and df3.loc["2026-10-01", "cpi_yoy"] == 5.08


def test_tin_dung_nhnn():
    mau = "<table><tr><td>Tháng</td></tr><tr><td>TỔNG CỘNG</td><td></td><td></td></tr></table>"
    that = ("<p>Dư nợ tín dụng đối với nền kinh tế Tháng 8 năm 2026</p><table><tr><th>Chỉ tiêu</th><th>Dư nợ (tỷ đồng)</th>"
            "<th>Tốc độ tăng so với cuối năm trước (%)</th></tr><tr><td>Nông nghiệp</td><td>1.000</td><td>5,0</td></tr>"
            "<tr><td>TỔNG CỘNG</td><td>20.489.434</td><td>10,19</td></tr></table>")
    assert nso.tin_dung(mau + that) == [(pd.Timestamp("2026-08-01"), 20489434.0, 10.19)]


def test_tin_rss():
    xml = ("<rss><channel><item><title><![CDATA[NHNN giữ nguyên lãi suất &amp; tỷ giá]]></title>"
           "<link>https://cafef.vn/a-188.chn</link><pubDate>Wed, 25 Nov 2026 03:15:00 GMT</pubDate></item>"
           "<item><title>Tin lạ</title><link>javascript:alert(1)</link></item>"
           "<item><title>Không ngày</title><link>https://cafef.vn/b.chn</link></item></channel></rss>")
    t = nso.tin_rss(xml)
    assert t == [{"t": "NHNN giữ nguyên lãi suất & tỷ giá", "u": "https://cafef.vn/a-188.chn", "d": "2026-11-25 10:15"},
                 {"t": "Không ngày", "u": "https://cafef.vn/b.chn", "d": ""}]
    assert len(nso.tin_rss(xml, so_tin=1)) == 1


def test_thu_chi_ngan_sach_va_dn_rut_lui():
    """Câu thu / chi NSNN lũy kế 3 kiểu (T6: "lũy kế … đạt", T9: "Tính chung … ước đạt", T10: chữ thường) – bỏ qua số tháng đứng trước."""
    t9 = ("Tổng thu ngân sách Nhà nước tháng Chín ước đạt 162,7 nghìn tỷ đồng. Lũy kế tổng thu ngân sách Nhà nước chín tháng năm "
          "2026 ước đạt 2.187,3 nghìn tỷ đồng, bằng 86,5% dự toán năm và tăng 12,1%. Tổng chi ngân sách Nhà nước tháng Chín ước đạt "
          "256,8 nghìn tỷ đồng. Tính chung chín tháng năm 2026, chi ngân sách Nhà nước ước đạt 1.873,7 nghìn tỷ đồng, bằng 59,3% dự "
          "toán năm. Số doanh nghiệp rút lui khỏi thị trường là 172,0 nghìn doanh nghiệp, giảm 1,7%")
    t6 = ("8. Thu, chi ngân sách Nhà nước Tổng thu ngân sách Nhà nước tháng Sáu ước đạt 205,0 nghìn tỷ đồng, lũy kế tổng thu ngân sách Nhà nước sáu tháng đầu năm "
          "2026 đạt 1.568,2 nghìn tỷ đồng, bằng 62,0% dự toán năm. Tổng chi ngân sách Nhà nước tháng Sáu ước đạt 292,3 nghìn tỷ "
          "đồng, lũy kế sáu tháng đầu năm 2026 đạt 1.149,1 nghìn tỷ đồng, bằng 36,4% dự toán năm")
    for t, kq in ((t9, (2187.3, 86.5, 1873.7, 59.3, 172000)), (t6, (1568.2, 62.0, 1149.1, 36.4, None))):
        d = nso.doc(t)
        assert tuple(d.get(k) for k in ("thu_lk", "thu_dt", "chi_lk", "chi_dt", "dn_rut_lui")) == kq


def test_m2_nhnn():
    h = ('<h3>Tổng phương tiện thanh toán và Tiền gửi của khách hàng tại TCTD Tháng 8 năm 2026</h3><table>'
         '<tr><td>Tổng phương tiện thanh toán (*)</td><td>20.774.696</td><td>6,84</td></tr>'
         '<tr><td>- Tiền gửi của các TCKT</td><td>6.337.186</td><td>2,54</td></tr>'
         '<tr><td>- Tiền gửi của dân cư</td><td>11.434.266</td><td>10,63</td></tr></table>')
    assert nso.m2(h) == [(pd.Timestamp("2026-08-01"), 20774696.0, 6.84, 10.63)]
    assert nso.m2("<p>Trang lỗi</p>") == []
