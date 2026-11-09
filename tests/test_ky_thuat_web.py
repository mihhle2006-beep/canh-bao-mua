# -*- coding: utf-8 -*-
"""thi_truong/ky_thuat_web.py – chỉ số bộ lọc kỹ thuật từ gia/<MÃ>.json."""
import json

from thi_truong import ky_thuat_web as K


def _gia(c, v=None):
    return {"c": c, "h": [x * 1.01 for x in c], "l": [x * 0.99 for x in c], "v": v or [1000] * len(c)}


def test_tang_deu_dinh_52_tuan_va_nen():
    c = [10 * 1.006 ** i for i in range(300)]                            # tăng đều → đỉnh 52 tuần, trên mọi MA, RSI cao
    x = K.chi_so(_gia(c, [1000] * 299 + [3000]))
    assert x["d52"] == 1 and x["tr20"] > 0 and x["tr200"] > 0 and x["rsi"] > 70 and x["kl_d"] == 3.0
    assert abs(x["p1t"] - (1.006 ** 21 - 1)) < 1e-3
    co = [20 + (i % 3) * 0.3 for i in range(240)] + [20.2 + (i % 2) * 0.2 for i in range(40)]   # đi ngang hẹp ≥ 15 phiên
    y = K.chi_so(_gia(co))
    assert y["nen"] >= 15 and y["vuot"] == 0
    z = K.chi_so(_gia(co + [24.0]))                                          # đóng cửa vượt đỉnh nền
    assert z["vuot"] == 1 and z["nen"] == 0
    assert K.chi_so(_gia(c[:30])) == {}


def test_main_ghi_ds(tmp_path):
    (tmp_path / "gia").mkdir()
    (tmp_path / "gia" / "AAA.json").write_text(json.dumps(_gia([10 * 1.006 ** i for i in range(300)])))
    (tmp_path / "ds.json").write_text(json.dumps({"ds": [{"ma": "AAA"}, {"ma": "BBB"}]}))
    assert K.main(["--ra", str(tmp_path)]) == 0
    ds = json.loads((tmp_path / "ds.json").read_text())["ds"]
    assert ds[0]["d52"] == 1 and ds[1]["rsi"] is None and set(K.COT) <= set(ds[1])
