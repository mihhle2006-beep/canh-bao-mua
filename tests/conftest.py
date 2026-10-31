# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(autouse=True)
def _khong_goi_lich_quyen(monkeypatch):
    """Test không gọi API lịch quyền (VNDirect) – test nào cần thì tự bật & giả lập."""
    from canh_bao import cau_hinh as C
    monkeypatch.setattr(C, "BAO_SU_KIEN_QUYEN", False)


@pytest.fixture(autouse=True)
def _khong_co_doanh_nghiep(monkeypatch):
    """Test không đọc cờ doanh nghiệp thật (ptcp/co_dn.json) – tin MUA giữ đúng mẫu; test nào cần thì tự đặt _CACHE."""
    try:
        from ptcp import co_doanh_nghiep as C
    except ImportError:
        return
    monkeypatch.setattr(C, "_CACHE", {"d": {}})
