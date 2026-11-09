// MẤT MẠNG (Tra cứu mã / Biểu đồ): lấy mạng trước, lưu bản vừa tải; mất mạng → trả bản đã lưu (trang + dữ liệu đã xem).
// Khoá = đường dẫn không kèm tham số (?t= chống đệm 5 phút, ?v= / ?ban= bản trang) → mỗi file chỉ giữ 1 bản mới nhất.
// shortcut: không giới hạn dung lượng – mỗi mã đã xem giữ 1 bản (~vài trăm KB); cần thì xoá khi quá ~300 file.
const KHO = "tra-cuu-v1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== self.location.origin) return;
  const khoa = u.origin + u.pathname;
  e.respondWith(fetch(r).then(res => {
    if (res.ok && res.type === "basic") { const c = res.clone(); caches.open(KHO).then(k => k.put(khoa, c)).catch(() => {}); }
    return res;
  }).catch(() => caches.match(khoa).then(c => c || Response.error())));
});
