# -*- coding: utf-8 -*-
"""canh_bao/lenh_tele.py – lệnh nhắn Telegram → nhap.txt (giả lập Telegram & GitHub API)."""
import base64
import json

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
    ten = [g[0] for g in goi]
    assert ten.index("getUpdates", 1) > ten.index("nhap.txt") and ten[-1] == "sendMessage"   # ghi xong mới xác nhận
    out = capsys.readouterr().out
    assert "MWG" not in out and "74" not in out                          # log công khai: chỉ số lượng


def test_cho_long_poll(monkeypatch):
    goi = []
    monkeypatch.setattr(T, "_goi", lambda url, data=None, headers=None, method=None, cho=0: goi.append((url, cho)) or {})
    T.chay({"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "1", "DANH_MUC_TOKEN_GHI": "g", "CHO": "300"})
    assert "timeout=50&" in goi[0][0] and goi[0][1] == 50                # chặn 50s, urlopen chờ lâu hơn
