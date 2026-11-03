# -*- coding: utf-8 -*-
"""
NHẬP LỆNH QUA TELEGRAM → nhap.txt (repo riêng tư danh-muc). Nhắn cho bot danh mục đúng cú pháp nhap.txt, mỗi dòng 1
lệnh – VD "BAN MWG 21 74,5" · "NAP 5" · "TRUNG 5 6" · "LAI_TRUNG 6T 7,5 12T 7,6". Dòng không ghi ngày → thêm ngày gửi tin.
Lần chạy danh mục kế tiếp áp lệnh (trong phiên: vòng quét 15' gọi danh mục ngay; ngoài phiên: 08:30 / 15:02), dòng sai
thành "# ⚠ …" như nhập tay. "/help" → trả cú pháp.
  • Chỉ nhận tin từ đúng chat chủ quỹ (TELEGRAM_CHAT_ID_DANH_MUC / TELEGRAM_CHAT_ID); tin người khác bỏ qua.
  • Mỗi dòng ghi kèm "# tg:<update_id>" → chạy trùng (vòng quét + lịch mỗi giờ) không ghi 2 lần.
  • CHO=<giây> (≤ 50): chờ tin tới (long-poll) – vòng quét gọi lặp trong lúc đợi mốc 15' → trong phiên trả lời sau vài giây.
  • Repo bot CÔNG KHAI → log chỉ in SỐ LƯỢNG, không in nội dung lệnh; trả lời qua Telegram (riêng tư).
TỰ ĐẶT LỆNH (tu_dat, gọi từ chay.py): tin CHẠM CẮT LỖ → bán hết (lô chẵn + lô lẻ) – không cần bấm.
NÚT trên tin cảnh báo (bot TELEGRAM_TOKEN, chat TELEGRAM_CHAT_ID) – LUÔN HỎI LẠI: bấm "🛒 <số CP>" (tin MUA ★ / mã dự
phòng) hoặc "🛑 Bán hết" → 1 tin xác nhận [✅ Mua / Bán] [❌ Thôi] (5 phút) → ✅: repository_dispatch "dat_lenh" tới danh-muc
→ máy Mac đặt lệnh (dmuc/dnse_lenh.py theo_yeu_cau, tự tách lô chẵn + lô lẻ), ghi kết quả vào danh-muc
lenh_dat/ket_qua.jsonl → mỗi lần chạy chuyển kết quả: SỬA tin xác nhận thành dòng ✅ / ✘ (không thêm tin); ❌ Thôi → xoá
tin xác nhận. Nút trên tin > 3 giờ không nhận. Bot danh mục khác bot cảnh báo → đọc 2 bot song song.
Chỉ thư viện chuẩn Python.  Biến môi trường: TELEGRAM_TOKEN_DANH_MUC (hoặc TELEGRAM_TOKEN), TELEGRAM_CHAT_ID_DANH_MUC
(hoặc TELEGRAM_CHAT_ID), DANH_MUC_TOKEN_GHI (Contents: Read and write repo danh-muc), DANH_MUC_REPO.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
FILE = "nhap.txt"
FILE_KQ = "lenh_dat/ket_qua.jsonl"                                       # kết quả lệnh nút do máy Mac ghi
NUT = re.compile(r"d[lx]\|(?:M\|[A-Z0-9]{3}\|\d{1,6}\|\d{4,7}|B\|[A-Z0-9]{3})")   # dl = nút trên tin, dx = ✅
CO_NGAY = re.compile(r"(^|\s)\d{1,2}[/\-]\d{1,2}([/\-]\d{2,4})?(\s|$)")
HUONG_DAN = ("📝 Nhắn lệnh cho bot, mỗi dòng 1 lệnh (không ghi ngày → lấy ngày gửi tin):\n"
             "  BAN MWG 21 74,5 · BAN VIB HET 16,2 · HPG 1000 27,5 (mua; bỏ giá → lấy theo khuyến nghị)\n"
             "  NAP 5 (5 triệu) · RUT 2.000.000 · TIEN 6.041.733 (đặt đúng tiền mặt)\n"
             "  TRUNG 5 6 (ấp 5 tr kỳ 6T) · THU 3 · THU HET · LAI_TRUNG 6T 7,5 12T 7,6\n"
             "Lệnh khớp, tiền, nạp / rút trên DNSE tự đồng bộ (trong phiên mỗi 10', ngoài phiên mỗi 3 giờ – khi máy Mac "
             "mở) → chỉ cần nhắn lệnh ở app khác, Trứng vàng, bảng lãi. Tin không bắt đầu bằng / đều coi là lệnh.\n"
             "🛒 Nút trên tin MUA: chọn số CP → ✅ xác nhận mới đặt lệnh (máy Mac). Chạm cắt lỗ: tự bán hết – máy Mac tắt thì "
             "bán tay trên app DNSE. 08:40 duyệt Smart OTP 1 lần cho cả ngày.")


def _goi(url, data=None, headers=None, method=None, cho=0):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=30 + cho) as r:
        return json.loads(r.read().decode() or "null")


def dong_lenh(tin):
    """Tin Telegram (update) → [dòng nhap.txt] (bỏ dòng trống; thêm ngày gửi khi dòng chưa có ngày)."""
    m = tin.get("message") or tin.get("edited_message") or {}
    ngay = datetime.fromtimestamp(int(m.get("date") or 0), VN)
    out = []
    for d in str(m.get("text") or "").splitlines():
        d = " ".join(d.replace("#", " ").split())[:120]             # 1 dòng, không chèn ghi chú / dòng lạ vào file
        if not d:
            continue
        if not CO_NGAY.search(d) and not d.upper().startswith("LAI_TRUNG"):
            d = f"{ngay:%d/%m/%Y} {d}"
        out.append(f"{d}  # tg:{tin['update_id']}")
    return out


def loc_tin(updates, chat_id):
    """→ (tin của chủ quỹ, có hỏi /help, số tin bị bỏ vì không phải chủ quỹ)."""
    cua_chu, hoi, la = [], False, 0
    for u in updates or []:
        m = u.get("message") or u.get("edited_message") or {}
        if str((m.get("chat") or {}).get("id")) != str(chat_id):
            la += 1
            continue
        if str(m.get("text") or "").strip().startswith("/"):
            hoi = True
            continue
        cua_chu.append(u)
    return cua_chu, hoi, la


def them_vao(noi_dung, dong):
    """Nối dòng mới vào nhap.txt, bỏ dòng có tg:<id> đã ghi (chạy trùng). → (nội dung mới, [dòng đã thêm])."""
    da = set(re.findall(r"tg:(\d+)", noi_dung))
    moi = [d for d in dong if re.search(r"tg:(\d+)", d)[1] not in da]
    if not moi:
        return noi_dung, []
    return noi_dung.rstrip("\n") + "\n" + "\n".join(moi) + "\n", moi


def chu_kl(n):
    """237 → '200 + 37 lẻ' · 200 → '200' · 37 → '37 lẻ' (lô chẵn + lô lẻ – máy Mac đặt 2 lệnh)."""
    c, le = n // 100 * 100, n % 100
    return " + ".join([f"{c:,}".replace(",", ".")] * bool(c) + [f"{le} lẻ"] * bool(le))


def mo_ta_nut(data):
    p = data.split("|")
    if p[1] == "M":
        return f"MUA {chu_kl(int(p[3]))} {p[2]} (LO ≤ {int(p[4]):,}đ)".replace(",", ".")
    return f"BÁN HẾT {p[2]} (lô chẵn + lẻ, giá khớp −2 %)"


def gui_may_mac(yc, gh, repo):
    """Yêu cầu lệnh → repository_dispatch "dat_lenh" (repo danh-muc) → máy Mac đặt lệnh (dmuc/dnse_lenh.theo_yeu_cau)."""
    _goi(f"https://api.github.com/repos/{repo}/dispatches", {"event_type": "dat_lenh", "client_payload": yc},
         {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}, "POST")


def tu_dat(ben, ma, kl=0, gia=0, env=os.environ):
    """Tin CHẠM CẮT LỖ (chay.py) → gửi lệnh tới máy Mac luôn, không nút. id theo bên + mã + ngày → mỗi ngày
    tối đa 1 lệnh tự động / mã / bên (máy Mac bỏ id trùng). → True khi đã gửi. Log công khai: không in mã / số lượng."""
    gh, chat = env.get("DANH_MUC_TOKEN_GHI"), env.get("TELEGRAM_CHAT_ID")
    if not (gh and chat):
        return False
    bg = datetime.now(VN)
    try:
        gui_may_mac({"id": f"tu:{ben}:{ma}:{bg:%Y-%m-%d}", "ben": ben, "ma": ma, "kl": int(kl), "gia": int(gia),
                     "luc": int(bg.timestamp()), "chat": str(chat), "tu": True},
                    gh, env.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc")
        return True
    except (urllib.error.URLError, OSError) as e:
        print(f"⚠ Gửi lệnh tự động tới máy Mac lỗi: {type(e).__name__}")
        return False


def xu_ly_nut(api, cqs, chat, gh, repo, bay_gio=None):
    """Bấm nút (callback_query) trên tin của chat chủ quỹ: dl → tin xác nhận (trả lời tin gốc) · dx (✅, ≤ 5 phút) → gửi
    lệnh tới máy Mac, tin xác nhận thành dòng ⏳ · dt (❌ Thôi) → xoá tin xác nhận · dh (❌ Bỏ trên tin gốc) → bỏ hết nút.
    → số lệnh đã gửi máy Mac."""
    bay, gui, xong = bay_gio or time.time(), 0, set()
    for cq in cqs:
        m, data = cq.get("message") or {}, str(cq.get("data") or "")
        tin, tra = m.get("message_id"), {"callback_query_id": cq.get("id")}
        if str((m.get("chat") or {}).get("id")) != str(chat) or not (NUT.fullmatch(data) or data in ("dh", "dt")):
            _goi(f"{api}/answerCallbackQuery", {**tra, "text": "Không nhận nút này"})
            continue
        tuoi = bay - int(m.get("date") or 0)
        if data.startswith("dl") and tuoi > 3 * 3600:
            _goi(f"{api}/answerCallbackQuery", {**tra, "text": "Tin quá 3 giờ – không đặt lệnh từ tin này"})
            continue
        _goi(f"{api}/answerCallbackQuery", tra)
        if data == "dh":
            _goi(f"{api}/editMessageReplyMarkup", {"chat_id": chat, "message_id": tin,
                                                   "reply_markup": {"inline_keyboard": []}})
            continue
        if data == "dt":
            _goi(f"{api}/deleteMessage", {"chat_id": chat, "message_id": tin})
            continue
        if data.startswith("dl"):
            _goi(f"{api}/sendMessage", {"chat_id": chat, "reply_to_message_id": tin, "text": f"Xác nhận {mo_ta_nut(data)}?",
                                        "reply_markup": {"inline_keyboard": [[
                                            {"text": "✅ Mua" if "|M|" in data else "✅ Bán", "callback_data": "dx" + data[2:]},
                                            {"text": "❌ Thôi", "callback_data": "dt"}]]}})
            continue
        if tin in xong:                                                 # bấm ✅ 2 lần trong 1 lượt đọc
            continue
        xong.add(tin)

        def sua(t):
            _goi(f"{api}/editMessageText", {"chat_id": chat, "message_id": tin, "text": t})
        if tuoi > 300:
            sua("⌛ Quá 5 phút chưa xác nhận – không đặt; bấm lại nút trên tin")
            continue
        p = data.split("|")
        yc = {"id": f"{chat}:{tin}", "ben": p[1], "ma": p[2], "kl": int(p[3]) if p[1] == "M" else 0,
              "gia": int(p[4]) if p[1] == "M" else 0, "luc": int(bay), "chat": str(chat), "tin": tin}
        try:
            gui_may_mac(yc, gh, repo)
        except urllib.error.HTTPError as e:
            sua(f"⚠ Không gửi được lệnh (GitHub HTTP {e.code}) – đặt tay trên app DNSE")
            continue
        sua(f"⏳ Đã gửi {mo_ta_nut(data)} – lần đầu trong ngày: duyệt Smart OTP")
        gui += 1
    return gui


def chuyen_ket_qua(tg, chat, gh, repo):
    """Kết quả lệnh nút (máy Mac ghi FILE_KQ ở danh-muc) → Telegram. Xoá file (theo sha) TRƯỚC khi gửi: không gửi trùng;
    máy Mac vừa ghi thêm → xoá lỗi 409 → để lượt sau. → số kết quả đã gửi."""
    url = f"https://api.github.com/repos/{repo}/contents/{FILE_KQ}"
    h = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
    try:
        f = _goi(url, headers=h)
        if not (isinstance(f, dict) and f.get("sha")):
            return 0
        _goi(url, {"message": "lenh_dat: đã chuyển kết quả lên Telegram", "sha": f["sha"]}, h, "DELETE")
    except urllib.error.HTTPError:                                      # 404 = chưa có kết quả nào
        return 0
    ds = [d for d in base64.b64decode(f["content"]).decode("utf-8").splitlines() if d.strip()]
    api = f"https://api.telegram.org/bot{tg}"
    for d in ds:
        try:
            d = json.loads(d)
        except ValueError:
            pass
        d = d if isinstance(d, dict) else {"text": str(d)}
        if d.get("tin"):                                                # lệnh bấm nút: sửa tin xác nhận thành kết quả
            try:
                _goi(f"{api}/editMessageText", {"chat_id": chat, "message_id": d["tin"], "text": d["text"]})
                continue
            except urllib.error.HTTPError:
                pass
        nut = {"reply_markup": {"inline_keyboard": [[{"text": t, "callback_data": c} for t, c in h] for h in d["nut"]]}} \
            if d.get("nut") else {}                                     # VD ⚠ bán chưa khớp → [🛑 Bán lại theo giá mới]
        _goi(f"{api}/sendMessage", {"chat_id": chat, "text": d["text"], **nut})
    return len(ds)


def _mot_bot(tg, chat, chat_nut, gh, repo, cho, loai):
    """Đọc 1 bot (long-poll): tin lệnh → nhap.txt (chat), nút đặt lệnh → máy Mac (chat_nut). → số dòng ghi + lệnh gửi."""
    api = f"https://api.telegram.org/bot{tg}"
    try:
        ups = _goi(f"{api}/getUpdates?timeout={cho}&allowed_updates={urllib.parse.quote(json.dumps(loai))}",
                   cho=cho).get("result") or []
    except urllib.error.HTTPError as e:                     # 409 = webhook / lần đọc khác (lịch mỗi giờ) chen ngang
        print(f"Lệnh Telegram: getUpdates HTTP {e.code} – bỏ qua")
        return 0
    if not ups:
        return 0
    cqs = [u["callback_query"] for u in ups if "callback_query" in u]
    tin, hoi, la = loc_tin([u for u in ups if "callback_query" not in u], chat)
    dong = [d for u in tin for d in dong_lenh(u)]
    moi = []
    if dong:
        url = f"https://api.github.com/repos/{repo}/contents/{FILE}"
        h = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
        for lan in range(3):                                            # sha cũ (bot khác vừa ghi) → đọc lại
            f = _goi(url, headers=h)
            cu = base64.b64decode(f["content"]).decode("utf-8")
            moi_nd, moi = them_vao(cu, dong)
            if not moi:
                break
            try:
                _goi(url, {"message": f"nhap.txt: {len(moi)} dòng từ Telegram", "sha": f["sha"],
                           "content": base64.b64encode(moi_nd.encode("utf-8")).decode()}, h, "PUT")
                break
            except urllib.error.HTTPError as e:
                if e.code != 409 or lan == 2:
                    raise
    _goi(f"{api}/getUpdates?offset={max(u['update_id'] for u in ups) + 1}&timeout=0")   # xác nhận đã đọc
    tra_loi = []
    if moi:
        tra_loi.append("📝 Đã ghi vào nhap.txt:\n" + "\n".join(d.split("  # tg:")[0] for d in moi)
                       + "\n→ áp ở lần chạy danh mục kế tiếp (trong phiên ~15 phút; ngoài phiên 08:30 / 15:02)")
    if hoi:
        tra_loi.append(HUONG_DAN)
    for t in tra_loi:
        _goi(f"{api}/sendMessage", {"chat_id": chat, "text": t})
    so_nut = xu_ly_nut(api, cqs, chat_nut, gh, repo) if cqs else 0      # sau xác nhận đọc: lỗi giữa chừng → bấm lại
    print(f"Lệnh Telegram: {len(tin)} tin · ghi {len(moi)} dòng · bỏ {la} tin không phải chủ quỹ"
          + (f" · {len(cqs)} nút bấm, {so_nut} lệnh gửi máy Mac" if cqs else ""))
    return len(moi) + so_nut


def chay(env=os.environ):
    tg = env.get("TELEGRAM_TOKEN_DANH_MUC") or env.get("TELEGRAM_TOKEN")
    chat = env.get("TELEGRAM_CHAT_ID_DANH_MUC") or env.get("TELEGRAM_CHAT_ID")
    tg_nut, chat_nut = env.get("TELEGRAM_TOKEN") or tg, env.get("TELEGRAM_CHAT_ID") or chat   # bot gửi tin cảnh báo
    gh, repo = env.get("DANH_MUC_TOKEN_GHI"), env.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc"
    if not (tg and chat and gh):
        print("Lệnh Telegram: thiếu TELEGRAM_TOKEN / CHAT_ID / DANH_MUC_TOKEN_GHI – bỏ qua")
        return 0
    cho = max(0, min(50, int(env.get("CHO") or 0)))                     # long-poll: tin tới là trả lời ngay
    if tg_nut == tg:
        n = _mot_bot(tg, chat, chat_nut, gh, repo, cho, ["message", "callback_query"])
    else:
        with ThreadPoolExecutor(2) as ex:                               # 2 bot: long-poll song song, bot nào có tin trả lời ngay
            viec = [ex.submit(_mot_bot, tg, chat, chat_nut, gh, repo, cho, ["message"]),
                    ex.submit(_mot_bot, tg_nut, chat, chat_nut, gh, repo, cho, ["callback_query"])]
            n = sum(v.result() for v in viec)
    kq = chuyen_ket_qua(tg_nut, chat_nut, gh, repo)
    if kq:
        print(f"Lệnh Telegram: chuyển {kq} kết quả lệnh nút từ máy Mac")
    return n


if __name__ == "__main__":
    try:
        chay()
    except Exception as e:                                              # noqa: BLE001 – không làm hỏng vòng quét
        print(f"⚠ Lệnh Telegram lỗi: {type(e).__name__}")
        sys.exit(0)
