"""Funciones auxiliares: rutas de programas, formato de tamaños/tiempos, ffprobe."""
import json
import os
import re
import shutil
import subprocess
import sys

from .config import cfg

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

AUDIO_EXTS = {"mp3", "m4a", "aac", "flac", "wav", "ogg", "opus", "wma", "alac", "aiff", "aif", "mka", "ac3", "oga"}
VIDEO_EXTS = {"mp4", "mkv", "webm", "mov", "avi", "flv", "wmv", "m4v", "ts", "mpg", "mpeg", "3gp", "gif", "ogv"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "gif"}
SUB_EXTS = {"srt", "ass", "ssa", "vtt", "sub"}

MEDIA_FILTER = ("Multimedia (*.mp4 *.mkv *.webm *.mov *.avi *.flv *.wmv *.m4v *.ts *.mpg *.mpeg *.3gp "
                "*.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus *.wma *.aiff *.mka *.ac3);;Todos los archivos (*)")
VIDEO_FILTER = "Video (*.mp4 *.mkv *.webm *.mov *.avi *.flv *.wmv *.m4v *.ts *.mpg *.mpeg *.3gp);;Todos (*)"
AUDIO_FILTER = "Audio (*.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus *.wma *.aiff *.mka);;Todos (*)"
IMAGE_FILTER = "Imágenes (*.jpg *.jpeg *.png *.webp *.bmp);;Todos (*)"
SUB_FILTER = "Subtítulos (*.srt *.ass *.ssa *.vtt);;Todos (*)"


def ext_of(path):
    return os.path.splitext(path)[1].lstrip(".").lower()


def is_audio_file(path):
    return ext_of(path) in AUDIO_EXTS


def find_ffmpeg():
    custom = (cfg["ffmpeg_path"] or "").strip()
    if custom:
        if os.path.isdir(custom):
            cand = os.path.join(custom, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if os.path.isfile(cand):
                return cand
        elif os.path.isfile(custom):
            return custom
    from .deps import local_ffmpeg
    return local_ffmpeg() or shutil.which("ffmpeg")


def find_ffprobe():
    ff = find_ffmpeg()
    if ff:
        d = os.path.dirname(ff)
        cand = os.path.join(d, "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if os.path.isfile(cand):
            return cand
    return shutil.which("ffprobe")


def find_js_runtime():
    from .deps import local_deno
    if local_deno():
        return "deno", local_deno()
    for name in ("deno", "node", "bun"):
        p = shutil.which(name)
        if p:
            return name, p
    return None, None


def python_console_exe():
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.isfile(cand):
            return cand
    return exe


def run_quiet(cmd, timeout=30):
    """Ejecuta un comando y devuelve (código, salida)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, creationflags=CREATE_NO_WINDOW)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return -1, str(e)


def ffmpeg_version():
    ff = find_ffmpeg()
    if not ff:
        return None
    code, out = run_quiet([ff, "-version"], 10)
    if code != 0:
        return None
    m = re.search(r"ffmpeg version (\S+)", out)
    return m.group(1) if m else "?"


_encoders_cache = None


def ffmpeg_encoders():
    global _encoders_cache
    if _encoders_cache is not None:
        return _encoders_cache
    ff = find_ffmpeg()
    enc = set()
    if ff:
        code, out = run_quiet([ff, "-hide_banner", "-encoders"], 15)
        for line in out.splitlines():
            m = re.match(r"\s*[VAS][F.][S.][X.][B.][D.]\s+(\S+)", line)
            if m:
                enc.add(m.group(1))
    _encoders_cache = enc
    return enc


def ffprobe_json(path):
    fp = find_ffprobe()
    if not fp:
        raise RuntimeError("No se encontró ffprobe. Configura la ruta de FFmpeg en Ajustes.")
    code, out = run_quiet([fp, "-v", "error", "-print_format", "json", "-show_format",
                           "-show_streams", "-show_chapters", path], 60)
    if code != 0:
        raise RuntimeError(out.strip() or "ffprobe falló")
    return json.loads(out)


def media_duration(path):
    try:
        data = ffprobe_json(path)
        return float(data.get("format", {}).get("duration") or 0) or None
    except Exception:
        return None


def fmt_size(n):
    if n is None:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def fmt_time(sec):
    if sec is None:
        return "—"
    try:
        sec = int(round(float(sec)))
    except (TypeError, ValueError):
        return "—"
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_count(n):
    if n is None:
        return ""
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1e9:.1f} mil M"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f} M"
    if n >= 1_000:
        return f"{n / 1e3:.1f} K"
    return str(n)


def parse_time(text):
    """'1:23:45.5', '90', '2:30' -> segundos (float). Vacío -> None."""
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    parts = text.split(":")
    try:
        total = 0.0
        for p in parts:
            total = total * 60 + float(p)
        return total
    except ValueError:
        raise ValueError(f"Tiempo no válido: {text!r} (usa hh:mm:ss, mm:ss o segundos)")


def ts(seconds):
    """Segundos -> 'hh:mm:ss.mmm' para ffmpeg."""
    seconds = max(0.0, float(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


def derive_output(src, suffix, ext=None, folder=None):
    base = os.path.splitext(os.path.basename(src))[0]
    ext = ext or ext_of(src)
    folder = folder or os.path.dirname(src)
    return unique_path(os.path.join(folder, f"{base}{suffix}.{ext}"))


def open_path(path):
    if path and os.path.exists(path):
        os.startfile(path)


def reveal_path(path):
    if not path:
        return
    if os.path.isfile(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    elif os.path.isdir(path):
        os.startfile(path)
    elif os.path.isdir(os.path.dirname(path)):
        os.startfile(os.path.dirname(path))


def best_thumbnail_url(info):
    thumbs = info.get("thumbnails") or []
    jpgs = [t for t in thumbs if t.get("url") and not t["url"].split("?")[0].endswith(".webp")]
    pool = jpgs or [t for t in thumbs if t.get("url")]
    if pool:
        pool.sort(key=lambda t: (t.get("preference") or 0, t.get("width") or 0))
        # Preferimos un tamaño mediano para la vista previa
        mids = [t for t in pool if (t.get("width") or 0) and t["width"] <= 720]
        return (mids[-1] if mids else pool[-1])["url"]
    return info.get("thumbnail")
