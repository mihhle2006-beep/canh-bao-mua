/* ĐỌC BIỂU ĐỒ (trang Biểu đồ / toàn màn hình) – tổng hợp TỰ ĐỘNG từ dữ liệu giá + dữ liệu hệ thống (không phải AI,
 * không phải khuyến nghị): vùng hỗ trợ / kháng cự (đỉnh / đáy cục bộ gộp theo ATR), xu hướng, mẫu nến kèm BẰNG CHỨNG trên
 * chính mã (bao nhiêu lần xuất hiện, đúng hướng bao nhiêu % sau 5 nến), mẫu hình giá (tam giác, hai đỉnh / hai đáy), điều
 * kiện chọn mã của Quỹ Bứt Phá (he_thong.json – chỉ đạt / chưa đạt, không ngưỡng luật), khuyến nghị bot hiện tại + lịch sử
 * tín hiệu (tin_hieu/<MÃ>.json).
 * Nạp động từ docs/ma/index.html; dùng chung so, pt, esc, ngay_vn, gio_vn, lay, DL, BOT, LIVE, dong_ds, BD_VE. */
(() => {
"use strict";
const CP = window.BD_DOC = {};
const doc_ls = (k, mac) => { try { const v = localStorage.getItem(k); return v == null ? mac : JSON.parse(v); } catch (e) { return mac; } };
const ghi_ls = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
const S = Object.assign({lop: true, kieu: "gon", he: true}, doc_ls("cp_cai_dat", {}));
const luu_s = () => ghi_ls("cp_cai_dat", {lop: S.lop, kieu: S.kieu, he: S.he});
const AN = {};                                          // mã → Set id chú thích đã bỏ (trong phiên xem)

// ---------------------------------------------------------------- PHÂN TÍCH (hàm thuần trên chuỗi nến x = {o,h,l,c,v})
function atr(x, n = 14) {
  const N = x.c.length, o = new Array(N).fill(null); let e = null, s = 0;
  for (let i = 0; i < N; i++) { const tr = i ? Math.max(x.h[i] - x.l[i], Math.abs(x.h[i] - x.c[i - 1]), Math.abs(x.l[i] - x.c[i - 1])) : x.h[i] - x.l[i];
    if (i < n) { s += tr; if (i === n - 1) { e = s / n; o[i] = e; } } else { e = (e * (n - 1) + tr) / n; o[i] = e; } }
  return o;
}
function pivots(x, k = 5, tu = 0) {                     // đỉnh / đáy cục bộ: cao (thấp) nhất trong k nến hai bên
  const cao = [], thap = [], N = x.c.length;
  for (let i = Math.max(k, tu); i < N - k; i++) {
    let a = true, b = true;
    for (let j = i - k; j <= i + k && (a || b); j++) { if (j === i) continue; if (x.h[j] > x.h[i]) a = false; if (x.l[j] < x.l[i]) b = false; }
    if (a) cao.push(i); if (b) thap.push(i);
  }
  return {cao, thap};
}
function vung_gia(x, P, a) {                            // gộp đỉnh / đáy trong 0,6 ATR → vùng (≥ 2 lần chạm)
  const ds = P.cao.map(i => ({i, v: x.h[i]})).concat(P.thap.map(i => ({i, v: x.l[i]}))).sort((p, q) => p.v - q.v), out = [];
  let nhom = [];
  const xong = () => { if (nhom.length >= 2) { const vs = nhom.map(z => z.v), idx = nhom.map(z => z.i).sort((p, q) => p - q);
    let lo = Math.min(...vs), hi = Math.max(...vs); if (hi - lo < 0.2 * a) { lo -= 0.1 * a; hi += 0.1 * a; }
    out.push({lo, hi, cham: nhom.length, idx, cuoi: idx[idx.length - 1], dau: idx[0]}); } nhom = []; };
  for (const p of ds) { if (nhom.length && p.v - nhom[0].v > 0.6 * a) xong(); nhom.push(p); }
  xong();
  return out;
}
const MAU_NEN = [                                        // [tên, hướng (+1 tăng, −1 giảm), hàm phát hiện tại nến i]
  ["Búa", 1, (x, i) => { const b = Math.abs(x.c[i] - x.o[i]), r = x.h[i] - x.l[i], d = Math.min(x.o[i], x.c[i]) - x.l[i], u = x.h[i] - Math.max(x.o[i], x.c[i]);
    return r > 0 && d >= 2 * b && u <= 0.15 * r && b >= 0.03 * r && x.c[i] < x.c[i - 5]; }],
  ["Người treo cổ", -1, (x, i) => { const b = Math.abs(x.c[i] - x.o[i]), r = x.h[i] - x.l[i], d = Math.min(x.o[i], x.c[i]) - x.l[i], u = x.h[i] - Math.max(x.o[i], x.c[i]);
    return r > 0 && d >= 2 * b && u <= 0.15 * r && b >= 0.03 * r && x.c[i] > x.c[i - 5]; }],
  ["Búa ngược", 1, (x, i) => { const b = Math.abs(x.c[i] - x.o[i]), r = x.h[i] - x.l[i], d = Math.min(x.o[i], x.c[i]) - x.l[i], u = x.h[i] - Math.max(x.o[i], x.c[i]);
    return r > 0 && u >= 2 * b && d <= 0.15 * r && b >= 0.03 * r && x.c[i] < x.c[i - 5]; }],
  ["Sao băng", -1, (x, i) => { const b = Math.abs(x.c[i] - x.o[i]), r = x.h[i] - x.l[i], d = Math.min(x.o[i], x.c[i]) - x.l[i], u = x.h[i] - Math.max(x.o[i], x.c[i]);
    return r > 0 && u >= 2 * b && d <= 0.15 * r && b >= 0.03 * r && x.c[i] > x.c[i - 5]; }],
  ["Nhấn chìm tăng", 1, (x, i) => x.c[i - 1] < x.o[i - 1] && x.c[i] > x.o[i] && x.o[i] <= x.c[i - 1] && x.c[i] >= x.o[i - 1] && x.c[i] - x.o[i] > x.o[i - 1] - x.c[i - 1]],
  ["Nhấn chìm giảm", -1, (x, i) => x.c[i - 1] > x.o[i - 1] && x.c[i] < x.o[i] && x.o[i] >= x.c[i - 1] && x.c[i] <= x.o[i - 1] && x.o[i] - x.c[i] > x.c[i - 1] - x.o[i - 1]],
  ["Sao mai", 1, (x, i) => { const b2 = x.o[i - 2] - x.c[i - 2], b1 = Math.abs(x.c[i - 1] - x.o[i - 1]);
    return b2 > 0 && b2 >= 0.6 * (x.h[i - 2] - x.l[i - 2]) && b1 <= 0.3 * b2 && x.c[i] > x.o[i] && x.c[i] >= (x.o[i - 2] + x.c[i - 2]) / 2; }],
  ["Sao hôm", -1, (x, i) => { const b2 = x.c[i - 2] - x.o[i - 2], b1 = Math.abs(x.c[i - 1] - x.o[i - 1]);
    return b2 > 0 && b2 >= 0.6 * (x.h[i - 2] - x.l[i - 2]) && b1 <= 0.3 * b2 && x.c[i] < x.o[i] && x.c[i] <= (x.o[i - 2] + x.c[i - 2]) / 2; }],
  ["Ba chàng lính trắng", 1, (x, i) => [0, 1, 2].every(k => x.c[i - k] > x.o[i - k] && (x.c[i - k] - x.o[i - k]) >= 0.5 * (x.h[i - k] - x.l[i - k])) &&
    x.c[i] > x.c[i - 1] && x.c[i - 1] > x.c[i - 2] && x.o[i] >= x.o[i - 1] && x.o[i - 1] >= x.o[i - 2]],
  ["Ba con quạ đen", -1, (x, i) => [0, 1, 2].every(k => x.c[i - k] < x.o[i - k] && (x.o[i - k] - x.c[i - k]) >= 0.5 * (x.h[i - k] - x.l[i - k])) &&
    x.c[i] < x.c[i - 1] && x.c[i - 1] < x.c[i - 2] && x.o[i] <= x.o[i - 1] && x.o[i - 1] <= x.o[i - 2]],
];
const SAU = 5, SAU_MH = 10, TIN_N = 10, Z = 1.96;
function wilson(k, n) {                                 // khoảng tin cậy 95% (Wilson) của tỷ lệ k / n
  if (!n) return [null, null];
  const p = k / n, d = 1 + Z * Z / n, g = p + Z * Z / (2 * n), e = Z * Math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n));
  return [Math.max(0, (g - e) / d), Math.min(1, (g + e) / d)];
}
const trung_vi = a => { if (!a.length) return null; const b = [...a].sort((p, q) => p - q), m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
function thong_ke(x, ds, huong, sau) {                  // kiểm thử trên chính mã: vào ở giá MỞ CỬA nến sau nến tín hiệu, ra ở giá đóng cửa sau `sau` nến
  const N = x.c.length, r = [];
  for (const i of ds) if (i + sau < N && x.o[i + 1] > 0) r.push(x.c[i + sau] / x.o[i + 1] - 1);
  const dung = r.filter(v => Math.sign(v) === huong).length, [lo, hi] = wilson(dung, r.length);
  return {n: r.length, dung, tl: r.length ? dung / r.length : null, lo, hi, tv: trung_vi(r), tb: r.length ? r.reduce((a, b) => a + b, 0) / r.length : null,
    tin: r.length >= TIN_N && lo > 0.5, sai: r.length >= TIN_N && hi < 0.5};      // đáng tin: cả khoảng tin cậy trên 50%; thường sai: dưới 50%
}
function bang_chung(x, ten, huong) {                    // mẫu nến trên CHÍNH mã: mọi lần xuất hiện → thong_ke sau SAU nến
  const m = MAU_NEN.find(z => z[0] === ten); if (!m) return null;
  const ds = []; for (let i = 6; i < x.c.length; i++) { let ok = false; try { ok = m[2](x, i); } catch (e) {} if (ok) ds.push(i); }
  return thong_ke(x, ds, huong, SAU);
}
function mau_nen_cuoi(x, so_nen = 3) {                  // mẫu nến xuất hiện ở so_nen nến cuối (mới nhất trước)
  const N = x.c.length, out = [];
  for (let i = N - 1; i >= Math.max(6, N - so_nen); i--) for (const [ten, huong, f] of MAU_NEN) { let ok = false; try { ok = f(x, i); } catch (e) {}
    if (ok && !out.some(z => z.ten === ten)) out.push({ten, huong, i, bc: bang_chung(x, ten, huong)}); }
  return out;
}
function duong(x, i1, v1, i2, v2) { return i => v1 + (v2 - v1) * (i - i1) / ((i2 - i1) || 1); }
function pivots_dong(x, k = 5, tu = 0) { return pivots({h: x.c, l: x.c, c: x.c}, k, tu); }   // đỉnh / đáy theo GIÁ ĐÓNG CỬA
function xu_huong(x, P, a) {                            // đường xu hướng theo GIÁ ĐÓNG CỬA (P: pivots_dong): nối 2 đỉnh thấp dần / 2 đáy cao dần
  const N = x.c.length, c = x.c[N - 1], g = x.c, h2 = P.cao.slice(-2), l2 = P.thap.slice(-2);
  const giam = h2.length === 2 && g[h2[1]] < g[h2[0]] - 0.2 * a, tang = l2.length === 2 && g[l2[1]] > g[l2[0]] + 0.2 * a;
  const mo_dau = (ds, cao) => { let k = ds.length - 1; while (k > 0 && (cao ? g[ds[k - 1]] > g[ds[k]] : g[ds[k - 1]] < g[ds[k]])) k--; return ds[k]; };
  const pha = (f, tu, len) => { for (let i = tu + 1; i < N; i++) if (len ? g[i] < f(i) : g[i] > f(i)) return i; return null; };   // nến đóng cửa đầu tiên qua đường
  if (giam && (!tang || h2[1] > l2[1])) { const f = duong(x, h2[0], g[h2[0]], h2[1], g[h2[1]]), ip = pha(f, h2[1], false);
    return {huong: -1, tu: mo_dau(P.cao, true), line: [h2[0], g[h2[0]], h2[1], g[h2[1]]], giu: ip == null, pha: ip, muc: f(N - 1), muc_pha: ip == null ? null : f(ip)}; }
  if (tang) { const f = duong(x, l2[0], g[l2[0]], l2[1], g[l2[1]]), ip = pha(f, l2[1], true);
    return {huong: 1, tu: mo_dau(P.thap, false), line: [l2[0], g[l2[0]], l2[1], g[l2[1]]], giu: ip == null, pha: ip, muc: f(N - 1), muc_pha: ip == null ? null : f(ip)}; }
  void c;
  return {huong: 0};
}
function mau_gia(x, P, a) {                             // tam giác (cân / tăng / giảm), hai đỉnh, hai đáy từ 2 đỉnh + 2 đáy gần nhất
  const N = x.c.length, c = x.c[N - 1], h = P.cao.slice(-2), l = P.thap.slice(-2), out = [];
  if (h.length === 2 && l.length === 2 && Math.min(h[0], l[0]) >= N - 90) {
    const dh = x.h[h[1]] - x.h[h[0]], dl = x.l[l[1]] - x.l[l[0]], phang = z => Math.abs(z) <= 0.5 * a;
    const fh = duong(x, h[0], x.h[h[0]], h[1], x.h[h[1]]), fl = duong(x, l[0], x.l[l[0]], l[1], x.l[l[1]]);
    const trong = c <= fh(N - 1) && c >= fl(N - 1) && fh(N - 1) > fl(N - 1);          // còn trong tam giác (chưa phá)
    let ten = null, huong = 0;
    if (dh < -0.2 * a && dl > 0.2 * a) ten = "Tam giác cân"; else if (phang(dh) && dl > 0.2 * a) { ten = "Tam giác tăng"; huong = 1; } else if (dh < -0.2 * a && phang(dl)) { ten = "Tam giác giảm"; huong = -1; }
    if (ten && trong) out.push({ten, huong, loai: "tam_giac", tren: [h[0], x.h[h[0]], h[1], x.h[h[1]]], duoi: [l[0], x.l[l[0]], l[1], x.l[l[1]]], vuot: fh(N - 1), thung: fl(N - 1)});
  }
  const qua = (tu, f) => { for (let i = tu + 1; i < N; i++) if (f(x.c[i])) return i; return null; };   // nến đầu tiên đóng cửa qua đường cổ
  if (h.length === 2 && Math.abs(x.h[h[1]] - x.h[h[0]]) <= 0.5 * a && h[1] - h[0] >= 8) { const g = P.thap.filter(i => i > h[0] && i < h[1]);
    if (g.length) { const co = Math.min(...g.map(i => x.l[i])), ip = qua(h[1], v => v < co);
      if (c < Math.max(x.h[h[0]], x.h[h[1]]) && (ip == null || N - 1 - ip <= 5))                   // chưa xác nhận, hoặc vừa thủng cổ ≤ 5 nến
        out.push({ten: "Hai đỉnh", huong: -1, loai: "hai", dinh: h, co, thung: ip == null ? co : null, xac_nhan: ip}); } }
  if (l.length === 2 && Math.abs(x.l[l[1]] - x.l[l[0]]) <= 0.5 * a && l[1] - l[0] >= 8) { const g = P.cao.filter(i => i > l[0] && i < l[1]);
    if (g.length) { const co = Math.max(...g.map(i => x.h[i])), ip = qua(l[1], v => v > co);
      if (c > Math.min(x.l[l[0]], x.l[l[1]]) && (ip == null || N - 1 - ip <= 5))
        out.push({ten: "Hai đáy", huong: 1, loai: "hai", dinh: l, co, vuot: ip == null ? co : null, xac_nhan: ip}); } }
  return out;
}
function xen_ke(x, P) {                                 // đỉnh / đáy xen kẽ theo thời gian (2 đỉnh liền → giữ đỉnh cao hơn…)
  const ds = P.cao.map(i => ({i, v: x.h[i], k: "H"})).concat(P.thap.map(i => ({i, v: x.l[i], k: "L"}))).sort((a, b) => a.i - b.i), out = [];
  for (const p of ds) { const q = out[out.length - 1];
    if (q && q.k === p.k) { if (p.k === "H" ? p.v >= q.v : p.v <= q.v) out[out.length - 1] = p; } else if (!q || q.i !== p.i) out.push(p); }
  return out;
}
const K_MH = 3;                                          // đỉnh / đáy cho mẫu hình: cao / thấp nhất trong 3 nến hai bên (biết sau 3 nến)
function quet_mau_hinh(x, A) {                          // → [{loai, ten, huong, t (nến xác nhận) | null, het (nến cuối còn hiệu lực), kich_hoat, vo_hieu, hinh}]
  const N = x.c.length, Q = xen_ke(x, pivots(x, K_MH)), out = [], aa = i => A[i] || A.find(v => v) || x.c[i] * 0.02;
  const cho = (bat_dau, het, kich, vo, len) => {        // tìm nến xác nhận (đóng cửa qua kich(t)) trước khi bị vô hiệu (đóng cửa qua vo(t))
    for (let t = bat_dau; t <= Math.min(N - 1, het); t++) {
      if (len ? x.c[t] > kich(t) : x.c[t] < kich(t)) return {t, vo: false};
      if (len ? x.c[t] < vo(t) : x.c[t] > vo(t)) return {t, vo: true};
    }
    return null;
  };
  // vai – đầu – vai (đỉnh: giảm) / ngược (đáy: tăng): 3 đỉnh, đầu cao nhất, 2 vai gần bằng nhau, đường cổ qua 2 đáy giữa
  for (let j = 0; j + 4 < Q.length; j++) {
    const [v1, d1, dau, d2, v2] = Q.slice(j, j + 5), len = v1.k === "L", s = len ? -1 : 1, a = aa(dau.i);
    if (v1.k !== (len ? "L" : "H") || v2.i - v1.i < 10 || v2.i - v1.i > 150) continue;
    if (!(s * (dau.v - v1.v) > 0.5 * a && s * (dau.v - v2.v) > 0.5 * a && Math.abs(v1.v - v2.v) <= 1.2 * a && Math.abs(d1.v - d2.v) <= 1.5 * a)) continue;
    const co = duong(x, d1.i, d1.v, d2.i, d2.v);
    if (!(s * (v1.v - co(v1.i)) > 0.5 * a && s * (v2.v - co(v2.i)) > 0.5 * a)) continue;
    const kq = cho(v2.i + K_MH, v2.i + 30, co, () => v2.v, len);
    out.push({loai: "vdv", ten: len ? "Vai–đầu–vai ngược" : "Vai–đầu–vai", huong: len ? 1 : -1, t: kq && !kq.vo ? kq.t : null, huy: kq?.vo ? kq.t : null,
      tu: v1.i, biet: v2.i + K_MH, het: kq ? kq.t : v2.i + 30, kich_hoat: co, vo_hieu: v2.v, hinh: {diem: [v1, d1, dau, d2, v2].map(p => [p.i, p.v]), co: [d1.i, d1.v, d2.i, d2.v]}});
  }
  // cờ: cán cờ (≤ 10 nến, ≥ 3 ATR) tới 1 đỉnh / đáy, rồi đi ngang / hồi ≤ 50% cán (3 – 20 nến); xác nhận khi đóng cửa qua đỉnh / đáy của lá cờ
  for (const p of Q) {
    const len = p.k === "H", j = p.i, a = aa(j);
    let s0 = -1; for (let i = Math.max(0, j - 10); i <= j - 3; i++) if (s0 < 0 || (len ? x.l[i] < x.l[s0] : x.h[i] > x.h[s0])) s0 = i;
    if (s0 < 0) continue;
    const can = len ? x.h[j] - x.l[s0] : x.h[s0] - x.l[j]; if (can < 3 * a) continue;
    const giua = len ? x.l[s0] + can / 2 : x.h[s0] - can / 2;
    let cao = -Infinity, thap = Infinity, t = null, huy = null, cuoi = Math.min(N - 1, j + 21);
    for (let i = j + 1; i <= cuoi; i++) {
      if (i >= j + K_MH + 1 && (len ? x.c[i] > cao : x.c[i] < thap)) { t = i; break; }
      if (len ? x.c[i] < giua : x.c[i] > giua) { huy = i; break; }
      cao = Math.max(cao, x.h[i]); thap = Math.min(thap, x.l[i]);
    }
    const het = t ?? huy ?? cuoi;
    out.push({loai: "co", ten: len ? "Cờ tăng" : "Cờ giảm", huong: len ? 1 : -1, t, huy, tu: s0, biet: j + K_MH, het,
      kich_hoat: () => len ? cao : thap, vo_hieu: giua, hinh: {can: [s0, len ? x.l[s0] : x.h[s0], j, len ? x.h[j] : x.l[j]], la: [j + 1, het, thap, cao]}});
  }
  // nêm: 2 đỉnh + 2 đáy gần nhất cùng dốc lên (nêm tăng – giảm giá) / xuống (nêm giảm – tăng giá) và hội tụ
  const da = new Set();
  for (let j = 3; j < Q.length; j++) {
    const cuoi4 = Q.slice(j - 3, j + 1), H = cuoi4.filter(q => q.k === "H"), L = cuoi4.filter(q => q.k === "L");
    if (H.length !== 2 || L.length !== 2) continue;
    const tu = cuoi4[0].i, den = cuoi4[3].i, a = aa(den); if (den - tu < 10 || den - tu > 90) continue;
    const su = (H[1].v - H[0].v) / (H[1].i - H[0].i), sl = (L[1].v - L[0].v) / (L[1].i - L[0].i), nho = 0.03 * a;
    const fu = duong(x, H[0].i, H[0].v, H[1].i, H[1].v), fl = duong(x, L[0].i, L[0].v, L[1].i, L[1].v);
    const rong0 = fu(tu) - fl(tu), rong1 = fu(den) - fl(den);
    let ten = null, len = null;
    if (su < -nho && sl < -nho && su < sl) { ten = "Nêm giảm"; len = true; } else if (su > nho && sl > nho && sl > su) { ten = "Nêm tăng"; len = false; }
    if (!ten || !(rong1 > 0 && rong0 > 1.3 * rong1)) continue;
    const khoa = `${H[0].i}-${L[0].i}`; if (da.has(khoa)) continue; da.add(khoa);
    const kq = cho(den + K_MH, den + 30, len ? fu : fl, len ? fl : fu, len);
    out.push({loai: "nem", ten, huong: len ? 1 : -1, t: kq && !kq.vo ? kq.t : null, huy: kq?.vo ? kq.t : null, tu, biet: den + K_MH,
      het: kq ? kq.t : den + 30, kich_hoat: len ? fu : fl, vo_hieu: len ? fl : fu, hinh: {tren: [H[0].i, H[0].v, H[1].i, H[1].v], duoi: [L[0].i, L[0].v, L[1].i, L[1].v]}});
  }
  return out;
}
function mau_hinh(x, A, gan = 10) {                     // mẫu hình đang hình thành / vừa xác nhận (≤ gan nến) + thống kê các lần xác nhận trên mã
  const N = x.c.length, ds = quet_mau_hinh(x, A), out = [];
  for (const ten of ["Vai–đầu–vai", "Vai–đầu–vai ngược", "Cờ tăng", "Cờ giảm", "Nêm tăng", "Nêm giảm"]) {
    const cung = ds.filter(z => z.ten === ten && z.biet <= N - 1);
    const xn = [...new Set(cung.filter(z => z.t != null).map(z => z.t))].sort((p, q) => p - q);
    const nay = cung.filter(z => (z.t != null && N - 1 - z.t <= gan) || (z.t == null && z.huy == null && z.het >= N - 1)).sort((p, q) => (q.t ?? N) - (p.t ?? N))[0];
    if (!nay) continue;
    const i_kh = nay.t ?? N - 1, kh = typeof nay.kich_hoat === "function" ? nay.kich_hoat(i_kh) : nay.kich_hoat;
    const vh = typeof nay.vo_hieu === "function" ? nay.vo_hieu(i_kh) : nay.vo_hieu;
    out.push({...nay, kich: kh, vo: vh, bc: thong_ke(x, xn.filter(t => t < N - 1), nay.huong, SAU_MH), lan: xn.length});
  }
  return out;
}
// ---- CẤU TRÚC THỊ TRƯỜNG kiểu SMC (định nghĩa công khai, tự viết): BOS / CHoCH + khoảng trống giá FVG – không vẽ lại
function cau_truc(x, k = 3) {                           // đỉnh / đáy cục bộ (k nến hai bên) chỉ dùng từ phiên đã xác nhận (k nến sau)
  const N = x.c.length, P = pivots(x, k), ds = P.cao.map(i => ({i, k: "H"})).concat(P.thap.map(i => ({i, k: "L"}))).sort((a, b) => a.i - b.i);
  const ev = []; let H = null, L = null, xu = 0, j = 0;
  for (let t = 0; t < N; t++) {
    while (j < ds.length && ds[j].i + k <= t) { const p = ds[j++]; if (p.k === "H") H = {i: p.i, v: x.h[p.i], pha: false}; else L = {i: p.i, v: x.l[p.i], pha: false}; }
    if (H && !H.pha && x.c[t] > H.v) { ev.push({loai: xu === -1 ? "CHoCH" : "BOS", huong: 1, i: t, muc: H.v, tu: H.i, dau: xu === 0}); xu = 1; H.pha = true; }
    else if (L && !L.pha && x.c[t] < L.v) { ev.push({loai: xu === 1 ? "CHoCH" : "BOS", huong: -1, i: t, muc: L.v, tu: L.i, dau: xu === 0}); xu = -1; L.pha = true; }
  }
  return {ev, xu, H, L};
}
function fvg(x, A, k_min = 0.1) {                       // FVG 3 nến: đáy nến 3 > đỉnh nến 1 (tăng) / đỉnh nến 3 < đáy nến 1 (giảm), rộng ≥ k_min ATR
  const N = x.c.length, out = [];
  for (let i = 2; i < N; i++) { const a = A[i] || A[N - 1] || 0;
    if (x.l[i] > x.h[i - 2] && x.l[i] - x.h[i - 2] >= k_min * a) out.push({huong: 1, i, tren: x.l[i], duoi: x.h[i - 2]});
    else if (x.h[i] < x.l[i - 2] && x.l[i - 2] - x.h[i] >= k_min * a) out.push({huong: -1, i, tren: x.l[i - 2], duoi: x.h[i]}); }
  for (const f of out) { f.cham = null; f.lap = null;     // cham: lần đầu giá quay lại vùng · lap: giá đi xuyên hết vùng
    for (let j = f.i + 1; j < N; j++) {
      if (f.cham == null && (f.huong > 0 ? x.l[j] <= f.tren : x.h[j] >= f.duoi)) f.cham = j;
      if (f.huong > 0 ? x.l[j] <= f.duoi : x.h[j] >= f.tren) { f.lap = j; break; } } }
  return out;
}
function smc(x, A, gan = 3) {
  const N = x.c.length, ct = cau_truc(x), F = fvg(x, A), tk = {};
  for (const loai of ["BOS", "CHoCH"]) for (const h of [1, -1])
    tk[loai + h] = thong_ke(x, ct.ev.filter(e => !e.dau && e.loai === loai && e.huong === h && e.i < N - 1).map(e => e.i), h, SAU_MH);
  const du = F.filter(f => f.i + 20 < N), tkf = {};
  for (const h of [1, -1]) tkf[h] = thong_ke(x, F.filter(f => f.huong === h && f.cham != null && f.cham < N - 1).map(f => f.cham), h, SAU);
  const c = x.c[N - 1], mo = F.filter(f => f.lap == null && f.i >= N - 150);
  return {ct, ev: ct.ev.slice(-gan), tk, tkf, n_fvg: du.length, lap20: du.length ? du.filter(f => f.lap != null && f.lap - f.i <= 20).length / du.length : null,
    tren: mo.filter(f => f.duoi > c).sort((a, b) => a.duoi - b.duoi), duoi: mo.filter(f => f.tren < c).sort((a, b) => b.tren - a.tren),
    trong: mo.filter(f => f.duoi <= c && f.tren >= c)};
}
function phan_tich(x) {                                 // → {vung, xh, nen, gia, mh, smc, a, N} ; dùng 250 nến gần nhất cho vùng / xu hướng
  const N = x.c.length; if (N < 30) return null;
  const A = atr(x), a = A[N - 1] || (x.h[N - 1] - x.l[N - 1]) || x.c[N - 1] * 0.02, P = pivots(x, 5, Math.max(0, N - 250)), c = x.c[N - 1];
  const vg = vung_gia(x, P, a).map(z => ({...z, loai: z.hi < c ? "ho_tro" : z.lo > c ? "khang_cu" : "trong", cach: z.hi < c ? (c - z.hi) / c : z.lo > c ? (z.lo - c) / c : 0}));
  vg.sort((p, q) => p.cach - q.cach || q.cham - p.cham);
  const gon = S.kieu === "gon";
  return {vung: vg, xh: xu_huong(x, pivots_dong(x, 5, Math.max(0, N - 250)), a), nen: mau_nen_cuoi(x, gon ? 5 : 20), gia: mau_gia(x, P, a), mh: mau_hinh(x, A, gon ? 10 : 30), smc: smc(x, A, gon ? 3 : 8), a, N, c};
}
CP._thu = {atr, pivots, pivots_dong, vung_gia, bang_chung, mau_nen_cuoi, xu_huong, mau_gia, phan_tich, MAU_NEN, wilson, thong_ke, quet_mau_hinh, mau_hinh, cau_truc, fvg, smc};

// ---------------------------------------------------------------- DỮ LIỆU HỆ THỐNG
let HT_P = null; const TH_P = {};
const tai_ht = () => (HT_P = HT_P || lay(DL + "he_thong.json", false).catch(() => null));
const tai_th = ma => (TH_P[ma] = TH_P[ma] || lay(DL + `tin_hieu/${ma}.json`, false).catch(() => null));
function dieu_kien(ht, ma) {                            // điều kiện chọn mã Quỹ Bứt Phá → [{ten, dat (true / false / null = lưu ý / chưa rõ), chu}]
  if (!ht?.ma) return null;                             // he_thong.json chỉ có đạt / chưa đạt (1 / 0 / null) – không ngưỡng, không số liệu so
  const r = ht.ma[ma], san = String(LIVE[ma]?.san || dong_ds(ma).san || "").toUpperCase(), out = [];
  if (!r) return [{ten: "Có trong dữ liệu lọc của hệ thống", dat: false, chu: "mã ngoài rổ HOSE + HNX hoặc chưa đủ dữ liệu"}];
  const o = {}; (ht.cot || []).forEach((k, i) => o[k] = r[i] == null ? null : !!r[i]);
  const ro_chu = v => v === true ? "đạt" : v === false ? "chưa đạt" : "chưa rõ";
  out.push({ten: "Sàn HOSE / HNX", dat: !san || !/UPCOM/.test(san), chu: san || "–"});
  out.push({ten: `Trong rổ thanh khoản tuần (chốt ${ngay_vn(ht.ro_ngay_chot)})`, dat: o.ro, chu: o.ro ? "có trong rổ tuần này" : o.ro === false ? "ngoài rổ tuần này" : "chưa rõ"});
  out.push({ten: "RS 3 tháng chưa quá nóng", dat: o.rs, chu: o.rs === false ? "RS 3 tháng quá nóng – bỏ" : ro_chu(o.rs)});
  out.push({ten: "Không thuộc nhóm biến động mạnh nhất rổ", dat: o.bien_dong, chu: o.bien_dong === false ? "thuộc nhóm biến động mạnh nhất – bỏ" : ro_chu(o.bien_dong)});
  out.push({ten: "Định giá", dat: o.dat == null ? null : o.dat ? null : true, chu: o.dat == null ? "chưa có định giá" : o.dat ? "ĐẮT – vẫn chọn nhưng giảm khối lượng" : "không đắt"});
  const manh = [[o.m_dinh, "sát đỉnh 52 tuần"], [o.m_rs, "RS 3 tháng cao"], [o.m_tk, "thanh khoản tăng"], [o.m_nganh, "ngành mạnh"]];
  out.push({ten: "Tín hiệu MẠNH (đủ thì được dùng suất dự phòng)", dat: o.manh ? true : null,
    chu: (o.manh ? "đủ · " : o.manh === false ? "chưa đủ · " : "") + manh.map(([v, t]) => (v ? "✓ " : v === false ? "✗ " : "? ") + t).join(" · ")});
  const bl = (ht.bo_loc || {})[ma]; if (bl) out.push({ten: `Bộ lọc phiên ${ngay_vn(ht.bo_loc_phien)}`, dat: true, chu: "có trong danh sách mua · " + bl.join(", ")});
  return out;
}

// ---------------------------------------------------------------- LỚP VẼ TRÊN BIỂU ĐỒ
class LopPrim {
  constructor(B) { this.B = B; this.d = null; this.v = [{zOrder: () => "bottom", renderer: () => ({draw: t => this.ve(t, true)})}, {zOrder: () => "top", renderer: () => ({draw: t => this.ve(t, false)})}]; }
  attached(p) { this.req = p.requestUpdate; } paneViews() { return this.v; } updateAllViews() {}
  ve(t, nen) {
    const d = this.d; if (!d) return; const ts = this.B.ch.timeScale(), s = this.B.nen;
    t.useMediaCoordinateSpace(({context: ctx, mediaSize: M}) => {
      const X = l => ts.logicalToCoordinate(l), Y = v => s.priceToCoordinate(v);
      const chu = (x, y, txt, o = {}) => { ctx.save(); ctx.font = `${o.dam ? 600 : 500} ${o.c || 10.5}px Inter,"SF Pro Text",system-ui,-apple-system,Segoe UI,Roboto,sans-serif`; const w = ctx.measureText(txt).width;
        const x0 = Math.max(2, Math.min(o.can === "phai" ? x - w - 8 : o.can === "giua" ? x - w / 2 - 4 : x, M.width - w - 12)), y0 = y - 9; ctx.fillStyle = o.nen || "#ffffffe6"; ctx.strokeStyle = o.vien || "#9aa3af"; ctx.lineWidth = 1;
        ctx.beginPath(); (ctx.roundRect ? ctx.roundRect(x0, y0 + 1, w + 8, 16, 3) : ctx.rect(x0, y0 + 1, w + 8, 16)); ctx.fill(); ctx.stroke(); ctx.fillStyle = o.m || "#1f2430"; ctx.textBaseline = "middle"; ctx.fillText(txt, x0 + 4, y0 + 9.5); ctx.restore(); };
      const tia = (l1, v1, l2, v2, m, w = 1.6, dash = []) => { const a = {x: X(l1), y: Y(v1)}, b = {x: X(l2), y: Y(v2)}; if ([a.x, a.y, b.x, b.y].some(z => z == null)) return null;
        const k = (b.y - a.y) / ((b.x - a.x) || 1), e = {x: M.width, y: a.y + k * (M.width - a.x)}; ctx.save(); ctx.strokeStyle = m; ctx.lineWidth = w; ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(e.x, e.y); ctx.stroke(); ctx.restore(); return a; };
      for (const it of d.items) {
        if (it.an) continue;
        if (it.loai === "vung" && nen) { const y1 = Y(it.hi), y2 = Y(it.lo), x0 = Math.max(0, X(it.dau - 3) ?? 0); if (y1 == null || y2 == null) continue;
          ctx.fillStyle = it.ho_tro ? "rgba(15,138,74,0.10)" : it.trong ? "rgba(232,113,10,0.10)" : "rgba(209,52,43,0.10)"; ctx.fillRect(x0, y1, M.width - x0, Math.max(2, y2 - y1));
          ctx.strokeStyle = it.ho_tro ? "rgba(15,138,74,0.5)" : it.trong ? "rgba(232,113,10,0.5)" : "rgba(209,52,43,0.5)"; ctx.lineWidth = 1; ctx.strokeRect(x0, y1, M.width - x0, Math.max(2, y2 - y1)); }
        if (it.loai === "vung" && !nen) { const y1 = Y(it.hi); if (y1 != null) chu(Math.max(4, X(it.dau - 3) ?? 4), y1 - 1, it.nhan, {vien: it.ho_tro ? "#0f8a4a" : it.trong ? "#e8710a" : "#d1342b"}); }
        if (it.loai === "xh" && !nen) { const [l1, v1, l2, v2] = it.line; const a = tia(l1, v1, l2, v2, it.huong < 0 ? "#d1342b" : "#0f8a4a", 1.8); if (a) chu(a.x + 4, a.y - 14, it.nhan, {vien: it.huong < 0 ? "#d1342b" : "#0f8a4a"}); }
        if (it.loai === "tam_giac" && !nen) { tia(...it.tren, "#9b3fd1", 1.4, [5, 3]); tia(...it.duoi, "#9b3fd1", 1.4, [5, 3]); const y = Y(it.tren[3]); if (y != null) chu(X(it.tren[2]) + 4, y - 14, it.ten, {vien: "#9b3fd1"}); }
        if (it.loai === "hai" && !nen) { const y = Y(it.co); if (y != null) { ctx.save(); ctx.strokeStyle = "#9b3fd1"; ctx.setLineDash([5, 3]); ctx.beginPath(); ctx.moveTo(X(it.dinh[0]), y); ctx.lineTo(M.width, y); ctx.stroke(); ctx.restore(); chu(X(it.dinh[1]) + 4, y + (it.huong < 0 ? 14 : -14), `${it.ten} · cổ ${so(it.co, 2)}`, {vien: "#9b3fd1"}); } }
        if (it.loai === "fvg" && nen) { const f = it.f, x0 = X(f.i - 2), y1 = Y(f.tren), y2 = Y(f.duoi); if (x0 == null || y1 == null || y2 == null) continue;
          ctx.fillStyle = f.huong > 0 ? "rgba(15,138,74,0.13)" : "rgba(209,52,43,0.13)"; ctx.fillRect(x0, y1, M.width - x0, Math.max(1.5, y2 - y1)); }
        if (it.loai === "fvg" && !nen) { const f = it.f, x0 = X(f.i - 2), y1 = Y(f.tren); if (x0 == null || y1 == null) continue;
          chu(x0, y1 - 1, `${it.id} FVG ${f.huong > 0 ? "tăng" : "giảm"}`, {c: 9.5, vien: f.huong > 0 ? "#0f8a4a" : "#d1342b", m: f.huong > 0 ? "#0f6b3a" : "#a3241d"}); }
        if (it.loai === "ct" && !nen) for (const e of it.ds) { const a = X(e.tu), b = X(e.i), y = Y(e.muc); if (a == null || b == null || y == null) continue;
          const m = e.huong > 0 ? "#0f8a4a" : "#d1342b"; ctx.save(); ctx.strokeStyle = m; ctx.lineWidth = 1.2; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(a, y); ctx.lineTo(b, y); ctx.stroke(); ctx.restore();
          ctx.save(); ctx.font = "600 9.5px Inter,system-ui,sans-serif"; ctx.fillStyle = m; ctx.textAlign = "center"; ctx.fillText(e.loai, (a + b) / 2, y + (e.huong > 0 ? -4 : 11)); ctx.restore(); }
        if (it.loai === "mh" && !nen) { const m = it.huong > 0 ? "#0f8a4a" : "#d1342b", H = it.hinh;
          const doan = (l1, v1, l2, v2, w = 1.6, dash = []) => { const a = {x: X(l1), y: Y(v1)}, b = {x: X(l2), y: Y(v2)}; if ([a.x, a.y, b.x, b.y].some(z => z == null)) return null;
            ctx.save(); ctx.strokeStyle = m; ctx.lineWidth = w; ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); ctx.restore(); return a; };
          const f = (q, i) => q[1] + (q[3] - q[1]) * (i - q[0]) / ((q[2] - q[0]) || 1);
          let nhan = null;
          if (it.kieu === "vdv") { for (let k = 0; k + 1 < H.diem.length; k++) doan(...H.diem[k], ...H.diem[k + 1], 1.4); doan(H.co[0], H.co[1], it.het, f(H.co, it.het), 1.4, [5, 3]); nhan = H.diem[2]; }
          if (it.kieu === "nem") { doan(H.tren[0], H.tren[1], it.het, f(H.tren, it.het), 1.4, [5, 3]); doan(H.duoi[0], H.duoi[1], it.het, f(H.duoi, it.het), 1.4, [5, 3]); nhan = [H.tren[0], H.tren[1]]; }
          if (it.kieu === "co") { doan(...H.can, 2); const [i1, i2, lo, hi] = H.la, x1 = X(i1), x2 = X(i2), y1 = Y(hi), y2 = Y(lo);
            if ([x1, x2, y1, y2].every(z => z != null)) { ctx.fillStyle = it.huong > 0 ? "rgba(15,138,74,0.10)" : "rgba(209,52,43,0.10)"; ctx.fillRect(x1, y1, Math.max(2, x2 - x1), Math.max(2, y2 - y1));
              ctx.strokeStyle = m; ctx.lineWidth = 1; ctx.strokeRect(x1, y1, Math.max(2, x2 - x1), Math.max(2, y2 - y1)); } nhan = [H.can[2], H.can[3]]; }
          if (nhan) { const x0 = X(nhan[0]), y0 = Y(nhan[1]); if (x0 != null && y0 != null) chu(x0, y0 + (it.huong > 0 ? 16 : -16), `${it.id} ${it.ten}`, {can: "giua", m, vien: m}); } }
        if (it.loai === "nen" && !nen) { const x = X(it.i), cao = it.huong > 0 ? this.B.x.l[it.i] : this.B.x.h[it.i], y = Y(cao); if (x == null || y == null) continue;
          chu(x, y + (it.huong > 0 ? 18 : -18), it.ten, {can: "giua", m: it.huong > 0 ? "#0f6b3a" : "#a3241d", vien: it.huong > 0 ? "#0f8a4a" : "#d1342b", c: 10}); }
        if (it.loai === "bot" && !nen) { const n = this.B.n, x0 = X(n - 1); if (x0 == null) continue;
          const [, nhom, tu, den, cl, mt1, mt3] = it.r, y1 = Y(den), y2 = Y(tu);
          if (y1 != null && y2 != null) { ctx.fillStyle = "rgba(41,98,255,0.13)"; ctx.fillRect(x0, y1, M.width - x0, Math.max(2, y2 - y1)); chu(x0 + 4, y1 - 2, `Bot ${nhom}: vùng mua ${so(tu, 2)}–${so(den, 2)}`, {vien: "#2962ff", m: "#1f4fa8"}); }
          for (const [v, t_, m] of [[cl, "Cắt lỗ bot", "#d1342b"], [mt1, "Mục tiêu 1R", "#0f8a4a"], [mt3, "Mục tiêu 3R", "#0f8a4a"]]) { const y = Y(v); if (y == null || !v) continue;
            ctx.save(); ctx.strokeStyle = m; ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(M.width, y); ctx.stroke(); ctx.restore(); chu(M.width - 4, y - 1, `${t_} ${so(v, 2)}`, {can: "phai", vien: m, m}); } }
        if (it.loai === "lich_su" && !nen) for (const z of it.ds) { const x = X(z.i), y = Y(this.B.x.l[z.i]); if (x == null || y == null) continue;
          const m = z.kq === "ĐÚNG" ? "#0f8a4a" : z.kq === "SAI" ? "#d1342b" : "#787b86"; ctx.save(); ctx.fillStyle = m; ctx.strokeStyle = "#fff"; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(x, y + 5); ctx.lineTo(x - 5, y + 14); ctx.lineTo(x + 5, y + 14); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.restore(); }
      }
    });
  }
}

const ngay_nen = B => i => B.phut ? new Date(B.x.d[i] * 1000).toISOString().slice(0, 10) : String(B.x.d[i]);   // phút: d đã là giờ VN
function th_loc(B, th) {                                // tín hiệu MUA của bot; tua lại: chỉ tới ngày đang xem, kết quả sau ngày đó coi như đang chờ
  if (!Array.isArray(th)) return [];
  const ds = th.filter(z => z.nhom === "MUA");
  if (!B.tua || !B.n) return ds;
  const den = ngay_nen(B)(B.n - 1);
  return ds.filter(z => z.ngay <= den).map(z => z.ngay_ket_thuc && z.ngay_ket_thuc <= den ? z : {...z, ket_qua: "ĐANG CHỜ", ket_qua_pct: "", giai_thich: "chưa có kết quả tới ngày đang xem"});
}
CP._thu_th = th_loc; CP._dung = (...a) => dung(...a); CP._dk = (...a) => dieu_kien(...a);

// ---------------------------------------------------------------- DỰNG CHÚ THÍCH + LỜI GIẢI THÍCH
const muc_tin = b => !b?.n ? "chưa có lần nào trước trên mã" : b.tin ? "đáng tin" : b.sai ? "thường SAI trên mã này" : b.n < TIN_N ? "chưa đáng tin (ít lần)" : "chưa đáng tin";
const pt1 = v => v == null ? "–" : pt(v, 1);
const bang_tk = (b, sau, ten_n) => !b ? [] : [[ten_n, `${b.n} lần`], [`Đúng hướng sau ${sau} phiên`, b.tl == null ? "–" : `${pt(b.tl, 1, false)} (${pt(b.lo, 1, false)}–${pt(b.hi, 1, false)})`],
  [`Thay đổi trung vị sau ${sau} phiên`, pt1(b.tv)], [`Thay đổi trung bình sau ${sau} phiên`, pt1(b.tb)]];
function dung(B, kq, ht, th) {
  const x = B.x, N = B.n, c = x.c[N - 1], ma = B.ma, an = AN[ma] || (AN[ma] = new Set()), ngay = i => B.phut ? gio_vn(x.d[i]) : ngay_vn(x.d[i]);
  const items = [], cau = [];
  if (kq) {
    const ht_ = kq.vung.filter(z => z.loai === "ho_tro"), kc_ = kq.vung.filter(z => z.loai === "khang_cu"), trong = kq.vung.find(z => z.loai === "trong");
    const chon = S.kieu === "gon" ? [trong, ht_[0], kc_[0]].filter(Boolean) : kq.vung.slice(0, 8);
    chon.forEach((z, k) => { const ten = z.loai === "ho_tro" ? "Hỗ trợ" : z.loai === "khang_cu" ? "Kháng cự" : "Vùng giá hiện tại";
      items.push({id: `Z${k + 1}`, loai: "vung", lo: z.lo, hi: z.hi, dau: z.dau, cuoi: z.cuoi, ho_tro: z.loai === "ho_tro", trong: z.loai === "trong",
        tieu_de: `${ten} ${so(z.lo, 2)}–${so(z.hi, 2)} · ${z.cham} lần chạm`, nhom: "Vùng giá", nhan: `${ten} ${so(z.lo, 2)}–${so(z.hi, 2)}`,
        bang: [["Số lần chạm", `${z.cham} lần`], ["Cách giá hiện tại", z.loai === "trong" ? "đang trong vùng" : pt(z.cach, 1, false)], ["Lần chạm gần nhất cách", `${N - 1 - z.cuoi} nến`]],
        cach: "Đỉnh / đáy cục bộ (5 nến hai bên) gộp trong 0,6 ATR(14)"}); });
    const h0 = ht_[0], k0 = kc_[0];
    const vz = z => `${so(z.lo, 2)}–${so(z.hi, 2)} (${z.cham} lần chạm)`;
    cau.push(trong ? `Giá ${so(c, 2)} đang trong vùng ${vz(trong)}` : h0 && k0 ? `Giá ${so(c, 2)} nằm giữa hỗ trợ ${vz(h0)} và kháng cự ${vz(k0)}`
      : h0 ? `Giá ${so(c, 2)} trên hỗ trợ ${vz(h0)}, phía trên chưa có kháng cự gần` : k0 ? `Giá ${so(c, 2)} dưới kháng cự ${vz(k0)}, phía dưới chưa có hỗ trợ trong 1 năm` : "Chưa có vùng giá đủ 2 lần chạm");
    const xh = kq.xh;
    if (xh.huong) { const ten = xh.huong < 0 ? "giảm" : "tăng", cu = !xh.giu && N - 1 - xh.pha > 5;
      const t = xh.giu ? `Xu hướng ${ten} từ ${ngay(xh.tu)} vẫn giữ (đường xu hướng hôm nay ${so(xh.muc, 2)})`
        : `Xu hướng ${ten} từ ${ngay(xh.tu)} ${cu ? "đã bị phá" : "vừa bị phá"}: ${ngay(xh.pha)} đóng cửa ${xh.huong < 0 ? "vượt lên trên" : "thủng xuống dưới"} đường xu hướng (${so(xh.muc_pha, 2)})`;
      cau.push(t); items.push({id: "T1", loai: "xh", huong: xh.huong, line: xh.line, nhan: `Xu hướng ${ten}${xh.giu ? "" : ` – bị phá ${ngay(xh.pha)}`}`, tieu_de: t, nhom: "Đường xu hướng",
        bang: [["Nối", `${xh.huong < 0 ? "2 đỉnh" : "2 đáy"} ${ngay(xh.line[0])} → ${ngay(xh.line[2])}`], ["Giá trị đường hôm nay", so(xh.muc, 2)], ["Giá so đường", pt(c / xh.muc - 1, 1)]]
          .concat(xh.giu ? [] : [["Bị phá", `${ngay(xh.pha)} · cách ${N - 1 - xh.pha} nến`]]),
        cach: "Nối 2 đỉnh thấp dần (giảm) / 2 đáy cao dần (tăng) gần nhất theo GIÁ ĐÓNG CỬA; giữ khi giá chưa đóng cửa vượt qua"}); }
    else cau.push("Chưa có xu hướng rõ (đỉnh / đáy gần nhất chưa cùng chiều)");
    for (const m of kq.nen) { const b = m.bc, tin = muc_tin(b);
      cau.push(`Mẫu nến ${m.ten} (${m.huong > 0 ? "tăng" : "giảm"}, ${ngay(m.i)}) – ${tin}${b?.n ? `: đúng hướng ${pt(b.tl, 0, false)} trong ${b.n} lần trước trên ${ma}` : ""}`);
      items.push({id: `N${items.filter(z => z.loai === "nen").length + 1}`, loai: "nen", i: m.i, huong: m.huong, ten: m.ten, nhom: "Mẫu nến", tin,
        tieu_de: `${m.ten} (${m.huong > 0 ? "tăng" : "giảm"}) · ${ngay(m.i)}`, bang: bang_tk(b, SAU, "Xuất hiện trên mã"),
        cach: `Bằng chứng: mọi lần mẫu này xuất hiện trong lịch sử ${ma}, vào ở giá mở cửa nến sau, ra sau ${SAU} nến`}); }
    for (const g of kq.mh) { const b = g.bc, tin = muc_tin(b), xn = g.t != null;
      cau.push(`Mẫu hình ${g.ten}${xn ? ` – đã xác nhận ${ngay(g.t)} (${g.huong > 0 ? "vượt" : "thủng"} ${so(g.kich, 2)})` : ` – đang hình thành, ${g.huong > 0 ? "vượt" : "thủng"} ${so(g.kich, 2)} là xác nhận`}` +
        ` – ${tin}${b?.n ? `: đúng hướng ${pt(b.tl, 0, false)} trong ${b.n} lần trên ${ma}` : ""}`);
      items.push({id: `M${items.filter(z => ["tam_giac", "hai", "mh"].includes(z.loai)).length + 1}`, loai: "mh", kieu: g.loai, ten: g.ten, huong: g.huong, hinh: g.hinh,
        tu: g.tu, het: xn ? g.t : B.n - 1, xn, kich: g.kich, vo: g.vo, nhom: "Mẫu hình", tin,
        tieu_de: `${g.ten} · ${xn ? `đã xác nhận ${ngay(g.t)}` : "đang hình thành"}`,
        bang: [[xn ? "Mức kích hoạt đã " + (g.huong > 0 ? "vượt" : "thủng") : "Mức kích hoạt", so(g.kich, 2)], ["Mức vô hiệu của mẫu", so(g.vo, 2)]].concat(bang_tk(b, SAU_MH, "Số lần xác nhận trên mã")),
        cach: ({vdv: "3 đỉnh (đáy), đầu cao (thấp) nhất, 2 vai chênh ≤ 1,2 ATR; xác nhận khi đóng cửa qua đường cổ trong 30 nến, vô hiệu khi qua vai phải",
          co: "Cán cờ ≥ 3 ATR trong ≤ 10 nến, lá cờ 3–20 nến hồi ≤ 50% cán; xác nhận khi đóng cửa qua đỉnh (đáy) lá cờ, vô hiệu khi hồi quá 50%",
          nem: "2 đỉnh + 2 đáy cùng dốc và hội tụ (10–90 nến); xác nhận khi đóng cửa ra khỏi nêm theo hướng ngược độ dốc trong 30 nến"})[g.loai] +
          `. Kiểm thử: mọi lần xác nhận trên ${ma}, vào ở giá mở cửa nến sau, ra sau ${SAU_MH} nến`}); }
    for (const g of kq.gia) {
      cau.push(`Mẫu hình ${g.ten}${g.xac_nhan != null ? ` – đã xác nhận ${ngay(g.xac_nhan)} (${g.huong > 0 ? "vượt" : "thủng"} cổ ${so(g.co, 2)})`
        : g.huong ? (g.huong > 0 ? " (nghiêng tăng, chưa xác nhận)" : " (nghiêng giảm, chưa xác nhận)") : " – chờ phá vỡ"}`);
      items.push({id: `M${items.filter(z => z.loai === "tam_giac" || z.loai === "hai").length + 1}`, ...g, nhom: "Mẫu hình giá", tieu_de: g.ten,
        bang: [g.vuot != null ? ["Xác nhận khi vượt", so(g.vuot, 2)] : null, g.thung != null ? ["Xác nhận khi thủng", so(g.thung, 2)] : null,
          g.xac_nhan != null ? ["Đã xác nhận", ngay(g.xac_nhan)] : null].filter(Boolean),
        cach: g.loai === "tam_giac" ? "2 đỉnh + 2 đáy gần nhất hội tụ (90 nến), giá còn trong tam giác" : "2 đỉnh / đáy chênh ≤ 0,5 ATR, cách ≥ 8 nến; đường cổ = đáy / đỉnh giữa"}); }
    const td = [];
    if (h0) td.push(`thủng ${so(h0.lo, 2)} là mất vùng hỗ trợ`); else if (trong) td.push(`thủng ${so(trong.lo, 2)} là rời vùng`);
    if (k0) td.push(`vượt ${so(k0.hi, 2)} là phá kháng cự`);
    if (xh.huong < 0 && xh.giu) td.push(`vượt ${so(xh.muc, 2)} là phá xu hướng giảm`);
    const sm = kq.smc;
    if (sm?.ev.length) { const e = sm.ev[sm.ev.length - 1], b = sm.tk[e.loai + e.huong], tin = muc_tin(b), ten = h => h > 0 ? "tăng" : "giảm";
      const mo_ta = z => `${z.loai} ${ten(z.huong)} ${ngay(z.i)} (đóng cửa ${z.huong > 0 ? "vượt đỉnh" : "thủng đáy"} ${so(z.muc, 2)})`;
      cau.push(`Cấu trúc thị trường ${sm.ct.xu > 0 ? "tăng" : sm.ct.xu < 0 ? "giảm" : "chưa rõ"}: ${mo_ta(e)} – ${tin}${b?.n ? `: sau ${e.loai} ${ten(e.huong)} trên ${ma} đúng hướng ${pt(b.tl, 0, false)} trong ${b.n} lần (${SAU_MH} phiên)` : ""}`);
      items.push({id: "C1", loai: "ct", huong: sm.ct.xu, ds: sm.ev, tu: sm.ev[0].tu, het: e.i, nhom: "Cấu trúc thị trường", tin,
        tieu_de: `${e.loai} ${ten(e.huong)} · ${ngay(e.i)}`,
        bang: [["Xu hướng cấu trúc", sm.ct.xu > 0 ? "tăng (đỉnh / đáy cao dần)" : sm.ct.xu < 0 ? "giảm (đỉnh / đáy thấp dần)" : "chưa rõ"], ["Sự kiện gần nhất", mo_ta(e)]]
          .concat(sm.ct.H && !sm.ct.H.pha ? [["Đỉnh cấu trúc chờ phá", `${so(sm.ct.H.v, 2)} (${ngay(sm.ct.H.i)})`]] : [])
          .concat(sm.ct.L && !sm.ct.L.pha ? [["Đáy cấu trúc chờ thủng", `${so(sm.ct.L.v, 2)} (${ngay(sm.ct.L.i)})`]] : [])
          .concat(bang_tk(b, SAU_MH, `Số lần ${e.loai} ${ten(e.huong)} trên mã`)),
        cach: `Đỉnh / đáy cục bộ (3 nến hai bên) chỉ dùng sau khi đã xác nhận (không vẽ lại). BOS = đóng cửa phá đỉnh / đáy gần nhất CÙNG chiều xu hướng (tiếp diễn), CHoCH = phá NGƯỢC chiều (đổi xu hướng). Kiểm thử: mọi lần trên ${ma}, vào ở giá mở cửa nến sau, ra sau ${SAU_MH} phiên`});
      if (sm.ct.H && !sm.ct.H.pha) td.push(`vượt ${so(sm.ct.H.v, 2)} là ${sm.ct.xu > 0 ? "BOS" : "CHoCH"} tăng`);
      if (sm.ct.L && !sm.ct.L.pha) td.push(`thủng ${so(sm.ct.L.v, 2)} là ${sm.ct.xu < 0 ? "BOS" : "CHoCH"} giảm`); }
    if (sm) {
      const chon = S.kieu === "gon" ? [sm.trong[0], sm.duoi[0], sm.tren[0]].filter(Boolean) : [...sm.trong, ...sm.duoi, ...sm.tren].slice(0, 6);
      const nhan = f => `${so(f.duoi, 2)}–${so(f.tren, 2)}`;
      if (chon.length) cau.push(`Khoảng trống giá (FVG) chưa lấp: ${[sm.duoi[0] ? `dưới giá ${nhan(sm.duoi[0])}` : "", sm.tren[0] ? `trên giá ${nhan(sm.tren[0])}` : "", sm.trong[0] ? `giá đang trong ${nhan(sm.trong[0])}` : ""].filter(Boolean).join(" · ")}` +
        (sm.lap20 != null ? ` – trên ${ma} ${pt(sm.lap20, 0, false)} FVG bị lấp trong 20 phiên (${sm.n_fvg} lần)` : ""));
      chon.forEach((f, j) => { const b = sm.tkf[f.huong], tin = muc_tin(b);
        items.push({id: `G${j + 1}`, loai: "fvg", huong: f.huong, f, dau: f.i - 2, nhom: "Khoảng trống giá (FVG)", tin,
          tieu_de: `FVG ${f.huong > 0 ? "tăng" : "giảm"} ${nhan(f)} · ${ngay(f.i)}`,
          bang: [["Vị trí", f.duoi > kq.c ? "trên giá (kháng cự)" : f.tren < kq.c ? "dưới giá (hỗ trợ)" : "giá đang trong vùng"], ["Đã chạm lại", f.cham != null ? ngay(f.cham) : "chưa"],
            ["FVG trên mã bị lấp trong 20 phiên", sm.lap20 == null ? "–" : `${pt(sm.lap20, 0, false)} (${sm.n_fvg} lần)`]].concat(bang_tk(b, SAU, "Số lần giá chạm lại FVG cùng chiều")),
          cach: `3 nến: đáy nến 3 cao hơn đỉnh nến 1 (tăng) hoặc đỉnh nến 3 thấp hơn đáy nến 1 (giảm), rộng ≥ 0,1 ATR; "lấp" khi giá đi xuyên hết vùng. Kiểm thử: lần đầu giá quay lại chạm vùng, vào ở giá mở cửa nến sau, ra sau ${SAU} phiên – đúng hướng = bật theo chiều FVG`}); }); }
    for (const g of kq.mh) if (g.t == null) td.push(`${g.huong > 0 ? "vượt" : "thủng"} ${so(g.kich, 2)} xác nhận ${g.ten.toLowerCase()}`);
    for (const g of kq.gia) { if (g.vuot != null && g.huong >= 0) td.push(`vượt ${so(g.vuot, 2)} xác nhận ${g.ten.toLowerCase()}`); if (g.thung != null && g.huong <= 0) td.push(`thủng ${so(g.thung, 2)} xác nhận ${g.ten.toLowerCase()}`); }
    if (td.length) cau.push("Theo dõi: " + [...new Set(td)].slice(0, 3).join(" · "));
  }
  const b = B.tua ? null : BOT[ma];                     // tua lại: không hiện khuyến nghị hôm nay (thông tin "tương lai")
  if (S.he && b) items.push({id: "H1", loai: "bot", r: b, nhom: "Hệ thống", tieu_de: `Bot ${b[1]}: vùng mua ${so(b[2], 2)}–${so(b[3], 2)}`,
    bang: [["Cắt lỗ", so(b[4], 2)], ["Mục tiêu 1R / 3R", `${so(b[5], 2)} / ${so(b[6], 2)}`]], cach: b[7] || "khuyến nghị bot sau tổng kết 15:20"});
  const thm = th_loc(B, th);
  if (S.he && thm.length) {
    const ngay_i = ngay_nen(B), ds = thm.map(z => { let i = -1;      // ngày → nến: khung ngày / tuần / tháng: nến đầu có ngày ≥; khung phút: nến cuối của đúng ngày đó
      if (B.phut) { for (let j = N - 1; j >= 0; j--) if (ngay_i(j) === z.ngay) { i = j; break; } } else i = x.d.findIndex((_, j) => ngay_i(j) >= z.ngay);
      return {i: i < 0 ? null : i, kq: z.ket_qua, chu: "MUA"}; }).filter(z => z.i != null);
    if (ds.length) items.push({id: "H2", loai: "lich_su", ds, nhom: "Hệ thống", tieu_de: `Lịch sử bot báo MUA trên ${ma} (${ds.length} lần trong khung)`, bang: [], cach: "Tam giác nhỏ dưới nến ngày bot báo MUA: xanh = đúng, đỏ = sai, xám = đang chờ"});
  }
  for (const it of items) it.an = an.has(it.id);
  return {items, cau};
}

// ---------------------------------------------------------------- PANEL
const esc_ = s => esc(s);
function panel_html(B, kq, dd, ht, th) {
  const ma = B.ma, x = B.x, dk = dieu_kien(ht, ma), b = B.tua ? null : BOT[ma];
  const muc = dd.items.filter(z => !z.an).length;
  const th_mua = th_loc(B, th);
  const dung = th_mua.filter(z => z.ket_qua === "ĐÚNG").length, sai = th_mua.filter(z => z.ket_qua === "SAI").length, cho = th_mua.length - dung - sai;
  const tb = th_mua.map(z => parseFloat(z.ket_qua_pct)).filter(v => isFinite(v)), tbv = tb.length ? tb.reduce((a, v) => a + v, 0) / tb.length : null;
  const du_dk = dk && dk.slice(0, 4).every(z => z.dat === true), truot = dk && dk.slice(0, 4).some(z => z.dat === false);
  return `<div class="cp-dau"><b>Đọc biểu đồ</b><button class="cp-x" data-cp="dong" title="Đóng">✕</button></div>
  <div class="cp-than">
    <div class="cp-luu">Tổng hợp tự động từ dữ liệu giá và dữ liệu hệ thống – không phải AI, không phải khuyến nghị đầu tư.</div>
    <label class="cp-dong"><input type="checkbox" data-cp="lop"${S.lop ? " checked" : ""}> Hiện chú thích trên biểu đồ</label>
    <label class="cp-dong"><input type="checkbox" data-cp="he"${S.he ? " checked" : ""}> Hiện tín hiệu hệ thống (bot) trên biểu đồ</label>
    <div class="cp-dong"><span class="nut"><button data-cpk="gon" aria-pressed="${S.kieu === "gon"}">Gọn</button><button data-cpk="du" aria-pressed="${S.kieu === "du"}">Đầy đủ</button></span>
      <span class="cp-phu">${S.kieu === "gon" ? "Vùng gần giá, xu hướng, mẫu hình gần đây" : "Mọi vùng giá và mẫu hình tìm được"}</span></div>
    ${kq ? `<h3>${esc_(dd.cau[0])}</h3><p>${dd.cau.slice(1).map(esc_).join("<br>")}</p>` : `<p class="cp-phu">Chưa đủ dữ liệu (cần ≥ 30 nến).</p>`}
    <details class="cp-doc"><summary>Cách đọc</summary><p>Vùng hỗ trợ / kháng cự: các đỉnh, đáy cục bộ (cao / thấp nhất trong 5 nến hai bên) nằm sát nhau (≤ 0,6 ATR) gộp thành vùng; càng nhiều lần chạm càng đáng chú ý.
      Xu hướng: nối 2 đỉnh thấp dần hoặc 2 đáy cao dần gần nhất. Mẫu nến (sau ${SAU} phiên) và mẫu hình cờ, nêm, vai–đầu–vai (sau ${SAU_MH} phiên) được kiểm thử trên chính mã:
      mọi lần xuất hiện / xác nhận trước đây, vào ở giá mở cửa nến sau. Tỷ lệ đúng hướng kèm khoảng tin cậy 95%: "đáng tin" khi ≥ ${TIN_N} lần và cả khoảng nằm trên 50%,
      "thường SAI" khi cả khoảng dưới 50%. Cấu trúc thị trường (kiểu SMC): BOS = phá đỉnh / đáy gần nhất cùng chiều xu hướng, CHoCH = phá ngược chiều;
      FVG = khoảng trống giá 3 nến chưa bị lấp. Tính trên khung đang xem${TUA_CHU()}.</p></details>
    <div class="cp-meta">${esc_(ma)} · ${esc_(B.ten_khung)} · dữ liệu tới ${esc_(B.phut ? gio_vn(x.d[B.n - 1]) : ngay_vn(x.d[B.n - 1]))}</div>
    <button class="cp-tinh" data-cp="tinh">Tính lại bằng chứng</button>
    <h4>HỆ THỐNG</h4>
    <div class="cp-the">${b ? `<b>Bot đang khuyến nghị ${esc_(b[1])}</b><div>Vùng mua ${so(b[2], 2)}–${so(b[3], 2)} · cắt lỗ ${so(b[4], 2)} · mục tiêu ${so(b[5], 2)} / ${so(b[6], 2)}</div>${b[7] ? `<div class="cp-phu">${esc_(b[7])}</div>` : ""}`
      : B.tua ? `<b>Đang tua lại</b><div class="cp-phu">Ẩn khuyến nghị bot hôm nay; điều kiện chọn mã bên dưới là dữ liệu hôm nay, không phải ngày tua.</div>`
      : `<b>Bot chưa có khuyến nghị mua ${esc_(ma)}</b>`}</div>
    ${dk ? `<div class="cp-the"><b>${du_dk ? "Đủ điều kiện chọn mã của Quỹ Bứt Phá" : truot ? "Chưa đủ điều kiện chọn mã của Quỹ Bứt Phá" : "Chưa đủ dữ liệu để kết luận"}</b>
      <div class="cp-phu">${du_dk ? "Còn chờ điểm vào của bot (15', giờ, ATC) – không mua khi chưa có tin MUA." : truot ? "Mã không qua điều kiện dưới đây – bot sẽ không mua mới." : "Một số điều kiện chưa có dữ liệu hôm nay."}</div>
      <table class="cp-bang">${dk.map(z => `<tr><td class="${z.dat === true ? "t" : z.dat === false ? "g" : "m"}">${z.dat === true ? "✓" : z.dat === false ? "✗" : "!"}</td><td>${esc_(z.ten)}<div class="cp-phu">${esc_(z.chu)}</div></td></tr>`).join("")}</table>
      <div class="cp-phu">Dữ liệu lọc phiên ${esc_(ngay_vn(ht.ngay_gia))} (cập nhật ${esc_(ht.cap_nhat)}).</div></div>` : ""}
    ${th_mua.length ? `<div class="cp-the"><b>Bot đã báo MUA ${th_mua.length} lần trên ${esc_(ma)}</b><div>${dung} đúng · ${sai} sai · ${cho} đang chờ${tbv != null ? ` · kết quả TB ${tbv > 0 ? "+" : ""}${so(tbv, 2)}%` : ""}</div>
      <table class="cp-bang">${th_mua.slice(-8).reverse().map(z => `<tr><td class="${z.ket_qua === "ĐÚNG" ? "t" : z.ket_qua === "SAI" ? "g" : "m"}">${z.ket_qua === "ĐÚNG" ? "✓" : z.ket_qua === "SAI" ? "✗" : "…"}</td><td>${esc_(ngay_vn(z.ngay))} · ${esc_(z.khuyen_nghi)} · giá ${esc_(z.gia)}<div class="cp-phu">${esc_(z.giai_thich || z.ket_qua)}${z.ket_qua_pct ? ` (${esc_(z.ket_qua_pct)}%)` : ""}</div></td></tr>`).join("")}</table></div>` : ""}
    <h4>CHÚ THÍCH · ${dd.items.length} · ĐANG HIỆN ${muc}</h4>
    ${dd.items.map(it => `<div class="cp-the cp-ct${it.an ? " an" : ""}" data-cpid="${it.id}"><div class="cp-ct-dau"><i class="cham ${it.loai === "vung" ? (it.ho_tro ? "t" : it.trong ? "cam" : "g") : it.huong > 0 ? "t" : it.huong < 0 ? "g" : "tim"}"></i><span class="cp-id">${it.id}</span><b>${esc_(it.tieu_de)}</b>${it.tin ? `<span class="cp-nhan ${it.tin === "đáng tin" ? "t" : /SAI/.test(it.tin) ? "g" : ""}">${esc_(it.tin.replace(/ \(.*\)| trên mã.*$/g, ""))}</span>` : ""}${S.lop && !it.an && !["bot", "lich_su"].includes(it.loai) ? '<span class="cp-nhan b">trên biểu đồ</span>' : ""}</div>
      <div class="cp-phu">${esc_(it.nhom)}</div>${it.bang.length ? `<table class="cp-bang">${it.bang.map(([a, v]) => `<tr><td>${esc_(a)}</td><td class="so">${esc_(v)}</td></tr>`).join("")}</table>` : ""}
      <div class="cp-cach"><b>Chỉ báo</b> ${esc_(it.cach)}</div>
      <div class="cp-nut"><button data-cpx="${it.id}">Xem trên biểu đồ</button>${["vung", "xh", "tam_giac", "hai", "mh", "fvg", "ct"].includes(it.loai) ? `<button data-cpg="${it.id}">Giữ thành hình vẽ</button>` : ""}<button data-cpb="${it.id}">${it.an ? "Hiện lại" : "Bỏ"}</button></div></div>`).join("")}
  </div>`;
}
let TUA_CHU = () => "";
let HT = null, CUR = null;
CP.ve = async (B, o) => {                               // B: BD_DK; o: {el (khung biểu đồ), panel, mo (đang mở), ten_khung, phut, tua}
  if (!B?.x || !B.ma) return;
  if (!o.mo) {                                          // đóng: bỏ lớp vẽ, hộp tóm tắt, panel
    if (B._cp_prim) { B._cp_prim.d = null; B._cp_prim.req?.(); }
    if (o.panel) { o.panel.hidden = true; o.panel.innerHTML = ""; } CUR = null; return;
  }
  TUA_CHU = () => o.tua ? ` (đang tua lại tới ${o.tua})` : "";
  B.tua = o.tua || null;
  const [ht, th] = await Promise.all([tai_ht(), tai_th(B.ma)]); HT = ht;
  const kq = phan_tich({o: B.x.o.slice(0, B.n), h: B.x.h.slice(0, B.n), l: B.x.l.slice(0, B.n), c: B.x.c.slice(0, B.n), v: B.x.v.slice(0, B.n)});
  B.ten_khung = o.ten_khung || ""; B.phut = !!o.phut;
  const dd = dung(B, kq, ht, th);
  CUR = {B, o, kq, dd, ht, th};
  if (BD_DK !== B) return;
  // lớp vẽ + hộp tóm tắt trên biểu đồ
  if (!B._cp_prim) { B._cp_prim = new LopPrim(B); B.nen.attachPrimitive(B._cp_prim); }
  B._cp_prim.d = S.lop || S.he ? {items: dd.items.filter(it => (S.lop && !["bot", "lich_su"].includes(it.loai)) || (S.he && ["bot", "lich_su"].includes(it.loai)))} : null;
  B._cp_prim.req?.();
  if (o.panel && o.mo) { o.panel.hidden = false; o.panel.innerHTML = panel_html(B, kq, dd, ht, th); gan_panel(o.panel); }
};
function ve_lai() { if (CUR) CP.ve(CUR.B, CUR.o); }
function gan_panel(p) {
  p.onchange = e => { const k = e.target.dataset.cp; if (k === "lop" || k === "he") { S[k] = e.target.checked; luu_s(); ve_lai(); } };
  p.onclick = e => {
    const t = e.target, B = CUR?.B;
    const k = t.closest("[data-cpk]"); if (k) { S.kieu = k.dataset.cpk; luu_s(); return ve_lai(); }
    if (t.closest('[data-cp="dong"]')) return CP.dong?.();
    if (t.closest('[data-cp="tinh"]')) { delete TH_P[B.ma]; HT_P = null; ve_lai(); return; }
    const id = t.closest("[data-cpx],[data-cpg],[data-cpb]"); if (!id || !B) return;
    const it = CUR.dd.items.find(z => z.id === (id.dataset.cpx || id.dataset.cpg || id.dataset.cpb)); if (!it) return;
    if (id.dataset.cpb) { const an = AN[B.ma] || (AN[B.ma] = new Set()); an.has(it.id) ? an.delete(it.id) : an.add(it.id); return ve_lai(); }
    if (id.dataset.cpx) { const ts = B.ch.timeScale(), r = ts.getVisibleLogicalRange(), w = r ? r.to - r.from : 120;
      const a = it.dau ?? it.line?.[0] ?? it.tren?.[0] ?? it.dinh?.[0] ?? it.tu ?? it.i ?? (it.ds?.[0]?.i) ?? B.n - w; ts.setVisibleLogicalRange({from: Math.max(0, Math.min(a - 10, B.n - w)), to: Math.max(a - 10, B.n - w) + w});
      try { B.nen.priceScale().applyOptions({autoScale: true}); } catch (e_) {} return; }
    if (id.dataset.cpg && window.BD_VE?.them_hinh) {
      const T = i => window.BD_VE.t_cua(i);
      if (it.loai === "vung") BD_VE.them_hinh({c: "vung", p: [{t: T(it.dau), v: it.hi}, {t: T(it.dau), v: it.lo}], s: {m: it.ho_tro ? "#0f8a4a" : "#d1342b"}});
      if (it.loai === "xh") BD_VE.them_hinh({c: "tia", p: [{t: T(it.line[0]), v: it.line[1]}, {t: T(it.line[2]), v: it.line[3]}], s: {m: it.huong < 0 ? "#d1342b" : "#0f8a4a"}});
      if (it.loai === "tam_giac") for (const z of [it.tren, it.duoi]) BD_VE.them_hinh({c: "tia", p: [{t: T(z[0]), v: z[1]}, {t: T(z[2]), v: z[3]}], s: {m: "#9b3fd1"}});
      if (it.loai === "hai") BD_VE.them_hinh({c: "tia_ngang", p: [{t: T(it.dinh[0]), v: it.co}], s: {m: "#9b3fd1"}});
      if (it.loai === "fvg") BD_VE.them_hinh({c: "hcn", p: [{t: T(it.f.i - 2), v: it.f.tren}, {t: T(B.n + 10), v: it.f.duoi}], s: {m: it.huong > 0 ? "#0f8a4a" : "#d1342b"}});
      if (it.loai === "ct") for (const e of it.ds) BD_VE.them_hinh({c: "xu_huong", p: [{t: T(e.tu), v: e.muc}, {t: T(e.i), v: e.muc}], s: {m: e.huong > 0 ? "#0f8a4a" : "#d1342b"}});
      if (it.loai === "mh") { const m = it.huong > 0 ? "#0f8a4a" : "#d1342b", H = it.hinh, f = (q, i) => q[1] + (q[3] - q[1]) * (i - q[0]) / ((q[2] - q[0]) || 1);
        const seg = (l1, v1, l2, v2) => BD_VE.them_hinh({c: "xu_huong", p: [{t: T(l1), v: v1}, {t: T(l2), v: v2}], s: {m}});
        if (it.kieu === "vdv") { for (let k = 0; k + 1 < H.diem.length; k++) seg(...H.diem[k], ...H.diem[k + 1]); seg(H.co[0], H.co[1], it.het, f(H.co, it.het)); }
        if (it.kieu === "nem") for (const q of [H.tren, H.duoi]) seg(q[0], q[1], it.het, f(q, it.het));
        if (it.kieu === "co") { seg(...H.can); BD_VE.them_hinh({c: "hcn", p: [{t: T(H.la[0]), v: H.la[3]}, {t: T(H.la[1]), v: H.la[2]}], s: {m}}); } }
      const an = AN[B.ma] || (AN[B.ma] = new Set()); an.add(it.id); ve_lai();
    }
  };
}
})();
