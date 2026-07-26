"""音频 tag 写入：使用 mutagen 写入标题、艺术家、专辑、封面（已有则保持不动）"""

from pathlib import Path

from utils.logging_setup import get_logger

logger = get_logger(__name__)


def write_tags(
    audio_path: str,
    title: str = "",
    artist: str = "",
    album: str = "",
    cover_bytes: bytes | None = None,
    cover_mime: str = "image/jpeg",
) -> dict[str, bool]:
    """
    向音频文件写入 tag，已有字段保持不动。

    返回 {"title": bool, "artist": bool, "album": bool, "cover": bool}，
    表示每个字段是否成功写入（False 表示已存在或写入失败）。
    """
    ext = Path(audio_path).suffix.lower()
    result = {"title": False, "artist": False, "album": False, "cover": False}

    try:
        if ext == ".mp3":
            _write_mp3(audio_path, title, artist, album, cover_bytes, cover_mime, result)
        elif ext == ".flac":
            _write_flac(audio_path, title, artist, album, cover_bytes, cover_mime, result)
        elif ext == ".m4a":
            _write_mp4(audio_path, title, artist, album, cover_bytes, cover_mime, result)
    except Exception as e:
        logger.warning("写入 tag 失败 %s: %s", audio_path, e, exc_info=True)

    return result


# ── MP3 (ID3) ────────────────────────────────────────────────────────────────


def _write_mp3(path, title, artist, album, cover_bytes, mime, result):
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    if title and not tags.get("TIT2"):
        tags.add(TIT2(encoding=3, text=title))
        result["title"] = True

    if artist and not tags.get("TPE1"):
        tags.add(TPE1(encoding=3, text=artist))
        result["artist"] = True

    if album and not tags.get("TALB"):
        tags.add(TALB(encoding=3, text=album))
        result["album"] = True

    # 检测是否已有封面：遍历所有 key，匹配 "APIC" 前缀
    has_cover = any(k.startswith("APIC") for k in tags.keys())
    if cover_bytes and not has_cover:
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="", data=cover_bytes))
        result["cover"] = True

    # v2_version=3 强制输出 ID3v2.3，兼容主流播放器
    tags.save(path, v2_version=3)


# ── FLAC ─────────────────────────────────────────────────────────────────────


def _write_flac(path, title, artist, album, cover_bytes, mime, result):
    from mutagen.flac import FLAC, Picture

    audio = FLAC(path)

    if title and not audio.get("title"):
        audio["title"] = title
        result["title"] = True

    if artist and not audio.get("artist"):
        audio["artist"] = artist
        result["artist"] = True

    if album and not audio.get("album"):
        audio["album"] = album
        result["album"] = True

    if cover_bytes and not audio.pictures:
        pic = Picture()
        pic.type = 3  # Cover (front)
        pic.mime = mime
        pic.data = cover_bytes
        audio.add_picture(pic)
        result["cover"] = True

    audio.save()


# ── M4A (MP4) ────────────────────────────────────────────────────────────────


def _write_mp4(path, title, artist, album, cover_bytes, mime, result):
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()

    if title and not audio.tags.get("\xa9nam"):
        audio.tags["\xa9nam"] = [title]
        result["title"] = True

    if artist and not audio.tags.get("\xa9ART"):
        audio.tags["\xa9ART"] = [artist]
        result["artist"] = True

    if album and not audio.tags.get("\xa9alb"):
        audio.tags["\xa9alb"] = [album]
        result["album"] = True

    if cover_bytes and not audio.tags.get("covr"):
        img_format = MP4Cover.FORMAT_JPEG if "jpeg" in mime else MP4Cover.FORMAT_PNG
        audio.tags["covr"] = [MP4Cover(cover_bytes, imageformat=img_format)]
        result["cover"] = True

    audio.save()
