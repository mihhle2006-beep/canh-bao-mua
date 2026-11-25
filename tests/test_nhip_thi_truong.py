# -*- coding: utf-8 -*-
"""nhip_thi_truong.yml: lịch GitHub tới trễ hàng giờ (VD rạng sáng) → phải thoát ngay, không chạy vòng tới quá 290' (lỗi
hết giờ 11/2026). Chạy thật đoạn bash của bước với date / curl / sleep giả."""
import os
import shutil
import subprocess

import pytest
import yaml

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(GOC, ".github", "workflows", "nhip_thi_truong.yml")
DATE = shutil.which("date")


def _chay(tmp_path, luc):
    buoc = yaml.safe_load(open(WF, encoding="utf-8"))["jobs"]["nhip"]["steps"][0]["run"]
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "date").write_text(f'#!/bin/bash\nexec {DATE} -d "$FAKE_DT" "$@"\n')
    (bin_ / "curl").write_text('#!/bin/bash\necho "$@" >> "$GHI/curl"\necho \'{"workflow_runs": []}\'\n')
    (bin_ / "sleep").write_text('#!/bin/bash\necho ngu >> "$GHI/sleep"\nexit 1\n')     # vào vòng → dừng ngay
    for f in bin_.iterdir():
        f.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "FAKE_DT": luc, "GHI": str(tmp_path),
           "GH_TOKEN": "x", "GITHUB_REPOSITORY": "a/b", "GITHUB_RUN_ID": "1"}
    kq = subprocess.run(["bash", "-e", "-c", buoc], env=env, capture_output=True, text=True, timeout=30)
    return kq, (tmp_path / "sleep").exists()


@pytest.mark.skipif(DATE is None, reason="không có date")
@pytest.mark.parametrize("luc", ["2026-11-25 02:00", "2026-11-25 07:30", "2026-11-25 20:00", "2026-11-28 10:00"])
def test_ngoai_gio_thoat_ngay(tmp_path, luc):
    kq, vao_vong = _chay(tmp_path, luc)
    assert kq.returncode == 0 and not vao_vong and "thoát" in kq.stdout, kq.stdout + kq.stderr


@pytest.mark.skipif(DATE is None, reason="không có date")
@pytest.mark.parametrize("luc", ["2026-11-25 09:15", "2026-11-25 13:30"])
def test_trong_gio_vao_vong(tmp_path, luc):
    _, vao_vong = _chay(tmp_path, luc)
    assert vao_vong


def test_moi_vong_cho_gio_deu_chan_lich_tre():
    """Mọi bước có vòng chờ theo giờ VN (while … date +%H%M …) phải tự thoát khi lịch GitHub tới trễ sang cuối tuần /
    rạng sáng – kiểm theo cờ thứ trong tuần (date +%u) ngay trong bước (chống lặp lại lỗi hết giờ 11/2026)."""
    import glob
    thieu = []
    for f in sorted(glob.glob(os.path.join(GOC, ".github", "workflows", "*.yml"))):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        for ten, job in (d.get("jobs") or {}).items():
            for i, b in enumerate(job.get("steps") or []):
                run = str(b.get("run", ""))
                if "while [" in run and "Asia/Ho_Chi_Minh date" in run and "date +%u" not in run:
                    thieu.append(f"{os.path.basename(f)}:{ten}:{i}")
    assert not thieu, f"vòng chờ theo giờ không chặn lịch trễ: {thieu}"
