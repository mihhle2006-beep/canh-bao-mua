# -*- coding: utf-8 -*-
"""
TRA CỨU TỶ LỆ SỞ HỮU (công cụ riêng – không thuộc bot; workflow tra_cuu_so_huu.yml chạy tay, 27/10/2026)
  • Báo cáo thường niên (BCTN) năm từ CafeF (danh sách loại 3) → tải PDF (cafefnew, link cũ thử cafef1.mediacdn.vn) →
    chữ (pdftotext; bản scan → OCR tiếng Việt pdftoppm + tesseract (PDF ký số vẫn đọc được)) → dò tỷ lệ sở hữu Nhà nước · nước ngoài · tổ chức · HĐQT kèm
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
import zipfile
from concurrent.futures import ThreadPoolExecutor

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
    """Tải BCTN về p (link cũ thử cafef1); file .zip → lấy PDF lớn nhất bên trong. → True / False."""
    import io
    for u in (url, url.replace("cafefnew.mediacdn.vn", "cafef1.mediacdn.vn")):
        r = _get(u, headers=UA)
        if r is None:
            continue
        if r.content[:4] == b"%PDF":
            open(p, "wb").write(r.content)
            return True
        if r.content[:2] == b"PK":
            try:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                ds = [i for i in z.infolist() if i.filename.lower().endswith(".pdf")]
                if ds:
                    open(p, "wb").write(z.read(max(ds, key=lambda i: i.file_size)))
                    return True
            except zipfile.BadZipFile:
                pass
    return False


def ocr_trang(p, trang, dpi=200):
    """OCR tiếng Việt các trang (đánh số từ 0) bằng pdftoppm + tesseract, 4 luồng – KHÔNG qua ocrmypdf (ocrmypdf từ chối
    PDF có CHỮ KÝ SỐ – hầu hết BCTN ở VN). → chữ các trang nối bằng \\f."""
    def mot(i):
        png = f"{p}.{i}"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", str(i + 1), "-l", str(i + 1), "-singlefile",
                        p, png], capture_output=True, timeout=120)
        if not os.path.exists(png + ".png"):
            return ""
        try:                                         # 1 luồng / tiến trình: nhiều luồng OpenMP × 4 tiến trình → treo trang
            r = subprocess.run(["tesseract", png + ".png", "-", "-l", "vie", "--psm", "6"], capture_output=True, text=True,
                               timeout=30, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
        except subprocess.TimeoutExpired:
            print(f"    tesseract quá 30 giây trang {i + 1} – bỏ trang", flush=True)
            return ""
        finally:
            os.remove(png + ".png")
        if r.returncode:
            print(f"    tesseract lỗi trang {i + 1}: {r.stderr.strip()[-120:]}", flush=True)
        return r.stdout
    with ThreadPoolExecutor(4) as ex:
        return "\n\f".join(ex.map(mot, trang))


def so_trang(p):
    m = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", p], capture_output=True, text=True).stdout)
    return int(m[1]) if m else 0


def chu_pdf(p):
    """Chữ theo trang (\\f) – bản scan (ít chữ) → OCR tiếng Việt cả file; bản chữ → OCR thêm các trang có 'cơ cấu cổ
    đông' / 'sở hữu' (bảng & biểu đồ thường là ảnh). → (chữ, cách đọc)."""
    t = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
    if len(t.strip()) <= 3000:                       # bản scan → OCR cả file (tối đa 250 trang)
        n = so_trang(p)
        if not n:
            return t, "không đọc được (PDF hỏng)"
        t = ocr_trang(p, range(min(n, 250)))
        return t, "OCR" if len(t.strip()) > 1000 else "không đọc được (OCR rỗng)"
    trang = t.split("\f")
    # trang có từ khoá cơ cấu (bảng hay là ảnh) + trang gần như không chữ (bảng / biểu đồ chụp ảnh) ở 70% đầu file
    can = [i for i, x in enumerate(trang) if any(w in kd(x) for w in ("co cau co dong", "co cau so huu", "ty le so huu",
                                                                         "co dong lon"))][:8]
    can += [i for i, x in enumerate(trang[:int(len(trang) * 0.7)]) if len(x.strip()) < 80 and i not in can][:60]
    them = ocr_trang(p, sorted(can)) if can else ""
    return t + "\n\f" + them, f"chữ + OCR {len(can)} trang ảnh / cơ cấu" if can else "chữ"


# Cổ đông Nhà nước thường gặp (không dấu, chữ thường) – tổng công ty / tập đoàn / cơ quan nắm vốn Nhà nước.
NHA_NUOC = ("hang hai viet nam", "vimc", "vinalines", "dau khi viet nam", "petrovietnam", "pvn", "tan cang sai gon",
            "scic", "dau tu va kinh doanh von nha nuoc", "xang dau viet nam", "petrolimex", "cang hang khong viet nam",
            "acv", "viettel", "bo quoc phong", "bo giao thong", "bo tai chinh", "ubnd", "uy ban nhan dan", "vnpt",
            "buu chinh vien thong", "vnpost", "vicem", "xi mang viet nam", "hang khong viet nam", "vietnam airlines",
            "tong cong ty hang khong", "hang khong viet", "tong cong ty hang hai", "tong cong ty tan cang", "cang hang khong",
            "song da", "vinacomin", "than - khoang san", "dien luc viet nam", "evn", "cao su viet nam", "vrg",
            "luong thuc mien", "vinafood", "vinatex", "det may viet nam", "hoa chat viet nam", "vinachem", "tisco",
            "thep viet nam", "vnsteel", "cong nghiep tau thuy", "sbic", "vinashin", "cang sai gon")
SAI = ("dai dien", "thong qua", "toi da", "nhiem ky", "nguon von", "rac thai", "doanh thu", "loi nhuan", "ke hoach",
       "tang truong", "chiem", "thu lao", "co tuc", "lai suat", "ty le chi")   # câu văn / chỉ tiêu khác, không phải sở hữu
SO_CP = r"\d{1,3}(?:[.,]\d{3}){1,}|\d{5,}"                     # số cổ phần (phân cách nghìn, hoặc OCR mất dấu)
NHAN = r"^[\s\-–—_|.*•+]*(?:[0-9IVX]{1,3}[.)]?\s+)?[\-–—_|.*•+]*\s*"   # STT / gạch đầu dòng trước nhãn


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


def _pt_sau(dong, vt=0):
    """Các % trong dòng tính từ vị trí vt (bỏ số ngoài 0–100)."""
    return [v for v in (_so(m) for m in re.findall(PT, dong[vt:])) if v is not None]


def _dong_bang(dong, x, v):
    """Dòng bảng cổ đông: có số cổ phần, hoặc 0% kèm '-' (dòng trống); không chứa từ của câu văn / chỉ tiêu khác."""
    return not any(w in x for w in SAI) and (re.search(SO_CP, dong) is not None or (v == 0 and "-" in dong))


def _noi_dong(dong):
    """Nối dòng nhãn bị xuống hàng: dòng có chữ mà không có % + dòng sau bắt đầu bằng số cổ phần và có % → 1 dòng."""
    out, i = [], 0
    while i < len(dong):
        a = dong[i]
        if i + 1 < len(dong) and "%" not in a and re.search(r"[A-Za-zÀ-ỹ]{2,}", a) and "%" in dong[i + 1] \
                and re.match(r"\s*(?:\d{1,3}(?:[.,]\d{3})+|\d{5,})\s", dong[i + 1]):   # dòng sau mở đầu bằng SỐ CỔ PHẦN (không phải STT)
            out.append(a.rstrip() + "  " + dong[i + 1].strip())
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def _tim_ten(x):
    """Tên cổ đông Nhà nước trong dòng (so khớp BỎ KHOẢNG TRẮNG – OCR hay dính / tách chữ: 'ViệNam') → (vị trí sau tên
    trong dòng gốc, tên) hoặc (0, None)."""
    vt = [i for i, c in enumerate(x) if c != " "]
    gon = "".join(x[i] for i in vt)
    for w in NHA_NUOC:
        w2 = w.replace(" ", "")
        j = gon.find(w2)
        if j >= 0 and (len(w2) > 4 or re.search(r"\b" + re.escape(w) + r"\b", x)):
            return vt[j + len(w2) - 1] + 1, w
    return 0, None


def vung_co_cau(k):
    """Chỉ số dòng thuộc các bảng cơ cấu cổ đông / cổ đông lớn (từ tiêu đề tới dòng tổng ≈ 100% hoặc 90 dòng)."""
    out = set()
    for i, x in enumerate(k):
        if re.search(r"co cau co dong|co cau so huu|thanh phan co dong|danh sach co dong lon|co dong lon", x):
            for j in range(i, min(i + 90, len(k))):
                out.add(j)
                if j > i + 3 and re.match(NHAN + r"(tong cong|tong so|cong)\b", k[j]):
                    break
    return sorted(out)


def do_so_huu(t):
    """Dò trong chữ BCTN → {chỉ tiêu: (%, dòng trích)} + "_trich". CHỈ lấy % ngay sau NHÃN của dòng bảng (không lấy
    % cuối dòng – trang 2 cột hay ghép bảng khác), dòng phải có số cổ phần; không chắc → bỏ trống (gop kiểm chéo)."""
    dong = _noi_dong(t.split("\n"))
    k = [kd(d) for d in dong]
    vung = vung_co_cau(k)
    out = {}

    def nhan(ten, mau, bo=()):
        for i in vung:
            m = re.match(NHAN + mau, k[i])
            if not m or any(b in k[i] for b in bo):
                continue
            ps = _pt_sau(dong[i], m.end())
            if ps and _dong_bang(dong[i], k[i], ps[0]):
                # 3 cột trong nước – nước ngoài – tổng (a + b ≈ c) → lấy cột TỔNG
                v = ps[2] if len(ps) >= 3 and abs(ps[0] + ps[1] - ps[2]) <= 0.6 else ps[0]
                out[ten] = (v, dong[i].strip()[:220])
                return
    nhan("Nhà nước %", r"(?:co dong )?(?:von )?nha nuoc\b", ("ngan hang nha nuoc",))
    nhan("Nước ngoài %", r"(?:co dong |nha dau tu )?nuoc ngoai\b", ("room", "gioi han"))
    # cơ cấu Tổ chức / Cá nhân: dòng nhãn riêng, hoặc dòng "trong nước / nước ngoài" có 3 cột tổ chức – cá nhân – tổng
    to, cn, tr = 0.0, 0.0, []
    for i in vung:
        m = re.match(NHAN + r"(?:co dong )?(?:trong nuoc|nuoc ngoai)\b", k[i])
        ps = _pt_sau(dong[i], m.end()) if m else []
        if len(ps) >= 3 and abs(ps[0] + ps[1] - ps[2]) <= 0.6 and len(tr) < 2:
            to, cn = to + ps[0], cn + ps[1]
            tr.append(dong[i].strip()[:120])
    if len(tr) == 2 and 97 <= to + cn <= 103:
        out["Tổ chức %"], out["Cá nhân %"] = (round(to, 2), " | ".join(tr)), (round(cn, 2), " | ".join(tr))
    else:
        nhan("Tổ chức %", r"(?:co dong )?(?:la )?(?:to chuc|phap nhan|phap)\b", ("tin dung", "ca nhan va to chuc"))
        nhan("Cá nhân %", r"(?:co dong )?(?:la )?ca nhan\b")
    # Nhà nước qua danh sách cổ đông lớn (khi bảng không có dòng Nhà nước, hoặc dòng đó 0% mà có DN Nhà nước ≥ 5%)
    tong, tr, da = 0.0, [], set()
    for i in vung:
        vt, ten = _tim_ten(k[i])
        if not ten or ten in da:
            continue
        ps = _pt_sau(dong[i], vt)
        if ps and _dong_bang(dong[i], k[i], ps[0]) and ps[0] > 0:
            da.add(ten)
            tong += ps[0]
            tr.append(dong[i].strip()[:120])
    if tr and tong <= 100 and (out.get("Nhà nước %", (0,))[0] == 0):
        out["Nhà nước %"] = (round(tong, 2), "cổ đông lớn Nhà nước: " + " | ".join(tr))
    # HĐQT: bảng thành viên HĐQT có cột tỷ lệ sở hữu → cộng riêng SỞ HỮU cá nhân và phần ĐẠI DIỆN vốn
    for i, x in enumerate(k):
        if ("hoi dong quan tri" in x or "hdqt" in x) and any("so huu" in k[j] for j in range(i, min(i + 6, len(k)))):
            sh, dd, dong_sh, rong = 0.0, 0.0, [], 0
            for j in range(i + 1, min(i + 45, len(k))):
                ps = _pt_sau(dong[j])
                hop = ps and re.search(r"[A-Za-zÀ-ỹ]{2,}", dong[j]) and not any(w in k[j] for w in SAI if w != "dai dien")
                if hop and (re.search(SO_CP, dong[j]) or ps[-1] == 0):
                    if "dai dien" in k[j]:
                        dd += ps[-1]
                    else:
                        sh += ps[-1]
                        dong_sh.append(dong[j].strip()[:80])
                    rong = 0
                elif dong_sh:
                    rong += 1
                    if rong > 6 or "ban kiem soat" in k[j] or "ban dieu hanh" in k[j] or "ban tong giam doc" in k[j]:
                        break
            if 2 <= len(dong_sh) <= 15:
                if sh > 50:                                  # cá nhân không thể > 50% – thực chất là tỷ lệ đại diện
                    dd, sh = dd + sh, None
                if sh is not None:
                    out["HĐQT sở hữu %"] = (round(sh, 4), " | ".join(dong_sh)[:400])
                if 0 < dd <= 100:
                    out["HĐQT đại diện %"] = (round(dd, 4), " | ".join(dong_sh)[:400])
                break
    trich = []
    for i in [i for i in vung if re.search(r"co cau co dong|co cau so huu", k[i])][:3]:
        trich += [dong[j].strip() for j in range(i, min(i + 40, len(dong))) if dong[j].strip()]
    out["_trich"] = "\n".join(trich)[:3000]
    return out


def kiem_cheo(nam_bctn, vc):
    """Kiểm chéo số dò của 1 mã (sửa tại chỗ) → thêm cột "Kiểm tra" từng năm.
    • Nước ngoài: lệch Vietcap cuối năm > 3 điểm → dùng số Vietcap (bảng BCTN hay bị nhầm bảng cổ đông lớn / cột khác).
    • Nhà nước > Tổ chức + 1 → bỏ Tổ chức (bắt nhầm dòng 'tổ chức khác'); Tổ chức + Cá nhân lệch 100 > 5 → bỏ cả hai.
    • Nhà nước nhảy > 15 điểm so CẢ năm trước lẫn năm sau (đỉnh nhọn 1 năm) → bỏ, ghi chú."""
    nn = (vc or {}).get("nn_nam") or {}
    ds = sorted(nam_bctn, key=int)
    for y in ds:
        b, gc = nam_bctn[y], []
        x = b.get("Nước ngoài %")
        v = nn.get(str(y))
        if v is not None and (x is None or abs(x - v) > 3):
            if x is not None:
                gc.append(f"NN BCTN {x}% lệch Vietcap {v}% → dùng Vietcap")
                b["Nước ngoài % (BCTN dò)"] = x
            b["Nước ngoài %"], b["Nguồn nước ngoài"] = v, "Vietcap cuối năm"
        elif x is not None:
            b["Nguồn nước ngoài"] = "BCTN (khớp Vietcap ±3)" if v is not None else "BCTN"
        nh, to, cn = b.get("Nhà nước %"), b.get("Tổ chức %"), b.get("Cá nhân %")
        if to is not None and cn is not None and nh and abs(to + cn - 100) > 5 and abs(nh + to + cn - 100) <= 5:
            gc.append(f"bảng tách Nhà nước riêng → Tổ chức = {to}% + Nhà nước {nh}%")
            b["Tổ chức %"] = to = round(to + nh, 2)
        if nh is not None and to is not None and nh > to + 1:
            gc.append(f"Tổ chức {to}% < Nhà nước {nh}% → bỏ Tổ chức")
            b.pop("Tổ chức %"); to = None
        if to is not None and cn is not None and abs(to + cn - 100) > 5:
            gc.append(f"Tổ chức + Cá nhân = {to + cn:.1f}% ≠ 100 → bỏ")
            b.pop("Tổ chức %"); b.pop("Cá nhân %")
        b["Kiểm tra"] = "; ".join(gc)
    nh = [(y, nam_bctn[y].get("Nhà nước %")) for y in ds if nam_bctn[y].get("Nhà nước %") is not None]
    for (_, a), (y, x), (_, c) in zip(nh, nh[1:], nh[2:]):
        if abs(x - a) > 15 and abs(x - c) > 15:
            b = nam_bctn[y]
            b["Kiểm tra"] = "; ".join(filter(None, [b["Kiểm tra"], f"Nhà nước {x}% nhảy riêng năm này (trước {a}%, sau {c}%) → bỏ"]))
            b.pop("Nhà nước %")
    return nam_bctn


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


LAM_LAI = ("không đọc được", "không tải được")


def lenh_tai(a):
    """Tải & dò từng mã. --lam_lai <json lần trước>: giữ năm đã đọc được, chỉ làm lại năm lỗi (không đọc / không tải)."""
    out, cu = {}, {}
    if getattr(a, "lam_lai", None) and os.path.exists(a.lam_lai):
        cu = json.load(open(a.lam_lai))
    with tempfile.TemporaryDirectory() as tm:
        for ma in [m.strip().upper() for m in a.ma.split(",") if m.strip()]:
            r = {"vietcap": (cu.get(ma) or {}).get("vietcap") or vietcap(ma), "bctn": {}}
            giu = {int(n): b for n, b in ((cu.get(ma) or {}).get("bctn") or {}).items()
                   if not str(b.get("cach", "")).startswith(LAM_LAI)}
            for nam, url in sorted(ds_bctn(ma, a.tu, a.den).items()):
                if nam in giu:
                    r["bctn"][nam] = giu[nam]
                    continue
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
    CT = ("Nhà nước %", "Nước ngoài %", "Tổ chức %", "Cá nhân %", "HĐQT sở hữu %", "HĐQT đại diện %")
    for m in thu_tu:
        bc = kiem_cheo({str(k): v for k, v in d[m]["bctn"].items()}, d[m]["vietcap"])
        for y in nam:
            b = bc.get(str(y)) or {}
            rows.append({"Mã": m, "Nhóm": nhom.get(m, ""), "Năm": y, "Đọc": b.get("cach", "không có BCTN trên CafeF"),
                         **{k: b.get(k) for k in CT}, "Nguồn nước ngoài": b.get("Nguồn nước ngoài"),
                         "Nước ngoài % (BCTN dò, lệch Vietcap)": b.get("Nước ngoài % (BCTN dò)"),
                         "Kiểm tra (tự sửa / bỏ số)": b.get("Kiểm tra"),
                         **{f"trích {k}": b.get(f"trích {k}") for k in CT},
                         "Link BCTN": b.get("link"), "Đoạn 'cơ cấu cổ đông' (kiểm tay)": b.get("đoạn cơ cấu")})
    with pd.ExcelWriter(a.ra) as w:
        pd.DataFrame(rows).to_excel(w, sheet_name="Theo năm (BCTN)", index=False)
        nn.to_excel(w, sheet_name="Nước ngoài cuối năm", index=False)
        pd.DataFrame(cc).to_excel(w, sheet_name="Cơ cấu hiện tại", index=False)
        pd.DataFrame({"Ghi chú": [
            "Theo năm (BCTN): số dò TỰ ĐỘNG từ báo cáo thường niên năm đó (CafeF) – cột 'trích' là dòng gốc, cần kiểm tay; "
            "ô trống = không dò được (bảng dạng ảnh mờ / cách trình bày khác) → mở Link BCTN.",
            "Chỉ lấy % NGAY SAU NHÃN của dòng bảng cơ cấu / cổ đông lớn có số cổ phần (bỏ câu văn, bỏ % cuối dòng của bảng bên "
            "cạnh); không chắc → để trống. Cột 'Kiểm tra' ghi các số đã tự sửa / bỏ.",
            "Nước ngoài: lệch Vietcap cuối năm > 3 điểm → dùng số Vietcap (cột Nguồn nước ngoài); số BCTN dò giữ ở cột riêng.",
            "Nhà nước: dòng 'Cổ đông Nhà nước' hoặc cộng cổ đông lớn là DN / cơ quan Nhà nước (VIMC, PVN, ACV, VNA, SCIC…); "
            "nhảy > 15 điểm riêng 1 năm → bỏ. Tổ chức: gồm Nhà nước; Tổ chức + Cá nhân phải ≈ 100%, Nhà nước ≤ Tổ chức.",
            "HĐQT sở hữu % = cộng sở hữu CÁ NHÂN thành viên HĐQT; HĐQT đại diện % = phần vốn thành viên HĐQT đại diện (Nhà nước /"
            " tổ chức) – trước đây gộp chung nên có năm ra 80–100%.",
            "Nước ngoài cuối năm: Vietcap IQ price-history (tỷ lệ NĐTNN nắm giữ cuối năm; năm cuối = hiện tại).",
            "Cơ cấu hiện tại: Vietcap IQ shareholder-structure (thời điểm chạy).",
            f"Tạo {time.strftime('%d/%m/%Y')} – workflow tra_cuu_so_huu (canh-bao-mua), công cụ cong_cu/so_huu/so_huu.py."]}
        ).to_excel(w, sheet_name="Ghi chú", index=False)
    print("✔", a.ra)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="lenh", required=True)
    t = s.add_parser("tai")
    t.add_argument("--ma", required=True)
    t.add_argument("--lam_lai", help="json kết quả lần trước – chỉ làm lại năm lỗi")
    g = s.add_parser("gop")
    g.add_argument("phan", nargs="+")
    for x in (t, g):
        x.add_argument("--tu", type=int, default=2018)
        x.add_argument("--den", type=int, default=2025)
        x.add_argument("--ra", required=True)
    a = p.parse_args()
    lenh_tai(a) if a.lenh == "tai" else lenh_gop(a)
