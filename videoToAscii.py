#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
aa_video_ascii_64palette.py

依存:
    pip install opencv-python numpy yt-dlp
    （GUI 不要な環境では opencv-python-headless を使ってください）

使い方（例）:
    python aa_video_ascii_64palette.py "https://www.youtube.com/watch?v=XXXX"
    python aa_video_ascii_64palette.py local.mp4 --levels 4 --clahe

注意:
- ターミナルが ANSI TrueColor をサポートしていれば色が正しく表示されます。
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
import re
from typing import Optional
from urllib.parse import urlparse

try:
    import cv2
    import numpy as np
except Exception:
    sys.stderr.write("必要なライブラリが見つかりません。pip install opencv-python numpy\n")
    raise

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


def download_subtitles(url: str, tmpdir: str) -> Optional[str]:
    """
    Download subtitles from a YouTube URL using yt-dlp.
    Returns the path to the downloaded subtitle file, or None if unavailable.
    """
    out_template = os.path.join(tmpdir, "%(id)s.%(ext)s")
    try:
        if _HAS_YTDLP:
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["ja", "en"],
                "subtitlesformat": "vtt/srt/best",
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
        else:
            # fallback to external yt-dlp command
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", "ja,en",
                "--sub-format", "vtt/srt/best",
                "-o", out_template,
                url
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return None
        
        # Find subtitle file in tmpdir
        subtitle_files = [
            f for f in os.listdir(tmpdir)
            if f.endswith((".vtt", ".srt", ".ja.vtt", ".en.vtt", ".ja.srt", ".en.srt"))
        ]
        if subtitle_files:
            # Prefer Japanese subtitles
            ja_files = [f for f in subtitle_files if ".ja." in f]
            if ja_files:
                return os.path.join(tmpdir, ja_files[0])
            return os.path.join(tmpdir, subtitle_files[0])
        return None
    except Exception:
        return None


def extract_text_from_subtitle(subtitle_path: str) -> str:
    """
    Extract plain text from a subtitle file (VTT or SRT format).
    Returns the concatenated text content.
    """
    try:
        with open(subtitle_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove VTT/SRT metadata and timestamps
        # Remove WEBVTT header
        content = re.sub(r"^WEBVTT.*?\n\n", "", content, flags=re.MULTILINE)
        # Remove timestamp lines (e.g., "00:00:01.000 --> 00:00:05.000")
        content = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}", "", content)
        # Remove sequence numbers
        content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)
        # Remove HTML-like tags
        content = re.sub(r"<[^>]+>", "", content)
        # Remove extra whitespace
        content = re.sub(r"\n\n+", "\n", content)
        
        return content.strip()
    except Exception:
        return ""


def extract_kanji(text: str) -> list[str]:
    """
    Extract unique kanji characters from text.
    Returns a list of unique kanji characters in order of appearance.
    
    Note: This uses the CJK Unified Ideographs Unicode range (U+4E00-U+9FFF),
    which includes Japanese kanji, Chinese hanzi, and Korean hanja.
    For Japanese subtitle context, this primarily extracts kanji.
    """
    # CJK Unified Ideographs range: U+4E00 to U+9FFF
    # (includes Japanese kanji, Chinese hanzi, Korean hanja)
    kanji_pattern = r"[\u4E00-\u9FFF]"
    kanji_matches = re.findall(kanji_pattern, text)
    
    # Preserve order while removing duplicates
    seen = set()
    unique_kanji = []
    for k in kanji_matches:
        if k not in seen:
            seen.add(k)
            unique_kanji.append(k)
    
    return unique_kanji


def create_ramp_with_kanji(kanji_list: list[str], original_ramp: str = DEFAULT_RAMP) -> str:
    """
    Create a new character ramp by prepending kanji to the original ramp.
    If no kanji are provided, return the original ramp.
    """
    if not kanji_list:
        return original_ramp
    
    kanji_str = "".join(kanji_list)
    return kanji_str + original_ramp


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
    args = parse_args()
    src = args.input
    tmpdir = None
    downloaded = False
    video_path = src
    cut_requested_for_url = False
    max_process_frames = None  # for local file cut: how many frames to process
    custom_ramp = args.chars  # Initialize with command-line provided chars or DEFAULT_RAMP

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
            
            # Extract subtitles and kanji for YouTube URLs
            try:
                sys.stderr.write("字幕を取得しています...\n")
                subtitle_path = download_subtitles(src, tmpdir)
                if subtitle_path:
                    sys.stderr.write(f"字幕を取得しました: {subtitle_path}\n")
                    subtitle_text = extract_text_from_subtitle(subtitle_path)
                    if subtitle_text:
                        kanji_list = extract_kanji(subtitle_text)
                        if kanji_list:
                            sys.stderr.write(f"字幕から {len(kanji_list)} 個の漢字を抽出しました\n")
                            custom_ramp = create_ramp_with_kanji(kanji_list, args.chars)
                            sys.stderr.write(f"文字ランプを更新しました（漢字を先頭に追加）\n")
                        else:
                            sys.stderr.write("字幕に漢字が見つかりませんでした\n")
                else:
                    sys.stderr.write("字幕が利用できません\n")
            except Exception as subtitle_error:
                # If subtitle extraction fails, continue with original ramp
                sys.stderr.write(f"字幕の処理中にエラーが発生しました（スキップします）: {subtitle_error}\n")
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
                chars=custom_ramp,
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

