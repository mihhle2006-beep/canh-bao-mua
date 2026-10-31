# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(autouse=True)
def _khong_goi_lich_quyen(monkeypatch):
    """Test không gọi API lịch quyền (VNDirect) – test nào cần thì tự bật & giả lập."""
    from canh_bao import cau_hinh as C
    monkeypatch.setattr(C, "BAO_SU_KIEN_QUYEN", False)



@pytest.fixture(autouse=True)
def _khong_doc_nav_that(monkeypatch):
    """Test không đọc NAV tài khoản thật (vi_the.nav_that) – tin MUA không kèm số CP trừ test tự đặt."""
    from canh_bao import vi_the
    monkeypatch.setattr(vi_the, "_NAV", {"v": None})
