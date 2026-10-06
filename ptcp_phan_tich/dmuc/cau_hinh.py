# -*- coding: utf-8 -*-
"""
CẤU HÌNH – sửa trực tiếp tại đây (hoặc dùng tham số dòng lệnh, xem Danh_mục.py).
Các module khác chỉ ĐỌC file này. Giá theo NGHÌN ĐỒNG (73.9 = 73.900 đ).
Tham số KỸ THUẬT của từng mã nằm ở ptcp/cau_hinh.py (dùng chung với chay.py).
"""
# ==========================================================================
# DANH MỤC
# ==========================================================================
#  • Mỗi mã 1 dòng, các cột cách nhau bằng dấu phẩy.
#  • Mã CHƯA MUA (theo dõi): bỏ trống so_cp và gia_von
#  • Cột tuỳ chọn: cat_lo_dat (cắt lỗ đã đặt khi mua), muc_tieu_dat, kl_phat_hanh, kl_niem_yet, cp_quy,
#    so_huu_nn, beta, san (HOSE/HNX/UPCOM), csv_ngay, csv_gio
#  • Giá vốn nhập nhầm theo ĐỒNG (73900) sẽ được tự quy đổi về nghìn đồng (có cảnh báo).
DANH_MUC = ""                       # (tuỳ chọn) gõ danh mục trực tiếp ở đây thay cho file, cùng định dạng CSV:
                                   #   ma,so_cp,gia_von,gia_muc_tieu,cat_lo_dat,ngay_mua,nhom_nganh
                                   #   AAA,100,25.5,30,,15/03/2026,BBB;CCC
FILE_DANH_MUC = "danh_muc.csv"     # file danh mục mặc định (chưa có → tự tạo file mẫu để điền)
FILE_NHAT_KY = None                # VD "nhat_ky.csv" – nhật ký giao dịch (xem danh_muc.doc_nhat_ky); có thì
                                   # số CP & giá vốn TÍNH TỪ NHẬT KÝ (kể cả cổ tức tiền/cổ phiếu)
NGAY_BAT_DAU = "2019-01-01"        # lấy dữ liệu từ ngày – Markowitz cần ≥ 5 năm (tự lùi ngày nếu chưa đủ)
FILE_VNINDEX = None                # VD "VNINDEX.csv"; None = tự lấy online
TIEN_MAT_TRIEU = 8                 # tiền mặt sẵn có (triệu đồng)
GIU_TIEN_MAT_TU_DONG = True        # True = % tiền mặt TỰ ĐỘNG theo trạng thái VN-Index (xem dmuc/thi_truong.py)
TIEN_MAT_THEO_THI_TRUONG = {"GIẢM": 50.0, "TRUNG TÍNH": 25.0, "TĂNG": 0.0}   # % TỔNG TÀI SẢN giữ tiền mặt
NGUONG_GIAM = 4                    # ≥ 4/6 tiêu chí xấu (dưới MA200, MA50<MA200, dưới SuperTrend, MACD tuần ≤ Signal,
NGUONG_TANG = 1                    #   đáy sau thấp hơn, đỉnh sau thấp hơn) → GIẢM; ≤ 1 → TĂNG; còn lại TRUNG TÍNH
SUPERTREND_ATR, SUPERTREND_HE_SO = 10, 3.0
GIU_TIEN_MAT_PCT = 50.0            # dùng khi TẮT tự động (hoặc thiếu dữ liệu VN-Index). Ghi đè khi chạy: --giu_tien_mat 30
HOI_KHI_CHAY = True                # True = HỎI tiền mặt, % giữ tiền mặt, chiến lược mỗi lần chạy (Enter = giữ mặc định)
                                   # – hỏi được khi chạy bằng  %run Danh_mục.py  (Colab) hoặc cửa sổ lệnh;
                                   #   chạy bằng  !python ...  thì không nhập được → dùng giá trị ở đây / tham số
LAI_SUAT_PHI_RUI_RO = 4.0          # %/năm
SO_PHIEN_KICH_BAN = 63             # số phiên cho xác suất kịch bản / mục tiêu (≈ 3 tháng)
IN_CHI_TIET = False                # True = in báo cáo đầy đủ từng mã ra màn hình

# ==========================================================================
# PHÂN TÍCH TỪNG MÃ = BỘ ptcp (mọi tham số kỹ thuật – MACD, đỉnh/đáy, cắt lỗ, EV, R/R… – sửa trong
# ptcp/cau_hinh.py, dùng CHUNG cho chay.py và Danh_mục.py)
# ==========================================================================
GOP_NGANH = False                  # True = ptcp tải thêm mã cùng ngành cho từng mã (EV gộp ngành, so sánh ngành)
                                   # – chính xác hơn nhưng chậm hơn nhiều khi danh mục có nhiều mã
XUAT_FILE_TUNG_MA = True           # True = lưu báo cáo đầy đủ của ptcp cho từng mã (TXT/HTML/Excel/biểu đồ)
NGAY_DU_LIEU_CU = 7                # phiên cuối cũ hơn N ngày → coi là dữ liệu cũ / mã tạm ngừng giao dịch

# ==========================================================================
# DANH MỤC – QUẢN TRỊ RỦI RO
# ==========================================================================
TY_TRONG_TOI_DA = 30.0             # % TỔNG TÀI SẢN (gồm tiền mặt) tối đa cho 1 mã
NGUONG_TUONG_QUAN = 0.8            # tương quan lợi suất TUẦN cao hơn mức này → cảnh báo
LO_TOI_DA_GIA_VON = 10.0           # % lỗ so giá vốn → xem xét cắt lỗ (khi khung tuần không ủng hộ)
RUI_RO_MOI_LENH = 1.0              # % tổng tài sản chấp nhận mất / lệnh mới
TONG_RUI_RO_MO_TOI_DA = 6.0        # % tổng tài sản: tổng lỗ nếu MỌI mã chạm cắt lỗ đã đặt – vượt thì không mua thêm
LO_CHAN = 100                      # lô chẵn HOSE
CHO_PHEP_LO_LE = True              # cho phép gợi ý lô lẻ (1–99 CP) khi vốn nhỏ
TY_LE_THANH_KHOAN = 20.0           # chỉ bán ≤ 20% KLGD TB20 mỗi phiên → tính số phiên cần để thoát vị thế
HE_SO_THI_TRUONG_XAU = 0.5         # VN-Index xấu → rủi ro mỗi lệnh × 0.5, "MUA" → "MUA TỪNG PHẦN"
CU_SOC_STRESS = (-10, -20, -30)    # % VN-Index – kiểm tra sức chịu đựng theo beta
CAP_NHAT_FILE_DANH_MUC = True      # True = sau mỗi lần chạy ghi lại vào danh_muc.csv: ngày mua, cắt lỗ/chốt lời đã
                                   # đặt, giá mua/cắt lỗ/mục tiêu đề xuất cho mã theo dõi, cột de_xuat (bản cũ → .bak)
AP_DUNG_CAT_LO_DE_XUAT = True      # True = tự DỜI LÊN cắt lỗ theo đề xuất (hoà vốn / khoá lãi / Chandelier); không bao giờ hạ
from ptcp import cau_hinh as _ptcp_cfg  # noqa: E402
CHANDELIER_ATR = _ptcp_cfg.TRAILING_ATR   # dùng CHUNG cấu hình ptcp (TRAILING_ATR) – sửa ở ptcp/cau_hinh.py
KHOANG_CACH_ATR_MIN = 1.0          # mức cắt lỗ đề xuất phải cách giá hiện tại ≥ 1×ATR (tránh bị nhiễu quét)
FILE_TRANG_THAI = "trang_thai_vi_the.json"   # lưu cắt lỗ/mục tiêu đã đặt của mã đang giữ (dời lên, không dời xuống)
FILE_LICH_SU = "lich_su_danh_muc.csv"         # ảnh chụp mỗi lần chạy → so sánh thay đổi hành động

# ==========================================================================
# MARKOWITZ
# ==========================================================================
MKW_SO_NAM = 5                     # Markowitz dùng ĐÚNG 5 năm lợi suất TUẦN gần nhất (≈ 260 tuần)
MKW_SO_TUAN = 52 * MKW_SO_NAM
MKW_SO_TUAN_TOI_THIEU = MKW_SO_TUAN - 5   # mã có ít hơn ~5 năm dữ liệu → KHÔNG đưa vào tối ưu (giữ nguyên vị thế)
MKW_KY_VONG = "lich_su"            # "lich_su" | "muc_tieu" (giá mục tiêu TỰ NHẬP) | "ket_hop"
MKW_TY_TRONG_TOI_DA = 40.0         # % phần cổ phiếu tối đa cho 1 mã
MKW_DANH_MUC_CHON = "gmv"          # danh mục dùng làm kế hoạch CHÍNH: "gmv" | "max_sharpe" (báo cáo in CẢ HAI để so sánh)
                                   #   gmv        : chỉ dựa vào Σ (biến động & tương quan) – ổn định, khuyên dùng khi ít mã
                                   #   max_sharpe : cần thêm μ (lợi suất kỳ vọng) – nhạy với sai số ước lượng μ
MKW_CO_GIAN = True                 # co ma trận hiệp phương sai Ledoit–Wolf
MKW_NGUONG_TAI_CAN_BANG = 5.0      # điểm % tổng tài sản – lệch ít hơn thì không giao dịch
MKW_GIA_TRI_GD_TOI_THIEU = 500_000 # đồng – lệnh nhỏ hơn bỏ qua (phí không đáng)
MKW_SO_DANH_MUC_NGAU_NHIEN = 5000
