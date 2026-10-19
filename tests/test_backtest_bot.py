

def test_dinh_gia_khong_co_kho_khong_loi(monkeypatch):
    import pandas as pd
    from canh_bao import backtest_bot as B
    from ptcp import kiem_dinh_dinh_gia as kd
    monkeypatch.setattr(kd, "chay", lambda *a, **k: (_ for _ in ()).throw(OSError("thiếu kho")))
    assert B._dinh_gia(pd.DataFrame({"Mã": ["AAA"]}), {"AAA": pd.DataFrame({"close": [1.0]})}) is None
