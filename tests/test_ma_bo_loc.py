# -*- coding: utf-8 -*-
"""Mã từ bộ lọc Bo_Loc: hạn 2 tuần, đạt thì thêm 2 tuần, hết hạn thì xoá – kể cả mã đang giữ (không mạng)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canh_bao import ma_bo_loc as bl  # noqa: E402


def _nguon(ngay, **ma):
    return {"ngay_quet": ngay, "ma": {m: list(cl) for m, cl in ma.items()}}


def test_vong_doi_ma():
    tt = {}
    moi = bl.nhan_nguon(tt, _nguon("2026-10-05", fpt=["rieng"], HPG=["xu_huong"], VNM=["rieng"]), co_dinh=["vnm"])
    assert moi == ["FPT", "HPG"] and tt["ma"]["FPT"]["het_han"] == "2026-10-19"   # VNM đã cố định → bỏ qua
    assert bl.nhan_nguon(tt, _nguon("2026-10-05", AAA=["rieng"])) == []            # cùng lần quét → không nhận lại
    assert bl.danh_dau_dat(tt, ["HPG", "MWG"], "2026-10-08 15:20") == ["HPG"]
    assert tt["ma"]["HPG"]["het_han"] == "2026-10-22"                              # đạt → thêm 2 tuần từ ngày đạt
    assert bl.danh_dau_dat(tt, ["HPG"], "2026-10-12") == [] and tt["ma"]["HPG"]["het_han"] == "2026-10-26"
    assert bl.xoa_het_han(tt, "2026-10-19 15:20") == []                            # còn trong hạn (ngày cuối)
    assert bl.xoa_het_han(tt, "2026-10-20 15:20") == ["FPT"]                       # hết 2 tuần chưa đạt → xoá
    assert bl.xoa_het_han(tt, "2026-10-27") == ["HPG"]
    assert bl.nhan_nguon(tt, _nguon("2026-10-22", FPT=["rieng"])) == ["FPT"]       # lọc ra lại sau khi xoá → hạn mới
    assert tt["ma"]["FPT"]["het_han"] == "2026-11-05"


def test_loc_lai_khong_gia_han():
    tt = {}
    bl.nhan_nguon(tt, _nguon("2026-10-05", FPT=["rieng"]))
    assert bl.nhan_nguon(tt, _nguon("2026-10-08", FPT=["xu_huong"])) == []
    assert tt["ma"]["FPT"]["het_han"] == "2026-10-19" and tt["ma"]["FPT"]["chien_luoc"] == ["rieng", "xu_huong"]
    assert bl.xoa_het_han(tt, "2026-10-20") == ["FPT"]


def test_doc_ghi_va_nguon_file(tmp_path, monkeypatch):
    p = tmp_path / "ma_bo_loc.json"
    assert bl.doc(str(p)) == {}
    bl.ghi({"ma": {"FPT": {"het_han": "2026-10-19"}}}, str(p))
    assert bl.doc(str(p))["ma"]["FPT"]["het_han"] == "2026-10-19"
    f = tmp_path / "ma_mua_bo_loc.json"
    f.write_text(json.dumps(_nguon("2026-10-05", FPT=["rieng"])), encoding="utf-8")
    monkeypatch.setenv("BO_LOC_FILE", str(f))
    assert bl.lay_nguon()["ma"] == {"FPT": ["rieng"]}
    assert "➕ thêm: FPT" in bl.dong_tin(["FPT"], [], [], {"ma": {"FPT": {}}})
    assert bl.dong_tin([], [], [], {}) == ""


def test_cung_ngay_quet_lan_hai_van_nhan():
    tt = {}
    bl.nhan_nguon(tt, {"ngay_quet": "2026-10-08", "luc": "2026-10-08 04:08", "ma": {}})
    assert bl.nhan_nguon(tt, {"ngay_quet": "2026-10-08", "luc": "2026-10-08 04:16", "ma": {"SBT": ["rieng"]}}) == ["SBT"]
    assert bl.nhan_nguon(tt, {"ngay_quet": "2026-10-08", "luc": "2026-10-08 04:16", "ma": {"AAA": ["rieng"]}}) == []


def test_dong_tin_ghi_ro_ma_tham_do():
    tt = {"ma": {"HDB": {"chien_luoc": ["xu_huong ½"]}, "TLG": {"chien_luoc": ["rieng", "xu_huong"]}}}
    t = bl.dong_tin(["HDB", "TLG"], ["TLG"], [], tt)
    assert "➕ thêm: HDB (xu_huong ½), TLG (rieng, xu_huong)" in t and "✅" in t and "½ = mua thăm dò" in t
