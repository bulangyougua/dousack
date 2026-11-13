# -*- coding: utf-8 -*-
"""TikTok 公开视频下载：yt-dlp 解析，浏览器指纹用于平台验证。"""
from contextlib import nullcontext, redirect_stderr, redirect_stdout
import os
import sys

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget


class _Logger:
    """把解析器的提示接入原有界面日志，不重复输出下载百分比。"""
    def __init__(self, log):
        self.log = log

    def debug(self, msg):
        if not msg.startswith("[debug]"):
            self.info(msg)

    def info(self, msg):
        if msg and not msg.startswith("[download]"):
            self.log(msg)

    def warning(self, msg):
        self.log("提示：%s" % msg)

    def error(self, msg):
        self.log("解析器：%s" % msg)


def _null_stdio():
    """无控制台 exe 中，yt-dlp 仍要求 stdout/stderr 是有效流。"""
    if sys.stdout is not None and sys.stderr is not None:
        return nullcontext()
    stream = open(os.devnull, "w", encoding="utf-8")
    return redirect_stdout(stream) if sys.stdout is None else redirect_stderr(stream)


def _friendly_error(exc):
    message = str(exc).removeprefix("ERROR: ").strip()
    lower = message.lower()
    if "login" in lower or "private" in lower or "permission" in lower:
        return "该 TikTok 视频需要登录或为私密内容，目前仅支持无需登录的公开视频。"
    if "unsupported url" in lower:
        return "无法识别此 TikTok 链接，请使用单个视频的分享链接。"
    if "http error 429" in lower:
        return "TikTok 请求过于频繁，请稍后再试。"
    if "http error 403" in lower or "blocked" in lower:
        return "TikTok 拒绝了当前网络的访问，请稍后重试或更换网络。"
    if "timed out" in lower or "timeout" in lower:
        return "连接 TikTok 超时，请检查网络后重试。"
    return "TikTok 下载失败：%s" % message


def download_tiktok(url, outdir, log=print, progress=None):
    """下载单个 TikTok 视频，返回实际保存路径。"""
    os.makedirs(outdir, exist_ok=True)
    log("平台：TikTok")
    log("正在通过平台验证并解析无水印视频…")
    completed = []
    log("解析视频信息…")

    def on_progress(data):
        if data.get("status") == "downloading" and progress:
            done = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            progress(done, total)
        elif data.get("status") == "finished":
            log("视频数据下载完成，正在保存…")

    # 只选自带音轨的单个文件，不要求用户额外安装 FFmpeg。
    # 优先兼容性更好的 H.264；没有该格式时保留可用的其他 MP4。
    options = {
        "format": (
            "best[ext=mp4][vcodec=h264][acodec!=none]/"
            "best[ext=mp4][vcodec!=none][acodec!=none]/"
            "best[vcodec!=none][acodec!=none]"
        ),
        "outtmpl": os.path.join(outdir, "%(title).80B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": False,
        "logger": _Logger(log),
        "progress_hooks": [on_progress],
        "impersonate": ImpersonateTarget("chrome"),
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "continuedl": True,
        "overwrites": False,
        "trim_file_name": 180,
        "windowsfilenames": True,
    }
    try:
        with _null_stdio(), yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("_type") == "playlist":
                raise RuntimeError("请使用单个 TikTok 视频链接，而不是主页或合集链接。")
            log("视频：%s" % (info.get("title") or "TikTok 视频"))
            log("作者：%s" % (info.get("uploader") or "未知"))
            path = info.get("requested_downloads", [{}])[0].get("filepath")
            if not path:
                path = ydl.prepare_filename(info)
            ext = info.get("ext") or "mp4"
            if not os.path.splitext(path)[1]:
                path += "." + ext
            completed.append(path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(_friendly_error(exc)) from exc

    if not completed or not os.path.isfile(completed[0]):
        raise RuntimeError("TikTok 视频已解析，但没有找到下载后的文件。")
    path = completed[0]
    log("完成：%s（%.2f MB）" % (path, os.path.getsize(path) / 1048576))
    return path
