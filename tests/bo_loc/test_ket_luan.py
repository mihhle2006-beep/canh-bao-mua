# -*- coding: utf-8 -*-
"""Kiểm thử bước KẾT LUẬN: phân nhóm, nửa vị thế khi thăm dò, điều kiện cần chờ, lý do loại."""
import numpy as np
import pandas as pd

from bo_loc.ket_luan import in_ket_luan, lap_ket_luan


def _dong(ma, hd, **k):
    r = {"Mã": ma, "Hành động": hd, "Điểm tổng": 75.0, "Đạt lọc": "✔", "Giá": 50.0, "vung_mua": "48,00 – 50,00",
         "cat_lo_kh": 47.0, "kc_cat_lo": 6.0, "muc_tieu_kh": 58.0, "rr_kh": 2.7, "so_cp_kh": 3300,
         "gia_tri_kh": 165.0, "ty_trong_kh": 16.5, "Xu hướng": 85.0, "Động lượng": 72.0, "Định giá": 50.0,
         "Chất lượng": np.nan, "Rủi ro": 30.0, "Cờ đỏ (nặng)": "", "Lưu ý (nhẹ)": "", "Thiếu tiêu chí lọc": "",
         "SuperTrend": 49.2}
    r.update(k)
    return r


def test_phan_nhom_va_thu_tu():
    e = pd.DataFrame([_dong("LLL", "LOẠI", **{"Đạt lọc": "", "Thiếu tiêu chí lọc": "A; B"}),
                      _dong("TTT", "THEO DÕI – có cờ đỏ", **{"Cờ đỏ (nặng)": "Dưới SuperTrend (xu hướng ngắn hạn giảm)"}),
                      _dong("MMM", "MUA"), _dong("DDD", "MUA THĂM DÒ (½ vị thế)")])
    k = lap_ket_luan(e).set_index("Mã")
    assert list(k.index) == ["MMM", "DDD", "TTT", "LLL"]
    assert k.loc["MMM", "Kết luận"] == "[NÊN MUA]"
    assert k.loc["DDD", "Số CP"] == 1600                       # ½ của 3.300 làm tròn lô 100
    assert "vượt lại SuperTrend (49.20)" in k.loc["TTT", "Cần chờ"]            # bên trong: kiểu quốc tế
    assert k.loc["LLL", "Lý do loại"].startswith("không khớp chiến lược")
    assert "xu hướng tốt (85)" in k.loc["MMM", "Điểm mạnh"] and "rủi ro cao (30)" in k.loc["MMM", "Điểm yếu"]


def test_in_ket_luan_khong_loi(capsys):
    e = pd.DataFrame([_dong("MMM", "MUA"), _dong("CCC", "CHỜ NHỊP CHỈNH", **{"Lưu ý (nhẹ)": "RSI 78 – quá mua"})])
    in_ket_luan(lap_ket_luan(e), 1000, thieu_co_ban=True)
    from bo_loc.so import vn_hoa
    out = vn_hoa(capsys.readouterr().out)                                       # đầu ra: kiểu Việt Nam
    assert "[NÊN MUA]" in out and "▸ MMM" in out and "3.300 CP" in out and "chờ nhịp chỉnh" in out
    assert "Chất lượng" in out                                  # nhắc thiếu dữ liệu cơ bản


def test_cach_ghi_so_viet_nam_va_4_chu_so():
    from bo_loc.so import so4, vn_hoa
    assert vn_hoa("giá 1,234.56 (+5.0%) · 02/10/2026 10:30 · VN30 · list 1, 2") == \
        "giá 1.234,56 (+5,0%) · 02/10/2026 10:30 · VN30 · list 1, 2"
    assert so4(15.234567) == "15.2346" and so4(1.5) == "1.5" and so4(2.0, dau=True) == "+2"
    from bo_loc.bang import ve_bang
    import pandas as pd
    b = ve_bang(pd.DataFrame({"Mã": ["A"], "P/E": [12.345678], "Upside %": [3.0], "Giá": [12345.678]}),
                dinh_dang={"Upside %": "{:+.1f}"})
    assert "12.3457" in b and "+3" in b and "12,345.68" in b
