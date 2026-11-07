# -*- coding: utf-8 -*-
"""thi_truong/vni_web.py – VN-Index ngày từ 2010 (đường RS trang Biểu đồ): file gọn như gia_dai, lỗi tải giữ file cũ."""
import json

from thi_truong import vni_web as V


def test_gon_va_main(tmp_path, monkeypatch):
    dong = [("2024-01-02", 1100.5), ("2024-01-03", 1101.0), ("2024-01-08", 1099.0)]
    assert V.gon(dong) == {"d0": "2024-01-02", "g": [0, 1, 5], "c": [1100.5, 1101.0, 1099.0]} and V.gon([]) is None
    monkeypatch.setattr(V, "tai", lambda: [(f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}", 1000.0 + i) for i in range(300)])
    assert V.main(["--ra", str(tmp_path)]) == 0
    d = json.loads((tmp_path / "vni.json").read_text())
    assert d["d0"] == "2024-01-01" and len(d["c"]) == 300 and d["g"][0] == 0
    monkeypatch.setattr(V, "tai", lambda: None)                              # lỗi mạng: giữ file cũ
    assert V.main(["--ra", str(tmp_path)]) == 0 and len(json.loads((tmp_path / "vni.json").read_text())["c"]) == 300
