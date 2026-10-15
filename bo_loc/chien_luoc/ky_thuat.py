# -*- coding: utf-8 -*-
"""KỸ THUẬT là chính (xu hướng, động lượng, thanh khoản) + cơ bản tối thiểu 4/7. Chiến lược mặc định."""
from ..cau_hinh import SUPERTREND

CHIEN_LUOC = {
    "ten": "Kỹ thuật",
    "mo_ta": "Kỹ thuật là chính (xu hướng, động lượng, thanh khoản) + cơ bản tối thiểu",
    "bat_buoc": {
        "gtgd_min": 5, "klgd_min": 100_000,              # thanh khoản
        "tren_supertrend": SUPERTREND,                   # xu hướng ngắn hạn
        "tren_ma50": None, "ma20_tren_ma50": None,       # cấu trúc trung bình động
        "macd_ngay_tren_sig": None,                      # động lượng ngày
        "macd_tuan_tren_sig": None,                      # xu hướng lớn (khung tuần)
        "rsi_trong": (45, 75),                           # khoẻ nhưng chưa quá mua
        "khong_thung_ho_tro": None,
    },
    "cong_diem": {
        "ma50_tren_ma200": None, "ma20_doc_len": None, "adx_min": 20,
        "cau_truc_tang": None, "day_cao_hon": None, "macd_ngay_cat_len": None,
        "macd_tuan_tren_0": None, "breakout_20": None, "vol_dot_bien": 1.5,
        "rs_3t": 0,
        "gan_dinh52": 15,          # cách đỉnh 52 tuần không quá 15%
        "cach_xa_day52": 30,       # cao hơn đáy 52 tuần ít nhất 30%
        "vi_tri_52t": 75,          # giá ở 75–100% biên độ 52 tuần
    },
    "toi_thieu": {
        "can_dat": 4,
        "tieu_chi": {
            "pe_max": 17, "roe_min": 12, "roa_min": 5,
            "eps_tang_nam": None, "eps_tang_quy": None,
            "no_phai_tra_tts_max": 60, "pb_max": 3,
        },
    },
}
