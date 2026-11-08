# -*- coding: utf-8 -*-
"""Trang Biểu đồ + công cụ vẽ (docs/ma/bieu_do.js): chạy trong node với biểu đồ / canvas giả – mọi công cụ vẽ không lỗi,
phép tính thông minh (hồi quy, VWAP, hồ sơ khối lượng, xu hướng tự động) đúng, đổi thời gian ↔ vị trí nến khớp."""
import json
import re
import shutil
import subprocess

import numpy as np
import pytest

TRANG, VE = "docs/ma/index.html", "docs/ma/bieu_do.js"

KHUNG_JS = r"""
const LS = {}; globalThis.localStorage = {getItem: k => LS[k] ?? null, setItem: (k, v) => { LS[k] = String(v); }, removeItem: k => { delete LS[k]; }};
globalThis.window = globalThis; globalThis.alert = () => {};
globalThis.document = {addEventListener() {}, body: {contains: () => true}, querySelectorAll: () => [], querySelector: () => null};
globalThis.ST = {khung: "D"};
const so = (v, l = 0) => v == null || !isFinite(v) ? "–" : Number(v).toFixed(l);
const pt = (v, l = 0) => v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + (v * 100).toFixed(l) + "%";
const kl = v => String(Math.round(v)); const esc = s => String(s);
""" + "\n"

CANVAS_JS = r"""
const ctx = new Proxy({}, {get: (o, k) => k === "measureText" ? (() => ({width: 30})) : k in o ? o[k] : () => {}, set: (o, k, v) => { o[k] = v; return true; }});
const target = {useMediaCoordinateSpace: f => f({context: ctx, mediaSize: {width: 1000, height: 500}}), useBitmapCoordinateSpace: f => f({context: ctx, horizontalPixelRatio: 1, verticalPixelRatio: 1})};
let PR = null;
const ts = {logicalToCoordinate: l => l * 4, coordinateToLogical: x => x / 4, getVisibleLogicalRange: () => ({from: 0, to: 250})};
const ch = {timeScale: () => ts, panes: () => [{getHTMLElement: () => null}], applyOptions() {}};
const nen = {priceToCoordinate: v => 500 - v * 8, coordinateToPrice: y => (500 - y) / 8, attachPrimitive(p) { PR = p; }};
const ve = () => PR.paneViews()[0].renderer().draw(target);
"""


def _js(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open(TRANG, encoding="utf-8").read()
    phien_sau = re.search(r"^function phien_sau\(d\) \{.*?^\}", h, re.M | re.S).group(0)
    js = KHUNG_JS + phien_sau + "\n" + open(VE, encoding="utf-8").read() + "\n" + CANVAS_JS + ma_js
    kq = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr[-3000:]
    return json.loads(kq.stdout)


def _nen(n=240, seed=4):
    r = np.random.default_rng(seed)
    c = 30 * np.exp(np.cumsum(r.normal(0.001, 0.015, n)))
    o = c * np.exp(r.normal(0, 0.004, n))
    h = np.maximum(o, c) * 1.01
    l_ = np.minimum(o, c) * 0.99
    v = np.round(1e5 * np.exp(r.normal(0, .3, n)))
    d, t = [], np.datetime64("2025-06-02")
    while len(d) < n:
        if np.is_busday(t):
            d.append(str(t))
        t += np.timedelta64(1, "D")
    return {"d": d, "o": [round(float(z), 3) for z in o], "h": [round(float(z), 3) for z in h], "l": [round(float(z), 3) for z in l_],
            "c": [round(float(z), 3) for z in c], "v": [float(z) for z in v]}


def test_moi_cong_cu_ve_khong_loi_va_tinh_dung():
    x = _nen()
    kq = _js(f"const x = {json.dumps(x)};\n" + r"""
      const n = x.d.length; BD_VE.gan({ch, nen, x, n, ma: "AAA", khung: "D"}, {el: null, tuong_tac: false});
      const T = BD_VE._thu, K = T.KHO; K.AAA = [];
      const vong = []; for (const l of [0, 10.5, 120, n - 1, n + 7]) vong.push(Math.abs(T.t2l(T.l2t(l)) - l));
      const ds = Object.keys(BD_VE.CONG).filter(k => BD_VE.CONG[k].so !== -1);
      ds.forEach((k, i) => { const cg = BD_VE.CONG[k], m = cg.so === 0 ? (cg.tu_do ? 10 : 4) : cg.so, p = [];
        for (let j = 0; j < m; j++) p.push(cg.neo ? {fx: .1 + j * .05, fy: .2} : {t: T.l2t(60 + j * 15 + (i % 5)), v: x.c[100] * (1 + (j % 2 ? .05 : -.05))});
        if (k === "vt_mua") p[1].v = p[0].v * .95; if (k === "vt_ban") p[1].v = p[0].v * 1.05;
        const d = {id: k, c: k, p, s: {}, chu: cg.chu ? "Ghi chú\nhai dòng" : undefined, r: 2}; if (cg.tao) cg.tao(d); K.AAA.push(d); });
      K._cfg.an = false; ve();
      const hq = T.hoi_quy(20, 80), vw = T.vwap(150), hs = T.ho_so_kl(30, 90), tu = T.xu_huong_tu_dong(n - 1);
      console.log(JSON.stringify({so: ds.length, loi: BD_VE._loi, hit: T.HIT.length, vong, hq, vw_cuoi: vw[vw.length - 1], vw_n: vw.length,
        hs_tong: hs.tong.reduce((a, b) => a + b, 0), hs_va: hs.va, hs_poc: hs.poc, tu, ten: ds.map(k => BD_VE.CONG[k].ten)}));
    """)
    assert kq["so"] >= 90 and kq["loi"] == [], kq["loi"]            # ~92 công cụ vẽ, không công cụ nào lỗi
    assert kq["hit"] > 100 and max(kq["vong"]) < 1e-6
    for ten in ("Đường xu hướng", "Chĩa ba Schiff điều chỉnh", "Đường xu hướng tự động", "Quạt Gann", "Mẫu XABCD", "Sóng đẩy Elliott (12345)",
                "Vị thế mua", "VWAP neo", "Volume Profile khoảng cố định", "Bút dạ quang", "Hình chữ nhật xoay", "Chữ neo khung", "Biển chỉ dẫn",
                "Đo giá và thời gian"):
        assert ten in kq["ten"], ten
    c, h, l_, v = (np.array(x[k]) for k in ("c", "h", "l", "v"))
    b, a = np.polyfit(np.arange(61), c[20:81], 1)                     # hồi quy giá đóng cửa
    assert abs(kq["hq"]["b"] - b) < 1e-6 and abs(kq["hq"]["a"] - a) < 1e-6
    sd = np.sqrt(np.mean((c[20:81] - (a + b * np.arange(61))) ** 2))
    assert abs(kq["hq"]["sd"] - sd) < 1e-6
    tp = (h + l_ + c) / 3                                            # VWAP neo từ nến 150 tới cuối
    assert abs(kq["vw_cuoi"]["m"] - (tp[150:] * v[150:]).sum() / v[150:].sum()) < 1e-6 and kq["vw_n"] == len(c) - 150
    assert abs(kq["hs_tong"] - v[30:91].sum()) < 1e-3                # hồ sơ KL: chia hết KL vào các mức giá
    lo, hi = kq["hs_va"]
    assert lo <= kq["hs_poc"] <= hi
    s1, s2, r1, r2 = kq["tu"]                                         # xu hướng tự động: hỗ trợ đi lên, kháng cự đi xuống
    assert s1 is None or s2["v"] > s1["v"]
    assert r1 is None or r2["v"] < r1["v"]


def test_vi_the_1r_2r_va_ket_qua():
    x = _nen(120, 9)
    kq = _js(f"const x = {json.dumps(x)};\n" + r"""
      const n = x.d.length; BD_VE.gan({ch, nen, x, n, ma: "BBB", khung: "D"}, {el: null, tuong_tac: false});
      const T = BD_VE._thu, K = T.KHO, v0 = x.c[60];
      K.BBB = [{id: "a", c: "vt_mua", p: [{t: T.l2t(60), v: v0}, {t: T.l2t(119), v: v0 * 0.97}], s: {}, r: 2}];
      const ghi = []; const goc = ctx.fillText; ctx.fillText = (t) => ghi.push(t); ve();
      console.log(JSON.stringify({ghi, loi: BD_VE._loi}));
    """)
    chu = " | ".join(kq["ghi"])
    assert "1R" in chu and "2R" in chu and "Mục tiêu" in chu and "Cắt lỗ" in chu and "lời/lỗ 2" in chu
    assert any(k in chu for k in ("Đạt mục tiêu sau", "Chạm cắt lỗ sau", "Đang mở"))


def test_trang_bieu_do_va_khung_phut():
    h = open(TRANG, encoding="utf-8").read()
    assert '<a href="#bieu-do">Biểu đồ</a>' in h and 'if (h === "BIEU-DO")' in h and "function bd_trang(" in h
    assert 'sc.src = "bieu_do.js?v=' in h and "function mo_tim_bd(" in h                 # file riêng, tải động; gõ phím → tìm mã
    for k in ('["1", "1m"]', '["5", "5m"]', '["15", "15m"]', '["60", "1H"]', '["1", "1\'"]', '["5", "5\'"]'):
        assert k in h, k
    assert 'lay(DL + `phut/${goc}/${ma}.json?p=${' in h
    v = open(VE, encoding="utf-8").read()
    assert "localStorage.setItem(KHOA" in v and 'KHOA = "ma_hinh_ve_2"' in v and "KHOA_CU" in v       # lưu + chuyển hình vẽ kiểu cũ
    assert not re.search(r"fetch\(|https?://", v)                     # không gọi ra ngoài
    assert not re.search("[\U0001F300-\U0001FAFF★⭐]", v)
    assert "ma/#bieu-do" in open("canh_bao/trang_tong_hop.py", encoding="utf-8").read()


def test_watchlist_co_nhom_tin_hieu_bot():
    """Danh sách mã cạnh biểu đồ: nhóm 'Tín hiệu bot' (khuyến nghị mua phiên tới, kèm vùng mua / cắt lỗ); điện thoại: bảng
    không nằm dưới cột nút bên phải (che giá + nút đóng)."""
    h = open("docs/ma/index.html", encoding="utf-8").read()
    assert 'bot: ["Tín hiệu bot", Object.keys(BOT)]' in h and '["bot", `Tín hiệu bot (${Object.keys(BOT).length})`]' in h
    assert "vùng mua ${so(bt[2], 2)}–${so(bt[3], 2)} · cắt lỗ ${so(bt[4], 2)}" in h and '.dt-nhan.bot{' in h
    assert ".fs .ds-td{position:absolute;left:0;right:44px;" in h


def test_toan_man_hinh_khi_khong_co_fullscreen_api():
    """Safari iPhone không có Element.requestFullscreen → nút ⛶ trang Biểu đồ phủ kín cửa sổ bằng CSS (phu-kin), nút đổi
    '✕ Thu nhỏ'; trình duyệt có API mà từ chối → cũng phủ kín; Esc / bấm lại → thu nhỏ; rời trang → bỏ khoá cuộn."""
    h = open("docs/ma/index.html", encoding="utf-8").read()
    assert ".fs.phu-kin{top:0;z-index:300}body.co-phu-kin{overflow:hidden}" in h
    assert 'if (t.closest("#rail-full")) { fs_toan_man(); return; }' in h and "const req = f.requestFullscreen || f.webkitRequestFullscreen;" in h
    assert "if (!req) return phu();" in h and "if (p?.catch) p.catch(phu);" in h
    assert 'b.title = k ? "Thu nhỏ (Esc)" : "Toàn màn hình"' in h and 'document.body.classList.remove("co-phu-kin");' in h
    assert '<button id="rail-full" title="Toàn màn hình"' in h and "#rail-full{display:none}.fs.trang #rail-full{display:grid}" in h
    assert 'id="fs-full"' not in h                                      # nút chữ trên thanh trên đã chuyển sang cột công cụ


def test_xoay_may_giu_khoang_va_mo_tu_man_hinh_chinh():
    """Xoay máy / đổi cỡ: giữ đúng khoảng nến đang xem (thư viện giữ độ rộng nến → hiện thêm nến); màn hình thấp (điện thoại
    nằm ngang) ở chế độ phủ kín: gọn thanh trên; thêm vào màn hình chính iPhone → mở không có thanh Safari (standalone)."""
    import json
    h = open("docs/ma/index.html", encoding="utf-8").read()
    assert "ts_.subscribeVisibleLogicalRangeChange(r => {" in h and "if (w !== w0 && v0)" in h
    assert "@media (max-height:520px){.fs.phu-kin .fs-tren .ten{display:none}" in h
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in h and '<link rel="manifest" href="manifest.webmanifest">' in h
    assert '<link rel="apple-touch-icon" href="icon-180.png">' in h
    m = json.load(open("docs/ma/manifest.webmanifest", encoding="utf-8"))
    assert m["display"] == "standalone" and m["start_url"] == "./#bieu-do" and m["scope"] == "../"
    for f in ("icon-180.png", "icon-192.png", "icon-512.png"):
        assert open("docs/ma/" + f, "rb").read(8) == b"\x89PNG\r\n\x1a\n"
