# -*- coding: utf-8 -*-
"""Danh sách mã quét: nhóm hose_hnx (17/10/2026 – Quỹ Bứt Phá mua cả HNX) – không mạng."""
from bo_loc import danh_sach_ma as D


def test_hose_hnx_gop_khong_trung(monkeypatch):
    monkeypatch.setattr(D, "lay_danh_sach_hose", lambda: (["HPG", "SSI"], "file"))
    monkeypatch.setattr(D, "lay_danh_sach_hnx", lambda: ["SHS", "HPG", "CEO"])
    assert D.lay_danh_sach_ma(nhom="hose_hnx") == ["HPG", "SSI", "SHS", "CEO"]


def test_hnx_tu_ptcp(monkeypatch):
    from ptcp import san
    monkeypatch.setattr(san, "doc_san", lambda: {"HOSE": ["HPG"], "HNX": ["SHS", "CEO"]})
    assert D.lay_danh_sach_hnx() == ["SHS", "CEO"]
