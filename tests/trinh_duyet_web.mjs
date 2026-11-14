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
