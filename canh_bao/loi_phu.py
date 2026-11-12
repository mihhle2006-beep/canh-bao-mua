# -*- coding: utf-8 -*-
"""
LỖI PHẦN PHỤ BỊ BỎ QUA – nhưng làm TẮT 1 LUẬT (13/11/2026, rà except Exception): lọc Quỹ B, nhiệt thị trường (hệ số khối
lượng), NAV thật (số CP), điều chỉnh quyền… Trước đây lỗi các phần này bị nuốt im lặng → luật ngừng áp dụng mà không ai
biết. Nay: in log 1 lần / (phần, loại lỗi) và gom thành 1 dòng ⚙ cuối tin tổng kết bản riêng (dong_tin).
Log công khai: an=True → chỉ in loại lỗi (phần đọc dữ liệu danh mục thật).
"""
_DS = {}                                                            # (phần, loại lỗi) → số lần


def ghi(phan, e, an=False):
    """Ghi 1 lỗi bị bỏ qua của `phan` (tên tiếng Việt ngắn) – e: ngoại lệ hoặc lý do (chuỗi ngắn, không chứa dữ liệu
    riêng). In log ở lần đầu mỗi (phần, loại lỗi)."""
    k = (phan, e if isinstance(e, str) else type(e).__name__)
    if k not in _DS:
        print(f"⚠ {phan}: {k[1]}" + ("" if an or isinstance(e, str) else f": {str(e)[:120]}")
              + " – bỏ qua, luật này tạm không áp dụng")
    _DS[k] = _DS.get(k, 0) + 1


def dong_tin():
    """1 dòng cuối tin tổng kết (rỗng khi không có lỗi)."""
    if not _DS:
        return ""
    return ("⚙ Phần bị lỗi, đã bỏ qua (luật tạm không áp dụng – xem log workflow): "
            + " · ".join(f"{p} ({t}{f' ×{n}' if n > 1 else ''})" for (p, t), n in _DS.items()))


def xoa():
    _DS.clear()
