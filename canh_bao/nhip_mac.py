# -*- coding: utf-8 -*-
"""
MÁY MAC CÒN ĐỒNG BỘ DNSE KHÔNG – vòng quét 15' gọi mỗi lượt. Máy Mac (workflow danh-muc "Dong bo DNSE") đồng bộ thành công
là đẩy 1 commit rỗng lên nhánh nhip-dnse; trong phiên (T2–T6 09:15–14:45) nhịp cũ hơn IM_PHUT phút → nhắn Telegram 1 lần
mỗi lần chạy vòng quét (cờ trong /tmp). Không đọc được nhánh (chưa có nhịp, token) → im lặng, không báo nhầm.
Chỉ thư viện chuẩn. Biến môi trường: DANH_MUC_TOKEN, DANH_MUC_REPO, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
IM_PHUT = 35
CO = "/tmp/da_bao_mac"


def _get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def nhip_cuoi(env=os.environ, get=_get):
    """Thời điểm nhịp đồng bộ gần nhất (UTC) – None khi không đọc được."""
    repo, tk = env.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc", env.get("DANH_MUC_TOKEN")
    if not tk:
        return None
    try:
        d = get(f"https://api.github.com/repos/{repo}/commits/nhip-dnse", tk)
        return datetime.fromisoformat(d["commit"]["committer"]["date"].replace("Z", "+00:00"))
    except Exception:                                                   # noqa: BLE001 – không đọc được → không báo
        return None


def can_bao(bay_gio, luc):
    """→ số phút im nếu cần báo, không thì None."""
    vn = bay_gio.astimezone(VN)
    if vn.weekday() >= 5 or not 915 <= vn.hour * 100 + vn.minute <= 1445 or luc is None:
        return None
    phut = int((bay_gio - luc).total_seconds() // 60)
    return phut if phut > IM_PHUT else None


def chay(env=os.environ, bay_gio=None, get=_get, gui=None):
    if os.path.exists(CO):
        return 0
    bay_gio = bay_gio or datetime.now(timezone.utc)
    luc = nhip_cuoi(env, get)
    if luc is None and not os.path.exists(CO + "_doc"):                # 1 dòng log / lần chạy: biết token / nhánh có vấn đề
        print("Nhịp DNSE: chưa đọc được nhánh nhip-dnse (chưa có nhịp hoặc DANH_MUC_TOKEN thiếu quyền Contents) – không báo")
        open(CO + "_doc", "w").close()
    phut = can_bao(bay_gio, luc)
    if phut is None:
        return 0
    tin = (f"⚠ MÁY MAC KHÔNG ĐỒNG BỘ DNSE {phut // 60} giờ {phut % 60} phút (lần cuối {luc.astimezone(VN):%H:%M %d/%m}) – "
           "danh mục, tiền, lệnh khớp chưa cập nhật. Mở máy / kiểm tra mạng & runner GitHub (Actions → Runners).")
    (gui or _gui)(env, tin)
    open(CO, "w").close()
    print(f"Nhịp DNSE: im {phut} phút → đã báo")
    return 1


def _gui(env, tin):
    tk, chat = env.get("TELEGRAM_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if tk and chat:
        data = urllib.parse.urlencode({"chat_id": chat, "text": tin}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tk}/sendMessage", data, timeout=20).read()


if __name__ == "__main__":
    try:
        chay()
    except Exception as e:                                              # noqa: BLE001 – không làm hỏng vòng quét
        print(f"⚠ Nhịp DNSE lỗi: {type(e).__name__}")
