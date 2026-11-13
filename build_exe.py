# -*- coding: utf-8 -*-
"""一键重新打包 exe（在项目根目录运行）： python build_exe.py

构建依赖见 requirements-build.txt。
产出：./抖音视频下载器.exe（支持抖音和 TikTok）
"""
import os
import subprocess
import sys

import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    subprocess.run([sys.executable, "build_assets.py"], cwd=HERE, check=True)
    if os.name == "nt":
        import subprocess as sp
        # 构建前关闭仍在运行的旧版，避免 Windows 锁定待覆盖的 EXE。
        sp.run(["taskkill", "/IM", "抖音视频下载器.exe", "/F"],
               capture_output=True, check=False)
    # 显式收集 yt-dlp 的 TikTok 提取器及 curl_cffi 原生组件。
    datas = [
        ("assets/app_logo.png", "assets"),
        ("assets/app_icon.ico", "assets"),
    ]
    hiddenimports = []
    for package in ("yt_dlp", "curl_cffi"):
        pkg_datas, _binaries, pkg_imports = collect_all(package)
        datas += pkg_datas
        hiddenimports += pkg_imports
    cmd = [
        "--onefile", "--noconsole", "--clean",
        "--name", "抖音视频下载器",
        "--icon", os.path.join("assets", "app_icon.ico"),
        "--distpath", ".",
        "--workpath", "build",
        "--specpath", ".",
    ]
    for source, dest in datas:
        cmd += ["--add-data", "%s;%s" % (source, dest)]
    for module in sorted(set(hiddenimports)):
        cmd += ["--hidden-import", module]
    cmd += [
        "--collect-submodules", "yt_dlp.extractor",
        "--collect-submodules", "yt_dlp.downloader",
        "--collect-submodules", "yt_dlp.networking",
        "--collect-submodules", "yt_dlp.postprocessor",
        "main.py",
    ]
    # 在进程内调用，避免 Windows 命令行长度限制（提取器模块较多）。
    previous_dir = os.getcwd()
    try:
        os.chdir(HERE)
        PyInstaller.__main__.run(cmd)
    finally:
        os.chdir(previous_dir)
    print("完成：", os.path.join(HERE, "抖音视频下载器.exe"))


if __name__ == "__main__":
    main()
