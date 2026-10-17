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
    monkeypatch.setattr(C, "MA_VN30", DS)
    monkeypatch.setattr(C, "MA_THEM", [])
    monkeypatch.setattr(C, "TU_LAY_VN30", False)          # test không gọi mạng lấy rổ VN30
    monkeypatch.setattr(C, "DUNG_BO_LOC", False)          # test không gọi mạng lấy mã Bo_Loc
    monkeypatch.setattr(C, "NGAY_BAT_DAU_CL", "2021-01-01")
    monkeypatch.delenv("DANH_MUC_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setattr(tong_ket_cl, "_loc_quy", lambda ma, vni: None)   # mã giả không có trong ptcp/loc_quy_b.json
    monkeypatch.setattr(C, "CACH_VAO_15P", "tu_dong")     # test chọn cách vào theo backtest (cấu hình thật cố định)
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
    assert "CL" in t and "💼" not in t and "Điểm vào 15' phiên tới" not in t and "Mua trong vùng" not in t
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
        assert "👉 Đặt lệnh 19.90. Không đặt cao hơn 20.50" in gui[0]        # tin gọn: không in tiêu chí 15' / KL
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


def test_mua_them_theo_luat_nhoi_kieu_b(monkeypatch):
    from canh_bao import cau_hinh as C
    monkeypatch.setattr(C, "NGUONG_KHUNG_TUAN_R", 3.0)          # số liệu dựng cho khung tuần từ 3R (sàn 2R)
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
    monkeypatch.setattr(C, "RUI_RO_MOI_LENH_PCT", 1.0)
    monkeypatch.setattr(C, "ATR_MUC_TIEU_PCT", 3.5)
    hs, atr_pct = tong_ket_cl.he_so_kl(20.0, 1.4)                  # ATR 7%/ngày → × 0,5
    assert atr_pct == pytest.approx(7.0) and hs == pytest.approx(0.5)
    assert tong_ket_cl.he_so_kl(20.0, 0.4)[0] == 1.0                 # ATR 2% → đủ khối lượng
    assert tong_ket_cl.he_so_kl(20.0, 1.4, nua=True)[0] == pytest.approx(0.25)
    s = tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4, von_trieu=500)
    # 500 tr × 1% × 0,5 ÷ 1,4 nghìn/CP = 1.785 CP → làm tròn lô 100 = 1.700 CP
    assert "rủi ro 0.50%" in s and "ATR 7.0%/ngày > 3.5%" in s and "1,700 CP" in s
    monkeypatch.setattr(C, "KL_THEO_BIEN_DONG", False)
    assert tong_ket_cl.he_so_kl(20.0, 1.4)[0] == 1.0
    assert tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4) == "Khối lượng: mua 14.3% NAV (rủi ro 1.00% ÷ cắt lỗ 7.0%)"
    assert "mua 20.0% NAV" in tong_ket_cl.dong_khoi_luong(20.0, 19.6, 1.4)          # 1% ÷ 2% = 50% → trần 20%/mã
    assert tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4, nua=True).startswith("Khối lượng: mua 7.1% NAV (rủi ro 0.50%")
    assert tong_ket_cl.dong_khoi_luong(20.0, np.nan, 1.4) == "Khối lượng: 1% vốn ÷ (giá mua − cắt lỗ)"


def test_dong_su_kien_bao_truoc_gdkhq(monkeypatch):
    import pandas as pd
    from canh_bao import tong_ket_cl as T
    S = pytest.importorskip("ptcp.su_kien_quyen")  # ptcp mới (danh-muc)
    monkeypatch.setattr(T.C, "BAO_SU_KIEN_QUYEN", True)
    x = {pd.Timestamp("2026-10-09"): {"he_so_cp": 1.3, "tien": 0.0, "mo_ta": "cổ tức bằng CP 25% + CP thưởng 5%"}}
    monkeypatch.setattr(S, "sap_toi", lambda ma, n, h: x if ma == "HDB" else {})
    d = T.dong_su_kien({"HDB": 28.0, "SBT": 22.7}, "2026-10-07 15:20")
    assert d[1].startswith("📅 SẮP GDKHQ") and len(d) == 3
    assert "HDB GDKHQ 09/10" in d[2] and "× 0.769" in d[2] and "≈ 21.54" in d[2] and "số CP × 1.30" in d[2]
    monkeypatch.setattr(T.C, "BAO_SU_KIEN_QUYEN", False)
    assert T.dong_su_kien({"HDB": 28.0}, "2026-10-07") == []


def test_dong_nhiet_va_khoi_luong_theo_nhiet():
    nh = {"diem": 5, "so_chi_bao": 6, "he_so": 0.5, "chi_bao": [{"ten": "RSI14 VN-Index > 50", "dat": True}]}
    s = tong_ket_cl.dong_nhiet(nh, rr=0.75)
    assert "5/6 (NÓNG)" in s and "= 0.38% vốn" in s and "RSI14" in s
    assert tong_ket_cl.dong_nhiet(None) is None
    assert "mua 5.4% NAV (rủi ro 0.38%" in tong_ket_cl.dong_khoi_luong(20.0, 18.6, 1.4, he_so_nhiet=0.5)


def test_loc_quy_b_ngoai_top_va_he_so(monkeypatch):
    hd = pd.DataFrame([{"Mã": m, "Nhóm": "VAO_NHU_MOI", "Thành phần": "B", "Giá đóng cửa": 10.0, "Cắt lỗ": 9.5,
                        "Vùng mua từ": 9.9, "Vùng mua đến": 10.2, "Hiệu lực": "2026-10-15", "Ưu tiên": ut}
                       for m, ut in (("AAA", 2), ("BBB", 1))])
    ra = {"hanh_dong": hd, "doc": {"ngay": "2026-10-14"}, "vni_df": None}
    loc = {"AAA": {"bo": False, "he_so": 0.5, "he_so_vni": 0.5, "ly_do": ["VN-Index Tăng ×0.5"]},
           "BBB": {"bo": True, "he_so": 1.0, "ly_do": ["ngoài top 100 GTGD (hạng 180)"]}}
    monkeypatch.setattr(tong_ket_cl, "_loc_quy", lambda ma, vni: loc[ma])
    a, b = tong_ket_cl.ds_khuyen_nghi(ra)
    assert a["nhom"] == "VAO_NHU_MOI" and a["he_so_quy"] == 0.5 and a["he_so_vni"] == 0.5
    assert "VN-Index Tăng" in tong_ket_cl.dong_mua(a)
    assert a["uu_tien"] == 1 and tong_ket_cl.dong_mua(a).startswith("★ ")   # BBB (hạng 1) bị loại → AAA lên ★
    assert b["nhom"] == "NGOAI_TOP" and b["nhom"] not in tong_ket_cl.NHOM_MUA


def test_tin_mua_lo_khong_in_tieu_chi_15p():
    kq = {"ma": "DGW", "nhom": "VAO_NHU_MOI", "tu": 44.5, "den": 46.75, "cl": 43.49, "gia_mua": 45.1, "gia_nay": 45.1,
          "thoi_diem": pd.Timestamp("2026-10-15 09:15"), "ly_do": "mở cửa ≤ giá LO", "ly_do_ngay": "MACD",
          "tieu_chi": [("Kích hoạt 15' (MACD cắt lên / phá đỉnh + KL)", False, "chưa")], "atr": np.nan}
    tin = diem_vao.tin_mua(kq, "2026-10-15 09:58", "LO")
    assert "chưa kích hoạt" not in tin and "👉 Đặt lệnh 45.10. Không đặt cao hơn 46.75" in tin
    assert "Đạt điểm mua" not in tin and "Khối lượng" not in tin


def test_von_lenh_nhan_san_moi_he_so():
    k = {"ma": "BBB", "nhom": "MUA_MOI", "tu": 24.1, "den": 24.6, "mt1": 26.0, "mt3": 28.4, "cl": 22.9, "ly_do": "MACD",
         "rui_ro": 6.0, "he_so_kl": 1.0, "nhiet": 4, "he_so_nhiet": 0.75, "he_so_quy": 0.125, "he_so_vni": 0.25,
         "he_so_quy_ma": 0.5, "loc_quy_ma": "ĐẮT (định giá -32%) ×0.5"}
    v = tong_ket_cl.von_lenh(k)
    assert abs(v["rr"] - 0.75 * 0.75 * 0.125) < 1e-9 and abs(v["ty_trong"] - v["rr"] / 6 * 100) < 1e-9
    s = tong_ket_cl.dong_mua(k)
    assert "💰 ≤1.2% NAV (nhiệt ×0.75 · VNI ×0.25 · ĐẮT ×0.5)" in s and "0.07%" not in s
    g = tong_ket_cl.von_lenh({**k, "he_so_nhiet": 1.0, "he_so_quy": 1.5, "he_so_vni": 1.5, "he_so_quy_ma": 1.0,
                              "rui_ro": 2.0})
    assert g["ty_trong"] == 20.0                                       # 1,125% ÷ 2% = 56% → trần 20%/mã


def test_dong_mua_ghi_gia_lo():
    k = {"ma": "DGW", "tu": 44.5, "den": 46.75, "mt1": 47.0, "mt3": 49.9, "cl": 43.49, "ly_do": "MACD", "nhom": "VAO_NHU_MOI"}
    assert "đặt LO 45.25" in tong_ket_cl.dong_mua(k, bien_the="LO")
    assert "LO" not in tong_ket_cl.dong_mua(k, bien_the="15P+ATC")
    assert tong_ket_cl.gia_lo(10.0, 10.5) == 10.15                   # 10,1667 → làm tròn xuống bước 0,05


def test_cach_vao_uu_tien_bang_top_gtgd(monkeypatch):
    monkeypatch.setattr(C, "CACH_VAO_15P", "tu_dong")
    kq = {"15p": {"tot_nhat": "15P+GIO+ATC", "bang": [],
                  "top_gtgd": {"top": 100, "tot_nhat": "LO", "bang": [{"Biến thể": "LO", "TB/lệnh khớp %": -2.37,
                                                                         "Khớp %": 62.5}]}}}
    assert tong_ket_cl.cach_vao(kq) == ("LO", "tốt nhất theo backtest top 100 GTGD")
    assert tong_ket_cl.cach_vao({"15p": {"tot_nhat": "VWAP"}})[0] == "VWAP"


def test_cach_vao_co_dinh():
    assert tong_ket_cl.cach_vao({"15p": {"tot_nhat": "VWAP"}}) == (C.CACH_VAO_15P, "cấu hình")


def test_atc_chi_cho_ma_sao():
    hom_nay = _phien("2026-10-08", [20.3] * 17)                       # cả phiên trên giá LO (19,83) – không khớp LO
    dp = _nen_15p(hom_nay)
    z = {"ma": "AAA", "nhom": "MUA_MOI", "tu": 19.5, "den": 20.5, "cl": 18.7, "ly_do": "MACD", "atr": 0.6}
    sao = diem_vao.danh_gia({**z, "uu_tien": 1.0}, dp, "2026-10-08 14:50", "LO+ATC")
    assert sao["trang_thai"] == "MUA" and sao["atc"]
    for ut in (C.SO_MA_MOI_TUAN + 1.0, None):
        k = diem_vao.danh_gia({**z, "uu_tien": ut}, dp, "2026-10-08 14:50", "LO+ATC")
        assert k["trang_thai"] == "BỎ" and "không phải mã ★" in k["ly_do"]


def test_ma_dang_giu_khong_bao_mua_ngay():
    """Mã đang giữ + hệ thống có điểm mua → tin GIỮ THEO HỆ THỐNG (không 'MUA NGAY', không khối lượng mua)."""
    kq = {"ma": "MSN", "nhom": "VAO_NHU_MOI", "tu": 72.0, "den": 75.0, "cl": 70.92, "gia_mua": 73.8, "gia_nay": 73.8,
          "thoi_diem": pd.Timestamp("2026-10-12 09:15"), "ly_do": "mở cửa ≤ giá LO", "ly_do_ngay": "MACD",
          "tieu_chi": [], "atr": np.nan}
    tin = diem_vao.tin_mua(kq, "2026-10-12 09:20", "LO", dang_giu=True)
    assert tin.startswith("💼 GIỮ THEO HỆ THỐNG – MSN") and "MUA NGAY" not in tin and "KHÔNG mua trùng" in tin
    assert "cắt lỗ 70" in tin and "CP" not in tin
    assert diem_vao.tin_mua(kq, "2026-10-12 09:20", "LO").startswith("🟢 MUA NGAY – MSN")


def test_gia_duoi_lo_van_trong_vung_mua_gia_hien_tai():
    """Đã chạm LO (19,83) từ trước, lúc báo giá 19,60 < LO nhưng ≥ đáy vùng 19,5 → giá mua = giá hiện tại, không phải LO."""
    hom_nay = _phien("2026-10-08", [20.2, 20.0, 19.8, 19.7, 19.6])
    dp = _nen_15p(hom_nay)
    z = {"ma": "AAA", "nhom": "VAO_NHU_MOI", "tu": 19.5, "den": 20.5, "cl": 18.7, "ly_do": "MACD", "atr": 0.6,
         "uu_tien": 1.0}
    k = diem_vao.danh_gia(z, dp, "2026-10-08 10:20", "LO")
    assert k["trang_thai"] == "MUA" and k["gia_mua"] == 19.6 and "dưới LO" in k["ly_do"]
    assert diem_vao.muc_sau_mua(k)[0] == 19.6
    tin = diem_vao.tin_mua(k, "2026-10-08 10:20", "LO")
    assert "MUA NGAY – AAA 19.60" in tin and "Đặt lệnh 19.60" in tin


def test_xep_sao_toi_da_2_ma_cung_nganh():
    from canh_bao.tong_ket_cl import xep_sao_theo_nganh
    mua = [{"ma": m} for m in ("VCB", "BID", "CTG", "HPG", "FPT")]          # 3 ngân hàng đứng đầu
    out = [k["ma"] for k in xep_sao_theo_nganh(mua, so_sao=4, toi_da=2)]
    assert out[:4] == ["VCB", "BID", "HPG", "FPT"] and out[4] == "CTG"


def test_tin_hieu_manh_suat_du_phong(monkeypatch):
    """17/10/2026: tín hiệu MẠNH B → 💪 trong tin + dòng giải thích suất dự phòng; mã biến động mạnh bị lọc."""
    hd = pd.DataFrame([{"Mã": m, "Nhóm": "MUA_MOI", "Thành phần": "B", "Giá đóng cửa": 10.0, "Cắt lỗ": 9.5,
                        "Vùng mua từ": 9.9, "Vùng mua đến": 10.2, "Hiệu lực": "2026-10-19", "Ưu tiên": ut}
                       for m, ut in (("AAA", 1), ("BBB", 2), ("CCC", 3))])
    ra = {"hanh_dong": hd, "doc": {"ngay": "2026-10-16"}, "vni_df": None}
    loc = {"AAA": {"bo": False, "he_so": 1.0, "ly_do": [], "manh_b": True, "dau_hieu_manh": ["sát đỉnh 52T", "RS 3T cao",
                                                                                           "ngành mạnh"]},
           "BBB": {"bo": False, "he_so": 1.0, "ly_do": [], "manh_b": False, "dau_hieu_manh": []},
           "CCC": {"bo": True, "he_so": 1.0, "ly_do": ["biến động mạnh (top 12% rổ, bỏ top 30%)"], "manh_b": False}}
    monkeypatch.setattr(tong_ket_cl, "_loc_quy", lambda ma, vni: loc[ma])
    a, b, c = tong_ket_cl.ds_khuyen_nghi(ra)
    assert a["manh_b"] and "ngành mạnh" in a["dau_hieu_manh"] and not b["manh_b"]
    assert "AAA💪 |" in tong_ket_cl.dong_mua(a) and "💪" not in tong_ket_cl.dong_mua(b)
    assert c["nhom"] == "NGOAI_TOP"
    assert C.CACH_VAO_15P == "15P+GIO+ATC"


def test_tin_ghi_ro_cach_vao_tung_ma():
    k = {"ma": "DGW", "tu": 44.5, "den": 46.75, "mt1": 47.0, "mt3": 49.9, "cl": 43.49, "ly_do": "MACD", "nhom": "MUA_MOI"}
    s = tong_ket_cl.dong_mua(k, bien_the="15P+GIO+ATC")
    assert "↳ vào: chờ 🟢 15' khi giá 44.50–46.75" in s and f"{C.GIO_ATC} chưa mua → ATC nếu 44.50–46.75" in s
    assert "mở cửa > 46.75 → bỏ" in s
    m = tong_ket_cl.mo_ta_cach_vao("15P+GIO+ATC")
    assert "MACD giờ > Signal" in m and "ATC" in m and "không đuổi" in m
    assert "MACD giờ" not in tong_ket_cl.mo_ta_cach_vao("15P+ATC")
    assert "đặt LO 45.25" in tong_ket_cl.dong_mua(k, bien_the="LO+ATC_VWAP") and \
        "VWAP" in tong_ket_cl.cach_vao_ma(k, "LO+ATC_VWAP")
    assert "ATO nếu mở cửa" in tong_ket_cl.cach_vao_ma(k, "ATO") and tong_ket_cl.cach_vao_ma(k, None) == ""


def test_tin_15p_ghi_ro_gia_va_cach_vao():
    kq = {"ma": "DGW", "nhom": "MUA_MOI", "tu": 44.5, "den": 46.75, "cl": 43.49, "gia_mua": 45.1, "gia_nay": 45.1,
          "thoi_diem": pd.Timestamp("2026-10-15 10:15"), "ly_do": "đủ tiêu chí 15'", "ly_do_ngay": "MACD",
          "tieu_chi": [("Kích hoạt 15' (MACD cắt lên / phá đỉnh + KL)", True, "MACD 15' cắt lên")], "atr": np.nan}
    tin = diem_vao.tin_mua(kq, "2026-10-15 10:16", "15P+GIO+ATC")
    assert tin.split("\n")[1] == "👉 Đặt lệnh 45.10. Không đặt cao hơn 46.75" and len(tin.split("\n")) == 3
    tin = diem_vao.tin_mua({**kq, "atc": True}, "2026-10-15 14:26", "15P+GIO+ATC")
    assert tin.startswith("⏰ MUA ATC") and "👉 Đặt lệnh ATC (giá ước tính 45.10). Không mua nếu giá cao hơn 46.75" in tin


def test_canh_bao_da_giu_2_ma_cung_nganh():
    """Bản tin riêng: danh mục đã giữ 2 mã cùng ngành với mã tín hiệu → cảnh báo không mua thêm."""
    from ptcp.loc_quy_b import nganh_cua
    from ptcp.nganh import NGANH
    ng = next(n for n, ds in NGANH.items() if len(ds.split()) >= 3)
    a, b, c = NGANH[ng].split()[:3]
    k = {"ma": c, "tu": 10.0, "den": 10.5, "mt1": 11.0, "mt3": 12.0, "cl": 9.5, "ly_do": "MACD", "nhom": "MUA_MOI"}
    s = tong_ket_cl.dong_mua(k, {a, b})
    assert nganh_cua(c) == ng and f"⚠ đã giữ 2 mã ngành {ng}" in s and a in s and b in s
    assert "⚠" not in tong_ket_cl.dong_mua(k, {a}) and "⚠" not in tong_ket_cl.dong_mua(k, set())   # bản công khai
