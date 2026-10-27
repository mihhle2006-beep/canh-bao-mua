# -*- coding: utf-8 -*-
"""Kiểm thử chiến lược (hợp lệ, nạp JSON riêng) và bước lọc B1."""
import json

import numpy as np
import pytest

from bo_loc import chien_luoc as clm
from bo_loc.loc import bang_ket_qua, danh_gia, gan_dat, nhan_dat
from bo_loc.tieu_chi import TIEU_CHI, kiem_tra, ten_tieu_chi

CHIEN_LUOC_GOC = ["quy_b", "xu_huong", "tuy_chinh"]          # 27/10/2026 bỏ chiến lược backtest không hiệu quả


def test_du_chien_luoc_va_deu_hop_le():
    ds = clm.tai_tat_ca(thu_muc_rieng=None)
    assert set(ds) == set(CHIEN_LUOC_GOC)                                 # đã gộp, bỏ bản *_goc
    for ten, cl in ds.items():
        for _, k, t in clm.cac_tieu_chi(cl):
            assert k in TIEU_CHI, f"{ten}: {k}"
            ten_tieu_chi(k, t)                        # định dạng tên không lỗi


def test_chien_luoc_json_rieng(tmp_path):
    d = tmp_path / "chien_luoc_rieng"
    d.mkdir()
    (d / "cang_re.json").write_text(json.dumps({"mo_ta": "Cảng giá rẻ", "bat_buoc": {"pe_max": 12},
                                                "cong_diem": {"rsi_trong": [40, 60]}}), encoding="utf-8")
    cl = clm.lay("cang_re", thu_muc_rieng=str(d))
    assert cl["bat_buoc"] == {"pe_max": 12}
    assert ten_tieu_chi("rsi_trong", [40, 60]) == "RSI trong 40–60"


def test_khoa_sai_bao_loi(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    (d / "hong.json").write_text(json.dumps({"bat_buoc": {"khong_ton_tai": 1}}), encoding="utf-8")
    with pytest.raises(ValueError, match="khong_ton_tai"):
        clm.tai_tat_ca(thu_muc_rieng=str(d))


def test_ap_nguong_khong_lam_hong_ban_goc():
    cl = clm.lay("xu_huong", thu_muc_rieng=None)
    c2 = clm.ap_nguong(cl, {"gtgd_min": 1, "khong_co": 9})
    assert c2["bat_buoc"]["gtgd_min"] == 1 and cl["bat_buoc"]["gtgd_min"] == 10
    assert "khong_co" not in c2["bat_buoc"]


def _m(**k):
    m = {"gia": 80, "ma50": 70, "ma200": 60, "rsi": 60, "pe": 12, "roe": 15, "upside": 18, "rr": 2.5, "gtgd20": 20}
    m.update(k)
    return m


def test_kiem_tra_thieu_du_lieu_tra_none():
    assert kiem_tra("pe_max", _m(pe=np.nan), 15) is None
    assert kiem_tra("pe_max", _m(pe=-5), 15) is False          # P/E âm không đạt
    assert kiem_tra("khong_co_cot", {}, None) is None


def test_danh_gia_dat_khong_dat_va_thieu_du_lieu():
    cl = {"bat_buoc": {"tren_ma50": None, "pe_max": 15}, "cong_diem": {"rr_min": 2}}
    kq, diem, toi_da, dat, thieu, thieu_dl = danh_gia(_m(), cl, nghiem_ngat=False)
    assert dat and diem == toi_da == 5
    _, _, _, dat, thieu, _ = danh_gia(_m(gia=60), cl, nghiem_ngat=False)
    assert not dat and thieu == ["Giá > MA50"]
    _, _, _, dat, _, thieu_dl = danh_gia(_m(pe=np.nan), cl, nghiem_ngat=False)
    assert dat and thieu_dl == ["P/E ≤ 15"]
    assert nhan_dat(dat, thieu_dl, 2) == "◐"
    _, _, _, dat, _, _ = danh_gia(_m(pe=np.nan), cl, nghiem_ngat=True)
    assert not dat


def test_toi_thieu_can_dat_n_tieu_chi():
    cl = {"bat_buoc": {}, "cong_diem": {},
          "toi_thieu": {"can_dat": 2, "tieu_chi": {"pe_max": 15, "roe_min": 12, "rsi_duoi": 30}}}
    kq, *_ , dat, thieu, _ = danh_gia(_m(), cl, nghiem_ngat=False)
    assert dat and kq["Cơ bản đạt (cần 2/3)"] == "2/3"
    *_, dat, thieu, _ = danh_gia(_m(roe=5), cl, nghiem_ngat=False)
    assert not dat and "1/2" in thieu[0]


def test_bang_ket_qua_xep_hang_va_gan_dat():
    cl = {"bat_buoc": {"tren_ma50": None, "pe_max": 15}, "cong_diem": {"rr_min": 2}}
    ms = [dict(_m(), **{"Mã": "A"}), dict(_m(gia=60), **{"Mã": "B"}), dict(_m(pe=np.nan), **{"Mã": "C"})]
    b = bang_ket_qua(ms, [danh_gia(m, cl, nghiem_ngat=False) for m in ms], max_thieu=2)
    assert list(b["Mã"]) == ["A", "C", "B"]
    assert list(b["Đạt lọc"]) == ["✔", "◐", ""]
    assert list(gan_dat(b)["Mã"]) == ["B"]


def test_ds_hose_tu_chuyen_nguon(tmp_path, monkeypatch):
    from bo_loc import cau_hinh as ch
    from bo_loc import danh_sach_ma as dsm
    monkeypatch.setattr(ch, "FILE_DS_HOSE", str(tmp_path / "ds.txt"))
    ma = [a + b + c for a in "ABC" for b in "DEFGH" for c in "IJKLMNOP"]          # 120 mã giả
    monkeypatch.setattr(dsm, "NGUON_DS_HOSE", [("A", lambda: (_ for _ in ()).throw(ValueError("HTTP 403"))),
                                               ("B", lambda: ma + ["E1VFVN30", "VN30F1M"])])
    ds, nguon = dsm.lay_danh_sach_hose()
    assert nguon == "online B" and len(ds) == 120 and (tmp_path / "ds.txt").exists()


def test_ds_hose_bao_loi_ro_nguon(tmp_path, monkeypatch):
    from bo_loc import cau_hinh as ch
    from bo_loc import danh_sach_ma as dsm
    monkeypatch.setattr(ch, "FILE_DS_HOSE", str(tmp_path / "khong_co.txt"))
    monkeypatch.setattr(dsm, "NGUON_DS_HOSE", [("A", lambda: (_ for _ in ()).throw(ValueError("HTTP 403")))])
    with pytest.raises(ValueError, match="A: HTTP 403"):
        dsm.lay_danh_sach_hose()


def test_ten_cu_tu_chuyen_sang_chien_luoc_moi():
    cl = clm.lay("rui_ro_cao_xu_huong", thu_muc_rieng=None)
    assert cl["bat_buoc"]["beta_min"] == 1.2 and "tren_ma50" in cl["bat_buoc"]
    for cu in ("bat_day", "gia_tri", "ky_thuat", "sieu_cp", "tieu_chuan"):                 # đã bỏ → xu_huong
        assert clm.lay(cu, thu_muc_rieng=None)["ten"] == "Xu hướng"


def test_them_bo_tieu_chi_luc_chay():
    cl = clm.lay("xu_huong", thu_muc_rieng=None)
    c2 = clm.them_bot(cl, "von_hoa_min=300,gtgd_min=2,rsi_trong=30:60,pe_max=", "tren_ma50")
    assert c2["bat_buoc"]["von_hoa_min"] == 300 and c2["bat_buoc"]["rsi_trong"] == (30, 60)
    assert c2["bat_buoc"]["pe_max"] is None and "pe_max" not in c2["cong_diem"]                    # chuyển sang bắt buộc
    assert "tren_ma50" not in c2["bat_buoc"] and "von_hoa_min" not in cl["bat_buoc"]               # bản gốc không đổi
    with pytest.raises(SystemExit, match="khong_co"):
        clm.them_bot(cl, "khong_co=1")
    with pytest.raises(SystemExit, match="rsi_duoi"):
        clm.them_bot(cl, None, "rsi_duoi")


def test_sieu_cp_tieu_chi_moi():
    m = {"von_hoa": 5_000, "gtgd_tang": 1.5, "bien_dong_co": 0.7}
    assert TIEU_CHI["von_hoa_max"][1](m, 10_000) and TIEU_CHI["gtgd_tang_min"][1](m, 1.3)
    assert TIEU_CHI["bien_dong_co_max"][1](m, 0.8) and TIEU_CHI["von_hoa_max"][1]({}, 1) is None
