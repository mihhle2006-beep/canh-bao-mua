# -*- coding: utf-8 -*-
"""cong_cu/so_huu/so_huu.py – dò tỷ lệ sở hữu trong chữ BCTN + kiểm chéo (không mạng)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cong_cu", "so_huu"))
import so_huu as S  # noqa: E402

BANG = """CƠ CẤU CỔ ĐÔNG
STT Đối tượng  Tổ chức  Cá nhân  Tổng
1  Cổ đông trong nước  61,1%  27,0%  88,1%  4  Sở hữu cá nhân  -  -  0,00%
2  Cổ đông nước ngoài  11,6%  0,3%  11,9%  Đại diện sở hữu cho PVN  35.601.638  10,00%
TỔNG CỘNG  72,7%  27,3%  100,0%
Danh sách cổ đông lớn
Tập đoàn Dầu khí Việt Nam  181.573.141  51%  8  Trương Thị Anh Đào  Trưởng BKS  -  -  0,00%
Cơ cấu nguồn vốn có vốn chủ sở hữu chiếm 66% tổng nguồn
VIMC tại Cảng, tỷ lệ đại diện là 18% vốn điều lệ
"""


def test_do_bang_3_cot_va_bo_cau_van():
    d = S.do_so_huu(BANG)
    assert d["Tổ chức %"][0] == 72.7 and d["Cá nhân %"][0] == 27.3
    assert d["Nhà nước %"][0] == 51.0                            # PVN, không cộng câu "đại diện 18%"
    assert "Nước ngoài %" not in d or d["Nước ngoài %"][0] != 10.0


def test_kiem_cheo_vietcap_va_nha_nuoc():
    nam = {"2022": {"Nước ngoài %": 0.0, "Nhà nước %": 51.0, "Tổ chức %": 21.0, "Cá nhân %": 28.0},
           "2023": {"Nhà nước %": 18.0}, "2024": {"Nhà nước %": 51.0}}
    S.kiem_cheo(nam, {"nn_nam": {"2022": 12.1}})
    assert nam["2022"]["Nước ngoài %"] == 12.1 and nam["2022"]["Nguồn nước ngoài"] == "Vietcap cuối năm"
    assert nam["2022"]["Tổ chức %"] == 72.0                      # bảng tách Nhà nước riêng → cộng vào Tổ chức
    assert "Nhà nước %" not in nam["2023"]                        # nhảy riêng 1 năm → bỏ
