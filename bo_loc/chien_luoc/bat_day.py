# -*- coding: utf-8 -*-
"""
BẮT ĐÁY – HỒI PHỤC CÓ XÁC NHẬN (gộp bat_day cũ + rui_ro_cao).
Giá đã giảm sâu, RSI thấp NHƯNG phải có tín hiệu đảo chiều (không mua khi chỉ mới rẻ); doanh nghiệp có lãi,
định giá hợp lý; cắt lỗ / mốc 1R–3R theo chiến lược thị trường. Muốn bản rủi ro cao (Beta lớn): --them beta_min=1.2
Nên dùng rủi ro/lệnh thấp (VD --rui_ro 0.5).
"""
CHIEN_LUOC = {
    "ten": "Bắt đáy",
    "mo_ta": "Bắt đáy – hồi phục có xác nhận (RSI thấp + tín hiệu đảo chiều, có lãi, P/E ≤ 20)",
    "bat_buoc": {
        "gtgd_min": 5,
        "xa_dinh52": 30,                       # đã chiết khấu ≥ 30% từ đỉnh 52 tuần
        "rsi_trong": (25, 45),                 # vừa thoát vùng quá bán, chưa hồi quá xa
        "tin_hieu_dao_chieu": None,            # RSI vượt 30 / MACD cắt lên / phân kỳ dương / nến đảo chiều tăng
        "eps_duong": None, "pe_max": 20,
    },
    "cong_diem": {
        "fa_khong_nguy_hiem": None,
        "phan_ky_duong": None, "day_cao_hon": None, "macd_ngay_cat_len": None, "vol_dot_bien": 1.5,
        "macd_tuan_tren_sig": None, "eps_tang_quy": None, "roe_min": 12,
        "gan_day52": 20,                       # còn gần đáy 52 tuần → rủi ro tới cắt lỗ ngắn
        "tren_ma200": None,                    # xu hướng dài hạn chưa gãy → hồi phục dễ thành công hơn
    },
}
