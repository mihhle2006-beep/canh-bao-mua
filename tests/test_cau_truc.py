# -*- coding: utf-8 -*-
"""CAU_TRUC.md phải liệt kê ĐỦ workflow (14/11/2026: ghi 30 trong khi có 41) – thêm workflow thì thêm dòng vào bảng."""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]


def test_cau_truc_liet_ke_du_workflow():
    doc = (GOC / "CAU_TRUC.md").read_text(encoding="utf-8")
    ds = sorted((GOC / ".github/workflows").glob("*.yml"))
    thieu = []
    for p in ds:
        m = re.search(r"^name:\s*(.+)$", p.read_text(encoding="utf-8"), re.M)
        ten = m.group(1).strip().strip('"') if m else p.name
        if ten not in doc and p.name not in doc:
            thieu.append(p.name)
    assert thieu == [], f"workflow chưa có trong CAU_TRUC.md: {thieu}"
    assert f"| {len(ds)} workflow" in doc, f"CAU_TRUC.md ghi sai số workflow (thực tế {len(ds)})"
    assert f"({len(ds)} workflow" in (GOC / "README.md").read_text(encoding="utf-8")
