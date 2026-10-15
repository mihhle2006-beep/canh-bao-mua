# -*- coding: utf-8 -*-
"""
Nguồn vnstock = ptcp.vnstock_nguon (một nguồn logic): giá (KBS → VCI), số liệu tài chính CHỈ VCI (KBS ghi nhãn kỳ
ngược số liệu), BCTC năm (CFO đúng dòng, phải thu, tỷ đồng), danh sách HOSE, giới hạn lượt gọi dùng chung.
"""
from .._ptcp import bi_danh

bi_danh(__name__, "ptcp.vnstock_nguon")
