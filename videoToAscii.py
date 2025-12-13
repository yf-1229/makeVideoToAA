#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
videoToAscii.py

- ブロック描画は禁止（半ブロックモード無し）
- 文字の「濃度（ランプ）」で明暗を表現
- 色は文字の前景色で表現（ANSI を使用するが、値は 4-level per channel に量子化して 64 色に制限）
- YouTube URL に対しては yt-dlp を使ってメタ情報を取得し、30分を超える場合はダウンロードせずに
  「先頭30分だけ処理（カット）する」か「キャンセルするか」をユーザーに尋ねる。
- ローカルファイルは再生前に長さをチェックし、30分超なら同様にユーザーに確認する。
- width は 100 に固定（コマンドラインで変更不可）
- 新機能: YouTube 以外のリンク、あるいは https 以外のプロトコルが入力されたときは、
  処理をキャンセルしてアラート（端末プロンプトによる警告）を表示して終了する。
- Windows サポート: Windows コンソールで ANSI エスケープシーケンスを有効化（enable_vt_mode()）

依存:
    pip install opencv-python numpy yt-dlp
    （GUI 不要な環境では opencv-python-headless を使ってください）

使い方（例）:
    python videoToAscii.py "https://www.youtube.com/watch?v=XXXX"
    python videoToAscii.py local.mp4 --levels 4 --clahe
    
    Windows の場合:
    run_videoToAscii.cmd "https://www.youtube.com/watch?v=XXXX"
    または PowerShell: python videoToAscii.py "https://www.youtube.com/watch?v=XXXX"

注意:
- デフォルトでチャネル当たり 4 レベル (= 4^3 = 64 色) に量子化します。
- ターミナルが ANSI TrueColor をサポートしていれば色が正しく表示されます。
- Windows 10/11 では ANSI サポートが自動的に有効化されます（失敗しても処理は続行されます）
- インタラクティブなプロンプトが出ます。CI 等の非対話環境では動作しないことがあります。
"""
from __future__ import annotations
import argparse
import os
import sys
import tempfile
import shutil
import time
import subprocess
import json
from typing import Optional
from urllib.parse import urlparse

try:
    import cv2
    import numpy as np
except Exception:
    sys.stderr.write("必要なライブラリが見つかりません。pip install opencv-python numpy\n")
    raise


def enable_vt_mode():
    """
    Windows コンソールで ANSI VT (仮想端末) 処理を有効化する。
    ENABLE_VIRTUAL_TERMINAL_PROCESSING フラグを設定して、ANSI エスケープシーケンスを使えるようにする。
    失敗しても例外は発生させず、処理を続行する（非 Windows 環境や権限不足の場合でも安全）。
    """
    if sys.platform != "win32":
        # Windows 以外では何もしない
        return
    try:
        import ctypes
        from ctypes import wintypes

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11

        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if h_out == -1 or h_out is None:
            return

        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            return

        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(h_out, mode)
    except Exception:
        # ctypes が使えない、または設定に失敗した場合でも続行
        pass

# try import yt_dlp; fallback to external command
try:
    import yt_dlp  # type: ignore
    _HAS_YTDLP = True
except Exception:
    _HAS_YTDLP = False

# Characters ramp (left = dark, right = bright)
DEFAULT_RAMP = "$@B%8&WM#*oahkbdpqwmZ0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
DEFAULT_ASPECT = 0.55  # character aspect ratio correction
FIXED_WIDTH = 100      # width is fixed to 100 as requested
MAX_SECONDS = 30 * 60  # 30 minutes in seconds


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def is_allowed_youtube_https(url: str) -> bool:
    """
   許可される URL は:
      - プロトコルが https
      - ドメインが youtube.com のサブドメイン、または youtu.be
    それ以外は許可しない（ユーザーにアラートを出してキャンセルする）。
    """
    try:
        p = urlparse(url)
    except Exception:
        return False
    scheme = (p.scheme or "").lower()
    netloc = (p.netloc or "").lower()
    if scheme != "https":
        return False
    # allow domains like youtube.com, www.youtube.com, m.youtube.com, youtu.be
    if "youtube.com" in netloc or "youtu.be" in netloc:
        return True
    return False


def alert_and_exit(msg: str):
    """
    ユーザーにアラート（端末上での表示）して処理をキャンセルして終了する。
    非対話環境でも分かるようにメッセージを出力し、Enterで閉じるUIを表示。
    """
    banner = "=" * 60
    full = (
        f"\n{banner}\nALERT: {msg}\n処理をキャンセルしました。\n{banner}\n"
        "続行するには Enter を押してください...\n"
    )
    try:
        # print to stderr so it's clear this is an alert
        sys.stderr.write(full)
        # wait for user acknowledgement in interactive shell
        input()
    except Exception:
        # non-interactive -> just exit
        pass
    sys.exit(1)


def get_duration_from_url(url: str) -> Optional[float]:
    """
    Get duration in seconds from a URL using yt-dlp metadata (without downloading).
    Returns None if duration unknown or cannot fetch metadata.
    """
    if _HAS_YTDLP:
        try:
            ydl_opts = {"quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                dur = info.get("duration")
                if dur is None:
                    return None
                return float(dur)
        except Exception:
            return None
    else:
        # fallback to external yt-dlp --dump-json
        cmd = ["yt-dlp", "--dump-json", url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # yt-dlp may output multiple json objects for playlists; take first
            out = proc.stdout.strip().splitlines()[0]
            info = json.loads(out)
            dur = info.get("duration")
            if dur is None:
                return None
            return float(dur)
        except Exception:
            return None


def download_with_yt_dlp(url: str, tmpdir: str, cut_to_30: bool) -> str:
    """
    Download URL into tmpdir and return downloaded path.
    If cut_to_30 is True, request yt-dlp to download only the first 1800 seconds.
    Use format 'best' to try to avoid requiring ffmpeg merging when possible.
    """
    out_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
    if _HAS_YTDLP:
        ydl_opts = {
            "outtmpl": out_template,
            "format": "best",  # prefer single-file to reduce ffmpeg merging requirement
            "noplaylist": True,
            "quiet": False,
            "no_warnings": True,
        }
        if cut_to_30:
            # request only first 0-1800 seconds
            ydl_opts["download_sections"] = ["*0-1800"]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            try:
                filename = ydl.prepare_filename(info)
            except Exception:
                filename = newest_file_in_dir(tmpdir)
            if not os.path.exists(filename):
                filename = newest_file_in_dir(tmpdir)
            return filename
    else:
        cmd = ["yt-dlp", "-f", "best", "-o", out_template]
        if cut_to_30:
            cmd += ["--download-sections", "*0-1800"]
        cmd.append(url)
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            raise RuntimeError("yt-dlp によるダウンロードに失敗しました（外部コマンド）。ffmpeg の有無にも注意してください。")
        return newest_file_in_dir(tmpdir)


def newest_file_in_dir(d: str) -> str:
    files = [os.path.join(d, f) for f in os.listdir(d)]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        raise FileNotFoundError("ダウンロードファイルが見つかりません: " + d)
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files[0]


def get_duration_local(path: str) -> Optional[float]:
    """
    Get duration in seconds for a local video file using OpenCV metadata if possible.
    Returns None if cannot determine.
    """
    try:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        cap.release()
        if fps > 0 and frames > 0:
            return float(frames) / float(fps)
        # fallback: try probing with ffprobe if available
        return None
    except Exception:
        return None


def human_time(sec: Optional[float]) -> str:
    if sec is None:
        return "不明"
    s = int(sec)
    h = s // 3600
    m = (s % 3600) // 60
    s2 = s % 60
    if h:
        return f"{h}h{m:02d}m{s2:02d}s"
    if m:
        return f"{m}m{s2:02d}s"
    return f"{s2}s"


def get_terminal_size():
    return shutil.get_terminal_size(fallback=(80, 24))


def clear_screen():
    sys.stdout.write("\x1b[2J")
    sys.stdout.flush()


def move_cursor_home():
    sys.stdout.write("\x1b[H")
    sys.stdout.flush()


def quantize_palette_rgb_array(bgr: np.ndarray, levels_per_channel: int) -> np.ndarray:
    """
    BGR uint8 array -> quantized RGB uint8 array with levels_per_channel per channel.
    """
    arr = bgr.astype(np.float32) / 255.0
    B = arr[:, :, 0]
    G = arr[:, :, 1]
    R = arr[:, :, 2]
    L = float(max(1, levels_per_channel) - 1)
    qR = np.round(R * L).astype(np.int32)
    qG = np.round(G * L).astype(np.int32)
    qB = np.round(B * L).astype(np.int32)

    def expand(q):
        if levels_per_channel <= 1:
            return np.zeros_like(q, dtype=np.uint8)
        scale = 255.0 / L
        return np.clip((q.astype(np.float32) * scale).round(), 0, 255).astype(np.uint8)

    Rq = expand(qR)
    Gq = expand(qG)
    Bq = expand(qB)
    rgb = np.stack([Rq, Gq, Bq], axis=-1)  # RGB order
    return rgb


def frame_to_ascii(
    frame,
    chars: str = DEFAULT_RAMP,
    aspect: float = DEFAULT_ASPECT,
    invert: bool = False,
    gamma: float = 1.0,
    clahe_flag: bool = False,
    dither: bool = False,
    use_color: bool = True,
    levels_per_channel: int = 4,
    width: int = FIXED_WIDTH,
):
    """
    Convert BGR frame to ASCII text (width fixed to FIXED_WIDTH).
    """
    h, w = frame.shape[:2]
    # fixed width
    target_w = width
    target_h = max(1, int((h / w) * target_w * aspect))

    resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    if invert:
        gray = 1.0 - gray
    if gamma and gamma > 0:
        gray = np.clip(gray, 0.0, 1.0) ** (1.0 / float(gamma))
    if clahe_flag:
        gray_uint8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_uint8 = clahe.apply(gray_uint8)
        gray = gray_uint8.astype(np.float32) / 255.0

    n_chars = len(chars)
    indices = np.clip(np.rint(gray * (n_chars - 1)), 0, n_chars - 1).astype(np.int32)

    if use_color:
        rgb_quant = quantize_palette_rgb_array(resized, levels_per_channel)
    else:
        rgb_quant = None

    out_lines = []
    reset = "\x1b[0m"
    for y in range(target_h):
        if use_color:
            row_rgb = rgb_quant[y]
            row_idx = indices[y]
            row_parts = []
            for x in range(target_w):
                ch = chars[int(row_idx[x])]
                R, G, B = int(row_rgb[x, 0]), int(row_rgb[x, 1]), int(row_rgb[x, 2])
                row_parts.append(f"\x1b[38;2;{R};{G};{B}m{ch}{reset}")
            out_lines.append("".join(row_parts))
        else:
            row_idx = indices[y]
            out_lines.append("".join(chars[int(row_idx[x])] for x in range(target_w)))
    return "\n".join(out_lines)


def parse_args():
    p = argparse.ArgumentParser(
        description="ASCII アート（文字のみ）を色付きで表示。色を 4-level per channel に量子化して 64 色に制限します。width は 100 固定。"
    )
    p.add_argument("input", help="YouTube の URL またはローカル動画ファイルパス")
    p.add_argument("--chars", "-c", type=str, default=DEFAULT_RAMP, help="文字ランプ（左が濃い）")
    p.add_argument("--aspect", "-a", type=float, default=DEFAULT_ASPECT, help="縦横補正")
    p.add_argument("--no-color", dest="color", action="store_false", help="カラーを使わない")
    p.add_argument("--gamma", type=float, default=1.0, help="ガンマ補正（デフォルト1.0）")
    p.add_argument("--clahe", action="store_true", help="CLAHE を適用してコントラストを強める")
    p.add_argument("--dither", action="store_true", help="誤差拡散ディザ（速度低下注意）")
    p.add_argument("--levels", type=int, default=4, help="チャネル当たりの量子化レベル（デフォルト4 -> 4^3=64色）")
    p.add_argument("--loop", action="store_true", help="動画をループ再生")
    p.add_argument("--no-clear", action="store_true", help="開始時に画面をクリアしない")
    p.add_argument("--keep", action="store_true", help="ダウンロードしたファイルを削除せず残す")
    return p.parse_args()


def ask_user_cut_or_abort(source_desc: str, duration_sec: Optional[float]) -> bool:
    """
    Prompt the user when a video exceeds MAX_SECONDS.
    Returns True if the user chooses to process only the first 30 minutes (cut).
    Returns False if the user aborts.
    """
    dur_text = human_time(duration_sec)
    prompt = (
        f"{source_desc} の長さは {dur_text} です（30分を超えています）。\n"
        "オプション:\n"
        "  1) 先頭30分だけ処理して続行する（ダウンロードは先頭30分に限定します） -> 入力 y\n"
        "  2) キャンセルして 30 分以内の動画を指定する -> 入力 n\n"
        "選択してください (y/n): "
    )
    while True:
        try:
            ans = input(prompt).strip().lower()
        except EOFError:
            # non-interactive environment, default to abort
            return False
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("y か n を入力してください。")


def main():
    # Windows コンソールで ANSI サポートを有効化（起動時に一度だけ実行）
    enable_vt_mode()
    
    args = parse_args()
    src = args.input
    tmpdir = None
    downloaded = False
    video_path = src
    cut_requested_for_url = False
    max_process_frames = None  # for local file cut: how many frames to process

    # New feature: reject non-YouTube links or non-https protocols
    if is_url(src):
        if not is_allowed_youtube_https(src):
            alert_and_exit("YouTube の HTTPS リンク以外は受け付けません。YouTube の HTTPS (https://...) の URL を指定してください。")

    if is_url(src):
        # get duration metadata without downloading
        sys.stderr.write("URL のメタデータを取得しています...\n")
        duration = get_duration_from_url(src)
        if duration is None:
            # unknown duration -> ask whether proceed (treat as unknown and ask)
            sys.stderr.write("動画の長さが取得できませんでした。\n")
            proceed = ask_user_cut_or_abort("この URL", duration)
            if not proceed:
                sys.stderr.write("入力をキャンセルしました。30分以内の動画を指定してください。\n")
                sys.exit(1)
            else:
                # user chose to "cut" but we don't know real duration; attempt to download first 30 min
                cut_requested_for_url = True
        else:
            if duration > MAX_SECONDS:
                want_cut = ask_user_cut_or_abort("この URL", duration)
                if not want_cut:
                    sys.stderr.write("入力をキャンセルしました。30分以内の動画を指定してください。\n")
                    sys.exit(1)
                cut_requested_for_url = True
        # perform download (possibly with sections)
        tmpdir = tempfile.mkdtemp(prefix="aa_video_")
        sys.stderr.write(f"Downloading {src} into temporary dir {tmpdir} ...\n")
        try:
            video_path = download_with_yt_dlp(src, tmpdir, cut_to_30=cut_requested_for_url)
            downloaded = True
            sys.stderr.write(f"Downloaded -> {video_path}\n")
        except Exception as e:
            if tmpdir and os.path.isdir(tmpdir) and not args.keep:
                shutil.rmtree(tmpdir, ignore_errors=True)
            sys.stderr.write("ダウンロードに失敗しました: " + str(e) + "\n")
            sys.exit(1)
    else:
        # local file: check duration, prompt if over 30 minutes
        if not os.path.exists(video_path):
            sys.stderr.write(f"入力ファイルが見つかりません: {video_path}\n")
            sys.exit(1)
        duration = get_duration_local(video_path)
        if duration is not None and duration > MAX_SECONDS:
            want_cut = ask_user_cut_or_abort("このファイル", duration)
            if not want_cut:
                sys.stderr.write("入力をキャンセルしました。30分以内の動画を指定してください。\n")
                sys.exit(1)
            # compute how many frames to process: open capture to get fps & frame count
            cap_tmp = cv2.VideoCapture(video_path)
            fps = cap_tmp.get(cv2.CAP_PROP_FPS) or 0.0
            total_frames = cap_tmp.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
            cap_tmp.release()
            if fps > 0:
                max_process_frames = int(min(total_frames, fps * MAX_SECONDS)) if total_frames > 0 else int(fps * MAX_SECONDS)
            else:
                max_process_frames = None  # fallback: we'll stop by time condition later

    # open capture
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        sys.stderr.write("動画を開けませんでした: " + str(video_path) + "\n")
        if tmpdir and os.path.isdir(tmpdir) and not args.keep:
            shutil.rmtree(tmpdir, ignore_errors=True)
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    if fps <= 0 or fps != fps:
        fps = 24.0
    frame_time = 1.0 / fps

    if not args.no_clear:
        clear_screen()

    frame_idx = 0
    try:
        while True:
            if max_process_frames is not None and frame_idx >= max_process_frames:
                # reached the cut for local file
                break
            ret, frame = cap.read()
            if not ret:
                if args.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    continue
                else:
                    break
            start = time.time()

            ascii_frame = frame_to_ascii(
                frame,
                chars=args.chars,
                aspect=args.aspect,
                invert=False,
                gamma=args.gamma,
                clahe_flag=args.clahe,
                dither=args.dither,
                use_color=args.color,
                levels_per_channel=max(1, min(16, args.levels)),
                width=FIXED_WIDTH,
            )

            move_cursor_home()
            print(ascii_frame, end="", flush=True)

            elapsed = time.time() - start
            to_sleep = frame_time - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

            frame_idx += 1

    except KeyboardInterrupt:
        move_cursor_home()
        print("\n再生を中断しました。")
    finally:
        cap.release()
        if downloaded and tmpdir:
            if args.keep:
                sys.stderr.write(f"ダウンロードファイルは {tmpdir} に残しました (--keep).\n")
            else:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass


if __name__ == "__main__":
    main()