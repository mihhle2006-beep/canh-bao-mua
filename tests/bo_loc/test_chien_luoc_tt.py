# -*- coding: utf-8 -*-
"""Chiến lược theo thị trường trong bộ lọc – cùng logic bot canh-bao-mua / ptcp (không mạng)."""
import numpy as np
import pandas as pd
import pytest

from bo_loc import chien_luoc_tt as T
from bo_loc.danh_gia_sau_loc import ke_hoach_giao_dich, xep_loai_theo_chien_luoc
from bo_loc.loi.chien_luoc import vung_gia
from bo_loc.loi.he_thoat import stop_chuan
from tests.bo_loc.conftest import tao_gia


@pytest.fixture
def ro():
    gia = {f"M{i}": tao_gia(n=900, xu_huong=0.001 * (i % 3), seed=20 + i) for i in range(5)}
    vni = tao_gia(n=900, gia_dau=1200, xu_huong=0.0004, bien_dong=0.01, seed=99)
    return gia, vni


def test_thi_truong_8_chi_bao_uoc_tinh_do_rong(ro, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gia, vni = ro
    tt = T.thi_truong(vni, gia)
    assert tt["so_chi_bao"] == 8 and "ước tính" in tt["nguon"] and tt["cl"] in (1, 2)
    c = vni.close
    bien = (c.iloc[-60:].max() / c.iloc[-60:].min() - 1) * 100
    assert tt["bien"] == pytest.approx(bien) and tt["di_ngang"] == (bien < tt["nguong_bien"])
    assert "Thị trường:" in T.dong_thi_truong(tt) and T.dong_thi_truong(None).startswith("Thị trường: không có")


def test_nhom_vung_cat_lo_dung_nhu_bot(ro, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gia, vni = ro
    tt, kq = T.danh_gia(gia, vni)
    assert set(kq) == set(gia)
    for ma, k in kq.items():
        assert k["nhom"] in T.TEN_NHOM
        if k["nhom"] in T.NHOM_MUA + ("CHO",):
            if k["nhom"] == "MUA_MOI":
                assert (k["tu"], k["den"]) == vung_gia(k["nhom"], k["gia"], k["cl"])
            elif k["tu"] != k["tu"]:                       # Quỹ B: cắt lỗ đã > giá vào + ½R → không vùng vào trễ
                assert k["nhom"] == "CHO"
                continue
            assert k["cl"] < k["tu"] <= k["den"]
            assert k["den"] <= vung_gia(k["nhom"], k["gia"], k["cl"])[1]     # ≤ vùng không giới hạn ½R
            assert k["mt1"] == pytest.approx(2 * k["gia"] - k["cl"]) and k["mt3"] == pytest.approx(4 * k["gia"] - 3 * k["cl"])
        if k["nhom"] == "MUA_MOI":
            atr = __import__("bo_loc.loi.chi_bao", fromlist=["x"]).tinh_chi_bao(gia[ma]).ATR.iloc[-1]
            assert k["cl"] == pytest.approx(stop_chuan(k["gia"], atr))


def test_ke_hoach_va_hanh_dong_theo_chien_luoc():
    m = {"gia": 20.0, "atr": 0.5, "klgd20": 1e6,
         "cl_tt": {"nhom": "VAO_NUA", "ten_nhom": "🟡", "cl": 18.8, "tu": 19.4, "den": 20.6, "ly_do": "x", "vo_hieu": "y"}}
    kh = ke_hoach_giao_dich(m, 1000, 1.0)
    assert kh["cat_lo_kh"] == 18.8 and kh["muc_tieu_kh"] == pytest.approx(21.2) and kh["muc_tieu_3r"] == pytest.approx(23.6)
    assert kh["vung_mua"] == "19.40 – 20.60" and kh["nhom_cl"] == "VAO_NUA" and kh["rr_kh"] != kh["rr_kh"]
    assert kh["so_cp_kh"] == 7500                       # 1% × 1 tỷ ÷ 1,2 nghìn = 8.333 > trần 15% × 1 tỷ ÷ 20 nghìn = 7.500
    kh2 = ke_hoach_giao_dich({"gia": 20.0, "atr": 0.5, "klgd20": 1e6, "cl_tt": {"nhom": "CHO_TIN_HIEU", "cl": np.nan}},
                             1000, 1.0)
    assert kh2["cat_lo_kh"] == pytest.approx(stop_chuan(20.0, 0.5)) and kh2["vung_mua"] == "–"
    assert xep_loai_theo_chien_luoc("MUA_MOI", True, False, []) == "MUA"
    assert xep_loai_theo_chien_luoc("VAO_NUA", True, False, []) == "MUA THĂM DÒ (½ vị thế)"
    assert xep_loai_theo_chien_luoc("CHO", True, False, []) == "CHỜ NHỊP CHỈNH"
    assert xep_loai_theo_chien_luoc("MUA_MOI", True, False, ["cờ đỏ"]) == "THEO DÕI – có cờ đỏ"
    assert xep_loai_theo_chien_luoc("MUA_MOI", False, True, []) == "THEO DÕI"
    assert xep_loai_theo_chien_luoc("DUOI_VON", True, False, []) == "THEO DÕI"
    assert xep_loai_theo_chien_luoc("MUA_MOI", False, False, []) == "LOẠI"


def test_dau_cuoi_mac_dinh_la_chien_luoc_quy_b(thu_muc_du_lieu, monkeypatch, capsys):
    from bo_loc import cau_hinh as ch
    from bo_loc.cli import chay
    monkeypatch.chdir(thu_muc_du_lieu)
    for ten in ("THU_TU_NGUON_GIA", "THU_TU_NGUON_CO_BAN"):            # --khong_vnstock sửa danh sách nguồn → trả lại
        monkeypatch.setattr(ch, ten, list(getattr(ch, ten)))
    kq = chay(["--thu_muc_csv", "gia", "--vnindex", "vnindex.csv", "--ma", "AAA,BBB,CCC,DDD,EEE",
               "--khong_online_co_ban", "--khong_vnstock", "--khong_bieu_do", "--khong_cache"])
    out = capsys.readouterr().out
    assert "CHIẾN LƯỢC QUỸ B" in out and "Thị trường:" in out and kq["thi_truong"]["so_chi_bao"] == 8
    k = kq["ket_luan"]
    assert {"Nhóm chiến lược", "Đạt điểm mua", "Vô hiệu khi", "MT 3R"} <= set(k.columns)
    mua = k[k["Kết luận"] == "[NÊN MUA]"]
    assert mua["Nhóm chiến lược"].str.contains("MUA MỚI|NHƯ LỆNH MỚI").all()


def test_loc_quy_b_ngoai_top(ro, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gia, vni = ro
    monkeypatch.setattr(T, "_loc_quy", lambda ma, v: {"bo": ma == "M0", "he_so": 0.5, "ly_do": ["ĐẮT ×0.5"]})
    _, kq = T.danh_gia(gia, vni)
    mua = [k for m, k in kq.items() if m != "M0" and k["nhom"] in T.NHOM_MUA]
    assert kq["M0"]["nhom"] in ("NGOAI_TOP", "CHO_TIN_HIEU", "CHO", "DUOI_VON", "BAN")
    assert all(k["he_so_quy"] == 0.5 and "ĐẮT" in str(k["khoi_luong"]) for k in mua)


def test_tham_so_dong_bo_quy_b():
    """Khối lượng gợi ý của bộ lọc dùng đúng luật Quỹ B của ptcp."""
    import pytest
    P = pytest.importorskip("ptcp.cau_hinh")
    from bo_loc import cau_hinh as ch
    assert ch.RUI_RO_MOI_LENH == P.QUY_RUI_RO_LENH_PCT and ch.TY_TRONG_MAX == P.QUY_TRAN_MA_PCT
    assert ch.GTGD_MIN == P.QUY_GTGD_TOI_THIEU
