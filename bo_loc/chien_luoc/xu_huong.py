# -*- coding: utf-8 -*-
"""
XU HƯỚNG – MUA THEO ĐÀ (gộp xu_huong cũ + rui_ro_cao_xu_huong).
Cổ phiếu đang tăng (giá > MA50 > MA200, MACD ngày & tuần tốt), mạnh hơn VN-Index, doanh nghiệp có lãi.
Muốn bản rủi ro cao (Beta lớn): --them beta_min=1.2
"""
CHIEN_LUOC = {
    "ten": "Xu hướng",
    "mo_ta": "Xu hướng – mua theo đà (giá > MA50 > MA200, RSI 50–72, mạnh hơn VN-Index, có lãi)",
    "bat_buoc": {
        "gtgd_min": 10, "tren_ma50": None, "ma50_tren_ma200": None,
        "macd_ngay_tren_sig": None, "macd_tuan_tren_sig": None,
        "rsi_trong": (50, 72), "rs_3t": 0, "eps_duong": None,
    },
    "cong_diem": {
        "fa_khong_nguy_hiem": None, "cau_truc_tang": None, "gan_dinh52": 15, "breakout_20": None, "vol_dot_bien": 1.5, "adx_min": 20,
        "macd_tuan_tren_0": None, "eps_tang_quy": None, "pe_max": 25,
    },
}
