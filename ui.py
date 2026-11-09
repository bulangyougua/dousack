# -*- coding: utf-8 -*-
"""抖音视频下载器 —— 图形界面"""
import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from douyin_downloader import (
    app_dir, default_outdir, download_one, extract_urls, resource_path,
)

BG = "#F4F6FB"
CARD = "#FFFFFF"
INK = "#101A3A"
MUTED = "#6B7280"
LINE = "#E4E8F2"
PINK = "#FE2C55"
CYAN = "#25F4EE"
OK = "#0F9D8A"
ERR = "#E5484D"
PLACEHOLDER = "在这里粘贴抖音分享链接或整段口令…\n支持一次粘贴多个链接，每行一个"


class App:
    def __init__(self, root):
        self.root = root
        self.outdir = default_outdir()
        self.q = queue.Queue()
        self.busy = False
        self.has_placeholder = True

        root.title("抖音视频下载器")
        root.geometry("700x620")
        root.minsize(620, 560)
        root.configure(bg=BG)
        try:
            root.iconbitmap(resource_path(os.path.join("assets", "app_icon.ico")))
        except Exception:
            pass

        self._style()
        self._header()
        self._body()
        self.root.after(100, self.poll)

        self.log("准备就绪 · 无水印原片 · 保留原声", "ok")
        self.log("在抖音点「分享 → 复制链接」，粘贴到上方即可。", "dim")

    # ---------------------------------------------------------------- 界面
    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=INK,
                     font=("Microsoft YaHei UI", 10))
        st.configure("Card.TLabel", background=CARD)
        st.configure("Title.TLabel", background=CARD, foreground=INK,
                     font=("Microsoft YaHei UI", 15, "bold"))
        st.configure("Sub.TLabel", background=CARD, foreground=MUTED,
                     font=("Microsoft YaHei UI", 9))
        st.configure("Hint.TLabel", background=BG, foreground=MUTED,
                     font=("Microsoft YaHei UI", 9))
        st.configure("Step.TLabel", background=BG, foreground=INK,
                     font=("Microsoft YaHei UI", 10, "bold"))
        st.configure("TButton", font=("Microsoft YaHei UI", 9), padding=(12, 7),
                     background="#FFFFFF", foreground=INK, bordercolor=LINE,
                     relief="flat", focusthickness=0)
        st.map("TButton", background=[("active", "#EDF1F9")])
        st.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"),
                     padding=(20, 9), background=PINK, foreground="#FFFFFF",
                     bordercolor=PINK, relief="flat", focusthickness=0)
        st.map("Accent.TButton",
               background=[("active", "#E21F49"), ("disabled", "#F3B7C4")])
        st.configure("Brand.Horizontal.TProgressbar", troughcolor="#E9EDF6",
                     background=PINK, bordercolor="#E9EDF6",
                     lightcolor=PINK, darkcolor=PINK, thickness=10)

    def _header(self):
        bar = tk.Canvas(self.root, height=4, highlightthickness=0, bd=0)
        bar.pack(fill="x")
        w = 700
        for x in range(0, w, 2):
            t = x / w
            color = "#%02x%02x%02x" % (
                int(254 + (37 - 254) * t),
                int(44 + (244 - 44) * t),
                int(85 + (238 - 85) * t),
            )
            bar.create_rectangle(x, 0, x + 2, 4, fill=color, outline=color)

        head = ttk.Frame(self.root, style="Card.TFrame", padding=(18, 14))
        head.pack(fill="x")
        try:
            self.logo_img = tk.PhotoImage(
                file=resource_path(os.path.join("assets", "app_logo.png"))
            )
            tk.Label(head, image=self.logo_img, bg=CARD, bd=0).pack(side="left", padx=(0, 14))
        except Exception:
            pass
        texts = ttk.Frame(head, style="Card.TFrame")
        texts.pack(side="left")
        ttk.Label(texts, text="抖音视频下载器", style="Title.TLabel").pack(anchor="w")
        ttk.Label(texts, text="无水印原片 · 保留原声 · 一键保存到本地",
                  style="Sub.TLabel").pack(anchor="w", pady=(3, 0))

    def _body(self):
        body = ttk.Frame(self.root, padding=(18, 14, 18, 16))
        body.pack(fill="both", expand=True)

        row1 = ttk.Frame(body)
        row1.pack(fill="x")
        ttk.Label(row1, text="①  粘贴抖音链接", style="Step.TLabel").pack(side="left")
        self.count_var = tk.StringVar(value="已识别 0 个链接")
        ttk.Label(row1, textvariable=self.count_var, style="Hint.TLabel").pack(side="right")

        box = tk.Frame(body, bg=LINE, bd=0, highlightthickness=0)
        box.pack(fill="x", pady=(7, 10))
        inner = tk.Frame(box, bg=CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.txt = tk.Text(inner, height=5, wrap="word", bd=0, relief="flat",
                           bg=CARD, fg="#9AA3B2", padx=12, pady=10,
                           font=("Microsoft YaHei UI", 10),
                           selectbackground="#DCE3F5")
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("1.0", PLACEHOLDER)
        self.txt.bind("<FocusIn>", self._on_focus_in)
        self.txt.bind("<FocusOut>", self._on_focus_out)
        self.txt.bind("<KeyRelease>", self._update_count)
        self.txt.bind("<Control-Return>", lambda e: self.start())

        btns = ttk.Frame(body)
        btns.pack(fill="x")
        self.btn = ttk.Button(btns, text="开始下载", style="Accent.TButton",
                              command=self.start)
        self.btn.pack(side="left")
        ttk.Button(btns, text="清空", command=self.clear).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="打开保存文件夹", command=self.open_dir).pack(
            side="left", padx=(8, 0))
        ttk.Label(btns, text="Ctrl + Enter 快捷下载", style="Hint.TLabel").pack(side="right")

        ttk.Label(body, text="②  保存位置", style="Step.TLabel").pack(
            anchor="w", pady=(16, 6))
        pathrow = ttk.Frame(body)
        pathrow.pack(fill="x")
        self.dir_var = tk.StringVar(value=self.outdir)
        ttk.Label(pathrow, textvariable=self.dir_var, style="Hint.TLabel").pack(side="left")
        ttk.Button(pathrow, text="更改…", command=self.choose_dir).pack(side="right")

        ttk.Label(body, text="③  进度与日志", style="Step.TLabel").pack(
            anchor="w", pady=(16, 6))
        self.status_var = tk.StringVar(value="等待任务")
        ttk.Label(body, textvariable=self.status_var, style="TLabel").pack(anchor="w")
        self.pb = ttk.Progressbar(body, style="Brand.Horizontal.TProgressbar",
                                  mode="determinate", maximum=100)
        self.pb.pack(fill="x", pady=(6, 10))

        self.logbox = scrolledtext.ScrolledText(
            body, height=8, wrap="word", bd=0, relief="flat", bg=CARD, fg=INK,
            padx=12, pady=10, font=("Microsoft YaHei UI", 9))
        self.logbox.pack(fill="both", expand=True)
        self.logbox.tag_config("ok", foreground=OK)
        self.logbox.tag_config("err", foreground=ERR)
        self.logbox.tag_config("dim", foreground=MUTED)
        self.logbox.configure(state="disabled")

    # ---------------------------------------------------------------- 交互
    def _on_focus_in(self, _e):
        if self.has_placeholder:
            self.txt.delete("1.0", "end")
            self.txt.configure(fg=INK)
            self.has_placeholder = False

    def _on_focus_out(self, _e):
        if not self.txt.get("1.0", "end").strip():
            self.txt.insert("1.0", PLACEHOLDER)
            self.txt.configure(fg="#9AA3B2")
            self.has_placeholder = True

    def _update_count(self, _e=None):
        text = "" if self.has_placeholder else self.txt.get("1.0", "end")
        self.count_var.set("已识别 %d 个链接" % len(extract_urls(text)))

    def clear(self):
        self.txt.delete("1.0", "end")
        self.has_placeholder = False
        self.txt.configure(fg=INK)
        self._update_count()

    def choose_dir(self):
        d = filedialog.askdirectory(
            initialdir=self.outdir if os.path.isdir(self.outdir) else app_dir())
        if d:
            self.outdir = d
            self.dir_var.set(d)

    def open_dir(self):
        os.makedirs(self.outdir, exist_ok=True)
        try:
            os.startfile(self.outdir)
        except Exception:
            subprocess.Popen(["explorer", self.outdir])

    def log(self, msg, tag=None):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n", tag or ())
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    # ---------------------------------------------------------------- 下载
    def start(self):
        if self.busy:
            return
        urls = extract_urls(self.txt.get("1.0", "end"))
        if not urls:
            messagebox.showwarning("提示", "没有识别到链接，请先粘贴抖音分享口令。")
            return
        self.busy = True
        self.btn.configure(state="disabled", text="下载中…")
        self.pb["value"] = 0
        self.log("—" * 34, "dim")
        threading.Thread(target=self.worker, args=(urls,), daemon=True).start()

    def progress(self, done, total):
        pct = int(done * 100 / total) if total else 0
        text = ("下载中  %d%%   %.2f / %.2f MB" % (pct, done / 1048576, total / 1048576)
                if total else "下载中  %.2f MB" % (done / 1048576))
        self.q.put(("prog", pct, text))

    def worker(self, urls):
        os.makedirs(self.outdir, exist_ok=True)
        ok = 0
        for i, u in enumerate(urls, 1):
            self.q.put(("status", "正在处理第 %d/%d 个链接" % (i, len(urls))))
            try:
                download_one(u, self.outdir,
                             log=lambda m: self.q.put(("log", m)),
                             progress=self.progress)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                self.q.put(("log", "失败：%s" % exc, "err"))
        msg = "全部完成：成功 %d/%d，保存在 %s" % (ok, len(urls), self.outdir)
        self.q.put(("done", msg, ok == len(urls)))

    def poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "log":
                    msg = item[1]
                    tag = item[2] if len(item) > 2 else None
                    if not tag:
                        if msg.startswith("完成"):
                            tag = "ok"
                        elif msg.startswith("风控预热"):
                            tag = "dim"
                    self.log(msg, tag)
                elif kind == "prog":
                    self.pb["value"] = item[1]
                    self.status_var.set(item[2])
                elif kind == "status":
                    self.status_var.set(item[1])
                elif kind == "done":
                    msg, success = item[1], item[2]
                    self.status_var.set("任务完成" if success else "部分任务失败")
                    self.pb["value"] = 100 if success else self.pb["value"]
                    self.log(msg, "ok" if success else "err")
                    self.busy = False
                    self.btn.configure(state="normal", text="开始下载")
                    if success:
                        if messagebox.askyesno("完成", msg + "\n\n现在打开保存文件夹吗？"):
                            self.open_dir()
                    else:
                        messagebox.showwarning("完成", msg)
        except queue.Empty:
            pass
        self.root.after(120, self.poll)


def run_gui():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
