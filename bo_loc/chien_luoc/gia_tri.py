# -*- coding: utf-8 -*-
"""
GIÁ TRỊ – RẺ MÀ TỐT (gộp co_ban + tieu_chuan cũ + bộ lọc giá trị).
  • Bắt buộc: ROE ≥ 15%, P/E ≤ 10 (= giá ÷ EPS 4 quý tự tính), P/B ≤ 2, EPS > 0, quy mô & thanh khoản đủ lớn.
  • Chặn BẪY GIÁ TRỊ: lợi nhuận quý không giảm so cùng kỳ, giá chưa gãy xu hướng dài hạn (> MA200).
  • Cộng điểm: rẻ hơn ngành, sức khoẻ tài chính, dòng tiền, cổ tức, kiểm toán (từ bộ tiêu chuẩn cũ).
  • Ngân hàng/CK: chỉ tiêu nợ & thanh toán không phù hợp → chỉ ở cộng điểm.
Nới điều kiện: --them von_hoa_min=300,gtgd_min=2 ; bỏ một tiêu chí: --bo tren_ma200
"""
CHIEN_LUOC = {
    "ten": "Giá trị",
    "mo_ta": "Giá trị – rẻ mà tốt (ROE ≥ 15%, P/E ≤ 10, P/B ≤ 2, lợi nhuận không suy giảm)",
    "bat_buoc": {
        "von_hoa_min": 1000, "gtgd_min": 3,
        "eps_duong": None, "roe_min": 15, "pe_max": 10, "pb_max": 2,
        "eps_tang_quy": None,                  # tránh P/E thấp do lợi nhuận đỉnh/sắp giảm
        "tren_ma200": None,                    # tránh "rẻ vì đang có chuyện"
        "fa_khong_nguy_hiem": None,            # 10 tiêu chí tài chính: không tiêu chí nào ở mức Nguy hiểm
    },
    "cong_diem": {
        "pe_duoi_tv_nganh": None, "fa_diem_min": 60, "eps_tang_nam": None, "roa_min": 7,
        "no_phai_tra_tts_max": 60, "no_vay_tts_max": 50, "tt_hien_thoi_min": 1.5, "fcf_duong": None,
        "ty_suat_co_tuc_min": 4, "co_tuc_lien_tuc": 3, "kiem_toan_5nam": None,
        "macd_tuan_tren_sig": None,
    },
}
