# -*- coding: utf-8 -*-
"""
TRA CỨU TỶ LỆ SỞ HỮU (công cụ riêng – không thuộc bot; workflow tra_cuu_so_huu.yml chạy tay, 27/10/2026)
  • Báo cáo thường niên (BCTN) năm từ CafeF (danh sách loại 3) → tải PDF (cafefnew, link cũ thử cafef1.mediacdn.vn) →
    chữ (pdftotext; bản scan → OCR tiếng Việt ocrmypdf) → dò tỷ lệ sở hữu Nhà nước · nước ngoài · tổ chức · HĐQT kèm
    ĐOẠN TRÍCH (dòng gốc) để kiểm tay.
  • Vietcap IQ: sở hữu nước ngoài cuối mỗi năm (price-history ONE_YEAR) + cơ cấu hiện tại (Nhà nước / nước ngoài /
    HĐQT / tổ chức).
  python cong_cu/so_huu/so_huu.py tai --ma GMD,VSC --tu 2018 --den 2025 --ra phan.json
  python cong_cu/so_huu/so_huu.py gop phan_*.json --ra So_huu.xlsx
Số dò tự động từ BCTN có thể sai (bảng mỗi DN một kiểu) – cột "trích" là dòng gốc để đối chiếu.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import tempfile
import time
import unicodedata

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126"}
VC = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{}/"
VC_H = {**UA, "Accept": "application/json", "Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"}
PT = r"(\d{1,3}(?:[.,]\d{1,4})?)\s*%"


def _get(url, **kw):
    for k in range(3):
        try:
            r = requests.get(url, timeout=120, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def ds_bctn(ma, tu, den):
    r = _get(f"https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol={ma}&Type=3&Year=0", headers=UA)
    out = {}
    for x in ((r.json() or {}).get("Data") or []) if r else []:
        if "thường niên" in x["Name"].lower() and tu <= int(x["Year"]) <= den:
            out.setdefault(int(x["Year"]), x["Link"])
    return out


def tai_pdf(url, p):
    for u in (url, url.replace("cafefnew.mediacdn.vn", "cafef1.mediacdn.vn")):
        r = _get(u, headers=UA)
        if r is not None and r.content[:4] == b"%PDF":
            open(p, "wb").write(r.content)
            return True
    return False


def chu_pdf(p):
    """Chữ theo trang (\\f) – bản scan (ít chữ) → OCR tiếng Việt cả file; bản chữ → OCR thêm các trang có 'cơ cấu cổ
    đông' / 'sở hữu' (bảng & biểu đồ thường là ảnh). → (chữ, cách đọc)."""
    t = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
    if len(t.strip()) <= 3000:
        o = p + ".ocr.pdf"
        subprocess.run(["ocrmypdf", "-q", "-l", "vie", "--force-ocr", "-j", "4", "--output-type", "pdf",
                        "--optimize", "0", p, o], capture_output=True)
        if not os.path.exists(o):
            return t, "không đọc được"
        t = subprocess.run(["pdftotext", "-layout", o, "-"], capture_output=True, text=True).stdout
        os.remove(o)
        return t, "OCR"
    trang = t.split("\f")
    can = [i for i, x in enumerate(trang) if any(w in kd(x) for w in ("co cau co dong", "co cau so huu", "ty le so huu"))][:6]
    them = []
    for i in can:
        png = f"{p}.{i}"
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", "-f", str(i + 1), "-l", str(i + 1), "-singlefile", p, png],
                       capture_output=True)
        if os.path.exists(png + ".png"):
            them.append(subprocess.run(["tesseract", png + ".png", "-", "-l", "vie", "--psm", "6"], capture_output=True,
                                       text=True).stdout)
            os.remove(png + ".png")
    return t + "\n\f" + "\n\f".join(them), "chữ + OCR trang cơ cấu" if them else "chữ"


NHA_NUOC = ("hang hai viet nam", "vimc", "vinalines", "dau khi viet nam", "pvn", "tan cang sai gon", "scic",
            "dau tu va kinh doanh von nha nuoc", "xang dau viet nam", "petrolimex", "cang hang khong viet nam",
            "acv", "viettel", "bo quoc phong", "bo giao thong", "ubnd", "uy ban nhan dan", "vnpt", "buu chinh vien thong",
            "vicem", "xi mang viet nam", "tong cong ty hang khong viet nam", "vietnam airlines", "song da", "cong doan")


def kd(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _so(x):
    x = x.replace(",", ".")
    try:
        v = float(x)
    except ValueError:
        return None
    return v if 0 <= v <= 100 else None


def do_so_huu(t):
    """Dò trong chữ BCTN → {chỉ tiêu: (%, dòng trích)} + "_trich" (đoạn quanh 'cơ cấu cổ đông' để kiểm tay)."""
    dong = t.split("\n")
    k = [kd(d) for d in dong]
    vung = [i for i, x in enumerate(k) if "co cau co dong" in x or "co cau so huu" in x]
    pham_vi = sorted({j for i in vung for j in range(i, min(i + 80, len(k)))})
    out = {}

    def tim(ten, dk, bo=(), ds=None):
        for i in (ds if ds is not None else pham_vi):
            x = k[i]
            if dk(x) and not any(b_ in x for b_ in bo):
                ps = [v for v in (_so(m) for m in re.findall(PT, dong[i])) if v is not None]
                if ps:
                    out[ten] = (ps[-1], dong[i].strip()[:220])
                    return True
        return False
    tim("Nhà nước %", lambda x: "nha nuoc" in x, ("ngan sach", "ngan hang nha nuoc"))
    tim("Nước ngoài %", lambda x: "nuoc ngoai" in x, ("room", "toi da", "gioi han", "ty gia"))
    tim("Tổ chức %", lambda x: re.search(r"\bto chuc\b", x) is not None, ("ca nhan va to chuc", "to chuc tin dung"))
    tim("Cá nhân %", lambda x: re.search(r"\bca nhan\b", x) is not None and "to chuc" not in x)
    if "Nhà nước %" not in out:              # không ghi thẳng → cộng cổ đông lớn là DN / cơ quan nhà nước
        lon = [i for i, x in enumerate(k) if "co dong lon" in x]
        ds = sorted({j for i in lon for j in range(i, min(i + 30, len(k)))})
        tong, tr, da = 0.0, [], set()
        for i in ds:
            ten = next((w for w in NHA_NUOC if w in k[i]), None)
            ps = [v for v in (_so(m) for m in re.findall(PT, dong[i])) if v is not None]
            if ten and ps and ten not in da:
                da.add(ten)
                tong += ps[-1]
                tr.append(dong[i].strip()[:120])
        if tr and tong <= 100:
            out["Nhà nước %"] = (round(tong, 2), "cổ đông lớn nhà nước: " + " | ".join(tr))
    for i, x in enumerate(k):                 # HĐQT: bảng thành viên HĐQT có cột tỷ lệ sở hữu → cộng % cá nhân
        if ("hoi dong quan tri" in x or "hdqt" in x) and any("so huu" in k[j] for j in range(i, min(i + 6, len(k)))):
            tong, dong_tt, rong = 0.0, [], 0
            for j in range(i + 1, min(i + 45, len(k))):
                ps = [v for v in (_so(m) for m in re.findall(PT, dong[j])) if v is not None]
                if ps and re.search(r"[A-Za-zÀ-ỹ]{2,}", dong[j]) and "dai dien" not in k[j]:
                    tong += ps[-1]
                    dong_tt.append(dong[j].strip()[:80])
                    rong = 0
                elif dong_tt:
                    rong += 1
                    if rong > 6 or "ban kiem soat" in k[j] or "ban dieu hanh" in k[j] or "ban tong giam doc" in k[j]:
                        break
            if 2 <= len(dong_tt) <= 15 and tong <= 100:
                out["HĐQT %"] = (round(tong, 4), " | ".join(dong_tt)[:400])
                break
    trich = []
    for i in vung[:3]:
        trich += [dong[j].strip() for j in range(i, min(i + 40, len(dong))) if dong[j].strip()]
    out["_trich"] = "\n".join(trich)[:3000]
    return out


def vietcap(ma):
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


def lenh_tai(a):
    out = {}
    with tempfile.TemporaryDirectory() as tm:
        for ma in [m.strip().upper() for m in a.ma.split(",") if m.strip()]:
            r = {"vietcap": vietcap(ma), "bctn": {}}
            for nam, url in sorted(ds_bctn(ma, a.tu, a.den).items()):
                p = os.path.join(tm, f"{ma}_{nam}.pdf")
                if not tai_pdf(url, p):
                    r["bctn"][nam] = {"link": url, "cach": "không tải được"}
                    print(ma, nam, "không tải được", flush=True)
                    continue
                t, cach = chu_pdf(p)
                os.remove(p)
                d = do_so_huu(t)
                trich = d.pop("_trich", "")
                r["bctn"][nam] = {"link": url, "cach": cach, **{k: v[0] for k, v in d.items()},
                                  **{f"trích {k}": v[1] for k, v in d.items()}, "đoạn cơ cấu": trich}
                print(ma, nam, cach, {k: v[0] for k, v in d.items()}, flush=True)
            out[ma] = r
    json.dump(out, open(a.ra, "w"), ensure_ascii=False)


NHOM = {"Cảng & khai thác cảng": "GMD VSC PHP CDN MVN DXP PDN SGP ILB TCL DVP", "Vận tải biển": "HAH VOS VTO PVT GSP VIP VNA",
        "Kho vận & giao nhận": "TMS STG VNL SFI PJT HTV", "Dịch vụ hàng không": "SCS NCT SAS", "Bưu chính – chuyển phát": "VTP"}


def lenh_gop(a):
    import pandas as pd
    d = {}
    for f in sorted(sum((glob.glob(x) for x in a.phan), [])):
        d.update(json.load(open(f)))
    nhom = {m: n for n, s in NHOM.items() for m in s.split()}
    thu_tu = [m for s in NHOM.values() for m in s.split() if m in d] + [m for m in d if m not in nhom]
    nam = list(range(a.tu, a.den + 1))
    nn = pd.DataFrame([{"Mã": m, "Nhóm": nhom.get(m, ""), "Tên": d[m]["vietcap"]["ten"],
                        **{str(y): d[m]["vietcap"]["nn_nam"].get(str(y)) for y in nam + [a.den + 1]}} for m in thu_tu])
    cc = []
    for m in thu_tu:
        c = d[m]["vietcap"]["co_cau"] or {}
        cc.append({"Mã": m, "Nhóm": nhom.get(m, ""), "Nhà nước %": round((c.get("statePercentage") or 0) * 100, 2),
                   "Nước ngoài %": round((c.get("foreignPercentage") or 0) * 100, 2),
                   "HĐQT %": round((c.get("bodPercentage") or 0) * 100, 2),
                   "Tổ chức %": round((c.get("institutionPercentage") or 0) * 100, 2),
                   "Khác %": round((c.get("otherPercentage") or 0) * 100, 2), "Tổng CP": c.get("totalShares")})
    rows = []
    for m in thu_tu:
        for y in nam:
            b = d[m]["bctn"].get(str(y)) or d[m]["bctn"].get(y) or {}
            rows.append({"Mã": m, "Nhóm": nhom.get(m, ""), "Năm": y, "Đọc": b.get("cach", "không có BCTN trên CafeF"),
                         **{k: b.get(k) for k in ("Nhà nước %", "Nước ngoài %", "Tổ chức %", "Cá nhân %", "HĐQT %")},
                         "Nước ngoài % (Vietcap cuối năm)": d[m]["vietcap"]["nn_nam"].get(str(y)),
                         **{f"trích {k}": b.get(f"trích {k}") for k in ("Nhà nước %", "Nước ngoài %", "Tổ chức %", "HĐQT %")},
                         "Link BCTN": b.get("link"), "Đoạn 'cơ cấu cổ đông' (kiểm tay)": b.get("đoạn cơ cấu")})
    with pd.ExcelWriter(a.ra) as w:
        pd.DataFrame(rows).to_excel(w, "Theo năm (BCTN)", index=False)
        nn.to_excel(w, "Nước ngoài cuối năm", index=False)
        pd.DataFrame(cc).to_excel(w, "Cơ cấu hiện tại", index=False)
        pd.DataFrame({"Ghi chú": [
            "Theo năm (BCTN): số dò TỰ ĐỘNG từ báo cáo thường niên năm đó (CafeF) – cột 'trích' là dòng gốc, cần kiểm tay; "
            "ô trống = không dò được (bảng dạng ảnh mờ / cách trình bày khác) → mở Link BCTN.",
            "HĐQT % = cộng tỷ lệ sở hữu cá nhân các thành viên HĐQT trong bảng của BCTN (có thể thiếu phần đại diện sở hữu).",
            "Nước ngoài cuối năm: Vietcap IQ price-history (tỷ lệ NĐTNN nắm giữ cuối năm; năm cuối = hiện tại).",
            "Cơ cấu hiện tại: Vietcap IQ shareholder-structure (thời điểm chạy).",
            f"Tạo {time.strftime('%d/%m/%Y')} – workflow tra_cuu_so_huu (canh-bao-mua), công cụ cong_cu/so_huu/so_huu.py."]}
        ).to_excel(w, "Ghi chú", index=False)
    print("✔", a.ra)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="lenh", required=True)
    t = s.add_parser("tai")
    t.add_argument("--ma", required=True)
    g = s.add_parser("gop")
    g.add_argument("phan", nargs="+")
    for x in (t, g):
        x.add_argument("--tu", type=int, default=2018)
        x.add_argument("--den", type=int, default=2025)
        x.add_argument("--ra", required=True)
    a = p.parse_args()
    lenh_tai(a) if a.lenh == "tai" else lenh_gop(a)
