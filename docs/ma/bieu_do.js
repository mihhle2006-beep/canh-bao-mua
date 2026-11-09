/* CÔNG CỤ VẼ trên biểu đồ giá (trang Biểu đồ, toàn màn hình; trang mã chỉ hiển thị) – nạp động từ docs/ma/index.html.
 * Hình vẽ lưu theo mã trong trình duyệt (localStorage "ma_hinh_ve_2"): điểm = {t: giây UTC, v: giá} nên đổi khung
 * (1' … 1 tháng) vẫn đúng chỗ. Chọn hình → kéo điểm neo để sửa, kéo thân để di chuyển, Delete xoá, Ctrl+Z hoàn tác.
 * Dùng các hàm chung của trang: so, pt, kl, esc, phien_sau, BD_DK, ST. */
(() => {
"use strict";
const VE = window.BD_VE = {_loi: []};
const KHOA = "ma_hinh_ve_2", KHOA_CU = "ma_hinh_ve";
const uid = () => Math.random().toString(36).slice(2, 10);
const MAU = ["#2962ff", "#0f8a4a", "#d1342b", "#e8710a", "#9b3fd1", "#00897b", "#1f2430", "#f9a825"];
const FIB = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.618, 2.618];
const MAU_FIB = ["#787b86", "#f23645", "#ff9800", "#4caf50", "#089981", "#00bcd4", "#787b86", "#2962ff", "#9c27b0"];
const t_so = t => typeof t === "number" ? t : t && typeof t === "object" ? Date.UTC(t.year, t.month - 1, t.day) / 1000 : Date.parse(String(t).slice(0, 10) + "T00:00:00Z") / 1000;
const kc = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const bo_dau = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();

// ---------------------------------------------------------------- KHO (lưu trình duyệt)
let KHO = {};
try { KHO = JSON.parse(localStorage.getItem(KHOA) || "{}") || {}; } catch (e) { KHO = {}; }
KHO._cfg = Object.assign({an: false, khoa: false, nam: true, gan: {}, giu: false}, KHO._cfg || {});
let bao_day = false;
function luu() {
  try { localStorage.setItem(KHOA, JSON.stringify(KHO)); }
  catch (e) { if (!bao_day) { bao_day = true; alert("Bộ nhớ trình duyệt đầy – hình vẽ mới chưa lưu được. Xoá bớt hình (nhất là hình ảnh) rồi thử lại."); } }
}
(() => {                                                // chuyển hình vẽ kiểu cũ (đường xu hướng / đường ngang)
  try {
    const cu = JSON.parse(localStorage.getItem(KHOA_CU) || "null"); if (!cu || typeof cu !== "object") return;
    for (const [ma, ds] of Object.entries(cu)) { if (!Array.isArray(ds)) continue; const moi = KHO[ma] || (KHO[ma] = []);
      for (const h of ds) {
        if (h.loai === "ngang" && isFinite(h.p)) moi.push({id: uid(), c: "ngang", p: [{t: 0, v: +h.p}], s: {}});
        else if (h.loai === "duong" && h.a && h.b) moi.push({id: uid(), c: "tia", p: [{t: t_so(h.a.time), v: h.a.value}, {t: t_so(h.b.time), v: h.b.value}], s: {}});
      } }
    localStorage.removeItem(KHOA_CU); luu();
  } catch (e) {}
})();
const LS = {};                                          // lịch sử hoàn tác / làm lại theo mã
const chup = ma => { const h = LS[ma] || (LS[ma] = {lui: [], toi: []}); h.lui.push(JSON.stringify(KHO[ma] || [])); if (h.lui.length > 60) h.lui.shift(); h.toi = []; };
function hoan_tac(toi = false) {
  const ma = C?.ma, h = LS[ma]; if (!h) return;
  const a = toi ? h.toi : h.lui, b = toi ? h.lui : h.toi; if (!a.length) return;
  b.push(JSON.stringify(KHO[ma] || [])); KHO[ma] = JSON.parse(a.pop()); CHON = null; luu(); cap_nhat();
}

// ---------------------------------------------------------------- BẢNG CÔNG CỤ
const CONG = {}, NHOM = [];
const nhom = (k, ten, icon) => NHOM.push({k, ten, icon, ds: []});
const T = (k, ten, so, ve, o = {}) => { const g = NHOM[NHOM.length - 1]; CONG[k] = {k, ten, so, ve, nhom: g.k, ...o}; g.ds.push(k); };
const IC = {
  tro: '<path d="M12 4v16M4 12h16"/>', duong: '<path d="M5 19 19 5"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="5" r="2"/>',
  ngang: '<path d="M3 12h18M6 9v6M18 9v6"/>', fib: '<path d="M4 6h16M4 10h16M4 14h16M4 18h16"/>', mau: '<path d="M3 18 8 7l4 8 4-9 5 12"/>',
  vithe: '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 12h16"/>', hinh: '<path d="M4 20c4-1 6-4 8-8l6-7 1 1-6 7c-3 3-5 6-9 7z"/>',
  chu: '<path d="M5 5h14v10H10l-4 4v-4H5z"/>', do: '<path d="m4 15 11-11 5 5L9 20z"/><path d="m8 11 2 2M11 8l2 2M14 5l2 2"/>',
  nam: '<path d="M6 3v8a6 6 0 0 0 12 0V3M6 7h4M14 7h4"/>', them: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
  lui: '<path d="M9 7 4 12l5 5M4 12h11a5 5 0 0 1 0 10h-2"/>', toi: '<path d="m15 7 5 5-5 5M20 12H9a5 5 0 0 0 0 10h2"/>',
  mat: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>', khoa: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  xoa: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>',
  ds: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2"/><circle cx="4.5" cy="12" r="1.2"/><circle cx="4.5" cy="18" r="1.2"/>'};
const svg = (p, w = 18) => `<svg viewBox="0 0 24 24" width="${w}" height="${w}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;

// ---------------------------------------------------------------- TRẠNG THÁI BIỂU ĐỒ HIỆN TẠI
let C = null;                 // {ch, nen, x, n, ma, T (thời gian các nến + tương lai), du (giây / nến), khung, tuong_tac, req}
let HIT = [], NEO = [], CHON = null, TAM = null, CONG_HT = null, KEO = null, HOVER = null, CHUOT = null, CAM = false;   // CAM: đang vẽ bằng ngón tay
const W_ = () => C?.W || 800, H_ = () => C?.H || 400;
function tg_sau(t, k) {                                 // k mốc thời gian sau t theo khung đang xem (bỏ T7 / CN, nghỉ trưa, sau 14:45)
  const out = [], kh = C.khung;
  if (kh === "D") { let d = new Date(t * 1000).toISOString().slice(0, 10); for (let i = 0; i < k; i++) { d = phien_sau(d); out.push(t_so(d)); } return out; }
  if (kh === "W") { for (let i = 1; i <= k; i++) out.push(t + 7 * 86400 * i); return out; }
  if (kh === "M") { const x = new Date(t * 1000); for (let i = 1; i <= k; i++) { const y = new Date(Date.UTC(x.getUTCFullYear(), x.getUTCMonth() + i, 28)); out.push(y.getTime() / 1000); } return out; }
  const b = +kh * 60; let s = t;
  while (out.length < k) {
    s += b; const v = new Date((s + 25200) * 1000), wd = v.getUTCDay(), m = v.getUTCHours() * 60 + v.getUTCMinutes();
    if (wd === 0 || wd === 6) continue;
    if ((m >= 555 && m < 690) || (m >= 780 && m <= 885)) out.push(s);
  }
  return out;
}
function t2l(t) {                                       // giây → chỉ số logic (số thực; ngoài dữ liệu: nội suy theo lịch phiên)
  const A = C.T, n = A.length; if (!n) return 0;
  if (t <= A[0]) return (t - A[0]) / C.du;
  if (t >= A[n - 1]) return n - 1 + (t - A[n - 1]) / C.du;
  let lo = 0, hi = n - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (A[m] <= t) lo = m; else hi = m; }
  return lo + (t - A[lo]) / ((A[hi] - A[lo]) || 1);
}
function l2t(l) {
  const A = C.T, n = A.length; if (!n) return 0;
  if (l <= 0) return A[0] + l * C.du;
  if (l >= n - 1) return A[n - 1] + (l - n + 1) * C.du;
  const i = Math.floor(l); return A[i] + (A[i + 1] - A[i]) * (l - i);
}
const X = l => { const v = C.ch.timeScale().logicalToCoordinate(l); return v == null ? null : v; };
const Y = v => { const y = C.nen.priceToCoordinate(v); return y == null ? null : y; };
const px = p => { if (p.fx != null) return {x: p.fx * W_(), y: p.fy * H_(), l: null, v: null, neo: true};
  const l = t2l(p.t); return {x: X(l), y: Y(p.v), l, v: p.v}; };
function tu_chuot(x, y, nam = true) {                   // toạ độ chuột → {t, v} (nam châm: bám O / H / L / C nến gần nhất)
  let l = C.ch.timeScale().coordinateToLogical(x), v = C.nen.coordinateToPrice(y);
  if (l == null || v == null) return null;
  if (nam && KHO._cfg.nam && !TAM?.tu_do) {
    const i = Math.round(l), x_ = C.x;
    if (i >= 0 && i < C.n) { l = i; const ung = [x_.o[i], x_.h[i], x_.l[i], x_.c[i]].filter(z => z != null);
      const g = ung.reduce((a, z) => Math.abs(Y(z) - y) < Math.abs(Y(a) - y) ? z : a, ung[0]); if (Math.abs(Y(g) - y) < (CAM ? 24 : 14)) v = g; }
  }
  return {t: l2t(l), v: +v.toFixed(4)};
}
const idx = l => Math.max(0, Math.min(C.n - 1, Math.round(l)));
const ngay_chu = t => { const d = new Date((t + (/^\d+$/.test(C.khung) ? 25200 : 0)) * 1000);
  const dd = String(d.getUTCDate()).padStart(2, "0") + "/" + String(d.getUTCMonth() + 1).padStart(2, "0");
  return /^\d+$/.test(C.khung) ? `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} ${dd}` : `${dd}/${d.getUTCFullYear()}`; };
const gia = v => so(v, 2);
const phan_tram = (a, b) => a ? pt(b / a - 1, 2) : "–";

// ---------------------------------------------------------------- VẼ: hàm tiện ích (toạ độ CSS px của khung giá)
function G(ctx, d) {
  const s = d.s || {}, m = s.m || CONG[d.c]?.mau || MAU[0], w = s.w || CONG[d.c]?.day || 1.5;
  const g = {ctx, m, w, d,
    nen(dash = s.k) { ctx.strokeStyle = m; ctx.lineWidth = w; ctx.setLineDash(dash === 1 ? [6, 4] : dash === 2 ? [2, 3] : []); },
    hit(o) { HIT.push({id: d.id, ...o}); },
    seg(a, b, o = {}) { if (!a || !b || a.x == null || b.x == null) return; ctx.save(); g.nen(o.k ?? s.k); if (o.m) ctx.strokeStyle = o.m; if (o.w) ctx.lineWidth = o.w;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); ctx.restore(); if (o.hit !== false) g.hit({k: "seg", a, b}); },
    keo(a, b, hai = false) { const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy) || 1, f = 6000 / L;
      return [hai ? {x: a.x - dx * f, y: a.y - dy * f} : a, {x: b.x + dx * f, y: b.y + dy * f}]; },
    tia(a, b, o) { if (!a || !b) return; const [p, q] = g.keo(a, b); g.seg(p, q, o); },
    dai(a, b, o) { if (!a || !b) return; const [p, q] = g.keo(a, b, true); g.seg(p, q, o); },
    poly(pts, o = {}) { pts = pts.filter(p => p && p.x != null && p.y != null); if (pts.length < 2) return; ctx.save(); g.nen(o.k ?? s.k); if (o.m) ctx.strokeStyle = o.m;
      ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); if (o.dong) ctx.closePath();
      if (o.to) { ctx.fillStyle = o.to; ctx.fill(); } if (o.vien !== false) ctx.stroke(); ctx.restore();
      if (o.to && o.dong) g.hit({k: "poly", pts}); for (let i = 1; i < pts.length; i++) g.hit({k: "seg", a: pts[i - 1], b: pts[i]}); if (o.dong) g.hit({k: "seg", a: pts[pts.length - 1], b: pts[0]}); },
    to(pts, mau_) { pts = pts.filter(p => p && p.x != null); if (pts.length < 3) return; ctx.save(); ctx.fillStyle = mau_; ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.closePath(); ctx.fill(); ctx.restore(); g.hit({k: "poly", pts}); },
    hcn(a, b, o = {}) { const x0 = Math.min(a.x, b.x), y0 = Math.min(a.y, b.y), x1 = Math.max(a.x, b.x), y1 = Math.max(a.y, b.y);
      if (o.to) { ctx.save(); ctx.fillStyle = o.to; ctx.fillRect(x0, y0, x1 - x0, y1 - y0); ctx.restore(); }
      if (o.vien !== false) { ctx.save(); g.nen(o.k ?? s.k); if (o.m) ctx.strokeStyle = o.m; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.restore(); }
      g.hit(o.to ? {k: "rect", r: [x0, y0, x1, y1]} : {k: "khung", r: [x0, y0, x1, y1]}); },
    tron(c, r, o = {}) { if (!c || !(r > 0)) return; ctx.save(); g.nen(o.k ?? s.k); if (o.m) ctx.strokeStyle = o.m; ctx.beginPath();
      if (o.ry) ctx.ellipse(c.x, c.y, r, o.ry, o.goc || 0, o.a0 ?? 0, o.a1 ?? Math.PI * 2, o.nguoc); else ctx.arc(c.x, c.y, r, o.a0 ?? 0, o.a1 ?? Math.PI * 2, o.nguoc);
      if (o.to) { ctx.fillStyle = o.to; ctx.fill(); } ctx.stroke(); ctx.restore(); g.hit({k: "tron", c, r, ry: o.ry || r, to: !!o.to}); },
    chu(x, y, t, o = {}) { if (x == null || y == null || t == null || t === "") return; ctx.save(); const c_ = o.c || 12;
      ctx.font = `${o.dam ? 600 : 400} ${c_}px system-ui,-apple-system,Segoe UI,Roboto,sans-serif`; const dong = String(t).split("\n");
      const w_ = Math.max(...dong.map(z => ctx.measureText(z).width)), h_ = dong.length * (c_ + 3);
      let x0 = o.can === "phai" ? x - w_ : o.can === "giua" ? x - w_ / 2 : x, y0 = o.doc === "duoi" ? y : o.doc === "giua" ? y - h_ / 2 : y - h_;
      if (o.nen) { ctx.fillStyle = o.nen; ctx.beginPath(); (ctx.roundRect ? ctx.roundRect(x0 - 4, y0 - 2, w_ + 8, h_ + 4, 4) : ctx.rect(x0 - 4, y0 - 2, w_ + 8, h_ + 4)); ctx.fill();
        if (o.vien) { ctx.strokeStyle = o.vien; ctx.lineWidth = 1; ctx.stroke(); } }
      ctx.fillStyle = o.m || "#1f2430"; ctx.textBaseline = "top"; dong.forEach((z, i) => ctx.fillText(z, x0, y0 + i * (c_ + 3)));
      ctx.restore(); if (o.hit !== false) g.hit({k: "rect", r: [x0 - 4, y0 - 2, x0 + w_ + 4, y0 + h_ + 2]}); return {x0, y0, w: w_, h: h_}; },
    mui(a, b, kt = 10, o = {}) { if (!a || !b || a.x == null || b.x == null) return; const g_ = Math.atan2(b.y - a.y, b.x - a.x); ctx.save(); ctx.fillStyle = o.m || m;
      ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x - kt * Math.cos(g_ - .45), b.y - kt * Math.sin(g_ - .45)); ctx.lineTo(b.x - kt * Math.cos(g_ + .45), b.y - kt * Math.sin(g_ + .45)); ctx.closePath(); ctx.fill(); ctx.restore(); },
    ngang(y, x0 = 0, x1 = W_(), o) { g.seg({x: x0, y}, {x: x1, y}, o); },
    doc(x, o) { g.seg({x, y: 0}, {x, y: H_()}, o); },
    nhan_truc(y, t, mau_ = m) { g.chu(W_() - 2, y, t, {can: "phai", doc: "giua", nen: mau_, m: "#fff", c: 11, hit: false}); },
    nhan_tg(x, t, mau_ = m) { g.chu(x, H_() - 2, t, {can: "giua", doc: "tren", nen: mau_, m: "#fff", c: 11, hit: false}); },
    to_mau(mau_, a) { return mau_ + Math.round(a * 255).toString(16).padStart(2, "0"); },
    diem: (l, v) => ({x: X(l), y: Y(v), l, v}),
  };
  return g;
}
const tren_doan = (p, a, b) => { const dx = b.x - a.x, dy = b.y - a.y, L = dx * dx + dy * dy; let u = L ? ((p.x - a.x) * dx + (p.y - a.y) * dy) / L : 0; u = Math.max(0, Math.min(1, u)); return Math.hypot(p.x - a.x - u * dx, p.y - a.y - u * dy); };
const trong_da_giac = (p, pts) => { let c = false; for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) { const a = pts[i], b = pts[j]; if ((a.y > p.y) !== (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / ((b.y - a.y) || 1e-9) + a.x) c = !c; } return c; };
function trung(h, p) {
  if (h.k === "seg") return tren_doan(p, h.a, h.b) <= 6;
  if (h.k === "poly") return trong_da_giac(p, h.pts);
  if (h.k === "rect") return p.x >= h.r[0] - 3 && p.x <= h.r[2] + 3 && p.y >= h.r[1] - 3 && p.y <= h.r[3] + 3;
  if (h.k === "khung") { const [x0, y0, x1, y1] = h.r; return (p.x >= x0 - 5 && p.x <= x1 + 5 && p.y >= y0 - 5 && p.y <= y1 + 5) && (Math.abs(p.x - x0) <= 5 || Math.abs(p.x - x1) <= 5 || Math.abs(p.y - y0) <= 5 || Math.abs(p.y - y1) <= 5); }
  if (h.k === "tron") { const e = Math.hypot((p.x - h.c.x) / h.r, (p.y - h.c.y) / h.ry); return h.to ? e <= 1.02 : Math.abs(e - 1) * Math.min(h.r, h.ry) <= 6; }
  return false;
}

// ---------------------------------------------------------------- DỮ LIỆU NẾN cho công cụ thông minh
const vung_nen = (a, b) => { let i = idx(Math.min(a, b)), j = idx(Math.max(a, b)); return [i, j]; };
function hoi_quy(a, b) {
  const [i, j] = vung_nen(a, b), c = C.x.c, n = j - i + 1; if (n < 3) return null;
  let sx = 0, sy = 0, sxy = 0, sxx = 0; for (let k = i; k <= j; k++) { const x = k - i; sx += x; sy += c[k]; sxy += x * c[k]; sxx += x * x; }
  const b_ = (n * sxy - sx * sy) / (n * sxx - sx * sx), a_ = (sy - b_ * sx) / n;
  let e = 0; for (let k = i; k <= j; k++) e += (c[k] - (a_ + b_ * (k - i))) ** 2;
  return {i, j, a: a_, b: b_, sd: Math.sqrt(e / n)};
}
function pivot(i0, i1, cao, k = 4, a = null) {          // đỉnh / đáy fractal trong [i0, i1] (a: chuỗi giá, mặc định cao / thấp)
  const x = C.x, out = []; a = a || (cao ? x.h : x.l);
  for (let i = Math.max(i0, k); i <= Math.min(i1, C.n - 1 - k); i++) {
    let ok = true; for (let j = i - k; j <= i + k && ok; j++) if (j !== i && (cao ? a[j] > a[i] : a[j] < a[i])) ok = false;
    if (ok) out.push(i);
  }
  return out;
}
function xu_huong_tu_dong(l) {                         // 2 đường theo GIÁ ĐÓNG CỬA: hỗ trợ nối 2 đáy gần nhất đi lên / kháng cự nối 2 đỉnh đi xuống
  const i1 = idx(Math.min(l, C.n - 1)), i0 = Math.max(0, i1 - 160), x = C.x, out = [];
  for (const cao of [false, true]) {
    const a = x.c, pv = pivot(i0, i1, cao, 4, a); let chon = null;
    for (let u = pv.length - 1; u > 0 && !chon; u--) for (let v = u - 1; v >= 0 && !chon; v--) {
      const p = pv[v], q = pv[u]; if (cao ? a[q] >= a[p] : a[q] <= a[p]) continue;
      const k_ = (a[q] - a[p]) / (q - p); let gay = false;
      for (let z = q + 1; z <= i1 && !gay; z++) { const y = a[p] + k_ * (z - p); if (cao ? x.c[z] > y * 1.005 : x.c[z] < y * 0.995) gay = true; }
      if (!gay) chon = [p, q];
    }
    for (let u = pv.length - 1; u > 0 && !chon; u--) for (let v = u - 1; v >= 0 && !chon; v--)      // không có đường chưa bị phá: lấy cặp đúng chiều gần nhất
      if (cao ? a[pv[u]] < a[pv[v]] : a[pv[u]] > a[pv[v]]) chon = [pv[v], pv[u]];
    if (!chon && pv.length >= 2) chon = pv.slice(-2);
    if (chon) out.push({t: C.T[chon[0]], v: a[chon[0]]}, {t: C.T[chon[1]], v: a[chon[1]]});
    else out.push(null, null);
  }
  return out;
}
function vwap(i0) {
  const x = C.x, o = []; let pv = 0, vv = 0, p2 = 0;
  for (let i = i0; i < C.n; i++) { const tp = (x.h[i] + x.l[i] + x.c[i]) / 3, v = x.v[i] || 0; pv += tp * v; vv += v; p2 += tp * tp * v;
    const m = vv ? pv / vv : tp; o.push({i, m, sd: vv ? Math.sqrt(Math.max(0, p2 / vv - m * m)) : 0}); }
  return o;
}
function ho_so_kl(i, j, so_bin = 24) {                 // phân bố khối lượng theo giá (chia đều KL nến trên [thấp, cao])
  const x = C.x; let lo = Infinity, hi = -Infinity; for (let k = i; k <= j; k++) { lo = Math.min(lo, x.l[k]); hi = Math.max(hi, x.h[k]); }
  if (!(hi > lo)) return null;
  const b = (hi - lo) / so_bin, tang = new Array(so_bin).fill(0), giam = new Array(so_bin).fill(0);
  for (let k = i; k <= j; k++) { const v = x.v[k] || 0, a = Math.floor((x.l[k] - lo) / b), z = Math.min(so_bin - 1, Math.floor((x.h[k] - lo) / b)), n = z - a + 1;
    for (let q = Math.max(0, a); q <= z; q++) (x.c[k] >= x.o[k] ? tang : giam)[q] += v / n; }
  const tong = tang.map((v, q) => v + giam[q]), poc = tong.indexOf(Math.max(...tong)), S = tong.reduce((s, v) => s + v, 0);
  let lo_i = poc, hi_i = poc, acc = tong[poc];
  while (acc < 0.7 * S && (lo_i > 0 || hi_i < so_bin - 1)) { const u = hi_i < so_bin - 1 ? tong[hi_i + 1] : -1, d_ = lo_i > 0 ? tong[lo_i - 1] : -1; if (u >= d_) acc += tong[++hi_i]; else acc += tong[--lo_i]; }
  return {lo, b, tang, giam, tong, poc, va: [lo_i, hi_i], max: Math.max(...tong)};
}
function ve_ho_so(g, i, j, x0, x1) {
  const h = ho_so_kl(i, j); if (!h) return;
  const rong = Math.max(60, Math.min(180, (x1 - x0) * 0.35)), ctx = g.ctx;
  for (let q = 0; q < h.tong.length; q++) {
    const y0 = Y(h.lo + h.b * (q + 1)), y1 = Y(h.lo + h.b * q); if (y0 == null || y1 == null) continue;
    const wt = h.tang[q] / h.max * rong, wg = h.giam[q] / h.max * rong, trong = q >= h.va[0] && q <= h.va[1];
    ctx.fillStyle = trong ? "rgba(41,98,255,0.45)" : "rgba(41,98,255,0.18)"; ctx.fillRect(x0, y0 + 1, wt, Math.max(1, y1 - y0 - 1));
    ctx.fillStyle = trong ? "rgba(242,54,69,0.45)" : "rgba(242,54,69,0.18)"; ctx.fillRect(x0 + wt, y0 + 1, wg, Math.max(1, y1 - y0 - 1));
  }
  const yp = Y(h.lo + h.b * (h.poc + .5)); g.seg({x: x0, y: yp}, {x: x1, y: yp}, {m: "#f23645", k: 0, w: 1.5});
  g.chu(x1, yp - 2, `POC ${gia(h.lo + h.b * (h.poc + .5))}`, {can: "phai", c: 11, m: "#f23645", hit: false});
  g.hcn({x: x0, y: Y(h.lo + h.b * (h.va[1] + 1))}, {x: x1, y: Y(h.lo + h.b * h.va[0])}, {to: "rgba(41,98,255,0.04)", m: "#2962ff55", k: 1});
}
const nhan_ty_le = (g, a, b, r, mau_ = "#2962ff") => { if (!a || !b || !isFinite(r)) return; g.seg(a, b, {k: 1, m: mau_ + "aa", w: 1, hit: false}); g.chu((a.x + b.x) / 2, (a.y + b.y) / 2, so(r, 3), {can: "giua", doc: "giua", nen: "#ffffffe6", vien: mau_, m: mau_, c: 11, hit: false}); };
const ty = (a, b, c, d) => Math.abs(d.v - c.v) / (Math.abs(b.v - a.v) || 1e-9);
function nhan_diem(g, P, ten, mau_ = "#2962ff") {
  P.forEach((p, i) => { if (!p || p.x == null || !ten[i]) return; const tren = i === 0 ? (P[1] && P[1].y > p.y) : (P[i - 1] && P[i - 1].y > p.y);
    g.chu(p.x, tren ? p.y - 6 : p.y + 6, ten[i], {can: "giua", doc: tren ? "tren" : "duoi", dam: true, m: mau_, c: 12, hit: false}); });
}

// ---------------------------------------------------------------- 0. CON TRỎ
nhom("tro", "Con trỏ", IC.tro);
T("chu_thap", "Chữ thập", -1, null); T("cham", "Chấm", -1, null); T("mui_ten_tro", "Mũi tên", -1, null); T("tay", "Tẩy (bấm vào hình để xoá)", -1, null);

// ---------------------------------------------------------------- 1. ĐƯỜNG, KÊNH, CHĨA BA
nhom("duong", "Đường, kênh, chĩa ba", IC.duong);
T("xu_huong", "Đường xu hướng", 2, (g, P) => g.seg(P[0], P[1]), {phim: "Alt+T"});
T("tia", "Tia", 2, (g, P) => g.tia(P[0], P[1]));
T("thong_tin", "Đường thông tin", 2, (g, P) => { g.seg(P[0], P[1]); if (!P[1]) return; const a = P[0], b = P[1];
  const goc = Math.atan2(a.y - b.y, b.x - a.x) * 180 / Math.PI;
  g.chu(b.x + 8, b.y, `${gia(b.v - a.v)} (${phan_tram(a.v, b.v)})\n${Math.round(b.l - a.l)} nến · ${so(goc, 1)}°`, {doc: "giua", nen: "#ffffffee", vien: g.m, c: 11}); });
T("keo_dai", "Đường kéo dài", 2, (g, P) => g.dai(P[0], P[1]));
T("goc", "Góc xu hướng", 2, (g, P) => { g.seg(P[0], P[1]); if (!P[1]) return; const a = P[0], b = P[1], r = 40, goc = Math.atan2(a.y - b.y, b.x - a.x);
  g.seg(a, {x: a.x + r + 20, y: a.y}, {k: 1, w: 1, hit: false}); g.tron(a, r, {a0: Math.min(0, -goc), a1: Math.max(0, -goc), k: 0, w: 1});
  g.chu(a.x + r + 6, a.y - 4, so(goc * 180 / Math.PI, 1) + "°", {c: 11, m: g.m, hit: false}); });
function kenh(g, P, mid = true) {
  if (!P[1]) return g.seg(P[0], P[1]); const a = P[0], b = P[1]; g.seg(a, b); if (!P[2]) return;
  const dy = P[2].y - (a.y + (b.y - a.y) * ((P[2].x - a.x) / ((b.x - a.x) || 1)));
  const a2 = {x: a.x, y: a.y + dy}, b2 = {x: b.x, y: b.y + dy}; g.seg(a2, b2); g.to([a, b, b2, a2], g.to_mau(g.m, .08));
  if (mid) g.seg({x: a.x, y: a.y + dy / 2}, {x: b.x, y: b.y + dy / 2}, {k: 1, w: 1, hit: false});
}
T("kenh_ss", "Kênh song song", 3, (g, P) => kenh(g, P));
T("hoi_quy", "Kênh hồi quy", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const h = hoi_quy(P[0].l, P[1].l); if (!h) return g.seg(P[0], P[1]);
  const pt_ = (k, s) => g.diem(k, h.a + h.b * (k - h.i) + s * h.sd);
  const tr = [pt_(h.i, 2), pt_(h.j, 2)], du = [pt_(h.i, -2), pt_(h.j, -2)];
  g.to([tr[0], tr[1], du[1], du[0]], g.to_mau(g.m, .07)); g.seg(tr[0], tr[1]); g.seg(du[0], du[1]); g.seg(pt_(h.i, 0), pt_(h.j, 0), {k: 1});
  g.chu(tr[1].x + 4, tr[1].y, "+2σ", {doc: "giua", c: 10, m: g.m, hit: false}); g.chu(du[1].x + 4, du[1].y, "−2σ", {doc: "giua", c: 10, m: g.m, hit: false}); },
  {goi_y: "Tự tính theo giá đóng cửa giữa 2 điểm: đường hồi quy ± 2 độ lệch chuẩn"});
T("dinh_day_phang", "Đỉnh / đáy phẳng", 3, (g, P) => { g.seg(P[0], P[1]); if (!P[2] || !P[1]) return; const c = {x: P[0].x, y: P[2].y}, d = {x: P[1].x, y: P[2].y};
  g.seg(c, d); g.to([P[0], P[1], d, c], g.to_mau(g.m, .08)); });
T("kenh_roi", "Kênh rời", 3, (g, P) => { g.seg(P[0], P[1]); if (!P[2] || !P[1]) return; const c = {x: P[0].x, y: P[2].y}, d = {x: P[1].x, y: P[2].y - (P[1].y - P[0].y)};
  g.seg(c, d); g.to([P[0], P[1], d, c], g.to_mau(g.m, .08)); });
function chia_ba(g, P, kieu) {
  if (!P[2]) return g.poly(P); const [A, B, C_] = P, M = {x: (B.x + C_.x) / 2, y: (B.y + C_.y) / 2};
  const O = kieu === "schiff" ? {x: A.x, y: (A.y + B.y) / 2} : kieu === "schiff_dc" ? {x: (A.x + B.x) / 2, y: (A.y + B.y) / 2} : A;
  const dx = M.x - O.x, dy = M.y - O.y, f = 6000 / (Math.hypot(dx, dy) || 1), xa = p => ({x: p.x + dx * f, y: p.y + dy * f});
  g.seg(A, B, {k: 1, w: 1}); g.seg(B, C_, {k: 1, w: 1}); if (O !== A) g.seg(A, O, {k: 2, w: 1});
  g.seg(O, xa(O), {m: "#f23645"});
  const ngoai = kieu === "trong" ? [{x: (A.x + B.x) / 2, y: (A.y + B.y) / 2}, {x: (A.x + C_.x) / 2, y: (A.y + C_.y) / 2}] : [B, C_];
  for (const p of ngoai) g.seg(p, xa(p));
  g.to([ngoai[0], xa(ngoai[0]), xa(ngoai[1]), ngoai[1]], g.to_mau(g.m, .07));
  if (kieu === "trong") for (const p of [B, C_]) g.seg(p, xa(p), {k: 1, w: 1});
  else for (const r of [0.5]) for (const p of [B, C_]) { const q = {x: M.x + (p.x - M.x) * r, y: M.y + (p.y - M.y) * r}; g.seg(q, xa(q), {k: 1, w: 1, hit: false}); }
}
T("andrews", "Chĩa ba Andrews", 3, (g, P) => chia_ba(g, P, "andrews"));
T("schiff", "Chĩa ba Schiff", 3, (g, P) => chia_ba(g, P, "schiff"));
T("schiff_dc", "Chĩa ba Schiff điều chỉnh", 3, (g, P) => chia_ba(g, P, "schiff_dc"));
T("chia_ba_trong", "Chĩa ba bên trong", 3, (g, P) => chia_ba(g, P, "trong"));

// ---------------------------------------------------------------- 2. NGANG, DỌC, VÙNG
nhom("ngang", "Đường ngang, dọc, vùng", IC.ngang);
T("ngang", "Đường ngang", 1, (g, P) => { g.ngang(P[0].y); g.nhan_truc(P[0].y, gia(P[0].v)); }, {phim: "Alt+H"});
T("tia_ngang", "Tia ngang", 1, (g, P) => { g.ngang(P[0].y, P[0].x); g.nhan_truc(P[0].y, gia(P[0].v)); }, {phim: "Alt+J"});
T("doc", "Đường dọc", 1, (g, P) => { g.doc(P[0].x); g.nhan_tg(P[0].x, ngay_chu(l2t(P[0].l))); }, {phim: "Alt+V"});
T("chu_thap_ve", "Đường chữ thập", 1, (g, P) => { g.ngang(P[0].y); g.doc(P[0].x); g.nhan_truc(P[0].y, gia(P[0].v)); g.nhan_tg(P[0].x, ngay_chu(l2t(P[0].l))); }, {phim: "Alt+C"});
T("vung", "Vùng hỗ trợ / kháng cự", 2, (g, P) => { if (!P[1]) return g.ngang(P[0].y, P[0].x); const x1 = W_();
  g.hcn({x: P[0].x, y: P[0].y}, {x: x1, y: P[1].y}, {to: g.to_mau(g.m, .12), m: g.m});
  g.nhan_truc(P[0].y, gia(P[0].v)); g.nhan_truc(P[1].y, gia(P[1].v));
  g.chu(P[0].x + 4, Math.min(P[0].y, P[1].y) - 2, `Vùng ${gia(Math.min(P[0].v, P[1].v))}–${gia(Math.max(P[0].v, P[1].v))} (${pt(Math.abs(P[1].v / P[0].v - 1), 1, false)})`, {c: 11, m: g.m, hit: false}); },
  {mau: "#0f8a4a"});
T("tu_dong", "Đường xu hướng tự động", 1, (g, P) => { if (P.length < 4) { g.chu(P[0].x, P[0].y - 8, "Bấm để tự nối đỉnh / đáy gần nhất", {can: "giua", c: 11, nen: "#ffffffee", hit: false}); return; }
  if (P[0] && P[1]) { g.tia(P[0], P[1], {m: "#0f8a4a"}); g.chu(P[1].x, P[1].y + 6, "Hỗ trợ", {can: "giua", doc: "duoi", c: 11, m: "#0f8a4a", hit: false}); }
  if (P[2] && P[3]) { g.tia(P[2], P[3], {m: "#d1342b"}); g.chu(P[3].x, P[3].y - 6, "Kháng cự", {can: "giua", c: 11, m: "#d1342b", hit: false}); } },
  {tao: d => { const ds = xu_huong_tu_dong(t2l(d.p[0].t)); d.p = ds.map(p => p || {t: d.p[0].t, v: d.p[0].v}); },
   goi_y: "Bấm 1 lần: tự tìm 2 đáy gần nhất đi lên (hỗ trợ) và 2 đỉnh gần nhất đi xuống (kháng cự) chưa bị phá"});

// ---------------------------------------------------------------- 3. FIBONACCI, GANN
nhom("fib", "Fibonacci, Gann", IC.fib);
function muc_fib(g, x0, x1, gia_r, ds = FIB, ghi = true) {
  let truoc = null;
  ds.forEach((r, i) => { const v = gia_r(r), y = Y(v); if (y == null) return; const m = MAU_FIB[i % MAU_FIB.length];
    if (truoc) g.to([{x: x0, y: truoc}, {x: x1, y: truoc}, {x: x1, y}, {x: x0, y}], m + "14");
    g.seg({x: x0, y}, {x: x1, y}, {m, k: 0, w: 1});
    if (ghi) g.chu(x0 + 3, y - 1, `${so(r, 3)} (${gia(v)})`, {c: 11, m, hit: false}); truoc = y; });
}
T("fib_tl", "Fibonacci thoái lui", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P; g.seg(A, B, {k: 1, w: 1, m: "#787b86"});
  muc_fib(g, Math.min(A.x, B.x), W_(), r => B.v + (A.v - B.v) * r); }, {phim: "Alt+F", goi_y: "Điểm 1 = đầu sóng, điểm 2 = cuối sóng; các mức kéo dài sang phải"});
T("fib_mr", "Fibonacci mở rộng", 3, (g, P) => { g.poly(P, {k: 1, w: 1}); if (!P[2]) return; const [A, B, C_] = P;
  muc_fib(g, C_.x, W_(), r => C_.v + (B.v - A.v) * r, [0, 0.382, 0.618, 1, 1.272, 1.618, 2, 2.618]); }, {goi_y: "3 điểm: đầu sóng, cuối sóng, điểm hồi – mục tiêu mở rộng tính từ điểm hồi"});
T("kenh_fib", "Kênh Fibonacci", 3, (g, P) => { if (!P[2]) return kenh(g, P, false); const [A, B, C_] = P;
  const dy = C_.y - (A.y + (B.y - A.y) * ((C_.x - A.x) / ((B.x - A.x) || 1)));
  FIB.forEach((r, i) => { const a = {x: A.x, y: A.y + dy * r}, b = {x: B.x, y: B.y + dy * r}; g.tia(a, b, {m: MAU_FIB[i], w: 1, k: 0});
    g.chu(a.x - 4, a.y, so(r, 3), {can: "phai", doc: "giua", c: 10, m: MAU_FIB[i], hit: false}); }); });
T("vung_tg_fib", "Vùng thời gian Fibonacci", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const d = P[1].l - P[0].l;
  [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89].forEach((f, i) => { const x = X(P[0].l + d * f); if (x == null) return; g.doc(x, {m: MAU_FIB[i % 9], w: 1, k: 0}); g.chu(x + 3, 4, String(f), {doc: "duoi", c: 10, m: MAU_FIB[i % 9], hit: false}); }); });
T("quat_fib", "Quạt tốc độ Fibonacci", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P;
  g.hcn(A, B, {m: "#787b8655", k: 2, vien: true});
  [0.25, 0.382, 0.5, 0.618, 0.75, 1].forEach((r, i) => { g.tia(A, {x: B.x, y: A.y + (B.y - A.y) * r}, {m: MAU_FIB[i + 1], w: 1, k: 0}); if (r < 1) g.tia(A, {x: A.x + (B.x - A.x) * r, y: B.y}, {m: MAU_FIB[i + 1] + "88", w: 1, k: 1});
    g.chu(B.x + 3, A.y + (B.y - A.y) * r, so(r, 3), {doc: "giua", c: 10, m: MAU_FIB[i + 1], hit: false}); }); });
T("tg_fib_xh", "Thời gian Fibonacci theo xu hướng", 3, (g, P) => { g.poly(P, {k: 1, w: 1}); if (!P[2]) return; const d = P[1].l - P[0].l;
  [0, 0.382, 0.5, 0.618, 1, 1.382, 1.618, 2, 2.618, 3].forEach((r, i) => { const x = X(P[2].l + d * r); if (x == null) return; g.doc(x, {m: MAU_FIB[i % 9], w: 1, k: 0}); g.chu(x + 3, 4, so(r, 3), {doc: "duoi", c: 10, m: MAU_FIB[i % 9], hit: false}); }); });
T("vong_fib", "Vòng tròn Fibonacci", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const R = kc(P[0], P[1]); g.seg(P[0], P[1], {k: 1, w: 1});
  [0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.618, 2.618].forEach((r, i) => g.tron(P[0], R * r, {m: MAU_FIB[(i + 1) % 9], w: 1, k: 0})); });
T("xoan_fib", "Xoắn ốc Fibonacci", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P, R = kc(A, B), g0 = Math.atan2(B.y - A.y, B.x - A.x), phi = 1.6180339887;
  const pts = []; for (let th = -4 * Math.PI; th <= 4 * Math.PI; th += 0.05) { const r = R * Math.pow(phi, th * 2 / Math.PI); if (r > 4000) break; pts.push({x: A.x + r * Math.cos(g0 + th), y: A.y + r * Math.sin(g0 + th)}); }
  g.poly(pts, {k: 0}); g.seg(A, B, {k: 1, w: 1}); });
T("cung_fib", "Cung tốc độ Fibonacci", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P, R = kc(A, B), g0 = Math.atan2(A.y - B.y, A.x - B.x); g.seg(A, B, {k: 1, w: 1});
  [0.236, 0.382, 0.5, 0.618, 0.786, 1].forEach((r, i) => g.tron(B, R * r, {a0: g0 - Math.PI / 2, a1: g0 + Math.PI / 2, m: MAU_FIB[i + 1], w: 1, k: 0})); });
T("nem_fib", "Nêm Fibonacci", 3, (g, P) => { if (!P[2]) return g.poly(P); const [A, B, C_] = P, R = kc(A, B); g.tia(A, B); g.tia(A, C_);
  const a0 = Math.atan2(B.y - A.y, B.x - A.x), a1 = Math.atan2(C_.y - A.y, C_.x - A.x), lo = Math.min(a0, a1), hi = Math.max(a0, a1), nguoc = hi - lo > Math.PI;
  [0.236, 0.382, 0.5, 0.618, 0.786, 1].forEach((r, i) => g.tron(A, R * r, {a0: nguoc ? hi : lo, a1: nguoc ? lo + 2 * Math.PI : hi, m: MAU_FIB[i + 1], w: 1, k: 0})); });
T("quat_chia_ba", "Quạt chĩa ba", 3, (g, P) => { if (!P[2]) return g.poly(P); const [A, B, C_] = P; g.seg(B, C_, {k: 1, w: 1});
  [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1].forEach((r, i) => g.tia(A, {x: B.x + (C_.x - B.x) * r, y: B.y + (C_.y - B.y) * r}, {m: MAU_FIB[i % 9], w: r === 0.5 ? 1.6 : 1, k: 0})); });
function luoi(g, A, B, ds, cheo) {
  const x0 = Math.min(A.x, B.x), x1 = Math.max(A.x, B.x), y0 = Math.min(A.y, B.y), y1 = Math.max(A.y, B.y);
  g.hcn({x: x0, y: y0}, {x: x1, y: y1}, {to: g.to_mau(g.m, .04)});
  ds.forEach((r, i) => { const m = MAU_FIB[i % 9]; g.seg({x: x0 + (x1 - x0) * r, y: y0}, {x: x0 + (x1 - x0) * r, y: y1}, {m, w: 1, k: 0, hit: false});
    g.seg({x: x0, y: y0 + (y1 - y0) * r}, {x: x1, y: y0 + (y1 - y0) * r}, {m, w: 1, k: 0, hit: false});
    g.chu(x0 + (x1 - x0) * r, y1 + 3, so(r, 3), {can: "giua", doc: "duoi", c: 9, m, hit: false}); g.chu(x0 - 3, y0 + (y1 - y0) * r, so(r, 3), {can: "phai", doc: "giua", c: 9, m, hit: false}); });
  if (cheo) { g.seg({x: x0, y: y0}, {x: x1, y: y1}, {k: 1, w: 1, hit: false}); g.seg({x: x0, y: y1}, {x: x1, y: y0}, {k: 1, w: 1, hit: false}); }
}
T("hop_gann", "Hộp Gann", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); luoi(g, P[0], P[1], [0, 0.25, 0.382, 0.5, 0.618, 0.75, 1], false); });
T("vuong_gann_cd", "Ô vuông Gann cố định", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const s = Math.abs(P[1].x - P[0].x) * Math.sign(P[1].x - P[0].x || 1), sy = Math.sign(P[1].y - P[0].y || 1);
  const B = {x: P[0].x + s, y: P[0].y + Math.abs(s) * sy}; luoi(g, P[0], B, [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1], true);
  g.tron(P[0], Math.abs(s), {a0: 0, a1: Math.PI * 2, w: 1, k: 2}); });
T("vuong_gann", "Ô vuông Gann", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); luoi(g, P[0], P[1], [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1], true);
  const x0 = Math.min(P[0].x, P[1].x), y1 = Math.max(P[0].y, P[1].y); [0.25, 0.5, 0.75, 1].forEach(r => g.tron({x: x0, y: y1}, Math.abs(P[1].x - P[0].x) * r, {a0: -Math.PI / 2, a1: 0, ry: Math.abs(P[1].y - P[0].y) * r, w: 1, k: 2})); });
T("quat_gann", "Quạt Gann", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P, dx = B.x - A.x, dy = B.y - A.y;
  [[8, "1×8"], [4, "1×4"], [3, "1×3"], [2, "1×2"], [1, "1×1"], [1 / 2, "2×1"], [1 / 3, "3×1"], [1 / 4, "4×1"], [1 / 8, "8×1"]].forEach(([k, t], i) => {
    const q = {x: A.x + dx, y: A.y + dy * k}; g.tia(A, q, {m: MAU_FIB[i % 9], w: k === 1 ? 1.8 : 1, k: 0}); g.chu(q.x + 3, q.y, t, {doc: "giua", c: 10, m: MAU_FIB[i % 9], hit: false}); }); });

// ---------------------------------------------------------------- 4. MẪU HÌNH, SÓNG, CHU KỲ
nhom("mau", "Mẫu hình, sóng, chu kỳ", IC.mau);
function hai_hoa(g, P, ten, ds_ty) {
  g.poly(P); nhan_diem(g, P, ten);
  if (P[2]) g.to([P[0], P[1], P[2]], g.to_mau(g.m, .1)); if (P[4]) g.to([P[2], P[3], P[4]], g.to_mau(g.m, .1));
  for (const [i, j, r] of ds_ty) if (P[i] && P[j]) nhan_ty_le(g, P[i], P[j], r(P));
}
T("xabcd", "Mẫu XABCD", 5, (g, P) => hai_hoa(g, P, ["X", "A", "B", "C", "D"], [[0, 2, P => ty(P[0], P[1], P[1], P[2])], [1, 3, P => ty(P[1], P[2], P[2], P[3])], [2, 4, P => ty(P[2], P[3], P[3], P[4])], [0, 4, P => ty(P[0], P[1], P[1], P[4])]]),
  {goi_y: "Tỷ lệ hiện trên đường nét đứt: AB/XA, BC/AB, CD/BC, AD/XA – Gartley ~0,618 / 0,786; Bat 0,382–0,5 / 0,886; Butterfly 0,786 / 1,27–1,618"});
T("cypher", "Mẫu Cypher", 5, (g, P) => hai_hoa(g, P, ["X", "A", "B", "C", "D"], [[0, 2, P => ty(P[0], P[1], P[1], P[2])], [1, 3, P => ty(P[0], P[1], P[2], P[3])], [2, 4, P => ty(P[0], P[3], P[3], P[4])]]),
  {goi_y: "Cypher chuẩn: B hồi 0,382–0,618 XA · C vượt 1,272–1,414 XA · D hồi 0,786 XC"});
T("vai_dau_vai", "Vai đầu vai", 7, (g, P) => { g.poly(P); nhan_diem(g, P, ["", "Vai trái", "", "Đầu", "", "Vai phải", ""]);
  if (P[2] && P[4]) { g.dai(P[2], P[4], {m: "#d1342b", k: 1}); g.chu(P[4].x, P[4].y + 6, "Đường cổ", {doc: "duoi", c: 11, m: "#d1342b", hit: false}); }
  if (P[1] && P[2] && P[3] && P[4] && P[5]) g.to([P[1], P[2], P[3], P[4], P[5]], g.to_mau(g.m, .08));
  if (P[3] && P[2] && P[4] && P[6]) { const co = P[2].v + (P[4].v - P[2].v) * ((P[3].l - P[2].l) / ((P[4].l - P[2].l) || 1)), mt = 2 * co - P[3].v; const y = Y(mt);
    if (y != null) { g.seg({x: P[6].x, y: P[6].y}, {x: P[6].x, y}, {k: 1, m: "#d1342b", hit: false}); g.chu(P[6].x + 4, y, `Mục tiêu ${gia(mt)}`, {doc: "giua", c: 11, m: "#d1342b", hit: false}); } } },
  {goi_y: "7 điểm theo thứ tự: chân trái, vai trái, đáy 1, đầu, đáy 2, vai phải, điểm phá cổ – tự tính mục tiêu = cổ − (đầu − cổ)"});
T("abcd", "Mẫu ABCD", 4, (g, P) => hai_hoa(g, P, ["A", "B", "C", "D"], [[0, 2, P => ty(P[0], P[1], P[1], P[2])], [1, 3, P => ty(P[1], P[2], P[2], P[3])]]));
T("tam_giac_mau", "Mẫu tam giác", 4, (g, P) => { g.poly(P); nhan_diem(g, P, ["A", "B", "C", "D"]); if (P[2]) g.tia(P[0], P[2], {k: 1}); if (P[3]) g.tia(P[1], P[3], {k: 1});
  if (P[3]) g.to([P[0], P[1], P[3], P[2]], g.to_mau(g.m, .07)); });
T("ba_nhip", "Mẫu ba nhịp", 6, (g, P) => hai_hoa(g, P, ["", "1", "A", "2", "B", "3"], [[1, 3, P => ty(P[1], P[2], P[2], P[3])], [3, 5, P => ty(P[3], P[4], P[4], P[5])]]),
  {goi_y: "Ba nhịp chuẩn: mỗi nhịp mở rộng 1,272–1,618 lần đoạn hồi trước"});
function elliott(g, P, ten, kiem) {
  g.poly(P); nhan_diem(g, P, ten, "#2962ff");
  if (kiem && P.length >= 6 && P[5]) { const loi = kiem(P.map(p => p.v)); const z = P[5];
    g.chu(z.x + 8, z.y, loi.length ? "Cần xem lại: " + loi.join("; ") : "Đúng 3 quy tắc sóng đẩy", {doc: "giua", c: 11, nen: loi.length ? "#fff3e0" : "#e8f5e9", vien: loi.length ? "#e8710a" : "#0f8a4a", m: loi.length ? "#b35c00" : "#0f6b3a", hit: false}); }
}
T("elliott_day", "Sóng đẩy Elliott (12345)", 6, (g, P) => elliott(g, P, ["(0)", "(1)", "(2)", "(3)", "(4)", "(5)"], v => {
  const len = v[1] > v[0] ? 1 : -1, l1 = Math.abs(v[1] - v[0]), l3 = Math.abs(v[3] - v[2]), l5 = Math.abs(v[5] - v[4]), loi = [];
  if ((v[2] - v[0]) * len <= 0) loi.push("sóng 2 vượt điểm đầu"); if (l3 < l1 && l3 < l5) loi.push("sóng 3 ngắn nhất"); if ((v[4] - v[1]) * len <= 0) loi.push("sóng 4 chồng sóng 1"); return loi; }),
  {goi_y: "Tự kiểm 3 quy tắc: sóng 2 không về quá điểm đầu, sóng 3 không ngắn nhất, sóng 4 không chồng vùng sóng 1"});
T("elliott_abc", "Sóng điều chỉnh Elliott (ABC)", 4, (g, P) => elliott(g, P, ["", "(A)", "(B)", "(C)"]));
T("elliott_abcde", "Sóng tam giác Elliott (ABCDE)", 6, (g, P) => { elliott(g, P, ["", "(A)", "(B)", "(C)", "(D)", "(E)"]); if (P[3]) g.tia(P[1], P[3], {k: 1, w: 1}); if (P[4]) g.tia(P[2], P[4], {k: 1, w: 1}); });
T("elliott_wxy", "Kết hợp đôi Elliott (WXY)", 4, (g, P) => elliott(g, P, ["", "(W)", "(X)", "(Y)"]));
T("elliott_wxyxz", "Kết hợp ba Elliott (WXYXZ)", 6, (g, P) => elliott(g, P, ["", "(W)", "(X)", "(Y)", "(X)", "(Z)"]));
T("chu_ky", "Đường chu kỳ", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const d = P[1].l - P[0].l; if (Math.abs(d) < 1) return;
  const r = C.ch.timeScale().getVisibleLogicalRange(); if (!r) return; for (let k = Math.ceil((r.from - P[0].l) / d) - 1; k <= Math.ceil((r.to - P[0].l) / d) + 1; k++) { const x = X(P[0].l + k * d); if (x != null) g.doc(x, {k: k ? 1 : 0, w: 1}); }
  g.chu(P[1].x + 3, 16, `Chu kỳ ${Math.round(Math.abs(d))} nến`, {doc: "duoi", c: 11, m: g.m, hit: false}); });
T("chu_ky_tg", "Chu kỳ thời gian", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const d = P[1].l - P[0].l; if (Math.abs(d) < 1) return; const r = C.ch.timeScale().getVisibleLogicalRange(); if (!r) return;
  for (let k = Math.ceil((r.from - P[0].l) / d) - 1; k <= Math.ceil((r.to - P[0].l) / d) + 1; k++) { const a = X(P[0].l + k * d), b = X(P[0].l + (k + 1) * d); if (a == null || b == null) continue;
    g.tron({x: (a + b) / 2, y: P[0].y}, Math.abs(b - a) / 2, {a0: Math.PI, a1: 2 * Math.PI, ry: Math.min(H_() / 3, Math.abs(b - a) / 2), w: 1, k: 0, to: g.to_mau(g.m, .05)}); } });
T("hinh_sin", "Đường hình sin", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P, T2 = (B.x - A.x) * 2, amp = (B.y - A.y) / 2, y0 = (A.y + B.y) / 2;
  if (Math.abs(T2) < 4) return; const pts = []; for (let x = 0; x <= W_(); x += 3) pts.push({x, y: y0 - amp * Math.cos((x - A.x) / T2 * 2 * Math.PI)}); g.poly(pts, {k: 0}); });

// ---------------------------------------------------------------- 5. VỊ THẾ, DỰ BÁO, KHỐI LƯỢNG
nhom("vithe", "Vị thế, dự báo, khối lượng", IC.vithe);
function vi_the(g, P, d) {
  if (!P[1]) return; const A = P[0], S = P[1], r = d.r ?? 2, x0 = A.x, x1 = S.x > A.x + 12 ? S.x : A.x + 140;
  const v0 = A.v, vs = S.v, vt = v0 + r * (v0 - vs), mua = vt >= v0, yt = Y(vt), dr = v0 - vs;
  if (yt == null) return;
  g.hcn({x: x0, y: A.y}, {x: x1, y: yt}, {to: "rgba(15,138,74,0.16)", m: "#0f8a4a", k: 0});
  g.hcn({x: x0, y: A.y}, {x: x1, y: S.y}, {to: "rgba(209,52,43,0.16)", m: "#d1342b", k: 0});
  for (let k = 1; k <= Math.floor(r + 1e-9); k++) { const y = Y(v0 + k * dr); g.seg({x: x0, y}, {x: x1, y}, {m: "#0f8a4a", k: 1, w: 1, hit: false}); g.chu(x1 - 3, y - 1, `${k}R ${gia(v0 + k * dr)}`, {can: "phai", c: 10, m: "#0f6b3a", hit: false}); }
  g.seg({x: x0, y: A.y}, {x: x1, y: A.y}, {m: "#4b5565", k: 0, w: 1, hit: false});
  g.chu(x0 + 4, yt + (mua ? 3 : -3), `Mục tiêu ${gia(vt)} · ${phan_tram(v0, vt)} · ${so(r, 1)}R`, {doc: mua ? "duoi" : "tren", c: 11, dam: true, m: "#0f6b3a", hit: false});
  g.chu(x0 + 4, S.y + (mua ? -3 : 3), `Cắt lỗ ${gia(vs)} · ${phan_tram(v0, vs)}`, {doc: mua ? "tren" : "duoi", c: 11, dam: true, m: "#a3241d", hit: false});
  g.chu(x0 + 4, A.y + (mua ? -3 : 3), `${mua ? "Mua" : "Bán"} ${gia(v0)} · lời/lỗ ${so(r, 2)}`, {doc: mua ? "tren" : "duoi", c: 11, m: "#1f2430", nen: "#ffffffd9", hit: false});
  const i0 = Math.ceil(A.l + 1e-9), i1 = Math.min(C.n - 1, Math.floor(C.ch.timeScale().coordinateToLogical(x1) ?? C.n - 1));   // kết quả: chạm mục tiêu / cắt lỗ trước
  if (i0 < C.n && i0 >= 0) { let kq = null;
    for (let i = i0; i <= i1 && !kq; i++) { const h = C.x.h[i], l = C.x.l[i]; if (mua ? l <= vs : h >= vs) kq = ["Chạm cắt lỗ", i]; else if (mua ? h >= vt : l <= vt) kq = ["Đạt mục tiêu", i]; }
    const z = C.x.c[Math.min(i1, C.n - 1)];
    g.chu(x0 + 4, Math.max(S.y, yt) + 6, kq ? `${kq[0]} sau ${kq[1] - i0 + 1} nến` : `Đang mở ${phan_tram(v0, z)} (${so((z - v0) / (dr || 1), 2)}R)`, {doc: "duoi", c: 11, nen: kq ? (kq[0][0] === "Đ" ? "#e8f5e9" : "#fdecea") : "#f4f6f8", vien: "#c9d1db", hit: false}); }
  NEO_THEM.push({x: x1, y: yt, keo: (dd, p) => { const r2 = (p.v - dd.p[0].v) / ((dd.p[0].v - dd.p[1].v) || 1e-9); dd.r = Math.max(0.2, +r2.toFixed(2)); }});
}
T("vt_mua", "Vị thế mua", 2, vi_the, {goi_y: "Bấm điểm vào, rồi bấm mức cắt lỗ (dưới) – mục tiêu mặc định 2R, kéo nút ở mép mục tiêu hoặc chọn 1R / 1,5R / 2R / 3R trên thanh chỉnh"});
T("vt_ban", "Vị thế bán", 2, vi_the, {goi_y: "Bấm điểm vào, rồi bấm mức cắt lỗ (trên) – mục tiêu mặc định 2R"});
T("du_bao", "Dự báo", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [A, B] = P; g.seg(A, B, {k: 1}); g.mui(A, B);
  let kq = ""; if (B.l <= C.n - 1 && A.l >= 0) { const [i, j] = vung_nen(A.l, B.l); let dat = false; for (let k = i; k <= j && !dat; k++) dat = B.v >= A.v ? C.x.h[k] >= B.v : C.x.l[k] <= B.v; kq = dat ? "\nĐã đạt" : "\nChưa đạt"; }
  g.chu(B.x + 6, B.y, `${gia(B.v)} (${phan_tram(A.v, B.v)})\n${Math.round(B.l - A.l)} nến · ${ngay_chu(l2t(B.l))}${kq}`, {doc: "giua", c: 11, nen: "#ffffffee", vien: g.m}); },
  {goi_y: "Khi thời gian tới mốc dự báo, tự ghi Đã đạt / Chưa đạt"});
T("phong_chieu", "Phóng chiếu", 3, (g, P) => { g.poly(P); if (!P[2]) return; g.to(P, g.to_mau(g.m, .08));
  g.chu(P[2].x + 6, P[2].y, `${so(ty(P[0], P[1], P[1], P[2]) * 100, 1)}% đoạn đầu`, {doc: "giua", c: 11, nen: "#ffffffee", vien: g.m}); });
T("lap_lai", "Mẫu nến lặp lại", 3, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [i, j] = vung_nen(P[0].l, P[1].l);
  g.hcn({x: X(i - .5), y: Y(Math.max(...C.x.h.slice(i, j + 1)))}, {x: X(j + .5), y: Y(Math.min(...C.x.l.slice(i, j + 1)))}, {m: "#787b86", k: 2, w: 1});
  if (!P[2]) return; const goc = C.x.c[i], hs = P[2].v / goc, ctx = g.ctx, b = Math.max(1, (X(i + 1) - X(i)) * .6);
  for (let k = i; k <= j; k++) { const x = X(P[2].l + (k - i)); if (x == null) continue; const o = Y(C.x.o[k] * hs), c = Y(C.x.c[k] * hs), h = Y(C.x.h[k] * hs), l = Y(C.x.l[k] * hs);
    ctx.strokeStyle = ctx.fillStyle = C.x.c[k] >= C.x.o[k] ? "rgba(15,138,74,0.45)" : "rgba(209,52,43,0.45)"; ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(x, l); ctx.stroke(); ctx.fillRect(x - b / 2, Math.min(o, c), b, Math.max(1, Math.abs(c - o))); }
  g.hit({k: "rect", r: [P[2].x - 4, Math.min(...[Y(Math.max(...C.x.h.slice(i, j + 1)) * hs)]), X(P[2].l + j - i) + 4, Y(Math.min(...C.x.l.slice(i, j + 1)) * hs)]}); },
  {goi_y: "Bấm đầu và cuối đoạn nến mẫu, rồi bấm chỗ đặt bản sao (giá tính theo tỷ lệ)"});
T("nen_du_phong", "Nến dự phóng", 0, (g, P) => { g.poly(P, {k: 1, w: 1}); const ctx = g.ctx;
  for (let k = 1; k < P.length; k++) { const a = P[k - 1], c = P[k], x = c.x, b = Math.max(3, (X(1) - X(0)) * .6); if (x == null) continue;
    const than = Math.abs(c.y - a.y), h = Math.min(a.y, c.y) - than * .3 - 2, l = Math.max(a.y, c.y) + than * .3 + 2;
    ctx.strokeStyle = ctx.fillStyle = c.v >= a.v ? "rgba(15,138,74,0.55)" : "rgba(209,52,43,0.55)"; ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(x, l); ctx.stroke(); ctx.fillRect(x - b / 2, Math.min(a.y, c.y), b, Math.max(1, than)); } },
  {goi_y: "Bấm lần lượt giá đóng cửa từng nến dự phóng, bấm đúp (hoặc Enter) để xong"});
T("vwap_neo", "VWAP neo", 1, (g, P) => { const i0 = idx(P[0].l), ds = vwap(i0); if (!ds.length) return;
  const m = ds.map(z => g.diem(z.i, z.m)), tr = ds.map(z => g.diem(z.i, z.m + z.sd)), du = ds.map(z => g.diem(z.i, z.m - z.sd));
  g.poly(m, {k: 0, w: 2}); g.poly(tr, {k: 1, w: 1, m: g.m + "99"}); g.poly(du, {k: 1, w: 1, m: g.m + "99"});
  g.chu(m[m.length - 1].x + 4, m[m.length - 1].y, `VWAP ${gia(ds[ds.length - 1].m)}`, {doc: "giua", c: 11, m: g.m, hit: false}); },
  {mau: "#e8710a", goi_y: "Giá trung bình theo khối lượng tính từ nến được neo tới nay (± 1 độ lệch chuẩn)"});
T("vp_kc", "Volume Profile khoảng cố định", 2, (g, P) => { if (!P[1]) return g.seg(P[0], P[1]); const [i, j] = vung_nen(P[0].l, P[1].l); if (j - i < 2) return; ve_ho_so(g, i, j, X(i - .5), X(j + .5)); },
  {goi_y: "Phân bố khối lượng theo giá trong khoảng chọn: POC (giá nhiều KL nhất), vùng giá trị 70%"});
T("vp_neo", "Volume Profile neo", 1, (g, P) => { const i = idx(P[0].l), j = C.n - 1; if (j - i < 2) return; ve_ho_so(g, i, j, X(i - .5), X(j + .5)); });

// ---------------------------------------------------------------- 6. HÌNH, MŨI TÊN, BÚT
nhom("hinh", "Hình, mũi tên, bút", IC.hinh);
T("but", "Bút vẽ", 0, (g, P) => g.poly(P, {k: 0}), {tu_do: true, day: 2});
T("da_quang", "Bút dạ quang", 0, (g, P) => g.poly(P, {k: 0}), {tu_do: true, day: 14, mau: "#f9a82566"});
T("mui_ten", "Mũi tên", 2, (g, P) => { g.seg(P[0], P[1]); g.mui(P[0], P[1], 12); });
T("mui_ten_dd", "Mũi tên đánh dấu", 2, (g, P) => { if (!P[1]) return; const [A, B] = P, a = Math.atan2(B.y - A.y, B.x - A.x), w = 6, L = kc(A, B), h = Math.min(18, L / 2);
  const ux = Math.cos(a), uy = Math.sin(a), nx = -uy, ny = ux, cu = {x: B.x - ux * h, y: B.y - uy * h};
  g.poly([{x: A.x + nx * w / 2, y: A.y + ny * w / 2}, {x: cu.x + nx * w / 2, y: cu.y + ny * w / 2}, {x: cu.x + nx * w * 1.6, y: cu.y + ny * w * 1.6}, B, {x: cu.x - nx * w * 1.6, y: cu.y - ny * w * 1.6}, {x: cu.x - nx * w / 2, y: cu.y - ny * w / 2}, {x: A.x - nx * w / 2, y: A.y - ny * w / 2}], {dong: true, to: g.m, k: 0}); });
const mui_doc = len => (g, P) => { const p = P[0], s = len ? 1 : -1, y = p.y + s * 6;
  g.poly([{x: p.x, y}, {x: p.x - 8, y: y + s * 10}, {x: p.x - 3, y: y + s * 10}, {x: p.x - 3, y: y + s * 22}, {x: p.x + 3, y: y + s * 22}, {x: p.x + 3, y: y + s * 10}, {x: p.x + 8, y: y + s * 10}], {dong: true, to: g.m, k: 0}); };
T("mui_len", "Mũi tên lên", 1, mui_doc(true), {mau: "#0f8a4a"});
T("mui_xuong", "Mũi tên xuống", 1, mui_doc(false), {mau: "#d1342b"});
T("hcn", "Hình chữ nhật", 2, (g, P) => { if (!P[1]) return; g.hcn(P[0], P[1], {to: g.to_mau(g.m, .12)}); }, {phim: "Alt+Shift+R"});
T("hcn_xoay", "Hình chữ nhật xoay", 3, (g, P) => { if (!P[2]) return g.seg(P[0], P[1]); const [A, B, C_] = P, dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L, w = (C_.x - A.x) * nx + (C_.y - A.y) * ny;
  g.poly([A, B, {x: B.x + nx * w, y: B.y + ny * w}, {x: A.x + nx * w, y: A.y + ny * w}], {dong: true, to: g.to_mau(g.m, .12)}); });
T("duong_dan", "Đường dẫn", 0, (g, P) => { g.poly(P); if (P.length > 1) g.mui(P[P.length - 2], P[P.length - 1], 12); }, {goi_y: "Bấm từng điểm, bấm đúp (hoặc Enter) để xong"});
T("gap_khuc", "Đường gấp khúc", 0, (g, P, d) => { const dong = P.length > 2 && d.xong && kc(P[0], P[P.length - 1]) < 12; g.poly(dong ? P.slice(0, -1) : P, {dong, to: dong ? g.to_mau(g.m, .1) : null}); },
  {goi_y: "Bấm từng điểm; bấm lại điểm đầu để khép kín, bấm đúp (hoặc Enter) để xong"});
T("tron", "Hình tròn", 2, (g, P) => { if (!P[1]) return; g.tron(P[0], kc(P[0], P[1]), {to: g.to_mau(g.m, .1)}); });
T("elip", "Hình elip", 2, (g, P) => { if (!P[1]) return; g.tron({x: (P[0].x + P[1].x) / 2, y: (P[0].y + P[1].y) / 2}, Math.abs(P[1].x - P[0].x) / 2, {ry: Math.abs(P[1].y - P[0].y) / 2 || 1, to: g.to_mau(g.m, .1)}); });
T("tam_giac_h", "Hình tam giác", 3, (g, P) => g.poly(P, {dong: P.length === 3, to: g.to_mau(g.m, .12)}));
const cong = (A, B, C_) => { const K = {x: 2 * B.x - (A.x + C_.x) / 2, y: 2 * B.y - (A.y + C_.y) / 2}, pts = [];
  for (let t = 0; t <= 1.0001; t += 0.04) pts.push({x: (1 - t) ** 2 * A.x + 2 * (1 - t) * t * K.x + t * t * C_.x, y: (1 - t) ** 2 * A.y + 2 * (1 - t) * t * K.y + t * t * C_.y}); return pts; };
T("cung_tron", "Cung tròn", 3, (g, P) => { if (!P[2]) return g.poly(P); g.poly(cong(P[0], P[2], P[1]), {dong: true, to: g.to_mau(g.m, .1)}); }, {goi_y: "Bấm 2 đầu cung rồi bấm độ cong"});
T("duong_cong", "Đường cong", 3, (g, P) => { if (!P[2]) return g.poly(P); g.poly(cong(P[0], P[2], P[1])); }, {goi_y: "Bấm 2 đầu rồi bấm độ cong"});
T("cong_kep", "Đường cong kép", 3, (g, P) => { if (!P[2]) return g.poly(P); const [A, B, C_] = P, M1 = {x: (A.x + B.x) / 2, y: (A.y + B.y) / 2}, M2 = {x: (B.x + C_.x) / 2, y: (B.y + C_.y) / 2};
  const v = {x: (C_.x - A.x) / 4, y: (C_.y - A.y) / 4}, n1 = {x: M1.x - v.y * .8, y: M1.y + v.x * .8}, n2 = {x: M2.x + v.y * .8, y: M2.y - v.x * .8};
  g.poly(cong(A, n1, B).concat(cong(B, n2, C_).slice(1))); }, {goi_y: "Đường cong chữ S qua 3 điểm"});

// ---------------------------------------------------------------- 7. CHỮ VÀ CHÚ THÍCH
nhom("chu", "Chữ và chú thích", IC.chu);
const ND = (d, mac) => d.chu ?? mac;
T("ghi_chu", "Ghi chú", 1, (g, P, d) => { const p = P[0]; g.tron(p, 4, {to: g.m}); g.chu(p.x + 8, p.y - 8, ND(d, "Ghi chú"), {c: 12, nen: "#fff8d6", vien: "#e6c64a"}); }, {chu: true, mau: "#e6a700"});
T("chu", "Chữ", 1, (g, P, d) => g.chu(P[0].x, P[0].y, ND(d, "Chữ"), {doc: "giua", c: 14, m: g.m}), {chu: true, mau: "#1f2430"});
T("chu_neo", "Chữ neo khung", 1, (g, P, d) => g.chu(P[0].x, P[0].y, ND(d, "Chữ neo khung"), {doc: "giua", c: 14, m: g.m}), {chu: true, neo: true, mau: "#1f2430",
  goi_y: "Đứng yên trên khung khi kéo / phóng biểu đồ"});
T("ghi_chu_neo", "Ghi chú neo khung", 1, (g, P, d) => g.chu(P[0].x, P[0].y, ND(d, "Ghi chú"), {doc: "giua", c: 12, nen: "#fff8d6", vien: "#e6c64a"}), {chu: true, neo: true});
T("ghi_chu_gia", "Ghi chú giá", 2, (g, P, d) => { g.tron(P[0], 3, {to: g.m}); if (!P[1]) return; g.seg(P[0], P[1], {w: 1});
  g.chu(P[1].x, P[1].y, `${gia(P[0].v)}${d.chu ? " · " + d.chu : ""}`, {doc: "giua", c: 12, nen: g.m, m: "#fff"}); }, {chu: true});
T("nhan_gia", "Nhãn giá", 1, (g, P) => { const p = P[0], t = gia(p.v), ctx = g.ctx; ctx.font = "600 12px system-ui,sans-serif"; const w = ctx.measureText(t).width + 12;
  g.poly([p, {x: p.x + 8, y: p.y - 10}, {x: p.x + 8 + w, y: p.y - 10}, {x: p.x + 8 + w, y: p.y + 10}, {x: p.x + 8, y: p.y + 10}], {dong: true, to: g.m, k: 0}); g.chu(p.x + 14, p.y, t, {doc: "giua", c: 12, dam: true, m: "#fff", hit: false}); });
T("chu_thich", "Chú thích có mũi tên", 2, (g, P, d) => { if (!P[1]) return g.seg(P[0], P[1]); g.seg(P[1], P[0], {w: 1}); g.mui(P[1], P[0], 9);
  g.chu(P[1].x, P[1].y, ND(d, "Chú thích"), {can: "giua", doc: "giua", c: 12, nen: "#ffffff", vien: g.m}); }, {chu: true});
T("binh_luan", "Bình luận", 1, (g, P, d) => { const p = P[0], b = g.chu(p.x + 10, p.y - 18, ND(d, "Bình luận"), {c: 12, nen: "#e3f2fd", vien: "#2962ff"});
  if (b) g.to([{x: p.x, y: p.y}, {x: p.x + 10, y: b.y0 + b.h - 2}, {x: p.x + 22, y: b.y0 + b.h - 2}], "#2962ff"); }, {chu: true});
T("ghim", "Ghim", 1, (g, P, d) => { const p = P[0]; g.poly([p, {x: p.x - 6, y: p.y - 12}, {x: p.x + 6, y: p.y - 12}], {dong: true, to: g.m, k: 0}); g.tron({x: p.x, y: p.y - 15}, 6, {to: g.m});
  if (d.chu && (CHON === d.id || HOVER === d.id)) g.chu(p.x + 10, p.y - 18, d.chu, {c: 12, nen: "#fff", vien: g.m, hit: false}); }, {chu: true, mau: "#d1342b", goi_y: "Ghim kèm ghi chú – rê chuột / chọn để xem"});
T("co", "Cờ đánh dấu", 1, (g, P) => { const p = P[0]; g.seg(p, {x: p.x, y: p.y - 28}, {w: 2, k: 0}); g.poly([{x: p.x, y: p.y - 28}, {x: p.x + 16, y: p.y - 23}, {x: p.x, y: p.y - 18}], {dong: true, to: g.m, k: 0}); }, {mau: "#d1342b"});
T("bien", "Biển chỉ dẫn", 1, (g, P, d) => { const p = P[0]; g.seg(p, {x: p.x, y: 34}, {w: 1, k: 1}); g.chu(p.x, 30, ND(d, "Biển"), {can: "giua", c: 12, dam: true, nen: g.m, m: "#fff"}); }, {chu: true, mau: "#00897b"});
T("bang", "Bảng", 1, (g, P, d) => { const p = P[0], dong = String(ND(d, "Mục | Giá trị\nVào | \nCắt lỗ | \nMục tiêu | ")).split("\n").map(z => z.split("|").map(s => s.trim()));
  const ctx = g.ctx; ctx.font = "12px system-ui,sans-serif"; const so_cot = Math.max(...dong.map(r => r.length)), rong = Array.from({length: so_cot}, (_, j) => Math.max(...dong.map(r => ctx.measureText(r[j] || "").width)) + 14), h = 20;
  const W = rong.reduce((s, v) => s + v, 0); g.hcn({x: p.x, y: p.y}, {x: p.x + W, y: p.y + h * dong.length}, {to: "#ffffff", m: "#9aa3af", k: 0});
  dong.forEach((r, i) => { let x = p.x; if (i) g.seg({x: p.x, y: p.y + h * i}, {x: p.x + W, y: p.y + h * i}, {m: "#d0d5dd", w: 1, k: 0, hit: false});
    r.forEach((c, j) => { g.chu(x + 7, p.y + h * i + h / 2, c, {doc: "giua", c: 12, dam: i === 0, hit: false}); x += rong[j]; }); }); },
  {chu: true, goi_y: "Mỗi dòng một hàng, ngăn cột bằng dấu |"});
const ANH = {};
T("hinh_anh", "Hình ảnh", 2, (g, P, d) => { if (!P[1]) return g.seg(P[0], P[1]); const im = d.anh ? (ANH[d.id] || (ANH[d.id] = Object.assign(new Image(), {src: d.anh, onload: () => cap_nhat()}))) : null;
  const x0 = Math.min(P[0].x, P[1].x), y0 = Math.min(P[0].y, P[1].y), w = Math.abs(P[1].x - P[0].x), h = Math.abs(P[1].y - P[0].y);
  if (im && im.complete) g.ctx.drawImage(im, x0, y0, w, h); g.hcn(P[0], P[1], {m: "#9aa3af", k: im ? 0 : 1, to: im ? null : "#f4f6f8"}); if (!im) g.chu(x0 + w / 2, y0 + h / 2, "Chọn ảnh…", {can: "giua", doc: "giua", c: 12, hit: false}); },
  {anh: true, goi_y: "Kéo khung rồi chọn ảnh từ máy (ảnh tự thu nhỏ để lưu trong trình duyệt)"});
const BIEU_TUONG = ["✓", "✗", "!", "?", "▲", "▼", "●", "■", "◆", "$", "→", "←"];
T("bieu_tuong", "Biểu tượng", 1, (g, P, d) => g.chu(P[0].x, P[0].y, d.ky || "✓", {can: "giua", doc: "giua", c: 22, dam: true, m: g.m}), {ky: BIEU_TUONG, mau: "#0f8a4a"});
const NHAN_DAN = ["MUA", "BÁN", "CHỐT LỜI", "CẮT LỖ", "THEO DÕI", "PHÁ VỠ", "ĐỈNH", "ĐÁY"];
T("nhan_dan", "Nhãn dán", 1, (g, P, d) => { const t = d.ky || "MUA", m = /BÁN|CẮT|ĐỈNH/.test(t) ? "#d1342b" : /THEO/.test(t) ? "#e8710a" : "#0f8a4a";
  g.chu(P[0].x, P[0].y, t, {can: "giua", doc: "giua", c: 12, dam: true, nen: m, m: "#fff"}); }, {ky: NHAN_DAN});
T("danh_dau_phien", "Đánh dấu phiên", 1, (g, P) => { const i = Math.round(P[0].l), a = X(i - .5), b = X(i + .5); if (a == null || b == null) return;
  g.hcn({x: a, y: 0}, {x: b, y: H_()}, {to: g.to_mau(g.m, .14), vien: false}); }, {mau: "#f9a825", goi_y: "Tô nền cả một nến (phiên) để đánh dấu"});

// ---------------------------------------------------------------- 8. ĐO
nhom("do", "Đo", IC.do);
function do_(g, P, gia_, tg_) {
  if (!P[1]) return; const [A, B] = P, len = B.v >= A.v, m = len ? "#2962ff" : "#d1342b";
  const so_nen = Math.round(B.l - A.l), giay = l2t(B.l) - l2t(A.l), ngay = Math.round(giay / 86400);
  if (gia_ && tg_) g.hcn(A, B, {to: m + "22", m, k: 0, w: 1});
  if (gia_) { const x = tg_ ? (A.x + B.x) / 2 : A.x; g.seg({x, y: A.y}, {x, y: B.y}, {m, k: 0, w: 1}); g.mui({x, y: A.y}, {x, y: B.y}, 8, {m}); if (!tg_) { g.ngang(A.y, A.x - 20, A.x + 20, {m, w: 1}); g.ngang(B.y, B.x - 20, B.x + 20, {m, w: 1}); } }
  if (tg_) { const y = gia_ ? (A.y + B.y) / 2 : A.y; g.seg({x: A.x, y}, {x: B.x, y}, {m, k: 0, w: 1}); g.mui({x: A.x, y}, {x: B.x, y}, 8, {m}); if (!gia_) { g.seg({x: A.x, y: y - 20}, {x: A.x, y: y + 20}, {m, w: 1}); g.seg({x: B.x, y: y - 20}, {x: B.x, y: y + 20}, {m, w: 1}); } }
  let kl_ = 0; if (tg_) { const [i, j] = vung_nen(A.l, B.l); for (let k = i; k <= j; k++) kl_ += C.x.v[k] || 0; }
  const dong = [gia_ ? `${gia(B.v - A.v)} (${phan_tram(A.v, B.v)})` : "", tg_ ? `${so_nen} nến${/^\d+$/.test(C.khung) ? "" : ", " + ngay + " ngày"}` : "", tg_ && kl_ ? `KL ${kl(kl_)}` : ""].filter(Boolean).join("\n");
  g.chu((A.x + B.x) / 2, Math.max(A.y, B.y) + 8, dong, {can: "giua", doc: "duoi", c: 12, nen: m, m: "#fff", hit: false});
}
T("do_gia_tg", "Đo giá và thời gian", 2, (g, P) => do_(g, P, true, true), {phim: "Shift+Click"});
T("do_gia", "Đo khoảng giá", 2, (g, P) => do_(g, P, true, false));
T("do_tg", "Đo khoảng thời gian", 2, (g, P) => do_(g, P, false, true));
const PHIM = {T: "xu_huong", H: "ngang", J: "tia_ngang", V: "doc", C: "chu_thap_ve", F: "fib_tl"};

// ---------------------------------------------------------------- VẼ TẤT CẢ (plugin trên chuỗi nến – khung giá)
let NEO_THEM = [];
function ve_tat_ca(ctx) {
  HIT = []; NEO = [];
  if (!C) return;
  const ds = (KHO._cfg.an ? [] : (KHO[C.ma] || []).filter(d => !d.an)).concat(TAM ? [TAM] : []);
  for (const d of ds) {
    const cg = CONG[d.c]; if (!cg?.ve) continue;
    try {
      const P = d.p.map(px); NEO_THEM = [];
      ctx.save(); const g = G(ctx, d); if (d.id === HOVER && d.id !== CHON) ctx.globalAlpha = 0.9;
      cg.ve(g, P, d); ctx.restore();
      if (d.id === CHON || d === TAM) { P.forEach((p, i) => { if (p.x != null && p.y != null) NEO.push({x: p.x, y: p.y, i}); }); NEO_THEM.forEach(n => NEO.push({...n, i: "them"})); }
      if (d.id === CHON) for (const n of NEO) { ctx.save(); ctx.beginPath(); ctx.arc(n.x, n.y, 5, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#2962ff"; ctx.stroke(); ctx.restore(); }
    } catch (e) { VE._loi.push(`${d.c}: ${e.message}`); /* hình hỏng: bỏ qua, không làm hỏng biểu đồ */ }
  }
}
class VePrim {
  constructor() { this.v = [{zOrder: () => "top", renderer: () => ({draw: t => t.useMediaCoordinateSpace(({context, mediaSize}) => { if (C) { C.W = mediaSize.width; C.H = mediaSize.height; } ve_tat_ca(context); })})}]; }
  attached(p) { this.req = p.requestUpdate; }
  detached() { this.req = null; }
  paneViews() { return this.v; }
  updateAllViews() {}
}
let PRIM = null;
const cap_nhat = () => { try { PRIM?.req?.(); } catch (e) {} ve_thanh_chon(); };

// ---------------------------------------------------------------- GẮN VÀO BIỂU ĐỒ
VE.gan = (B, o = {}) => {                              // B = BD_DK của trang; o.tuong_tac: cho vẽ / sửa (trang Biểu đồ, toàn màn hình)
  const x = B.x, n = B.n, khung = B.khung || ST.khung;
  const ts = x.ts || x.d.map(t_so), cung_ma = C?.ma === (B.ma || "");
  C = {ch: B.ch, nen: B.nen, x, n, ma: B.ma || "", khung, el: o.el, tuong_tac: !!o.tuong_tac};
  const du = n > 1 ? Math.max(60, (() => { const d = []; for (let i = Math.max(1, n - 40); i < n; i++) d.push(ts[i] - ts[i - 1]); d.sort((a, b) => a - b); return d[d.length >> 1]; })()) : 86400;
  C.du = du; C.T = n ? ts.concat(tg_sau(ts[n - 1], 400)) : [];
  PRIM = new VePrim(); B.nen.attachPrimitive(PRIM);
  if (!cung_ma) { CHON = null; TAM = null; } KEO = null;                // vẽ lại cùng mã (làm mới giá): giữ hình đang chọn / đang vẽ
  if (C.tuong_tac) gan_su_kien(o.el, B);
  ve_thanh_chon();
};
VE.so_hinh = ma => (KHO[ma] || []).length;
VE.t_cua = l => l2t(l);                                // chỉ số nến → thời gian (cho mục Đọc biểu đồ: "Giữ thành hình vẽ")
VE.them_hinh = d => {                                  // thêm hình dựng sẵn ({c, p, s}) vào mã đang xem, có hoàn tác
  if (!C || !CONG[d.c]) return null;
  const h = {id: uid(), c: d.c, p: d.p, s: d.s || {}}; chup(C.ma); (KHO[C.ma] || (KHO[C.ma] = [])).push(h); luu(); cap_nhat(); return h.id;
};

// ---------------------------------------------------------------- CHUỘT / CẢM ỨNG
function toa_do(e) { const r = C.vung.getBoundingClientRect(); return {x: e.clientX - r.left, y: e.clientY - r.top, ngoai: e.clientX - r.left > (C.W || r.width) || e.clientY - r.top > (C.H || r.height)}; }
function cham(p) {
  if (CHON) for (const a of NEO) if (Math.hypot(a.x - p.x, a.y - p.y) <= 9) return {id: CHON, neo: a};
  for (let i = HIT.length - 1; i >= 0; i--) if (trung(HIT[i], p)) return {id: HIT[i].id, neo: null};
  return null;
}
const tim = id => (KHO[C.ma] || []).find(d => d.id === id);
function chan(B, bat) { try { B.ch.applyOptions({handleScroll: !bat, handleScale: !bat}); } catch (e) {} }
function gan_su_kien(el, B) {
  const pane = B.ch.panes()[0]?.getHTMLElement?.() || el; C.vung = pane;
  if (pane._ve_gan) return; pane._ve_gan = true;
  let dang = false, xuat = null, cham_dau = null;
  const nuot = e => { e.stopPropagation(); if (e.cancelable && e.type !== "pointermove") e.preventDefault(); };
  pane.addEventListener("pointerdown", e => {
    if (!C?.tuong_tac || e.button > 0) return;
    CAM = e.pointerType === "touch";
    const p = toa_do(e); if (p.ngoai) return;
    dang = false;
    const shift_do = e.shiftKey && !CONG_HT && !TAM;
    const k = TAM && !TAM.xong ? TAM.c : shift_do ? "do_gia_tg" : CONG_HT;
    if (k && CONG[k].so !== -1) {                       // đang vẽ
      dang = true; nuot(e); chan(B, true);
      const d0 = CONG[k].neo ? {fx: p.x / W_(), fy: p.y / H_()} : tu_chuot(p.x, p.y); if (!d0) return;
      if (CONG[k].tu_do) { TAM = {id: uid(), c: k, p: [d0], s: {}, tu_do: true}; xuat = "tu_do"; cap_nhat(); return; }
      if (!TAM) { TAM = {id: uid(), c: k, p: [d0, {...d0}], s: {}, tam_do: shift_do}; cham_dau = p; if (CONG[k].so === 1) { TAM.p = [d0]; return hoan_tat(); } cap_nhat(); xuat = "dat"; return; }
      TAM.p[TAM.p.length - 1] = d0;
      if (CONG[k].so === 0 && TAM.p.length > 2 && kc(px(TAM.p[0]), p) < 10 && k === "gap_khuc") { TAM.p.push({...TAM.p[0]}); return hoan_tat(); }
      if (CONG[k].so > 0 && TAM.p.length >= CONG[k].so) return hoan_tat();
      TAM.p.push({...d0}); cap_nhat(); xuat = "dat"; return;
    }
    if (TAM?.tam_do) { TAM = null; cap_nhat(); }
    const h = cham(p);
    if (CONG_HT === "tay") { if (h) { nuot(e); chup(C.ma); KHO[C.ma] = KHO[C.ma].filter(d => d.id !== h.id); luu(); cap_nhat(); } return; }
    if (h && !KHO._cfg.khoa && !tim(h.id)?.khoa) {
      nuot(e); chan(B, true); dang = true; CHON = h.id; const d = tim(h.id); if (!d) return;
      chup(C.ma); KEO = {d, neo: h.neo, goc: tu_chuot(p.x, p.y, false), p0: p, ban: JSON.parse(JSON.stringify(d.p)), co: false}; pane.setPointerCapture?.(e.pointerId); cap_nhat(); return;
    }
    if (h) { CHON = h.id; cap_nhat(); return; }
    if (CHON) { CHON = null; cap_nhat(); }
  }, true);
  for (const ev of ["mousedown", "touchstart"]) pane.addEventListener(ev, e => { if (dang) nuot(e); }, {capture: true, passive: false});
  pane.addEventListener("touchmove", e => { if (dang && e.cancelable) e.preventDefault(); }, {capture: true, passive: false});
  pane.addEventListener("pointermove", e => {
    if (!C?.tuong_tac) return; const p = toa_do(e); CHUOT = p;
    if (dang && e.pointerType === "touch") kinh(p);
    if (TAM && !TAM.xong) {
      const d0 = CONG[TAM.c].neo ? {fx: p.x / W_(), fy: p.y / H_()} : tu_chuot(p.x, p.y); if (!d0) return;
      if (TAM.tu_do) { if (e.buttons) { const cu = px(TAM.p[TAM.p.length - 1]); if (kc(cu, p) > 3) { TAM.p.push(d0); cap_nhat(); } } return; }
      TAM.p[TAM.p.length - 1] = d0; cap_nhat(); return;
    }
    if (KEO) {
      const d = KEO.d, m = tu_chuot(p.x, p.y, KEO.neo != null); if (!m) return; KEO.co = KEO.co || kc(p, KEO.p0) > 2;
      if (KEO.neo?.i === "them") KEO.neo.keo(d, m);
      else if (KEO.neo != null) { const i = KEO.neo.i; d.p[i] = d.p[i].fx != null ? {fx: p.x / W_(), fy: p.y / H_()} : m; }
      else { const dl = t2l(m.t) - t2l(KEO.goc.t), dv = m.v - KEO.goc.v;
        d.p = KEO.ban.map(q => q.fx != null ? {fx: q.fx + (p.x - KEO.p0.x) / W_(), fy: q.fy + (p.y - KEO.p0.y) / H_()} : (CONG[d.c].so === 1 && ["ngang", "tia_ngang"].includes(d.c)) ? {t: q.t, v: +(q.v + dv).toFixed(4)} : {t: l2t(t2l(q.t) + dl), v: +(q.v + dv).toFixed(4)}); }
      cap_nhat(); return;
    }
    const h = cham(p), id = h?.id || null; if (id !== HOVER) { HOVER = id; cap_nhat(); }
    pane.style.cursor = CONG_HT === "tay" ? (h ? "pointer" : "not-allowed") : CONG_HT && CONG[CONG_HT].so !== -1 ? "crosshair" : h ? (h.neo ? "move" : "pointer") : "";
  }, true);
  const tha = e => {
    if (!C?.tuong_tac) return;
    if (TAM?.tu_do) { dang = false; chan(B, false); if (TAM.p.length > 1) hoan_tat(); else { TAM = null; cap_nhat(); } return; }
    if (xuat === "dat" && TAM && cham_dau && TAM.p.length === 2 && CONG[TAM.c].so >= 2) {        // bấm–kéo–thả: thả = điểm 2
      const p = toa_do(e); if (kc(p, cham_dau) > 6) { const d0 = tu_chuot(p.x, p.y); if (d0) { TAM.p[1] = d0; if (CONG[TAM.c].so === 2) hoan_tat(); else { TAM.p.push({...d0}); cap_nhat(); } } } }
    cham_dau = null; xuat = null;
    if (KEO) { if (KEO.co) luu(); else LS[C.ma]?.lui.pop(); KEO = null; }
    if (dang) { dang = false; chan(B, false); }
    kinh_tat();
  };
  pane.addEventListener("pointerup", tha, true);
  pane.addEventListener("pointercancel", tha, true);
  pane.addEventListener("dblclick", e => {
    if (!C?.tuong_tac) return;
    if (TAM && CONG[TAM.c].so === 0) { e.stopPropagation(); TAM.p.pop(); if (TAM.p.length > 1) hoan_tat(); else { TAM = null; cap_nhat(); } return; }
    const h = cham(toa_do(e)); const d = h && tim(h.id); if (d && (CONG[d.c].chu || CONG[d.c].anh)) { e.stopPropagation(); sua_chu(d); }
  }, true);
  pane.addEventListener("pointerleave", () => { if (HOVER) { HOVER = null; cap_nhat(); } });
}
// KÍNH LÚP (điện thoại): ngón tay che đúng chỗ đặt điểm → kéo / vẽ bằng tay thì hiện vùng quanh ngón tay phóng 2× ở góc trên
// phía đối diện, kèm chữ thập + giá / ngày điểm sẽ đặt (đã bám nam châm)
let KINH_HEN = 0;
function kinh(p) {
  if (KINH_HEN || !C?.ch?.takeScreenshot) return;
  KINH_HEN = requestAnimationFrame(() => { KINH_HEN = 0;
    try {
      const goc = C.ch.chartElement(), rg = goc.getBoundingClientRect(), rp = C.vung.getBoundingClientRect(), shot = C.ch.takeScreenshot();
      const k = shot.width / rg.width, cx = (rp.left - rg.left + p.x) * k, cy = (rp.top - rg.top + p.y) * k, R = 30 * k;
      let b = document.querySelector(".ve-kinh");
      if (!b) { b = Object.assign(document.createElement("canvas"), {className: "ve-kinh", width: 240, height: 240}); document.body.appendChild(b); }
      b.style.left = (p.x > rp.width / 2 ? rp.left + 8 : rp.right - 136) + "px"; b.style.top = (rp.top + 8) + "px";
      const g = b.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, 240, 240);
      g.drawImage(shot, cx - R, cy - R, 2 * R, 2 * R, 0, 0, 240, 240);
      g.strokeStyle = "#2962ff"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(120, 96); g.lineTo(120, 144); g.moveTo(96, 120); g.lineTo(144, 120); g.stroke();
      const m = tu_chuot(p.x, p.y);
      if (m) { g.fillStyle = "rgba(255,255,255,.9)"; g.fillRect(40, 160, 160, 56); g.fillStyle = "#1f2430"; g.textAlign = "center";   // giá / ngày 2 dòng (vừa vòng tròn)
        g.font = "700 24px system-ui,sans-serif"; g.fillText(gia(m.v), 120, 186); g.font = "16px system-ui,sans-serif"; g.fillText(ngay_chu(m.t), 120, 208); }
    } catch (e) { kinh_tat(); }
  });
}
function kinh_tat() { if (KINH_HEN) cancelAnimationFrame(KINH_HEN); KINH_HEN = 0; document.querySelector(".ve-kinh")?.remove(); }
function hoan_tat() {
  const d = TAM; if (!d) return; TAM = null;
  const cg = CONG[d.c]; d.xong = true;
  if (cg.so > 0 && d.p.length > cg.so) d.p = d.p.slice(0, cg.so);
  if (cg.so === 0 && !cg.tu_do) d.p = d.p.filter((q, i) => !i || kc(px(q), px(d.p[i - 1])) > 3);
  if (d.tam_do) { d.id = "do_tam"; TAM = d; d.xong = true; cap_nhat(); return; }            // Shift + bấm: đo tạm, bấm tiếp để bỏ
  if (cg.tao) try { cg.tao(d); } catch (e) {}
  if (d.c === "vt_mua" || d.c === "vt_ban") d.r = 2;
  delete d.xong; if (d.c === "gap_khuc") d.xong = true;
  chup(C.ma); (KHO[C.ma] || (KHO[C.ma] = [])).push(d); luu();
  CHON = d.id; if (!KHO._cfg.giu) dat_cong(null);
  cap_nhat();
  if (cg.chu) sua_chu(d); else if (cg.anh) chon_anh(d);
}

// ---------------------------------------------------------------- SỬA CHỮ / ẢNH / THANH CHỈNH HÌNH ĐANG CHỌN
function sua_chu(d) {
  if (CONG[d.c].anh) return chon_anh(d);
  const p = px(d.p[0]), ta = document.createElement("textarea"); ta.className = "ve-sua"; ta.value = d.chu ?? "";
  ta.placeholder = CONG[d.c].ten + " – Enter để lưu, Shift+Enter xuống dòng";
  Object.assign(ta.style, {left: Math.max(4, Math.min((p.x || 20), W_() - 250)) + "px", top: Math.max(4, (p.y || 20) - 10) + "px"});
  C.el.appendChild(ta); ta.focus();
  let da = false;
  const xong = (luu_ = true) => { if (da) return; da = true; if (luu_) { chup(C.ma); d.chu = ta.value.trim() || null; luu(); } ta.remove(); cap_nhat(); };
  ta.addEventListener("keydown", e => { e.stopPropagation(); if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); xong(true); } if (e.key === "Escape") xong(false); });
  ta.addEventListener("blur", () => xong(true));
}
function chon_anh(d) {
  const i = document.createElement("input"); i.type = "file"; i.accept = "image/*";
  i.onchange = () => { const f = i.files?.[0]; if (!f) return; const r = new FileReader();
    r.onload = () => { const im = new Image(); im.onload = () => { const s = Math.min(1, 480 / Math.max(im.width, im.height)), cv = document.createElement("canvas");
      cv.width = Math.round(im.width * s); cv.height = Math.round(im.height * s); cv.getContext("2d").drawImage(im, 0, 0, cv.width, cv.height);
      chup(C.ma); d.anh = cv.toDataURL("image/jpeg", 0.82); delete ANH[d.id]; luu(); cap_nhat(); }; im.src = r.result; };
    r.readAsDataURL(f); };
  i.click();
}
function ve_thanh_chon() {
  const el = C?.el; if (!el) return;
  let b = el.querySelector(".ve-chon"); const d = C.tuong_tac && CHON ? tim(CHON) : null;
  if (!d) { if (b) b.remove(); return; }
  if (!b) { b = document.createElement("div"); b.className = "ve-chon"; el.appendChild(b);
    b.addEventListener("pointerdown", e => e.stopPropagation()); b.addEventListener("click", e => { e.stopPropagation(); bam_thanh(e); }); b.addEventListener("change", e => e.stopPropagation()); }
  if (b.dataset.id === d.id && b.dataset.ban === JSON.stringify([d.s, d.r, d.ky, d.khoa])) return;
  b.dataset.id = d.id; b.dataset.ban = JSON.stringify([d.s, d.r, d.ky, d.khoa]);
  const cg = CONG[d.c], s = d.s || {};
  b.innerHTML = `<span class="ten">${esc(cg.ten)}</span>` +
    MAU.map(m => `<button data-vm="${m}" style="background:${m}" aria-pressed="${(s.m || cg.mau || MAU[0]) === m}" title="Màu"></button>`).join("") +
    `<span class="nhom">${[1, 2, 3, 4].map(w => `<button data-vw="${w}" aria-pressed="${(s.w || cg.day || 1.5) == w}" title="Độ dày ${w}">${w}</button>`).join("")}</span>` +
    `<span class="nhom">${[["0", "──"], ["1", "╌╌"], ["2", "┈┈"]].map(([k, t]) => `<button data-vk="${k}" aria-pressed="${String(s.k || 0) === k}" title="Kiểu nét">${t}</button>`).join("")}</span>` +
    (d.c === "vt_mua" || d.c === "vt_ban" ? `<span class="nhom">${[1, 1.5, 2, 3].map(r => `<button data-vr="${r}" aria-pressed="${(d.r ?? 2) == r}">${String(r).replace(".", ",")}R</button>`).join("")}</span>` : "") +
    (cg.ky ? `<span class="nhom">${cg.ky.map(k => `<button data-vky="${esc(k)}" aria-pressed="${(d.ky || cg.ky[0]) === k}">${esc(k)}</button>`).join("")}</span>` : "") +
    (cg.chu ? `<button data-vsua>Sửa chữ</button>` : "") + (cg.anh ? `<button data-vsua>Đổi ảnh</button>` : "") +
    `<button data-vkhoa aria-pressed="${!!d.khoa}" title="Khoá: không kéo nhầm">${svg(IC.khoa, 15)}</button><button data-vnb title="Nhân bản">⧉</button><button data-vxoa title="Xoá (Delete)">${svg(IC.xoa, 15)}</button>` +
    (cg.goi_y ? `<div class="goi-y">${esc(cg.goi_y)}</div>` : "");
}
function bam_thanh(e) {
  const t = e.target.closest("button"); if (!t) return; const d = tim(CHON); if (!d) return; chup(C.ma); d.s = d.s || {};
  if (t.dataset.vm) d.s.m = t.dataset.vm; else if (t.dataset.vw) d.s.w = +t.dataset.vw; else if (t.dataset.vk) d.s.k = +t.dataset.vk;
  else if (t.dataset.vr) d.r = +t.dataset.vr; else if (t.dataset.vky) d.ky = t.dataset.vky;
  else if (t.hasAttribute("data-vsua")) { LS[C.ma].lui.pop(); return sua_chu(d); }
  else if (t.hasAttribute("data-vkhoa")) d.khoa = !d.khoa;
  else if (t.hasAttribute("data-vnb")) { const c = JSON.parse(JSON.stringify(d)); c.id = uid(); c.p = c.p.map(q => q.fx != null ? {fx: q.fx + .02, fy: q.fy + .02} : {t: l2t(t2l(q.t) + 3), v: q.v}); KHO[C.ma].push(c); CHON = c.id; }
  else if (t.hasAttribute("data-vxoa")) { KHO[C.ma] = KHO[C.ma].filter(z => z.id !== d.id); CHON = null; }
  luu(); cap_nhat();
}

// ---------------------------------------------------------------- PHÍM TẮT
document.addEventListener("keydown", e => {
  if (!C?.tuong_tac || !document.body.contains(C.el)) return;
  const t = e.target; if (t && (t.closest?.("input,textarea,select,[contenteditable]"))) return;
  if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) { e.preventDefault(); return hoan_tac(e.shiftKey); }
  if ((e.ctrlKey || e.metaKey) && (e.key === "y" || e.key === "Y")) { e.preventDefault(); return hoan_tac(true); }
  if (e.key === "Escape") { if (TAM || CONG_HT) { TAM = null; dat_cong(null); cap_nhat(); e.stopImmediatePropagation(); } else if (CHON) { CHON = null; cap_nhat(); } return; }
  if (e.key === "Enter" && TAM && CONG[TAM.c].so === 0) { TAM.p.pop(); if (TAM.p.length > 1) hoan_tat(); else { TAM = null; cap_nhat(); } return; }
  if ((e.key === "Delete" || e.key === "Backspace") && CHON) { e.preventDefault(); chup(C.ma); KHO[C.ma] = (KHO[C.ma] || []).filter(d => d.id !== CHON); CHON = null; luu(); cap_nhat(); return; }
  if (e.altKey && !e.ctrlKey) { const k = e.shiftKey && e.code === "KeyR" ? "hcn" : PHIM[(e.code || "").replace("Key", "")]; if (k && !e.shiftKey === (k !== "hcn")) { e.preventDefault(); dat_cong(k); } }
}, true);

// ---------------------------------------------------------------- THANH CÔNG CỤ (trái) + TÌM CÔNG CỤ
function dat_cong(k) {
  TAM = null; CONG_HT = k && CONG[k]?.so === -1 ? (k === "tay" ? "tay" : null) : k;
  if (k && CONG[k]) { KHO._cfg.gan[CONG[k].nhom] = k; luu(); }
  if (k && CONG[k]?.so === -1 && C) { const an = k === "mui_ten_tro", cham_ = k === "cham";
    try { C.ch.applyOptions({crosshair: {vertLine: {visible: !an && !cham_}, horzLine: {visible: !an && !cham_}}}); } catch (e) {} KHO._cfg.tro = k; luu(); }
  document.querySelectorAll("[data-vn]").forEach(b => { const g = NHOM.find(z => z.k === b.dataset.vn), ht = CONG_HT || KHO._cfg.tro || "chu_thap";
    b.setAttribute("aria-pressed", String(CONG[ht]?.nhom === g.k)); });
  const goi = C?.el?.querySelector(".fs-goi"); if (goi) { const cg = CONG_HT && CONG[CONG_HT]; goi.textContent = cg ? (cg.goi_y || `${cg.ten}: bấm ${cg.so > 1 ? cg.so + " điểm" : cg.so === 0 ? "từng điểm, bấm đúp để xong" : "1 lần"} · Esc để huỷ`) : ""; goi.style.display = cg ? "" : "none"; }
  cap_nhat();
}
VE.dat_cong = dat_cong;
VE.thanh = el => {                                      // dựng thanh công cụ dọc vào el (.fs-trai)
  el.innerHTML = NHOM.map(g => `<div class="ve-nhom"><button class="ve-nut" data-vn="${g.k}" title="${esc(g.ten)}">${svg(g.icon)}</button><button class="ve-mo" data-vmo="${g.k}" title="Mở ${esc(g.ten)}">›</button></div>`).join("") +
    `<hr><button class="ve-nut" data-vnam aria-pressed="${KHO._cfg.nam}" title="Nam châm: bám giá mở / cao / thấp / đóng của nến">${svg(IC.nam)}</button>
     <button class="ve-nut" data-vds title="Danh sách nét vẽ: chọn / ẩn / khoá / xoá từng nét · xuất / nhập file">${svg(IC.ds)}</button>
     <button class="ve-nut" data-van aria-pressed="${!!KHO._cfg.an}" title="Ẩn / hiện mọi hình vẽ">${svg(IC.mat)}</button>
     <button class="ve-nut" data-vtim title="Tìm công cụ, ẩn / khoá / xoá hình vẽ">${svg(IC.them)}</button>
     <button class="ve-nut" data-vlui title="Hoàn tác (Ctrl+Z)">${svg(IC.lui)}</button><button class="ve-nut" data-vtoi title="Làm lại (Ctrl+Y)">${svg(IC.toi)}</button>`;
  el.onclick = e => {
    const n = e.target.closest("[data-vn]"), m = e.target.closest("[data-vmo]");
    if (m) return mo_ds(m.dataset.vmo, m);
    if (n) { const g = n.dataset.vn; const k = g === "tro" ? (KHO._cfg.tro || "chu_thap") : (KHO._cfg.gan[g] || NHOM.find(z => z.k === g).ds[0]);
      if (CONG_HT && CONG[CONG_HT]?.nhom === g) return mo_ds(g, n); return dat_cong(k); }
    if (e.target.closest("[data-vnam]")) { KHO._cfg.nam = !KHO._cfg.nam; luu(); e.target.closest("[data-vnam]").setAttribute("aria-pressed", String(KHO._cfg.nam)); return; }
    if (e.target.closest("[data-vtim]")) return mo_tim();
    if (e.target.closest("[data-vds]")) return mo_danh_sach();
    if (e.target.closest("[data-van]")) return dat_cfg("an", !KHO._cfg.an);
    if (e.target.closest("[data-vlui]")) return hoan_tac(false);
    if (e.target.closest("[data-vtoi]")) return hoan_tac(true);
  };
  let giu = null;
  el.addEventListener("pointerdown", e => { const n = e.target.closest("[data-vn]"); if (n) giu = setTimeout(() => { giu = null; mo_ds(n.dataset.vn, n); }, 550); });
  el.addEventListener("pointerup", () => { if (giu) clearTimeout(giu); });
  dat_cong(CONG_HT);
};
function dong_bang() { document.querySelectorAll(".ve-ds,.ve-tim").forEach(z => z.remove()); }
function mo_ds(gk, nut) {
  const cu = document.querySelector(`.ve-ds[data-g="${gk}"]`); dong_bang(); if (cu) return;
  const g = NHOM.find(z => z.k === gk), r = nut.getBoundingClientRect(), b = document.createElement("div");
  b.className = "ve-ds"; b.dataset.g = gk;
  b.innerHTML = `<div class="dau">${esc(g.ten.toUpperCase())} · ${g.ds.length} công cụ</div>` + g.ds.map(k => `<button data-vk2="${k}" aria-pressed="${CONG_HT === k}"><span>${esc(CONG[k].ten)}</span>${CONG[k].phim ? `<i>${CONG[k].phim}</i>` : ""}</button>`).join("");
  document.body.appendChild(b);
  const h = b.offsetHeight; b.style.left = (r.right + 6) + "px"; b.style.top = Math.max(8, Math.min(r.top - 8, innerHeight - h - 8)) + "px";
  if (r.right + 6 + b.offsetWidth > innerWidth) b.style.left = Math.max(8, innerWidth - b.offsetWidth - 8) + "px";
  b.onclick = e => { const k = e.target.closest("[data-vk2]")?.dataset.vk2; if (k) { dong_bang(); dat_cong(k); } };
}
function mo_tim() {
  const cu = document.querySelector(".ve-tim"); dong_bang(); if (cu) return;
  const b = document.createElement("div"); b.className = "ve-tim";
  const so_ma = C ? (KHO[C.ma] || []).length : 0;
  b.innerHTML = `<input placeholder="Tìm công cụ vẽ – VD: fibo, kênh, elliott" aria-label="Tìm công cụ"><div class="kq"></div>
    <div class="tac"><label><input type="checkbox" data-vt="an"${KHO._cfg.an ? " checked" : ""}> Ẩn mọi hình vẽ</label><label><input type="checkbox" data-vt="khoa"${KHO._cfg.khoa ? " checked" : ""}> Khoá mọi hình vẽ</label>
    <label><input type="checkbox" data-vt="giu"${KHO._cfg.giu ? " checked" : ""}> Giữ công cụ sau khi vẽ</label>
    <button data-vxm>Xoá ${so_ma} hình của ${esc(C?.ma || "")}</button><button data-vxt>Xoá hình vẽ mọi mã</button></div>`;
  document.body.appendChild(b);
  const o = b.querySelector("input"), kq = b.querySelector(".kq");
  const ve = () => { const q = bo_dau(o.value).trim();
    kq.innerHTML = NHOM.filter(g => g.k !== "tro" || !q).map(g => { const ds = g.ds.filter(k => !q || bo_dau(CONG[k].ten).includes(q) || bo_dau(g.ten).includes(q)); if (!ds.length) return "";
      return `<div class="dau">${esc(g.ten)}</div>` + ds.map(k => `<button data-vk2="${k}"><span>${esc(CONG[k].ten)}</span>${CONG[k].phim ? `<i>${CONG[k].phim}</i>` : ""}</button>`).join(""); }).join("") || `<div class="trong">Không có công cụ khớp</div>`; };
  o.oninput = ve; ve(); o.focus();
  o.onkeydown = e => { e.stopPropagation(); if (e.key === "Escape") dong_bang(); if (e.key === "Enter") kq.querySelector("[data-vk2]")?.click(); };
  b.onclick = e => { const k = e.target.closest("[data-vk2]")?.dataset.vk2; if (k) { dong_bang(); return dat_cong(k); }
    if (e.target.closest("[data-vxm]") && C && confirm(`Xoá mọi hình vẽ của ${C.ma}?`)) { chup(C.ma); KHO[C.ma] = []; luu(); CHON = null; cap_nhat(); dong_bang(); }
    if (e.target.closest("[data-vxt]") && confirm("Xoá hình vẽ của MỌI mã? Không hoàn tác được.")) { for (const k_ of Object.keys(KHO)) if (k_ !== "_cfg") delete KHO[k_]; luu(); CHON = null; cap_nhat(); dong_bang(); } };
  b.onchange = e => { const k = e.target.dataset.vt; if (k) dat_cfg(k, e.target.checked); };
}
function dat_cfg(k, v) {                               // ẩn / khoá / giữ công cụ – đồng bộ nút thanh trái + ô trong bảng
  KHO._cfg[k] = v; luu(); if (k === "an" && v) CHON = null;
  document.querySelectorAll(`[data-vt="${k}"]`).forEach(z => { z.checked = v; });
  if (k === "an") document.querySelectorAll("[data-van]").forEach(z => z.setAttribute("aria-pressed", String(v)));
  cap_nhat();
}
// ---------------------------------------------------------------- DANH SÁCH NÉT VẼ (chọn / ẩn / khoá / xoá từng nét) + XUẤT / NHẬP FILE
function tom_net(d) {                                  // mô tả ngắn: ngày · giá điểm đầu
  const p = d.p?.[0]; if (!p) return "";
  if (p.fx != null) return "neo theo khung";
  return `${ngay_chu(p.t)} · ${gia(p.v)}${d.p.length > 1 && d.p[1].v != null ? ` → ${gia(d.p[d.p.length - 1].v)}` : ""}`;
}
function mo_danh_sach() {
  const cu = document.querySelector(".ve-dsnet"); dong_bang(); if (cu || !C) return;
  const b = document.createElement("div"); b.className = "ve-tim ve-dsnet"; document.body.appendChild(b);
  const ve = () => {
    const ds = KHO[C.ma] || [], ma_khac = Object.keys(KHO).filter(k => k !== "_cfg" && k !== C.ma && (KHO[k] || []).length);
    b.innerHTML = `<div class="dau">NÉT VẼ CỦA ${esc(C.ma)} · ${ds.length}${ma_khac.length ? ` · còn ${ma_khac.reduce((a, k) => a + KHO[k].length, 0)} nét ở ${ma_khac.length} mã khác` : ""}</div>` +
      (ds.length ? ds.map(d => `<div class="net-r${d.id === CHON ? " chon" : ""}${d.an ? " an" : ""}" data-nid="${esc(d.id)}"><button data-nchon title="Chọn và đưa tới nét này"><span>${esc(CONG[d.c]?.ten || d.c)}</span><i>${esc(tom_net(d))}</i></button>` +
        `<button data-nan aria-pressed="${!d.an}" title="${d.an ? "Hiện" : "Ẩn"}">${svg(IC.mat, 15)}</button><button data-nkhoa aria-pressed="${!!d.khoa}" title="Khoá: không kéo nhầm">${svg(IC.khoa, 15)}</button><button data-nxoa title="Xoá">${svg(IC.xoa, 15)}</button></div>`).join("")
        : `<div class="trong">Chưa có nét vẽ nào trên mã này.</div>`) +
      `<div class="tac"><label><input type="checkbox" data-vt="an"${KHO._cfg.an ? " checked" : ""}> Ẩn mọi hình vẽ</label><label><input type="checkbox" data-vt="khoa"${KHO._cfg.khoa ? " checked" : ""}> Khoá mọi hình vẽ</label>
      <button data-nxuat title="Tải file JSON chứa nét vẽ của mọi mã – mở ở máy khác bằng Nhập file">Xuất file (mọi mã)</button><button data-nnhap title="Gộp nét vẽ từ file đã xuất (không xoá nét đang có)">Nhập file</button>
      <input type="file" accept=".json,application/json" data-nfile hidden></div>`;
  };
  ve();
  b.onclick = e => {
    const r_ = e.target.closest("[data-nid]"), d = r_ && tim(r_.dataset.nid);
    if (d && e.target.closest("[data-nchon]")) {
      if (d.an) { chup(C.ma); d.an = false; luu(); }
      CHON = d.id; const p = d.p?.[0];
      if (p?.t != null) { const l = t2l(p.t), ts_ = C.ch.timeScale(), v = ts_.getVisibleLogicalRange();
        if (v && (l < v.from || l > v.to)) { const w = v.to - v.from; ts_.setVisibleLogicalRange({from: l - w / 2, to: l + w / 2}); } }
      cap_nhat(); return ve();
    }
    if (d && e.target.closest("[data-nan]")) { chup(C.ma); d.an = !d.an; if (d.an && CHON === d.id) CHON = null; luu(); cap_nhat(); return ve(); }
    if (d && e.target.closest("[data-nkhoa]")) { chup(C.ma); d.khoa = !d.khoa; luu(); cap_nhat(); return ve(); }
    if (d && e.target.closest("[data-nxoa]")) { chup(C.ma); KHO[C.ma] = KHO[C.ma].filter(z => z.id !== d.id); if (CHON === d.id) CHON = null; luu(); cap_nhat(); return ve(); }
    if (e.target.closest("[data-nxuat]")) return xuat_file();
    if (e.target.closest("[data-nnhap]")) return b.querySelector("[data-nfile]").click();
  };
  b.onchange = e => {
    const k = e.target.dataset.vt; if (k) return dat_cfg(k, e.target.checked);
    const f = e.target.files?.[0]; if (!f) return;
    if (f.size > 5e6) return alert("File quá lớn (> 5 MB) – không phải file nét vẽ xuất từ trang này?");
    f.text().then(t => { const kq = nhap_net(JSON.parse(t)); alert(`Đã nhập ${kq.net} nét vẽ cho ${kq.ma} mã${kq.bo ? ` · bỏ ${kq.bo} nét không hợp lệ / đã có` : ""}.`); cap_nhat(); ve(); })
      .catch(() => alert("Không đọc được file – cần file JSON xuất từ nút \"Xuất file\"."));
  };
}
function xuat_file() {
  const hinh = Object.fromEntries(Object.entries(KHO).filter(([k, v]) => k !== "_cfg" && Array.isArray(v) && v.length));
  const a = document.createElement("a"), ngay = new Date(Date.now() + 7 * 3600e3).toISOString().slice(0, 10);
  a.href = URL.createObjectURL(new Blob([JSON.stringify({loai: "net-ve", ban: 1, luc: new Date().toISOString(), hinh})], {type: "application/json"}));
  a.download = `net-ve-${ngay}.json`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 3000);
}
function nhap_net(j) {                                  // file ngoài = dữ liệu không tin cậy: chỉ nhận mã hợp lệ, công cụ có thật, điểm là số; gộp, bỏ trùng id
  const hinh = j && typeof j === "object" ? (j.hinh && typeof j.hinh === "object" ? j.hinh : j) : {};
  const so = v => typeof v === "number" && isFinite(v), kq = {net: 0, ma: 0, bo: 0};
  for (const [ma, ds] of Object.entries(hinh)) {
    if (!/^[A-Z0-9]{2,12}$/.test(ma) || !Array.isArray(ds)) continue;
    const cu = KHO[ma] || [], co = new Set(cu.map(d => d.id)); let them = 0;
    for (const d of ds) {
      const ok = d && typeof d === "object" && CONG[d.c] && Array.isArray(d.p) && d.p.length && d.p.length <= 500 &&
        d.p.every(q => q && ((so(q.t) && so(q.v)) || (so(q.fx) && so(q.fy)))) && (d.anh == null || (typeof d.anh === "string" && d.anh.startsWith("data:image/")));
      if (!ok || co.has(d.id)) { kq.bo++; continue; }
      const c = JSON.parse(JSON.stringify(d)); c.id = typeof c.id === "string" && c.id.length <= 20 ? c.id : uid(); c.s = c.s && typeof c.s === "object" ? c.s : {};
      cu.push(c); co.add(c.id); them++;
    }
    if (them) { if (C?.ma === ma) chup(ma); KHO[ma] = cu; kq.net += them; kq.ma++; }
  }
  luu(); return kq;
}
document.addEventListener("pointerdown", e => { if (!e.target.closest(".ve-ds,.ve-tim,[data-vmo],[data-vn],[data-vtim],[data-vds]")) dong_bang(); }, true);
VE.CONG = CONG; VE.NHOM = NHOM;
VE._thu = {t2l: t => t2l(t), l2t: l => l2t(l), ve_lai: () => cap_nhat(), get C() { return C; }, hoi_quy, ho_so_kl, vwap, xu_huong_tu_dong, get KHO() { return KHO; }, get CHON() { return CHON; }, get HIT() { return HIT; }, nhap_net, tom_net};
})();
