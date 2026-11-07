# -*- coding: utf-8 -*-
"""
CHIẾN LƯỢC QUỸ BỨT PHÁ (mặc định) – chiến lược đang áp dụng, cùng luật với danh-muc, canh-bao-mua, gia_lap:
  · tín hiệu hệ B: MACD ngày cắt lên có lọc MACD tuần + nhồi lệnh (chien_luoc_tt → ptcp, mọi trạng thái thị trường)
  · nhóm MUA: 🟢 mua mới · ✅ vào trễ trong biên cho phép (phân nhóm lấy từ ptcp)
  · rổ HOSE + HNX: rổ thanh khoản tuần, RS 3 tháng không quá nóng, không thuộc nhóm biến động nhất (ptcp/loc_quy_b.json);
    giới hạn số mã giữ / mã mới mỗi tuần, suất dự phòng cho tín hiệu MẠNH
  · mã ĐẮT giảm khối lượng · nhiệt dài hạn và độ rộng rổ yếu giảm rủi ro (ptcp/do_rong.py) · hệ bắt đáy chạy riêng
    (ptcp/bat_day.py – tin tổng kết canh-bao-mua, không qua bộ lọc này)
  · thoát theo hệ thoát của ptcp
Ngưỡng / hệ số: ptcp/cau_hinh.py (repo kín); mô tả đầy đủ: danh-muc/LUAT_CHI_TIET.md.
Điểm cộng chỉ để xếp hạng trong danh sách lọc.
"""
CHIEN_LUOC = {
    "ten": "Quỹ Bứt Phá",
    "mo_ta": "Chiến lược đang áp dụng – Quỹ Bứt Phá: hệ B (MACD ngày + tuần), HOSE + HNX, rổ thanh khoản tuần, bỏ mã RS 3 tháng "
             "quá nóng và nhóm biến động nhất, giới hạn mã mới / tuần và số mã giữ (+ suất dự phòng cho tín hiệu mạnh), vào "
             "trễ trong biên cho phép, thoát theo hệ thoát; độ rộng rổ yếu giảm rủi ro; cùng luật với danh-muc / canh-bao-mua",
    "bat_buoc": {"gtgd_min": 3, "cl_tt_mua": None},
    "cong_diem": {"tren_ma200": None, "ma50_tren_ma200": None, "rs_3t": 0, "vol_dot_bien": 1.5, "gan_dinh52": 15},
}
