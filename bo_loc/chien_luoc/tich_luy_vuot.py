# -*- coding: utf-8 -*-
"""
TÍCH LŨY VÀ VƯỢT : cổ phiếu đi ngang > 20 phiên (biên độ ≤ 15%), rồi phiên gần nhất
tăng > 5% với khối lượng > 5 lần trung bình vùng tích lũy và đóng cửa vượt đỉnh nền.
Đổi ngưỡng (>5D/10D/20D/40D · KL >2/3/4/5 · giá >1/3/5/7%):
    --them tich_luy_vuot=40:3:3          (nền > 40 phiên, KL > 3×, giá > 3%)
    --them tich_luy_vuot=20:5:5:10       (thêm số thứ 4 = biên độ nền tối đa 10%)
Lưu ý: chạy trong phiên thì KL hôm nay chưa đủ → dùng --bo_nen_dang_chay hoặc chạy sau 15h.
"""
CHIEN_LUOC = {
    "ten": "Tích lũy & vượt nền",
    "mo_ta": "Tích lũy & vượt nền – > 20 phiên, KL > 5× TB nền, giá tăng > 5%, đóng cửa vượt đỉnh nền",
    "bat_buoc": {"gtgd_min": 3, "tich_luy_vuot": (20, 5, 5)},
    "cong_diem": {
        "tren_ma200": None, "macd_tuan_tren_sig": None, "rs_3t": 0, "vi_tri_52t": 60,
        "eps_duong": None, "fa_khong_nguy_hiem": None,
    },
}
