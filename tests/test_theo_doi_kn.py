# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from canh_bao import nhat_ky, theo_doi_kn as T


def _gia(n=200, dinh=None):
    idx = pd.bdate_range(end="2026-10-08", periods=n)
    c = np.linspace(50, 60, n) if dinh is None else dinh
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6}, index=idx)


def _nk(tmp_path, dong):
    cot = nhat_ky.COT
    df = pd.DataFrame([{c: r.get(c, "") for c in cot} for r in dong])
    p = tmp_path / "nk.csv"
    df.to_csv(p, index=False)
    return p


def _r(ma, ngay, ngay_vao, gia_vao, cat_lo, ket_qua="ĐANG CHỜ", **k):
    return {"id": f"CL|{ma}|{ngay}", "thoi_diem": f"{ngay} 15:00", "ngay": ngay, "ma": ma, "loai": "CHIEN_LUOC",
            "khuyen_nghi": "MUA – TÍN HIỆU MỚI", "nhom": "MUA", "gia": gia_vao, "cat_lo": cat_lo, "ket_qua": ket_qua,
            "ngay_vao": ngay_vao, "gia_vao": gia_vao, "cach_cham": "HE_THOAT", **k}


def test_theo_doi(tmp_path):
    p = _nk(tmp_path, [
        _r("AAA", "2026-09-01", "2026-09-02", 55.0, 52.0),
        _r("AAA", "2026-09-20", "2026-09-21", 57.0, 54.0),                       # MUA lại cùng mã → ghi kèm
        _r("AAA", "2026-09-02", "2026-09-03", 55.5, 52.0),                       # ghi lặp trước/đúng ngày vào → bỏ
        _r("BBB", "2026-09-01", "2026-09-02", 60.0, 58.0),                       # giá rơi dưới cắt lỗ → BÁN
        _r("CCC", "2026-08-01", "2026-08-04", 50.0, 47.0, ket_qua="ĐÚNG", ngay_ket_thuc="2026-10-01",
           gia_ket_thuc=55.0, ket_qua_pct=9.5),
        {**_r("DDD", "2026-09-01", "", "", 10.0), "khuyen_nghi": "CHỜ ĐIỀU CHỈNH", "nhom": "CHỜ"},
    ])
    gia = {"AAA": _gia(), "BBB": _gia(dinh=np.r_[np.full(190, 60.0), np.full(10, 55.0)])}
    tt = tmp_path / "tt.json"
    out = T.tom_tat(pd.Timestamp("2026-10-08 16:00"), gia, None, path=p, path_tt=tt)
    txt = "\n".join(out)
    assert "📌 Theo dõi khuyến nghị: 2 lệnh mở · 1 GIỮ · cần làm:" in txt
    assert "🔴 BBB" in txt and "BÁN đầu phiên tới" in txt and "AAA" not in txt and "DDD" not in txt   # GIỮ → chỉ ở HTML
    bang = T.doc_tt(tt)["bang"]["dang_mo"]
    assert bang[0].startswith("🔴 BBB") and any(d.endswith("báo MUA lại 20/09") and "02/09," not in d and "\n" not in d for d in bang)
    assert "CCC" not in txt                                                    # lần đầu: không báo lệnh đóng cũ
    p2 = _nk(tmp_path, [_r("AAA", "2026-09-01", "2026-09-02", 55.0, 52.0),
                        _r("EEE", "2026-08-01", "2026-08-04", 50.0, 47.0, ket_qua="SAI", ngay_ket_thuc="2026-10-07",
                           gia_ket_thuc=47.0, ket_qua_pct=-6.6)])
    txt2 = "\n".join(T.tom_tat(pd.Timestamp("2026-10-09 16:00"), gia, None, path=p2, path_tt=tt))
    assert "❌ EEE" in txt2 and "-6.6%" in txt2
    assert "EEE" not in "\n".join(T.tom_tat(pd.Timestamp("2026-10-09 16:00"), gia, None, path=p2, path_tt=tt))


def test_khuyen_nghi_mua_lai_giu_theo_lenh_moi(tmp_path):
    """30/10/2026: lệnh cũ chạm cắt lỗ nhưng hệ thống vừa báo MUA lại (cắt lỗ mới thấp hơn giá) → GIỮ theo khuyến nghị mới,
    không báo 🔴 BÁN cạnh tin ★ MUA của chính mã đó; giá dưới cả cắt lỗ mới → vẫn BÁN."""
    gia = {"BBB": _gia(dinh=np.r_[np.full(190, 60.0), np.full(10, 55.0)])}
    for cl_moi, giu in ((54.0, True), (56.0, False)):
        p = _nk(tmp_path, [_r("BBB", "2026-09-01", "2026-09-02", 60.0, 58.0),
                           _r("BBB", "2026-10-06", "2026-10-07", 55.0, cl_moi)])
        tt = tmp_path / f"tt{cl_moi}.json"
        txt = "\n".join(T.tom_tat(pd.Timestamp("2026-10-08 16:00"), gia, None, path=p, path_tt=tt))
        bang = T.doc_tt(tt)["bang"]["dang_mo"]
        if giu:
            assert "🔴" not in txt and bang[0].startswith("🟢 BBB 55.00 | GIỮ theo khuyến nghị MUA mới 06/10 · Cắt lỗ 54.00")
        else:
            assert "🔴 BBB" in txt and "BÁN đầu phiên tới" in txt
