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


def test_ma_ptdttc(tmp_path):
    f = tmp_path / "ptdttc.csv"
    f.write_text("﻿ma,so_cp,gia_von\nMWG,100,70\ndhc,50,30\nMWG,10,72\n", encoding="utf-8")
    assert q.ma_ptdttc(str(f)) == ["MWG", "DHC"]
    assert q.ma_ptdttc(str(tmp_path / "khong_co.csv")) == []


def test_ptdttc_luon_bao_cao_va_khong_vao_ds_mua():
    goi = []
    full = {"quy_b": _kq("quy_b", {"FPT": "MUA", "MWG": "THEO DÕI"})}

    def chay(argv):
        goi.append(argv)
        cl = argv[argv.index("--chien_luoc") + 1]
        if "--ma" in argv:                                   # quét thêm riêng mã PTĐTTC ngoài rổ, thư mục tạm
            assert argv[argv.index("--ma") + 1] == "DHC" and "--thu_muc_ket_qua" in argv
            return _kq(cl, {"DHC": "KHÔNG MUA"})
        return full[cl]

    gop, loi, _ = q.quet(["quy_b"], chay=chay, ptdttc=["MWG", "DHC"])
    assert gop == {"FPT": ["quy_b"]} and not loi                           # MWG / DHC không vào danh sách MUA
    assert q.quet.ptdttc_kq["MWG"]["quy_b"]["hanh_dong"] == "THEO DÕI"
    assert q.quet.ptdttc_kq["DHC"]["quy_b"]["hanh_dong"] == "KHÔNG MUA" and len(goi) == 2


def test_chi_ptdttc_quet_dung_ma_va_khong_ghi_file_mua(tmp_path, monkeypatch):
    """Workflow kín ptdttc.yml: --chi_ptdttc chỉ quét mã PTĐTTC (--ma), không ghi ma_mua_bo_loc.json."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "danh_muc_ptdttc.csv").write_text("ma\nMWG\nDHC\n", encoding="utf-8")
    goi = []

    def chay(argv):
        goi.append(argv)
        return _kq(argv[argv.index("--chien_luoc") + 1], {"MWG": "MUA", "DHC": "THEO DÕI"})
    import bo_loc.cli as cli
    monkeypatch.setattr(cli, "chay", chay)
    assert q.main(["--chi_ptdttc", "--chien_luoc", "quy_b"]) == 0
    assert len(goi) == 1 and goi[0][goi[0].index("--ma") + 1] == "MWG,DHC"
    assert not (tmp_path / q.FILE_KET_QUA).exists()
    d = json.loads((tmp_path / "ptdttc_bo_loc.json").read_text(encoding="utf-8"))
    assert d["ma"]["MWG"]["quy_b"]["hanh_dong"] == "MUA"
    (tmp_path / "danh_muc_ptdttc.csv").unlink()
    assert q.main(["--chi_ptdttc"]) == 0                                    # không có mã → bỏ qua, không lỗi


def test_gui_chi_ptdttc(tmp_path, monkeypatch):
    import bo_loc.gui_html as G
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ptdttc_bo_loc.json").write_text('{"ma": {"MWG": {"quy_b": {"hanh_dong": "MUA"}}}}', encoding="utf-8")
    tin = []
    monkeypatch.setattr(G, "gui_tin", lambda t: tin.append(t) or True)
    monkeypatch.setattr(G, "gui_file", lambda *a: (_ for _ in ()).throw(AssertionError("không gửi file")))
    assert G.main(["--chi_ptdttc"]) == 0 and len(tin) == 1 and "MWG\n   Quỹ Bứt Phá: MUA" in tin[0]


def test_quet_thuong_khong_doc_ma_ptdttc(tmp_path, monkeypatch):
    """Repo CÔNG KHAI: quét toàn sàn (không --chi_ptdttc) KHÔNG đọc danh_muc_ptdttc.csv, không ghi ptdttc_bo_loc.json."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "danh_muc_ptdttc.csv").write_text("ma\nMWG\n", encoding="utf-8")
    goi = []

    def chay(argv):
        goi.append(argv)
        return _kq(argv[argv.index("--chien_luoc") + 1], {"FPT": "MUA", "MWG": "MUA"})
    import bo_loc.cli as cli
    monkeypatch.setattr(cli, "chay", chay)
    monkeypatch.setattr(q, "ma_ptdttc", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được đọc")))
    assert q.main(["--chien_luoc", "quy_b"]) == 0
    assert len(goi) == 1 and "--ma" not in goi[0] and not (tmp_path / "ptdttc_bo_loc.json").exists()
