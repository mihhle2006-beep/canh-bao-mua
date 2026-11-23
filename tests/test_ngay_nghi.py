"""cong_cu/ngay_nghi.py – lịch nghỉ giao dịch cập nhật hằng tuần: gộp thư viện + cấu hình + phiên thật VNINDEX + tin;
không tự bỏ ngày nghỉ sắp tới; tin chỉ báo; file trong repo đủ ngày cấu hình; bộ lọc / đồng hồ dùng file."""
import json
import os
import sys
from datetime import date, datetime, timedelta

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "cong_cu"))
import ngay_nghi as N  # noqa: E402

HN = date(2026, 11, 27)                                               # thứ Sáu – lượt cập nhật hằng tuần


def _phien(tu, den, tru=()):
    d, ra = tu, []
    while d <= den:
        if d.weekday() < 5 and f"{d:%Y-%m-%d}" not in tru:
            ra.append(f"{d:%Y-%m-%d}")
        d += timedelta(days=1)
    return ra


def test_gop_nguon_giu_ngay_sap_toi_va_doi_chieu_phien():
    tv = {"2026-09-01": "Quốc khánh", "2026-09-02": "Quốc khánh", "2026-11-24": "Ngày Văn hóa Việt Nam",
          "2027-01-01": "Tết Dương lịch", "2024-01-01": "cũ quá"}
    cu = {"2026-12-31": "Nghỉ thêm cũ", "2026-10-20": "Nhầm"}           # 31/12: tương lai, nguồn không còn → GIỮ + cảnh báo
    phien = _phien(HN - timedelta(days=130), HN - timedelta(days=1), tru={"2026-09-01", "2026-09-02", "2026-11-24",
                                                                           "2026-10-14"})
    phien.append("2026-11-26")                                         # đã có
    moi, bao = N.cap_nhat(cu, HN, tv, ["2026-01-02"], phien, {"2027-01-04": "Nghỉ giao dịch 4/1", "2027-01-01": "x"})
    assert "2024-01-01" not in moi and "2026-01-02" in moi and moi["2026-12-31"] == "Nghỉ thêm cũ"
    assert any("31/12/2026" in b and "vẫn giữ" in b for b in bao)
    assert moi["2026-10-14"].startswith("Không có phiên") and any(b.startswith("➕ T4 14/10/2026") for b in bao)
    assert "2026-10-20" in moi                                          # có phiên nhưng > 8 ngày trước: để nguyên, không báo
    assert any(b.startswith("❓") and "04/01/2027" in b for b in bao) and not any("01/01/2027" in b for b in bao)
    assert "2027-01-04" not in moi                                      # tin CHỈ báo, không tự thêm
    moi2, bao2 = N.cap_nhat(moi, HN, tv, ["2026-01-02"], phien + ["2026-11-24"], None)
    assert "2026-11-24" not in moi2 and any(b.startswith("➖ T3 24/11/2026") for b in bao2)   # nghỉ mà có phiên tuần qua
    _, bao3 = N.cap_nhat(moi, HN, tv, [], phien[:10], None)
    assert any("Dữ liệu VNINDEX thiếu" in b for b in bao3)


def test_thu_vien_loi_khong_bao_bo_va_tin_tele():
    cu = {"2026-11-24": "Ngày Văn hóa Việt Nam", "2027-01-01": "Tết Dương lịch"}
    moi, bao = N.cap_nhat(cu, date(2026, 11, 20), None, [], None, None)
    assert moi == cu and bao == []                                     # thư viện lỗi: không cảnh báo "không còn" từng ngày
    t = N.tin_tele(cu, moi, [], date(2026, 11, 20))
    assert t.startswith("📅") and "Sắp nghỉ: T3 24/11/2026 (Ngày Văn hóa Việt Nam)" in t
    assert N.tin_tele(cu, moi, [], date(2026, 12, 5)) is None          # không đổi, 10 ngày tới không nghỉ → im
    assert "+ thêm 1: T5 31/12/2026" in N.tin_tele(cu, {**moi, "2026-12-31": "x"}, [], date(2026, 12, 5))


def test_quet_tin_rss():
    xml = """<rss><channel>
    <item><title>Lịch nghỉ giao dịch chứng khoán Ngày Văn hóa Việt Nam (24/11) - Báo A</title>
      <description>&lt;a&gt;HOSE nghỉ giao dịch thứ Ba ngày 24/11/2026, giao dịch lại 25/11&lt;/a&gt;</description></item>
    <item><title>Chứng khoán nghỉ giao dịch Tết từ 4/2 đến 10/2/2027</title><description></description></item>
    <item><title>VN-Index tăng mạnh phiên 20/11</title><description>giao dịch sôi động</description></item>
    </channel></rss>"""
    tin = N.quet_tin(xml, date(2026, 11, 23))
    assert {"2026-11-24", "2026-11-25", "2027-02-04", "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10"} <= set(tin)
    assert "2027-02-06" not in tin and "2026-11-20" not in tin         # T7 · tin không nói nghỉ
    assert N.quet_tin("", HN) == {} and N.quet_tin(None, HN) == {}


def test_chay_cap_nhat_ghi_file_va_ma_thoat(tmp_path, monkeypatch):
    f = tmp_path / "nn.json"
    gui = []
    monkeypatch.setattr(N, "tu_thu_vien", lambda nam: ({"2026-11-24": "Ngày Văn hóa Việt Nam"}, "holidays 9.9"))
    assert N.chay_cap_nhat(date(2026, 11, 20), str(f), gui.append, lambda *_: None, lambda h: None,
                           lambda: (_ for _ in ()).throw(OSError("mạng"))) == 0
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d["thu_vien"] == "holidays 9.9" and "2026-11-24" in d["ngay"] and d["kiem_luc"]
    assert gui and "Sắp nghỉ" in gui[0]
    assert N.tuoi(str(f)) is not None and N.doc(str(f))["2026-11-24"] == "Ngày Văn hóa Việt Nam"
    monkeypatch.setattr(N, "tu_thu_vien", lambda nam: (_ for _ in ()).throw(ImportError("holidays")))
    assert N.chay_cap_nhat(date(2026, 11, 20), str(f), None, lambda *_: None, lambda h: None, lambda: "") == 1
    assert "2026-11-24" in json.loads(f.read_text(encoding="utf-8"))["ngay"]   # lỗi thư viện: giữ lịch cũ
    (tmp_path / "hong.json").write_text("{", encoding="utf-8")
    assert N.doc(str(tmp_path / "hong.json")) == N.DU_PHONG and N.tuoi(str(tmp_path / "hong.json")) is None


def test_file_trong_repo_du_va_duoc_dung():
    d = N.doc_file()
    assert d and d.get("kiem_luc") and "2026-11-24" in d["ngay"]
    assert set(N.tu_cau_hinh()) <= set(d["ngay"])                     # ngày sở nghỉ thêm ghi tay luôn có
    assert set(N.DU_PHONG) <= set(d["ngay"]) | {x for x in N.DU_PHONG if x < "2026-11-01"}
    assert N.nghi(datetime(2026, 11, 24, 9, 0)) and not N.nghi(date(2026, 11, 25)) and N.nghi(date(2026, 11, 28))
    import dong_ho
    assert "2026-11-24" in dong_ho.NGHI_LE
    sys.path.insert(0, GOC)
    from canh_bao import ma_bo_loc
    ma_bo_loc._LICH.clear()
    assert "2026-11-24" in ma_bo_loc.ngay_nghi(2026)


def test_ma_bo_loc_hop_lich_file(tmp_path, monkeypatch):
    sys.path.insert(0, GOC)
    from canh_bao import ma_bo_loc
    f = tmp_path / "nn.json"
    f.write_text(json.dumps({"kiem_luc": "2026-11-27", "ngay": {"2026-12-15": "Nghỉ đột xuất"}}), encoding="utf-8")
    monkeypatch.setattr(ma_bo_loc, "FILE_LICH_NGHI", str(f))
    ma_bo_loc._LICH.clear()
    try:
        assert "2026-12-15" in ma_bo_loc.ngay_nghi(2026)
        assert ma_bo_loc.han_tu("2026-12-14") == "2026-12-21"          # 4 phiên bỏ 15/12: 16, 17, 18, 21
    finally:
        ma_bo_loc._LICH.clear()


def test_dong_ho_nhan_khi_lich_cu(monkeypatch):
    import dong_ho
    tin = []
    monkeypatch.setattr(dong_ho, "nhan_tele", lambda t, kenh="he_thong": tin.append(t))
    monkeypatch.setattr(N, "tuoi", lambda file=None, bay_gio=None: 3)
    monkeypatch.setattr(dong_ho.NN, "tuoi", lambda file=None, bay_gio=None: 3)
    assert dong_ho.kiem_lich(datetime(2026, 11, 30, 20, 5, tzinfo=dong_ho.VN), in_ra=lambda *_: None) is None
    monkeypatch.setattr(dong_ho.NN, "tuoi", lambda file=None, bay_gio=None: 20)
    assert "chưa cập nhật 20 ngày" in dong_ho.kiem_lich(datetime(2026, 12, 17, 20, 5, tzinfo=dong_ho.VN),
                                                        in_ra=lambda *_: None) and len(tin) == 1
    monkeypatch.setattr(dong_ho.NN, "tuoi", lambda file=None, bay_gio=None: None)
    assert "không đọc được" in dong_ho.kiem_lich(datetime(2026, 12, 17, 20, 5, tzinfo=dong_ho.VN), in_ra=lambda *_: None)
