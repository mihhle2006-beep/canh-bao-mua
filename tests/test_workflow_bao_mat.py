# -*- coding: utf-8 -*-
"""Repo CÔNG KHAI: mọi workflow lấy repo kín danh-muc phải XOÁ file danh mục thật trước khi chạy code (log công khai) –
đủ danh sách, kể cả file mới thêm sau (VD trung_vang*.json – 11/2026). Thêm file riêng tư mới ở danh-muc → thêm vào FILE_THAT."""
import glob
import os

import yaml

FILE_THAT = ("danh_muc*.csv", "da_ban*.csv", "lenh_that*.csv", "tien_mat_*.json", "trang_thai_vi_the.json",
             "lich_su_danh_muc.csv", "nhap*.txt", "trung_vang*.json")
THU_MUC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github", "workflows")


def _lay_danh_muc(steps):
    return any("danh-muc" in str((s.get("with") or {}).get("repository", "")) or
               "DANH_MUC_REPO" in str((s.get("with") or {}).get("repository", "")) for s in steps)


def test_workflow_lay_danh_muc_deu_xoa_du_file_that():
    thieu = {}
    for f in sorted(glob.glob(os.path.join(THU_MUC, "*.yml"))):
        if os.path.basename(f) == "danh_muc.yml":          # workflow danh mục thật: CẦN file thật, chạy kín (không in)
            continue
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for ten, job in (d.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if not _lay_danh_muc(steps):
                continue
            lenh = " ".join(str(s.get("run", "")) for s in steps)
            if all(f"*.{d}" in lenh for d in ("csv", "json", "txt")) and "rm -f" in lenh:   # xoá cả loại (VD _kho_dm/*.csv)
                continue
            mat = [x for x in FILE_THAT if x not in lenh]
            if mat:
                thieu[f"{os.path.basename(f)}:{ten}"] = mat
    assert not thieu, f"workflow lấy danh-muc nhưng không xoá đủ file thật: {thieu}"


def test_chi_mot_token_github_va_khoa_cache_khong_theo_token():
    """11/2026: gộp còn 1 token GitHub (DANH_MUC_TOKEN_GHI – repo kín danh-muc + gia_lap: Contents R/W, Actions R/W) cho
    dễ gia hạn; trạng thái riêng mã hoá bằng khoá cố định (CACHE_KEY / token bot Telegram) – tạo lại token GitHub không
    làm mất trạng thái (mất → báo bán lặp)."""
    import re
    bo = {"DANH_MUC_TOKEN_DOC", "SUC_KHOE_TOKEN", "BO_LOC_TOKEN"}
    dung = set()
    for f in glob.glob(os.path.join(THU_MUC, "*.yml")):
        dung |= set(re.findall(r"secrets\.([A-Z0-9_]+)", open(f, encoding="utf-8").read()))
    assert not (dung & bo), f"đã gộp vào DANH_MUC_TOKEN_GHI – bỏ {dung & bo}"
    assert "DANH_MUC_TOKEN_GHI" in dung
    d = yaml.safe_load(open(os.path.join(THU_MUC, "canh_bao.yml"), encoding="utf-8"))
    buoc = {s.get("name", ""): s for s in d["jobs"]["chay"]["steps"]}
    giai = next(v for k, v in buoc.items() if k.startswith("Giải mã trạng thái"))
    ma = next(v for k, v in buoc.items() if k.startswith("Mã hoá trạng thái"))
    for s in (giai, ma):
        assert "DANH_MUC_TOKEN_GHI" not in s["env"]["KHOA"] and "CACHE_KEY" in s["env"]["KHOA"]
    assert "KHOA_CU" in giai["run"]                      # đọc được cache cũ (mã bằng token)
    assert 'rm -f $ds' in ma["run"].splitlines()[-1]     # luôn xoá bản rõ


def test_workflow_ghi_danh_muc_dua_file_that_ra_ngoai_vung_lam_viec():
    """14/11/2026: job lấy danh-muc rồi ĐẨY lên (git push) – tệp thật đã xoá phải ra ngoài vùng làm việc (sparse-checkout):
    không thì pull --rebase --autostash cất cả việc xoá → xung đột (xoá ↔ sửa) với commit đồng bộ danh mục → đẩy hỏng
    (Kế hoạch ĐHCĐ mất kết quả 2,5 giờ đọc 12 & 13/11), và git add -A có thể commit việc xoá tệp thật."""
    thieu = []
    for f in sorted(glob.glob(os.path.join(THU_MUC, "*.yml"))):
        if os.path.basename(f) == "danh_muc.yml":
            continue
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for ten, job in (d.get("jobs") or {}).items():
            steps = job.get("steps") or []
            lenh = " ".join(str(s.get("run", "")) for s in steps)
            if not _lay_danh_muc(steps) or "git push" not in lenh:
                continue
            xoa = [str(s.get("run", "")) for s in steps if "rm -f danh_muc" in str(s.get("run", ""))]
            if not xoa:                     # kiểu khác (VD backtest.yml: danh-muc ở _kho_dm chỉ đọc, đẩy repo này)
                continue
            if not all("sparse-checkout set --no-cone" in x and all(f"'!/{t}'" in x for t in FILE_THAT)
                                  for x in xoa):
                thieu.append(f"{os.path.basename(f)}:{ten}")
    assert not thieu, f"job đẩy lên danh-muc chưa đưa tệp thật ra ngoài vùng làm việc: {thieu}"
