# -*- coding: utf-8 -*-
"""Màu chủ đạo XANH LÁ: chữ màu trên màn hình (ANSI – Colab/GitHub Actions hiển thị được) & mã màu Excel/biểu đồ."""
import os

BAT_MAU = os.environ.get("PTCP_KHONG_MAU", "") == ""          # đặt PTCP_KHONG_MAU=1 để tắt màu chữ

XANH_DAM_HEX = "1B5E20"      # tiêu đề Excel, tiêu đề biểu đồ
XANH_HEX = "2E7D32"          # nhấn
XANH_NHAT_HEX = "E8F5E9"     # dòng xen kẽ Excel
XANH_VUA_HEX = "C8E6C9"


def _m(ma, chu):
    return f"\033[{ma}m{chu}\033[0m" if BAT_MAU else chu


def xanh(chu):
    return _m("1;32", chu)


def xanh_nhat(chu):
    return _m("32", chu)


def vang(chu):
    return _m("1;33", chu)


def do(chu):
    return _m("1;31", chu)


def mo(chu):
    return _m("2", chu)
