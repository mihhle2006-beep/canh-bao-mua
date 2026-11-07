# -*- coding: utf-8 -*-
"""thi_truong/he_thong_web.py – dữ liệu hệ thống cho mục "Đọc biểu đồ": ngưỡng luật đọc từ cau_hinh.py lúc chạy nhưng KHÔNG ghi
ra (trang công khai) – he_thong.json chỉ có đạt / chưa đạt từng điều kiện; lịch sử tín hiệu bot (lich_su_danh_gia.csv) theo mã.
Ngưỡng trong test là số giả."""
import json

from thi_truong import he_thong_web as H

CH = ("QUY_RS3T_NONG = 50\nQUY_BO_BIEN_DONG_PCT = 40   # ghi chú\nQUY_DAT_NGUONG_PCT = -10\nQUY_MANH_DINH_PCT = -5\n"
      "QUY_MANH_RS3T = 30\nQUY_MANH_TK = 2\n  QUY_MANH_SO_DAU_HIEU = 9\n")


def test_nguong_doc_tu_cau_hinh_thieu_thi_none(tmp_path):
    p = tmp_path / "cau_hinh.py"
    p.write_text(CH)
    ng = H.nguong(str(p))
    assert ng["QUY_RS3T_NONG"] == 50 and ng["QUY_BO_BIEN_DONG_PCT"] == 40 and ng["QUY_DAT_NGUONG_PCT"] == -10
    assert ng["QUY_MANH_SO_DAU_HIEU"] is None                                  # thụt lề (trong khối) → không lấy
    assert set(H.nguong(str(tmp_path / "khong_co.py")).values()) == {None}


def test_chi_ghi_dat_chua_dat_khong_ghi_nguong_va_so_lieu(tmp_path):
    p = tmp_path / "cau_hinh.py"
    p.write_text(CH.replace("  QUY_MANH", "QUY_MANH").replace("= 9", "= 2"))
    ng = H.nguong(str(p))
    loc = {"ngay_gia": "2026-11-06", "ro_tuan": {"ngay_chot": "2026-10-30", "ma": ["BBB", "AAA"]}, "hang_gtgd": {"AAA": 2, "BBB": 1, "CCC": 150},
           "gtgd": {"AAA": 300.5}, "hang_rs3t": {"AAA": 45, "BBB": 77.7}, "bien_dong_hang": {"AAA": 0.55, "BBB": 0.12},
           "dinh_gia": {"AAA": -3.3, "BBB": -12.3}, "cach_dinh_52t": {"AAA": -1.1}, "tk_tang": {"AAA": 1.2}, "rs_nganh": {"AAA": 4.4}}
    d = H.he_thong(loc, ng, {"phien": "2026-11-06", "ma": {"AAA": ["quy_b"]}})
    r = {m: dict(zip(d["cot"], v)) for m, v in d["ma"].items()}
    assert r["AAA"] == {"ro": 1, "rs": 1, "bien_dong": 1, "dat": 0, "m_dinh": 1, "m_rs": 1, "m_tk": 0, "m_nganh": 1, "manh": 1}
    assert r["BBB"]["rs"] == 0 and r["BBB"]["bien_dong"] == 0 and r["BBB"]["dat"] == 1 and r["BBB"]["m_tk"] is None
    assert r["CCC"]["ro"] == 0 and r["CCC"]["rs"] is None
    txt = json.dumps(d)
    assert "nguong" not in txt and "QUY_" not in txt                            # không lộ ngưỡng
    for so in ("45", "77.7", "0.55", "-12.3", "300.5", "150", "-1.1", "4.4"):   # không lộ số liệu đem so
        assert so not in txt.replace("2026-", ""), so
    r0 = dict(zip(H.COT, H.he_thong(loc, H.nguong(None))["ma"]["AAA"]))          # thiếu ngưỡng → không đánh giá
    assert {r0[k] for k in ("rs", "bien_dong", "dat", "m_dinh", "m_rs", "m_tk", "manh")} == {None} and r0["ro"] == 1


def test_lich_su_tin_hieu_va_main(tmp_path):
    csv = tmp_path / "ls.csv"
    csv.write_text("\ufeffid,ngay,ma,loai,nhom,ket_qua,gia,so_tk\n1,2026-11-02,aaa,MUA_NGAY,MUA,ĐÚNG,10,999\n2,2026-10-01,AAA,CHIEN_LUOC,MUA,SAI,9,1\n"
                   "3,2026-10-05,,X,MUA,SAI,1,1\n", encoding="utf-8")
    th = H.lich_su_tin_hieu(str(csv))
    assert list(th) == ["AAA"] and [z["ngay"] for z in th["AAA"]] == ["2026-10-01", "2026-11-02"]
    assert "so_tk" not in th["AAA"][0] and th["AAA"][1]["ket_qua"] == "ĐÚNG"                # chỉ cột cần, không cột lạ
    out = tmp_path / "ra"
    assert H.main(["--ra", str(out), "--loc", str(tmp_path / "x.json"), "--lich_su", str(csv), "--bo_loc", str(tmp_path / "y.json"),
                   "--cau_hinh", str(tmp_path / "z.py")]) == 0
    assert json.loads((out / "tin_hieu" / "AAA.json").read_text())[0]["ngay"] == "2026-10-01"
    assert json.loads((out / "he_thong.json").read_text())["ma"] == {}
