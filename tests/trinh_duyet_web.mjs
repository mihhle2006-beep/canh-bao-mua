// KIỂM THỬ TRÌNH DUYỆT THẬT (Chromium – Playwright) cho trang web: máy chủ tĩnh cục bộ trên thư mục site (dữ liệu mẫu do
// tests/test_trinh_duyet_web.py dựng), CHẶN mọi request ra ngoài (raw.githubusercontent…), mở từng trang ở khổ máy tính và
// điện thoại, gom lỗi JS (pageerror + console.error, trừ lỗi tải tài nguyên bị chặn / 404 tuỳ chọn) → JSON ra stdout;
// có lỗi → mã thoát 1. Chạy: node tests/trinh_duyet_web.mjs <site> "<đường>|<bộ chọn phải hiện>|<thao tác>" …
//   thao tác (tuỳ chọn, phân cách ";"): click:<bộ chọn> · cho:<ms>
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const {chromium, devices} = require("playwright");
const [site, ...trang] = process.argv.slice(2);
const MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json",
  ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json"};
const sv = http.createServer((q, r) => {
  let f = path.join(site, decodeURIComponent(new URL(q.url, "http://x").pathname));
  if (f.endsWith(path.sep) || f.endsWith("/")) f = path.join(f, "index.html");
  fs.readFile(f, (e, b) => {
    if (e) { r.writeHead(404); r.end(); return; }
    r.writeHead(200, {"content-type": MIME[path.extname(f)] || "application/octet-stream"});
    r.end(b);
  });
});
await new Promise(ok => sv.listen(0, "127.0.0.1", ok));
const goc = `http://127.0.0.1:${sv.address().port}/`;
const br = await chromium.launch(process.env.PW_CHROMIUM ? {executablePath: process.env.PW_CHROMIUM} : {});
const KHO = {"máy tính": {viewport: {width: 1366, height: 900}}, "điện thoại": devices["iPhone 13"]};
const kq = [];
for (const t of trang) {
  const [duong, cho, thao_tac] = t.split("|");
  for (const [kho, cau_hinh] of Object.entries(KHO)) {
    const ctx = await br.newContext({...cau_hinh, serviceWorkers: "block"});
    const pg = await ctx.newPage();
    const loi = [];
    pg.on("pageerror", e => loi.push("pageerror: " + String(e.stack || e.message).split("\n").slice(0, 3).join(" | ")));
    pg.on("console", m => {
      if (m.type() === "error" && !/Failed to load resource|net::ERR_/.test(m.text())) loi.push("console: " + m.text().slice(0, 300));
    });
    await pg.route("**/*", rt => rt.request().url().startsWith(goc) ? rt.continue() : rt.abort());
    try {
      await pg.goto(goc + duong, {waitUntil: "load", timeout: 30000});
      if (cho) await pg.waitForSelector(cho, {timeout: 15000, state: "attached"});
      for (const b of (thao_tac || "").split(";").filter(Boolean)) {
        const [lenh, ...x] = b.split(":"), v = x.join(":");
        if (lenh === "click") await pg.click(v, {timeout: 10000});
        else if (lenh === "cho") await pg.waitForTimeout(+v);
        else if (lenh === "skmo") {                   // bấm (máy tính) / chạm lần 2 (điện thoại) bong bóng CT → bảng cạnh bên Cổ tức
          const p = await pg.evaluate(() => { const hop = document.querySelector(".sk-hop"), hit = typeof BD_DK !== "undefined" ? BD_DK?.skp?.hit || [] : [];
            if (!hop) return null; const r = hop.parentElement.getBoundingClientRect();
            for (const h of hit.filter(z => z.e.k === "CT")) { const x = r.left + h.x, y = r.top + h.y; if (document.elementFromPoint(x, y)?.tagName === "CANVAS") return {x, y}; }
            return null; });
          if (!p) throw new Error("không thấy bong bóng CT bấm được");
          if (kho === "điện thoại") { await pg.touchscreen.tap(p.x, p.y); await pg.waitForTimeout(700); await pg.click(".sk-hop"); }   // chạm bong bóng → hộp → chạm hộp
          else await pg.mouse.click(p.x, p.y);
          await pg.waitForSelector(".sk-pnl.mo .ct-luoi", {state: "visible", timeout: 5000});
          const chu = await pg.$eval(".sk-pnl", e => e.innerText);
          if (!/Lợi suất 12 tháng/.test(chu) || !/Lịch sử chi trả/.test(chu)) throw new Error("bảng Cổ tức thiếu nội dung");
          await pg.click(".sk-pnl [aria-label='Đóng']");
          await pg.waitForTimeout(400);
        }
        else if (lenh === "vm") {                     // tab Vĩ mô: tổng quan (thẻ, nhịp, lịch) → chạm thẻ → bảng chủ đề + biểu đồ
          await pg.click("#tab-vm");                  // → Vàng & tỷ giá (4 biểu đồ) → Hàng hoá (bảng, % nhóm) → Thế giới → tìm → bản tin
          await pg.waitForSelector("#vm-tq .vm-o2", {timeout: 8000});
          const n = await pg.$$eval("#vm-tq .vm-o2", e => e.length);
          if (n < 8) throw new Error("Vĩ mô tổng quan thiếu thẻ: " + n);
          if (await pg.$$eval("#vm-nhip .c[class*=m]", e => e.length) < 10) throw new Error("nhịp kinh tế không tô màu");
          if (!(await pg.$eval("#vm-nhan", e => e.innerText)).includes("Lạm phát")) throw new Error("thiếu điểm nhấn");
          if (await pg.$$eval("#vm-lich .d", e => e.length) < 2) throw new Error("thiếu lịch công bố");
          if (await pg.$$eval("#vm-tin a.d[href^='https://'][target=_blank]", e => e.length) < 2) throw new Error("thiếu tin vĩ mô / báo cáo gốc");
          await pg.click("#vm-tq .vm-o2[data-k=vn_cpi]"); await pg.waitForTimeout(600);
          if (await pg.$eval("#vm-cd-ten", e => e.textContent) !== "Lạm phát & giá") throw new Error("chạm thẻ CPI không mở chủ đề giá");
          await pg.waitForSelector("#vm-bd-ct canvas", {timeout: 5000, state: "attached"});
          if (await pg.$eval("#vm-bang tr.chon", e => e.dataset.k) !== "vn_cpi") throw new Error("bảng không chọn CPI");
          await pg.click("#vm-cd-ds button[data-cd=vang]"); await pg.waitForTimeout(500);
          for (const id of ["#vm-bd-xau", "#vm-bd-sjc", "#vm-bd-chenh", "#vm-bd-tg"])
            await pg.waitForSelector(id + " canvas", {timeout: 8000, state: "attached"});
          if (await pg.$$eval("#vm-the .o", e => e.length) < 5) throw new Error("thiếu thẻ vàng / tỷ giá");
          await pg.click("#vm-xau-k button[data-k=gio]"); await pg.waitForTimeout(400);
          await pg.click("#vm-ky button[data-k='0']"); await pg.waitForTimeout(400);
          await pg.click("#vm-the .o[data-k=bac]"); await pg.waitForTimeout(600);
          if (await pg.$eval("#vm-hh tr.chon", e => e.dataset.k) !== "bac") throw new Error("chạm thẻ bạc không chọn bạc ở bảng hàng hoá");
          await pg.waitForSelector("#vm-bd-hh canvas", {timeout: 5000, state: "attached"});
          await pg.click("#vm-hh tr[data-k]:last-child"); await pg.waitForTimeout(400);
          await pg.click("#vm-hh-k button[data-k=pt]"); await pg.waitForTimeout(400);
          await pg.click("#vm-cd-ds button[data-cd=the_gioi]"); await pg.waitForTimeout(500);
          for (const id of ["#vm-bd-my", "#vm-bd-myl"]) await pg.waitForSelector(id + " canvas", {timeout: 5000, state: "attached"});
          await pg.fill("#vm-tim", "lam phat"); await pg.waitForTimeout(400);
          if (await pg.$$eval("#vm-bang tr[data-k]", e => e.length) < 2) throw new Error("tìm 'lam phat' (không dấu) không ra chỉ tiêu");
          await pg.fill("#vm-tim", ""); await pg.click("#vm-cd-ds button[data-cd=ban_tin]"); await pg.waitForTimeout(300);
          if ((await pg.$$eval("#vm-bt dd", e => e.length)) < 2) throw new Error("bản tin tháng trống");
          if (!(await pg.$$eval("#vm-bt a[href^='https://']", e => e.length))) throw new Error("bản tin thiếu đường dẫn báo cáo gốc");
          await pg.click("#vm-cd-ds button[data-cd=tq]"); await pg.waitForTimeout(300);
        }
        else if (lenh === "sk") {                     // rê chuột / chạm vào bong bóng sự kiện đầu tiên → hộp chi tiết phải hiện
          await pg.waitForTimeout(800);
          await pg.evaluate(() => document.querySelector(".sk-hop")?.parentElement.scrollIntoView({block: "center"}));
          await pg.waitForTimeout(400);
          const p = await pg.evaluate(() => {           // bong bóng đầu tiên không bị phần tử khác che (kiểm cả việc logo / lớp phủ chặn chạm)
            const hop = document.querySelector(".sk-hop"), hit = typeof BD_DK !== "undefined" ? BD_DK?.skp?.hit || [] : [];
            if (!hop || !hit.length) return null;
            const r = hop.parentElement.getBoundingClientRect();
            for (const h of hit) { const x = r.left + h.x, y = r.top + h.y, e = document.elementFromPoint(x, y);
              if (e && e.tagName === "CANVAS") return {x, y, k: h.e.k}; }
            return {x: r.left + hit[0].x, y: r.top + hit[0].y, k: hit[0].e.k, che: true}; });
          if (!p) throw new Error("không thấy bong bóng sự kiện trên biểu đồ");
          if (kho === "điện thoại") await pg.touchscreen.tap(p.x, p.y); else await pg.mouse.move(p.x, p.y);
          await pg.waitForSelector(".sk-hop", {state: "visible", timeout: 4000});
          const chu = await pg.$eval(".sk-hop", e => e.innerText);
          if (!chu || chu.length < 10) throw new Error("hộp chi tiết sự kiện trống");
        }
      }
      await pg.waitForTimeout(1500);
      const chu = (await pg.evaluate(() => document.body.innerText || "")).trim();
      if (chu.length < 40) loi.push(`trang gần như trắng (${chu.length} ký tự)`);
    } catch (e) {
      loi.push("tải / thao tác: " + String(e.message).split("\n")[0]);
    }
    kq.push({trang: t, kho, loi});
    await ctx.close();
  }
}
await br.close();
sv.close();
console.log(JSON.stringify(kq));
process.exit(kq.some(x => x.loi.length) ? 1 : 0);
