# -*- coding: utf-8 -*-
"""Gọi HTTP dùng chung: 1 phiên kết nối/luồng, tự thử lại khi lỗi mạng/5xx/429, timeout chuẩn."""
import logging
import threading
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}
TIMEOUT = 12
_cuc_bo = threading.local()
logging.getLogger("urllib3").setLevel(logging.ERROR)        # tắt cảnh báo "Retrying ..." gây rối màn hình


def phien():
    """Mỗi luồng 1 requests.Session (Session không an toàn khi dùng chung giữa các luồng)."""
    s = getattr(_cuc_bo, "s", None)
    if s is None:
        s = requests.Session()
        thu_lai = Retry(total=1, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504),
                        allowed_methods=frozenset(["GET", "POST"]), raise_on_status=False)
        s.mount("https://", HTTPAdapter(max_retries=thu_lai, pool_maxsize=16))
        s.mount("http://", HTTPAdapter(max_retries=thu_lai, pool_maxsize=16))
        s.headers.update(HEADERS)
        _cuc_bo.s = s
    return s


def lay_json(url, params=None, json_body=None, headers=None, timeout=TIMEOUT):
    """GET (hoặc POST nếu có json_body) → JSON. Lỗi HTTP ≥ 400 → ném ngoại lệ có mã lỗi."""
    s = phien()
    if json_body is not None:
        r = s.post(url, params=params, json=json_body, headers=headers, timeout=timeout)
    else:
        r = s.get(url, params=params, headers=headers, timeout=timeout)
    if r.status_code >= 400:
        raise ValueError(f"HTTP {r.status_code}")
    return r.json()


def ts(ngay_str, cong=0):
    """'YYYY-MM-DD' → unix timestamp (giây)."""
    return int(datetime.strptime(ngay_str, "%Y-%m-%d").timestamp()) + cong


class NhatKyNguon:
    """Ghi lại nguồn đã dùng / lỗi cho từng loại dữ liệu (an toàn đa luồng) → xuất sheet Excel."""

    def __init__(self):
        self._ds = []
        self._khoa = threading.Lock()

    def ghi(self, du_lieu, nguon, ket_qua, chi_tiet=""):
        with self._khoa:
            self._ds.append({"Dữ liệu": du_lieu, "Nguồn": nguon, "Kết quả": ket_qua, "Chi tiết": chi_tiet,
                             "Thời điểm": datetime.now().strftime("%d/%m/%Y %H:%M:%S")})

    def bang(self):
        import pandas as pd
        with self._khoa:
            return pd.DataFrame(self._ds, columns=["Dữ liệu", "Nguồn", "Kết quả", "Chi tiết", "Thời điểm"])

    def thong_ke(self):
        """Số lần thành công/lỗi theo nguồn – biết nguồn nào đang chết."""
        b = self.bang()
        if b.empty:
            return b
        return (b.assign(ok=b["Kết quả"].eq("OK")).groupby("Nguồn")
                .agg(**{"Thành công": ("ok", "sum"), "Tổng lần gọi": ("ok", "size")})
                .assign(**{"Tỷ lệ OK %": lambda x: x["Thành công"] / x["Tổng lần gọi"] * 100})
                .sort_values("Tỷ lệ OK %", ascending=False))

    def xoa(self):
        with self._khoa:
            self._ds.clear()


NHAT_KY = NhatKyNguon()


class CauDao:
    """
    Ngắt nguồn chết: nguồn lỗi LIÊN TIẾP ≥ nguong lần mà CHƯA thành công lần nào trong lần chạy
    → bỏ qua nguồn đó cho các mã còn lại (khỏi chờ timeout hàng trăm lần).
    """

    def __init__(self, nguong=5):
        self.nguong = nguong
        self._loi, self._ok = {}, {}
        self._khoa = threading.Lock()

    def bo_qua(self, ten):
        with self._khoa:
            return self._ok.get(ten, 0) == 0 and self._loi.get(ten, 0) >= self.nguong

    def ghi(self, ten, thanh_cong):
        with self._khoa:
            if thanh_cong:
                self._ok[ten] = self._ok.get(ten, 0) + 1
                self._loi[ten] = 0
            else:
                self._loi[ten] = self._loi.get(ten, 0) + 1

    def da_ngat(self):
        with self._khoa:
            return [t for t in self._loi if self._ok.get(t, 0) == 0 and self._loi[t] >= self.nguong]

    def xoa(self):
        with self._khoa:
            self._loi.clear()
            self._ok.clear()


CAU_DAO_GIA = CauDao()
CAU_DAO_CO_BAN = CauDao()
