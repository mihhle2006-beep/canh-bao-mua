# -*- coding: utf-8 -*-
"""
LỊCH SỰ KIỆN TOÀN THỊ TRƯỜNG cho trang Tra cứu mã (#lich) – chạy SAU tra_cuu_dn (cần dn/<MÃ>.json, phần "sk" từ Vietcap IQ).
Gom sự kiện mọi mã có ngày (ngày GDKHQ / phát hành / công bố) trong [hôm nay − LUI, hôm nay + TOI] ngày → su_kien.json:
  {"cap_nhat", "tu", "den", "cot": [ngay, ma, nhom, ten, chot, thuc_hien, gia_tri, ty_le], "dong": [...]} (xếp theo ngày)
nhom: "tien" cổ tức tiền · "cp" phát hành / cổ tức cổ phiếu · "dh" đại hội cổ đông · "khac".
  python -m thi_truong.su_kien_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

LUI, TOI = 14, 120
COT = ["ngay", "ma", "nhom", "ten", "chot", "thuc_hien", "gia_tri", "ty_le"]


def nhom(x):
    ma, ten = str(x.get("ma_sk") or "").upper(), f"{x.get('loai') or ''} {x.get('ten') or ''}".lower()
    if ma == "DIV" or ("cổ tức" in ten and "tiền" in ten):
        return "tien"
    if ma == "ISS" or "phát hành" in ten or ("cổ tức" in ten and "cổ phiếu" in ten):
        return "cp"
    if ma.startswith(("AGM", "EGM")) or "đại hội" in ten or "đhcđ" in ten:
        return "dh"
    return "khac"


def gom(ds_ma, doc_dn, hom_nay, lui=LUI, toi=TOI):
    """ds_ma: mã · doc_dn(mã) → json dn (hoặc None) · hom_nay: date → list dòng (không trùng mã + ngày + tên)."""
    tu, den = (hom_nay - timedelta(days=lui)).isoformat(), (hom_nay + timedelta(days=toi)).isoformat()
    out, da = [], set()
    for m in ds_ma:
        for x in (doc_dn(m) or {}).get("sk") or []:
            d = str(x.get("ngay") or "")[:10]
            if not d or not tu <= d <= den:
                continue
            ten = (x.get("ten") or x.get("loai") or "").strip()
            k = (d, m, ten)
            if k in da:
                continue
            da.add(k)
            out.append([d, m, nhom(x), ten, x.get("chot"), x.get("thuc_hien"), x.get("gia_tri"), x.get("ty_le")])
    out.sort(key=lambda r: (r[0], r[1]))
    return out, tu, den


def main(argv=None):
    p = argparse.ArgumentParser(description="Lịch sự kiện toàn thị trường cho trang Tra cứu mã")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    a = p.parse_args(argv)
    with open(os.path.join(a.ra, "ds.json"), encoding="utf-8") as fh:
        ds_ma = [r["ma"] for r in json.load(fh).get("ds") or [] if r.get("ma")]

    def doc(m):
        try:
            with open(os.path.join(a.ra, "dn", f"{m}.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None
    gio_vn = datetime.now(timezone(timedelta(hours=7)))
    dong, tu, den = gom(ds_ma, doc, gio_vn.date())
    with open(os.path.join(a.ra, "su_kien.json"), "w", encoding="utf-8") as fh:
        json.dump({"cap_nhat": f"{gio_vn:%Y-%m-%d %H:%M}", "tu": tu, "den": den, "cot": COT, "dong": dong}, fh,
                  ensure_ascii=False, separators=(",", ":"))
    sap = sum(r[0] >= gio_vn.date().isoformat() for r in dong)
    print(f"Lịch sự kiện: {len(dong)} sự kiện ({sap} sắp tới) · {len(ds_ma)} mã")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
