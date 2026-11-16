# -*- coding: utf-8 -*-
"""Lưu số CP / tỷ trọng bot gợi ý (tin MUA 15', tin tổng kết) → danh-muc/lenh_that_goi_y.csv cho dmuc/tuan_thu."""
import base64
import csv
import io
import urllib.error

import pandas as pd

from canh_bao import kl_goi_y as K


def _dong(ngay="2026-11-16", ma="AAA", nguon="MUA_NGAY", so_cp=300, tt="5.20"):
    return {"ngay": ngay, "thoi_diem": "10:15", "ma": ma, "nguon": nguon, "so_cp": so_cp, "ty_trong": tt, "gia": "20.00"}


def test_gop_thay_dong_cung_khoa_bo_dong_cu():
    cu, n = K.gop("", [_dong(), _dong(ma="BBB")])
    assert n == 2 and cu.splitlines()[0] == ",".join(K.COT)
    _, n = K.gop(cu, [_dong()])                                         # gửi lặp cùng số → không đổi
    assert n == 0
    moi, n = K.gop(cu, [_dong(so_cp=400), _dong(nguon="TONG_KET", so_cp="")])
    r = list(csv.DictReader(io.StringIO(moi)))
    assert n == 2 and len(r) == 3 and [x["so_cp"] for x in r if x["ma"] == "AAA" and x["nguon"] == "MUA_NGAY"] == ["400"]
    cu2, _ = K.gop(moi, [_dong(ngay="2026-01-02", ma="CCC")])
    sach, _ = K.gop(cu2, [], hom_nay="2026-11-16")                       # quá GIU_NGAY ngày → bỏ
    assert "CCC" not in sach and "AAA" in sach


class _Loi(urllib.error.HTTPError):
    def __init__(self, code):
        super().__init__("u", code, "x", {}, None)


def test_ghi_tao_moi_va_thu_lai_khi_sha_cu(monkeypatch):
    monkeypatch.setenv("DANH_MUC_TOKEN_GHI", "t")
    kho, goi_ds = {"nd": None, "sha": None, "xung_dot": 1}, []

    def goi(url, data=None, headers=None, method=None):
        goi_ds.append(method or "GET")
        if method == "PUT":
            if kho["xung_dot"]:
                kho["xung_dot"] -= 1
                raise _Loi(409)
            kho["nd"], kho["sha"] = base64.b64decode(data["content"]).decode(), "s2"
            return {}
        if kho["nd"] is None:
            raise _Loi(404)
        return {"content": base64.b64encode(kho["nd"].encode()).decode(), "sha": kho["sha"]}

    assert K.ghi([_dong()], "2026-11-16", goi=goi) == 1 and goi_ds == ["GET", "PUT", "GET", "PUT"]
    assert "AAA" in kho["nd"]
    assert K.ghi([_dong()], "2026-11-16", goi=goi) == 0                   # không đổi → không ghi
    monkeypatch.delenv("DANH_MUC_TOKEN_GHI")
    assert K.ghi([_dong(ma="ZZZ")], goi=goi) == 0                         # không token → bỏ qua


def test_dong_tong_ket_ty_trong_va_phien_hieu_luc():
    k = {"ma": "AAA", "nhom": "MUA_MOI", "gia": 20.0, "den": 20.5, "cl": 19.0, "hieu_luc": pd.Timestamp("2026-11-17"),
         "he_so_nhiet": 1.0, "he_so_quy": 0.5, "he_so_kl": 1.0}
    d = K.dong_tong_ket(k, pd.Timestamp("2026-11-16 15:20"))
    assert d["ngay"] == "2026-11-17" and d["nguon"] == "TONG_KET" and d["so_cp"] == ""
    assert abs(float(d["ty_trong"]) - min(0.75 * 0.5 / ((20.5 - 19) / 20.5 * 100) * 100, 20)) < 0.01
