# -*- coding: utf-8 -*-
"""一键重新打包 exe（在项目根目录运行）： python build_exe.py

依赖：PyInstaller、Pillow（仅构建期需要）
产出：./抖音视频下载器.exe
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    subprocess.check_call([sys.executable, "build_assets.py"], cwd=HERE)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole", "--clean",
        "--name", "抖音视频下载器",
        "--icon", os.path.join("assets", "app_icon.ico"),
        "--add-data", "assets/app_logo.png;assets",
        "--add-data", "assets/app_icon.ico;assets",
        "--distpath", ".",
        "--workpath", "build",
        "--specpath", ".",
        "main.py",
    ]
    subprocess.check_call(cmd, cwd=HERE)
    print("完成：", os.path.join(HERE, "抖音视频下载器.exe"))


if __name__ == "__main__":
    main()
