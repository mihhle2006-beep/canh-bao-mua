# -*- coding: utf-8 -*-
"""Chạy trọn main() không hỏi trên dữ liệu giả lập: không lỗi, kết luận nhất quán, xuất đủ file."""
import os

import pytest

from ptcp import main, quet_nhieu_ma, cau_hinh as cfg
from ptcp.in_an import BAO_CAO_TEXT


@pytest.fixture(scope="module")
def ket_qua(thu_muc_csv, tmp_path_factory):
    os.chdir(tmp_path_factory.mktemp("chay"))
    out = {}
    for ten in ("tang", "giam"):
        out[ten] = main(tuong_tac=False, im_lang=True, xuat_file=(ten == "tang"), symbol="TEST", san="HOSE",
                        csv_ngay=str(thu_muc_csv / f"{ten}.csv"), csv_vni=str(thu_muc_csv / "vni.csv"),
                        nhom="-", von_trieu=500, rui_ro_pct=1.5)
        out[ten + "_text"] = "".join(BAO_CAO_TEXT)
    return out


@pytest.mark.parametrize("ten", ["tang", "giam"])
def test_mot_khuyen_nghi_duy_nhat_xuyen_suot(ket_qua, ten):
    k, txt = ket_qua[ten], ket_qua[ten + "_text"]
    kn = k["qd"]["khuyen_nghi"]
    assert f"KHUYẾN NGHỊ: {kn}" in txt
    assert f"Khuyến nghị (hành động)     : {kn}" in txt
    assert k["tom_tat"]["dong"][0].startswith(f"1. KHUYẾN NGHỊ: {kn}")


@pytest.mark.parametrize("ten", ["tang", "giam"])
def test_mua_phai_thoa_moi_dieu_kien(ket_qua, ten):
    k = ket_qua[ten]
    if k["qd"]["mua"]:
        assert k["tg"]["tuan_ok"] and k["kb"]["ev_qd"] >= cfg.EV_NGUONG and k["qr"]["rr"] >= cfg.RR_NGUONG


@pytest.mark.parametrize("ten", ["tang", "giam"])
def test_kich_ban_hop_ly(ket_qua, ten):
    kb = ket_qua[ten]["kb"]
    assert kb["mt_tc"] > kb["kc"]                 # mục tiêu tích cực > mốc breakout
    assert kb["gia_tc"] < kb["cat_lo"]            # giá đích tiêu cực < cắt lỗ
    assert kb["cat_lo"] == ket_qua[ten]["stop"]["gia"] == ket_qua[ten]["qr"]["lo_ap_dung"]   # 1 mức cắt lỗ


def test_xu_huong_giam_khong_mua(ket_qua):
    assert not ket_qua["giam"]["qd"]["mua"]


def test_xuat_du_file(ket_qua):
    th = ket_qua["tang"]["thu_muc"]
    for duoi in ("_bao_cao.html", "_bao_cao.txt", "_phan_tich_tong_hop.xlsx", "_ngay.png"):
        assert os.path.exists(os.path.join(th, "TEST" + duoi))


def test_tham_so_sai_bao_loi():
    with pytest.raises(ValueError, match="Tham số không hợp lệ"):
        main(tuong_tac=False, symbool="X")


def test_quet_nhieu_ma_khong_vo_khi_loi_du_lieu(tmp_path):
    os.chdir(tmp_path)
    b = quet_nhieu_ma(["KHONGCO"], nhom="-")
    assert len(b) == 1 and "lỗi" in str(b["Điều kiện chưa đạt"].iloc[0])


def test_chay_co_ke_hoach_tu_gia_mua(thu_muc_csv, tmp_path):
    os.chdir(tmp_path)
    k = main(tuong_tac=False, im_lang=True, xuat_file=False, symbol="TEST", san="HOSE",
             csv_ngay=str(thu_muc_csv / "tang.csv"), csv_vni=str(thu_muc_csv / "vni.csv"), nhom="-",
             so_cp=100, gia_von=20.0, ngay_mua="02/01/2025")
    kh = k["kh"]
    assert kh and kh["ngay_mua"] == __import__("pandas").Timestamp("2025-01-02")
    assert "vni_pct" in kh["so_vni"]
    assert "KẾ HOẠCH VỊ THẾ TỪ GIÁ MUA" in "".join(BAO_CAO_TEXT)


@pytest.mark.parametrize("ten", ["tang", "giam"])
def test_phan_I_co_ket_luan(ket_qua, ten):
    txt = ket_qua[ten + "_text"]
    assert "KẾT LUẬN BACKTEST" in txt and "chưa đủ kết luận" not in txt
    assert "bt_vm" in ket_qua[ten] and "ket_luan_bt" in ket_qua[ten]
