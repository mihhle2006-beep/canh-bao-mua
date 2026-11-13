# -*- coding: utf-8 -*-
import pytest


@pytest.fixture(autouse=True)
def _khong_goi_lich_quyen(monkeypatch):
    """Test không gọi API lịch quyền (VNDirect) – test nào cần thì tự bật & giả lập."""
    from canh_bao import cau_hinh as C
    monkeypatch.setattr(C, "BAO_SU_KIEN_QUYEN", False)



@pytest.fixture(autouse=True)
def _xoa_loi_phu():
    """Lỗi phần phụ (canh_bao.loi_phu – dòng ⚙ cuối tin tổng kết) không dính từ test này sang test khác."""
    from canh_bao import loi_phu
    loi_phu.xoa()
    yield
    loi_phu.xoa()


@pytest.fixture(autouse=True)
def _trang_thai_rieng_tam(monkeypatch, tmp_path):
    """Trạng thái riêng (suất Quỹ Bứt Phá "_suat" – chay._qua_suat) ghi vào thư mục tạm của test, không vào repo."""
    from canh_bao import vi_the
    monkeypatch.setattr(vi_the, "FILE_TRANG_THAI_BAN", str(tmp_path / "cache_ptcp" / "trang_thai_ban.json"))


@pytest.fixture(autouse=True)
def _khong_doc_nav_that(monkeypatch):
    """Test không đọc NAV tài khoản thật (vi_the.nav_that) – tin MUA không kèm số CP trừ test tự đặt."""
    from canh_bao import vi_the
    monkeypatch.setattr(vi_the, "_NAV", {"v": None})
    monkeypatch.setattr(vi_the, "_LENH_THAT", {"v": []})             # không đọc lenh_that.csv thật


@pytest.fixture(autouse=True)
def _khong_quy_doi_quyen_khi_cham(monkeypatch):
    """Bộ chấm chung (ptcp/nhat_ky) không gọi API lịch quyền khi quy đổi giá ngày GDKHQ – test tự giả lập."""
    try:
        from ptcp import nhat_ky as NK
    except ImportError:
        return
    if hasattr(NK, "QUY_DOI_QUYEN"):
        monkeypatch.setattr(NK, "QUY_DOI_QUYEN", False)


@pytest.fixture(autouse=True)
def _khong_hoi_bang_gia_so(monkeypatch):
    """Quy đổi GDKHQ trong phiên không gọi bảng giá / finfo (hệ số sở) – test nào cần thì tự giả lập."""
    from canh_bao import diem_vao
    monkeypatch.setattr(diem_vao, "_HE_SO_SO_GOC", diem_vao._he_so_so, raising=False)
    monkeypatch.setattr(diem_vao, "_he_so_so", lambda ma, bay_gio: None)


@pytest.fixture(autouse=True)
def _khong_doc_so_lenh(monkeypatch):
    """Tin MUA NGAY không gọi bảng giá Vietcap lấy sổ lệnh (diem_vao.so_lenh) – test nào cần thì tự giả lập."""
    from canh_bao import diem_vao
    monkeypatch.setattr(diem_vao, "_SO_LENH_GOC", diem_vao.so_lenh, raising=False)
    monkeypatch.setattr(diem_vao, "so_lenh", lambda ma: None)


@pytest.fixture(autouse=True)
def _nut_khong_doc_mang(monkeypatch):
    """Nút đặt lệnh (lenh_tele.kiem_suat) không đọc danh mục / lệnh thật qua mạng – test tự đặt."""
    from canh_bao import lenh_tele
    monkeypatch.setattr(lenh_tele, "_doc_tep", lambda url, headers=None: None)
