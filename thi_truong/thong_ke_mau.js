// THỐNG KÊ MẪU TRÊN RỔ MÃ cho mục "Đọc biểu đồ" (11/2026): chạy CHÍNH các hàm của docs/ma/doc_bd.js (mẫu nến, mẫu hình,
// BOS / CHoCH, FVG, Order Block) trên `top` mã thanh khoản lớn nhất (rổ Quỹ Bứt Phá – loc_quy_b.json hang_gtgd), khung ngày
// từ khi niêm yết (gia_dai). Mỗi loại: tỷ lệ đúng hướng (vào giá mở cửa nến sau, ra sau SAU / SAU_MH nến – y như kiểm thử
// trên mã) so với NỀN = tỷ lệ giá tự đi cùng hướng sau cùng số nến trên CHÍNH mã đó (không cần tín hiệu). Khoảng tin cậy
// Wilson tính với số TUẦN có tín hiệu (tín hiệu dồn cùng tuần không độc lập) → "hơn nền" khi cả khoảng trên nền.
//   node thi_truong/thong_ke_mau.js <thư mục du_lieu> <loc_quy_b.json> [top=100]  → <du_lieu>/thong_ke_mau.json
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");

function nap_doc_bd(file) {                              // doc_bd.js cần vài biến trình duyệt – môi trường tối thiểu
  const g = {window: null, localStorage: {getItem: () => null, setItem() {}}, document: {createElement: () => ({style: {}})},
    requestAnimationFrame: f => f(), console, Math, Date, JSON, Number, String, Array, Object, Set, Map, Promise, isFinite};
  g.window = g; vm.createContext(g); vm.runInContext(fs.readFileSync(file, "utf8"), g);
  return g.BD_DOC._thu;
}
function giai(gd) {                                      // gia_dai gọn → cột theo ngày (như giai_gia_dai của trang)
  if (!gd?.d0 || !gd.c?.length) return null;
  const t = new Date(gd.d0 + "T00:00:00Z");
  const d = gd.g.map(n => { t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); });
  return {d, o: gd.o, h: gd.h, l: gd.l, c: gd.c, v: gd.v || gd.c.map(() => 0)};
}
const tuan = s => { const t = new Date(s + "T00:00:00Z"); t.setUTCDate(t.getUTCDate() - (t.getUTCDay() + 6) % 7); return t.toISOString().slice(0, 10); };
function wilson(k, n, z = 1.96) {
  if (!n) return [null, null];
  const p = k / n, d = 1 + z * z / n, g = p + z * z / (2 * n), e = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
  return [Math.max(0, (g - e) / d), Math.min(1, (g + e) / d)];
}

function chay(du_lieu, loc, top = 100, T = null) {
  T = T || nap_doc_bd(path.join(__dirname, "..", "docs", "ma", "doc_bd.js"));
  const hang = JSON.parse(fs.readFileSync(loc, "utf8")).hang_gtgd || {};
  const ds = Object.keys(hang).sort((a, b) => hang[a] - hang[b]).slice(0, top);
  const SAU = T.SAU, SAU_MH = T.SAU_MH, G = {}, ma_dung = [];
  const them = (khoa, ten, huong, sau, x, i, nen) => {
    if (i + sau >= x.c.length || !(x.o[i + 1] > 0)) return;
    const r = x.c[i + sau] / x.o[i + 1] - 1, z = G[khoa] || (G[khoa] = {ten, huong, sau, n: 0, dung: 0, sr: 0, sn: 0, snr: 0, tuan: new Set(), ma: new Set()});
    z.n++; z.dung += Math.sign(r) === huong ? 1 : 0; z.sr += r; z.sn += nen[sau][huong > 0 ? "len" : "xuong"]; z.snr += nen[sau].tb;
    z.tuan.add(tuan(x.d[i])); z.ma.add(x.ma);
  };
  for (const ma of ds) {
    let gd; try { gd = JSON.parse(fs.readFileSync(path.join(du_lieu, "gia_dai", ma + ".json"), "utf8")); } catch (e) { continue; }
    const x = giai(gd); if (!x || x.c.length < 250) continue;
    x.ma = ma; ma_dung.push(ma);
    const N = x.c.length, A = T.atr(x), nen = {};
    for (const s of [SAU, SAU_MH]) {                     // nền của chính mã: mọi phiên, cùng cách vào / ra
      let len = 0, xuong = 0, n = 0, sr = 0;
      for (let i = 0; i + s < N; i++) if (x.o[i + 1] > 0) { const r = x.c[i + s] / x.o[i + 1] - 1; n++; sr += r; if (r > 0) len++; else if (r < 0) xuong++; }
      nen[s] = {len: n ? len / n : 0.5, xuong: n ? xuong / n : 0.5, tb: n ? sr / n : 0};
    }
    for (const [ten, huong, f] of T.MAU_NEN) for (let i = 6; i < N; i++) { let ok = false; try { ok = f(x, i); } catch (e) { ok = false; } if (ok) them("nen:" + ten, ten, huong, SAU, x, i, nen); }
    for (const g of T.quet_mau_hinh(x, A)) if (g.t != null) them(`mh:${g.loai}:${g.huong}`, g.ten, g.huong, SAU_MH, x, g.t, nen);
    const ct = T.cau_truc(x);
    for (const e of ct.ev) if (!e.dau) them(`ct:${e.loai}:${e.huong}`, `${e.loai} ${e.huong > 0 ? "tăng" : "giảm"}`, e.huong, SAU_MH, x, e.i, nen);
    for (const f of T.fvg(x, A)) if (f.cham != null) them(`fvg:${f.huong}`, `FVG ${f.huong > 0 ? "tăng" : "giảm"}`, f.huong, SAU, x, f.cham, nen);
    for (const o of T.order_block(x, ct.ev)) if (o.cham != null) them(`ob:${o.huong}`, `OB ${o.huong > 0 ? "tăng" : "giảm"}`, o.huong, SAU, x, o.cham, nen);
  }
  const loai = {};
  for (const [k, z] of Object.entries(G)) {
    const tl = z.dung / z.n, nen = z.sn / z.n, ne = Math.min(z.n, z.tuan.size), [lo, hi] = wilson(tl * ne, ne);
    loai[k] = {ten: z.ten, huong: z.huong, sau: z.sau, n: z.n, so_tuan: z.tuan.size, so_ma: z.ma.size, tl: +tl.toFixed(4), lo: +lo.toFixed(4),
      hi: +hi.toFixed(4), nen: +nen.toFixed(4), tb: +(z.sr / z.n).toFixed(5), tb_nen: +(z.snr / z.n).toFixed(5),
      ket_luan: ne < 30 ? "ít mẫu" : lo > nen ? "hơn nền" : hi < nen ? "kém nền" : "như nền"};
  }
  return {cap_nhat: new Date().toISOString().slice(0, 10), so_ma: ma_dung.length, top, sau: SAU, sau_mh: SAU_MH, loai};
}

if (require.main === module) {
  const [du_lieu, loc, top] = process.argv.slice(2);
  const kq = chay(du_lieu, loc, +(top || 100));
  if (kq.so_ma < 20) { console.log(`Thống kê mẫu: chỉ ${kq.so_ma} mã có dữ liệu – giữ file cũ`); process.exit(0); }
  fs.writeFileSync(path.join(du_lieu, "thong_ke_mau.json"), JSON.stringify(kq));
  const dem = {};
  for (const z of Object.values(kq.loai)) dem[z.ket_luan] = (dem[z.ket_luan] || 0) + 1;
  console.log(`Thống kê mẫu: ${kq.so_ma} mã, ${Object.keys(kq.loai).length} loại – ` + Object.entries(dem).map(([k, v]) => `${k} ${v}`).join(" · "));
}
module.exports = {chay, nap_doc_bd, giai, wilson};
