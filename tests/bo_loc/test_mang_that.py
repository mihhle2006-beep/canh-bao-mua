# -*- coding: utf-8 -*-
"""
KIỂM TRA NGUỒN THẬT (gọi API) – bỏ qua mặc định. Chạy trên Colab/máy có mạng để biết nguồn nào còn sống:
    pytest -m mang -v
Nguồn báo FAILED = API đó đang lỗi/đổi/chặn → bộ lọc sẽ tự chuyển sang nguồn khác.
"""
import pytest

from bo_loc.nguon import co_ban, gia

pytestmark = pytest.mark.mang


@pytest.mark.parametrize("ten", list(gia.NGUON_GIA))
def test_nguon_gia_song(ten):
    ham, don_vi = gia.NGUON_GIA[ten]
    df = gia.ve_nghin_dong(gia.chuan_hoa(ham("GMD", "2026-01-01", "2026-12-31", False)), don_vi)
    assert len(df) > 20
    assert 10 < df.close.iloc[-1] < 500, "đơn vị giá sai (phải là nghìn đồng)"


@pytest.mark.parametrize("ten", list(co_ban.NGUON_CO_BAN))
def test_nguon_co_ban_song(ten):
    d = co_ban.NGUON_CO_BAN[ten]("GMD")
    assert d and any(k in d for k in ("pe", "pb", "roe", "eps_nam"))
