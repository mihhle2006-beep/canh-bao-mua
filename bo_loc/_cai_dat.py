# -*- coding: utf-8 -*-
"""Tự cài thư viện còn thiếu (tiện khi chạy Colab/máy mới). Không import pandas ở đây."""
import importlib
import subprocess
import sys

CAN = {"requests": "requests", "pandas": "pandas", "numpy": "numpy", "matplotlib": "matplotlib",
       "openpyxl": "openpyxl"}


def dam_bao_thu_vien():
    for mod, goi in CAN.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"Đang cài thư viện {goi} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", goi, "-q"])
