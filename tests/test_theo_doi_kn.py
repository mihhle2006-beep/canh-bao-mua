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
        _r("BBB", "2026-09-01", "2026-09-02", 60.0, 58.0),                       # giá rơi dưới cắt lỗ → BÁN
        _r("CCC", "2026-08-01", "2026-08-04", 50.0, 47.0, ket_qua="ĐÚNG", ngay_ket_thuc="2026-10-01",
           gia_ket_thuc=55.0, ket_qua_pct=9.5),
        {**_r("DDD", "2026-09-01", "", "", 10.0), "khuyen_nghi": "CHỜ ĐIỀU CHỈNH", "nhom": "CHỜ"},
    ])
    gia = {"AAA": _gia(), "BBB": _gia(dinh=np.r_[np.full(190, 60.0), np.full(10, 55.0)])}
    tt = tmp_path / "tt.json"
    out = T.tom_tat(pd.Timestamp("2026-10-08 16:00"), gia, None, path=p, path_tt=tt)
    txt = "\n".join(out)
    assert "📌 THEO DÕI KHUYẾN NGHỊ ĐÃ GỬI" in txt and "(2 lệnh đang mở)" in txt
    assert txt.index("🔴 BBB") < txt.index("AAA") and "BÁN đầu phiên tới" in txt
    assert "báo MUA lại 20/09" in txt and "DDD" not in txt
    assert "CCC" not in txt                                                    # lần đầu: không báo lệnh đóng cũ
    p2 = _nk(tmp_path, [_r("AAA", "2026-09-01", "2026-09-02", 55.0, 52.0),
                        _r("EEE", "2026-08-01", "2026-08-04", 50.0, 47.0, ket_qua="SAI", ngay_ket_thuc="2026-10-07",
                           gia_ket_thuc=47.0, ket_qua_pct=-6.6)])
    txt2 = "\n".join(T.tom_tat(pd.Timestamp("2026-10-09 16:00"), gia, None, path=p2, path_tt=tt))
    assert "❌ EEE" in txt2 and "-6.6%" in txt2
    assert "EEE" not in "\n".join(T.tom_tat(pd.Timestamp("2026-10-09 16:00"), gia, None, path=p2, path_tt=tt))
