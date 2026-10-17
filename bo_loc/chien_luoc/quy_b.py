# -*- coding: utf-8 -*-
"""
CHIẾN LƯỢC QUỸ B (mặc định) – chiến lược đang áp dụng 10/2026, cùng luật với danh-muc, canh-bao-mua, gia_lap:
  · tín hiệu hệ B: MACD ngày cắt lên có lọc MACD tuần + nhồi lệnh (chien_luoc_tt → ptcp, mọi trạng thái thị trường)
  · nhóm MUA: 🟢 mua mới · ✅ vào trễ (giá ≤ giá vào hệ thống + ½R, cắt lỗ ≤ 7%, đủ KL – quỹ chỉ vào mã đã bỏ vì
    hết suất 5 mã mới/tuần); không còn nhóm ½ KL (phân nhóm lấy từ ptcp)
  · rổ HOSE + HNX (17/10/2026): chỉ mã top 100 GTGD TB20 (hạng chốt thứ Sáu tuần trước, cố định cả tuần), hạng RS
    3 tháng < 90 và không thuộc 30% mã biến động nhất rổ (ptcp/loc_quy_b.json – ngoài top / quá nóng / biến động →
    không mua mới); đủ 8 mã vẫn mua thêm 1 mã nếu tín hiệu MẠNH B (suất dự phòng),
    GTGD ≥ 3 tỷ
  · mã ĐẮT (định giá ≤ −20%) ½ khối lượng · nhiệt dài hạn (VN-Index Tăng) ½ rủi ro
  · thoát theo hệ thoát 2R – MA10 tuần
Điểm cộng chỉ để xếp hạng trong danh sách lọc.
"""
CHIEN_LUOC = {
    "ten": "Quỹ B",
    "mo_ta": "Chiến lược đang áp dụng – Quỹ B: hệ B (MACD ngày + tuần), HOSE + HNX, top 100 GTGD, bỏ RS 3T quá nóng "
             "và 30% mã biến động nhất, ≤ 5 mã mới/tuần, 8 mã + 1 suất dự phòng cho tín hiệu mạnh, vào trễ ≤ giá vào "
             "+ ½R, thoát 2R – MA10 tuần; "
             "cùng luật với danh-muc / canh-bao-mua",
    "bat_buoc": {"gtgd_min": 3, "cl_tt_mua": None},
    "cong_diem": {"tren_ma200": None, "ma50_tren_ma200": None, "rs_3t": 0, "vol_dot_bien": 1.5, "gan_dinh52": 15},
}
