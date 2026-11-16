# -*- coding: utf-8 -*-
"""Tab Kỹ thuật (docs/ma/index.html): đồng thuận 15 chỉ báo + 6 trụ (Xu hướng 5 nhóm, Động lượng phiếu dao động + phân kỳ)
– chạy hàm thuần trong node với chuỗi giá giả."""
import json
import re
import shutil
import subprocess

import pytest


def _chay(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open("docs/ma/index.html", encoding="utf-8").read()
    tro = "\n".join(re.search(rf"^const {t} = .*$", h, re.M).group(0) for t in ("esc", "so", "pt", "mau", "tb", "ngay_vn"))
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
    assert a["xu"]["nhan"] == "Tăng" and b["xu"]["nhan"] == "Giảm"           # đa số 5 nhóm: MA khung · trật tự MA · ADX · mây · SAR
    assert a["xu"]["so"] == "5/5 nhóm tăng" and len(a["xu"]["ct"]) == 5
    for t, nhan in ((a["dl"], "Tích cực"), (b["dl"], "Tiêu cực")):           # động lượng theo đà (VN): RSI ≥ 55 / ≤ 45
        rsi = int(re.search(r"RSI (\d+)", t["so"]).group(1))
        assert t["nhan"] == nhan and (rsi >= 55 if nhan == "Tích cực" else rsi <= 45)
    assert a["rs"]["nhan"] == "Mạnh hơn thị trường"                        # không RRG → so lãi 3 tháng với VN-Index
    assert b["rs"]["nhan"] == "Tụt hậu" and "RS-Ratio 98,0" in b["rs"]["so"]   # RRG: cả 2 trục < 100
    assert a["vg"]["nhan"] == "Gần kháng cự" and "Kháng cự 96,00–97,00" in " ".join(a["vg"]["ct"])
    assert b["vg"]["nhan"] == "Chưa đủ dữ liệu"
    assert "Khối ngoại ròng 20 phiên" in " ".join(a["dt"]["ct"])


def test_o_hieu_suat_va_khoang_thap_cao():
    kq = _chay(CHUOI + """
const k1 = hs_khoang(len, 5), k0 = hs_khoang(len, 0), kd = hs_khoang({d: ["2025-12-30", "2026-01-02"], h: [10, 12], l: [9, 11], c: [9.5, 11.5]}, 8);
console.log(JSON.stringify({lop: [hs_lop(0.3), hs_lop(-0.07), hs_lop(0.01), hs_lop(0), hs_lop(null)], k1, k0, kd, ic: Object.keys(KT_IC).sort()}));""")
    assert kq["lop"] == ["t3", "g2", "t1", "", ""]
    assert "1 năm qua · từ" in kq["k1"] and "THẤP" in kq["k1"] and "Cách đáy" in kq["k1"]
    assert "1 ngày qua" in kq["k0"] and 'left:' in kq["k0"]
    assert "Từ đầu năm · từ 02/01/2026" in kq["kd"] and "THẤP 11,00" in kq["kd"]   # chỉ phiên của năm nay
    assert kq["ic"] == sorted(["xu", "dl", "bd", "dt", "rs", "vg"])               # mỗi trụ (kt_tru id) có biểu tượng


def test_xu_huong_thieu_du_lieu_va_di_ngang():
    kq = _chay(CHUOI + """
const ngan = kt_tru(tao(60, 0.1))[0], it = kt_tru(tao(15, 0.1))[0];
const x = tao(300, 0.15), c = x.c.slice(), N = c.length;           // giữa xu hướng tăng, 30 phiên cuối rơi về MA → nhóm lệch nhau
for (let i = N - 30; i < N; i++) { c[i] = c[N - 31] - (i - N + 31) * 0.55; }
const lech = kt_tru({...x, c, h: c.map(v => v + 0.5), l: c.map(v => v - 0.5)})[0];
console.log(JSON.stringify({ngan, it, lech}));""")
    assert kq["ngan"]["nhan"] == "Tăng" and kq["ngan"]["so"] == "4/4 nhóm tăng"          # < 78 nến: bỏ nhóm Ichimoku
    assert "chưa đủ 78 nến" in kq["ngan"]["ct"][3] and "MA200" not in kq["ngan"]["ct"][1]
    assert kq["it"]["nhan"] == "Chưa đủ dữ liệu"
    s = kq["lech"]
    dau = [z.split("</b>")[0] for z in s["ct"]]                             # phiếu từng nhóm (thẻ <b> đầu dòng)
    v = [("Tăng" in z) - ("Giảm" in z) for z in dau]
    tg, gi = v.count(1), v.count(-1)
    assert s["nhan"] == ("Tăng" if tg * 2 > 5 else "Giảm" if gi * 2 > 5 else "Đi ngang")


def test_phan_ky():
    kq = _chay("""
const nen = (n, f) => Array.from({length: n}, (_, i) => f(i));
const dinh = nen(50, i => i === 20 ? 12 : i === 40 ? 13 : 10), day = nen(50, i => i === 20 ? 8 : i === 40 ? 7 : 10);
const h = nen(50, i => Math.max(dinh[i], 10)), l = nen(50, i => Math.min(day[i], 10));
const r_giam = nen(50, i => i === 20 ? 80 : i === 40 ? 70 : 50), r_tang = nen(50, i => i === 20 ? 20 : i === 40 ? 30 : 50);
const a = kt_phan_ky(dinh, l, r_giam), b = kt_phan_ky(h, day, r_tang), c = kt_phan_ky(dinh, l, r_tang);
const cu = kt_phan_ky(dinh.concat(nen(30, () => 10)), l.concat(nen(30, () => 10)), r_giam.concat(nen(30, () => 50)));
console.log(JSON.stringify({a, b, c, cu}));""")
    assert kq["a"]["giam"] and not kq["a"]["tang"] and kq["a"]["dinh"] == [20, 40]   # giá đỉnh cao dần, RSI đỉnh thấp dần
    assert kq["b"]["tang"] and not kq["b"]["giam"] and kq["b"]["day"] == [20, 40]    # giá đáy thấp dần, RSI đáy cao dần
    assert not kq["c"]["giam"]                                                     # RSI cùng chiều giá → không phân kỳ
    assert not kq["cu"]["giam"]                                                    # đỉnh sau đã quá 25 nến → bỏ


def test_bieu_do_tung_tru():
    kq = _chay(CHUOI + """
const vni = len.c.map((z, i) => 1000 + i), vg = [{loai: "ho_tro", lo: 1, hi: 2}];
const r = Object.fromEntries(["xu", "dl", "bd", "dt", "rs", "vg"].map(id => [id, kt_bd_du(len, id, {vni, vung: vg})]));
const tom = z => ({tren: z.tren.map(a => [a[0], a[2].length]), khung: z.khung.map(k => k.ds.map(a => [a[0], a[2].length, !!a[3]])), ng: z.khung.map(k => k.ng), vung: (z.vung || []).length});
const rs = r.rs.khung[0].ds[0][2];
console.log(JSON.stringify({...Object.fromEntries(Object.entries(r).map(([k, z]) => [k, tom(z)])), rs_dau: rs[300 - 120], rs_cuoi: rs[299], rs_khong: kt_bd_du(len, "rs", {}).khung.length}));""")
    assert [a[0] for a in kq["xu"]["tren"]] == ["MA20", "MA50", "MA200"] and kq["xu"]["ng"] == [[25]]
    assert kq["dl"]["ng"] == [[30, 70], [0]] and kq["dl"]["khung"][1][0][2] is True        # RSI + MACD (histogram cột)
    assert len(kq["bd"]["tren"]) == 3 and kq["dt"]["khung"][0][0][0] == "Khối lượng"
    assert all(n == 300 for z in kq.values() if isinstance(z, dict) for k in z["khung"] for _, n, _c in k)   # đủ độ dài chuỗi nến
    assert abs(kq["rs_dau"] - 100) < 1e-9 and kq["rs_cuoi"] > 100 and kq["rs_khong"] == 0  # chuẩn 100 đầu 120 nến, không VN-Index → bỏ khung
    assert kq["vg"]["vung"] == 1 and kq["xu"]["vung"] == 0


def test_bien_dong_siet_cao_va_beta():
    kq = _chay(CHUOI + """
const mk = c => ({d: c.map((_, i) => String(i)), o: c, h: c.map(v => v * 1.004), l: c.map(v => v * 0.996), c, v: c.map(() => 1e6)});
const on = Array.from({length: 260}, (_, i) => 50 + 3 * Math.sin(i / 2) * (i < 230 ? 1 : 0.6 ** (i - 229)));   // biên co dần
const vot = on.slice(0, 259).concat([on[258] * 1.15]);
const v = Array.from({length: 300}, (_, i) => 1000 * (1 + 0.01 * Math.sin(i * 1.7)));
const c2 = [50]; for (let i = 1; i < 300; i++) c2.push(c2[i - 1] * (1 + 2 * (v[i] / v[i - 1] - 1)));
const hv0 = kt_hv(Array.from({length: 60}, (_, i) => 10 * 1.01 ** i));
console.log(JSON.stringify({siet: kt_tru(mk(on))[2], cao: kt_tru(mk(vot))[2], on: kt_tru(len)[2],
  beta: kt_beta(c2, v), beta_ngan: kt_beta(c2.slice(0, 50), v.slice(0, 50)), hv0: hv0.at(-1), hv_dau: hv0[19]}));""")
    assert kq["siet"]["nhan"] == "Đang siết" and "thấp nhất 120 kỳ" in kq["siet"]["ct"][0]
    assert kq["cao"]["nhan"] == "Biến động cao" and "trên dải trên" in kq["cao"]["ct"][0]
    assert kq["on"]["nhan"] == "Ổn định"
    assert abs(kq["beta"] - 2) < 1e-6 and kq["beta_ngan"] is None              # lãi mã = 2 × lãi chỉ số · thiếu dữ liệu → bỏ
    assert abs(kq["hv0"]) < 1e-9 and kq["hv_dau"] is None                       # tăng đều → độ biến động 0 · chưa đủ 20 kỳ


def test_dong_tien_phieu():
    kq = _chay(CHUOI + """
const x = tao(300, -0.1), v = x.v.slice(), c = x.c.slice(); v[299] = 5e6; c[299] = c[298] - 1;   // phiên cuối giảm, KL đột biến
const ra = kt_tru({...x, v, c, h: c.map(z => z + 0.5), l: c.map(z => z - 0.5)}, {nn: -30, cd: {pt: 0.3, ngay: "13/11/2026"}})[3];
const vao = kt_tru(len, {nn: 12, cd: {pt: 0.62, ngay: "13/11/2026", tam: true}})[3];
const tuan = kt_tru(len)[3];
console.log(JSON.stringify({ra, vao, tuan}));""")
    ra, vao, tuan = kq["ra"], kq["vao"], kq["tuan"]
    assert ra["nhan"] == "Tiền ra" and "(đột biến)" in ra["ct"][0] and "giá giảm" in ra["ct"][0]
    assert "Mua chủ động 30%" in " ".join(ra["ct"]) and "Khối ngoại ròng 20 phiên" in " ".join(ra["ct"])
    assert vao["nhan"] == "Tiền vào" and "(đang giao dịch)" in " ".join(vao["ct"])
    assert not any("Mua chủ động" in z or "Khối ngoại" in z for z in tuan["ct"])   # không có số liệu → không bỏ phiếu


def test_suc_manh_tuong_doi_rs_rrg_cung_nganh():
    kq = _chay(CHUOI + """
const f = o => kt_tru(len, o)[4];
console.log(JSON.stringify({
  manh: f({rs_pt: 85, rrg: [[99, 101], [99.5, 102]], cung: [["AAA", 90], ["BBB", 40]], hang: [2, 7]}),
  trai: f({rs_pt: 80, rrg: [[101, 99], [101, 98]]}),
  yeu: f({rs_pt: 12}),
  tam: f({rs_pt: 50, rrg: [[100.1, 100.2]]})}));""")
    m = kq["manh"]
    assert m["nhan"] == "Cải thiện" and m["muc"] == "t" and m["so"] == "RS 85"           # RS ≥ 70 + RRG cải thiện
    assert "xếp RS 2/7" in m["ct"][-1] and 'href="#AAA/ky-thuat"' in m["ct"][-1]
    assert kq["trai"]["nhan"] == "Trung bình"                                          # RS mạnh nhưng RRG suy yếu
    assert kq["yeu"]["nhan"] == "Yếu hơn thị trường" and kq["yeu"]["muc"] == "g"       # RS < 30, chưa có RRG
    assert kq["tam"]["nhan"] == "Trung bình" and "gần tâm" in " ".join(kq["tam"]["ct"])
