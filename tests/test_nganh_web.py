# -*- coding: utf-8 -*-
"""Trang Ngành (docs/ma/index.html): ngành hôm nay – cây ICB cấp 1 → cấp 2, % gia quyền vốn hoá, P/E gia quyền bỏ mã lỗ."""
import json
import re
import shutil
import subprocess

import pytest


def _chay(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open("docs/ma/index.html", encoding="utf-8").read()
    tro = "\n".join(re.search(rf"^const {t} = .*$", h, re.M).group(0) for t in ("esc", "so", "pt", "mau"))
    a = h[h.index("// ---------------------------------------------------------------- NGÀNH HÔM NAY"):h.index("async function hien_nganh()")]
    kq = subprocess.run(["node", "-e", tro + "\n" + a + "\n" + ma_js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr
    return json.loads(kq.stdout)


def test_nganh_hom_nay():
    kq = _chay("""
const mkt = {nganh: ["Ngân hàng", "Bảo hiểm", "Ngành lạ"], ten: {CCC: "Bảo hiểm C"}, ban_do: {dong: [["DDD", 1, 50]]},
  loc: {cot: ["ma", "san", "nganh", "gia", "pt", "gt", "p5", "p10", "p20"], dong: [
    ["AAA", "HSX", 0, 20, 2, 100, 1, 2, 5], ["BBB", "HSX", 0, 10, -1, 50, 0, 0, 0], ["EEE", "HNX", 0, 5, 0, 1, null, null, null],
    ["CCC", "HNX", 1, 30, 1, 10, 0, 0, 0], ["DDD", "UPCOM", 1, 8, -2, 2, 0, 0, 0], ["FFF", "HSX", 2, 9, 3, 5, 0, 0, 0], ["GGG", "HSX", 0, 0, 0, 0, 0, 0, 0]]}};
const ds = [{ma: "AAA", ten: "Ngân hàng A", von: 300, pe: 10, rs: 80}, {ma: "BBB", von: 100, pe: -4}, {ma: "EEE", von: 0},
  {ma: "CCC", von: 150, pe: 15}, {ma: "FFF", von: 10, pe: 5}];
const T = ng_tinh(mkt, ds), nh = T.l2.find(x => x.ten === "Ngân hàng"), tc = T.l1.find(x => x.ten === "Tài chính");
console.log(JSON.stringify({nh, tc: {...tc, con: tc.con.map(x => x.ten), ma: tc.ma.length}, l1: T.l1.map(x => x.ten),
  sp: ng_spark(nh.ma[0]), sp0: ng_spark(nh.ma[2]), trong: ng_tinh(null, ds)}));""")
    nh, tc = kq["nh"], kq["tc"]
    assert [x["ma"] for x in nh["ma"]] == ["AAA", "BBB", "EEE"]                 # bỏ mã giá 0, xếp vốn hoá giảm dần
    assert abs(nh["pt"] - (2 * 300 - 1 * 100) / 400 / 100) < 1e-12              # % gia quyền vốn hoá (mã không vốn hoá: bỏ khỏi bình quân)
    assert (nh["t"], nh["g"], nh["d"], nh["gt"]) == (1, 1, 1, 151)
    assert nh["pe"] == 10                                                        # P/E gia quyền: bỏ mã lỗ (P/E âm)
    assert nh["ma"][0]["ten"] == "Ngân hàng A" and nh["ma"][0]["rs"] == 80
    assert tc["con"] == ["Ngân hàng", "Bảo hiểm"] and tc["ma"] == 5 and tc["cap"] == 1
    assert abs(tc["pe"] - (300 + 150) / (300 / 10 + 150 / 15)) < 1e-12
    bh = [x for x in kq["l1"]]
    assert bh[-1] == "Khác" and "Tài chính" in bh                               # ngành cấp 2 chưa xếp → nhóm Khác
    assert kq["sp"].count(",") == 4 and "polyline" in kq["sp"] and kq["sp0"] == ""   # 4 điểm 20/10/5 phiên → nay · thiếu số: bỏ
    assert kq["trong"] == {"l1": [], "l2": []}
