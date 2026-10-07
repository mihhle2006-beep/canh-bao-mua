# -*- coding: utf-8 -*-
"""Rổ VN30 online: nhận nhiều dạng JSON, kết quả lạ / lỗi mạng → danh sách gõ sẵn (không mạng)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import ro_vn30  # noqa: E402

RO = [f"A{chr(65 + i // 26)}{chr(65 + i % 26)}" for i in range(30)]


def test_doc_nhieu_dang_json():
    assert ro_vn30.lay_vn30(lambda url: RO)[0] == sorted(RO)
    assert ro_vn30.lay_vn30(lambda url: {"data": [{"stockSymbol": m} for m in RO]})[0] == sorted(RO)
    assert ro_vn30.lay_vn30(lambda url: {"data": [{"code": m.lower()} for m in RO]})[0] == sorted(RO)


def test_khong_hop_le_hoac_loi_thi_dung_danh_sach_san():
    def loi(url):
        raise OSError("mất mạng")
    assert ro_vn30.lay_vn30(loi) == (list(C.MA_VN30), "danh sách gõ sẵn (cau_hinh.MA_VN30)")
    assert ro_vn30.lay_vn30(lambda url: RO[:10])[0] == list(C.MA_VN30)            # quá ít mã
    assert ro_vn30.lay_vn30(lambda url: RO[:29] + ["VN30F2410"])[0] == list(C.MA_VN30)   # mã lạ


def test_nguon_dau_loi_thi_thu_nguon_sau():
    goi = []

    def lay(url):
        goi.append(url)
        if len(goi) == 1:
            raise OSError
        return RO
    ds, nguon = ro_vn30.lay_vn30(lay)
    assert ds == sorted(RO) and nguon == ro_vn30.NGUON[1][0]
