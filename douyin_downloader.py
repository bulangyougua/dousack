# -*- coding: utf-8 -*-
"""
抖音 / TikTok 无水印视频下载器 —— 核心逻辑 / 命令行入口

用法：
  1) 双击「抖音视频下载器.exe」：图形界面，粘贴分享链接或口令即可下载
  2) 命令行：抖音视频下载器.exe "https://v.douyin.com/xxxx/" [-o 输出目录]

抖音使用 Python 标准库；TikTok 所需的 yt-dlp、curl-cffi 已内嵌在 exe 中。
"""
import argparse
import gzip
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.request

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

URL_RE = re.compile(r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")
ILLEGAL_RE = re.compile(r'[\\/:*?"<>|\r\n\t]')


def app_dir():
    """exe（或源码）所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(rel):
    """打包后从 _MEIPASS 读取内嵌资源。"""
    base = getattr(sys, "_MEIPASS", app_dir())
    return os.path.join(base, rel)


def default_outdir():
    """使用当前 Windows 用户的视频目录，不依赖 exe 的存放位置。"""
    if os.name == "nt":
        import ctypes

        # FOLDERID_Videos：支持用户把系统“视频”文件夹迁移到其他位置。
        videos_guid = (ctypes.c_ubyte * 16).from_buffer_copy(
            bytes.fromhex("18b78c9589ea9c4f8216af681ca47bb9"))
        path = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            videos_guid, 0, None, ctypes.byref(path))
        if result == 0 and path.value:
            folder = path.value
            ctypes.windll.ole32.CoTaskMemFree(path)
            return folder
    return os.path.join(os.path.expanduser("~"), "Videos")


def new_opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler(),
    )


def _headers(referer="https://www.iesdouyin.com/"):
    return {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": referer,
    }


def read_all(resp):
    data = resp.read()
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
    return data


def fetch_html(url, opener, timeout=25):
    req = urllib.request.Request(url, headers=_headers())
    with opener.open(req, timeout=timeout) as resp:
        return resp.geturl(), read_all(resp).decode("utf-8", "ignore")


def extract_urls(text):
    """从整段分享口令里挑出链接，去重并保持顺序。"""
    found = []
    for u in URL_RE.findall(text or ""):
        u = u.rstrip(".,;，。；")
        if u not in found:
            found.append(u)
    return found


def candidate_urls(url):
    """短链直接跟随重定向；长链接补一个 iesdouyin 分享页候选。"""
    cands = [url]
    m = re.search(r"/(?:share/)?video/(\d+)", url)
    if m and "v.douyin.com" not in url:
        share = "https://www.iesdouyin.com/share/video/%s/" % m.group(1)
        if share not in cands:
            cands.append(share)
    return cands


def parse_router_data(html):
    """解析 window._ROUTER_DATA，返回视频 item。"""
    idx = html.find("window._ROUTER_DATA")
    if idx < 0:
        return None
    start = html.find("{", idx)
    if start < 0:
        return None
    depth, end = 0, -1
    for i in range(start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return None
    try:
        data = json.loads(html[start:end])
    except json.JSONDecodeError:
        return None
    for value in data.get("loaderData", {}).values():
        if not isinstance(value, dict):
            continue
        items = (value.get("videoInfoRes") or {}).get("item_list") or []
        if items:
            return items[0]
    return None


def pick_play_url(item):
    """优先最高码率；playwm -> play 即无水印地址。"""
    video = item.get("video") or {}
    candidates = []
    for gear in video.get("bit_rate") or []:
        addr = (gear.get("play_addr") or {}).get("url_list") or []
        if addr:
            candidates.append((gear.get("bit_rate") or 0, addr[0]))
    addr = (video.get("play_addr") or {}).get("url_list") or []
    if addr:
        candidates.append((0, addr[0]))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1].replace("playwm", "play")


def clean_filename(desc, author):
    title = (desc or "抖音视频").split("#")[0].strip()
    title = ILLEGAL_RE.sub("", title)
    title = "".join(ch for ch in title if ord(ch) < 0x10000)
    title = title.strip().strip(".") or "抖音视频"
    if len(title) > 40:
        title = title[:40].rstrip()
    who = ILLEGAL_RE.sub("", (author or "").strip())
    who = "".join(ch for ch in who if ord(ch) < 0x10000)
    if who:
        title += "-" + who[:20]
    return title + ".mp4"


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists("%s (%d)%s" % (base, i, ext)):
        i += 1
    return "%s (%d)%s" % (base, i, ext)


def download_file(url, path, opener, progress=None, timeout=60):
    req = urllib.request.Request(url, headers=_headers())
    with opener.open(req, timeout=timeout) as resp, open(path, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if os.path.getsize(path) < 10240:
        raise RuntimeError("下载内容过小，可能被平台拦截，请稍后重试")
    return path


def download_one(url, outdir, log=print, progress=None):
    """按域名自动识别平台，下载单个链接并返回保存路径。"""
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    if host == "tiktok.com" or host.endswith(".tiktok.com") \
            or host in ("vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com"):
        from tiktok_downloader import download_tiktok
        return download_tiktok(url, outdir, log=log, progress=progress)
    if not (host == "douyin.com" or host.endswith(".douyin.com")
            or host == "iesdouyin.com" or host.endswith(".iesdouyin.com")):
        raise RuntimeError("暂不支持此网站，请使用抖音或 TikTok 的视频链接。")

    log("解析抖音链接：%s" % url)
    # 抖音先返回风控页，直到某次请求种下 ttwid cookie 才给真实数据。
    # 必须复用同一 CookieJar 连续重试，每轮重走短链以取新签名。
    opener = new_opener()
    item = None
    last_err = None
    max_rounds = 8
    for round_no in range(1, max_rounds + 1):
        for cand in candidate_urls(url):
            try:
                _, html = fetch_html(cand, opener)
                item = parse_router_data(html)
                if item:
                    break
                last_err = "分享页暂未返回视频数据（风控预热中 %d/%d）" % (round_no, max_rounds)
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
        if item:
            break
        log(last_err)
        time.sleep(0.3)
    if not item:
        raise RuntimeError(
            "没能解析到视频信息：%s\n建议复制完整的抖音分享口令（含 v.douyin.com 短链）后重试。"
            % last_err
        )

    desc = item.get("desc") or "抖音视频"
    author = (item.get("author") or {}).get("nickname") or ""
    duration = (item.get("video") or {}).get("duration") or 0
    log("视频：%s  |  作者：%s  |  时长：%.1f 秒"
        % (desc.split("#")[0].strip() or desc, author, duration / 1000))
    if item.get("images"):
        raise RuntimeError("这是图文作品，没有视频可下载")

    play_url = pick_play_url(item)
    if not play_url:
        raise RuntimeError("没有取到视频播放地址")

    os.makedirs(outdir, exist_ok=True)
    path = unique_path(os.path.join(outdir, clean_filename(desc, author)))
    log("开始下载（无水印，含原声）…")
    download_file(play_url, path, opener, progress=progress)
    log("完成：%s（%.2f MB）" % (path, os.path.getsize(path) / 1048576))
    return path


def run_cli(args):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    outdir = os.path.abspath(args.outdir or default_outdir())
    urls = []
    for raw in args.links:
        urls.extend(extract_urls(raw))
    if not urls:
        print("没有识别到有效的 http(s) 链接")
        return 1

    def progress(done, total):
        if total:
            print("\r下载中 %.1f%% (%.2f/%.2f MB)"
                  % (done * 100.0 / total, done / 1048576, total / 1048576),
                  end="", flush=True)
        else:
            print("\r下载中 %.2f MB" % (done / 1048576), end="", flush=True)

    ok = 0
    for u in urls:
        try:
            download_one(u, outdir, log=print, progress=progress)
            print()
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print("\n失败：%s" % exc)
    print("成功 %d/%d，保存目录：%s" % (ok, len(urls), outdir))
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("links", nargs="*")
    parser.add_argument("-o", "--outdir", default=None)
    if len(sys.argv) > 1:
        return run_cli(parser.parse_args())
    from ui import run_gui
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
