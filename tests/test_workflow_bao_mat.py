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
