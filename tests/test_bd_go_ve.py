# -*- coding: utf-8 -*-
"""Lỗi "Object is disposed" (15/11/2026): lớp hình vẽ (bieu_do.js) còn gắn vào biểu đồ giá đã xoá → lần cập nhật sau
(mở trang Biểu đồ) làm thư viện vẽ lại biểu đồ đã huỷ. Mọi chỗ xoá biểu đồ giá phải qua bo_bd_gia() (gỡ lớp vẽ trước)."""
import re


def test_xoa_bieu_do_gia_qua_bo_bd_gia():
    h = open("docs/ma/index.html", encoding="utf-8").read()
    i = h.index("function bo_bd_gia() {")
    than = h[i:h.index("\n}", i)]
    assert than.index("BD_VE?.go?.()") < than.index("BD_GIA.remove()")      # gỡ lớp vẽ TRƯỚC khi xoá
    ngoai = h[:i] + h[h.index("\n}", i):]
    assert "BD_GIA.remove()" not in ngoai and not re.search(r"BD_GIA = null; BD_DK = null", ngoai)


def test_ve_go_tach_lop_ve():
    j = open("docs/ma/bieu_do.js", encoding="utf-8").read()
    i = j.index("VE.go = () => {")
    than = j[i:j.index("\n};", i)]
    assert "detachPrimitive(PRIM)" in than and "PRIM = null" in than and "C = null" in than
    assert "MA_GO" in j[j.index("VE.gan = "):j.index("VE.go = ")]                # vẽ lại cùng mã: giữ hình đang chọn
