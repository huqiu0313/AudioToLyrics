"""处理流程编排：加密解密 → 视频转音频 → 歌词搜索 → tag写入 → 人声分离 → 语音识别 → LRC 输出"""

import os
import shutil
import requests
from pathlib import Path
from typing import Callable

import zhconv

from utils.audio_info import extract_info
from utils.dep_installer import check_and_install
from core.internet_search import search_lyrics, search_song_info
from core.decryptor import is_encrypted, decrypt_audio
from core.video_converter import is_video, convert_to_audio
from core.tag_writer import write_tags
from core.separator import separate_vocals
from core.transcriber import transcribe
from core.lrc_builder import (
    build_lrc_from_whisper,
    save_lrc,
    get_lrc_path,
)


def process_file(
    audio_path: str,
    progress_callback: Callable[[int, str], None],
    config: dict | None = None,
) -> str:
    """
    处理单个音频/视频文件的完整流程。

    流程：
    -1. 若为加密音频 → 解密（首次使用自动下载解密工具）
    0. 若为视频且启用了自动转换 → 无损提取音轨
    1. 提取歌曲信息（标题/艺术家）
    2. 联网搜索官方歌词 + 专辑/封面
    3. 写入 tag（标题/艺术家/专辑/封面）
    4. 若找到歌词 → 直接保存 LRC
    5. 若未找到 → 检查是否启用 Demucs/Whisper → 分离 + 识别 → 生成 LRC
    6. 若设置了输出目录 → 移动成功文件到输出目录
    """
    cfg = config or {}
    whisper_model = cfg.get("whisper_model", "base")
    demucs_model = cfg.get("demucs_model", "htdemucs")
    providers = cfg.get("providers", None)
    auto_convert = cfg.get("auto_convert_video", True)
    use_demucs = cfg.get("use_demucs", False)
    use_whisper = cfg.get("use_whisper", False)
    output_dir = cfg.get("output_dir", None) or None
    delete_source = cfg.get("delete_source_after_convert", False)

    # ── Step -1: 加密文件解密 ─────────────────────────────────────────────
    if is_encrypted(audio_path):
        progress_callback(2, "检测到加密音频，正在解密...")
        try:
            original_path = audio_path
            audio_path = decrypt_audio(
                audio_path,
                output_dir=output_dir,
                progress_callback=progress_callback,
            )
            progress_callback(7, f"解密完成: {Path(audio_path).name}")
            _try_delete_source(delete_source, original_path, progress_callback)
        except Exception as e:
            ext = Path(audio_path).suffix.lower()
            raise RuntimeError(f"歌曲解码失败，文件格式为{ext}: {e}") from e

    # ── Step 0: 视频转音频 ────────────────────────────────────────────────
    if is_video(audio_path):
        if auto_convert:
            if not check_and_install(["imageio-ffmpeg"], progress_callback):
                raise RuntimeError("缺少 imageio-ffmpeg，无法进行视频转音频")
            progress_callback(3, "检测到视频文件，正在提取音轨...")
            try:
                original_path = audio_path
                audio_path = convert_to_audio(audio_path)
                progress_callback(8, f"音轨提取完成: {Path(audio_path).name}")
                _try_delete_source(delete_source, original_path, progress_callback)
            except Exception as e:
                raise RuntimeError(f"视频转音频失败: {e}") from e
        else:
            raise RuntimeError(f"跳过视频文件（未启用自动转换）: {Path(audio_path).name}")

    # ── Step 1: 提取歌曲信息 ──────────────────────────────────────────────
    progress_callback(10, "正在读取歌曲信息...")
    title, artist, alternates = extract_info(audio_path)
    lrc_path = get_lrc_path(audio_path)
    filename = Path(audio_path).name

    # ── Step 2: 联网搜索歌词 + 专辑/封面 ──────────────────────────────────
    progress_callback(18, f"正在联网搜索歌词: {title} - {artist}")
    search_result = search_lyrics(title, artist, providers=providers)

    if not search_result:
        for alt_title, alt_artist in alternates:
            progress_callback(18, f"尝试备选: {alt_title} - {alt_artist}")
            search_result = search_lyrics(alt_title, alt_artist, providers=providers)
            if search_result:
                title, artist = alt_title, alt_artist
                break

    # 提取搜索结果中的歌曲信息
    song_info: dict = {}
    official_lrc = ""
    source = ""
    if search_result:
        official_lrc, source, song_info = search_result
        song_info = song_info or {}

    # 若歌词搜索未返回专辑/封面，独立搜索一次
    if not song_info.get("album") and not song_info.get("cover_url") \
            and not song_info.get("matched_title") and not song_info.get("matched_artist"):
        progress_callback(30, "正在搜索专辑信息...")
        extra_info = search_song_info(title, artist, providers=providers)
        if extra_info:
            song_info.update({k: v for k, v in extra_info.items() if v})

    # 用联网匹配到的歌曲名/歌手名覆盖（比文件名解析更准确）
    tag_title = song_info.get("matched_title") or title
    tag_artist = song_info.get("matched_artist") or artist

    # ── Step 3: 下载封面 + 写入 tag ──────────────────────────────────────
    # 检查音频文件是否已有专辑/封面标签，有则跳过
    existing = _check_existing_tags(audio_path)

    cover_bytes = None
    cover_url = song_info.get("cover_url", "")
    if cover_url and not existing.get("cover"):
        progress_callback(35, "正在下载专辑封面...")
        try:
            # 根据域名自动加 Referer，绕过 CDN 防盗链
            headers = {}
            if "y.qq.com" in cover_url or "qq.com" in cover_url:
                headers["Referer"] = "https://y.qq.com"
            elif "kugou.com" in cover_url:
                headers["Referer"] = "https://www.kugou.com"
            elif "163.com" in cover_url:
                headers["Referer"] = "https://music.163.com"
            resp = requests.get(cover_url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 500:
                cover_bytes = resp.content
        except Exception:
            pass

    album = "" if existing.get("album") else song_info.get("album", "")
    progress_callback(38, "正在写入音频标签...")
    tag_result = write_tags(
        audio_path,
        title=tag_title,
        artist=tag_artist,
        album=album,
        cover_bytes=cover_bytes,
    )
    written = [k for k, v in tag_result.items() if v]
    if written:
        progress_callback(40, f"已写入标签: {', '.join(written)}")

    # ── Step 4: 保存官方歌词 ──────────────────────────────────────────────
    if official_lrc:
        official_lrc = zhconv.convert(official_lrc, "zh-cn")
        progress_callback(85, f"找到官方歌词（来源: {source}），正在保存...")
        save_lrc(official_lrc, lrc_path)
        # 移动到输出目录
        final_path = _move_to_output(audio_path, lrc_path, output_dir, progress_callback)
        progress_callback(100, f"完成（官方歌词 · {source}）: {filename}")
        return f"完成（官方歌词 · {source}）→ {final_path}"

    # ── Step 5: 未找到官方歌词 → 可选 Demucs + Whisper ───────────────────
    if not use_demucs and not use_whisper:
        msg = f"歌词匹配失败，匹配关键词为 {title} - {artist}，且未启用语音识别"
        progress_callback(100, msg)
        raise RuntimeError(f"{msg}: {filename}")

    progress_callback(45, "未找到官方歌词，准备语音识别...")

    # 检查并安装依赖
    deps_needed = []
    if use_demucs:
        deps_needed.append("demucs")
    if use_whisper:
        deps_needed.append("faster-whisper")
    if deps_needed:
        progress_callback(46, f"正在检查依赖: {', '.join(deps_needed)}...")
        if not check_and_install(deps_needed, progress_callback):
            raise RuntimeError(f"依赖安装失败（{', '.join(deps_needed)}），无法进行语音识别")

    # 人声分离（仅在启用时执行）
    vocals_path = audio_path
    if use_demucs:
        progress_callback(50, f"正在使用 Demucs ({demucs_model}) 分离人声...")
        vocals_path = separate_vocals(audio_path, model_name=demucs_model)
        progress_callback(60, "人声分离完成")
    else:
        progress_callback(50, "未启用 Demucs，使用原始音频进行识别...")

    # Whisper 识别
    if not use_whisper:
        msg = "未启用 Whisper，无法进行语音识别"
        progress_callback(100, msg)
        raise RuntimeError(f"{msg}: {filename}")

    progress_callback(65, f"正在使用 Whisper ({whisper_model}) 识别歌词...")
    segments = transcribe(vocals_path, model_name=whisper_model)

    if not segments:
        progress_callback(100, f"未识别到任何歌词: {filename}")
        raise RuntimeError(f"未识别到歌词: {filename}")

    # 繁体转简体
    for seg in segments:
        seg["text"] = zhconv.convert(seg["text"], "zh-cn")

    # 生成 LRC 并保存
    progress_callback(90, "正在生成 LRC 文件...")
    lrc_content = build_lrc_from_whisper(segments, title=title, artist=artist)
    save_lrc(lrc_content, lrc_path)
    progress_callback(95, f"LRC 已保存: {lrc_path}")

    # 移动到输出目录
    final_path = _move_to_output(audio_path, lrc_path, output_dir, progress_callback)
    if not Path(final_path).exists():
        raise RuntimeError(f"LRC 文件生成失败: {filename}")

    return f"完成（Whisper 识别 · {whisper_model}）→ {final_path}"


def _move_to_output(
    audio_path: str,
    lrc_path: str,
    output_dir: str | None,
    progress_callback: Callable[[int, str], None],
) -> str:
    """
    若设置了输出目录，将音频文件和 LRC 文件移动到输出目录。

    返回: 最终文件路径（用于显示）
    """
    if not output_dir:
        return lrc_path

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    final_lrc = lrc_path
    try:
        # 移动音频文件
        src_audio = Path(audio_path)
        if src_audio.exists():
            dst_audio = out_dir / src_audio.name
            shutil.move(str(src_audio), str(dst_audio))

        # 移动 LRC 文件
        src_lrc = Path(lrc_path)
        if src_lrc.exists():
            dst_lrc = out_dir / src_lrc.name
            shutil.move(str(src_lrc), str(dst_lrc))
            final_lrc = str(dst_lrc)

        progress_callback(98, f"已移动到输出目录: {out_dir.name}/")
    except Exception as e:
        progress_callback(98, f"移动到输出目录失败: {e}")

    return final_lrc


def _check_existing_tags(audio_path: str) -> dict[str, bool]:
    """检查音频文件是否已有专辑和封面标签，返回 {"album": bool, "cover": bool}"""
    result = {"album": False, "cover": False}
    try:
        ext = Path(audio_path).suffix.lower()
        if ext == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError
            try:
                tags = ID3(audio_path)
                result["album"] = bool(tags.get("TALB"))
                result["cover"] = any(k.startswith("APIC") for k in tags.keys())
            except ID3NoHeaderError:
                pass
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(audio_path)
            result["album"] = bool(audio.get("album"))
            result["cover"] = bool(audio.pictures)
        elif ext == ".m4a":
            from mutagen.mp4 import MP4
            audio = MP4(audio_path)
            if audio.tags:
                result["album"] = bool(audio.tags.get("\xa9alb"))
                result["cover"] = bool(audio.tags.get("covr"))
        elif ext == ".ogg":
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(audio_path)
            result["album"] = bool(audio.get("album"))
            result["cover"] = bool(audio.get("metadata_block_picture"))
    except Exception:
        pass
    return result


def _try_delete_source(enabled: bool, path: str, progress_callback: Callable[[int, str], None]) -> None:
    """若启用删除源文件，删除指定路径的文件"""
    if enabled and os.path.exists(path):
        os.remove(path)
        progress_callback(9, f"已删除源文件: {Path(path).name}")
