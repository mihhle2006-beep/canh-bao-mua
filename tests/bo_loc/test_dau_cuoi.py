# -*- coding: utf-8 -*-
"""Chạy TOÀN BỘ bộ lọc offline (CSV giả lập) với mọi chiến lược → kiểm tra Excel & cột đầu ra."""
import os

import pandas as pd
import pytest

from bo_loc import cau_hinh as ch
from bo_loc.cli import chay
from tests.bo_loc.test_chien_luoc_loc import CHIEN_LUOC_GOC


def _tham_so(d, chien_luoc="ky_thuat", them=()):
    return ["--ma", "AAA,BBB,CCC,DDD,EEE", "--thu_muc_csv", str(d / "gia"), "--vnindex", str(d / "vnindex.csv"),
            "--co_ban", str(d / "co_ban.csv"), "--khong_online_co_ban", "--khong_cache",
            "--thu_muc_ket_qua", str(d), "--chien_luoc", chien_luoc, "--gtgd_min", "0", "--klgd_min", "0", *them]


def test_chay_day_du_xuat_excel(thu_muc_du_lieu, monkeypatch):
    monkeypatch.chdir(thu_muc_du_lieu)
    kq = chay(_tham_so(thu_muc_du_lieu))
    assert os.path.exists(kq["file_excel"])
    with pd.ExcelFile(kq["file_excel"]) as x:
        sheets = x.sheet_names
    assert sheets[0] == "Ket luan"
    assert kq["ket_luan"]["Kết luận"].isin(["[NÊN MUA]", "[MUA CÓ ĐIỀU KIỆN]", "[THEO DÕI]", "[LOẠI]"]).all()
    for s in ("Dat loc", "Tat ca", "Tieu chi", "Danh gia sau loc", "Nguon du lieu"):
        assert s in sheets
    b = kq["bang"]
    assert set(b["Mã"]) == {"AAA", "BBB", "CCC", "DDD", "EEE"}
    a = b.set_index("Mã").loc["AAA"]
    assert a["pe"] == pytest.approx(a["gia"] * 1000 / 5000)      # P/E theo giá hiện tại / EPS 4 quý
    assert a["nguon_gia"] == "CSV" and "file" in a["nguon_co_ban"]
    assert os.path.exists(os.path.join(kq["thu_muc"], "tong_quan_loc.png"))
    assert os.path.exists(ch.FILE_LICH_SU)
    assert os.path.basename(kq["file_chien_luoc"]) == "chien_luoc_ky_thuat.xlsx"
    with pd.ExcelFile(kq["file_chien_luoc"]) as x:
        assert x.sheet_names[0] == "TỔNG QUAN CHUNG" and {"TỔNG QUAN", "KỸ THUẬT", "BIẾN ĐỘNG"} <= set(x.sheet_names)
    assert set(kq["bang_ket_qua"]["BIẾN ĐỘNG"]["MÃ"]) <= {"AAA", "BBB", "CCC", "DDD", "EEE"}


@pytest.mark.parametrize("ten", CHIEN_LUOC_GOC)
def test_moi_chien_luoc_deu_chay(thu_muc_du_lieu, monkeypatch, ten):
    monkeypatch.chdir(thu_muc_du_lieu)
    kq = chay(_tham_so(thu_muc_du_lieu, ten, ["--khong_bieu_do"]))
    assert len(kq["bang"]) == 5 and kq["danh_gia"] is not None


def test_lan_chay_thu_hai_bao_thay_doi(thu_muc_du_lieu, monkeypatch, capsys):
    monkeypatch.chdir(thu_muc_du_lieu)
    pd.DataFrame({"ngay": ["2000-01-03"], "chien_luoc": ["ky_thuat"], "ma": ["ZZZ"], "diem": ["50"],
                  "trang_thai": ["✔"]}).to_csv(ch.FILE_LICH_SU, index=False)
    chay(_tham_so(thu_muc_du_lieu, them=["--khong_bieu_do", "--khong_danh_gia"]))
    out = capsys.readouterr().out
    assert "phiên 2000-01-03" in out and "rời khỏi: ZZZ" in out


def test_tao_mau_co_ban(thu_muc_du_lieu, monkeypatch):
    monkeypatch.chdir(thu_muc_du_lieu)
    assert chay(["--ma", "GMD,VSC", "--tao_mau_co_ban"]) is None
    assert pd.read_csv("co_ban_mau.csv")["ma"].tolist() == ["GMD", "VSC"]


def test_chay_voi_them_bo(thu_muc_du_lieu, monkeypatch):
    monkeypatch.chdir(thu_muc_du_lieu)
    kq = chay(_tham_so(thu_muc_du_lieu, "xu_huong", ["--khong_bieu_do", "--them", "beta_min=0.1", "--bo", "rs_3t"]))
    cot = [c for c in kq["bang"].columns if c.startswith("Beta ≥")]
    assert cot and not any(c.startswith("Mạnh hơn VNINDEX") for c in kq["bang"].columns)


def test_chay_co_phan_tich_tai_chinh_10_tieu_chi(thu_muc_du_lieu, monkeypatch):
    from bo_loc import cli
    from tests.bo_loc.test_danh_gia_tai_chinh import bc
    monkeypatch.chdir(thu_muc_du_lieu)
    monkeypatch.setattr(cli, "_cai_tuy_chon", lambda: None)
    monkeypatch.setattr(cli.nguon_cb, "lay_online", lambda *a, **k: {})
    monkeypatch.setattr(cli.nguon_bctc, "lay_bctc_nam", lambda ma, *a, **k: dict(bc(), nguon="Yahoo"))
    ts = [x for x in _tham_so(thu_muc_du_lieu, "gia_tri", ["--khong_bieu_do"]) if x != "--khong_online_co_ban"]
    kq = chay(ts)
    fa_bang = kq["bang_ket_qua"]["PHÂN TÍCH TÀI CHÍNH"]
    assert not fa_bang.empty and fa_bang.iloc[8, 1] == "Rất tốt"                   # ROE
    assert (kq["bang"]["fa_nguy_hiem"] == 0).all() and kq["bang"]["fa_diem"].gt(75).all()
    with pd.ExcelFile(kq["file_chien_luoc"]) as x:
        assert "PHÂN TÍCH TÀI CHÍNH" in x.sheet_names
