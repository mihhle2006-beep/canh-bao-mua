# -*- coding: utf-8 -*-
"""
CHIẾN LƯỢC LỌC – mỗi chiến lược 1 file trong thư mục này, khai báo biến CHIEN_LUOC:

    CHIEN_LUOC = {
        "mo_ta": "...",
        "bat_buoc":  {khoá tiêu chí: ngưỡng, ...},     # phải đạt hết mới lọt lọc
        "cong_diem": {khoá tiêu chí: ngưỡng, ...},     # đạt thì cộng điểm xếp hạng
        "toi_thieu": {"can_dat": n, "tieu_chi": {...}} # (tuỳ chọn) chỉ cần đạt n trong số này
    }

Tên chiến lược = tên file (VD ky_thuat.py → --chien_luoc ky_thuat). Khoá tiêu chí xem bo_loc/tieu_chi.py.
Thêm chiến lược: copy 1 file có sẵn, đổi tên, sửa ngưỡng – KHÔNG cần sửa chỗ nào khác.
Không muốn sửa code: đặt file JSON cùng cấu trúc vào thư mục ./chien_luoc_rieng/ (nơi chạy lệnh).
"""
import copy
import importlib
import json
import os
import pkgutil

from ..tieu_chi import TIEU_CHI

THU_MUC_RIENG = "chien_luoc_rieng"


def _kiem_tra(ten, cl):
    """Báo lỗi sớm nếu chiến lược dùng khoá tiêu chí không tồn tại / cấu trúc sai."""
    loi = []
    if not isinstance(cl.get("bat_buoc"), dict) or not isinstance(cl.get("cong_diem", {}), dict):
        loi.append("thiếu 'bat_buoc' hoặc sai kiểu")
    for nhom in ("bat_buoc", "cong_diem"):
        for k in cl.get(nhom, {}):
            if k not in TIEU_CHI:
                loi.append(f"{nhom}.{k} không có trong TIEU_CHI")
    tt = cl.get("toi_thieu")
    if tt:
        for k in tt.get("tieu_chi", {}):
            if k not in TIEU_CHI:
                loi.append(f"toi_thieu.{k} không có trong TIEU_CHI")
        if not 0 < tt.get("can_dat", 0) <= len(tt.get("tieu_chi", {})):
            loi.append("toi_thieu.can_dat phải trong 1..số tiêu chí")
    if loi:
        raise ValueError(f"Chiến lược '{ten}' lỗi: " + "; ".join(loi))
    cl.setdefault("cong_diem", {})
    cl.setdefault("mo_ta", ten)
    cl.setdefault("ten", ten.replace("_", " ").capitalize())
    return cl


def tai_tat_ca(thu_muc_rieng=THU_MUC_RIENG):
    """{tên: chiến lược} từ các file .py trong gói + file .json trong thư mục riêng (ghi đè nếu trùng tên)."""
    ds = {}
    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        m = importlib.import_module(f"{__name__}.{mod.name}")
        if hasattr(m, "CHIEN_LUOC"):
            ds[mod.name] = _kiem_tra(mod.name, copy.deepcopy(m.CHIEN_LUOC))
    if thu_muc_rieng and os.path.isdir(thu_muc_rieng):
        for f in sorted(os.listdir(thu_muc_rieng)):
            if f.endswith(".json"):
                ten = f[:-5]
                with open(os.path.join(thu_muc_rieng, f), encoding="utf-8") as fh:
                    ds[ten] = _kiem_tra(ten, json.load(fh))
    return ds


# Tên cũ (trước khi gộp) → (tên mới, tiêu chí thêm)
TEN_CU = {"rui_ro_cao": ("bat_day", {"beta_min": 1.2}), "rui_ro_cao_goc": ("bat_day", {"beta_min": 1.2}),
          "rui_ro_cao_xu_huong": ("xu_huong", {"beta_min": 1.2}), "co_ban": ("gia_tri", {}),
          "tieu_chuan": ("gia_tri", {}), "gia_tri_goc": ("gia_tri", {})}


def doc_gia_tri(chuoi):
    """'1.2' → 1.2 | '1000' → 1000 | '25:45' → (25, 45) | '' / 'None' → None."""
    s = str(chuoi).strip()
    if s in ("", "None", "none"):
        return None
    if ":" in s:
        return tuple(doc_gia_tri(x) for x in s.split(":"))
    try:
        v = float(s)
        return int(v) if v.is_integer() else v
    except ValueError:
        return s


def them_bot(cl, them=None, bo=None):
    """
    Ghép tiêu chí lúc chạy: them = "beta_min=1.2,rsi_trong=25:45" (vào BẮT BUỘC; đã có thì đổi ngưỡng),
    bo = "tren_ma200,pe_max" (xoá khỏi mọi nhóm). Khoá sai → báo lỗi rõ.
    """
    c = copy.deepcopy(cl)
    for muc in [x.strip() for x in str(them or "").split(",") if x.strip()]:
        k, _, v = muc.partition("=")
        k = k.strip()
        if k not in TIEU_CHI:
            raise SystemExit(f"--them: không có tiêu chí '{k}'. Xem danh sách khoá trong bo_loc/tieu_chi.py")
        for nhom in ("cong_diem",):
            c.get(nhom, {}).pop(k, None)
        c["bat_buoc"][k] = doc_gia_tri(v)
    for k in [x.strip() for x in str(bo or "").split(",") if x.strip()]:
        if not any(k in c.get(n, {}) for n in ("bat_buoc", "cong_diem")) and \
                k not in c.get("toi_thieu", {}).get("tieu_chi", {}):
            raise SystemExit(f"--bo: chiến lược không có tiêu chí '{k}'")
        for n in ("bat_buoc", "cong_diem"):
            c.get(n, {}).pop(k, None)
        if c.get("toi_thieu"):
            c["toi_thieu"]["tieu_chi"].pop(k, None)
            c["toi_thieu"]["can_dat"] = min(c["toi_thieu"]["can_dat"], len(c["toi_thieu"]["tieu_chi"]))
            if not c["toi_thieu"]["tieu_chi"]:
                c.pop("toi_thieu")
    if them or bo:
        c["mo_ta"] += " | " + "; ".join(x for x in (f"thêm {them}" if them else "", f"bỏ {bo}" if bo else "") if x)
    return c


def lay(ten, thu_muc_rieng=THU_MUC_RIENG):
    ds = tai_tat_ca(thu_muc_rieng)
    if ten not in ds and ten in TEN_CU:
        moi, them = TEN_CU[ten]
        print(f"  (Chiến lược '{ten}' đã gộp vào '{moi}'" + (f" + {them}" if them else "") + ")")
        cl = copy.deepcopy(ds[moi])
        for k, v in them.items():
            cl["bat_buoc"][k] = v
            cl.get("cong_diem", {}).pop(k, None)
        return cl
    if ten not in ds:
        raise SystemExit(f"Không có chiến lược '{ten}'. Có: {', '.join(ds)}")
    return copy.deepcopy(ds[ten])


def cac_tieu_chi(cl):
    """(nhóm, khoá, ngưỡng) của mọi tiêu chí trong chiến lược."""
    for n in ("bat_buoc", "cong_diem"):
        for k, t in cl.get(n, {}).items():
            yield n, k, t
    for k, t in cl.get("toi_thieu", {}).get("tieu_chi", {}).items():
        yield "toi_thieu", k, t


def ap_nguong(cl, ghi_de):
    """Bản sao chiến lược với ngưỡng ghi đè (VD thanh khoản riêng theo nhóm/mã)."""
    c = copy.deepcopy(cl)
    for k, v in (ghi_de or {}).items():
        for nhom in ("bat_buoc", "cong_diem"):
            if k in c.get(nhom, {}):
                c[nhom][k] = v
    return c
