"""从音频文件元数据或文件名中提取歌曲名和艺术家信息"""

from pathlib import Path


def extract_info(audio_path: str) -> tuple[str, str, list[tuple[str, str]]]:
    """
    提取歌曲标题和艺术家。

    优先读取音频文件的 ID3/FLAC 元数据；
    若元数据缺失，则从文件名推断（支持 "艺术家 - 歌名" 或 "歌名 - 艺术家" 格式）。

    返回 (title, artist, alternates)：
    - title/artist: 首选结果
    - alternates: 备选的 (title, artist) 列表（来自文件名双向拆分）
    """
    title, artist = _read_metadata(audio_path)
    alternates: list[tuple[str, str]] = []
    if not title:
        title, artist, alternates = _parse_filename(audio_path)
    return title, artist, alternates


def _read_metadata(audio_path: str) -> tuple[str, str]:
    """尝试用 mutagen 读取音频元数据"""
    try:
        from mutagen import File as MutagenFile
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4

        ext = Path(audio_path).suffix.lower()

        if ext == ".mp3":
            audio = MutagenFile(audio_path)
            if audio and audio.tags:
                tags = audio.tags
                title = str(tags.get("TIT2", ""))
                artist = str(tags.get("TPE1", ""))
                return title.strip(), artist.strip()

        elif ext == ".flac":
            audio = FLAC(audio_path)
            title = _join(audio.get("title", []))
            artist = _join(audio.get("artist", []))
            return title, artist

        elif ext == ".m4a":
            audio = MP4(audio_path)
            title = _first(audio.tags.get("\xa9nam", []) if audio.tags else [])
            artist = _first(audio.tags.get("\xa9ART", []) if audio.tags else [])
            return title, artist

        elif ext == ".ogg":
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(audio_path)
            title = _first(audio.get("title", []))
            artist = _first(audio.get("artist", []))
            return title, artist

        else:
            # 通用尝试
            audio = MutagenFile(audio_path)
            if audio and audio.tags:
                for key in ("TIT2", "title", "TITLE"):
                    if key in audio.tags:
                        title = str(audio.tags[key])
                        artist = ""
                        for akey in ("TPE1", "artist", "ARTIST"):
                            if akey in audio.tags:
                                artist = str(audio.tags[akey])
                                break
                        return title.strip(), artist.strip()
    except Exception:
        pass
    return "", ""


def _parse_filename(audio_path: str) -> tuple[str, str, list[tuple[str, str]]]:
    """
    从文件名推断歌曲名和艺术家。

    返回 (title, artist, alternates)：
    - title/artist: 首选结果（默认按 "艺术家 - 歌名" 格式解析）
    - alternates: 备选 (title, artist) 组合列表（当首选不确定时提供）
    """
    stem = Path(audio_path).stem.strip()
    if " - " in stem:
        parts = stem.split(" - ", 1)
        part_a = parts[0].strip()
        part_b = parts[1].strip()
        # 默认 "艺术家 - 歌名"，备选 "歌名 - 艺术家"
        return part_b, part_a, [(part_a, part_b)]
    return stem, "", []


def _first(lst: list) -> str:
    """取列表第一个元素（转字符串），空列表返回空字符串"""
    if not lst:
        return ""
    val = lst[0]
    return str(val).strip() if val else ""


def _join(lst: list, sep: str = "/") -> str:
    """将列表元素用分隔符拼接（如 FLAC 多歌手），空列表返回空字符串"""
    if not lst:
        return ""
    return sep.join(str(v).strip() for v in lst if v)
