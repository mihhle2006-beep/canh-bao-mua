# -*- coding: utf-8 -*-
"""
TRA CỨU CƠ CẤU SỞ HỮU (công cụ riêng – không thuộc bot; workflow tra_cuu_so_huu.yml chạy tay)
Nguồn Vietcap IQ: cơ cấu cổ đông HIỆN TẠI (Nhà nước / nước ngoài / HĐQT / tổ chức / khác) + tỷ lệ sở hữu nước ngoài
cuối mỗi năm (price-history ONE_YEAR) → Excel.
28/10/2026: bỏ phần dò tỷ lệ sở hữu từ báo cáo thường niên (OCR + dò bảng) – không kiểm chứng được (bảng mỗi DN một
kiểu, đối chiếu Vietcap sai nhiều).
  python cong_cu/so_huu/so_huu.py --ma GMD,VSC --ra So_huu.xlsx
"""
import argparse
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126"}
VC = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{}/"
VC_H = {**UA, "Accept": "application/json", "Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"}


def _get(url, **kw):
    for k in range(3):
        try:
            r = requests.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def vietcap(ma):
    """→ {nn_nam: {năm: % nước ngoài cuối năm}, co_cau: shareholder-structure, ten}."""
    r = {}
    x = _get(VC.format(ma) + "price-history?timeFrame=ONE_YEAR&pageSize=30", headers=VC_H)
    if x is not None:
        for d in x.json()["data"]["content"]:
            if d.get("foreignOwnedPercentage") is not None:
                r[str(int(d["tradingDate"][:4]))] = round(d["foreignOwnedPercentage"] * 100, 2)
    cc = _get(VC.format(ma) + "shareholder-structure", headers=VC_H)
    ten = _get(VC.format(ma).rstrip("/"), headers=VC_H)
    return {"nn_nam": r, "co_cau": cc.json()["data"] if cc is not None else None,
            "ten": (ten.json()["data"] or {}).get("viOrganName") if ten is not None else None}


def bang(d, tu, den):
    """{mã: vietcap(mã)} → (DataFrame cơ cấu hiện tại, DataFrame nước ngoài cuối năm)."""
    import pandas as pd
    cc, nn = [], []
    for m, v in d.items():
        c = v["co_cau"] or {}
        cc.append({"Mã": m, "Tên": v["ten"], "Nhà nước %": round((c.get("statePercentage") or 0) * 100, 2),
                   "Nước ngoài %": round((c.get("foreignPercentage") or 0) * 100, 2),
                   "HĐQT %": round((c.get("bodPercentage") or 0) * 100, 2),
                   "Tổ chức %": round((c.get("institutionPercentage") or 0) * 100, 2),
                   "Khác %": round((c.get("otherPercentage") or 0) * 100, 2), "Tổng CP": c.get("totalShares")})
        nn.append({"Mã": m, "Tên": v["ten"], **{str(y): v["nn_nam"].get(str(y)) for y in range(tu, den + 2)}})
    return pd.DataFrame(cc), pd.DataFrame(nn)


def main(argv=None):
    import pandas as pd
    p = argparse.ArgumentParser()
    p.add_argument("--ma", required=True)
    p.add_argument("--tu", type=int, default=2018)
    p.add_argument("--den", type=int, default=2025)
    p.add_argument("--ra", required=True)
    a = p.parse_args(argv)
    d = {m: vietcap(m) for m in dict.fromkeys(x.strip().upper() for x in a.ma.split(",") if x.strip())}
    cc, nn = bang(d, a.tu, a.den)
    with pd.ExcelWriter(a.ra) as w:
        cc.to_excel(w, sheet_name="Cơ cấu hiện tại", index=False)
        nn.to_excel(w, sheet_name="Nước ngoài cuối năm", index=False)
        pd.DataFrame({"Ghi chú": [
            "Cơ cấu hiện tại: Vietcap IQ shareholder-structure (thời điểm chạy). HĐQT % = sở hữu cá nhân HĐQT theo Vietcap.",
            f"Nước ngoài cuối năm: Vietcap IQ price-history (năm {a.den + 1} = hiện tại).",
            f"Tạo {time.strftime('%d/%m/%Y')} – workflow tra_cuu_so_huu (canh-bao-mua), cong_cu/so_huu/so_huu.py."]}
        ).to_excel(w, sheet_name="Ghi chú", index=False)
    print(f"✔ {len(d)} mã → {a.ra}")


if __name__ == "__main__":
    main()
