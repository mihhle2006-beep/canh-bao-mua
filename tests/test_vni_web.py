# -*- coding: utf-8 -*-
"""thi_truong/vni_web.py – VN-Index ngày từ 2010 (đường RS trang Biểu đồ): file gọn như gia_dai, lỗi tải giữ file cũ."""
import json

from thi_truong import vni_web as V


def test_gon_va_main(tmp_path, monkeypatch):
    dong = [("2024-01-02", 1100.5), ("2024-01-03", 1101.0), ("2024-01-08", 1099.0)]
    assert V.gon(dong) == {"d0": "2024-01-02", "g": [0, 1, 5], "c": [1100.5, 1101.0, 1099.0]} and V.gon([]) is None
    monkeypatch.setattr(V, "tai", lambda: [(f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}", 1000.0 + i) for i in range(300)])
    monkeypatch.setattr(V, "ghi_chi_so", lambda ra: ([], []))
    assert V.main(["--ra", str(tmp_path)]) == 0
    d = json.loads((tmp_path / "vni.json").read_text())
    assert d["d0"] == "2024-01-01" and len(d["c"]) == 300 and d["g"][0] == 0
    monkeypatch.setattr(V, "tai", lambda: None)                              # lỗi mạng: giữ file cũ
    assert V.main(["--ra", str(tmp_path)]) == 0 and len(json.loads((tmp_path / "vni.json").read_text())["c"]) == 300


def test_ghi_chi_so(tmp_path):
    nen = [(f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}", 10.0, 12.0, 9.0, 11.0 + i, 100) for i in range(300)]
    goi = []

    def tai_(ma, so_lan=2):
        goi.append(ma)
        return nen if ma in ("VN30", "HNXINDEX") else None
    co, thieu = V.ghi_chi_so(str(tmp_path), tai_, lambda ma: nen if ma in ("VNDIAMOND", "VNMIDCAP") else None)
    assert co == ["VN30", "VNMID", "VNDIAMOND", "HNX"] and "VNFINLEAD" in thieu and goi.count("HNX") == 1 and "HNXINDEX" in goi
    d = json.loads((tmp_path / "chi_so" / "VN30.json").read_text())
    assert d["d0"] == "2024-01-01" and len(d["o"]) == len(d["c"]) == len(d["v"]) == 300 and d["h"][0] == 12.0
    assert json.loads((tmp_path / "chi_so" / "ds.json").read_text())["ds"] == {"VN30": "VN30", "VNMID": "VNMidcap", "VNDIAMOND": "VNDiamond",
                                                                             "HNX": "HNX-Index"}
