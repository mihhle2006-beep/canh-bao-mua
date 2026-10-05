# -*- coding: utf-8 -*-
"""Tham số cấu hình & dữ liệu CTCK nạp sẵn. Sửa ở đây (hoặc gán ptcp.cau_hinh.X = ... lúc chạy)."""
import sys
import subprocess
import importlib

for _tv in ["requests", "pandas", "numpy", "matplotlib", "openpyxl"]:
    try:
        importlib.import_module(_tv)
    except ImportError:
        print(f"Đang cài thư viện {_tv} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _tv, "-q"])

import numpy as np

# ==========================================================================
# THAM SỐ CẤU HÌNH
# ==========================================================================
MACD_NHANH, MACD_CHAM, MACD_TIN_HIEU = 12, 26, 9


BO_QUA_DAU = 30              # bỏ qua N nến đầu (MACD chưa ổn định)


# [SỬA lần 3] Đỉnh/đáy theo GIÁ ĐÓNG CỬA: đường nối đỉnh–đáy, đường hỗ trợ/kháng cự, số lần chạm, mục tiêu
#       "đỉnh cũ" và cắt lỗ "dưới đáy" đều dựa trên giá đóng cửa – không tính theo râu nến (high/low trong phiên).
#       Lưu ý: đỉnh/đáy TUẦN = giá đóng cửa tuần (thứ Sáu) nên có thể thấp/cao hơn đỉnh/đáy ngày trong cùng tuần –
#       đây là khác biệt tự nhiên, không phải lỗi dữ liệu (mục kiểm tra (1) chỉ chạy khi dùng "high_low").
DINH_DAY_THEO = "close"      # "close" (theo nến đóng) | "high_low" (theo râu nến)


# [MỚI] Đỉnh/đáy của đoạn MACD CHƯA kết thúc chỉ được coi là XÁC NHẬN khi đã có ≥ n nến sau nó mà không bị phá.
#       Đỉnh/đáy chưa xác nhận KHÔNG được dùng để vẽ đường xu hướng, so sánh đáy/đỉnh, tính mục tiêu hay cắt lỗ.
N_XAC_NHAN = {"Tuần": 3, "Ngày": 5, "Giờ": 10}


NGUONG_GAN_HO_TRO = 3.0      # % – giá cách đường hỗ trợ ≤ 3% coi là "gần hỗ trợ"


SO_NEN_GAN = {"Tuần": 3, "Ngày": 5, "Giờ": 10}     # cửa sổ xét tín hiệu "vừa xảy ra"


SO_NEN_HIEN_THI = {"Tuần": 156, "Ngày": 250, "Giờ": 200}


MA_NGAN, MA_DAI = 50, 200    # đường trung bình động giá đóng cửa vẽ trên biểu đồ (MA50, MA200)


MAU_MA = {MA_NGAN: "#F9A825", MA_DAI: "#6D4C41"}      # MA ngắn vàng hổ phách, MA dài nâu (nền xanh lá chủ đạo)


KEO_DAI = {"Tuần": 12, "Ngày": 25, "Giờ": 30}       # kéo dài đường xu hướng sang tương lai


# --- Lấy dữ liệu ---
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*",
           "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}


SO_LAN_THU = 3               # [MỚI] số lần thử lại mỗi nguồn (backoff 0.6s → 1.2s → 2.4s)


THOI_GIAN_CHO = 20           # giây


THU_MUC_CACHE = "cache_du_lieu"   # [MỚI] lưu giá ngày/giờ/VNINDEX; dùng lại khi mọi nguồn đều lỗi


# --- Đường xu hướng ---
MAX_CACH_DUONG_XH = 25.0     # [MỚI] đường xu hướng cách giá > 25% → bỏ qua (không dùng làm mốc hành động)


SAI_SO_CHAM = 1.5            # [MỚI] % – nến có giá đóng cửa (high/low nếu DINH_DAY_THEO="high_low") cách đường ≤ 1.5% = 1 lần chạm


SO_CHAM_XAC_NHAN = 3         # [MỚI] đường có ≥ 3 lần chạm = đã xác nhận


# --- Chấm điểm tín hiệu ---
TRONG_SO_KHUNG = {"Tuần": 3, "Ngày": 2, "Giờ": 1}  # [MỚI] tuần > ngày > giờ (không cộng đều)


# --- Cắt lỗ THỐNG NHẤT (một quy tắc duy nhất cho mọi phần của báo cáo) ---
#   cắt lỗ = max(đáy ngày ĐÃ XÁC NHẬN gần nhất dưới giá − BUFFER_ATR×ATR ; giá − STOP_ATR_MAX×ATR ; giá × (1 − LO_CUNG_PCT%))
#   nếu khoảng cách < STOP_ATR_MIN×ATR → nới ra giá − STOP_ATR_MIN×ATR (tránh bị nhiễu quét)
BUFFER_ATR = 0.5


STOP_ATR_MAX = 2.0


STOP_ATR_MIN = 1.5


LO_CUNG_PCT = 7.0            # cắt lỗ cứng tối đa −7% so với giá mua


# --- Ngưỡng cứng cho khuyến nghị cuối cùng ---
EV_NGUONG = 1.0              # [MỚI] % – lợi suất kỳ vọng (sau phí) < ngưỡng → KHÔNG khuyến nghị mua


RR_NGUONG = 2.0              # R/R tối thiểu


PHI_GD_KHU_HOI = 0.4         # % phí mua + bán + thuế bán, trừ vào lợi suất kỳ vọng


TRUOT_GIA_PCT = 0.1          # [MỚI] % trượt giá MỖI chiều (mua cao hơn / bán thấp hơn giá lý thuyết)


# --- [MỚI] Luật giao dịch Việt Nam trong mô phỏng & backtest ---
T_CONG = 2                   # cổ phiếu về tài khoản T+2 → chỉ bán được từ phiên thứ 2 sau ngày mua


MUA_GIA_MO_CUA = True        # mua ở giá MỞ CỬA phiên sau ngày có tín hiệu (không mua được đúng giá đóng cửa)


WF_SO_KHOI = 5               # số khối thời gian cho kiểm định walk-forward bước chọn mục tiêu


TRONG_SO_GOP_NGANH = 0.5     # EV cơ sở = (1 − w) × EV của mã + w × EV gộp ngành (co về trung bình ngành)


# --- [MỚI] Bối cảnh thị trường & sự kiện trong quyết định ---
HE_SO_THI_TRUONG_XAU = 0.5   # khối lượng × 0.5 cho mỗi yếu tố xấu (VN-Index xấu; RS ở đáy 1 năm)


SO_PHIEN_SU_KIEN = 5         # KQKD / GDKHQ trong 5 phiên tới → không mở vị thế mới


THU_TU_NGUON_SO_CP = ["TCBS", "vnstock", "VNDirect", "Yahoo"]   # ưu tiên khi chọn số CP lưu hành (nhập tay luôn đứng đầu)
DUNG_VNSTOCK = True           # dùng thư viện vnstock (bản Cộng đồng) làm nguồn; trên Colab tự cài
IN_GON = False                # True / main(gon=True): màn hình chỉ in Tóm tắt, Phần C, D2, Kết luận chung Phần J – file vẫn đầy đủ
SO_MA_SO_SANH_FA = 2          # Phần J5: số mã cùng ngành (đầu danh sách) đem so sánh 10 tiêu chí (như FiinTrade)
CHO_VNSTOCK = False           # True: hết lượt vnstock thì CHỜ (chậm, đúng hạn mức) thay vì chuyển nguồn khác
LECH_SO_CP_PCT = 0.5          # các nguồn lệch nhau > 0,5% số CP → cảnh báo
LECH_VON_HOA_PCT = 2.0        # vốn hoá tự tính lệch Yahoo > 2% → cảnh báo


N_HIEU_DUNG_MIN = 10         # [MỚI] số mẫu hiệu dụng < 10 → gắn nhãn "độ tin cậy THẤP"


# --- Xác suất lịch sử ---
XS_CUA_SO = 252              # cửa sổ "1 năm gần nhất": điểm mua giả định trong 252 phiên gần nhất


XS_BAN_RA = 252              # [MỚI] xác suất TRỘN: trọng số mỗi điểm mua giảm 1/2 sau mỗi 252 phiên (ưu tiên gần đây)


BOOTSTRAP_B = 400            # [MỚI] số lần lấy mẫu lại (block bootstrap) để tính khoảng tin cậy 90%


SO_MAU_DK_MIN = 40           # [MỚI] số điểm mua tối thiểu cho xác suất CÓ ĐIỀU KIỆN (trạng thái tương tự hiện tại)


EWMA_LAMBDA = 0.94           # [MỚI] biến động EWMA (RiskMetrics) – phản ánh giai đoạn biến động cao hiện tại


SO_MUC_TIEU = 3              # [MỚI] chỉ hiển thị 3 mục tiêu tốt nhất (theo EV) mỗi khung


UPSIDE_TOI_THIEU = 3.0       # % – mục tiêu chính phải cao hơn giá ít nhất 3%


XS_TOI_THIEU_MT = 30.0       # % – mục tiêu chính phải có XS chạm trước cắt lỗ ≥ 30% (tránh chọn mục tiêu quá xa


                             #     chỉ vì EV cao nhờ lãi lớn nhưng hiếm khi đạt)
NGUONG_HOI_TU = 3.0          # % chênh lệch tối đa để coi mục tiêu ngày & tuần là hội tụ


# --- Tham số phần A & D (% tăng/giảm, kịch bản) ---
KICH_BAN = {                 # % so với giá hiện tại
    "Rất lạc quan": 30,
    "Lạc quan":     15,
    "Tăng nhẹ":      5,
    "Giảm nhẹ":     -5,
    "Bi quan":     -15,
    "Rất bi quan": -30,
}


NHOM_PHIEN = [               # (tên trường hợp, cận dưới %, cận trên %)
    ("Tăng mạnh (>3%)",     3.0,  np.inf),
    ("Tăng vừa (1–3%)",     1.0,  3.0),
    ("Đi ngang (±1%)",     -1.0,  1.0),
    ("Giảm vừa (1–3%)",    -3.0, -1.0),
    ("Giảm mạnh (>3%)", -np.inf, -3.0),
]


# [SỬA] Biên độ theo SÀN NIÊM YẾT (bản cũ cố định 6.7% kiểu HOSE). Ngưỡng nhận diện = biên độ − 0.3%.
BIEN_DO_SAN = {"HOSE": 7.0, "HNX": 10.0, "UPCOM": 15.0}


NGUONG_TRAN_SAN = 6.7        # được cập nhật trong main() theo sàn của mã


# --- Tham số phần E (đề xuất mục tiêu & quản trị rủi ro) ---
XS_SAN, XS_TRAN = 70.0, 30.0  # % giai đoạn lịch sử chạm mức: ≥70% = quá dễ (sàn) ; ≤30% = quá khó (trần)


TY_TRONG_MAX = 20.0          # tỷ trọng tối đa 1 mã trong danh mục, %


TY_LE_THANH_KHOAN = 20.0     # mỗi phiên chỉ nên bán tối đa 20% KLGD TB20


RUI_RO_KHUYEN_NGHI = 2.0     # % vốn/lệnh theo thông lệ; nhập cao hơn 3% sẽ bị cảnh báo


KHUNG_TG = {"1 tuần": 5, "1 tháng": 21, "3 tháng": 63, "6 tháng": 126, "1 năm": 252}


# --- Bối cảnh thị trường: nhóm so sánh mặc định ---
# Công cụ dùng cho MỌI mã → không cài sẵn nhóm ngành của mã nào. Muốn so sánh ngành: nhập khi chạy
# ("Mã cùng ngành ..."), truyền main(nhom="A,B,C"), cột nhom_nganh trong danh mục, hoặc điền ở đây:
#   NHOM_NGANH = {"MÃ": ["MÃ1", "MÃ2", ...]}
NHOM_NGANH = {}


MA_CTCK = {"SSI", "VND", "HCM", "VCI", "SHS", "MBS", "VIX", "FTS", "BSI", "CTS", "ORS", "AGR", "TVS", "APG",
           "BVS", "VDS", "EVS", "IVS", "TCI", "WSS", "SBS", "PSI", "HBS", "APS"}


# --- Trình bày & xuất file ---
DO_RONG_DONG = None          # None = tự nhận (Colab/Jupyter: 110 ký tự; terminal: theo độ rộng cửa sổ)


TU_DONG_TAI_VE = False       # True = trên Colab tự tải file .zip kết quả về máy khi chạy xong


# ==========================================================================
# DỮ LIỆU TỪ BÁO CÁO CÔNG TY CHỨNG KHOÁN (TUỲ CHỌN – mặc định TRỐNG, công cụ dùng cho mọi mã)
#   Nếu muốn nạp sẵn giá mục tiêu / chỉ số từ báo cáo CTCK cho một mã, thêm theo mẫu (giá NGHÌN ĐỒNG):
#   DU_LIEU_CTCK = {
#       "MÃ": {
#           "bao_cao": [("dd/mm/yyyy", "Tên CTCK", "KHUYẾN NGHỊ", giá_MT, giá_lúc_công_bố, "Tên báo cáo"), ...],
#           "kl_phat_hanh": ..., "kl_niem_yet": ..., "cp_quy": ..., "nguon_cp": "nguồn",
#           "so_huu_nn": ..., "nguon_nn": "nguồn", "beta": ..., "nguon_beta": "nguồn",
#           "chi_so": [("P/E TTM (lần)", giá_trị, "nguồn"), ...],
#           "ngay_bat_dau": "2019-01-01", "san": "HOSE", "nhom_nganh": ["MÃ1", "MÃ2"],
#       },
#   }
# ==========================================================================
DU_LIEU_CTCK = {}
