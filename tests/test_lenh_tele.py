# -*- coding: utf-8 -*-
"""canh_bao/lenh_tele.py – lệnh nhắn Telegram → nhap.txt (giả lập Telegram & GitHub API)."""
import base64
import json
from datetime import datetime

from canh_bao import lenh_tele as T

NGAY = 1793600000                                                      # 02/11/2026 giờ VN


def _tin(uid, text, chat=111):
    return {"update_id": uid, "message": {"date": NGAY, "chat": {"id": chat}, "text": text}}


def test_dong_lenh_them_ngay_va_khong_chen_ghi_chu():
    d = T.dong_lenh(_tin(7, "BAN MWG 21 74,5\n\n21/10 NAP 5 # x\nLAI_TRUNG 6T 7,5"))
    assert d == ["02/11/2026 BAN MWG 21 74,5  # tg:7", "21/10 NAP 5 x  # tg:7", "LAI_TRUNG 6T 7,5  # tg:7"]


def test_loc_tin_chi_chu_quy_va_them_vao_khong_trung():
    tin, hoi, la = T.loc_tin([_tin(1, "NAP 5"), _tin(2, "NAP 9", chat=999), _tin(3, "/help")], 111)
    assert [u["update_id"] for u in tin] == [1] and hoi and la == 1
    nd, moi = T.them_vao("# mẫu\n", ["02/11/2026 NAP 5  # tg:1"])
    assert moi and nd.endswith("NAP 5  # tg:1\n")
    assert T.them_vao(nd, ["02/11/2026 NAP 5  # tg:1"])[1] == []        # chạy lại → không ghi lần 2


def test_chay_ghi_file_xac_nhan_va_tra_loi(monkeypatch, capsys):
    file = {"nd": "# mẫu\n# ✔ 30/10: 30/10 BAN MWG HET\n"}
    goi = []

    def gia(url, data=None, headers=None, method=None, cho=0):
        goi.append((url.split("?")[0].rsplit("/", 1)[-1], method, data))
        if "getUpdates" in url and "offset" not in url:
            return {"result": [_tin(5, "BAN MWG 21 74,5"), _tin(6, "RUT 1", chat=999)]}
        if url.endswith("nhap.txt") and method is None:
            return {"sha": "s1", "content": base64.b64encode(file["nd"].encode()).decode()}
        if method == "PUT":
            file["nd"] = base64.b64decode(data["content"]).decode()
        return {}

    monkeypatch.setattr(T, "_goi", gia)
    env = {"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "111", "DANH_MUC_TOKEN_GHI": "g"}
    assert T.chay(env) == 1
    assert file["nd"].endswith("02/11/2026 BAN MWG 21 74,5  # tg:5\n") and "RUT" not in file["nd"]
    ten = [g[0] for g in goi if g[0] != "ket_qua.jsonl"]
    assert ten.index("getUpdates", 1) > ten.index("nhap.txt") and ten[-1] == "sendMessage"   # ghi xong mới xác nhận
    out = capsys.readouterr().out
    assert "MWG" not in out and "74" not in out                          # log công khai: chỉ số lượng


def test_cho_long_poll(monkeypatch):
    goi = []
    monkeypatch.setattr(T, "_goi", lambda url, data=None, headers=None, method=None, cho=0: goi.append((url, cho)) or {})
    T.chay({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "1", "DANH_MUC_TOKEN_GHI": "g", "CHO": "300"})
    assert "timeout=50&" in goi[0][0] and goi[0][1] == 50                # chặn 50s, urlopen chờ lâu hơn


def _nut(uid, data, mid=7, date=NGAY, chat=111):
    return {"update_id": uid, "callback_query": {"id": f"c{uid}", "data": data,
                                                 "message": {"message_id": mid, "date": date, "chat": {"id": chat}}}}


def test_bam_nut_hoi_xac_nhan_roi_moi_dat(monkeypatch, capsys):
    goi, ups = [], [_nut(1, "dl|M|REE|237|46600", mid=7),                       # chọn số CP → chỉ hỏi, chưa đặt
                    _nut(2, "dl|B|VIX", mid=8, date=NGAY - 4 * 3600),            # tin > 3 giờ
                    _nut(3, "dx|M|REE|237|46600", mid=9), _nut(4, "dx|M|REE|237|46600", mid=9),   # ✅ 2 lần
                    _nut(5, "dx|M|REE|100|46600", mid=11, date=NGAY - 400),      # ✅ quá 5 phút
                    _nut(6, "dl|M|REE|237|46600", chat=999), _nut(7, "dt", mid=12), _nut(8, "dh", mid=7)]

    def gia(url, data=None, headers=None, method=None, cho=0):
        goi.append((url.split("?")[0].rsplit("/", 1)[-1], data))
        return {"result": ups} if "getUpdates" in url and "offset" not in url else None

    monkeypatch.setattr(T, "_goi", gia)
    monkeypatch.setattr(T.time, "time", lambda: NGAY + 60)
    assert T.chay({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "111", "DANH_MUC_TOKEN_GHI": "g"}) == 1
    ten = [g[0] for g in goi]
    xn = [g[1] for g in goi if g[0] == "sendMessage"]
    assert len(xn) == 1 and xn[0]["text"] == "Xác nhận MUA 200 + 37 lẻ REE (LO ≤ 46.600đ)?" and xn[0]["reply_to_message_id"] == 7
    assert [b["callback_data"] for b in xn[0]["reply_markup"]["inline_keyboard"][0]] == ["dx|M|REE|237|46600", "dt"]
    gd = [g[1] for g in goi if g[0] == "dispatches"]
    assert len(gd) == 1 and gd[0]["client_payload"] == {"id": "111:9", "ben": "M", "ma": "REE", "kl": 237, "gia": 46600,
                                                        "luc": NGAY + 60, "chat": "111", "tin": 9}
    sua = [(g[1]["message_id"], g[1]["text"][:2]) for g in goi if g[0] == "editMessageText"]
    assert sua == [(9, "⏳ "), (11, "⌛ ")]
    assert [g[1]["message_id"] for g in goi if g[0] == "deleteMessage"] == [12]          # ❌ Thôi: xoá tin xác nhận
    assert [g[1]["message_id"] for g in goi if g[0] == "editMessageReplyMarkup"] == [7]  # ❌ Bỏ trên tin gốc
    assert ten.index("getUpdates", 1) < ten.index("dispatches")
    out = capsys.readouterr().out
    assert "REE" not in out and "8 nút bấm, 1 lệnh gửi máy Mac" in out


def test_chu_kl():
    assert [T.chu_kl(n) for n in (237, 200, 37, 1250)] == ["200 + 37 lẻ", "200", "37 lẻ", "1.200 + 50 lẻ"]


def test_hai_bot_doc_song_song(monkeypatch):
    goi = []
    monkeypatch.setattr(T, "_goi", lambda url, data=None, headers=None, method=None, cho=0: goi.append(url) or {})
    T.chay({"TELEGRAM_TOKEN": "a", "TELEGRAM_TOKEN_DANH_MUC": "b", "TELEGRAM_CHAT_ID": "1", "DANH_MUC_TOKEN_GHI": "g"})
    assert sorted(u.split("/getUpdates")[0][-1] + ("cb" if "callback" in u else "") for u in goi if "getUpdates" in u) \
        == ["acb", "b"]


def test_chuyen_ket_qua_xoa_truoc_roi_gui(monkeypatch, capsys):
    goi = []
    nd = base64.b64encode('"✅ Đã đặt MUA 300 REE"\n"✘ lỗi"\n{"text": "✅ MUA 37 lẻ REE", "ok": true, "tin": 7}\n'
                          '{"text": "⚠ VIX chưa khớp", "nut": [[["🛑 Bán lại", "dl|B|VIX"]]]}\n'.encode()).decode()

    def gia(url, data=None, headers=None, method=None, cho=0):
        goi.append((url.rsplit("/", 1)[-1].split("?")[0], method, data))
        if url.endswith("ket_qua.jsonl") and method is None:
            return {"sha": "s", "content": nd}
        return {}

    monkeypatch.setattr(T, "_goi", gia)
    T.chay({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "111", "DANH_MUC_TOKEN_GHI": "g"})
    ten = [(g[0], g[1]) for g in goi]
    assert ten.index(("ket_qua.jsonl", "DELETE")) < ten.index(("sendMessage", None))
    gui = [g[2] for g in goi if g[0] == "sendMessage"]
    assert [g["text"] for g in gui] == ["✅ Đã đặt MUA 300 REE", "✘ lỗi", "⚠ VIX chưa khớp"]
    assert gui[2]["reply_markup"] == {"inline_keyboard": [[{"text": "🛑 Bán lại", "callback_data": "dl|B|VIX"}]]}
    out = capsys.readouterr().out
    assert [g[2]["text"] for g in goi if g[0] == "editMessageText"] == ["✅ MUA 37 lẻ REE"]   # sửa tin xác nhận
    assert "REE" not in out and "chuyển 4 kết quả" in out


def test_tu_dat_id_theo_ngay(monkeypatch, capsys):
    goi = []
    monkeypatch.setattr(T, "_goi", lambda url, data=None, headers=None, method=None, cho=0: goi.append((url, data)))
    env = {"DANH_MUC_TOKEN_GHI": "g", "TELEGRAM_CHAT_ID": "111"}
    assert T.tu_dat("M", "REE", 300, 46600, env) and T.tu_dat("B", "VIX", env=env)
    yc = [d["client_payload"] for u, d in goi]
    hom_nay = datetime.now(T.VN).strftime("%Y-%m-%d")
    assert [y["id"] for y in yc] == [f"tu:M:REE:{hom_nay}", f"tu:B:VIX:{hom_nay}"]   # mỗi ngày 1 lệnh tự động / mã / bên
    assert (yc[0]["kl"], yc[0]["gia"], yc[0]["chat"], yc[0]["tu"]) == (300, 46600, "111", True)
    assert goi[0][0].endswith("/repos/mihhle2006-beep/danh-muc/dispatches")
    assert T.tu_dat("M", "REE", 300, 46600, {}) is False and len(goi) == 2
    assert "REE" not in capsys.readouterr().out
