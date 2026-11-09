# -*- coding: utf-8 -*-
"""thi_truong/buoc_gia_web.py – khớp theo bước giá trong phiên (Vietcap) → buoc_gia/<MÃ>.json."""
import json

from thi_truong import buoc_gia_web as B


def test_gon_va_main(tmp_path):
    assert B.gon([{"priceStep": 25600, "accumulatedVolume": 10, "accumulatedBuyVolume": 7, "accumulatedSellVolume": 3},
                  {"priceStep": 25500, "accumulatedVolume": 5, "accumulatedBuyVolume": 1, "accumulatedSellVolume": 4},
                  {"priceStep": None}]) == [[25.5, 5, 1, 4], [25.6, 10, 7, 3]]
    (tmp_path / "gia").mkdir()
    for m, gt in (("AAA", 50), ("BBB", 10)):
        (tmp_path / "gia" / f"{m}.json").write_text(json.dumps({"c": [1.0] * 25, "gt": [gt] * 25}))
    assert B.main(["--ra", str(tmp_path), "--so_ma", "1"], tai_=lambda m: [[10.0, 5, 3, 2]] if m == "AAA" else None) == 0
    d = json.loads((tmp_path / "buoc_gia" / "AAA.json").read_text())
    assert d["b"] == [[10.0, 5, 3, 2]] and json.loads((tmp_path / "buoc_gia" / "ds.json").read_text())["ma"] == ["AAA"]
    assert not (tmp_path / "buoc_gia" / "BBB.json").exists()
