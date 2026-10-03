# -*- coding: utf-8 -*-
"""Telegram + nội dung tin + chống báo trùng (file trạng thái) + lịch sử tín hiệu."""
import json
import os

import pandas as pd
import requests

from . import cau_hinh as C

KY_HIEU = {True: "✔", False: "✘", None: "–"}


def gui(noi_dung):
    token, chat = os.environ.get("TELEGRAM_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    print(noi_dung)
    if not (token and chat):
        print("(chưa đặt TELEGRAM_TOKEN / TELEGRAM_CHAT_ID → chỉ in ra màn hình)")
        return False
    ok = True
    for i in range(0, len(noi_dung), 3900):
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": noi_dung[i:i + 3900]}, timeout=30)
        if r.status_code != 200:
            print("Telegram lỗi:", r.text[:200])
            ok = False
    return ok


def _f(x, le=2):
    return "N/A" if x is None or x != x else f"{x:,.{le}f}"


def dong_khung(kq):
    out = []
    for k in kq["khung"]:
        them = f" ({k['diem']}/{k['tong_diem']} điểm cộng)" if k["tong_diem"] and k["khung"] == "Ngày" else ""
        out.append(f"{k['khung']} {KY_HIEU[k['dat']]}{them}")
    return " | ".join(out)


def dong_muc_tieu(kq):
    """Giá mục tiêu / cắt lỗ / XS đạt mục tiêu – cắt lỗ / 3 kịch bản."""
    g, d = kq["gia"], []
    if kq["muc_tieu"] == kq["muc_tieu"]:
        d.append(f"🎯 Mục tiêu {_f(kq['muc_tieu'])} ({(kq['muc_tieu'] / g - 1) * 100:+.1f}%, {kq['nguon_mt']}) | "
                 f"✘ Cắt lỗ {_f(kq['cat_lo'])} ({(kq['cat_lo'] / g - 1) * 100:+.1f}%) | R/R {_f(kq['rr'], 1)}")
    pt = kq.get("ptcp") or {}
    if pt.get("muc_tieu") and "12 tháng" not in kq.get("nguon_mt", ""):
        d.append(f"   Mục tiêu dài hạn 12 tháng (ptcp): {_f(pt['muc_tieu'])} ({(pt['muc_tieu'] / g - 1) * 100:+.1f}%, "
                 f"{pt.get('moc_muc_tieu', '')})")
    x = kq.get("xac_suat")
    if x:
        d += [f"Xác suất lịch sử ({x['H']} phiên, luật T+2, sau phí):",
              f"  • Chạm MỤC TIÊU trước: {x['muc_tieu']:.0f}%" + (f" (~{x['phien_muc_tieu']:.0f} phiên)"
                                                               if x["phien_muc_tieu"] == x["phien_muc_tieu"] else ""),
              f"  • Chạm CẮT LỖ trước: {x['cat_lo']:.0f}%",
              f"  • Không chạm cả hai: {x['ngang']:.0f}% | EV {x['ev']:+.2f}%"]
    kb = (kq.get("ptcp") or {}).get("kich_ban") or []
    if kb:
        d.append("3 kịch bản (ptcp):")
        bieu = {"TÍCH CỰC": "🟢", "CƠ SỞ": "🟡", "TIÊU CỰC": "🔴"}
        for k in kb:
            pct = f" ({(k['gia'] / g - 1) * 100:+.1f}%)" if k.get("gia") and g == g else ""
            them = f" – {', '.join(k['chi_tiet'])}" if k.get("chi_tiet") else (
                f" – {k['dieu_kien']}" if k.get("dieu_kien") else "")
            phien = f" ~{k['phien']:.0f} phiên" if k.get("phien") else ""
            d.append(f"  {bieu[k['ten']]} {k['ten']} {_f(k.get('gia'))}{pct}: XS {k['xs']:.0f}%{phien}{them}")
    return d


def dong_ptcp(pt):
    """1–2 dòng tóm tắt phân tích ngày của ptcp."""
    if not pt:
        return []
    d = [f"ptcp ({pt['ngay_du_lieu']}): {pt['khuyen_nghi']} | EV {_f(pt.get('ev'))}% | XS chạm MT trước CL "
         f"{_f(pt.get('xs_muc_tieu'), 0)}% | XS cắt lỗ {_f(pt.get('xs_cat_lo'), 0)}%"]
    if pt.get("su_kien") or pt.get("canh_bao_su_kien"):
        d.append("Sự kiện: " + "; ".join(pt.get("su_kien", []) + pt.get("canh_bao_su_kien", [])))
    if pt.get("vni_xau") or pt.get("rs_yeu"):
        d.append(f"ptcp: {'VN-Index xấu ' if pt.get('vni_xau') else ''}{'RS ở đáy 1 năm ' if pt.get('rs_yeu') else ''}"
                 f"→ khối lượng × {pt.get('he_so', 1):g}")
    return d


def tin_mua_ngay(kq, bay_gio):
    g = kq["gia"]
    return "\n".join([
        f"🟢 MUA NGAY – {kq['ma']} @ {_f(g)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})",
        dong_khung(kq),
        f"Kích hoạt: {kq['ly_do'].replace('đủ 4 khung: ', '')}",
        *dong_muc_tieu(kq),
        f"Thị trường: {kq['thi_truong']['nhan']}"
        + (" → giảm ½ khối lượng" if kq["thi_truong"].get("tot") is False else ""),
        *dong_ptcp(kq.get("ptcp")),
        "(Tham khảo – tự kiểm tra trước khi đặt lệnh)"])


def tin_tong_ket(ds, tt, bay_gio):
    d = [f"📋 TỔNG KẾT {pd.Timestamp(bay_gio):%d/%m/%Y} – {tt['nhan']}", ""]
    for kq in ds:
        d.append(f"■ {kq['ma']} {_f(kq['gia'])} – {kq['trang_thai']}")
        d.append(f"  {dong_khung(kq)}")
        d.append(f"  {kq['ly_do']}")
        d += [f"  {x}" for x in dong_muc_tieu(kq)]
        d += [f"  {x}" for x in dong_ptcp(kq.get("ptcp"))]
        d.append("")
    return "\n".join(d).rstrip()


def doc_trang_thai(path=C.FILE_TRANG_THAI):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ghi_trang_thai(tt, path=C.FILE_TRANG_THAI):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False, indent=1)


def can_bao(ma, mua_ngay, bay_gio, trang_thai):
    """
    Báo khi mã CHUYỂN sang MUA NGAY (lần chạy trước trong ngày chưa đạt). BAO_LAI_TRONG_NGAY = True → báo mọi lần.
    Cập nhật trang_thai tại chỗ. Trả True nếu cần gửi.
    """
    hom_nay = pd.Timestamp(bay_gio).strftime("%Y-%m-%d")
    cu = trang_thai.get(ma, {})
    truoc = cu.get("mua_ngay", False) if cu.get("ngay") == hom_nay else False
    trang_thai[ma] = {"ngay": hom_nay, "mua_ngay": bool(mua_ngay),
                      "so_lan_bao": cu.get("so_lan_bao", 0) if cu.get("ngay") == hom_nay else 0}
    gui_ = bool(mua_ngay) and (C.BAO_LAI_TRONG_NGAY or not truoc)
    if gui_:
        trang_thai[ma]["so_lan_bao"] += 1
    return gui_


def ghi_lich_su(kq, bay_gio, path="lich_su_tin_hieu.csv"):
    dong = pd.DataFrame([{"thoi_diem": pd.Timestamp(bay_gio).strftime("%Y-%m-%d %H:%M"), "ma": kq["ma"],
                          "gia": round(kq["gia"], 2), "cat_lo": round(kq["cat_lo"], 2),
                          "muc_tieu": round(kq["muc_tieu"], 2), "rr": round(kq["rr"], 2),
                          "kich_hoat": kq["ly_do"]}])
    dong.to_csv(path, mode="a", header=not os.path.exists(path), index=False, encoding="utf-8")
