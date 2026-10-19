# -*- coding: utf-8 -*-
"""
CẤU HÌNH – sửa tại đây. Giá theo NGHÌN ĐỒNG.
Tiêu chí lấy từ bộ lọc cổ phiếu (chiến lược "ky_thuat" & "diem_mua"), sắp theo 4 khung:
  TUẦN  – định hướng, có QUYỀN PHỦ QUYẾT
  NGÀY  – xu hướng & sức khoẻ (các tiêu chí BẮT BUỘC của chiến lược ky_thuat + cộng điểm)
  GIỜ   – động lượng trong phiên xác nhận
  PHÚT  – điểm vào (kích hoạt "MUA NGAY")
"""
# --- Mã theo dõi (cảnh báo MUA): toàn bộ VN30 + MA_THEM; mã từ bộ lọc Bo_Loc tự thêm/xoá (FILE_MA_BO_LOC) ---
MA_VN30 = ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB", "MBB", "MSN", "MWG", "PLX",
           "SAB", "SHB", "SSB", "SSI", "STB", "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"]
TU_LAY_VN30 = True                 # True: lúc tổng kết tự lấy rổ VN30 online (rổ đổi kỳ tháng 1 & 7); lỗi → MA_VN30 trên
MA_THEM = ["DHC", "GMD", "MWG"]
MA_THEO_DOI = list(dict.fromkeys(MA_VN30 + MA_THEM))
# Độ rộng thị trường (1 trong 8 chỉ báo → CL1/CL2) tính trên rổ top 100 GTGD chốt phiên thứ Sáu tuần liền trước
# (ptcp/loc_quy_b.json – chien_luoc_bot.ro_do_rong; thiếu thì MA_CHIEN_LUOC 41 mã) + mã đang quét, để điểm thị trường
# không đổi theo danh sách cảnh báo. Mã chỉ dùng cho độ rộng KHÔNG lên danh sách mua.
DO_RONG_THEO_MA_CHIEN_LUOC = True
SO_MA_CUNG_NGANH = 4               # xem riêng 1 mã (--chi_ma): kèm trạng thái tối đa N mã cùng ngành (bản đồ ptcp/nganh.py)
# Mã tự thêm từ bộ lọc (repo Bo_Loc, quét mỗi phiên) nằm ở FILE_MA_BO_LOC – xem mục "MÃ TỪ BỘ LỌC" cuối file.
NGAY_BAT_DAU = "2019-01-01"        # dữ liệu ngày TỐI THIỂU từ 2019 (= giai đoạn backtest; khung tuần, MA200, đỉnh/đáy)

# --- Chỉ báo ---
MACD_NHANH, MACD_CHAM, MACD_TIN_HIEU = 12, 26, 9
SUPERTREND = (10, 3.5)             # (chu kỳ ATR, hệ số) – như bộ lọc


VOL_DOT_BIEN = 1.5                 # KL phiên ≥ 1.5× TB20


# --- KHUNG PHÚT (điểm vào) ---
KHUNG_PHUT = "15"                  # "5" | "15" | "30" – nến phút dùng làm điểm vào

# --- Cắt lỗ / mục tiêu / R/R (cắt lỗ thống nhất như ptcp) ---
BUFFER_ATR, STOP_ATR_MAX, STOP_ATR_MIN, LO_CUNG_PCT = 0.5, 2.0, 1.5, 7.0
UPSIDE_TOI_THIEU = 3.0             # % – mục tiêu phải cao hơn giá ít nhất 3%
SO_PHIEN_XAC_SUAT = 63             # kỳ hạn (phiên) tính XS chạm mục tiêu / cắt lỗ khi không có ptcp
RR_TOI_THIEU = 2.0                 # R/R tối thiểu để phát "MUA NGAY" (= ngưỡng của ptcp)


# --- Phiên giao dịch (giờ Việt Nam) ---
PHIEN = [("09:00", "11:30"), ("13:00", "14:45")]
GIO_TONG_KET = "15:00"             # sau giờ này chế độ tu_dong = gửi bản tổng kết cuối ngày

# --- Thông báo ---
ANH_MUA_TOI_DA = 0                 # tin tổng kết: gửi tối đa N biểu đồ mốc giá cho các mã nhóm MUA (0 = tắt, 10/2026)
GUI_ANH = True                     # gửi kèm ảnh biểu đồ (MUA NGAY / cảnh báo bán) & ảnh bảng tổng kết
BAO_LAI_TRONG_NGAY = False         # False: chỉ báo khi mã CHUYỂN sang MUA NGAY (không lặp mỗi 15 phút); True: báo mọi lần chạy
FILE_TRANG_THAI = "trang_thai_canh_bao.json"
THU_MUC_CACHE = "cache_gia"

EV_NGUONG = 1.0                    # % – EV sau phí (ptcp) tối thiểu để phát MUA NGAY (= ngưỡng ptcp)

# --- Nhật ký & chấm điểm tín hiệu (canh_bao/nhat_ky.py) ---
GHI_NHAT_KY = True                 # ghi mọi tín hiệu (MUA NGAY, khuyến nghị ptcp, cảnh báo bán) & tự chấm ĐÚNG/SAI
KY_HAN_MUA = 63                    # phiên – hạn chấm lệnh mua khi ptcp không cho kỳ hạn (= SO_PHIEN_XAC_SUAT)
KY_HAN_BAN = 20                    # phiên – sau cảnh báo bán bao lâu thì so giá để chấm
# T+2, phí + trượt giá, ngưỡng trần/sàn, "ít mẫu": lấy từ ptcp/cau_hinh.py (một bộ máy chấm chung – ptcp/nhat_ky.py)

# --- HỆ THOÁT cho mã đang giữ (ptcp/he_thoat.py – Quỹ B 10/2026: T2-2R-ma10, = ptcp QUY_NGUONG_TUAN) ---
#   lãi < 1R : cắt lỗ ban đầu (cat_lo_goc; thiếu thì max(giá vốn − 2×ATR, −7%), tối thiểu 1,5×ATR)
#   lãi ≥ 1R : cắt lỗ động = đóng cửa cao nhất − 3×ATR, không dưới hoà vốn (+ phí)
#   lãi ≥ 2R : chuyển KHUNG TUẦN – bán khi đóng cửa tuần < MA10 tuần; sàn khoá lãi 1R; KHÔNG chốt lời cố định
#   63 phiên mà lãi < 1R : lệnh không chạy → bán.  Cắt lỗ chỉ dời LÊN; dùng mức cao hơn giữa hệ thống & cat_lo_dat.
DUNG_HE_THOAT = True               # False: quay về cách cũ (cắt lỗ / mục tiêu đặt tay + MACD tuần / SuperTrend / ptcp)
NGUONG_KHUNG_TUAN_R = 2.0          # lãi (theo R) chuyển khung tuần – PHẢI = ptcp QUY_NGUONG_TUAN (test kiểm tra; trước 10/2026: 3)
DOI_CAT_LO_TOI_THIEU_PCT = 0.5     # chỉ nhắc "DỜI CẮT LỖ" khi mức hệ thống cao hơn mức đã đặt ≥ 0,5%

# 41 mã đã backtest – dùng cho backtest (backtest_bot.py) & dự phòng độ rộng thị trường; cảnh báo quét MA_THEO_DOI + Bo_Loc.
MA_CHIEN_LUOC = ["ANV", "BID", "BSR", "CEO", "CSV", "DBC", "DGC", "DGW", "DHC", "DIG", "FPT", "GAS", "GMD", "GVR",
                 "HAG", "HAH", "HCM", "HPG", "HSG", "HVN", "KDH", "LPB", "MBB", "MSB", "MSN", "MWG", "NAB", "NKG",
                 "NVL", "PLX", "PNJ", "POW", "PVD", "PVS", "SSI", "TCB", "VCB", "VHM", "VJC", "VNM", "VPB"]
NGAY_BAT_DAU_CL = NGAY_BAT_DAU     # dữ liệu cho bản tin (≥ 1 năm để có MA200 & độ rộng thị trường)
FILE_TRANG_THAI_CL = "trang_thai_chien_luoc.json"   # CL đang áp dụng (để báo khi ĐỔI) – không chứa dữ liệu riêng

# --- TỔNG KẾT GỌN + FILE EXCEL (canh_bao/tong_ket_cl.py, bao_cao_excel.py) ---
#   Tin 15:20 chỉ còn: thị trường & CL · 🟢/✅/🟡 mua (mã | vùng | mục tiêu 1R→3R | cắt lỗ | đạt điểm mua) ·
#   ⏳ chờ điều chỉnh · ⛔ không vào · 💼 đang giữ (lãi/lỗ theo danh mục, cắt lỗ, mua thêm). Chi tiết → file Excel.
SO_MA_MOI_NHOM = 8                 # số mã tối đa mỗi nhóm trong tin (còn lại xem Excel)
BAO_SU_KIEN_QUYEN = True           # tin tổng kết: báo trước GDKHQ (chia / thưởng CP, cổ tức) – lịch VNDirect
SO_NGAY_BAO_QUYEN = 10             # báo sự kiện có GDKHQ trong 10 ngày tới
GUI_EXCEL = True                   # gửi file Excel chi tiết kèm tin tổng kết (riêng tư nếu có danh mục)
FILE_EXCEL = "bao_cao_chien_luoc.xlsx"
LOAI_NHAT_KY_CL = "CHIEN_LUOC"     # loại dòng nhật ký cho khuyến nghị chiến lược (chấm theo hệ thoát)

# --- ĐIỂM VÀO 15 PHÚT – đồng bộ chiến lược (ptcp/diem_vao_15p.py: một bộ tiêu chí cho cảnh báo & backtest) ---
#   Chỉ quét mã trong nhóm mua của tin tổng kết gần nhất, trong đúng phiên hiệu lực; không phủ quyết MACD tuần.
CACH_VAO_15P = "15P+GIO"           # 19/10/2026: backtest quỹ B theo cách vào khớp luật live (★ ATC, suất dự phòng, lọc biến
                                   # động, ĐẮT ½; 687 mã, nến 15' 09/2023–10/2026): 15P+GIO 17,6%/năm MDD −16,7% Sharpe 1,41
                                   # · 15P+GIO+ATC★ 15,4% / −19,0% / 1,13 · LO+ATC★ 7,0%. Mẫu ~3 năm – theo dõi. Trước:
                                   # 15P+GIO+ATC (17/10, số 22,5% đo khi mọi mã được ATC);
                                   # LO+ATC (cố định 10/2026, rổ chiến lược 41 mã);
                                   # "tu_dong": cách vào tốt nhất của lần backtest gần nhất (FILE_BACKTEST);
                                   # chưa backtest → "15P+ATC". Hoặc đặt cố định: ATO | 15P | 15P+ATC | 15P+GIO | VWAP | LO …
GIO_ATC = "14:25"                  # từ giờ này, cách vào "+ATC" chưa có điểm vào → báo đặt ATC nếu giá còn trong vùng
QUET_DANH_MUC_CU = True            # trong phiên: quét cả danh_muc_cu.csv (repo danh-muc) – chạm / sát cắt lỗ đề xuất
GAN_CAT_LO_PCT = 1.0               # trong phiên: mã đang giữ cách cắt lỗ ≤ 1% → nhắc chuẩn bị lệnh bán
FILE_BACKTEST = "ket_qua_backtest.json"   # kết quả backtest (công khai – chỉ thống kê, không có danh mục)
BACKTEST_TU = "2019-01-01"         # giá ngày cho backtest điểm bán / mua thêm
BACKTEST_15P_TU = "2023-09-11"     # nến 15' lấy từ ngày này – Vietcap có từ 11/09/2023 (VNDirect/DNSE/SSI chỉ ~1 năm)

# --- MUA THÊM mã đang giữ (đúng luật nhồi lệnh đã backtest – kiểu B) ---
#   Đủ cả: lãi đã ≥ NGUONG_KHUNG_TUAN_R (khung tuần) · đóng cửa lập đỉnh mới từ ngày mua · cách lần mua trước ≥ 10 phiên ·
#   cắt lỗ hiện tại ≥ giá vốn bình quân MỚI + phí (chạm cắt lỗ cả vị thế vẫn hoà vốn) · tối đa 2 lần.
MUA_THEM_TY_LE = 0.25              # mỗi lần mua thêm = 25% số CP đang giữ
MUA_THEM_GIAN_CACH = 10            # phiên
MUA_THEM_TOI_DA = 2

# --- KHỐI LƯỢNG THEO BIẾN ĐỘNG (Barroso & Santa-Clara – backtest 41 mã: lãi/năm 13,0% → 10,9%, sụt giảm lớn nhất
#     −27% → −19,5%, Sharpe giữ 1,05). KL gợi ý = RUI_RO_MOI_LENH_PCT % vốn ÷ (giá mua − cắt lỗ) × hệ số,
#     hệ số = min(1, ATR_MUC_TIEU_PCT ÷ ATR% của mã) – mã biến động mạnh mua ít đi; nhóm 🟡 thêm × ½.
KL_THEO_BIEN_DONG = False         # TẮT theo yêu cầu – KL = 1% vốn ÷ (giá mua − cắt lỗ), nhóm 🟡 ½
ATR_MUC_TIEU_PCT = 3.5             # % / ngày; 2,5 = an toàn hơn (sụt giảm ~−15%, lãi ~8,9%/năm)
RUI_RO_MOI_LENH_PCT = 0.75         # % vốn chấp nhận mất nếu chạm cắt lỗ – QUỸ B 10/2026 (trước: 1%)
SO_MA_MOI_TUAN = 5                 # ★ đánh dấu bấy nhiêu mã ưu tiên trong tin (= QUY_MOI_TUAN_TOI_DA của ptcp)
VON_TRIEU = None                   # tổng vốn (triệu đồng) – điền để tin ghi luôn số CP; None = chỉ ghi công thức

# --- MÃ TỪ BỘ LỌC (canh_bao/ma_bo_loc.py) ---
#   Bộ lọc (bo_loc/, workflow Quet dinh ky của repo này) chạy cuối mỗi phiên (quy_b + xu_huong) → ma_mua_bo_loc.json.
#   Tổng kết 15:20 đọc file đó, thêm mã vào danh sách quét trong BO_LOC_SO_PHIEN phiên kế tiếp. Bo_Loc lọc lại vẫn
#   đạt, hoặc vào nhóm mua 🟢/✅/🟡 = ĐẠT → hạn = BO_LOC_SO_PHIEN phiên tính từ ngày đó. Hết hạn → tự xoá (kể cả mã đang giữ – mã đó vẫn có cảnh báo bán / mua thêm ở phần danh mục riêng tư).
#   Muốn bỏ sớm 1 mã: xoá dòng của mã đó trong FILE_MA_BO_LOC.
DUNG_BO_LOC = True
BO_LOC_SO_PHIEN = 4                # theo dõi 4 PHIÊN GIAO DỊCH kế tiếp (T2–T6, trừ ngày nghỉ lễ bên dưới) – lọc lại / đạt thì tính lại
# Lịch lễ VN tự lấy từ thư viện `holidays` (mọi năm, Tết âm lịch, nghỉ bù) + phiên thật từ VNINDEX → không cần nhập.
# Chỉ thêm ở đây ngày HOSE nghỉ THÊM mà thư viện không có (để dự kiến hạn đúng ngay từ đầu).
NGAY_NGHI_GIAO_DICH = ["2025-05-02", "2026-01-02"]
FILE_MA_BO_LOC = "ma_bo_loc.json"  # trạng thái theo dõi (công khai – chỉ mã & ngày)
BO_LOC_REPO = "mihhle2006-beep/canh-bao-mua"   # 10/2026: bộ lọc (bo_loc/) chạy NGAY TRONG repo này (workflow
#                                                 Quet dinh ky) – đọc qua GitHub API để luôn lấy bản mới nhất
BO_LOC_PATH = "ma_mua_bo_loc.json"
BO_LOC_FILE = None                 # đường dẫn file trên máy (ưu tiên hơn GitHub) – hoặc biến môi trường BO_LOC_FILE

# --- TRANG TỔNG HỢP (canh_bao/trang_tong_hop.py) – 1 trang HTML: thị trường, tín hiệu hôm nay, độ chính xác.
#     (Giao dịch giả lập ở repo riêng gia_lap – đọc danh sách mua từ trang_thai_chien_luoc.json.)
#     Bản CÔNG KHAI → docs/index.html (GitHub Pages). Bản RIÊNG có danh mục thật → chỉ gửi Telegram.
DUNG_TRANG_TONG_HOP = True
FILE_TRANG = "docs/index.html"
GUI_TRANG_RIENG = True             # gửi kèm file HTML có mục 💼 danh mục thật qua Telegram (không commit)
