# -*- coding: utf-8 -*-
"""
CẤU HÌNH – sửa tại đây. Giá theo NGHÌN ĐỒNG.
Tiêu chí lấy từ bộ lọc cổ phiếu (chiến lược "ky_thuat" & "diem_mua"), sắp theo 4 khung:
  TUẦN  – định hướng, có QUYỀN PHỦ QUYẾT
  NGÀY  – xu hướng & sức khoẻ (các tiêu chí BẮT BUỘC của chiến lược ky_thuat + cộng điểm)
  GIỜ   – động lượng trong phiên xác nhận
  PHÚT  – điểm vào (kích hoạt "MUA NGAY")
"""
# --- Mã theo dõi ---
MA_THEO_DOI = ["MWG", "DHC", "GMD" , "VPB" , "VHM" , "NAB"]
NGAY_BAT_DAU = "2021-01-01"        # dữ liệu ngày (≥ 4 năm cho khung tuần, MA200, đỉnh/đáy)

# --- Chỉ báo ---
MACD_NHANH, MACD_CHAM, MACD_TIN_HIEU = 12, 26, 9
SUPERTREND = (10, 3.5)             # (chu kỳ ATR, hệ số) – như bộ lọc
BO_QUA_DAU = 30                    # bỏ N nến đầu khi tìm đỉnh/đáy (MACD chưa ổn định)
N_XAC_NHAN = 5                     # đỉnh/đáy của đoạn MACD đang chạy cần ≥ 5 nến chưa bị phá mới xác nhận

# --- KHUNG TUẦN (bắt buộc) ---
TUAN_MACD_TREN_0_LA_BAT_BUOC = False   # True: đòi thêm MACD tuần > 0 (chặt hơn)

# --- KHUNG NGÀY – bắt buộc (chiến lược ky_thuat của bộ lọc) ---
GTGD_MIN = 5.0                     # tỷ đồng/phiên – GTGD TB20
KLGD_MIN = 100_000                 # CP/phiên – KLGD TB20
RSI_NGAY = (45, 75)                # khoẻ nhưng chưa quá mua
# --- KHUNG NGÀY – cộng điểm ---
ADX_MIN = 20
VOL_DOT_BIEN = 1.5                 # KL phiên ≥ 1.5× TB20
GAN_DINH52 = 15.0                  # cách đỉnh 52 tuần ≤ 15%
DIEM_CONG_TOI_THIEU = 3            # cần ≥ 3 điểm cộng (trên 9) để coi khung ngày "đạt"

# --- KHUNG GIỜ ---
SO_NEN_GIO_GAN = 10                # MACD giờ cắt lên trong 10 nến gần nhất / phá đỉnh 10 nến

# --- KHUNG PHÚT (điểm vào) ---
KHUNG_PHUT = "15"                  # "5" | "15" | "30" – nến phút dùng làm điểm vào
SO_NEN_PHUT_GAN = 3                # tín hiệu phải xảy ra trong 3 nến phút gần nhất
DINH_PHUT_N = 20                   # phá đỉnh 20 nến phút ...
VOL_PHUT_DOT_BIEN = 1.5            # ... kèm KL nến ≥ 1.5× TB20 nến
RSI_PHUT_MAX = 75                  # không mua đuổi khi RSI phút quá cao

# --- Cắt lỗ / mục tiêu / R/R (cắt lỗ thống nhất như ptcp) ---
BUFFER_ATR, STOP_ATR_MAX, STOP_ATR_MIN, LO_CUNG_PCT = 0.5, 2.0, 1.5, 7.0
UPSIDE_TOI_THIEU = 3.0             # % – mục tiêu phải cao hơn giá ít nhất 3%
SO_PHIEN_XAC_SUAT = 63             # kỳ hạn (phiên) tính XS chạm mục tiêu / cắt lỗ khi không có ptcp
RR_TOI_THIEU = 2.0                 # R/R tối thiểu để phát "MUA NGAY" (= ngưỡng của ptcp)

# --- Thị trường chung ---
CHAN_KHI_THI_TRUONG_XAU = False    # True: VN-Index xấu → KHÔNG phát MUA NGAY (False: vẫn báo, kèm cảnh báo)

# --- Phiên giao dịch (giờ Việt Nam) ---
PHIEN = [("09:00", "11:30"), ("13:00", "14:45")]
GIO_TONG_KET = "15:00"             # sau giờ này chế độ tu_dong = gửi bản tổng kết cuối ngày

# --- Thông báo ---
GUI_ANH = True                     # gửi kèm ảnh biểu đồ (MUA NGAY / cảnh báo bán) & ảnh bảng tổng kết
BAO_LAI_TRONG_NGAY = False         # False: chỉ báo khi mã CHUYỂN sang MUA NGAY (không lặp mỗi 15 phút); True: báo mọi lần chạy
FILE_TRANG_THAI = "trang_thai_canh_bao.json"
THU_MUC_CACHE = "cache_gia"

# --- Phân tích NGÀY bằng bộ ptcp (chạy 1 lần/ngày/mã, có cache) ---
DUNG_PTCP = True                   # True: lấy cắt lỗ/mục tiêu/EV/sự kiện từ ptcp; False: chỉ dùng tiêu chí 4 khung
EV_NGUONG = 1.0                    # % – EV sau phí (ptcp) tối thiểu để phát MUA NGAY (= ngưỡng ptcp)
YEU_CAU_PTCP_MUA = False           # True: CHỈ báo khi khuyến nghị cuối của ptcp là MUA / MUA TỪNG PHẦN (chặt nhất)
SU_KIEN = {                        # ngày công bố KQKD / GDKHQ đã biết → ptcp chặn mua trong 5 phiên trước sự kiện
    # "MWG": {"ngay_kqkd": "20/10/2026", "ngay_gdkhq": "05/11/2026"},
}
