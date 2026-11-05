"""Rổ HOSE + HNX & bảng cách vào theo sàn cho backtest điểm vào 15' (không mạng)."""
import pandas as pd

from canh_bao import backtest_bot as B


def test_bang_san_tach_hose_hnx(monkeypatch):
    import ptcp.san as S
    monkeypatch.setattr(S, "doc_san", lambda: {"HOSE": ["HPG"], "HNX": ["SHS"]})
    ct = pd.DataFrame([{"Mã": m, "Biến thể": bt, "Nhóm": "MUA_MOI", "Khớp": True, "Lãi/lỗ %": l, "So mở cửa %": 0.0}
                       for m, l in (("HPG", 2.0), ("SHS", -1.0), ("ACV", 1.0)) for bt in ("ATO", "LO")])
    k = B._bang_san(ct)
    assert list(k) == ["HOSE", "HNX", "khác"]
    assert k["HNX"]["so_ma"] == 1 and k["HNX"]["so_tin_hieu"] == 1 and k["HNX"]["bang"][0]["TB/lệnh khớp %"] == -1.0
    assert B._bang_san(ct.iloc[:0]) is None


def test_ro_hose_hnx(monkeypatch):
    import ptcp.nganh as N
    import ptcp.san as S
    monkeypatch.setattr(S, "doc_san", lambda: {"HOSE": ["HPG", "FPT"], "HNX": ["SHS"]})
    monkeypatch.setattr(N, "HUY_NIEM_YET", {"FLC": "x"})
    assert B.ro_hose_hnx() == ["HPG", "FPT", "SHS", "FLC"]


def test_luu_file_rieng_khong_doi_file_bot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ra = {"15p": {"ket_luan": "x", "mo_ta": "m"}, "diem_ban": {"ket_luan": "y"}}
    assert B._luu_gui(ra, "2026-10-17", True, None, None, "ket_qua_backtest_hose_hnx.json") == 0
    assert (tmp_path / "ket_qua_backtest_hose_hnx.json").exists() and not (tmp_path / "ket_qua_backtest.json").exists()


def test_tai_nen_5p_gop_tu_1p_va_dung_cache(monkeypatch, tmp_path):
    import numpy as np
    import pandas as pd

    from canh_bao import backtest_bot as B
    from canh_bao import du_lieu
    monkeypatch.setattr(du_lieu, "THU_MUC_CACHE", str(tmp_path))
    goi = []

    def gia_1p(ma, tu, den, khung, chi_so=False):
        goi.append((tu, den))
        ngay = [d for d in pd.bdate_range(pd.Timestamp(tu, unit="s"), pd.Timestamp(den, unit="s")) if d < pd.Timestamp("2026-11-06")]
        t = [x for d in ngay for x in pd.date_range(f"{d:%Y-%m-%d} 09:15", f"{d:%Y-%m-%d} 09:44", freq="1min")]
        t = [x for x in t if tu <= (x - pd.Timedelta(hours=7)).timestamp() < den]
        if not t:
            raise ValueError("rỗng")
        g = 20000.0 + np.arange(len(t))
        return pd.DataFrame({"time": t, "open": g, "high": g + 5, "low": g - 5, "close": g, "volume": 100.0})
    monkeypatch.setattr(du_lieu, "tu_vci", gia_1p)
    d = B.tai_nen_5p("AAA", tu="2026-10-20", cua_so=5, nghi=0)
    assert d is not None and len(d) and (d.index.minute % 5 == 0).all()
    mot = d[d.index.normalize() == d.index[0].normalize()]
    assert len(mot) == 6 and mot.volume.iloc[0] == 500 and mot.open.iloc[0] == 20.0          # 9:15–9:44 → 6 nến 5'
    so_goi = len(goi)
    d2 = B.tai_nen_5p("AAA", tu="2026-10-20", cua_so=5, nghi=0)                          # lần 2: chỉ tải phần mới
    assert len(goi) - so_goi < so_goi and d2.index.equals(d.index)
