/* ĐỌC BIỂU ĐỒ (trang Biểu đồ / toàn màn hình) – tổng hợp TỰ ĐỘNG từ dữ liệu giá + dữ liệu hệ thống (không phải AI,
 * không phải khuyến nghị): vùng hỗ trợ / kháng cự (đỉnh / đáy cục bộ gộp theo ATR), xu hướng, mẫu nến kèm BẰNG CHỨNG trên
 * chính mã (bao nhiêu lần xuất hiện, đúng hướng bao nhiêu % sau 5 nến), mẫu hình giá (tam giác, hai đỉnh / hai đáy), điều
 * kiện chọn mã của Quỹ Bứt Phá (he_thong.json), khuyến nghị bot hiện tại + lịch sử tín hiệu (tin_hieu/<MÃ>.json).
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
const SAU = 5, TIN_N = 10, TIN_TL = 0.58;
function bang_chung(x, ten, huong) {                    // mẫu nến trên CHÍNH mã: số lần, % đúng hướng sau SAU nến, lãi TB
  const m = MAU_NEN.find(z => z[0] === ten); if (!m) return null;
  const N = x.c.length, r = [];
  for (let i = 6; i < N - SAU; i++) { let ok = false; try { ok = m[2](x, i); } catch (e) {} if (ok) r.push(x.c[i + SAU] / x.c[i] - 1); }
  const dung = r.filter(v => Math.sign(v) === huong).length;
  return {n: r.length, dung, tl: r.length ? dung / r.length : null, tb: r.length ? r.reduce((a, b) => a + b, 0) / r.length : null,
    tin: r.length >= TIN_N && dung / r.length >= TIN_TL};
}
function mau_nen_cuoi(x, so_nen = 3) {                  // mẫu nến xuất hiện ở so_nen nến cuối (mới nhất trước)
  const N = x.c.length, out = [];
  for (let i = N - 1; i >= Math.max(6, N - so_nen); i--) for (const [ten, huong, f] of MAU_NEN) { let ok = false; try { ok = f(x, i); } catch (e) {}
    if (ok && !out.some(z => z.ten === ten)) out.push({ten, huong, i, bc: bang_chung(x, ten, huong)}); }
  return out;
}
function duong(x, i1, v1, i2, v2) { return i => v1 + (v2 - v1) * (i - i1) / ((i2 - i1) || 1); }
function xu_huong(x, P, a) {
  const N = x.c.length, c = x.c[N - 1], h = P.cao.slice(-3), l = P.thap.slice(-3);
  const h2 = h.slice(-2), l2 = l.slice(-2);
  const giam = h2.length === 2 && x.h[h2[1]] < x.h[h2[0]] - 0.2 * a, tang = l2.length === 2 && x.l[l2[1]] > x.l[l2[0]] + 0.2 * a;
  const mo_dau = (ds, cao) => { let k = ds.length - 1; const arr = cao ? x.h : x.l; while (k > 0 && (cao ? arr[ds[k - 1]] > arr[ds[k]] : arr[ds[k - 1]] < arr[ds[k]])) k--; return ds[k]; };
  const pha = (f, tu, len) => { for (let i = tu + 1; i < N; i++) if (len ? x.c[i] < f(i) : x.c[i] > f(i)) return i; return null; };   // nến đóng cửa đầu tiên qua đường
  if (giam && (!tang || h2[1] > l2[1])) { const f = duong(x, h2[0], x.h[h2[0]], h2[1], x.h[h2[1]]), ip = pha(f, h2[1], false);
    return {huong: -1, tu: mo_dau(P.cao, true), line: [h2[0], x.h[h2[0]], h2[1], x.h[h2[1]]], giu: ip == null, pha: ip, muc: f(N - 1), muc_pha: ip == null ? null : f(ip)}; }
  if (tang) { const f = duong(x, l2[0], x.l[l2[0]], l2[1], x.l[l2[1]]), ip = pha(f, l2[1], true);
    return {huong: 1, tu: mo_dau(P.thap, false), line: [l2[0], x.l[l2[0]], l2[1], x.l[l2[1]]], giu: ip == null, pha: ip, muc: f(N - 1), muc_pha: ip == null ? null : f(ip)}; }
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
function phan_tich(x) {                                 // → {vung, xh, nen, gia, a, N} ; dùng 250 nến gần nhất cho vùng / xu hướng
  const N = x.c.length; if (N < 30) return null;
  const A = atr(x), a = A[N - 1] || (x.h[N - 1] - x.l[N - 1]) || x.c[N - 1] * 0.02, P = pivots(x, 5, Math.max(0, N - 250)), c = x.c[N - 1];
  const vg = vung_gia(x, P, a).map(z => ({...z, loai: z.hi < c ? "ho_tro" : z.lo > c ? "khang_cu" : "trong", cach: z.hi < c ? (c - z.hi) / c : z.lo > c ? (z.lo - c) / c : 0}));
  vg.sort((p, q) => p.cach - q.cach || q.cham - p.cham);
  return {vung: vg, xh: xu_huong(x, P, a), nen: mau_nen_cuoi(x), gia: mau_gia(x, P, a), a, N, c};
}
CP._thu = {atr, pivots, vung_gia, bang_chung, mau_nen_cuoi, xu_huong, mau_gia, phan_tich, MAU_NEN};

// ---------------------------------------------------------------- DỮ LIỆU HỆ THỐNG
let HT_P = null; const TH_P = {};
const tai_ht = () => (HT_P = HT_P || lay(DL + "he_thong.json", false).catch(() => null));
const tai_th = ma => (TH_P[ma] = TH_P[ma] || lay(DL + `tin_hieu/${ma}.json`, false).catch(() => null));
function dieu_kien(ht, ma) {                            // điều kiện chọn mã Quỹ Bứt Phá → [{ten, dat (true / false / null = lưu ý), chu}]
  if (!ht?.ma) return null;
  const r = ht.ma[ma], ng = ht.nguong || {}, san = String(LIVE[ma]?.san || dong_ds(ma).san || "").toUpperCase(), out = [];
  if (!r) return [{ten: "Có trong dữ liệu lọc của hệ thống", dat: false, chu: "mã ngoài rổ HOSE + HNX hoặc chưa đủ dữ liệu"}];
  const [hr, hg, gt, rs, bd, dg, dinh, tk, rsn] = r;
  out.push({ten: "Sàn HOSE / HNX", dat: !san || !/UPCOM/.test(san), chu: san || "–"});
  out.push({ten: `Trong rổ thanh khoản tuần (top ${ng.QUY_TOP_GTGD} GTGD TB20, chốt ${ngay_vn(ht.ro_ngay_chot)})`, dat: hr != null,
    chu: hr != null ? `hạng ${hr}` : `hạng GTGD ${hg ?? "–"}${gt != null ? ` · ${so(gt, 1)} tỷ / phiên` : ""}`});
  out.push({ten: `RS 3 tháng chưa quá nóng (hạng < ${ng.QUY_RS3T_NONG})`, dat: rs == null ? null : rs < ng.QUY_RS3T_NONG, chu: rs == null ? "–" : `hạng ${so(rs, 0)}/100`});
  out.push({ten: `Không thuộc ${ng.QUY_BO_BIEN_DONG_PCT}% mã biến động mạnh nhất (60 phiên)`, dat: bd == null ? null : bd * 100 > ng.QUY_BO_BIEN_DONG_PCT,
    chu: bd == null ? "–" : `nằm ở top ${so(bd * 100, 0)}% biến động mạnh nhất (bỏ nếu ≤ top ${ng.QUY_BO_BIEN_DONG_PCT}%)`});
  out.push({ten: "Định giá (đắt → mua ½ khối lượng)", dat: dg == null ? null : dg > ng.QUY_DAT_NGUONG_PCT ? true : null,
    chu: dg == null ? "chưa có định giá" : `giá trị hợp lý ${dg >= 0 ? "cao" : "thấp"} hơn giá ${so(Math.abs(dg), 1)}%` + (dg > ng.QUY_DAT_NGUONG_PCT ? "" : ` – ĐẮT (ngưỡng ${ng.QUY_DAT_NGUONG_PCT}%)`)});
  const manh = [[dinh != null && dinh >= ng.QUY_MANH_DINH_PCT, "sát đỉnh 52 tuần"], [rs != null && rs >= ng.QUY_MANH_RS3T, "RS 3T cao"],
    [tk != null && tk >= ng.QUY_MANH_TK, "thanh khoản tăng"], [rsn != null && rsn > 0, "ngành mạnh"]];
  const k = manh.filter(z => z[0]).length;
  out.push({ten: `Tín hiệu MẠNH ${k}/4 (≥ ${ng.QUY_MANH_SO_DAU_HIEU} được dùng suất dự phòng)`, dat: k >= ng.QUY_MANH_SO_DAU_HIEU ? true : null, chu: manh.map(([o, t]) => (o ? "✓ " : "✗ ") + t).join(" · ")});
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
        cach: "Nối 2 đỉnh thấp dần (giảm) / 2 đáy cao dần (tăng) gần nhất; giữ khi giá chưa đóng cửa vượt qua"}); }
    else cau.push("Chưa có xu hướng rõ (đỉnh / đáy gần nhất chưa cùng chiều)");
    for (const m of kq.nen) { const b = m.bc, nguoc = b && b.n >= TIN_N && b.tl <= 1 - TIN_TL;
      const tin = b?.tin ? "đáng tin" : nguoc ? "thường SAI trên mã này" : b && b.n < TIN_N ? "chưa đáng tin (ít lần xuất hiện)" : "chưa đáng tin";
      cau.push(`Mẫu nến ${m.ten} (${m.huong > 0 ? "tăng" : "giảm"}, ${ngay(m.i)}) – ${tin}${b?.n ? `: đúng hướng ${pt(b.tl, 0, false)} trong ${b.n} lần trước trên ${ma}` : ""}`);
      items.push({id: `N${items.filter(z => z.loai === "nen").length + 1}`, loai: "nen", i: m.i, huong: m.huong, ten: m.ten, nhom: "Mẫu nến",
        tieu_de: `${m.ten} (${m.huong > 0 ? "tăng" : "giảm"}) · ${ngay(m.i)}`,
        bang: b ? [["Xuất hiện trên mã này", `${b.n} lần`], [`Đúng hướng sau ${SAU} nến`, b.tl == null ? "–" : pt(b.tl, 0, false)], [`Lãi TB sau ${SAU} nến`, b.tb == null ? "–" : pt(b.tb, 1)]] : [],
        cach: `Bằng chứng: mọi lần mẫu này xuất hiện trong lịch sử ${ma} – đáng tin khi ≥ ${TIN_N} lần và đúng hướng ≥ ${Math.round(TIN_TL * 100)}%`}); }
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
  const du_dk = dk && dk.slice(0, 4).every(z => z.dat !== false);
  return `<div class="cp-dau"><b>Đọc biểu đồ</b><button class="cp-x" data-cp="dong" title="Đóng">✕</button></div>
  <div class="cp-than">
    <div class="cp-luu">Tổng hợp tự động từ dữ liệu giá và dữ liệu hệ thống – không phải AI, không phải khuyến nghị đầu tư.</div>
    <label class="cp-dong"><input type="checkbox" data-cp="lop"${S.lop ? " checked" : ""}> Hiện chú thích trên biểu đồ</label>
    <label class="cp-dong"><input type="checkbox" data-cp="he"${S.he ? " checked" : ""}> Hiện tín hiệu hệ thống (bot) trên biểu đồ</label>
    <div class="cp-dong"><span class="nut"><button data-cpk="gon" aria-pressed="${S.kieu === "gon"}">Gọn</button><button data-cpk="du" aria-pressed="${S.kieu === "du"}">Đầy đủ</button></span>
      <span class="cp-phu">${S.kieu === "gon" ? "Vùng gần giá, xu hướng, mẫu hình gần đây" : "Mọi vùng giá và mẫu hình tìm được"}</span></div>
    ${kq ? `<h3>${esc_(dd.cau[0])}</h3><p>${dd.cau.slice(1).map(esc_).join("<br>")}</p>` : `<p class="cp-phu">Chưa đủ dữ liệu (cần ≥ 30 nến).</p>`}
    <details class="cp-doc"><summary>Cách đọc</summary><p>Vùng hỗ trợ / kháng cự: các đỉnh, đáy cục bộ (cao / thấp nhất trong 5 nến hai bên) nằm sát nhau (≤ 0,6 ATR) gộp thành vùng; càng nhiều lần chạm càng đáng chú ý.
      Xu hướng: nối 2 đỉnh thấp dần hoặc 2 đáy cao dần gần nhất. Mẫu nến được kiểm bằng chứng trên chính mã: mọi lần xuất hiện trước đây, sau ${SAU} nến giá đi đúng hướng bao nhiêu % –
      dưới ${TIN_N} lần hoặc dưới ${Math.round(TIN_TL * 100)}% thì ghi "chưa đáng tin". Tính trên khung đang xem${TUA_CHU()}.</p></details>
    <div class="cp-meta">${esc_(ma)} · ${esc_(B.ten_khung)} · dữ liệu tới ${esc_(B.phut ? gio_vn(x.d[B.n - 1]) : ngay_vn(x.d[B.n - 1]))}</div>
    <button class="cp-tinh" data-cp="tinh">Tính lại bằng chứng</button>
    <h4>HỆ THỐNG</h4>
    <div class="cp-the">${b ? `<b>Bot đang khuyến nghị ${esc_(b[1])}</b><div>Vùng mua ${so(b[2], 2)}–${so(b[3], 2)} · cắt lỗ ${so(b[4], 2)} · mục tiêu ${so(b[5], 2)} / ${so(b[6], 2)}</div>${b[7] ? `<div class="cp-phu">${esc_(b[7])}</div>` : ""}`
      : B.tua ? `<b>Đang tua lại</b><div class="cp-phu">Ẩn khuyến nghị bot hôm nay; điều kiện chọn mã bên dưới là dữ liệu hôm nay, không phải ngày tua.</div>`
      : `<b>Bot chưa có khuyến nghị mua ${esc_(ma)}</b>`}</div>
    ${dk ? `<div class="cp-the"><b>${du_dk ? "Đủ điều kiện chọn mã của Quỹ Bứt Phá" : "Chưa đủ điều kiện chọn mã của Quỹ Bứt Phá"}</b>
      <div class="cp-phu">${du_dk ? "Còn chờ điểm vào của bot (15', giờ, ATC) – không mua khi chưa có tin MUA." : "Mã không qua điều kiện dưới đây – bot sẽ không mua mới."}</div>
      <table class="cp-bang">${dk.map(z => `<tr><td class="${z.dat === true ? "t" : z.dat === false ? "g" : "m"}">${z.dat === true ? "✓" : z.dat === false ? "✗" : "!"}</td><td>${esc_(z.ten)}<div class="cp-phu">${esc_(z.chu)}</div></td></tr>`).join("")}</table>
      <div class="cp-phu">Dữ liệu lọc phiên ${esc_(ngay_vn(ht.ngay_gia))} (cập nhật ${esc_(ht.cap_nhat)}).</div></div>` : ""}
    ${th_mua.length ? `<div class="cp-the"><b>Bot đã báo MUA ${th_mua.length} lần trên ${esc_(ma)}</b><div>${dung} đúng · ${sai} sai · ${cho} đang chờ${tbv != null ? ` · kết quả TB ${tbv > 0 ? "+" : ""}${so(tbv, 2)}%` : ""}</div>
      <table class="cp-bang">${th_mua.slice(-8).reverse().map(z => `<tr><td class="${z.ket_qua === "ĐÚNG" ? "t" : z.ket_qua === "SAI" ? "g" : "m"}">${z.ket_qua === "ĐÚNG" ? "✓" : z.ket_qua === "SAI" ? "✗" : "…"}</td><td>${esc_(ngay_vn(z.ngay))} · ${esc_(z.khuyen_nghi)} · giá ${esc_(z.gia)}<div class="cp-phu">${esc_(z.giai_thich || z.ket_qua)}${z.ket_qua_pct ? ` (${esc_(z.ket_qua_pct)}%)` : ""}</div></td></tr>`).join("")}</table></div>` : ""}
    <h4>CHÚ THÍCH · ${dd.items.length} · ĐANG HIỆN ${muc}</h4>
    ${dd.items.map(it => `<div class="cp-the cp-ct${it.an ? " an" : ""}" data-cpid="${it.id}"><div class="cp-ct-dau"><i class="cham ${it.loai === "vung" ? (it.ho_tro ? "t" : it.trong ? "cam" : "g") : it.huong > 0 ? "t" : it.huong < 0 ? "g" : "tim"}"></i><span class="cp-id">${it.id}</span><b>${esc_(it.tieu_de)}</b></div>
      <div class="cp-phu">${esc_(it.nhom)}</div>${it.bang.length ? `<table class="cp-bang">${it.bang.map(([a, v]) => `<tr><td>${esc_(a)}</td><td class="so">${esc_(v)}</td></tr>`).join("")}</table>` : ""}
      <div class="cp-cach"><b>Chỉ báo</b> ${esc_(it.cach)}</div>
      <div class="cp-nut"><button data-cpx="${it.id}">Xem trên biểu đồ</button>${["vung", "xh", "tam_giac", "hai"].includes(it.loai) ? `<button data-cpg="${it.id}">Giữ thành hình vẽ</button>` : ""}<button data-cpb="${it.id}">${it.an ? "Hiện lại" : "Bỏ"}</button></div></div>`).join("")}
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
      const a = it.dau ?? it.line?.[0] ?? it.tren?.[0] ?? it.dinh?.[0] ?? it.i ?? (it.ds?.[0]?.i) ?? B.n - w; ts.setVisibleLogicalRange({from: Math.max(0, Math.min(a - 10, B.n - w)), to: Math.max(a - 10, B.n - w) + w});
      try { B.nen.priceScale().applyOptions({autoScale: true}); } catch (e_) {} return; }
    if (id.dataset.cpg && window.BD_VE?.them_hinh) {
      const T = i => window.BD_VE.t_cua(i);
      if (it.loai === "vung") BD_VE.them_hinh({c: "vung", p: [{t: T(it.dau), v: it.hi}, {t: T(it.dau), v: it.lo}], s: {m: it.ho_tro ? "#0f8a4a" : "#d1342b"}});
      if (it.loai === "xh") BD_VE.them_hinh({c: "tia", p: [{t: T(it.line[0]), v: it.line[1]}, {t: T(it.line[2]), v: it.line[3]}], s: {m: it.huong < 0 ? "#d1342b" : "#0f8a4a"}});
      if (it.loai === "tam_giac") for (const z of [it.tren, it.duoi]) BD_VE.them_hinh({c: "tia", p: [{t: T(z[0]), v: z[1]}, {t: T(z[2]), v: z[3]}], s: {m: "#9b3fd1"}});
      if (it.loai === "hai") BD_VE.them_hinh({c: "tia_ngang", p: [{t: T(it.dinh[0]), v: it.co}], s: {m: "#9b3fd1"}});
      const an = AN[B.ma] || (AN[B.ma] = new Set()); an.add(it.id); ve_lai();
    }
  };
}
})();
