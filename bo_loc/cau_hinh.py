# -*- coding: utf-8 -*-
"""
CẤU HÌNH CHUNG – mọi ngưỡng/hằng số chỉnh tại đây (chiến lược nằm riêng trong thư mục chien_luoc/).
Đơn vị giá trong toàn bộ chương trình: NGHÌN ĐỒNG.
"""

# --------------------------------------------------------------------------
# Thuật toán kỹ thuật (MACD đỉnh/đáy, mục tiêu)
# --------------------------------------------------------------------------
MACD_NHANH, MACD_CHAM, MACD_TIN_HIEU = 12, 26, 9
BO_QUA_DAU = 30                      # bỏ qua N nến đầu (MACD chưa ổn định)
UPSIDE_MIN, UPSIDE_MAX = 15.0, 20.0  # vùng upside ưu tiên khi chọn mục tiêu chính
NGUONG_GAN_HO_TRO = 3.0              # % – giá cách đường hỗ trợ ≤ 3% coi là "gần hỗ trợ"
SO_NEN_GAN = {"Tuần": 3, "Ngày": 5, "Giờ": 10}   # cửa sổ xét tín hiệu "vừa xảy ra"
SUPERTREND = (10, 3.5)               # (chu kỳ ATR, hệ số nhân)
SO_PHIEN_TOI_THIEU = 150             # mã có ít hơn số phiên này bị bỏ qua

# --------------------------------------------------------------------------
# Dữ liệu & chạy
# --------------------------------------------------------------------------
NGAY_BAT_DAU = "2019-01-01"          # dữ liệu ngày TỐI THIỂU từ 2019 (= giai đoạn backtest của bot canh-bao-mua)
SO_LUONG_TAI = 8                     # số luồng tải song song
TOP_N = 15
SO_BIEU_DO_NHO = 9
THU_MUC_CACHE = "du_lieu_gia"        # giá ngày đã tải → lần sau chỉ tải thêm phiên mới
THU_MUC_CACHE_CO_BAN = "du_lieu_co_ban"
HAN_CACHE_CO_BAN_GIO = 24            # dữ liệu cơ bản lưu đệm 24 giờ (BCTC chỉ đổi theo quý)
FILE_DS_HOSE = "danh_sach_hose.txt"
FILE_LICH_SU = "lich_su_loc.csv"
GIO_DONG_CUA = 15
# Dán code vào ô Colab/Jupyter (không truyền được tham số dòng lệnh) → đặt tham số tại đây
THAM_SO_NOTEBOOK = ["--nhom", "tat_ca"]

# Thứ tự thử nguồn GIÁ (tên phải có trong bo_loc/nguon/gia.py). Nguồn lỗi → tự chuyển nguồn sau.
THU_TU_NGUON_GIA = ["VNDirect", "TCBS", "DNSE", "VCI", "SSI", "vnstock", "Yahoo"]
# Thứ tự ưu tiên nguồn CƠ BẢN khi nhiều nguồn cùng có 1 chỉ tiêu (file người dùng luôn ưu tiên nhất)
THU_TU_NGUON_CO_BAN = ["VNDirect", "vnstock", "Yahoo"]   # VNDirect: EPS 4 quý chuẩn, chạy được trên Colab
# TCBS đã TẮT (07/10/2026 không trả dữ liệu cho mọi mã, mỗi lần gọi vẫn tốn thời gian chờ) – thêm "TCBS" vào danh
# sách trên để bật lại (cùng ptcp/cau_hinh.py NGUON_TAT).
LECH_CANH_BAO_PCT = 20               # 2 nguồn lệch nhau > 20% ở cùng chỉ tiêu → cảnh báo dữ liệu
DUNG_VNSTOCK = True                  # dùng thư viện vnstock (bản Cộng đồng) làm nguồn; Colab tự cài
PE_THEO_GIA_HIEN_TAI = True          # tự tính lại P/E, P/B theo giá đóng cửa mới nhất (khuyên dùng)

# --------------------------------------------------------------------------
# Ngưỡng dùng chung cho các chiến lược
# --------------------------------------------------------------------------
VON_HOA_LON = 10_000                 # tỷ đồng
KLGD_MIN = 100_000                   # CP/phiên
KLGD_CAO = 1_000_000
GTGD_MIN = 3                         # tỷ đồng/phiên
TT_HIEN_THOI_MIN = 1.5
TT_NHANH_MIN = 1.0
NGHIEM_NGAT = False                  # True: thiếu dữ liệu = KHÔNG đạt; False: bỏ qua & đánh dấu ◐
MAX_TC_THIEU_DL = 2                  # thiếu dữ liệu quá số tiêu chí bắt buộc này → "?"

# --------------------------------------------------------------------------
# Đánh giá sau lọc (B2–B6)
# --------------------------------------------------------------------------
VON_DANH_MUC = 1_000                 # triệu đồng (NAV)
RUI_RO_MOI_LENH = 0.75               # % NAV chấp nhận mất nếu chạm cắt lỗ – = ptcp QUY_RUI_RO_LENH_PCT (Quỹ B; trước: 1)
TY_TRONG_MAX = 15                    # % NAV tối đa cho 1 mã – = ptcp QUY_TRAN_MA_PCT (Quỹ B; trước: 20)
TY_LE_THANH_KHOAN = 10               # mua tối đa 10% KLGD TB20 mỗi phiên
SO_ATR_CAT_LO = 2.0                  # cắt lỗ = giá − k × ATR(14)
TRONG_SO = {"Xu hướng": 0.30, "Động lượng": 0.20, "Định giá": 0.15, "Chất lượng": 0.20, "Rủi ro": 0.15}
NGUONG_HANH_DONG = {"mua": 70, "tham_do": 55}
SO_MA_TOI_THIEU_SO_SANH_NHOM = 3     # B6: nhóm ≥ 3 mã mới so với trung vị nhóm, ít hơn → so toàn bộ

# --- CHIẾN LƯỢC THEO THỊ TRƯỜNG (bo_loc/chien_luoc_tt.py – cùng logic bot canh-bao-mua & ptcp) ---
#   True: hành động / kế hoạch theo nhóm chiến lược (🟢 MUA MỚI · ✅ VÀO NHƯ LỆNH MỚI · 🟡 VÀO ½ · ⏳ CHỜ ĐIỀU CHỈNH),
#   cắt lỗ chuẩn hệ thoát, mục tiêu tạm thời 1R → 3R (không chốt cứng), bỏ điều kiện R/R ≥ 2 theo mục tiêu kỹ thuật.
#   False: cách cũ (điểm 5 trụ cột + R/R ≥ 2, cắt lỗ thống nhất, mục tiêu kỹ thuật).
THEO_CHIEN_LUOC_TT = True
CHIEN_LUOC_MAC_DINH = "quy_b"   # chiến lược chạy khi không truyền --chien_luoc (cũ: "rieng", "ky_thuat")
