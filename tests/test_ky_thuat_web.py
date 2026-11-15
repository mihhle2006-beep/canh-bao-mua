# -*- coding: utf-8 -*-
"""Tab Kỹ thuật (docs/ma/index.html): đồng thuận 15 chỉ báo + 6 trụ – chạy hàm thuần trong node với chuỗi giá giả."""
import json
import re
import shutil
import subprocess

import pytest


def _chay(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open("docs/ma/index.html", encoding="utf-8").read()
    tro = "\n".join(re.search(rf"^const {t} = .*$", h, re.M).group(0) for t in ("esc", "so", "pt", "mau", "tb"))
    a = h[h.index("// ---------------------------------------------------------------- CHỈ BÁO KỸ THUẬT (hàm thuần"):
          h.index("// ---------------------------------------------------------------- hết chỉ báo kỹ thuật")]
    b = h[h.index("// ---------------------------------------------------------------- PHÂN TÍCH KỸ THUẬT – hàm thuần"):
          h.index("// ---------------------------------------------------------------- hết hàm thuần kỹ thuật")]
    kq = subprocess.run(["node", "-e", tro + "\n" + a + "\n" + b + "\n" + ma_js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr
    return json.loads(kq.stdout)


CHUOI = """
const tao = (n, buoc, nhieu = 0.6) => { const c = [], h = [], l = [], v = [], d = [];
  for (let i = 0; i < n; i++) { const g = 50 + buoc * i + nhieu * Math.sin(i / 3); c.push(g); h.push(g + 0.5); l.push(g - 0.5); v.push(1e6 * (1 + (i % 5) / 10));
    d.push(new Date(Date.UTC(2025, 0, 1 + i)).toISOString().slice(0, 10)); }
  return {d, o: c.map((x, i) => i ? c[i - 1] : x), h, l, c, v}; };
const len = tao(300, 0.15), xuong = tao(300, -0.1), ngang = tao(300, 0, 2);
"""


def test_dong_thuan_theo_xu_huong():
    kq = _chay(CHUOI + "console.log(JSON.stringify([len, xuong, ngang].map(x => kt_dong_thuan(x))));")
    up, dn, fl = kq
    assert up["n"] == 15 and len(up["ma"]) == 6 and len(up["dd"]) == 9
    assert up["ma_dem"][0] == 6 and dn["ma_dem"][2] == 6                    # giá trên / dưới mọi đường trung bình
    assert up["diem"] > dn["diem"] and up["muc"] in ("t", "d") and dn["muc"] in ("g", "d")
    for x in kq:                                                           # điểm = (mua − bán) / số chỉ báo
        mua = sum(1 for z in x["ma"] + x["dd"] if z[2] == 1)
        ban = sum(1 for z in x["ma"] + x["dd"] if z[2] == -1)
        assert abs(x["diem"] - (mua - ban) / x["n"]) < 1e-12
    ngan = _chay(CHUOI + "console.log(JSON.stringify(kt_dong_thuan(tao(120, 0.1))));")
    assert ngan["n"] == 14 and len(ngan["ma"]) == 5                        # chưa đủ 200 nến → không có SMA 200


def test_sau_tru():
    kq = _chay(CHUOI + """
const vni = len.c.map((_, i) => 1000 + 0.2 * i);
const vung = [{loai: "khang_cu", lo: 96, hi: 97, cach: 0.02, cham: 3}, {loai: "ho_tro", lo: 80, hi: 81, cach: 0.15, cham: 2}];
const a = kt_tru(len, {nn: 50, vni, n3: 63, vung}), b = kt_tru(xuong, {nn: -20, rrg: [[99, 97], [98, 96]], vung: []});
console.log(JSON.stringify({a, b}));""")
    a, b = ({t["id"]: t for t in kq[k]} for k in ("a", "b"))
    assert list(a) == ["xu", "dl", "bd", "dt", "rs", "vg"] and all(t["pp"] for t in kq["a"])
    assert a["xu"]["nhan"] in ("Tăng", "Tăng mạnh") and b["xu"]["nhan"] in ("Giảm", "Giảm mạnh")
    assert a["rs"]["nhan"] == "Mạnh hơn thị trường"                        # không RRG → so lãi 3 tháng với VN-Index
    assert b["rs"]["nhan"] == "Tụt hậu" and "RS 98,0" in b["rs"]["so"]     # RRG: cả 2 trục < 100
    assert a["vg"]["nhan"] == "Gần kháng cự" and "Kháng cự 96,00–97,00" in " ".join(a["vg"]["ct"])
    assert b["vg"]["nhan"] == "Chưa đủ dữ liệu"
    assert "Khối ngoại ròng 20 phiên" in " ".join(a["dt"]["ct"])
