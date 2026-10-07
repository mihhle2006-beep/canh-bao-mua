# -*- coding: utf-8 -*-
"""Tổng kết gọn theo chiến lược + danh mục + Excel; điểm vào 15' đồng bộ chiến lược; mua thêm (không mạng)."""
import json
import os
import sys
from unittest import mock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytest.importorskip("ptcp.diem_vao_15p", reason="ptcp trong danh-muc chưa cập nhật (thiếu diem_vao_15p.py)")
import chay  # noqa: E402
from canh_bao import cau_hinh as C  # noqa: E402
from canh_bao import diem_vao, tong_ket_cl, vi_the  # noqa: E402

DS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
GIO = ["09:00", "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15",
       "13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30"]


def _gia(r, g0=30.0, end="2026-10-02", seed=0):
    r = np.asarray(r, float)
    c = g0 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]]
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + rng.uniform(0, .004, len(c))),
                         "low": np.minimum(o, c) * (1 - rng.uniform(0, .004, len(c))), "close": c,
                         "volume": 1e6}, index=pd.bdate_range(end=end, periods=len(c)))


def _gia_dai(ma, chi_so=False):
    seed = 7 if chi_so else sum(map(ord, ma))
    rng = np.random.default_rng(seed)
    return _gia((0.0003 if chi_so else 0.0005) + 0.018 * rng.standard_normal(1500), g0=20 + seed % 30, seed=seed)


def _tai(ma, khung="D", tu=None, chi_so=False, **k):
    return _gia_dai(ma, chi_so or ma == "VNINDEX")


@pytest.fixture
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(C, "MA_CHIEN_LUOC", DS)
    monkeypatch.setattr(C, "MA_THEO_DOI", DS)
    monkeypatch.setattr(C, "DUNG_BO_LOC", False)          # test không gọi mạng lấy mã Bo_Loc
    monkeypatch.setattr(C, "NGAY_BAT_DAU_CL", "2021-01-01")
    monkeypatch.delenv("DANH_MUC_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    return tmp_path


def test_tong_ket_gon_cong_khai_va_luu_ds_mua(moi_truong):
    gui = []
    with mock.patch.object(chay, "tai", side_effect=_tai), \
            mock.patch.object(chay, "gui", side_effect=lambda nd, rieng_tu=False, **k: gui.append((nd, rieng_tu))), \
            mock.patch.object(chay, "gui_file", return_value=True) as gf:
        assert chay.main(["--che_do", "tong_ket", "--gio", "2026-10-02 15:30"]) == 0
    tin = [nd for nd, _ in gui if nd.startswith("📊 TỔNG KẾT")]
    assert len(tin) == 1 and all(rt is False for _, rt in gui)              # không có danh mục → công khai
    t = tin[0]
    assert "CL" in t and "💼" not in t and "Điểm vào 15' phiên tới: 15P+ATC – mặc định" in t
    ds = json.load(open(C.FILE_TRANG_THAI_CL, encoding="utf-8"))["ds_mua"]
    assert ds["hieu_luc"] == "2026-10-05"                                    # thứ Sáu → phiên thứ Hai
    for z in ds["ma"]:
        assert z["nhom"] in tong_ket_cl.NHOM_MUA and z["cl"] < z["tu"] <= z["den"]
        assert f"{z['ma']} | {z['tu']:,.2f}–{z['den']:,.2f} | MT {z['mt1']:,.2f} → {z['mt3']:,.2f}" in t
        assert z["mt1"] == pytest.approx(z["gia"] + (z["gia"] - z["cl"]))
    assert gf.call_count == 1 and os.path.exists(C.FILE_EXCEL)
    xl = pd.ExcelFile(C.FILE_EXCEL)
    assert {"Tong ket", "Thi truong", "Lich su KN", "Thong ke"} <= set(xl.sheet_names)
    assert "Dang giu" not in xl.sheet_names
    nk = pd.read_csv("lich_su_danh_gia.csv")
    assert set(nk["loai"]) <= {C.LOAI_NHAT_KY_CL} and (nk["cach_cham"] == "HE_THOAT").all()


def test_tong_ket_co_danh_muc_rieng_tu(moi_truong, monkeypatch, capsys):
    dn = _gia_dai("AAA")
    i = len(dn) - 30
    gv = float(dn.close.iloc[i])
    (moi_truong / "danh_muc.csv").write_text(
        f"ma,so_cp,gia_von,cat_lo_dat,ngay_mua\nAAA,47,{gv:.2f},,{dn.index[i]:%d/%m/%Y}\n"
        f"XYZ,21,{gv:.2f},,{dn.index[i]:%d/%m/%Y}\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    gui = []
    with mock.patch.object(chay, "tai", side_effect=_tai), \
            mock.patch.object(chay, "gui", side_effect=lambda nd, rieng_tu=False, **k: gui.append((nd, rieng_tu))), \
            mock.patch.object(chay, "gui_file", return_value=True) as gf:
        assert chay.main(["--che_do", "tong_ket", "--gio", "2026-10-02 15:30"]) == 0
    log = capsys.readouterr().out
    tin = next((nd, rt) for nd, rt in gui if nd.startswith("📊 TỔNG KẾT"))
    assert tin[1] is True and "💼 ĐANG GIỮ (2)" in tin[0] and "XYZ" in tin[0]
    assert "Mua thêm" in tin[0] or "MUA THÊM" in tin[0]
    assert "XYZ" not in log and f"{gv:,.2f}" not in log and "💼" not in log     # log công khai sạch
    assert gf.call_args[1]["rieng_tu"] is True and not os.path.exists(C.FILE_EXCEL)   # Actions: xoá file riêng
    assert "XYZ" not in open("lich_su_danh_gia.csv", encoding="utf-8").read()


def _phien(ngay, gia, kl=None):
    gia = np.asarray(gia, float)
    kl = np.full(len(gia), 1e5) if kl is None else np.asarray(kl, float)
    o = np.r_[gia[0], gia[:-1]]
    idx = [pd.Timestamp(ngay) + pd.Timedelta(g + ":00") for g in GIO[:len(gia)]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, gia) + 0.01, "low": np.minimum(o, gia) - 0.01,
                         "close": gia, "volume": kl}, index=idx)


def _nen_15p(hom_nay):
    ngay = pd.bdate_range(end=hom_nay.index[0].normalize() - pd.Timedelta(days=1), periods=6)
    return pd.concat([_phien(n, 20 - 0.02 * k - 0.01 * np.arange(17)) for k, n in enumerate(ngay)] + [hom_nay])


def _ds_mua(hieu_luc="2026-10-08"):
    z = {"ma": "AAA", "nhom": "MUA_MOI", "tp": "A0", "gia": 20.0, "tu": 19.5, "den": 20.5, "cl": 18.7, "R": 1.3,
         "mt1": 21.3, "mt3": 23.9, "rui_ro": 6.5, "ly_do": "MACD ngày cắt lên 07/10", "khoi_luong": "đủ",
         "hieu_luc": hieu_luc, "atr": 0.6}
    json.dump({"cl": 2, "ds_mua": {"hieu_luc": hieu_luc, "ma": [z]}}, open(C.FILE_TRANG_THAI_CL, "w", encoding="utf-8"))


def test_trong_phien_chi_quet_ds_mua_va_bao_mot_lan(moi_truong):
    _ds_mua()
    gia = [19.8, 19.7, 19.75, 19.8, 19.9, 20.3, 20.35, 20.4] + [20.4] * 9
    dp = _nen_15p(_phien("2026-10-08", gia, [1e5] * 5 + [6e5] + [1e5] * 11))
    goi = []

    def tai(ma, khung="D", *a, **k):
        goi.append((ma, khung))
        return dp if khung == C.KHUNG_PHUT else _tai(ma, khung)
    gui = []
    with mock.patch.object(chay, "tai", side_effect=tai), \
            mock.patch.object(chay, "gui", side_effect=lambda nd, rieng_tu=False, **k: gui.append(nd)):
        assert chay.main(["--che_do", "trong_phien", "--gio", "2026-10-08 10:50"]) == 0
        assert len(gui) == 1 and gui[0].startswith("🟢 MUA NGAY – AAA")
        assert "[Ngày] MACD ngày cắt lên 07/10 ✔" in gui[0] and "[15' · nến 10:00]" in gui[0] and "≥ VWAP" in gui[0]
        assert {m for m, _ in goi} == {"AAA"}                                  # chỉ quét mã trong danh sách mua
        chay.main(["--che_do", "trong_phien", "--gio", "2026-10-08 11:05"])
        assert len(gui) == 1                                                   # không báo trùng
    tt = json.load(open(C.FILE_TRANG_THAI, encoding="utf-8"))
    assert tt["_15p_hom_nay"]["ds"][0]["Trạng thái"] == "MUA"
    nk = pd.read_csv("lich_su_danh_gia.csv")
    assert list(nk["loai"]) == ["MUA_NGAY"]
    k = diem_vao.danh_gia(json.load(open(C.FILE_TRANG_THAI_CL, encoding="utf-8"))["ds_mua"]["ma"][0], dp,
                          "2026-10-08 10:50", "15P")
    gia_mua, cl, mt1, mt3 = diem_vao.muc_sau_mua(k)
    from ptcp.he_thoat import stop_chuan
    assert cl == pytest.approx(stop_chuan(gia_mua, 0.6)) and mt3 == pytest.approx(gia_mua + 3 * (gia_mua - cl))


def test_trong_phien_bo_khi_mo_cua_vuot_vung_va_het_hieu_luc(moi_truong):
    _ds_mua()
    dp = _nen_15p(_phien("2026-10-08", [21.0] * 6))
    gui = []
    with mock.patch.object(chay, "tai", side_effect=lambda ma, khung="D", *a, **k: dp if khung != "D" else _tai(ma)), \
            mock.patch.object(chay, "gui", side_effect=lambda nd, rieng_tu=False, **k: gui.append(nd)):
        chay.main(["--che_do", "trong_phien", "--gio", "2026-10-08 10:50"])
        assert len(gui) == 1 and gui[0].startswith("🚫 BỎ AAA") and "không đuổi" in gui[0]
        chay.main(["--che_do", "trong_phien", "--gio", "2026-10-09 10:50"])    # phiên khác → danh sách hết hạn
        assert len(gui) == 1
    assert diem_vao.doc_ds_mua("2026-10-09 10:00") == []


def test_mua_them_theo_luat_nhoi_kieu_b():
    r = np.r_[np.full(200, 0.0005), np.full(60, 0.006)]
    dn = _gia(r, g0=20.0, end="2026-10-02")
    i = 200
    gv = float(dn.close.iloc[i])
    vt = {"ma": "AAA", "so_cp": 100, "gia_von": gv, "cat_lo": None, "cat_lo_goc": gv * 0.95, "muc_tieu": None,
          "ngay_mua": f"{dn.index[i]:%d/%m/%Y}", "so_lan_mua_them": 0}
    kb = vi_the.danh_gia_ban(vt, {"ma": "AAA", "gia": float(dn.close.iloc[-1])}, dn, "2026-10-02 15:30")
    assert kb["tang"] == 2 and kb["lai_R"] > 3
    mt = tong_ket_cl.mua_them(vt, dn, kb, "2026-10-02 15:30")
    assert mt["du"] and mt["so_cp"] == 25 and mt["cl"] >= mt["gia_von_moi"]
    assert mt["tu"] == pytest.approx(dn.close.iloc[-1]) and mt["den"] > mt["tu"]
    d = tong_ket_cl.dong_giu(vt, kb, mt)
    assert any("➕ MUA THÊM 25 CP" in x for x in d) and any("MA10 tuần" in x for x in d)
    assert not tong_ket_cl.mua_them(dict(vt, so_lan_mua_them=2), dn, kb)["du"]
    vt2 = dict(vt, ngay_mua=f"{dn.index[-5]:%d/%m/%Y}", gia_von=float(dn.close.iloc[-5]), cat_lo_goc=None)
    kb2 = vi_the.danh_gia_ban(vt2, {"ma": "AAA", "gia": float(dn.close.iloc[-1])}, dn, "2026-10-02 15:30")
    m2 = tong_ket_cl.mua_them(vt2, dn, kb2)
    assert not m2["du"] and "3R" in m2["ly_do"]


def test_sat_cat_lo_trong_phien(monkeypatch):
    dn = _gia(np.full(300, 0.0005))
    gv = float(dn.close.iloc[-20])
    vt = {"ma": "AAA", "so_cp": 10, "gia_von": gv, "cat_lo": None, "cat_lo_goc": gv * 0.95, "muc_tieu": None,
          "ngay_mua": f"{dn.index[-20]:%d/%m/%Y}"}
    lo = vi_the.danh_gia_ban(vt, {"ma": "AAA", "gia": gv * 1.2}, dn, "2026-10-02 15:30")["cat_lo"]
    kb = vi_the.danh_gia_ban(vt, {"ma": "AAA", "gia": lo * 1.005}, dn, "2026-10-02 15:30")
    assert kb["muc"] == "GAN_CAT_LO" and "Chuẩn bị lệnh bán" in vi_the.tin_ban(vt, kb, {}, "2026-10-02 10:30")
    assert vi_the.danh_gia_ban(vt, {"ma": "AAA", "gia": lo * 0.999}, dn, "2026-10-02 15:30")["muc"] == "CAT_LO"
    assert vi_the.danh_gia_ban(vt, {"ma": "AAA", "gia": lo * 1.05}, dn, "2026-10-02 15:30")["muc"] != "GAN_CAT_LO"


def test_khoi_luong_theo_bien_dong(monkeypatch):
    monkeypatch.setattr(C, "KL_THEO_BIEN_DONG", True)
    monkeypatch.setattr(C, "ATR_MUC_TIEU_PCT", 3.5)
    hs, atr_pct = tong_ket_cl.he_so_kl(20.0, 1.4)                  # ATR 7%/ngày → × 0,5
    assert atr_pct == pytest.approx(7.0) and hs == pytest.approx(0.5)
    assert tong_ket_cl.he_so_kl(20.0, 0.4)[0] == 1.0                 # ATR 2% → đủ khối lượng
    assert tong_ket_cl.he_so_kl(20.0, 1.4, nua=True)[0] == pytest.approx(0.25)
    s = tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4, von_trieu=500)
    # 500 tr × 1% × 0,5 ÷ 1,4 nghìn/CP = 1.785 CP → làm tròn lô 100 = 1.700 CP
    assert "× 0.50" in s and "ATR 7.0%/ngày > 3.5%" in s and "1,700 CP" in s
    monkeypatch.setattr(C, "KL_THEO_BIEN_DONG", False)
    assert tong_ket_cl.he_so_kl(20.0, 1.4)[0] == 1.0
    assert tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4) == "Khối lượng: 1% vốn ÷ (giá mua − cắt lỗ)"
    assert tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4, nua=True).startswith("Khối lượng: ½ – 0.5% vốn")
