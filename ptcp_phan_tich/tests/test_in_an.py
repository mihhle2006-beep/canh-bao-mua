# -*- coding: utf-8 -*-
"""Trình bày: bảng gọn, không tràn màn hình, không '-0.00', số thống nhất."""
import numpy as np
import pandas as pd

from ptcp.in_an import ve_bang, fmt, so_vn


def _bang():
    return pd.DataFrame({
        "Mức": ["Chốt lời 3 – MỤC TIÊU ĐỀ XUẤT", "CẮT LỖ (thống nhất)"],
        "Giá": [98.46, 75.28],
        "% so giá hiện tại": [26.88, -2.99],
        "Lãi/Lỗ (đồng)": [-0.0001, np.nan],
        "Hành động": ["Bán 40% còn lại (hoặc giữ nếu trailing stop chưa bị chạm) " * 2,
                      "Đóng cửa dưới → BÁN toàn bộ phần còn lại"],
    })


def test_bang_khong_tran_do_rong():
    txt = ve_bang(_bang(), rong=80)
    assert max(len(d) for d in txt.split("\n")) <= 80


def test_bang_khong_tach_khoi_va_khong_am_0():
    txt = ve_bang(_bang(), rong=80)
    assert "\\" not in txt                    # không còn kiểu tách khối của pandas
    assert "-0.00" not in txt
    assert "–" in txt                          # NaN hiển thị gạch ngang
    assert txt.count("─") > 10                 # có đường kẻ dưới tiêu đề


def test_tieu_de_toi_da_2_dong():
    txt = ve_bang(_bang(), rong=80).split("\n")
    i = next(k for k, d in enumerate(txt) if "─" in d)
    assert i <= 2


def test_an_cot_va_dinh_dang():
    txt = ve_bang(_bang(), an=["Lãi/Lỗ (đồng)"], dinh_dang={"% so giá hiện tại": "{:+.1f}"}, rong=120)
    assert "Lãi/Lỗ" not in txt and "+26.88" in txt and "-2.99" in txt      # % → tối đa 4 chữ số thập phân


def test_dinh_dang_so_thong_nhat():
    assert so_vn(34500) == "34,500" and so_vn(1.05, 2) == "1.05"
    assert fmt(1234.5) == "1,234.50" and fmt(2.5, 1, True) == "+2.5" and fmt(np.nan) == "N/A"


def test_in_gon_giu_dung_cac_muc():
    from ptcp.in_an import _CHAY, _loc_gon
    txt = "\n".join([
        "████", " TÓM TẮT – X", "  dòng tóm tắt", "####", " PHẦN B. MACD", "  dòng B", "####",
        " PHẦN D. KỊCH BẢN", "---", " D1. BẢNG", "  dòng D1", "---", " D2. BA KỊCH BẢN", "  dòng D2",
        "####", " PHẦN E. ĐỀ XUẤT", "---", " E1. ĐỀ XUẤT GIÁ", "  dòng E1", "---", " E2. CÁC MỨC", "  dòng E2",
        "####", " PHẦN F. KHỐI LƯỢNG", "  dòng F", "####", " PHẦN G. BỐI CẢNH", "  dòng G",
        "####", " PHẦN H. CƠ BẢN", "  dòng H", "####", " PHẦN I. BACKTEST", "  dòng bảng I",
        "  ──────────────", "  KẾT LUẬN BACKTEST – X", "   → ĐỨNG NGOÀI", "####", " PHẦN K. LỊCH SỬ", "  dòng K"])
    _CHAY["muc"] = ""
    ra = _loc_gon(txt)
    for co in ("dòng tóm tắt", "dòng D2", "dòng E1", "dòng G", "dòng H", "KẾT LUẬN BACKTEST", "ĐỨNG NGOÀI"):
        assert co in ra
    for khong in ("dòng B", "dòng D1", "dòng E2", "dòng F", "dòng bảng I", "dòng K"):
        assert khong not in ra
