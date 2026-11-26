# -*- coding: utf-8 -*-
"""
KINH TẾ VĨ MÔ THEO CHỦ ĐỀ – tab "Vĩ mô" dạng bảng chỉ tiêu (25/11/2026, chủ quỹ gửi ảnh FireAnt "Kinh tế vĩ mô": "trình bày
như này đi"): điểm nhấn · chủ đề (đếm chỉ tiêu) · thẻ tổng quan có xu hướng 24 kỳ · nhịp kinh tế (bản đồ nhiệt 18 tháng, màu
theo độ lệch so trung bình 5 năm và hướng tốt của chỉ tiêu) · lịch công bố · bản tin tháng · bảng chỉ tiêu (kỳ · giá trị · đơn vị
· kỳ trước · cùng kỳ) + biểu đồ lịch sử khi chạm.

Thuần (không mạng) – vi_mo_web tải chuỗi rồi gọi dung_kt(). Nguồn đã dò + kiểm 25/11/2026 (thi_truong/vi_mo_nguon.do_vn):
  TradingView ECONOMICS (gốc Cục Thống kê / NHNN / Hải quan …) – ngày nến đã sửa (lai_suat.TV_BU_GIO); World Bank (năm).
  Cục Thống kê – báo cáo tình hình KT-XH tháng / quý (thi_truong/nso: chỉ số giá vàng / USD, CPI so tháng 12 / bình quân, vốn
  NSNN, doanh nghiệp, FDI đăng ký, GDP 3 khu vực; nối tháng mới cho xuất / nhập khẩu khi TradingView trễ); NHNN – tín dụng.
  KHÔNG dùng PMI (S&P Global cấm phát lại số liệu khi chưa được phép – ghi trong thông cáo).
  KHÔNG dùng: IMF (403), PMI VN (không có mã), tín dụng (không có nguồn mở), GDP theo ngành của TradingView (đổi năm gốc
  Q1/2026 – giá trị nhảy +35 %, so cùng kỳ sai), VNGBV (ngân sách – số 2024 bất thường), VNDIR / VNCCI (ngừng 2023 / 2021).
  Bỏ chỉ số CPI / CPI giao thông của TradingView (đổi năm gốc 2026 – so cùng kỳ ra −9,6 %, kiểm 26/11/2026).
  CPI so cùng kỳ: TradingView VNIRYY trễ 1 tháng → nối tháng mới bằng chuỗi CPI tháng/tháng (VNIRMM) khi 12 tháng trùng lệch
  ≤ 0,1 điểm (in log).
Tham khảo – không phải tín hiệu mua bán.
"""
import math

import pandas as pd

# (khoá, tên, mô tả)
CHU_DE = [("tq", "Tổng quan", "12 chỉ số chính: số mới nhất, thay đổi, xu hướng 24 kỳ"),
          ("ban_tin", "Bản tin tháng", "tóm tắt số liệu tháng mới nhất – dựng tự động từ số liệu"),
          ("tang_truong", "Tăng trưởng", "GDP theo quý, GDP năm, thu nhập đầu người, đầu tư, nợ công"),
          ("san_xuat", "Sản xuất", "sản xuất công nghiệp, khai thác dầu thô"),
          ("gia", "Lạm phát & giá", "CPI, lạm phát lõi, giá sản xuất, giá xăng"),
          ("tien_te", "Tiền tệ & lãi suất", "lãi điều hành, liên ngân hàng, lợi suất TPCP, cung tiền, dự trữ ngoại hối, tỷ giá"),
          ("thuong_mai", "Thương mại & vốn ngoại", "xuất nhập khẩu, cán cân thương mại, FDI, cán cân vãng lai"),
          ("tieu_dung", "Tiêu dùng & du lịch", "bán lẻ, khách quốc tế"),
          ("lao_dong", "Lao động & dân số", "thất nghiệp, lao động, thu nhập, lương tối thiểu, dân số"),
          ("the_gioi", "Thế giới", "Mỹ, Trung Quốc, châu Âu, Nhật, Hàn Quốc, Thái Lan"),
          ("vang", "Vàng & tỷ giá", "vàng thế giới, SJC, nhẫn, chênh lệch, tỷ giá – biểu đồ"),
          ("hh", "Hàng hoá", "22 hàng hoá thế giới – giá, % thay đổi, ngành VN liên quan")]

TC = "Cục Thống kê"
# Chỉ tiêu: (khoá, chủ đề, tên, nguồn, đơn vị, chia, kiểu đổi, tần suất, hướng tốt, mô tả gốc)
#   nguồn: "s:KHÓA" chuỗi vi_mo_web đã tải · "tv:MÃ" TradingView ECONOMICS · "wb:MÃ" World Bank · "yy:NGUỒN" % so cùng kỳ
#          tính từ chuỗi mức · "ld:NGUỒN" chuỗi lũy kế năm (so cùng kỳ theo ngày, kỳ trước = phần tăng trong tháng)
#   kiểu đổi: "pt" điểm % (chênh) · "d" chênh theo đơn vị · "%" phần trăm
#   tần suất: D ngày · M tháng · Q quý · Y năm;  hướng: +1 tăng là tốt · −1 tăng là xấu · 0 trung tính
CHI_TIEU = [
    # Tăng trưởng
    ("vn_gdp", "tang_truong", "Tăng trưởng GDP", "s:vn_gdp", "%", 1, "pt", "Q", 1, f"GDP giá so sánh so cùng kỳ · quý · {TC}"),
    ("vn_gdp_nam", "tang_truong", "Tăng trưởng GDP năm", "wb:NY.GDP.MKTP.KD.ZG", "%", 1, "pt", "Y", 1, "năm · World Bank"),
    ("vn_gdp_usd", "tang_truong", "GDP (USD)", "wb:NY.GDP.MKTP.CD", "tỷ USD", 1e9, "%", "Y", 1, "năm · World Bank"),
    ("vn_gdp_dn", "tang_truong", "GDP bình quân đầu người", "wb:NY.GDP.PCAP.CD", "USD", 1, "%", "Y", 1, "năm · World Bank"),
    ("vn_gdp_ppp", "tang_truong", "GDP đầu người (PPP)", "wb:NY.GDP.PCAP.PP.CD", "USD PPP", 1, "%", "Y", 1,
     "theo sức mua tương đương · năm · World Bank"),
    ("vn_gfcf", "tang_truong", "Tích luỹ tài sản cố định", "tv:VNGFCF", "nghìn tỷ đồng", 1e12, "%", "Y", 1,
     "giá hiện hành · năm · TradingView ECONOMICS"),
    ("vn_gdp_nn", "tang_truong", "GDP nông, lâm, thủy sản (YoY)", "s:nso_gdp_nn", "%", 1, "pt", "Q", 1, f"quý · {TC} – báo cáo quý"),
    ("vn_gdp_cn", "tang_truong", "GDP công nghiệp – xây dựng (YoY)", "s:nso_gdp_cn", "%", 1, "pt", "Q", 1, f"quý · {TC} – báo cáo quý"),
    ("vn_gdp_dv", "tang_truong", "GDP dịch vụ (YoY)", "s:nso_gdp_dv", "%", 1, "pt", "Q", 1, f"quý · {TC} – báo cáo quý"),
    ("vn_nsnn", "tang_truong", "Giải ngân vốn NSNN (tháng)", "s:nso_nsnn", "nghìn tỷ đồng", 1, "%", "M", 1,
     f"vốn đầu tư thực hiện từ ngân sách nhà nước · {TC}"),
    ("vn_nsnn_kh", "tang_truong", "Vốn NSNN lũy kế / kế hoạch năm", "ld:s:nso_nsnn_kh", "% KH", 1, "pt", "M", 1,
     f"cộng dồn từ đầu năm · {TC}"),
    ("vn_no_cong", "tang_truong", "Nợ Chính phủ / GDP", "tv:VNGDG", "% GDP", 1, "pt", "Y", -1, "năm · TradingView ECONOMICS"),
    # Sản xuất
    ("vn_sxcn", "san_xuat", "Sản xuất công nghiệp (IIP)", "s:vn_sxcn", "%", 1, "pt", "M", 1, f"so cùng kỳ · tháng · {TC}"),
    ("vn_dn_moi", "san_xuat", "Doanh nghiệp thành lập mới", "s:nso_dn_moi", "doanh nghiệp", 1, "%", "M", 1, f"tháng · {TC}"),
    ("vn_dn_quay_lai", "san_xuat", "Doanh nghiệp quay lại hoạt động", "s:nso_dn_quay_lai", "doanh nghiệp", 1, "%", "M", 1,
     f"tháng · {TC}"),
    ("vn_dau_tho", "san_xuat", "Khai thác dầu thô", "tv:VNCOP", "nghìn thùng/ngày", 1e3, "%", "M", 0,
     "tháng · TradingView ECONOMICS"),
    # Lạm phát & giá
    ("vn_cpi", "gia", "Lạm phát (CPI YoY)", "s:vn_cpi", "%", 1, "pt", "M", -1, f"CPI so cùng kỳ · tháng · {TC}"),
    ("vn_cpi_mom", "gia", "Lạm phát (CPI MoM)", "tv:VNIRMM", "%", 1, "pt", "M", -1, f"CPI so tháng trước · {TC}"),
    ("vn_cpi_loi", "gia", "Lạm phát lõi", "s:vn_cpi_loi", "%", 1, "pt", "M", -1, f"so cùng kỳ · tháng · {TC}"),
    ("vn_cpi_ytd", "gia", "CPI so tháng 12 năm trước", "s:nso_cpi_ytd", "%", 1, "pt", "M", -1, f"{TC} – báo cáo tháng"),
    ("vn_cpi_bq", "gia", "CPI bình quân từ đầu năm (YoY)", "s:nso_cpi_bq", "%", 1, "pt", "M", -1, f"{TC} – báo cáo tháng"),
    ("vn_lp_cb_bq", "gia", "Lạm phát cơ bản bình quân", "s:nso_lp_cb_bq", "%", 1, "pt", "M", -1, f"{TC} – báo cáo tháng"),
    ("vn_vang_cs", "gia", "Chỉ số giá vàng (YoY)", "s:nso_vang_yoy", "%", 1, "pt", "M", 0, f"{TC} – báo cáo tháng"),
    ("vn_usd_cs", "gia", "Chỉ số giá đô la Mỹ (YoY)", "s:nso_usd_yoy", "%", 1, "pt", "M", -1, f"{TC} – báo cáo tháng"),
    ("vn_ppi", "gia", "Giá sản xuất (PPI, YoY)", "yy:tv:VNPPI", "%", 1, "pt", "Q", 0, f"tính từ chỉ số PPI · quý · {TC}"),
    ("vn_xang", "gia", "Giá xăng", "tv:VNGASP", "USD/lít", 1, "%", "M", -1, "tháng · TradingView ECONOMICS"),
    ("vn_lp_nam", "gia", "Lạm phát năm", "wb:FP.CPI.TOTL.ZG", "%", 1, "pt", "Y", -1, "năm · World Bank"),
    # Tiền tệ & lãi suất
    ("vn_dh", "tien_te", "Lãi suất điều hành (tái cấp vốn)", "s:vn_dh", "%/năm", 1, "pt", "M", 0, "NHNN · tháng"),
    ("vn_lnh", "tien_te", "Lãi suất liên ngân hàng", "s:vn_lnh", "%/năm", 1, "pt", "M", -1, "NHNN · tháng"),
    ("vn_1n", "tien_te", "Lợi suất TPCP 1 năm", "s:vn_1n", "%/năm", 1, "pt", "D", 0, "HNX – đường cong lợi suất · ngày"),
    ("vn_10n", "tien_te", "Lợi suất TPCP 10 năm", "s:vn_10n", "%/năm", 1, "pt", "D", 0, "HNX – đường cong lợi suất · ngày"),
    ("vn_tin_dung", "tien_te", "Tín dụng (tăng từ đầu năm)", "s:td_tang", "%", 1, "pt", "M", 0,
     "dư nợ tín dụng đối với nền kinh tế so cuối năm trước · NHNN"),
    ("vn_du_no", "tien_te", "Dư nợ tín dụng nền kinh tế", "s:td_tong", "nghìn tỷ đồng", 1e3, "%", "M", 0, "NHNN"),
    ("vn_m2", "tien_te", "Cung tiền M2", "tv:VNM2", "nghìn tỷ đồng", 1e12, "%", "Y", 0, "năm · TradingView ECONOMICS"),
    ("vn_dtnh", "tien_te", "Dự trữ ngoại hối", "s:vn_dtnh", "tỷ USD", 1e9, "%", "M", 1, "tháng · TradingView ECONOMICS"),
    ("usdvnd", "tien_te", "Tỷ giá USD/VND", "s:usdvnd", "đồng", 1, "%", "D", -1, "thị trường · ngày · Yahoo"),
    # Thương mại & vốn ngoại
    ("vn_xk", "thuong_mai", "Xuất khẩu", "s:vn_xk", "tỷ USD", 1e9, "%", "M", 1, "tháng · Hải quan / Cục Thống kê"),
    ("vn_nk", "thuong_mai", "Nhập khẩu", "tv:VNIMP", "tỷ USD", 1e9, "%", "M", 0, "tháng · Hải quan / Cục Thống kê"),
    ("vn_bot", "thuong_mai", "Cán cân thương mại", "s:vn_bot", "tỷ USD", 1e9, "d", "M", 1, "hàng hoá · tháng · Hải quan"),
    ("vn_fdi", "thuong_mai", "FDI giải ngân (lũy kế)", "ld:s:vn_fdi", "tỷ USD", 1e9, "%", "M", 1,
     f"cộng dồn từ đầu năm · tháng · {TC}"),
    ("vn_fdi_dk", "thuong_mai", "FDI đăng ký (tổng, lũy kế)", "ld:s:nso_fdi_dk", "tỷ USD", 1, "%", "M", 1,
     f"đăng ký mới + điều chỉnh + góp vốn mua cổ phần · cộng dồn năm · {TC}"),
    ("vn_ca", "thuong_mai", "Cán cân vãng lai", "tv:VNCA", "tỷ USD", 1e9, "d", "Q", 1, "quý · NHNN (TradingView ECONOMICS)"),
    ("vn_ca_gdp", "thuong_mai", "Cán cân vãng lai / GDP", "wb:BN.CAB.XOKA.GD.ZS", "% GDP", 1, "pt", "Y", 1, "năm · World Bank"),
    ("vn_xk_gdp", "thuong_mai", "Xuất khẩu / GDP", "wb:NE.EXP.GNFS.ZS", "% GDP", 1, "pt", "Y", 0, "năm · World Bank"),
    # Tiêu dùng & du lịch
    ("vn_banle", "tieu_dung", "Bán lẻ (YoY)", "s:vn_banle", "%", 1, "pt", "M", 1,
     f"tổng mức bán lẻ hàng hoá & dịch vụ so cùng kỳ · tháng · {TC}"),
    ("vn_ban_le_gt", "tieu_dung", "Tổng mức bán lẻ (tháng)", "s:nso_ban_le", "nghìn tỷ đồng", 1, "%", "M", 1,
     f"hàng hoá & dịch vụ tiêu dùng, giá hiện hành · {TC}"),
    ("vn_khach", "tieu_dung", "Khách quốc tế", "tv:VNTA", "nghìn lượt", 1e3, "%", "M", 1, f"tháng · {TC}"),
    # Lao động & dân số
    ("vn_that_nghiep", "lao_dong", "Tỷ lệ thất nghiệp", "tv:VNUR", "%", 1, "pt", "Y", -1, "năm · TradingView ECONOMICS"),
    ("vn_lao_dong", "lao_dong", "Lao động có việc làm", "tv:VNEMP", "triệu người", 1e6, "%", "Q", 1, f"quý · {TC}"),
    ("vn_thu_nhap", "lao_dong", "Thu nhập bình quân lao động", "tv:VNWAG", "triệu đồng/tháng", 1e6, "%", "Q", 1, f"quý · {TC}"),
    ("vn_luong_tt", "lao_dong", "Lương tối thiểu vùng I", "tv:VNMW", "triệu đồng/tháng", 1e6, "%", "M", 0,
     "theo lần điều chỉnh · TradingView ECONOMICS"),
    ("vn_dan_so", "lao_dong", "Dân số", "tv:VNPOP", "triệu người", 1e6, "%", "Y", 0, "năm · TradingView ECONOMICS"),
    # Thế giới
    ("us_gdp", "the_gioi", "Mỹ – GDP (YoY)", "tv:USGDPYY", "%", 1, "pt", "Q", 1, "quý · BEA"),
    ("us_cpi", "the_gioi", "Mỹ – Lạm phát CPI", "s:us_cpi", "%", 1, "pt", "M", -1, "so cùng kỳ · tháng · BLS"),
    ("us_cpi_loi", "the_gioi", "Mỹ – Lạm phát lõi", "tv:USCIR", "%", 1, "pt", "M", -1, "so cùng kỳ · tháng · BLS"),
    ("us_ur", "the_gioi", "Mỹ – Thất nghiệp", "tv:USUR", "%", 1, "pt", "M", -1, "tháng · BLS"),
    ("us_nfp", "the_gioi", "Mỹ – Việc làm phi nông nghiệp", "tv:USNFP", "nghìn", 1e3, "d", "M", 1, "thay đổi trong tháng · BLS"),
    ("us_ff", "the_gioi", "Mỹ – Fed funds thực tế", "s:us_ff", "%/năm", 1, "pt", "D", 0, "ngày · NY Fed"),
    ("us_10n", "the_gioi", "Mỹ – Lợi suất 10 năm", "s:us_10n", "%/năm", 1, "pt", "D", 0, "ngày · Bộ Tài chính Mỹ"),
    ("us_vix", "the_gioi", "VIX – biến động S&P 500", "s:us_vix", "điểm", 1, "%", "D", -1, "ngày · CBOE"),
    ("dxy", "the_gioi", "Chỉ số USD (DXY)", "s:dxy", "điểm", 1, "%", "D", 0, "ngày · ICE"),
    ("cn_gdp", "the_gioi", "Trung Quốc – GDP (YoY)", "tv:CNGDPYY", "%", 1, "pt", "Q", 1, "quý · NBS"),
    ("cn_cpi", "the_gioi", "Trung Quốc – Lạm phát", "tv:CNIRYY", "%", 1, "pt", "M", 0, "so cùng kỳ · tháng · NBS"),
    ("cn_sxcn", "the_gioi", "Trung Quốc – SXCN (YoY)", "tv:CNIPYY", "%", 1, "pt", "M", 1, "tháng · NBS"),
    ("cn_banle", "the_gioi", "Trung Quốc – Bán lẻ (YoY)", "tv:CNRSYY", "%", 1, "pt", "M", 1, "tháng · NBS"),
    ("cn_ls", "the_gioi", "Trung Quốc – Lãi suất LPR 1 năm", "tv:CNINTR", "%/năm", 1, "pt", "M", 0, "PBOC"),
    ("usdcny", "the_gioi", "USD/CNY", "s:usdcny", "tệ", 1, "%", "D", 0, "ngày · Yahoo"),
    ("eu_gdp", "the_gioi", "Châu Âu – GDP (YoY)", "tv:EUGDPYY", "%", 1, "pt", "Q", 1, "khu vực đồng euro · quý · Eurostat"),
    ("eu_cpi", "the_gioi", "Châu Âu – Lạm phát", "tv:EUIRYY", "%", 1, "pt", "M", -1, "khu vực đồng euro · tháng · Eurostat"),
    ("eu_ls", "the_gioi", "Châu Âu – Lãi suất ECB", "tv:EUINTR", "%/năm", 1, "pt", "M", 0, "ECB"),
    ("eu_ur", "the_gioi", "Châu Âu – Thất nghiệp", "tv:EUUR", "%", 1, "pt", "M", -1, "tháng · Eurostat"),
    ("jp_gdp", "the_gioi", "Nhật – GDP (YoY)", "tv:JPGDPYY", "%", 1, "pt", "Q", 1, "quý"),
    ("jp_cpi", "the_gioi", "Nhật – Lạm phát", "tv:JPIRYY", "%", 1, "pt", "M", 0, "tháng"),
    ("jp_ls", "the_gioi", "Nhật – Lãi suất BOJ", "tv:JPINTR", "%/năm", 1, "pt", "M", 0, "BOJ"),
    ("kr_gdp", "the_gioi", "Hàn Quốc – GDP (YoY)", "tv:KRGDPYY", "%", 1, "pt", "Q", 1, "quý"),
    ("kr_cpi", "the_gioi", "Hàn Quốc – Lạm phát", "tv:KRIRYY", "%", 1, "pt", "M", -1, "tháng"),
    ("kr_ls", "the_gioi", "Hàn Quốc – Lãi suất BOK", "tv:KRINTR", "%/năm", 1, "pt", "M", 0, "BOK"),
    ("th_gdp", "the_gioi", "Thái Lan – GDP (YoY)", "tv:THGDPYY", "%", 1, "pt", "Q", 1, "quý"),
    ("th_cpi", "the_gioi", "Thái Lan – Lạm phát", "tv:THIRYY", "%", 1, "pt", "M", -1, "tháng"),
    ("th_ls", "the_gioi", "Thái Lan – Lãi suất BOT", "tv:THINTR", "%/năm", 1, "pt", "M", 0, "BOT"),
]
KHONG_CU = {"vn_luong_tt"}                     # đổi theo lần điều chỉnh (không định kỳ) – không gắn "cũ"
HAN_CU = {"vn_tin_dung": 135, "vn_du_no": 135}                     # NHNN công bố tín dụng trễ ~3 tháng (T8 có vào cuối T11)
TONG_QUAN = ["vn_gdp", "vn_cpi", "vn_cpi_loi", "vn_tin_dung", "vn_sxcn", "vn_banle", "vn_xk", "vn_bot", "vn_fdi", "vn_lnh",
             "vn_10n", "usdvnd"]
# Mục tiêu năm 2026 (Nghị quyết Quốc hội về kế hoạch phát triển KT-XH 2026): GDP từ 10 %, CPI khoảng 4,5 %
MUC_TIEU = {"vn_gdp": (10.0, "tăng"), "vn_cpi": (4.5, "trần")}
# Nhịp kinh tế: (khoá chỉ tiêu | khoá dẫn xuất, tên hàng, hướng)
NHIP = [("vn_cpi", "Lạm phát (CPI YoY)", -1), ("vn_cpi_loi", "Lạm phát lõi", -1), ("vn_sxcn", "Sản xuất công nghiệp", 1),
        ("vn_banle", "Bán lẻ (YoY)", 1), ("yy:vn_xk", "Xuất khẩu (cùng kỳ)", 1), ("vn_bot", "Cán cân thương mại", 1),
        ("yy:vn_fdi", "FDI giải ngân (cùng kỳ)", 1), ("yy:vn_khach", "Khách quốc tế (cùng kỳ)", 1),
        ("vn_lnh", "Lãi suất liên ngân hàng", -1), ("vn_dtnh", "Dự trữ ngoại hối", 1)]
# Lịch công bố: Cục Thống kê công bố số liệu tháng ngày 6 tháng sau (quý: ngày 6 tháng đầu quý sau); FOMC 2026 (lịch Fed)
FOMC_2026 = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
THU = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


# ------------------------------------------------------------------ tiện ích
def so_vn(x, le=2):
    """1234.5 → "1.234,50" (kiểu Việt Nam)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = f"{x:,.{le}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _s(x):
    s = pd.Series(x).dropna().astype(float).sort_index()
    return s[~s.index.duplicated(keep="last")]


def nhan_ky(d, ts, luy_ke=False):
    d = pd.Timestamp(d)
    if ts == "Q":
        return f"Q{(d.month - 1) // 3 + 1}/{d.year}"
    if ts == "Y":
        return f"{d.year}"
    if ts == "D":
        return f"{d:%d/%m/%Y}"
    return f"{d.month}T/{d.year}" if luy_ke else f"T{d.month}/{d.year}"


def theo_thang(s):
    """Chuỗi tháng (ngày bất kỳ trong tháng) → chỉ mục ngày 1 của tháng."""
    s = _s(s)
    s.index = s.index.to_period("M").to_timestamp()
    return s[~s.index.duplicated(keep="last")]


def cung_ky(s, d, ts):
    """Giá trị cùng kỳ năm trước (cho phép lệch ≤ 20 ngày; chuỗi ngày: giá cuối ở hoặc trước mốc)."""
    moc = pd.Timestamp(d) - pd.DateOffset(years=1)
    tr = s[s.index <= moc + pd.Timedelta(days=0 if ts == "D" else 20)]
    if not len(tr) or tr.index[-1] < moc - pd.Timedelta(days=7 if ts == "D" else 20):
        return None
    return float(tr.iloc[-1])


def so_cung_ky_pt(s, ts="M"):
    """Chuỗi mức → % so cùng kỳ (theo ngày, không theo số dòng)."""
    s = _s(s)
    out = {}
    for d, v in s.items():
        q = cung_ky(s, d, ts)
        if q:
            out[d] = (v / q - 1) * 100
    return pd.Series(out, dtype=float)


def doi(v, q, kieu):
    if v is None or q is None:
        return None
    if kieu == "%":
        return None if q == 0 else round((v / q - 1) * 100, 2)
    return round(v - q, 3)


def _le(v, dv):
    a = abs(v)
    if dv in ("đồng",) or a >= 10000:
        return 0
    if a >= 1000:
        return 0 if dv not in ("tỷ USD",) else 1
    if a >= 100:
        return 1
    return 2


def mo_rong_cpi(yy, mm):
    """CPI so cùng kỳ (VNIRYY, trễ) + CPI tháng/tháng (VNIRMM): nối các tháng mới bằng
    yy_t = ((1 + yy_{t−1}) × (1 + mm_t) / (1 + mm_{t−12})) − 1. Kiểm 12 tháng trùng – lệch lớn nhất > 0,1 điểm thì KHÔNG nối.
    → (chuỗi, số tháng nối, lệch lớn nhất | None)."""
    yy, mm = theo_thang(yy), theo_thang(mm)
    if not len(yy) or not len(mm):
        return yy, 0, None

    def tinh(t, truoc):
        a, b = mm.get(t), mm.get(t - pd.DateOffset(years=1))
        if a is None or b is None or truoc is None:
            return None
        return ((1 + truoc / 100) * (1 + a / 100) / (1 + b / 100) - 1) * 100
    lech = []
    for t in yy.index[-12:]:
        truoc = yy.get(t - pd.DateOffset(months=1))
        u = tinh(t, truoc)
        if u is not None:
            lech.append(abs(u - yy[t]))
    ml = max(lech) if lech else None
    if ml is None or ml > 0.1:
        return yy, 0, ml
    out, n, t = yy.copy(), 0, yy.index[-1]
    while (t + pd.DateOffset(months=1)) in mm.index:
        t2 = t + pd.DateOffset(months=1)
        u = tinh(t2, out[t])
        if u is None:
            break
        out[t2], n, t = round(u, 2), n + 1, t2
    return out.sort_index(), n, ml


def gon_ngay(s, nam=3):
    """Chuỗi ngày → [[ngày, v]]: theo ngày 3 năm gần nhất, theo tuần (giá cuối tuần) trước đó – trang nhẹ."""
    s = _s(s)
    if not len(s):
        return []
    moc = s.index[-1] - pd.DateOffset(years=nam)
    cu, moi = s[s.index < moc], s[s.index >= moc]
    if len(cu):
        cu = cu.groupby(cu.index.to_period("W-FRI")).last()
        cu.index = cu.index.to_timestamp(how="end").normalize()
        cu = cu[cu.index < moc]
    s = pd.concat([cu, moi]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return [[f"{d:%Y-%m-%d}", round(float(v), 4)] for d, v in s.items()]


# ------------------------------------------------------------------ một chỉ tiêu
def chi_tieu(spec, s, nguon="", hom_nay=None):
    """spec CHI_TIEU + chuỗi (đã chia đơn vị) → dict hàng bảng / thẻ."""
    k, cd, ten, ng, dv, _, kieu, ts, huong, mo = spec
    luy_ke = ng.startswith("ld:")
    s = _s(s)
    if not len(s):
        return None
    if ts in ("M",):
        s = theo_thang(s)
    d, v = s.index[-1], float(s.iloc[-1])
    q_truoc = float(s.iloc[-2]) if len(s) > 1 else None
    if q_truoc is not None and ts in ("M", "Q") and \
            s.index[-2] < d - pd.DateOffset(months=1 if ts == "M" else 3) - pd.Timedelta(days=20):
        q_truoc = None                                               # hụt kỳ liền trước (nguồn đọc từ chữ) → không so
    if luy_ke and d.month == 1:
        q_truoc = None                                               # lũy kế năm: tháng 1 là đầu kỳ mới
    kt = doi(v, q_truoc, kieu)
    ck = doi(v, cung_ky(s, d, ts), kieu)
    # xu hướng: 24 kỳ (chuỗi ngày: 1 năm, mỗi tuần 1 điểm)
    if ts == "D":
        w = s[s.index >= d - pd.DateOffset(years=1)]
        sp = w.groupby(w.index.to_period("W")).last().tolist()
    else:
        sp = s.iloc[-24:].tolist()
    r = {"k": k, "cd": cd, "ten": ten, "mo": mo, "dv": dv, "ky": nhan_ky(d, ts, luy_ke), "ngay": f"{d:%Y-%m-%d}",
         "gt": round(v, 4), "le": _le(v, dv), "kt": kt, "ck": ck, "kieu": kieu, "ts": ts, "huong": huong,
         "sp": [round(float(x), 4) for x in sp], "nguon": nguon, "ghi": "", "tot": 0}
    if hom_nay is not None:
        han = HAN_CU.get(k) or {"D": 10, "M": 95, "Q": 150, "Y": 550}[ts]   # số tháng công bố trễ tới ~75 ngày sau ngày 1
        r["cu"] = (pd.Timestamp(hom_nay) - d).days > han and k not in KHONG_CU
    # ghi chú + tốt / xấu
    if k in MUC_TIEU:
        mt, loai = MUC_TIEU[k]
        dat = v >= mt if loai == "tăng" else v <= mt
        r["tot"] = 1 if dat else -1
        r["ghi"] = (("Đạt" if dat else "Dưới") if loai == "tăng" else ("Trong" if dat else "Vượt")) + \
            f" mục tiêu {so_vn(mt, 1).rstrip('0').rstrip(',')}%"
    elif k == "vn_bot":
        n, dau = 0, v >= 0
        for x in reversed(s.tolist()):
            if (x >= 0) == dau:
                n += 1
            else:
                break
        r["ghi"] = ("Xuất siêu" if dau else "Nhập siêu") + f" · {n} tháng"
        r["tot"] = 1 if dau else -1
    elif luy_ke:
        thang = v - (q_truoc or 0) if q_truoc is not None or d.month == 1 else None
        if thang is not None:
            r["ghi"] = f"T{d.month}: {so_vn(thang, 2)} {dv}"
        r["tot"] = 0 if ck is None else (1 if ck > 0 else -1)
    elif ts == "D":
        w = s[s.index >= d - pd.DateOffset(years=1)]
        le = _le(v, dv)
        r["ghi"] = f"1 năm: {so_vn(w.min(), le)}–{so_vn(w.max(), le)}"
    elif ts in ("M", "Q") and len(s) > (12 if ts == "M" else 4):   # đủ 12 tháng / 4 quý trước mới so trung bình
        n = 12 if ts == "M" else 4
        tb = float(s.iloc[-1 - n:-1].mean())
        r["ghi"] = ("Trên" if v > tb else "Dưới" if v < tb else "Bằng") + \
            f" TB {n} {'tháng' if ts == 'M' else 'quý'} ({so_vn(tb, _le(tb, dv))})"
        if huong and abs(v - tb) > 1e-9:
            r["tot"] = 1 if (v - tb) * huong > 0 else -1
    elif ts == "Y" and q_truoc is not None:
        r["ghi"] = f"năm trước: {so_vn(q_truoc, _le(q_truoc, dv))}"
    return r


# ------------------------------------------------------------------ nhịp kinh tế
def nhip(ch, so_thang=18, nam=5):
    """ch: {khoá: Series tháng (đã chia đơn vị)} → {"thang": [...], "dong": [{k, ten, o: [mức −2..2 | None], moi}]}.
    Mức = (giá trị − TB 5 năm trước đó) / độ lệch chuẩn 5 năm × hướng: ≤ −1,5 xấu hơn nhiều · ≤ −0,5 xấu hơn · < 0,5 bình
    thường · < 1,5 tốt hơn · còn lại tốt hơn nhiều."""
    cuoi = None
    for k, _, _ in NHIP:
        s = ch.get(k)
        if s is not None and len(s):
            t = theo_thang(s).index[-1]
            cuoi = t if cuoi is None or t > cuoi else cuoi
    if cuoi is None:
        return {"thang": [], "dong": []}
    thang = [cuoi - pd.DateOffset(months=i) for i in range(so_thang - 1, -1, -1)]
    dong = []
    for k, ten, huong in NHIP:
        s = ch.get(k)
        if s is None or not len(s):
            continue
        s = theo_thang(s)
        o = []
        for t in thang:
            if t not in s.index:
                o.append(None)
                continue
            w = s[(s.index < t) & (s.index >= t - pd.DateOffset(years=nam))]
            if len(w) < 24 or not w.std():
                o.append(None)
                continue
            z = (s[t] - w.mean()) / w.std() * huong
            o.append(-2 if z <= -1.5 else -1 if z <= -0.5 else 0 if z < 0.5 else 1 if z < 1.5 else 2)
        v = float(s.iloc[-1])
        moi = (so_vn(v, 1) + "%") if k.startswith("yy:") else so_vn(v, 2 if abs(v) < 100 else 1)
        dong.append({"k": k, "ten": ten, "o": o, "moi": moi, "ky": nhan_ky(s.index[-1], "M")})
    return {"thang": [f"{t:%Y-%m}" for t in thang], "dong": dong}


# ------------------------------------------------------------------ lịch công bố
def lich(hom_nay, so=6):
    """Lịch dự kiến: Cục Thống kê ngày 6 hằng tháng (số liệu tháng trước; tháng 1/4/7/10 kèm GDP quý), FOMC (lịch Fed 2026)."""
    hom_nay = pd.Timestamp(hom_nay).normalize()
    out = []
    for i in range(0, 4):
        m = (hom_nay + pd.DateOffset(months=i)).replace(day=6)
        if m < hom_nay:
            continue
        tr = m - pd.DateOffset(months=1)
        mo = "Lạm phát, lạm phát lõi, sản xuất công nghiệp, bán lẻ, xuất nhập khẩu, FDI, khách quốc tế"
        out.append({"ngay": f"{m:%Y-%m-%d}", "thu": THU[m.weekday()], "ten": f"Số liệu T{tr.month}/{tr.year}", "mo": mo,
                    "nguon": TC})
        if m.month in (1, 4, 7, 10):
            q = (tr.month - 1) // 3 + 1
            out.append({"ngay": f"{m:%Y-%m-%d}", "thu": THU[m.weekday()], "ten": f"GDP Q{q}/{tr.year}",
                        "mo": "Tăng trưởng GDP quý, lao động – việc làm", "nguon": TC})
    for f in FOMC_2026:
        d = pd.Timestamp(f)
        if d >= hom_nay:
            out.append({"ngay": f, "thu": THU[d.weekday()], "ten": "Fed công bố lãi suất (FOMC)", "mo": "Mỹ – Fed funds",
                        "nguon": "Fed"})
    out.sort(key=lambda x: x["ngay"])
    return out[:so]


def vua_co_so(cu, hang, hom_nay, ngay_toi_da=10):
    """cu: {khoá: {"ky", "thay"}} (đệm) + hàng chỉ tiêu mới → (đệm mới, danh sách vừa có số kỳ mới ≤ 10 ngày, mới nhất
    trước). Lần đầu (chưa có đệm) không tính là "vừa có số"."""
    hom = f"{pd.Timestamp(hom_nay):%Y-%m-%d}"
    moi, vua = {}, []
    for r in hang:
        if r["ts"] == "D":
            continue
        c = cu.get(r["k"])
        thay = c["thay"] if c and c.get("ky") == r["ky"] else (hom if c else "")
        moi[r["k"]] = {"ky": r["ky"], "thay": thay}
        if thay and (pd.Timestamp(hom) - pd.Timestamp(thay)).days <= ngay_toi_da:
            vua.append({"ngay": thay, "k": r["k"], "ten": r["ten"], "ky": r["ky"],
                        "gt": so_vn(r["gt"], r["le"]) + (" " + r["dv"] if r["dv"] not in ("%",) else "%")})
    vua.sort(key=lambda x: x["ngay"], reverse=True)
    return moi, vua


# ------------------------------------------------------------------ điểm nhấn + bản tin
def _chuoi_lien_tiep(s):
    """Số kỳ tăng (+) / giảm (−) liên tiếp đến kỳ cuối."""
    x = _s(s).diff().dropna().tolist()
    if not x or x[-1] == 0:
        return 0
    dau, n = x[-1] > 0, 0
    for d in reversed(x):
        if d != 0 and (d > 0) == dau:
            n += 1
        else:
            break
    return n if dau else -n


def diem_nhan(h, ch):
    """→ [[đoạn chữ, đậm 0/1], …] (trang tự thoát ký tự – không HTML)."""
    out = []

    def them(*phan):
        if out:
            out.append([" · ", 0])
        out.extend([[t, b] for t, b in phan])
    c = h.get("vn_cpi")
    if c:
        n = _chuoi_lien_tiep(ch["vn_cpi"])
        them(["Lạm phát ", 0], [so_vn(c["gt"], 2) + "%", 1],
             [f" ({c['ky']})" + (f" — {'tăng' if n > 0 else 'giảm'} {abs(n)} tháng liên tiếp" if abs(n) >= 2 else "")
              + (", " + c["ghi"][0].lower() + c["ghi"][1:] if c["ghi"] else ""), 0])
    g = h.get("vn_gdp")
    if g:
        q = cung_ky(ch["vn_gdp"], g["ngay"], "Q")
        them(["GDP " + g["ky"] + " ", 0], [("+" if g["gt"] >= 0 else "") + so_vn(g["gt"], 2) + "%", 1],
             [f" (cùng kỳ {so_vn(q, 2)}%)" if q is not None else "", 0])
    b = h.get("vn_bot")
    if b:
        s = _s(ch["vn_bot"])
        v, truoc = b["gt"], _s(ch["vn_bot"]).iloc[:-1]
        hon = truoc[(truoc >= v) if v >= 0 else (truoc <= v)]          # tháng gần nhất có xuất (nhập) siêu lớn hơn
        if not len(hon):
            mo = f" — kỷ lục (số liệu từ {s.index[0].year})" if len(truoc) >= 24 else ""
        else:
            t = hon.index[-1]
            mo = f" — lớn nhất từ T{t.month}/{t.year}" if (truoc.index[-1] - t).days > 150 else ""
        them([("Xuất siêu " if v >= 0 else "Nhập siêu "), 0], [so_vn(abs(v), 2) + " tỷ USD", 1], [f" ({b['ky']})" + mo, 0])
    f = h.get("vn_fdi")
    if f:
        them(["FDI giải ngân " + f["ky"] + " ", 0], [so_vn(f["gt"], 2) + " tỷ USD", 1],
             [(f", {'+' if f['ck'] >= 0 else ''}{so_vn(f['ck'], 1)}% so với cùng kỳ") if f["ck"] is not None else "", 0])
    return out


def ban_tin(h):
    """Bản tin tháng mới nhất (câu dựng sẵn từ số liệu; chỉ mục có số)."""
    def gt(k, le=None, dau=False):
        r = h.get(k)
        if not r:
            return None
        x = r["gt"]
        return ("+" if dau and x > 0 else "") + so_vn(x, r["le"] if le is None else le)

    def dt(k):
        r = h.get(k)
        if not r or r["kt"] is None:
            return ""
        return f" ({'+' if r['kt'] > 0 else ''}{so_vn(r['kt'], 2)} {'điểm' if r['kieu'] in ('pt', 'd') else '%'} so kỳ trước)"
    thang = [h[k]["ngay"] for k in ("vn_cpi", "vn_sxcn", "vn_banle", "vn_bot") if k in h]
    ky = max(thang) if thang else None
    muc = []
    if "vn_cpi" in h:
        c = f"CPI {h['vn_cpi']['ky']} tăng {gt('vn_cpi')}% so cùng kỳ{dt('vn_cpi')}"
        if "vn_cpi_mom" in h:
            c += f", {gt('vn_cpi_mom', dau=True)}% so tháng trước"
        if "vn_cpi_loi" in h:
            c += f"; lạm phát lõi {gt('vn_cpi_loi')}%"
        muc.append({"tieu": "Giá cả", "cau": c + "."})
    sx = []
    if "vn_sxcn" in h:
        sx.append(f"Sản xuất công nghiệp {h['vn_sxcn']['ky']} {gt('vn_sxcn', dau=True)}% so cùng kỳ{dt('vn_sxcn')}")
    if "vn_dau_tho" in h:
        sx.append(f"khai thác dầu thô {gt('vn_dau_tho')} nghìn thùng/ngày ({h['vn_dau_tho']['ky']})")
    if sx:
        muc.append({"tieu": "Sản xuất", "cau": "; ".join(sx) + "."})
    td = []
    if "vn_banle" in h:
        td.append(f"Bán lẻ {h['vn_banle']['ky']} {gt('vn_banle', dau=True)}% so cùng kỳ")
    if "vn_khach" in h:
        r = h["vn_khach"]
        td.append(f"khách quốc tế {so_vn(r['gt'] / 1000, 2)} triệu lượt"
                  + (f" ({'+' if r['ck'] >= 0 else ''}{so_vn(r['ck'], 1)}% so cùng kỳ)" if r["ck"] is not None else ""))
    if td:
        muc.append({"tieu": "Tiêu dùng", "cau": "; ".join(td) + "."})
    tm = []
    if "vn_bot" in h:
        v = h["vn_bot"]["gt"]
        tm.append(f"{'Xuất siêu' if v >= 0 else 'Nhập siêu'} {so_vn(abs(v), 2)} tỷ USD ({h['vn_bot']['ky']})")
    if "vn_xk" in h:
        r = h["vn_xk"]
        tm.append(f"xuất khẩu {so_vn(r['gt'], 2)} tỷ USD ({r['ky']}"
                  + (f", {'+' if r['ck'] >= 0 else ''}{so_vn(r['ck'], 1)}% so cùng kỳ" if r["ck"] is not None else "") + ")")
    if "vn_fdi" in h:
        r = h["vn_fdi"]
        tm.append(f"FDI giải ngân {r['ky']} {so_vn(r['gt'], 2)} tỷ USD"
                  + (f" ({'+' if r['ck'] >= 0 else ''}{so_vn(r['ck'], 1)}% so cùng kỳ)" if r["ck"] is not None else ""))
    if tm:
        muc.append({"tieu": "Thương mại & vốn ngoại", "cau": "; ".join(tm) + "."})
    tt = []
    for k, ten in (("vn_dh", "lãi điều hành"), ("vn_lnh", "liên ngân hàng"), ("vn_10n", "lợi suất TPCP 10 năm")):
        if k in h:
            tt.append(f"{ten} {gt(k)}%/năm ({h[k]['ky']})")
    if "usdvnd" in h:
        r = h["usdvnd"]
        tt.append(f"USD/VND {so_vn(r['gt'], 0)}" + (f" ({'+' if r['ck'] >= 0 else ''}{so_vn(r['ck'], 2)}% so cùng kỳ)"
                                                   if r["ck"] is not None else ""))
    if tt:
        muc.append({"tieu": "Tiền tệ", "cau": (tt[0][0].upper() + "; ".join(tt)[1:]) + "."})
    if "vn_gdp" in h:
        r = h["vn_gdp"]
        muc.append({"tieu": "Tăng trưởng", "cau": f"GDP {r['ky']} {gt('vn_gdp', dau=True)}% so cùng kỳ"
                    + (f", {r['ghi'].lower()} năm 2026" if r["ghi"] else "") + "."})
    return {"ky": (f"Tháng {pd.Timestamp(ky).month}/{pd.Timestamp(ky).year}" if ky else ""), "muc": muc}


# ------------------------------------------------------------------ gom
def dung_kt(ch, nguon, hom_nay, dem_thay=None, ck_chinh=None):
    """ch: {khoá chỉ tiêu: Series (đơn vị gốc)} · nguon: {khoá: chữ} → (dict "kt" cho trang, {khoá: [[ngày, v]]} lịch sử,
    đệm "vừa có số" mới). ck_chinh: {khoá: Series % so cùng kỳ CƠ QUAN CÔNG BỐ} – có số đúng tháng cuối thì thay "cùng kỳ" tự tính
    (năm trước đã điều chỉnh: tự tính trên số sơ bộ cũ lệch vài điểm)."""
    spec = {x[0]: x for x in CHI_TIEU}
    hang, h, lich_su, chia = [], {}, {}, {}
    for k, x in spec.items():
        s = ch.get(k)
        if s is None or not len(pd.Series(s).dropna()):
            continue
        s = _s(s) / x[5]
        chia[k] = s
        r = chi_tieu(x, s, nguon.get(k, ""), hom_nay)
        c = (ck_chinh or {}).get(k)
        if r and c is not None and len(c) and x[6] == "%":
            c = theo_thang(c) if x[7] == "M" else _s(c)
            d = pd.Timestamp(r["ngay"])
            if d in c.index:
                r["ck"], r["ck_chinh"] = round(float(c[d]), 2), True
        if r:
            hang.append(r)
            h[k] = r
            lich_su[k] = gon_ngay(s) if x[7] == "D" else [[f"{d:%Y-%m-%d}", round(float(v), 4)] for d, v in s.items()]
    dem_moi, vua = vua_co_so(dem_thay or {}, hang, hom_nay)
    ch_nhip = dict(chia)
    for k in ("vn_xk", "vn_khach"):
        if k in chia:
            ch_nhip["yy:" + k] = so_cung_ky_pt(chia[k])
    if "vn_fdi" in chia:
        ch_nhip["yy:vn_fdi"] = so_cung_ky_pt(chia["vn_fdi"])
    dem = {c: sum(1 for r in hang if r["cd"] == c) for c, _, _ in CHU_DE}
    dem["tq"] = sum(1 for k in TONG_QUAN if k in h)
    kt = {"chu_de": [{"k": c, "ten": t, "mo": m, "n": dem.get(c, 0)} for c, t, m in CHU_DE],
          "ct": hang, "tq": [k for k in TONG_QUAN if k in h], "nhip": nhip(ch_nhip),
          "lich": {"vua": vua, "sap": lich(hom_nay)}, "ban_tin": ban_tin(h), "diem_nhan": diem_nhan(h, chia)}
    return kt, lich_su, dem_moi
