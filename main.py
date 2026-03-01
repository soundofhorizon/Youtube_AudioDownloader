import sys
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
import yt_dlp
import threading
import subprocess
import os
from pathlib import Path
import winsound

# ---------------- App ----------------
app = tb.Window(
    title="YouTube Audio Downloader",
    themename="darkly",
    size=(620, 360),
    resizable=(False, False)
)

# ---------------- Paths ----------------
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DOWNLOAD_DIR = BASE_DIR / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ---------------- State ----------------
download_files = []
total_count = 0

# ---------------- UI helpers ----------------
def set_dl_progress(v): dl_bar["value"] = v
def set_cv_progress(v): cv_bar["value"] = v
def start_cv_anim(): cv_bar.start(10)
def stop_cv_anim(): cv_bar.stop()
def set_percent(t): percent_label.config(text=t)
def set_speed(t): speed_label.config(text=f"速度: {t}")
def set_status(t): status_label.config(text=t)

def reset_progress(idx, phase):
    set_percent("0 %")
    set_speed("-- MB/s")
    set_status(f"({idx}/{total_count}) {phase}")

    if "ダウンロード" in phase:
        set_dl_progress(0)
        stop_cv_anim()
        set_cv_progress(0)
    else:
        set_dl_progress(100)
        start_cv_anim()

# ---------------- Logic ----------------
def download_audio():
    global download_files, total_count
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("エラー", "YouTubeのURLを入力してください")
        return

    set_status("初期化中…")
    download_files.clear()

    fmt = format_var.get()

    def hook(d):
        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            speed = d.get("speed")

            if total:
                percent = downloaded / total * 100
                app.after(0, set_dl_progress, percent)
                app.after(0, set_percent, f"{percent:.1f} %")

            if speed:
                app.after(0, set_speed, f"{speed/1024/1024:.2f} MB/s")

        elif d["status"] == "finished":
            download_files.append(Path(d["filename"]))

    def task():
        global total_count
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(DOWNLOAD_DIR / "%(playlist_index|)s%(title)s.%(ext)s"),
                "progress_hooks": [hook],
                "quiet": True,
                "noplaylist": False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = info["entries"] if "entries" in info else [info]
                total_count = len(entries)

                for i, e in enumerate(entries, start=1):
                    app.after(0, reset_progress, i, "ダウンロード中…")
                    ydl.download([e["webpage_url"]])

            app.after(0, set_dl_progress, 100)

            # ---- 変換 ----
            for i, webm in enumerate(download_files, start=1):
                app.after(0, reset_progress, i, f"webm → {fmt} へ変換中…")

                out = webm.with_suffix(f".{fmt}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", webm, out],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            stop_cv_anim()
            set_cv_progress(100)
            set_status("完了")
            set_percent("100 %")

            # webm 一括削除
            for f in download_files:
                if f.exists():
                    f.unlink()

            winsound.MessageBeep(winsound.MB_ICONASTERISK)

        except Exception as e:
            stop_cv_anim()
            messagebox.showerror("エラー", str(e))

    threading.Thread(target=task, daemon=True).start()

# ---------------- Dynamic UI update ----------------
def update_texts(*_):
    fmt = format_var.get()
    download_btn.config(text=f"{fmt}でダウンロード")
    convert_label.config(text=f"webm → {fmt} へ変換")

# ---------------- UI ----------------
tb.Label(app, text="YouTube URL をペースト", font=("Segoe UI", 12, "bold")).pack(pady=(8, 4))

url_entry = tb.Entry(app, width=65)
url_entry.pack(pady=(0, 8))

format_var = tk.StringVar(value="m4a")

seg = tb.Frame(app)
seg.pack(pady=(0, 10))

for f in ["m4a", "mp3", "ogg", "wav"]:
    tb.Radiobutton(
        seg,
        text=f.upper(),
        variable=format_var,
        value=f,
        bootstyle="toolbutton",
        padding=(14, 6)
    ).pack(side=LEFT, padx=4)

format_var.trace_add("write", update_texts)

download_btn = tb.Button(
    app,
    text="m4aでダウンロード",
    bootstyle="success-outline",
    width=32,
    command=download_audio
)
download_btn.pack(pady=(0, 10))

percent_label = tb.Label(app, text="0 %", font=("Segoe UI", 18, "bold"))
percent_label.pack()

speed_label = tb.Label(app, text="速度: -- MB/s", font=("Segoe UI", 11, "bold"))
speed_label.pack()

status_label = tb.Label(app, text="", font=("Segoe UI", 11, "bold"))
status_label.pack(pady=(2, 6))

# ---- ダウンロード ----
tb.Label(
    app,
    text="ダウンロード進捗",
    font=("Segoe UI", 11, "bold")
).pack(anchor="w", padx=16, pady=(4, 2))

dl_bar = tb.Progressbar(app, length=560, bootstyle="info-striped")
dl_bar.pack(pady=(0, 6))

# ---- 変換 ----
convert_label = tb.Label(
    app,
    text="webm → m4a へ変換",
    font=("Segoe UI", 11, "bold")
)
convert_label.pack(anchor="w", padx=16, pady=(4, 2))

cv_bar = tb.Progressbar(
    app,
    length=560,
    bootstyle="warning-striped",
    mode="indeterminate"
)
cv_bar.pack(pady=(0, 6))

app.mainloop()
