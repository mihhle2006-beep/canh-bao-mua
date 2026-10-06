# -*- coding: utf-8 -*-
"""
Chạy công cụ phân tích cổ phiếu.
  Terminal :  python chay.py
  Colab    :  %run chay.py                       (hỏi từng câu)
              from ptcp import main, quet_nhieu_ma  (gọi hàm, không hỏi – xem README.md)
"""
import sys
import traceback

from ptcp import main

if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        print(e)
    except Exception as e:
        traceback.print_exc()
        print(f"\n❌ Lỗi: {e}")
    if "ipykernel" not in sys.modules and sys.stdin and sys.stdin.isatty():
        try:
            input("\nNhấn Enter để thoát...")
        except EOFError:
            pass
