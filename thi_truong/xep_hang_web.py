# -*- coding: utf-8 -*-
"""
XẾP HẠNG A–F kiểu VGM (như FiinTrade) cho trang Tra cứu mã – chạy SAU canslim_web (cần rs, cach52 trong ds.json):
  Giá trị (V)       P/E thấp (P/E ≤ 0 – lỗ – xếp cuối), P/B thấp, rẻ so giá trị hợp lý (dinh_gia cao)
  Tăng trưởng (G)   LNST quý / 4 quý, doanh thu quý / 4 quý so cùng kỳ
  Động lượng (M)    hạng RS kiểu IBD, gần đỉnh 52 tuần, lãi 3 tháng (gia/<MÃ>.json)
  Mỗi nhóm = trung bình HẠNG PHẦN TRĂM (0–100, trong mọi mã có số liệu) các chỉ tiêu – cần ≥ 2 chỉ tiêu; VGM = trung bình
  các nhóm có điểm (≥ 2 nhóm). Chữ: A ≥ 80 · B ≥ 60 · C ≥ 40 · D ≥ 20 · F < 20 (xếp lại trên chính điểm nhóm → mỗi chữ ~⅕
  số mã). Chỉ để tham khảo khi chọn mã – KHÔNG vào luật mua của bot (backtest: lọc thêm không thắng luật đang dùng).
Ghi vào từng dòng ds.json: r["vgm"] = "V G M Tổng" (VD "B A C B"), r["vgm_d"] = điểm tổng 0–100; ds.json["xep_hang"] = mô tả.
  python -m thi_truong.xep_hang_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os

CHU = ((80, "A"), (60, "B"), (40, "C"), (20, "D"), (0, "F"))


def hang_pt(gt, cao_tot=True):
    """{mã: giá trị} → {mã: hạng phần trăm 0–100} (bằng nhau → cùng hạng TB); None / NaN bỏ qua."""
    ds = [(v, m) for m, v in gt.items() if v is not None and v == v]
    if not ds:
        return {}
    ds.sort(key=lambda x: x[0] if cao_tot else -x[0])
    n, out, i = len(ds), {}, 0
    while i < n:
        j = i
        while j + 1 < n and ds[j + 1][0] == ds[i][0]:
            j += 1
        h = ((i + j) / 2) / (n - 1) * 100 if n > 1 else 100.0
        for k in range(i, j + 1):
            out[ds[k][1]] = h
        i = j + 1
    return out


def chu(d):
    return None if d is None else next(c for nguong, c in CHU if d >= nguong)


def lai_3t(g):
    c = [v for v in (g or {}).get("c") or [] if v]
    return c[-1] / c[-64] - 1 if len(c) > 63 and c[-64] else None


def _pe_xep(pe):
    """P/E để xếp (thấp tốt): lỗ / không có → None (không xếp); P/E ≤ 0 → coi như rất đắt."""
    if pe is None or pe != pe:
        return None
    return 1e6 if pe <= 0 else pe


def tinh(ds, gia=None):
    """ds: list dòng ds.json (sửa tại chỗ) · gia: {mã: json giá} → số mã có hạng."""
    gia = gia or {}
    lay = lambda k: {r["ma"]: r.get(k) for r in ds}                  # noqa: E731
    chi = {
        "V": [hang_pt({m: _pe_xep(v) for m, v in lay("pe").items()}, cao_tot=False),
              hang_pt({m: (v if v and v > 0 else None) for m, v in lay("pb").items()}, cao_tot=False),
              hang_pt(lay("dinh_gia"))],
        "G": [hang_pt(lay("ln_yoy")), hang_pt(lay("ln4_yoy")), hang_pt(lay("dt_yoy")), hang_pt(lay("dt4_yoy"))],
        "M": [hang_pt(lay("rs")), hang_pt(lay("cach52")), hang_pt({m: lai_3t(gia.get(m)) for m in lay("ma")})],
    }
    diem = {}
    for nhom, ds_h in chi.items():
        tho = {}
        for r in ds:
            v = [h[r["ma"]] for h in ds_h if r["ma"] in h]
            if len(v) >= 2:
                tho[r["ma"]] = sum(v) / len(v)
        diem[nhom] = hang_pt(tho)                                     # xếp lại → chữ chia đều
    tong_tho = {}
    for r in ds:
        v = [diem[n][r["ma"]] for n in "VGM" if r["ma"] in diem[n]]
        if len(v) >= 2:
            tong_tho[r["ma"]] = sum(v) / len(v)
    tong = hang_pt(tong_tho)
    dem = 0
    for r in ds:
        m = r["ma"]
        if m in tong:
            r["vgm"] = " ".join(chu(diem[n].get(m)) or "–" for n in "VGM") + " " + chu(tong[m])
            r["vgm_d"] = round(tong[m])
            dem += 1
        else:
            r.pop("vgm", None)
            r.pop("vgm_d", None)
    return dem


MO_TA = {"V": "Giá trị: P/E, P/B thấp · rẻ so giá trị hợp lý", "G": "Tăng trưởng: LNST & doanh thu quý / 4 quý so cùng kỳ",
         "M": "Động lượng: hạng RS · gần đỉnh 52 tuần · lãi 3 tháng",
         "chu": "A top 20% · B · C · D · F 20% cuối (xếp trong mọi mã) – tham khảo, không vào luật mua"}


def main(argv=None):
    p = argparse.ArgumentParser(description="Xếp hạng A–F kiểu VGM cho trang Tra cứu mã")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    a = p.parse_args(argv)
    f = os.path.join(a.ra, "ds.json")
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    gia = {}
    for r in d.get("ds") or []:
        try:
            with open(os.path.join(a.ra, "gia", f"{r['ma']}.json"), encoding="utf-8") as fh:
                gia[r["ma"]] = json.load(fh)
        except (OSError, ValueError, KeyError):
            pass
    dem = tinh(d.get("ds") or [], gia)
    d["xep_hang"] = MO_TA
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
    a_ = sum((r.get("vgm") or "").endswith("A") for r in d.get("ds") or [])
    print(f"Xếp hạng VGM: {dem}/{len(d.get('ds') or [])} mã · {a_} mã hạng A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
