# -*- coding: utf-8 -*-
"""程序入口。

单独做一层入口，避免 PyInstaller 把主模块改名成 __main__ 后
其它模块 import douyin_downloader 失败。
"""
import sys
from douyin_downloader import main

if __name__ == "__main__":
    sys.exit(main())
