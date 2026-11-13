# -*- coding: utf-8 -*-
"""Chứng quyền cho trang Biểu đồ (thi_truong/chung_quyen_web.py → cw.json): hoà vốn = giá thực hiện + giá CW × tỷ lệ, bỏ CW
đã đáo hạn / thiếu thông tin, nhóm theo mã cơ sở, đáo hạn gần trước; không có dữ liệu thì giữ file cũ. Mã giả (AAA / BBB)."""
import json

from thi_truong import chung_quyen_web as C


def _cw(ma, cs, th, tl, dh, gia, tham_chieu=100, to_chuc="CTCK X"):
    return {"listingInfo": {"symbol": ma, "underlyingSymbol": cs, "exercisePrice": th, "exerciseRatio": tl, "maturityDate": dh,
                            "lastTradingDate": dh[:6] + "01", "issuerName": to_chuc, "refPrice": tham_chieu},
            "matchPrice": {"matchPrice": gia, "referencePrice": tham_chieu, "accumulatedVolume": 1200}}


def test_ty_le():
    assert C.ty_le("1.7245:1") == 1.7245 and C.ty_le("4:1") == 4 and C.ty_le("2") == 2.0
    assert C.ty_le("") is None and C.ty_le("x:1") is None and C.ty_le("2:0") is None


def test_gon_hoa_von_va_loc():
    ds = [_cw("CAAA2602", "AAA", 27420, "1.7245:1", "20270308", 150),
          _cw("CAAA2601", "AAA", 25000, "4:1", "20270118", 0, tham_chieu=50),        # chưa khớp → giá tham chiếu
          _cw("CAAA2501", "AAA", 30000, "2:1", "20261101", 10),                      # đã đáo hạn → bỏ
          _cw("CBBB2601", "bbb", 18500, "5:1", "2027-02-01", 300),
          _cw("CCCC2601", "CCC", None, "5:1", "20270201", 300),                      # thiếu giá thực hiện → bỏ
          {"listingInfo": {}}, {}]
    out = C.gon(ds, "2026-11-13")
    assert set(out) == {"AAA", "BBB"}
    a = out["AAA"]
    assert [z[0] for z in a] == ["CAAA2601", "CAAA2602"]                             # đáo hạn gần trước
    z = a[1]
    assert z[1] == "CTCK X" and z[2] == 27.42 and z[3] == 1.7245 and z[4] == "2027-03-08" and z[5] == "2027-03-01"
    assert z[6] == 150 and z[7] == round((27420 + 150 * 1.7245) / 1000, 2) and z[8] == 1200
    assert a[0][6] == 50 and a[0][7] == 25.2                                          # 25 000 + 50 × 4
    assert out["BBB"][0][7] == 20.0


def test_main_ghi_va_giu_file_cu(tmp_path):
    ra = str(tmp_path)
    assert C.main(["--ra", ra], tai_=lambda: [_cw("CAAA2602", "AAA", 27420, "2:1", "20991231", 100)]) == 0
    d = json.loads((tmp_path / "cw.json").read_text(encoding="utf-8"))
    assert d["ma"]["AAA"][0][0] == "CAAA2602" and d["ma"]["AAA"][0][7] == 27.62 and d["phien"] and d["cap_nhat"]
    assert C.main(["--ra", ra], tai_=lambda: []) == 0                                # lỗi nguồn / rỗng: giữ file cũ
    assert json.loads((tmp_path / "cw.json").read_text(encoding="utf-8"))["ma"]["AAA"]


def test_workflow_chay_chung_quyen():
    w = open(".github/workflows/bang_thi_truong.yml", encoding="utf-8").read()
    i = w.index("python -m thi_truong.chung_quyen_web --ra docs/ma/du_lieu")
    assert w.index("Lấy dữ liệu trang Tra cứu mã") < i < w.index("- name: Gói trang")           # sau khi lấy du_lieu, trước khi gói
    assert "continue-on-error: true" in w[w.rindex("- name:", 0, i):i]
