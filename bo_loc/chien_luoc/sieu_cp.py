# -*- coding: utf-8 -*-
"""
SIÊU CỔ PHIẾU TIỀM NĂNG – theo thống kê danh-muc/phan_tich_sieu_cp.py (mã × quý 2013–2025, nền 8% mã tăng ≥ 100%
trong 12 tháng): vốn hoá ≤ 10 nghìn tỷ + GTGD TB20 ≥ 1,3× TB120 → 13% (bắt 44% siêu CP); thêm nền tích luỹ (cách
đỉnh 52T ≤ 15% + biến động co ≤ 0,8) → ~14%. Lợi nhuận tăng mạnh (CANSLIM C/A) KHÔNG làm tỷ lệ cao hơn nền.
Chỉ là danh sách THEO DÕI – mua theo điểm mua của Quỹ Bứt Phá.
"""
CHIEN_LUOC = {
    "ten": "Siêu cổ phiếu tiềm năng",
    "mo_ta": "Vốn hoá ≤ 10.000 tỷ, thanh khoản tăng ≥ 1,3× – cộng điểm khi gần đỉnh 52T, nền co, xu hướng tăng",
    "bat_buoc": {"gtgd_min": 1, "von_hoa_max": 10_000, "gtgd_tang_min": 1.3},
    "cong_diem": {
        "gan_dinh52": 15, "bien_dong_co_max": 0.8, "tren_ma200": None, "ma50_tren_ma200": None, "rs_3t": 0,
    },
}
