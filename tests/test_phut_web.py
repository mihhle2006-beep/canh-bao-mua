# -*- coding: utf-8 -*-
"""thi_truong/phut_web.py – nến 1' / 5' cho trang Biểu đồ: mã hoá gọn, nối file cũ, cắt theo số ngày giữ, chọn mã thanh khoản."""
import json

from thi_truong import phut_web as P


def test_ma_hoa_giai_ma_khu_hoan_toan():
    t = [1_780_000_000 + 60 * i for i in range(5)] + [1_780_000_000 + 60 * 400]
    o, h, l_, c, v = [21.2, 21.25, 21.3, 21.2, 21.15, 21.4], [21.3] * 6, [21.1] * 6, [21.25, 21.3, 21.2, 21.15, 21.2, 21.35], [100, 0, 2500, 300, 1, 9]
    d = P.ma_hoa(t, o, h, l_, c, v)
    assert d["t0"] == t[0] and d["dt"] == [0, 1, 1, 1, 1, 396] and d["c"][:3] == [2125, 5, -10]
    assert P.giai_ma(d) == (t, o, h, l_, c, v) and P.giai_ma({}) == ([], [], [], [], [], [])


def test_cap_nhat_noi_file_cu_va_cat_ngay(tmp_path, monkeypatch):
    now = 1_790_000_000
    cu = [now - 200 * 86400, now - 10 * 86400]                       # nến 200 ngày trước (1' chỉ giữ 95 ngày) + 10 ngày trước
    (tmp_path / "phut" / "1").mkdir(parents=True)
    (tmp_path / "phut" / "1" / "AAA.json").write_text(json.dumps(P.ma_hoa(cu, [1, 2], [1, 2], [1, 2], [1, 2], [5, 6])))
    goi = []

    def tai(ma, res, tu, den, so_lan=3):
        goi.append((ma, res, tu))
        return [[now - 10 * 86400, now - 86400], [2.5, 3], [2.5, 3], [2.5, 3], [2.5, 3], [7, 8]]   # nến trùng → lấy bản mới
    monkeypatch.setattr(P, "tai", tai)
    assert P.cap_nhat(str(tmp_path), "AAA", "1", now) == 2
    assert goi[0][2] == now - 13 * 86400                              # tải từ nến cuối file cũ − 3 ngày
    t, o, *_, v = P.giai_ma(json.loads((tmp_path / "phut" / "1" / "AAA.json").read_text()))
    assert t == [now - 10 * 86400, now - 86400] and o == [2.5, 3] and v == [7, 8]
    monkeypatch.setattr(P, "tai", lambda *a, **k: None)              # lỗi mạng: giữ file cũ
    assert P.cap_nhat(str(tmp_path), "AAA", "1", now) == 2


def test_chon_ma_thanh_khoan(tmp_path):
    (tmp_path / "gia").mkdir()
    for m, gt in (("AAA", 50), ("BBB", 500), ("CCC", 5)):
        (tmp_path / "gia" / f"{m}.json").write_text(json.dumps({"c": [1] * 30, "gt": [gt] * 30}))
    (tmp_path / "gia" / "MOI.json").write_text(json.dumps({"c": [1] * 5, "gt": [999] * 5}))     # mới niêm yết < 20 phiên: bỏ
    assert P.ma_thanh_khoan(str(tmp_path), 2, ["ZZZ", "BBB"]) == ["BBB", "AAA", "ZZZ"]


def test_trong_phien_chi_noi_ma_chon_va_giu_ma_khac(tmp_path, monkeypatch):
    (tmp_path / "gia").mkdir()
    for m, gt in (("AAA", 50), ("BBB", 500), ("CCC", 5)):
        (tmp_path / "gia" / f"{m}.json").write_text(json.dumps({"c": [1] * 30, "gt": [gt] * 30}))
    for r in ("1", "5"):
        (tmp_path / "phut" / r).mkdir(parents=True)
        (tmp_path / "phut" / r / "CU.json").write_text("{}")                  # mã dựng sáng nay, ngoài danh sách trong phiên
    (tmp_path / "phut" / "ds.json").write_text(json.dumps({"1": ["CU"], "5": ["CU"]}))
    giu = tmp_path / "giu.txt"
    giu.write_text("GGG,BBB\n")
    tt = tmp_path / "tt.json"
    tt.write_text(json.dumps({"tin_hieu": {"ma": [["TTT", "Mua mới", 1, 2, 0.9, 2.1, 2.3, "x"]]}}))
    bl = tmp_path / "bl.json"
    bl.write_text(json.dumps({"ma": {"LLL": ["quy_b"]}}))
    chay = []
    monkeypatch.setattr(P, "cap_nhat", lambda thu_muc, ma, res, bay_gio: chay.append((ma, res)) or 3)
    assert P.main(["--ra", str(tmp_path), "--trong_phien", "--so_ma", "1", "--them_file", str(giu), "--tin_hieu", str(tt),
                   "--bo_loc", str(bl), "--them", "x y,ZZZ"]) == 0
    assert sorted({m for m, _ in chay}) == ["BBB", "GGG", "LLL", "TTT", "ZZZ"]       # top 1 + giữ + bot + bộ lọc (bỏ chuỗi rác)
    assert (tmp_path / "phut" / "1" / "CU.json").exists()                          # không xoá file mã khác
    ds = json.loads((tmp_path / "phut" / "ds.json").read_text())
    assert "CU" in ds["1"] and "TTT" in ds["5"]
    assert P.ma_them("", str(tmp_path / "khong_co.txt"), str(tmp_path / "khong.json"), None) == []
