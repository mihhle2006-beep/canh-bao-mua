# -*- coding: utf-8 -*-
"""
SUẤT QUỸ BỨT PHÁ – phần đếm / quyết định dùng chung, CHỈ thư viện chuẩn (13/11/2026): tong_ket_cl / chay.py (vòng 15', tin
tổng kết) và canh_bao/lenh_tele.py (nút đặt lệnh – workflow lenh_tele.yml chỉ có Python thuần) phải đếm giống hệt nhau.
  • ≤ so_ma mã hệ B đang giữ (mã hệ bắt đáy không tính) + dp suất dự phòng CHỈ cho tín hiệu mạnh (manh_b)
  • ≤ td mã MỚI / tuần ISO – đếm theo vị thế đang giữ VÀ lệnh MUA thật (lenh_that.csv, kể cả mã mua rồi bán trong tuần –
    trước 13/11/2026 chỉ đếm mã còn giữ nên mua-bán trong tuần không bị tính); lệnh MUA mã đã giữ từ trước tuần = mua thêm.
"""
from datetime import date, datetime, timedelta

MAC_DINH = {"so_ma": 8, "dp": 1, "td": 5}


def doc_ngay(s):
    """'25/08/2026' | '2026-08-25' (| date) → date | None."""
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    s = str(s or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def dem(giu, mua_that, hom_nay, la_bat_day=None):
    """giu {mã: ngày mua | None} (vị thế đang giữ) · mua_that [(mã, ngày)] (lệnh MUA thật) · hom_nay date.
    → (số mã hệ B đang giữ, số mã MỚI mua trong tuần ISO của hom_nay). la_bat_day(mã, ngày) → True: mã hệ bắt đáy."""
    la_bat_day = la_bat_day or (lambda m, n: False)
    giu = {m: doc_ngay(n) for m, n in giu.items()}
    tuan, dau_tuan = hom_nay.isocalendar()[:2], hom_nay - timedelta(days=hom_nay.weekday())
    giu_b = [m for m, n in giu.items() if not la_bat_day(m, n)]
    moi = set()
    for m, n in list(giu.items()) + [(m, doc_ngay(n)) for m, n in mua_that]:
        if n is None or n.isocalendar()[:2] != tuan or la_bat_day(m, n):
            continue
        if giu.get(m) is not None and giu[m] < dau_tuan:              # giữ từ trước tuần này → lệnh MUA là mua thêm
            continue
        moi.add(m)
    return len(giu_b), len(moi)


def quyet(ds, giu_b, moi, so_ma=8, dp=1, td=5):
    """ds: mã MỚI muốn mua (dict có "ma", "manh_b"), ĐÃ sắp theo ưu tiên – mã được nhận chiếm suất.
    → (được, bị bỏ [(mã, lý do)])."""
    n, duoc, bo = giu_b, [], []
    for k in ds:
        if moi >= td:
            bo.append((k["ma"], f"đã mua {moi}/{td} mã mới tuần này"))
        elif n >= so_ma and not k.get("manh_b"):
            bo.append((k["ma"], f"đủ {so_ma} mã, không phải tín hiệu mạnh"))
        elif n >= so_ma + dp:
            bo.append((k["ma"], f"đủ {so_ma} mã + {dp} suất dự phòng"))
        else:
            duoc.append(k)
            n, moi = n + 1, moi + 1
    return duoc, bo
