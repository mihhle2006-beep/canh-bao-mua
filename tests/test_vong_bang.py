# -*- coding: utf-8 -*-
"""Vòng bảng thị trường (thi_truong/vong_bang.py – chạy ở repo bang-thi-truong): ô 30 giây, khung giờ, dọn file, vòng với
giờ giả, đẩy git (repo cục bộ) – không gọi mạng."""
import json
import os
import subprocess

import pandas as pd
import yaml

from thi_truong import vong_bang as V

T = pd.Timestamp


def test_o_va_ten_file():
    assert V.o_cua(T("2026-11-16 09:00:00")) == 1080 and V.o_cua(T("2026-11-16 09:00:29")) == 1080
    assert V.o_cua(T("2026-11-16 09:00:30")) == 1081
    assert V.ten_o(T("2026-11-16 09:00:31")) == "p/20261116/1081.json"
    assert V.ten_o(T("2026-11-16 00:00:05")) == "p/20261116/0000.json"
    assert round(V.cho_toi_o_sau(T("2026-11-16 09:00:12.5")), 3) == 18.5        # tới 09:00:30 + 1 giây


def test_khung_gio():
    assert V.cua_so(T("2026-11-16 08:49")) is None and V.cua_so(T("2026-11-16 08:50")) is not None
    assert V.cua_so(T("2026-11-16 11:36")) is None and V.cua_so(T("2026-11-16 12:50")) is not None
    assert V.cua_so(T("2026-11-16 15:12")) is None and V.cua_so(T("2026-11-14 10:00")) is None   # thứ Bảy
    assert not V.dang_gd(T("2026-11-16 08:59")) and V.dang_gd(T("2026-11-16 09:00")) and V.dang_gd(T("2026-11-16 11:30"))
    assert not V.dang_gd(T("2026-11-16 11:31")) and not V.dang_gd(T("2026-11-16 12:59")) and V.dang_gd(T("2026-11-16 15:04"))
    assert not V.dang_gd(T("2026-11-16 15:05"))


def test_don_o(tmp_path):
    for ngay, n in (("20261113", 3), ("20261116", 14)):
        os.makedirs(tmp_path / "p" / ngay)
        for i in range(n):
            (tmp_path / "p" / ngay / f"{1000 + i:04d}.json").write_text("{}")
    V.don_o(str(tmp_path), giu=12)
    assert not (tmp_path / "p" / "20261113").exists()                      # ngày cũ hết file → xoá thư mục
    assert sorted(os.listdir(tmp_path / "p" / "20261116")) == [f"{1000 + i:04d}.json" for i in range(2, 14)]


def test_ma_giu():
    assert V.ma_giu(json.dumps({"danh_muc": ["AAA", "BBB", 3]})) == ["AAA", "BBB"]
    assert V.ma_giu(None) == [] and V.ma_giu("hỏng") == [] and V.ma_giu("{}") == []


class Xuat:
    def __init__(self):
        self.o, self.nen_ds, self.lm = [], [], 0

    def lam_moi(self):
        self.lm += 1
        return 2

    def nhanh(self, ten, du_lieu):
        self.o.append((ten, json.loads(du_lieu)["cap_nhat"]))

    def nen(self, f):
        self.nen_ds.append(f)


class DongHo:
    def __init__(self, bat_dau):
        self.t = T(bat_dau)

    def luc(self):
        return self.t

    def ngu(self, giay):
        self.t += pd.Timedelta(seconds=giay)


def _chup(ra, loi_luc=()):
    def chup(cb, f, luc=None, in_tien_do=None):
        if f"{luc:%H:%M}" in loi_luc:
            raise ValueError("nguồn chập chờn")
        luc += pd.Timedelta(seconds=12)                                     # chụp mất ~12 giây
        with open(f, "w") as fh:
            fh.write("{}")
        return {"cap_nhat": f"{luc:%Y-%m-%d %H:%M:%S}"}
    return chup


def test_vong_buoi_sang(tmp_path):
    """Job 08:50: chờ tới 09:00, chụp mỗi ô 30 giây tới 11:31 (tên file mới mỗi lượt, không trùng / không sót ô), bản nền
    Pages 10' / lần + cuối buổi, 1 lượt lỗi không dừng vòng, thoát khi hết khung 11:36."""
    dh, x, log = DongHo("2026-11-16 08:50:10"), Xuat(), []
    ra = str(tmp_path / "du_lieu.json")

    def chup(cb, f, luc=None, in_tien_do=None):
        dh.t += pd.Timedelta(seconds=12)
        return _chup(ra, loi_luc=("10:15",))(cb, f, luc=luc, in_tien_do=in_tien_do)
    luot, loi = V.vong({}, x, ra, luc_fn=dh.luc, ngu=dh.ngu, chup=chup, in_ra=log.append)
    ten = [t for t, _ in x.o]
    assert ten[0] == "p/20261116/1080.json" and ten[-1] == "p/20261116/1381.json"   # 09:00:01 → 11:30:31
    assert len(ten) == len(set(ten)) == luot == 302 - 2 and loi == 2               # 10:15:00 & 10:15:30 lỗi
    o = [int(t[-9:-5]) for t in ten]
    assert all(b - a in (1, 3) for a, b in zip(o, o[1:]))                          # liền ô (trừ 2 ô lỗi)
    assert 15 <= len(x.nen_ds) <= 17 and dh.t >= T("2026-11-16 11:36")              # 10' / lần + cuối buổi
    assert any("10:15:01" in d and "nguồn chập chờn" in d for d in log)


def test_vong_chot_phien_va_chay_thu(tmp_path):
    dh, x = DongHo("2026-11-16 15:04:40"), Xuat()
    ra = str(tmp_path / "du_lieu.json")
    luot, loi = V.vong({}, x, ra, luc_fn=dh.luc, ngu=dh.ngu, chup=_chup(ra))
    assert (luot, loi) == (2, 0) and [t for t, _ in x.o] == ["p/20261116/1809.json", "p/20261116/1810.json"]  # 15:05:01 chốt
    assert len(x.nen_ds) == 2
    dh, x = DongHo("2026-11-14 20:00:00"), Xuat()                                 # thứ Bảy, chạy thử 3 lượt
    assert V.vong({}, x, ra, luc_fn=dh.luc, ngu=dh.ngu, chup=_chup(ra), so_luot=3) == (3, 0) and len(x.o) == 3
    dh, x = DongHo("2026-11-14 20:00:00"), Xuat()                                 # ngoài khung, không chạy thử → thoát
    assert V.vong({}, x, ra, luc_fn=dh.luc, ngu=dh.ngu, chup=_chup(ra)) == (0, 0) and x.nen_ds == []


def test_git_day_ghi_de_1_commit(tmp_path):
    goc = tmp_path / "goc.git"
    subprocess.run(["git", "init", "-q", "--bare", str(goc)], check=True)
    g = V.Git(str(tmp_path / "lam"), "chu/bang-thi-truong", "tk", url=str(goc))
    d = g.thu_muc("nhanh")
    for i in range(3):
        (tmp_path / "lam" / "nhanh" / "a.json").write_text(json.dumps({"i": i}))
        g.day("nhanh", f"lượt {i}")
    so = subprocess.run(["git", "-C", str(goc), "rev-list", "--count", "nhanh"], capture_output=True, text=True).stdout
    assert so.strip() == "1" and json.loads(g.doc("nhanh", "a.json")) == {"i": 2} and os.path.isdir(d)
    assert g.doc("nhanh", "khong.json") is None and g.doc("khong-co", "a.json") is None


def test_workflow_bang_rieng():
    """Workflow vòng ở repo bang-thi-truong: checkout canh-bao-mua (công khai, không token), quyền tối thiểu, không đụng repo
    kín; đồng hồ gọi sáng / chiều; canh-bao-mua đồng bộ mọi bang_rieng/*.yml sang repo đó."""
    d = yaml.safe_load(open("bang_rieng/bang.yml", encoding="utf-8"))
    assert d["permissions"] == {"contents": "write", "actions": "write"}
    t = json.dumps(d, ensure_ascii=False)
    assert "DANH_MUC" not in t and "danh-muc" not in t and "secrets." not in t
    job = d["jobs"]["vong"]
    co = job["steps"][0]
    assert "checkout" in co["uses"] and co["with"]["persist-credentials"] is False and "token" not in co["with"]
    assert "thi_truong.vong_bang" in t and job["timeout-minutes"] <= 360
    tren = d.get("on") or d.get(True)
    assert tren["push"]["paths"] == [".github/workflows/bang.yml"] and "push' && '3'" in t    # đồng bộ xong → chạy thử 3 lượt
    import sys
    sys.path.insert(0, "cong_cu")
    import dong_ho
    assert [x[1] for x in dong_ho.LICH if x[0] == "bang-thi-truong/bang.yml"] == ["50 8 * * 1-5", "50 12 * * 1-5"]
    b = yaml.safe_load(open(".github/workflows/bang_thi_truong.yml", encoding="utf-8"))
    tb = json.dumps(b, ensure_ascii=False)
    assert "bang_rieng/*.yml" in tb and "chuan-bi" in tb and "du-lieu-nhanh" not in tb and "nhanh" not in b["jobs"]
