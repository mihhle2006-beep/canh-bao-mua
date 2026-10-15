# -*- coding: utf-8 -*-
"""Quét định kỳ cho canh-bao-mua: gộp mã MUA của nhiều chiến lược → ma_mua_bo_loc.json (không mạng)."""
import json

import pandas as pd

from bo_loc import quet_dinh_ky as q


def _kq(cl, hanh_dong):
    e = pd.DataFrame({"Mã": list(hanh_dong), "Hành động": list(hanh_dong.values())})
    return {"danh_gia": e, "bang": e, "thu_muc": f"/tmp/ket_qua_loc_{cl}_20261005"}


def test_gop_ma_mua_va_bo_qua_chien_luoc_loi(tmp_path):
    kq = {"quy_b": _kq("quy_b", {"FPT": "MUA", "HPG": "THEO DÕI", "mwg": "MUA"}),
          "xu_huong": _kq("xu_huong", {"FPT": "MUA", "VNM": "MUA THĂM DÒ (½ vị thế)"})}

    def chay(argv):
        cl = argv[argv.index("--chien_luoc") + 1]
        if cl == "loi":
            raise SystemExit("không tải được giá")
        return kq[cl]

    gop, loi, phien = q.quet(["quy_b", "xu_huong", "loi"], chay=chay)
    assert gop == {"FPT": ["quy_b", "xu_huong"], "MWG": ["quy_b"], "VNM": ["xu_huong ½"]}   # VNM: mua thăm dò top 2
    assert list(loi) == ["loi"] and phien == "2026-10-05"
    path = tmp_path / "ma.json"
    q.ghi(gop, loi, phien, str(path), bay_gio="2026-10-05 15:10", ds_cl=["quy_b", "xu_huong"])
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["ngay_quet"] == "2026-10-05" and d["ma"]["FPT"] == ["quy_b", "xu_huong"]


def test_khong_co_danh_gia():
    assert q.ma_mua(None) == [] and q.ma_mua({"danh_gia": None}) == []


def test_main_chay_that_offline(thu_muc_du_lieu, monkeypatch):
    """Chạy bộ lọc thật (CSV giả lập) với quy_b + xu_huong → ghi được file JSON đúng khuôn."""
    from tests.bo_loc.test_dau_cuoi import _tham_so
    monkeypatch.chdir(thu_muc_du_lieu)
    them = [x for x in _tham_so(thu_muc_du_lieu) if x not in ("--chien_luoc", "ky_thuat")]
    assert q.main(["--file", "ma.json", *them]) == 0
    d = json.loads((thu_muc_du_lieu / "ma.json").read_text(encoding="utf-8"))
    assert d["chien_luoc"] == ["quy_b", "xu_huong"] and d["phien"] and d["loi"] == {}
    assert all(set(v) <= {"quy_b", "xu_huong", "quy_b ½", "xu_huong ½"} for v in d["ma"].values())


def test_lay_them_2_ma_dau_mua_tham_do():
    e = pd.DataFrame({"Mã": ["AAA", "BBB", "CCC", "DDD", "EEE"],
                      "Hành động": ["MUA", q.THAM_DO, q.THAM_DO, q.THAM_DO, "THEO DÕI"]})
    assert q.ma_mua({"danh_gia": e}) == ["AAA", "BBB", "CCC"]
    assert q.ma_mua({"danh_gia": e}, so_tham_do=0) == ["AAA"]
    assert q.ma_mua_nhom({"danh_gia": e}) == {"AAA": "MUA", "BBB": "½", "CCC": "½"}


def test_ban_cong_khai_khong_doc_ptdttc(tmp_path, monkeypatch):
    """Bản trong repo công khai: không đọc / ghi file PTĐTTC (chỉ repo Bo_Loc riêng tư làm việc đó)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "danh_muc_ptdttc.csv").write_text("ma\nMWG\n", encoding="utf-8")
    goi = []

    def chay(argv):
        goi.append(argv)
        return _kq("quy_b", {"FPT": "MUA", "MWG": "THEO DÕI"})
    gop, loi, _ = q.quet(["quy_b"], chay=chay)
    assert gop == {"FPT": ["quy_b"]} and not loi and len(goi) == 1 and "--ma" not in goi[0]
    assert not hasattr(q, "ma_ptdttc") and not (tmp_path / "ptdttc_bo_loc.json").exists()
