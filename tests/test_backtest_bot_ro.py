"""Rổ tất cả mã (HOSE + HNX) & bảng cách vào theo sàn cho backtest điểm vào 15' (không mạng)."""
import pandas as pd

from canh_bao import backtest_bot as B


def test_ro_tat_ca_gom_toan_san(monkeypatch):
    import ptcp.san as S
    monkeypatch.setattr(B, "ro_rong", lambda: ["HPG", "ACV"])
    monkeypatch.setattr(S, "doc_san", lambda: {"HOSE": ["HPG", "FPT"], "HNX": ["SHS"]})
    assert B.ro_tat_ca() == ["HPG", "ACV", "FPT", "SHS"]


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
