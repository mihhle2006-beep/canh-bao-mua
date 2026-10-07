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
#   (rổ VN30 đổi kỳ tháng 1 & 7 – cập nhật danh sách trên khi HOSE công bố)
MA_THEM = ["DHC", "GMD", "MWG"]
MA_THEO_DOI = list(dict.fromkeys(MA_VN30 + MA_THEM))
# Mã tự thêm từ bộ lọc (repo Bo_Loc, quét thứ 2 & thứ 5) nằm ở FILE_MA_BO_LOC – xem mục "MÃ TỪ BỘ LỌC" cuối file.
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

# --- Nhật ký & chấm điểm tín hiệu (canh_bao/nhat_ky.py) ---
GHI_NHAT_KY = True                 # ghi mọi tín hiệu (MUA NGAY, khuyến nghị ptcp, cảnh báo bán) & tự chấm ĐÚNG/SAI
KY_HAN_MUA = 63                    # phiên – hạn chấm lệnh mua khi ptcp không cho kỳ hạn (= SO_PHIEN_XAC_SUAT)
KY_HAN_BAN = 20                    # phiên – sau cảnh báo bán bao lâu thì so giá để chấm
# T+2, phí + trượt giá, ngưỡng trần/sàn, "ít mẫu": lấy từ ptcp/cau_hinh.py (một bộ máy chấm chung – ptcp/nhat_ky.py)

# --- HỆ THOÁT MỚI cho mã đang giữ (ptcp/he_thoat.py – gốc T2-3R-ma10 đã backtest trên 41 mã 2019–2026) ---
#   lãi < 1R : cắt lỗ ban đầu (cat_lo_goc; thiếu thì max(giá vốn − 2×ATR, −7%), tối thiểu 1,5×ATR)
#   lãi ≥ 1R : cắt lỗ động = đóng cửa cao nhất − 3×ATR, không dưới hoà vốn (+ phí)
#   lãi ≥ 3R : chuyển KHUNG TUẦN – bán khi đóng cửa tuần < MA10 tuần; sàn khoá lãi 2R; KHÔNG chốt lời cố định
#   63 phiên mà lãi < 1R : lệnh không chạy → bán.  Cắt lỗ chỉ dời LÊN; dùng mức cao hơn giữa hệ thống & cat_lo_dat.
DUNG_HE_THOAT = True               # False: quay về cách cũ (cắt lỗ / mục tiêu đặt tay + MACD tuần / SuperTrend / ptcp)
NGUONG_KHUNG_TUAN_R = 3.0          # lãi (theo R) để chuyển sang bán theo khung tuần
DOI_CAT_LO_TOI_THIEU_PCT = 0.5     # chỉ nhắc "DỜI CẮT LỖ" khi mức hệ thống cao hơn mức đã đặt ≥ 0,5%

# --- BẢN TIN CHIẾN LƯỢC CL1 / CL2 (canh_bao/chien_luoc_bot.py – dùng ptcp/chien_luoc.py & he_thoat.py) ---
#   Điểm thị trường 8 chỉ báo (cuối tháng): ≥ 5 → CL2 (A0 70% + VN-Index 30%), ≤ 2 → CL1 (A0 50% + B 50%), 3–4 giữ.
#   A0 = vào MACD ngày KHÔNG lọc tuần; B = vào MACD ngày lọc tuần + nhồi lệnh; cả hai thoát theo hệ thoát mới.
DUNG_CHIEN_LUOC = True             # gửi bản tin chiến lược sau tin tổng kết 15:20 (tin CÔNG KHAI – không dùng danh mục)
# 41 mã đã backtest – chỉ dùng cho backtest (backtest_bot.py); cảnh báo hằng ngày quét MA_THEO_DOI + mã Bo_Loc.
MA_CHIEN_LUOC = ["ANV", "BID", "BSR", "CEO", "CSV", "DBC", "DGC", "DGW", "DHC", "DIG", "FPT", "GAS", "GMD", "GVR",
                 "HAG", "HAH", "HCM", "HPG", "HSG", "HVN", "KDH", "LPB", "MBB", "MSB", "MSN", "MWG", "NAB", "NKG",
                 "NVL", "PLX", "PNJ", "POW", "PVD", "PVS", "SSI", "TCB", "VCB", "VHM", "VJC", "VNM", "VPB"]
NGAY_BAT_DAU_CL = NGAY_BAT_DAU     # dữ liệu cho bản tin (≥ 1 năm để có MA200 & độ rộng thị trường)
FILE_TRANG_THAI_CL = "trang_thai_chien_luoc.json"   # CL đang áp dụng (để báo khi ĐỔI) – không chứa dữ liệu riêng
SO_MA_TRONG_TIN = 12               # số dòng tối đa mỗi mục (mua phiên tới / đang giữ) trong bản tin

# --- TỔNG KẾT GỌN + FILE EXCEL (canh_bao/tong_ket_cl.py, bao_cao_excel.py) ---
#   Tin 15:20 chỉ còn: thị trường & CL · 🟢/✅/🟡 mua (mã | vùng | mục tiêu 1R→3R | cắt lỗ | đạt điểm mua) ·
#   ⏳ chờ điều chỉnh · ⛔ không vào · 💼 đang giữ (lãi/lỗ theo danh mục, cắt lỗ, mua thêm). Chi tiết → file Excel.
SO_MA_MOI_NHOM = 8                 # số mã tối đa mỗi nhóm trong tin (còn lại xem Excel)
GUI_EXCEL = True                   # gửi file Excel chi tiết kèm tin tổng kết (riêng tư nếu có danh mục)
FILE_EXCEL = "bao_cao_chien_luoc.xlsx"
LOAI_NHAT_KY_CL = "CHIEN_LUOC"     # loại dòng nhật ký cho khuyến nghị chiến lược (chấm theo hệ thoát)

# --- ĐIỂM VÀO 15 PHÚT – đồng bộ chiến lược (ptcp/diem_vao_15p.py: một bộ tiêu chí cho cảnh báo & backtest) ---
#   Chỉ quét mã trong nhóm mua của tin tổng kết gần nhất, trong đúng phiên hiệu lực; không phủ quyết MACD tuần.
CACH_VAO_15P = "tu_dong"           # "tu_dong": cách vào tốt nhất của lần backtest gần nhất (FILE_BACKTEST);
                                   # chưa backtest → "15P+ATC". Hoặc đặt cố định: ATO | 15P | 15P+ATC | 15P+GIO | VWAP | LO …
GIO_ATC = "14:25"                  # từ giờ này, cách vào "+ATC" chưa có điểm vào → báo đặt ATC nếu giá còn trong vùng
GAN_CAT_LO_PCT = 1.0               # trong phiên: mã đang giữ cách cắt lỗ ≤ 1% → nhắc chuẩn bị lệnh bán
FILE_BACKTEST = "ket_qua_backtest.json"   # kết quả backtest (công khai – chỉ thống kê, không có danh mục)
BACKTEST_TU = "2019-01-01"         # giá ngày cho backtest điểm bán / mua thêm
BACKTEST_15P_TU = "2024-01-01"     # nến 15' lấy từ ngày này (nguồn giới hạn bao xa thì dùng tới đó)

# --- MUA THÊM mã đang giữ (đúng luật nhồi lệnh đã backtest – kiểu B) ---
#   Đủ cả: lãi đã ≥ 3R (khung tuần) · đóng cửa lập đỉnh mới từ ngày mua · cách lần mua trước ≥ 10 phiên ·
#   cắt lỗ hiện tại ≥ giá vốn bình quân MỚI + phí (chạm cắt lỗ cả vị thế vẫn hoà vốn) · tối đa 2 lần.
MUA_THEM_TY_LE = 0.25              # mỗi lần mua thêm = 25% số CP đang giữ
MUA_THEM_GIAN_CACH = 10            # phiên
MUA_THEM_TOI_DA = 2

# --- KHỐI LƯỢNG THEO BIẾN ĐỘNG (Barroso & Santa-Clara – backtest 41 mã: lãi/năm 13,0% → 10,9%, sụt giảm lớn nhất
#     −27% → −19,5%, Sharpe giữ 1,05). KL gợi ý = RUI_RO_MOI_LENH_PCT % vốn ÷ (giá mua − cắt lỗ) × hệ số,
#     hệ số = min(1, ATR_MUC_TIEU_PCT ÷ ATR% của mã) – mã biến động mạnh mua ít đi; nhóm 🟡 thêm × ½.
KL_THEO_BIEN_DONG = False         # TẮT theo yêu cầu – KL = 1% vốn ÷ (giá mua − cắt lỗ), nhóm 🟡 ½
ATR_MUC_TIEU_PCT = 3.5             # % / ngày; 2,5 = an toàn hơn (sụt giảm ~−15%, lãi ~8,9%/năm)
RUI_RO_MOI_LENH_PCT = 1.0          # % vốn chấp nhận mất nếu chạm cắt lỗ (trước khi nhân hệ số)
VON_TRIEU = None                   # tổng vốn (triệu đồng) – điền để tin ghi luôn số CP; None = chỉ ghi công thức

# --- MÃ TỪ BỘ LỌC (canh_bao/ma_bo_loc.py) ---
#   Bo_Loc chạy cuối phiên thứ 2 & thứ 5 (chiến lược rieng + xu_huong) → ma_mua_bo_loc.json (mã Hành động MUA).
#   Tổng kết 15:20 đọc file đó, thêm mã vào danh sách quét trong BO_LOC_SO_NGAY ngày. Vào nhóm mua 🟢/✅/🟡 = ĐẠT
#   → thêm hạn BO_LOC_SO_NGAY ngày từ ngày đạt. Hết hạn → tự xoá, trừ mã đang có trong danh mục (giữ lại).
#   Muốn bỏ sớm 1 mã: xoá dòng của mã đó trong FILE_MA_BO_LOC.
DUNG_BO_LOC = True
BO_LOC_SO_NGAY = 14                # 2 tuần (ngày lịch) – tính từ ngày thêm, đạt thì tính lại từ ngày đạt
FILE_MA_BO_LOC = "ma_bo_loc.json"  # trạng thái theo dõi (công khai – chỉ mã & ngày)
BO_LOC_REPO = "mihhle2006-beep/Bo_Loc"   # ghi đè bằng biến BO_LOC_REPO; repo riêng tư → secret BO_LOC_TOKEN
BO_LOC_PATH = "ma_mua_bo_loc.json"
BO_LOC_FILE = None                 # đường dẫn file trên máy (ưu tiên hơn GitHub) – hoặc biến môi trường BO_LOC_FILE

# --- TRANG TỔNG HỢP (canh_bao/trang_tong_hop.py) – 1 trang HTML: thị trường, tín hiệu hôm nay, độ chính xác.
#     (Giao dịch giả lập ở repo riêng gia_lap – đọc danh sách mua từ trang_thai_chien_luoc.json.)
#     Bản CÔNG KHAI → docs/index.html (GitHub Pages). Bản RIÊNG có danh mục thật → chỉ gửi Telegram.
DUNG_TRANG_TONG_HOP = True
FILE_TRANG = "docs/index.html"
GUI_TRANG_RIENG = True             # gửi kèm file HTML có mục 💼 danh mục thật qua Telegram (không commit)
