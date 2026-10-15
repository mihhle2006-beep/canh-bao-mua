# -*- coding: utf-8 -*-
"""MACD ngày vừa cho tín hiệu mua; cắt lỗ / mốc 1R–3R theo chiến lược thị trường."""
CHIEN_LUOC = {
    "ten": "Điểm mua",
    "mo_ta": "MACD ngày vừa cho tín hiệu mua",
    "bat_buoc": {"gtgd_min": 10, "macd_ngay_cat_len": None,
                 "khong_thung_ho_tro": None},
    "cong_diem": {"day_cao_hon": None, "phan_ky_duong": None, "macd_tuan_tren_sig": None,
                  "tren_ma200": None, "rsi_trong": (40, 65), "vol_dot_bien": 1.5, "rs_3t": 0},
}
