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
    assert P.ma_thanh_khoan(str(tmp_path), 0) == ["BBB", "AAA", "CCC"] == P.ma_thanh_khoan(str(tmp_path))   # 0 = mọi mã


def test_ma_them_doc_file(tmp_path):
    from thi_truong import ma_them
    p = tmp_path / "ma_them.txt"
    p.write_text("# ghi chú SBX\nsbb, VNM\n  hpg\nVNM x\n", encoding="utf-8")
    assert ma_them(str(p)) == ["SBB", "VNM", "HPG"] and ma_them(str(tmp_path / "khong.txt")) == []
    assert "SBB" in ma_them()


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
    monkeypatch.setattr("thi_truong.ma_them", lambda: ["SBB"])                    # thi_truong/ma_them.txt
    assert P.main(["--ra", str(tmp_path), "--trong_phien", "--so_ma", "1", "--them_file", str(giu), "--tin_hieu", str(tt),
                   "--bo_loc", str(bl), "--them", "x y,ZZZ"]) == 0
    assert sorted({m for m, _ in chay}) == ["BBB", "GGG", "LLL", "SBB", "TTT", "ZZZ"]   # top 1 + giữ + bot + bộ lọc + mã thêm (bỏ rác)
    assert (tmp_path / "phut" / "1" / "CU.json").exists()                          # không xoá file mã khác
    ds = json.loads((tmp_path / "phut" / "ds.json").read_text())
    assert "CU" in ds["1"] and "TTT" in ds["5"]
    monkeypatch.setattr("thi_truong.ma_them", lambda: [])
    assert P.ma_them("", str(tmp_path / "khong_co.txt"), str(tmp_path / "khong.json"), None) == []


def test_va_gia_ngay_tu_nen_5_phut(tmp_path):
    from datetime import datetime
    (tmp_path / "gia").mkdir()
    (tmp_path / "phut" / "5").mkdir(parents=True)
    g = {"d": ["2026-11-23"], "o": [10.0], "h": [10.5], "l": [9.8], "c": [10.2], "c0": [10.2], "v": [1000], "gt": [0.01],
         "nn": [0.5], "nn_pt": [3.1]}
    (tmp_path / "gia" / "VIC.json").write_text(json.dumps(g))
    s = lambda d, gio: int(datetime.fromisoformat(f"{d}T{gio}:00+07:00").timestamp())          # noqa: E731
    t = [s("2026-11-23", "14:45"), s("2026-11-24", "09:15"), s("2026-11-24", "14:45"), s("2026-11-26", "09:15"),
         s("2026-11-26", "14:45"), s("2026-11-27", "09:15")]
    o, h, l_, c, v = [10.2, 10.3, 10.6, 10.9, 11.0, 11.2], [10.3, 10.8, 10.7, 11.1, 11.3, 11.4], \
        [10.1, 10.2, 10.4, 10.8, 10.9, 11.1], [10.2, 10.6, 10.5, 11.0, 11.2, 11.3], [5, 100, 200, 300, 400, 9]
    (tmp_path / "phut" / "5" / "VIC.json").write_text(json.dumps(P.ma_hoa(t, o, h, l_, c, v)))
    assert P.va_gia_ngay(str(tmp_path), "VIC", "2026-11-27") == 2          # 24 và 26 (23 đã có, 27 = hôm nay chưa đóng)
    r = json.loads((tmp_path / "gia" / "VIC.json").read_text())
    assert r["d"] == ["2026-11-23", "2026-11-24", "2026-11-26"]
    assert r["o"][1:] == [10.3, 10.9] and r["h"][1:] == [10.8, 11.3] and r["l"][1:] == [10.2, 10.8] and r["c"][1:] == [10.5, 11.2]
    assert r["v"][1:] == [300, 700] and r["nn"] == [0.5, None, None] and r["nn_pt"] == [3.1, 3.1, 3.1]
    assert P.va_gia_ngay(str(tmp_path), "VIC", "2026-11-27") == 0          # chạy lại không thêm trùng


def test_va_gia_ngay_nen_phang_ngay_khong_khop_va_khoi_ngoai_bang(tmp_path):
    from datetime import datetime
    (tmp_path / "gia").mkdir()
    (tmp_path / "phut" / "5").mkdir(parents=True)
    g = {"d": ["2026-11-23"], "o": [5.0], "h": [5.0], "l": [5.0], "c": [5.0], "c0": [5.0], "v": [200], "gt": [0.001],
         "nn": [0.0], "nn_m": [0.0], "nn_b": [0.0], "dat_m": [10]}
    (tmp_path / "gia" / "NED.json").write_text(json.dumps(g))
    s = lambda d, gio: int(datetime.fromisoformat(f"{d}T{gio}:00+07:00").timestamp())          # noqa: E731
    t = [s("2026-11-23", "10:00"), s("2026-11-25", "10:00"), s("2026-11-25", "14:45")]       # 24 + 26: không khớp
    (tmp_path / "phut" / "5" / "NED.json").write_text(json.dumps(P.ma_hoa(t, [5.0, 5.1, 5.2], [5.0, 5.2, 5.3], [5.0, 5.1, 5.1],
                                                                            [5.0, 5.2, 5.25], [200, 300, 100])))
    phien = {"2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"}
    bang = ("2026-11-25", {"NED": {"nn": 0.3, "gt": 0.0021, "co_gd": 1}})
    assert P.va_gia_ngay(str(tmp_path), "NED", "2026-11-27", phien, bang) == 3
    r = json.loads((tmp_path / "gia" / "NED.json").read_text())
    assert r["d"] == ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"]
    assert [r["o"][1], r["h"][1], r["l"][1], r["c"][1], r["v"][1], r["nn"][1]] == [5.0, 5.0, 5.0, 5.0, 0, 0.0]   # nến phẳng
    assert r["c"][2] == 5.25 and r["v"][2] == 400 and r["nn"][2] == 0.3 and r["gt"][2] == 0.0021 and r["nn_m"][2] is None
    assert r["c"][3] == 5.25 and r["v"][3] == 0 and r["dat_m"] == [10, None, None, None]                          # phẳng theo giá mới
    # mã không khớp lệnh nào 10 phiên gần nhất (ngừng giao dịch) → không vẽ nến phẳng
    (tmp_path / "gia" / "OLD.json").write_text(json.dumps({**g, "d": ["2026-11-23"]}))
    (tmp_path / "phut" / "5" / "OLD.json").write_text(json.dumps(P.ma_hoa([s("2026-10-01", "10:00")], [5.0], [5.0], [5.0], [5.0], [1])))
    nhieu = phien | {f"2026-11-{x:02d}" for x in range(2, 23)}
    assert P.va_gia_ngay(str(tmp_path), "OLD", "2026-11-27", nhieu) == 0


def test_doc_bang_chi_nhan_bang_chot_phien(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"phien": "2026-11-27", "dang_gd": False, "loc": {"cot": ["ma", "gia", "nn", "gt", "co_gd"],
                                                                              "dong": [["VIC", 243, -6.1, 360.9, 1]]}}))
    assert P.doc_bang(str(f)) == ("2026-11-27", {"VIC": {"nn": -6.1, "gt": 360.9, "co_gd": 1}})
    f.write_text(json.dumps({"phien": "2026-11-27", "dang_gd": True, "loc": {"cot": ["ma"], "dong": []}}))
    assert P.doc_bang(str(f)) is None and P.doc_bang(str(tmp_path / "khong.json")) is None
