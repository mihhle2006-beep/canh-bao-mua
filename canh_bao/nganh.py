# -*- coding: utf-8 -*-
"""Ngành & mã cùng ngành – dùng bản đồ ngành CHUNG của ptcp (ptcp/nganh.py); ptcp cũ chưa có thì bỏ qua."""


def nganh_cua(ma):
    try:
        from ptcp.nganh import nganh_cua as f
    except ImportError:
        return ""
    return f(ma)


def ma_cung_nganh(ma, so_ma=4):
    try:
        from ptcp.nganh import ma_cung_nganh as f
    except ImportError:
        return []
    return f(ma, so_ma)
