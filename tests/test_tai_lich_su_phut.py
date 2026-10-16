import pandas as pd

from canh_bao import du_lieu


def _nen(tu, den):
    t = pd.date_range(pd.Timestamp(tu, unit="s").normalize() + pd.Timedelta(hours=9), periods=3, freq="15min")
    t = t[(t >= pd.Timestamp(tu, unit="s")) & (t < pd.Timestamp(den, unit="s"))]
    return pd.DataFrame({"time": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0})


def test_tai_bu_phan_dau_khi_moc_lui_xa_hon_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(du_lieu, "_cache", lambda ten: str(tmp_path / f"{ten}.csv"))
    goi = []

    def nguon(ma, tu, den, khung, chi_so=False):
        goi.append((tu, den))
        return [("VNDirect", lambda: _nen(tu, den)), ("DNSE", lambda: _nen(tu, den)),
                ("SSI", lambda: _nen(tu, den)), ("VCI", lambda: _nen(tu, den))]
    monkeypatch.setattr(du_lieu, "cac_nguon", nguon)
    monkeypatch.setattr(du_lieu.time, "time", lambda: pd.Timestamp("2024-03-01").timestamp())
    cache = _nen(pd.Timestamp("2024-02-20").timestamp(), pd.Timestamp("2024-02-21").timestamp()).set_index("time")
    cache.to_csv(tmp_path / "HPG_15_lich_su.csv")
    out = du_lieu.tai_lich_su_phut("HPG", "2023-09-11", nghi=0)
    assert out.index[0] < pd.Timestamp("2023-10-15")                    # đã tải bù về gần mốc 11/09/2023
    assert min(t for t, _ in goi) <= pd.Timestamp("2023-09-11").timestamp()
