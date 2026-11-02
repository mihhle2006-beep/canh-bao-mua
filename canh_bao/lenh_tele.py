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
Chỉ thư viện chuẩn Python.  Biến môi trường: TELEGRAM_TOKEN_DANH_MUC (hoặc TELEGRAM_TOKEN), TELEGRAM_CHAT_ID_DANH_MUC
(hoặc TELEGRAM_CHAT_ID), DANH_MUC_TOKEN_GHI (Contents: Read and write repo danh-muc), DANH_MUC_REPO.
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
FILE = "nhap.txt"
CO_NGAY = re.compile(r"(^|\s)\d{1,2}[/\-]\d{1,2}([/\-]\d{2,4})?(\s|$)")
HUONG_DAN = ("📝 Nhắn lệnh cho bot, mỗi dòng 1 lệnh (không ghi ngày → lấy ngày gửi tin):\n"
             "  BAN MWG 21 74,5 · BAN VIB HET 16,2 · HPG 1000 27,5 (mua; bỏ giá → lấy theo khuyến nghị)\n"
             "  NAP 5 (5 triệu) · RUT 2.000.000 · TIEN 6.041.733 (đặt đúng tiền mặt)\n"
             "  TRUNG 5 6 (ấp 5 tr kỳ 6T) · THU 3 · THU HET · LAI_TRUNG 6T 7,5 12T 7,6\n"
             "Lệnh khớp, tiền, nạp / rút trên DNSE tự đồng bộ (trong phiên mỗi 10', ngoài phiên mỗi 3 giờ – khi máy Mac "
             "mở) → chỉ cần nhắn lệnh ở app khác, Trứng vàng, bảng lãi. Tin không bắt đầu bằng / đều coi là lệnh.")


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


def chay(env=os.environ):
    tg = env.get("TELEGRAM_TOKEN_DANH_MUC") or env.get("TELEGRAM_TOKEN")
    chat = env.get("TELEGRAM_CHAT_ID_DANH_MUC") or env.get("TELEGRAM_CHAT_ID")
    gh, repo = env.get("DANH_MUC_TOKEN_GHI"), env.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc"
    if not (tg and chat and gh):
        print("Lệnh Telegram: thiếu TELEGRAM_TOKEN / CHAT_ID / DANH_MUC_TOKEN_GHI – bỏ qua")
        return 0
    api = f"https://api.telegram.org/bot{tg}"
    cho = max(0, min(50, int(env.get("CHO") or 0)))                     # long-poll: tin tới là trả lời ngay
    try:
        ups = _goi(f"{api}/getUpdates?timeout={cho}&allowed_updates=%5B%22message%22%5D", cho=cho).get("result") or []
    except urllib.error.HTTPError as e:                     # 409 = webhook / lần đọc khác (lịch mỗi giờ) chen ngang
        print(f"Lệnh Telegram: getUpdates HTTP {e.code} – bỏ qua")
        return 0
    if not ups:
        return 0
    tin, hoi, la = loc_tin(ups, chat)
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
    print(f"Lệnh Telegram: {len(tin)} tin · ghi {len(moi)} dòng · bỏ {la} tin không phải chủ quỹ")
    return len(moi)


if __name__ == "__main__":
    try:
        chay()
    except Exception as e:                                              # noqa: BLE001 – không làm hỏng vòng quét
        print(f"⚠ Lệnh Telegram lỗi: {type(e).__name__}")
        sys.exit(0)
