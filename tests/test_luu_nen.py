# -*- coding: utf-8 -*-
"""Kho nến 1' lâu dài (thi_truong/luu_nen.py – Release nen-1p repo bang-thi-truong): chia ngày giờ VN, file tháng, gộp
(cùng mã-ngày thì thay), lần đầu tải lùi – không gọi mạng."""
import gzip
import json
import os
from datetime import datetime

from thi_truong import luu_nen as L
from thi_truong import phut_web

VN = L.VN


def _ts(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=VN).timestamp())


def test_chia_ngay_theo_gio_vn():
    t = [_ts("2026-11-12 14:45"), _ts("2026-11-13 09:15"), _ts("2026-11-13 09:16"), _ts("2026-11-13 09:17")]
    d = L.chia_ngay(t, [10, 11, None, 11.2], [10, 11.1, 1, 11.3], [10, 10.9, 1, 11.1], [10, 11, 1, 11.2], [5, 6, 7])
    assert sorted(d) == ["2026-11-12", "2026-11-13"]
    tt, *_, c, v = phut_web.giai_ma(d["2026-11-13"])
    assert tt == [t[1], t[3]] and c == [11.0, 11.2] and v == [6, 0]                # nến thiếu giá bỏ, thiếu KL = 0


class Kho:
    def __init__(self, d, co=None):
        self.d, self.co, self.len = str(d), co, []
        os.makedirs(self.d, exist_ok=True)

    def ds_file(self):
        return None if self.co is None else list(self.co)

    def tai_ve(self, ten):
        p = os.path.join(self.d, "rl_" + ten)
        return p if os.path.exists(p) else None

    def dua_len(self, p):
        self.len.append(os.path.basename(p))
        os.replace(p, os.path.join(self.d, "rl_" + os.path.basename(p)))
        self.co = sorted(set(self.co or []) | {os.path.basename(p)})


def test_luu_lan_dau_tai_lui_roi_gop(tmp_path):
    goi = []

    def tai(m, tu, den):
        goi.append((m, tu, den))
        if m == "LOI":
            raise ValueError("x")
        ngay = ["2026-10-30 10:00", "2026-11-12 10:00", "2026-11-13 10:00"] if tu < _ts("2026-11-13 00:00") else ["2026-11-13 10:00"]
        t = [_ts(x) for x in ngay]
        gia = 20.0 if m == "AAA" else 30.0
        return [t, [gia] * len(t), [gia] * len(t), [gia] * len(t), [gia + (0.5 if len(t) == 1 else 0)] * len(t), [100] * len(t)]
    kho = Kho(tmp_path / "kho")
    bg = datetime(2026, 11, 13, 15, 12, tzinfo=VN)
    n = L.luu(["AAA", "BBB", "LOI"], kho, bg, tai=tai, in_ra=lambda *_: None)
    assert n == 6 and kho.len == ["nen1_2026-10.jsonl.gz", "nen1_2026-11.jsonl.gz"]     # kho trống → tải lùi 100 ngày
    assert goi[0][1] == int((bg.replace(hour=0, minute=0) - L.timedelta(days=L.LUI_DAU)).timestamp())
    th11 = L.doc_thang(kho.tai_ve("nen1_2026-11.jsonl.gz"))
    assert sorted(th11) == [("2026-11-12", "AAA"), ("2026-11-12", "BBB"), ("2026-11-13", "AAA"), ("2026-11-13", "BBB")]
    goi.clear()
    n = L.luu(["AAA", "BBB"], kho, bg, tai=tai, in_ra=lambda *_: None)                  # đã có kho → chỉ hôm nay, thay dòng cũ
    assert n == 2 and goi[0][1] == _ts("2026-11-13 00:00") and kho.len[-1] == "nen1_2026-11.jsonl.gz"
    th11 = L.doc_thang(kho.tai_ve("nen1_2026-11.jsonl.gz"))
    assert len(th11) == 4 and phut_web.giai_ma(json.loads(th11[("2026-11-13", "AAA")]))[4] == [20.5]
    with gzip.open(kho.tai_ve("nen1_2026-11.jsonl.gz"), "rt") as f:
        dong = [json.loads(x) for x in f]
    assert [(d["ngay"], d["ma"]) for d in dong] == sorted((d["ngay"], d["ma"]) for d in dong)   # sắp ngày rồi mã
    assert L.doc_thang(str(tmp_path / "khong.gz")) == {}


def test_main_chi_chay_sau_phien(monkeypatch, capsys):
    class Gio(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 16, 11, 36, tzinfo=VN)
    monkeypatch.setattr(L, "datetime", Gio)
    assert L.main(["--repo", "chu/bang", "--sau_phien"]) == 0 and "chưa hết phiên" in capsys.readouterr().out
