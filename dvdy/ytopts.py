"""Traduce las opciones elegidas en la interfaz a parámetros de la API de yt-dlp."""
import os

from .config import ARCHIVE_FILE, cfg
from .utils import find_ffmpeg, find_js_runtime, parse_time

VIDEO_QUALITIES = [
    ("Máxima disponible", "best"), ("8K (4320p)", "4320"), ("4K (2160p)", "2160"),
    ("1440p (2K)", "1440"), ("1080p (Full HD)", "1080"), ("720p (HD)", "720"),
    ("480p", "480"), ("360p", "360"), ("240p", "240"), ("144p", "144"),
]
CONTAINERS = [("MP4", "mp4"), ("MKV", "mkv"), ("WebM", "webm"), ("MOV", "mov")]
VIDEO_CODECS = [
    ("Automático (mejor calidad)", "any"), ("H.264 / AVC (máxima compatibilidad)", "h264"),
    ("H.265 / HEVC", "h265"), ("VP9", "vp9"), ("AV1 (más eficiente)", "av01"),
]
FPS_OPTIONS = [("Automático", "any"), ("Preferir 60 fps", "60"), ("Máximo 30 fps", "30")]
AUDIO_FORMATS = [
    ("MP3", "mp3"), ("M4A (AAC)", "m4a"), ("Opus", "opus"), ("FLAC (sin pérdida)", "flac"),
    ("WAV (sin compresión)", "wav"), ("AAC", "aac"), ("OGG Vorbis", "vorbis"),
    ("ALAC (Apple sin pérdida)", "alac"), ("Original (sin convertir)", "best"),
]
AUDIO_QUALITIES = [
    ("320 kbps", "320K"), ("256 kbps", "256K"), ("192 kbps", "192K"), ("160 kbps", "160K"),
    ("128 kbps", "128K"), ("96 kbps", "96K"), ("VBR máxima (0)", "0"), ("VBR media (5)", "5"),
]
SPONSOR_CATEGORIES = [
    ("sponsor", "Patrocinios"), ("intro", "Intro / intermedios"), ("outro", "Créditos / final"),
    ("selfpromo", "Autopromoción"), ("preview", "Avances / resúmenes"), ("filler", "Relleno"),
    ("interaction", "Recordatorios (suscríbete…)"), ("music_offtopic", "Música: partes sin música"),
]
SUB_FORMATS = [("SRT", "srt"), ("VTT", "vtt"), ("ASS", "ass"), ("Original", "best")]
TEMPLATE_PRESETS = [
    ("Título", "%(title)s.%(ext)s"),
    ("Título [ID]", "%(title)s [%(id)s].%(ext)s"),
    ("Canal - Título", "%(uploader)s - %(title)s.%(ext)s"),
    ("Fecha - Título", "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"),
    ("Canal / Título", "%(uploader)s/%(title)s.%(ext)s"),
    ("Playlist / Nº - Título", "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"),
    ("Artista - Título", "%(artist,uploader)s - %(track,title)s.%(ext)s"),
]
SQUARE_CROP = "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'"


def base_opts():
    """Opciones comunes de red / autenticación / programas tomadas de Ajustes."""
    o = {
        "quiet": True,
        "no_warnings": False,
        "noprogress": True,
        "retries": int(cfg["retries"] or 10),
        "fragment_retries": int(cfg["retries"] or 10),
        "concurrent_fragment_downloads": int(cfg["concurrent_fragments"] or 1),
        "geo_bypass": bool(cfg["geo_bypass"]),
        "windowsfilenames": True,
    }
    ff = find_ffmpeg()
    if ff:
        o["ffmpeg_location"] = ff
    name, path = find_js_runtime()
    if name:
        o["js_runtimes"] = {name: {"path": path}}
    if cfg["cookies_browser"]:
        o["cookiesfrombrowser"] = (cfg["cookies_browser"],)
    if cfg["cookies_file"] and os.path.isfile(cfg["cookies_file"]):
        o["cookiefile"] = cfg["cookies_file"]
    if cfg["proxy"]:
        o["proxy"] = cfg["proxy"]
    if cfg["rate_limit"]:
        from yt_dlp.utils import parse_bytes
        rl = parse_bytes(cfg["rate_limit"])
        if rl:
            o["ratelimit"] = rl
    return o


def build_opts(c):
    """c: diccionario con las elecciones de la interfaz (ver OptionsPanel.values())."""
    from yt_dlp.postprocessor.metadataparser import MetadataParserPP
    from yt_dlp.utils import download_range_func

    o = base_opts()
    pps = []
    mode = c.get("mode", "av")
    container = c.get("container", "mp4")
    audio_fmt = c.get("audio_format", "mp3")

    # ---------------- Selección de formato ----------------
    sort = []
    q = c.get("quality", "best")
    if q != "best":
        sort.append(f"res:{q}")
    if c.get("fps") == "60":
        sort.append("fps")
    elif c.get("fps") == "30":
        sort.append("fps:30")
    vc = c.get("vcodec", "any")
    if vc != "any":
        sort.append(f"vcodec:{vc}")
    if mode in ("av", "video"):
        if container == "mp4" and vc == "h264":
            sort.append("acodec:aac")
        if container == "webm":
            sort += ["vcodec:vp9", "acodec:opus"]

    if mode == "custom" and c.get("format_string"):
        o["format"] = c["format_string"]
        o["merge_output_format"] = container
    elif mode == "audio":
        o["format"] = "ba/b"
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": audio_fmt,
                    "preferredquality": c.get("audio_quality", "0"), "nopostoverwrites": False})
        if audio_fmt != "best":
            o["final_ext"] = {"vorbis": "ogg", "alac": "m4a"}.get(audio_fmt, audio_fmt)
    elif mode == "video":
        o["format"] = "bv/bv*/b"
    else:
        o["format"] = "bv*+ba/b"
        o["merge_output_format"] = "webm/mkv" if container == "webm" else container
    if sort:
        o["format_sort"] = sort
    if mode in ("av", "video", "custom") and container in ("mp4", "mkv", "mov"):
        pps.append({"key": "FFmpegVideoRemuxer", "preferedformat": container})
        o["final_ext"] = container
    if c.get("keep_video"):
        o["keepvideo"] = True

    # ---------------- Metadatos ----------------
    actions = []
    if c.get("parse_artist_title"):
        actions.append((MetadataParserPP.Actions.INTERPRET, "%(artist,creator,uploader)s", "%(artist)s"))
        actions.append((MetadataParserPP.Actions.REPLACE, "artist", r"\s+-\s+Topic$", ""))
        actions.append((MetadataParserPP.Actions.INTERPRET, "title", r"(?P<artist>.+?)\s+[-–—]\s+(?P<title>.+)"))
        actions.append((MetadataParserPP.Actions.REPLACE, "title",
                        r"\s*[\(\[](?:official|oficial|lyric|letra|audio|video|videoclip|visualizer|hd|4k)[^\)\]]*[\)\]]",
                        ""))
    if c.get("album_from_playlist"):
        actions.append((MetadataParserPP.Actions.INTERPRET, "%(album,playlist_title)s", "%(album)s"))
        actions.append((MetadataParserPP.Actions.INTERPRET, "%(track_number,playlist_index)s", "%(track_number)s"))
    if actions:
        pps.insert(0, {"key": "MetadataParser", "actions": actions, "when": "pre_process"})

    # ---------------- SponsorBlock ----------------
    sb_mode = c.get("sponsorblock", "none")
    cats = set(c.get("sponsor_categories") or [])
    if sb_mode != "none" and cats:
        pps.insert(1 if actions else 0, {"key": "SponsorBlock", "categories": cats, "when": "after_filter"})

    # ---------------- Miniaturas ----------------
    embed_thumb = c.get("embed_thumbnail") and not (mode != "audio" and container == "webm")
    if embed_thumb or c.get("write_thumbnail"):
        o["writethumbnail"] = True
        pps.insert(0, {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
        if c.get("square_thumbnail"):
            o["postprocessor_args"] = {
                "thumbnailsconvertor+ffmpeg_o": ["-c:v", "mjpeg", "-qmin", "1", "-qscale:v", "1",
                                                 "-vf", SQUARE_CROP]}
        if not c.get("write_thumbnail"):
            o.setdefault("outtmpl", {})["pl_thumbnail"] = ""

    # ---------------- Subtítulos ----------------
    if c.get("subs"):
        langs = [l.strip() for l in (c.get("sub_langs") or "es,en").split(",") if l.strip()]
        o["subtitleslangs"] = langs or ["all"]
        o["writesubtitles"] = True
        if c.get("auto_subs"):
            o["writeautomaticsub"] = True
        sfmt = c.get("sub_format", "srt")
        if sfmt != "best":
            o["subtitlesformat"] = f"{sfmt}/best"
            pps.append({"key": "FFmpegSubtitlesConvertor", "format": sfmt, "when": "before_dl"})
        if c.get("embed_subs") and mode != "audio":
            pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": bool(c.get("keep_sub_files"))})

    # ---------------- Capítulos y SponsorBlock (edición) ----------------
    if sb_mode != "none" and cats:
        pps.append({
            "key": "ModifyChapters",
            "remove_chapters_patterns": [],
            "remove_sponsor_segments": cats if sb_mode == "remove" else set(),
            "remove_ranges": [],
            "sponsorblock_chapter_title": "[SponsorBlock]: %(category_names)l",
            "force_keyframes": False,
        })

    add_meta = bool(c.get("embed_metadata"))
    add_chapters = bool(c.get("embed_chapters")) or sb_mode == "mark"
    if add_meta or add_chapters:
        pps.append({"key": "FFmpegMetadata", "add_chapters": add_chapters, "add_metadata": add_meta,
                    "add_infojson": "if_exists" if add_meta else None})
    if embed_thumb:
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": bool(c.get("write_thumbnail"))})
    if c.get("split_chapters"):
        pps.append({"key": "FFmpegSplitChapters", "force_keyframes": False})

    # ---------------- Fragmento ----------------
    if c.get("section"):
        start = parse_time(c.get("section_start")) or 0
        end = parse_time(c.get("section_end"))
        o["download_ranges"] = download_range_func(None, [(start, end if end else float("inf"))])
        o["force_keyframes_at_cuts"] = bool(c.get("precise_cut"))

    # ---------------- Archivos extra ----------------
    if c.get("write_description"):
        o["writedescription"] = True
    if c.get("write_info_json"):
        o["writeinfojson"] = True
    if c.get("write_comments"):
        o["getcomments"] = True
        o["writeinfojson"] = True

    # ---------------- Salida ----------------
    outdir = c.get("output_dir") or cfg["output_dir"]
    o["paths"] = {"home": outdir}
    tmpl = o.setdefault("outtmpl", {})
    tmpl["default"] = c.get("template") or cfg["filename_template"]
    tmpl["chapter"] = "%(title)s/%(section_number)02d - %(section_title)s.%(ext)s"
    o["restrictfilenames"] = bool(c.get("restrict_filenames", cfg["restrict_filenames"]))
    if c.get("no_overwrite", True):
        o["overwrites"] = False
    else:
        o["overwrites"] = True

    # ---------------- Playlists ----------------
    if c.get("noplaylist"):
        o["noplaylist"] = True
    if c.get("playlist_items"):
        o["playlist_items"] = c["playlist_items"]
    if c.get("playlist_reverse"):
        o["playlist_reverse"] = True
    if c.get("is_playlist"):
        o["ignoreerrors"] = "only_download"
    if c.get("use_archive"):
        os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
        o["download_archive"] = ARCHIVE_FILE

    # ---------------- Filtros ----------------
    filters = []
    if c.get("min_duration"):
        filters.append(f"duration >= {int(parse_time(c['min_duration']) or 0)}")
    if c.get("max_duration"):
        filters.append(f"duration <= {int(parse_time(c['max_duration']) or 0)}")
    if c.get("title_filter"):
        filters.append(f"title ~= '(?i){c['title_filter']}'")
    if filters:
        from yt_dlp.utils import match_filter_func
        o["match_filter"] = match_filter_func(" & ".join(filters))
    if c.get("date_after"):
        from yt_dlp.utils import DateRange
        o["daterange"] = DateRange(c["date_after"].replace("-", ""), None)

    if c.get("skip_download"):
        o["skip_download"] = True
    o["postprocessors"] = pps
    return o


def default_choices(audio=False):
    """Elecciones por defecto (desde Ajustes) para descargas rápidas."""
    return {
        "mode": "audio" if audio else "av",
        "quality": cfg["default_video_quality"],
        "container": cfg["default_container"],
        "vcodec": "any",
        "fps": "any",
        "audio_format": cfg["default_audio_format"],
        "audio_quality": cfg["default_audio_quality"],
        "embed_metadata": cfg["embed_metadata"],
        "embed_thumbnail": cfg["embed_thumbnail"],
        "square_thumbnail": audio,
        "parse_artist_title": audio,
        "output_dir": cfg["music_dir"] if audio else cfg["output_dir"],
        "template": cfg["filename_template"],
        "noplaylist": True,
    }


def info_opts(flat=False):
    o = base_opts()
    o["skip_download"] = True
    if flat:
        o["extract_flat"] = "in_playlist"
    return o
