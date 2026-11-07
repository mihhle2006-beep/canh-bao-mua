# -*- coding: utf-8 -*-
"""Mục "Đọc biểu đồ" (docs/ma/doc_bd.js) chạy trong node với biểu đồ / canvas giả: vùng hỗ trợ, xu hướng (+ ngày bị phá),
mẫu nến kèm bằng chứng trên chính mã, điều kiện chọn mã Quỹ Bứt Phá, tín hiệu bot (tua lại: không lộ thông tin sau ngày xem),
panel + lớp vẽ không lỗi; trang gắn nút / panel / tua lại."""
import json
import re
import shutil
import subprocess

import pytest

JS = "docs/ma/doc_bd.js"
KHUNG = r"""
globalThis.window = globalThis; globalThis.localStorage = {getItem: () => null, setItem() {}};
globalThis.requestAnimationFrame = f => f();
const mk = () => ({style: {}, className: "", innerHTML: "", appendChild() {}, remove() {}, querySelector: () => null});
globalThis.document = {createElement: mk};
globalThis.so = (v, l = 0) => v == null || !isFinite(v) ? "–" : Number(v).toFixed(l);
globalThis.pt = (v, l = 0, dau = true) => v == null || !isFinite(v) ? "–" : (dau && v > 0 ? "+" : "") + (v * 100).toFixed(l) + "%";
globalThis.esc = s => String(s).replace(/</g, "&lt;"); globalThis.ngay_vn = d => String(d); globalThis.gio_vn = s => String(s);
globalThis.DL = ""; globalThis.LIVE = {}; globalThis.dong_ds = () => ({}); globalThis.BOT = {};
globalThis.lay = async u => DATA[u] ?? null;
const ctx = new Proxy({}, {get: (o, k) => k === "measureText" ? (() => ({width: 30})) : k in o ? o[k] : () => {}, set: (o, k, v) => { o[k] = v; return true; }});
const target = {useMediaCoordinateSpace: f => f({context: ctx, mediaSize: {width: 1000, height: 500}})};
let PR = null;
const ts = {logicalToCoordinate: l => l * 4, getVisibleLogicalRange: () => ({from: 0, to: 250}), setVisibleLogicalRange() {}};
const ch = {timeScale: () => ts, panes: () => [{getHeight: () => 400}]};
const nen = {priceToCoordinate: v => 500 - v * 8, attachPrimitive(p) { PR = p; }, priceScale: () => ({applyOptions() {}})};
"""


def _chuoi():
    """Giá dao động quanh 10–12 (đáy 10 chạm nhiều lần), 6 nến cuối: xu hướng giảm ngắn rồi nến nhấn chìm tăng."""
    d, o, h, l_, c = [], [], [], [], []
    import datetime as dt
    t = dt.date(2025, 1, 1)
    for i in range(160):
        while t.weekday() >= 5:
            t += dt.timedelta(days=1)
        k = i % 20
        gia = 10.2 + (k if k <= 10 else 20 - k) * 0.18                       # răng cưa: đáy ~10.2 mỗi 20 phiên
        d.append(t.isoformat()); o.append(round(gia + 0.05, 3)); c.append(round(gia, 3))
        h.append(round(gia + 0.15, 3)); l_.append(round(gia - 0.15, 3))
        t += dt.timedelta(days=1)
    o[-2], c[-2], h[-2], l_[-2] = 10.6, 10.4, 10.65, 10.35                   # nến giảm
    o[-1], c[-1], h[-1], l_[-1] = 10.35, 10.75, 10.8, 10.3                   # nhấn chìm tăng
    return {"d": d, "o": o, "h": h, "l": l_, "c": c, "v": [1000] * len(d)}


def _chay(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    js = KHUNG + open(JS, encoding="utf-8").read() + "\n" + ma_js
    kq = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr[-3000:]
    return json.loads(kq.stdout)


def test_phan_tich_va_panel():
    x = _chuoi()
    ht = {"ngay_gia": "2025-08-01", "ro_ngay_chot": "2025-07-25", "cap_nhat": "x",
          "cot": ["ro", "rs", "bien_dong", "dat", "m_dinh", "m_rs", "m_tk", "m_nganh", "manh"],
          "ma": {"AAA": [0, 0, 0, 1, 0, 1, None, 0, 0], "BBB": [1, 1, 1, 0, 1, 1, 1, 0, 1]}, "bo_loc": {}}
    th = [{"ngay": x["d"][100], "nhom": "MUA", "ket_qua": "ĐÚNG", "ket_qua_pct": "5", "ngay_ket_thuc": x["d"][110], "khuyen_nghi": "MUA", "gia": "10"},
          {"ngay": x["d"][150], "nhom": "MUA", "ket_qua": "SAI", "ket_qua_pct": "-4", "ngay_ket_thuc": x["d"][158], "khuyen_nghi": "MUA", "gia": "11"},
          {"ngay": x["d"][120], "nhom": "CHỜ", "ket_qua": "SAI", "ngay_ket_thuc": x["d"][125]}]
    kq = _chay(f"const x = {json.dumps(x)}; const DATA = {{'he_thong.json': {json.dumps(ht)}, 'tin_hieu/AAA.json': {json.dumps(th)}}};\n" + r"""
      const CP = window.BD_DOC, T = CP._thu, n = x.d.length;
      BOT.AAA = ["AAA", "Mua mới", 10.5, 10.8, 10.1, 11.2, 12.4, "lý do <b>"];
      const B = {ch, nen, x, n, ma: "AAA"}; globalThis.BD_DK = B;
      const kq = T.phan_tich(x);
      const panel = {hidden: true, innerHTML: ""};
      (async () => {
        await CP.ve(B, {el: mk(), panel, mo: true, ten_khung: "khung ngày"});
        PR.paneViews().forEach(v => v.renderer().draw(target));
        const p1 = panel.innerHTML, lop = PR.d.items.map(i => i.loai);
        const tua = CP._thu_th({x, n: 155, tua: "x"}, DATA["tin_hieu/AAA.json"]);
        await CP.ve(B, {el: mk(), panel, mo: false});
        console.log(JSON.stringify({vung: kq.vung.slice(0, 3), nen: kq.nen, xh: kq.xh, p1, an: panel.hidden, lop, con: PR.d, tua,
          dk: CP._dk(DATA["he_thong.json"], "AAA"), dk_b: CP._dk(DATA["he_thong.json"], "BBB"), dk_ngoai: CP._dk(DATA["he_thong.json"], "ZZZ")}));
      })();
    """)
    ho_tro = [z for z in kq["vung"] if z["loai"] == "ho_tro"]
    assert ho_tro and ho_tro[0]["lo"] <= 10.1 <= ho_tro[0]["hi"] + 0.2 and ho_tro[0]["cham"] >= 3      # đáy ~10,05 chạm nhiều lần
    nen = {z["ten"]: z for z in kq["nen"]}
    assert "Nhấn chìm tăng" in nen and nen["Nhấn chìm tăng"]["bc"]["n"] >= 0                      # có bằng chứng (đếm trên chính mã)
    p = kq["p1"]
    assert "Đọc biểu đồ" in p and "Copilot" not in p and "không phải khuyến nghị" in p
    assert "Chưa đủ điều kiện chọn mã của Quỹ Bứt Phá" in p and "Bot đang khuyến nghị Mua mới" in p and "lý do &lt;b>" in p
    assert "Bot đã báo MUA 2 lần" in p and "1 đúng · 1 sai" in p                                     # nhóm CHỜ không tính
    assert "bot" in kq["lop"] and "lich_su" in kq["lop"] and "vung" in kq["lop"]
    assert kq["an"] is True and kq["con"] is None                                                   # đóng: bỏ panel + lớp vẽ
    dk = {z["ten"].split(" (")[0]: z for z in kq["dk"]}
    assert dk["Trong rổ thanh khoản tuần"]["dat"] is False and dk["RS 3 tháng chưa quá nóng"]["dat"] is False
    assert dk["Không thuộc nhóm biến động mạnh nhất rổ"]["dat"] is False and dk["Định giá"]["dat"] is None   # đắt: lưu ý (giảm KL)
    assert "? thanh khoản tăng" in dk["Tín hiệu MẠNH"]["chu"] and "✓ RS 3 tháng cao" in dk["Tín hiệu MẠNH"]["chu"]
    assert [z["dat"] for z in kq["dk_b"]][1:6] == [True, True, True, True, True]
    assert kq["dk_ngoai"][0]["dat"] is False
    assert not re.search(r"top \d|hạng < ?\d|ngưỡng|½|QUY_", p)                                    # không lộ ngưỡng luật
    # tua lại tới nến 154: tín hiệu nến 150 chưa có kết quả (kết thúc nến 158) → đang chờ; tín hiệu nến 100 giữ kết quả
    assert [z["ket_qua"] for z in kq["tua"]] == ["ĐÚNG", "ĐANG CHỜ"]


def test_xu_huong_bi_pha():
    kq = _chay(r"""
      const T = window.BD_DOC._thu, N = 120, x = {o: [], h: [], l: [], c: [], v: []};
      for (let i = 0; i < N; i++) { const g = 20 - i * 0.05 + 1.2 * Math.sin(i / 4); x.c.push(g); x.o.push(g + .05); x.h.push(g + .2); x.l.push(g - .2); x.v.push(1); }
      for (let i = N - 3; i < N; i++) { x.c[i] = 21 + i * .01; x.o[i] = x.c[i] - .1; x.h[i] = x.c[i] + .2; x.l[i] = x.c[i] - .3; }   // 3 nến cuối vượt lên
      const P = T.pivots(x, 5), a = T.atr(x)[N - 1], xh = T.xu_huong(x, P, a);
      console.log(JSON.stringify({xh, N}));
    """)
    xh = kq["xh"]
    assert xh["huong"] == -1 and xh["giu"] is False and kq["N"] - 3 <= xh["pha"] < kq["N"]        # đường xu hướng giảm bị phá ở 3 nến cuối


def test_trang_gan_doc_bieu_do_va_tua_lai():
    h = open("docs/ma/index.html", encoding="utf-8").read()
    assert 'sc.src = "doc_bd.js?v=' in h and 'id="rail-cp"' in h and '<aside class="cp" id="cp" hidden' in h
    assert "Copilot" not in h and "Copilot" not in open(JS, encoding="utf-8").read()
    for k in ("const TUA = {", "function tua_buoc(", "ch.subscribeClick(", 'data-tuak="lui"', 'data-tuak="chay"', 'data-tuak="thoat"', "↺ Tua lại"):
        assert k in h, k
    v = open(JS, encoding="utf-8").read()
    assert not re.search(r"fetch\(|https?://", v) and not re.search("[\U0001F300-\U0001FAFF★⭐]", v)
    assert "VE.them_hinh = " in open("docs/ma/bieu_do.js", encoding="utf-8").read()
