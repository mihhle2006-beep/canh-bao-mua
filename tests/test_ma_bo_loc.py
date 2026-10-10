# -*- coding: utf-8 -*-
"""Mã từ bộ lọc Bo_Loc: hạn 4 phiên, lọc lại / đạt thì tính lại 4 phiên, hết hạn thì xoá – kể cả mã đang giữ."""
import pandas as pd
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
    assert moi == ["FPT", "HPG"] and tt["ma"]["FPT"]["het_han"] == "2026-10-09"   # T2 + 4 phiên = T6; VNM cố định
    assert bl.nhan_nguon(tt, _nguon("2026-10-05", AAA=["rieng"])) == []            # cùng lần quét → không nhận lại
    assert bl.danh_dau_dat(tt, ["HPG", "MWG"], "2026-10-08 15:20") == ["HPG"]
    assert tt["ma"]["HPG"]["het_han"] == "2026-10-14"                              # đạt T5 → +4 phiên = T4 tuần sau
    assert bl.danh_dau_dat(tt, ["HPG"], "2026-10-12") == [] and tt["ma"]["HPG"]["het_han"] == "2026-10-16"
    assert bl.xoa_het_han(tt, "2026-10-09 15:20") == []                            # còn trong hạn (phiên cuối)
    assert bl.xoa_het_han(tt, "2026-10-12 15:20") == ["FPT"]                       # hết 4 phiên chưa đạt → xoá
    assert bl.xoa_het_han(tt, "2026-10-19") == ["HPG"]
    assert bl.nhan_nguon(tt, _nguon("2026-10-22", FPT=["rieng"])) == ["FPT"]       # lọc ra lại sau khi xoá → hạn mới
    assert tt["ma"]["FPT"]["het_han"] == "2026-10-28"


def test_loc_lai_gia_han():
    tt = {}
    bl.nhan_nguon(tt, _nguon("2026-10-05", FPT=["rieng"]))
    assert bl.nhan_nguon(tt, _nguon("2026-10-08", FPT=["xu_huong"])) == []        # vẫn đạt bộ lọc → hạn tính lại
    assert tt["ma"]["FPT"]["het_han"] == "2026-10-14" and tt["ma"]["FPT"]["chien_luoc"] == ["rieng", "xu_huong"]
    assert bl.xoa_het_han(tt, "2026-10-14") == [] and bl.xoa_het_han(tt, "2026-10-15") == ["FPT"]


def test_rut_han_cu_14_ngay():
    tt = {"ma": {"SBT": {"ngay_them": "2026-10-08", "het_han": "2026-10-22", "dat_gan_nhat": "2026-10-08"}}}
    assert bl.xoa_het_han(tt, "2026-10-10") == [] and tt["ma"]["SBT"]["het_han"] == "2026-10-14"


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


def test_han_bo_qua_ngay_le():
    assert bl.han_tu("2026-08-27") == "2026-09-07"        # nghỉ Quốc khánh 31/08–02/09 không tính phiên
    assert bl.han_tu("2026-02-12") == "2026-02-25"        # nghỉ Tết 16–20/02
    assert bl.han_tu("2026-04-23") == "2026-05-04"        # nghỉ 27/04 và 30/04–01/05
    tt = {}
    bl.nhan_nguon(tt, {"ngay_quet": "2026-08-27", "ma": {"FPT": ["rieng"]}})
    assert bl.xoa_het_han(tt, "2026-09-04 15:20") == [] and bl.xoa_het_han(tt, "2026-09-08") == ["FPT"]


def test_lich_le_tu_dong_nam_moi():
    assert "2027-02-08" in bl.ngay_nghi(2027)                # Tết 2027 – tự tính, không cần nhập
    assert bl.han_tu("2027-02-03") == "2027-02-16"          # nghỉ Tết 04–10/02/2027


def test_dem_phien_that_khi_nghi_dot_xuat():
    phien = pd.bdate_range("2026-10-01", "2026-10-14").drop(pd.Timestamp("2026-10-07"))   # 07/10 nghỉ đột xuất
    assert bl.han_tu("2026-10-05", phien, "2026-10-14") == "2026-10-12"
    assert bl.han_tu("2026-10-05", phien[phien <= "2026-10-08"], "2026-10-08") == "2026-10-12"   # 2 phiên thật + 2 dự kiến
    tt = {"ma": {"FPT": {"ngay_them": "2026-10-05", "het_han": "2026-10-09"}}}
    assert bl.xoa_het_han(tt, "2026-10-09 15:20", phien) == [] and tt["ma"]["FPT"]["het_han"] == "2026-10-12"
