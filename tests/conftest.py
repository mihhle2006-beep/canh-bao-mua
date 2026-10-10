# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(autouse=True)
def _khong_goi_lich_quyen(monkeypatch):
    """Test không gọi API lịch quyền (VNDirect) – test nào cần thì tự bật & giả lập."""
    from canh_bao import cau_hinh as C
    monkeypatch.setattr(C, "BAO_SU_KIEN_QUYEN", False)
