"""Página «Herramientas»: utilidades de FFmpeg definidas de forma declarativa."""
import os
import shlex
import shutil
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from .tasks import FFmpegTask
from .utils import (
    AUDIO_FILTER, IMAGE_FILTER, MEDIA_FILTER, SUB_FILTER, VIDEO_FILTER, derive_output, ext_of, ffprobe_json,
    is_audio_file, media_duration, parse_time, ts, unique_path,
)
from .widgets import FileList, PathPicker, button, card, combo, field, label, row


# ---------------------------------------------------------------------------
#  Definición de campos
# ---------------------------------------------------------------------------
class F:
    def __init__(self, key, kind, caption, default=None, options=None, hint=None, filt=MEDIA_FILTER,
                 minimum=0, maximum=100000, step=1, decimals=2, suffix=""):
        self.key, self.kind, self.caption, self.default = key, kind, caption, default
        self.options, self.hint, self.filt = options, hint, filt
        self.minimum, self.maximum, self.step, self.decimals, self.suffix = minimum, maximum, step, decimals, suffix


class Tool:
    def __init__(self, name, icon, desc, fields, build, out_suffix="", out_ext=None, out_kind="file",
                 input_key="input"):
        self.name, self.icon, self.desc, self.fields = name, icon, desc, fields
        self.build, self.out_suffix, self.out_ext = build, out_suffix, out_ext
        self.out_kind, self.input_key = out_kind, input_key


def need(v, key, msg):
    if not v.get(key):
        raise ValueError(msg)
    return v[key]


def need_file(v, key="input"):
    p = v.get(key)
    if not p or not os.path.isfile(p):
        raise ValueError("Elige un archivo de entrada válido.")
    return p


# ---------------------------------------------------------------------------
#  Constructores de comandos (devuelven dict para FFmpegTask)
# ---------------------------------------------------------------------------
def b_trim(v, out):
    src = need_file(v)
    start = parse_time(v["start"]) or 0
    end = parse_time(v["end"])
    if end is not None and end <= start:
        raise ValueError("El final debe ser posterior al inicio.")
    a = ["-ss", ts(start), "-i", src]
    if end is not None:
        a += ["-t", ts(end - start)]
    if v["mode"] == "copy":
        a += ["-map", "0", "-c", "copy", "-avoid_negative_ts", "make_zero"]
    else:
        a += ["-map", "0:v?", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac",
              "-b:a", "192k"] if not is_audio_file(src) else ["-map", "0:a"]
    a += ["-map_metadata", "0", out]
    dur = (end - start) if end is not None else None
    return {"commands": [a], "duration": dur, "probe": src,
            "on_probe": (lambda d: max(0.1, d - start)) if end is None else None}


def b_concat(v, out):
    files = v["files"]
    if len(files) < 2:
        raise ValueError("Añade al menos dos archivos para unir.")
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    for f in files:
        tmp.write("file '" + f.replace("\\", "/").replace("'", "'\\''") + "'\n")
    tmp.close()
    a = ["-f", "concat", "-safe", "0", "-i", tmp.name]
    if v["mode"] == "copy":
        a += ["-c", "copy"]
    else:
        if is_audio_file(out):
            a += ["-vn"]
        else:
            a += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
    a += [out]
    total = 0.0
    for f in files:
        total += media_duration(f) or 0
    return {"commands": [a], "duration": total or None, "cleanup": [tmp.name]}


def b_compress(v, out):
    src = need_file(v)
    dur = media_duration(src)
    if not dur:
        raise ValueError("No se pudo leer la duración del archivo.")
    target_mb = float(v["size"])
    abr = int(v["abitrate"])
    total_kbit = target_mb * 8192 * 0.97
    vbr = int(total_kbit / dur - abr)
    if vbr < 50:
        raise ValueError(f"El tamaño objetivo es demasiado pequeño para {dur / 60:.1f} min de video.")
    codec = v["codec"]
    workdir = tempfile.gettempdir()
    logname = f"dvdy2pass_{os.getpid()}_{id(v)}"
    logbase = logname
    scale = ["-vf", f"scale=-2:{v['res']}"] if v["res"] else []
    common = ["-i", src, "-c:v", codec, "-b:v", f"{vbr}k", "-preset", v["preset"], *scale]
    if codec == "libx265":
        p1 = common + ["-x265-params", f"pass=1:stats={logbase}.log", "-an", "-f", "null", "NUL"]
        p2 = common + ["-x265-params", f"pass=2:stats={logbase}.log", "-tag:v", "hvc1",
                       "-c:a", "aac", "-b:a", f"{abr}k", "-movflags", "+faststart", out]
    else:
        p1 = common + ["-pass", "1", "-passlogfile", logbase, "-an", "-f", "null", "NUL"]
        p2 = common + ["-pass", "2", "-passlogfile", logbase, "-pix_fmt", "yuv420p", "-c:a", "aac",
                       "-b:a", f"{abr}k", "-movflags", "+faststart", out]
    cleanup = [os.path.join(workdir, logname + s) for s in ("-0.log", "-0.log.mbtree", ".log", ".log.cutree",
                                                             ".log.temp", ".log.cutree.temp")]
    return {"commands": [p1, p2], "duration": dur, "cleanup": cleanup, "cwd": workdir}


AUDIO_COPY_EXT = {"aac": "m4a", "mp3": "mp3", "opus": "opus", "vorbis": "ogg", "flac": "flac", "alac": "m4a",
                  "pcm_s16le": "wav", "pcm_s24le": "wav", "ac3": "ac3", "eac3": "eac3"}


def audio_codec_of(src):
    try:
        for s in ffprobe_json(src).get("streams", []):
            if s.get("codec_type") == "audio":
                return s.get("codec_name")
    except Exception:
        pass
    return None


def ext_extract_audio(v):
    src = v.get("input")
    if not src or not os.path.isfile(src):
        return "m4a"
    if v.get("format") and v["format"] != "copy":
        return v["format"]
    return AUDIO_COPY_EXT.get(audio_codec_of(src) or "", "mka")


def b_extract_audio(v, out):
    src = need_file(v)
    fmt = v["format"]
    a = ["-i", src, "-vn", "-map", "0:a:0"]
    if fmt == "copy":
        a += ["-c:a", "copy"]
    else:
        codec = {"mp3": "libmp3lame", "m4a": "aac", "flac": "flac", "wav": "pcm_s16le", "opus": "libopus",
                 "ogg": "libvorbis"}[fmt]
        a += ["-c:a", codec]
        if fmt in ("mp3", "m4a", "opus", "ogg"):
            a += ["-b:a", v["bitrate"]]
    a += ["-map_metadata", "0", out]
    return {"commands": [a], "probe": src}


def b_mute(v, out):
    src = need_file(v)
    return {"commands": [["-i", src, "-map", "0", "-map", "-0:a", "-c", "copy", out]], "probe": src}


def b_replace_audio(v, out):
    vid = need_file(v)
    aud = need_file(v, "audio")
    if v["mode"] == "replace":
        a = ["-i", vid, "-i", aud, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    else:
        vol = float(v["music_vol"]) / 100
        a = ["-i", vid, "-i", aud, "-filter_complex",
             f"[1:a]volume={vol:.2f}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
             "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    if v["shortest"]:
        a += ["-shortest"]
    return {"commands": [a + [out]], "probe": vid}


def b_gif(v, out):
    src = need_file(v)
    start = parse_time(v["start"]) or 0
    length = parse_time(v["length"]) or 5
    fps, width = int(v["fps"]), int(v["width"])
    flt = (f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors={v['colors']}"
           f":stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3")
    a = ["-ss", ts(start), "-t", ts(length), "-i", src, "-vf", flt, "-loop", "0" if v["loop"] else "-1", out]
    return {"commands": [a], "duration": length}


def b_normalize(v, out):
    src = need_file(v)
    lufs = v["target"]
    a = ["-i", src, "-map", "0", "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-ar", "48000"]
    if is_audio_file(src):
        ext = ext_of(out)
        codec = {"mp3": ["-c:a", "libmp3lame", "-b:a", "320k"], "m4a": ["-c:a", "aac", "-b:a", "256k"],
                 "flac": ["-c:a", "flac"], "wav": ["-c:a", "pcm_s16le"], "opus": ["-c:a", "libopus", "-b:a", "192k"],
                 "ogg": ["-c:a", "libvorbis", "-q:a", "7"]}.get(ext, ["-c:a", "aac", "-b:a", "256k"])
        a += ["-vn"] + codec
    else:
        a += ["-c:v", "copy", "-c:a", "aac", "-b:a", "256k"]
    return {"commands": [a + [out]], "probe": src}


def b_volume(v, out):
    src = need_file(v)
    a = ["-i", src, "-map", "0", "-af", f"volume={float(v['db']):g}dB"]
    if not is_audio_file(src):
        a += ["-c:v", "copy", "-c:a", "aac", "-b:a", "256k"]
    elif ext_of(out) == "mp3":
        a += ["-c:a", "libmp3lame", "-b:a", "320k"]
    return {"commands": [a + [out]], "probe": src}


def atempo_chain(f):
    parts = []
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5")
        f /= 0.5
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def b_speed(v, out):
    src = need_file(v)
    f = float(v["factor"])
    if f <= 0:
        raise ValueError("El factor debe ser mayor que 0.")
    if is_audio_file(src):
        a = ["-i", src, "-filter:a", atempo_chain(f), out]
    else:
        a = ["-i", src, "-filter_complex", f"[0:v]setpts=PTS/{f}[v];[0:a]{atempo_chain(f)}[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-c:a", "aac", out]
        if v["no_audio"]:
            a = ["-i", src, "-filter:v", f"setpts=PTS/{f}", "-an", "-c:v", "libx264", "-crf", "20", "-preset", "fast", out]
    return {"commands": [a], "probe": src, "on_probe": lambda d: d / f}


def b_rotate(v, out):
    src = need_file(v)
    vf = {"90": "transpose=1", "270": "transpose=2", "180": "transpose=1,transpose=1",
          "hflip": "hflip", "vflip": "vflip"}[v["op"]]
    a = ["-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "copy", out]
    return {"commands": [a], "probe": src}


def b_crop_scale(v, out):
    src = need_file(v)
    flt = []
    if v["crop"]:
        flt.append({"16:9": "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)'",
                    "9:16": "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'",
                    "1:1": "crop='min(iw,ih)':'min(iw,ih)'",
                    "4:3": "crop='min(iw,ih*4/3)':'min(ih,iw*3/4)'"}[v["crop"]])
    if v["height"]:
        flt.append(f"scale=-2:{v['height']}")
    if not flt:
        raise ValueError("Elige una relación de aspecto o una altura.")
    a = ["-i", src, "-vf", ",".join(flt), "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-c:a", "copy", out]
    return {"commands": [a], "probe": src}


def b_frames(v, out_dir):
    src = need_file(v)
    if not out_dir:
        raise ValueError("Elige una carpeta de salida.")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    ext = v["img"]
    mode = v["mode"]
    if mode == "single":
        t = parse_time(v["time"]) or 0
        out = unique_path(os.path.join(out_dir, f"{base}_{int(t)}s.{ext}"))
        a = ["-ss", ts(t), "-i", src, "-frames:v", "1", "-q:v", "2", out]
        return {"commands": [a], "output": out, "duration": None}
    if mode == "every":
        n = float(v["every"] or 10)
        out = os.path.join(out_dir, f"{base}_%04d.{ext}")
        a = ["-i", src, "-vf", f"fps=1/{n}", "-q:v", "2", out]
        return {"commands": [a], "output": out_dir, "probe": src}
    cols, rows_ = 4, 4
    out = unique_path(os.path.join(out_dir, f"{base}_mosaico.{ext}"))
    dur = media_duration(src) or 60
    interval = max(0.5, dur / (cols * rows_))
    a = ["-i", src, "-vf", f"fps=1/{interval:.3f},scale=480:-1,tile={cols}x{rows_}:padding=6:margin=6",
         "-frames:v", "1", "-q:v", "2", out]
    return {"commands": [a], "output": out, "duration": dur}


def b_subs(v, out):
    src = need_file(v)
    sub = need_file(v, "subs")
    if v["mode"] == "soft":
        sub_codec = "mov_text" if ext_of(out) in ("mp4", "mov", "m4v") else ("webvtt" if ext_of(out) == "webm" else "copy")
        if sub_codec == "copy" and ext_of(sub) != ext_of(out):
            sub_codec = "srt" if ext_of(sub) in ("srt", "vtt") else "ass"
        try:
            n = sum(1 for s in ffprobe_json(src)["streams"] if s.get("codec_type") == "subtitle")
        except Exception:
            n = 0
        a = ["-i", src, "-i", sub, "-map", "0", "-map", "1:0", "-c", "copy", "-c:s", sub_codec,
             f"-metadata:s:s:{n}", f"language={v['lang'] or 'spa'}", f"-disposition:s:{n}", "default", out]
        return {"commands": [a], "probe": src}
    tmpdir = tempfile.mkdtemp(prefix="dvdy_subs_")
    local = "sub." + ext_of(sub)
    shutil.copy(sub, os.path.join(tmpdir, local))
    style = f":force_style='Fontsize={v['size']}'" if v["size"] else ""
    a = ["-i", src, "-vf", f"subtitles={local}{style}", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
         "-c:a", "copy", out]
    return {"commands": [a], "probe": src, "cwd": tmpdir, "cleanup": [os.path.join(tmpdir, local)]}


META_KEYS = [("title", "Título"), ("artist", "Artista"), ("album", "Álbum"), ("album_artist", "Artista del álbum"),
             ("date", "Año"), ("genre", "Género"), ("track", "Nº de pista"), ("comment", "Comentario")]


def b_metadata(v, out):
    src = need_file(v)
    cover = v.get("cover")
    if cover and not os.path.isfile(cover):
        raise ValueError("La carátula indicada no existe.")
    a = ["-i", src]
    if cover:
        a += ["-i", cover]
    audio = is_audio_file(src)
    if audio and cover:
        a += ["-map", "0:a"]
    else:
        a += ["-map", "0"]
    if cover:
        a += ["-map", "1:0"]
    a += ["-c", "copy"]
    if cover:
        nvid = 0
        if not audio:
            try:
                nvid = sum(1 for s in ffprobe_json(src)["streams"] if s.get("codec_type") == "video")
            except Exception:
                nvid = 1
        if ext_of(cover) not in ("jpg", "jpeg", "png"):
            a += [f"-c:v:{nvid}", "mjpeg"]
        a += [f"-disposition:v:{nvid}", "attached_pic", f"-metadata:s:v:{nvid}", "title=Album cover",
              f"-metadata:s:v:{nvid}", "comment=Cover (front)"]
    if v["clear"]:
        a += ["-map_metadata", "-1"]
    else:
        a += ["-map_metadata", "0"]
    for k, _ in META_KEYS:
        if v.get(k):
            a += ["-metadata", f"{k}={v[k]}"]
    if ext_of(out) == "mp3":
        a += ["-id3v2_version", "3"]
    return {"commands": [a + [out]], "probe": src}


def b_still(v, out):
    img = need_file(v, "image")
    aud = need_file(v, "audio")
    h = v["height"]
    a = ["-loop", "1", "-framerate", "2", "-i", img, "-i", aud, "-c:v", "libx264", "-tune", "stillimage",
         "-vf", f"scale=-2:{h},format=yuv420p",
         "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", out]
    return {"commands": [a], "probe": aud}


def b_watermark(v, out):
    src = need_file(v)
    logo = need_file(v, "logo")
    pos = {"tl": "20:20", "tr": "W-w-20:20", "bl": "20:H-h-20", "br": "W-w-20:H-h-20",
           "c": "(W-w)/2:(H-h)/2"}[v["pos"]]
    op = float(v["opacity"]) / 100
    scale = float(v["scale"]) / 100
    vh = 1080
    try:
        vh = next(int(s["height"]) for s in ffprobe_json(src)["streams"] if s.get("codec_type") == "video")
    except Exception:
        pass
    lh = max(2, int(vh * scale) // 2 * 2)
    fc = (f"[1:v]scale=-1:{lh},format=rgba,colorchannelmixer=aa={op:.2f}[wm];"
          f"[0:v][wm]overlay={pos}:format=auto,format=yuv420p")
    a = ["-i", src, "-i", logo, "-filter_complex", fc, "-c:v", "libx264", "-crf", "19", "-preset", "medium",
         "-c:a", "copy", out]
    return {"commands": [a], "probe": src}


def b_fade(v, out):
    src = need_file(v)
    dur = media_duration(src)
    if not dur:
        raise ValueError("No se pudo leer la duración del archivo.")
    fi, fo = float(v["fin"]), float(v["fout"])
    af, vf = [], []
    if fi:
        af.append(f"afade=t=in:st=0:d={fi}")
        vf.append(f"fade=t=in:st=0:d={fi}")
    if fo:
        af.append(f"afade=t=out:st={max(0, dur - fo):.3f}:d={fo}")
        vf.append(f"fade=t=out:st={max(0, dur - fo):.3f}:d={fo}")
    if not af:
        raise ValueError("Indica una duración de fundido.")
    a = ["-i", src, "-af", ",".join(af)]
    if not is_audio_file(src):
        a += ["-vf", ",".join(vf), "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"]
    elif ext_of(out) == "mp3":
        a += ["-c:a", "libmp3lame", "-b:a", "320k"]
    return {"commands": [a + [out]], "duration": dur}


def b_segment(v, out_dir):
    src = need_file(v)
    if not out_dir:
        raise ValueError("Elige una carpeta de salida.")
    os.makedirs(out_dir, exist_ok=True)
    seg = parse_time(v["length"]) or 600
    base, ext = os.path.splitext(os.path.basename(src))
    out = os.path.join(out_dir, f"{base}_parte%03d{ext}")
    a = ["-i", src, "-map", "0", "-c", "copy", "-f", "segment", "-segment_time", str(seg),
         "-reset_timestamps", "1", out]
    return {"commands": [a], "probe": src, "output": out_dir}


def b_silence(v, out):
    src = need_file(v)
    th = v["threshold"]
    d = v["min_len"]
    flt = (f"silenceremove=start_periods=1:start_duration=0:start_threshold={th}dB:"
           f"stop_periods=-1:stop_duration={d}:stop_threshold={th}dB")
    a = ["-i", src, "-af", flt]
    if not is_audio_file(src):
        a = ["-i", src, "-vn", "-af", flt]
    return {"commands": [a + [out]], "probe": src}


def b_reverse(v, out):
    src = need_file(v)
    if is_audio_file(src):
        a = ["-i", src, "-af", "areverse", out]
    else:
        a = ["-i", src, "-vf", "reverse", "-af", "areverse", "-c:v", "libx264", "-crf", "20", "-preset", "fast", out]
    return {"commands": [a], "probe": src}


def b_custom(v, out):
    src = v.get("input") or ""
    args = v["args"].strip()
    if not args:
        raise ValueError("Escribe los argumentos de FFmpeg.")
    parts = shlex.split(args, posix=True)
    parts = [p.replace("{entrada}", src).replace("{salida}", out) for p in parts]
    if "{salida}" not in args and out:
        parts.append(out)
    return {"commands": [parts], "probe": src if os.path.isfile(src) else None}


TOOLS = [
    Tool("Recortar fragmento", "", "Corta una parte de un video o audio indicando inicio y fin.",
         [F("input", "file", "Archivo"), F("start", "text", "Inicio", "0:00"),
          F("end", "text", "Fin (vacío = hasta el final)", ""),
          F("mode", "choice", "Modo", "copy", [("Rápido, sin recodificar (corta en fotogramas clave)", "copy"),
                                                ("Preciso, recodificando", "encode")])],
         b_trim, "_recorte"),
    Tool("Unir archivos", "", "Concatena varios videos o audios en uno solo, en el orden de la lista.",
         [F("files", "files", "Archivos (arrastra para reordenar)"),
          F("mode", "choice", "Modo", "copy", [("Sin recodificar (mismo formato y códec)", "copy"),
                                                ("Recodificar (formatos distintos)", "encode")])],
         b_concat, "_unido", input_key="files"),
    Tool("Comprimir a un tamaño", "", "Reduce un video para que pese aproximadamente los MB indicados "
                                           "(codificación en dos pasadas). Ideal para WhatsApp, Discord o correo.",
         [F("input", "file", "Video", filt=VIDEO_FILTER), F("size", "float", "Tamaño objetivo", 25, minimum=1, suffix=" MB"),
          F("codec", "choice", "Códec", "libx264", [("H.264 (compatible)", "libx264"), ("H.265 (más eficiente)", "libx265")]),
          F("res", "choice", "Resolución", "", [("Original", ""), ("1080p", "1080"), ("720p", "720"), ("480p", "480"), ("360p", "360")]),
          F("abitrate", "choice", "Audio", "128", [("192 kbps", "192"), ("128 kbps", "128"), ("96 kbps", "96"), ("64 kbps", "64")]),
          F("preset", "choice", "Velocidad", "medium", [("Rápida", "fast"), ("Normal", "medium"), ("Lenta (mejor)", "slow")])],
         b_compress, "_comprimido", "mp4"),
    Tool("Extraer audio", "", "Saca la pista de audio de un video. «Original» la copia sin pérdida de calidad.",
         [F("input", "file", "Video"),
          F("format", "choice", "Formato", "copy", [("Original (sin pérdida, instantáneo)", "copy"), ("MP3", "mp3"),
                                                    ("M4A (AAC)", "m4a"), ("FLAC", "flac"), ("WAV", "wav"),
                                                    ("Opus", "opus"), ("OGG", "ogg")]),
          F("bitrate", "choice", "Tasa de bits (si se convierte)", "320k", [("320 kbps", "320k"), ("256 kbps", "256k"),
                                                                            ("192 kbps", "192k"), ("128 kbps", "128k")])],
         b_extract_audio, "_audio", ext_extract_audio),
    Tool("Quitar audio", "", "Elimina todas las pistas de audio de un video sin recodificar.",
         [F("input", "file", "Video", filt=VIDEO_FILTER)], b_mute, "_sin_audio"),
    Tool("Reemplazar o mezclar audio", "", "Pone otra pista de audio a un video, o la mezcla con el sonido original "
                                                 "(música de fondo).",
         [F("input", "file", "Video", filt=VIDEO_FILTER), F("audio", "file", "Audio nuevo", filt=AUDIO_FILTER),
          F("mode", "choice", "Modo", "replace", [("Reemplazar el audio", "replace"), ("Mezclar con el original", "mix")]),
          F("music_vol", "int", "Volumen del audio nuevo al mezclar", 35, minimum=1, maximum=200, suffix=" %"),
          F("shortest", "bool", "Cortar al más corto de los dos", True)],
         b_replace_audio, "_audio"),
    Tool("Crear GIF", "", "Convierte un fragmento de video en un GIF animado de alta calidad (paleta optimizada).",
         [F("input", "file", "Video", filt=VIDEO_FILTER), F("start", "text", "Inicio", "0:00"),
          F("length", "text", "Duración (segundos)", "5"), F("fps", "int", "FPS", 15, minimum=1, maximum=50),
          F("width", "int", "Ancho", 480, minimum=50, maximum=3840, suffix=" px"),
          F("colors", "int", "Colores", 256, minimum=8, maximum=256), F("loop", "bool", "Repetir en bucle", True)],
         b_gif, "_gif", "gif"),
    Tool("Normalizar volumen", "", "Iguala el volumen percibido (EBU R128) para que todas las canciones suenen parejas.",
         [F("input", "file", "Archivo"),
          F("target", "choice", "Objetivo", "-14", [("-14 LUFS (Spotify / YouTube)", "-14"), ("-16 LUFS (Apple Music, podcasts)", "-16"),
                                                    ("-23 LUFS (TV / EBU)", "-23"), ("-9 LUFS (muy alto)", "-9")])],
         b_normalize, "_normalizado"),
    Tool("Ajustar volumen", "", "Sube o baja el volumen en decibelios.",
         [F("input", "file", "Archivo"), F("db", "float", "Cambio de volumen", 3, minimum=-40, maximum=40, suffix=" dB")],
         b_volume, "_volumen"),
    Tool("Cambiar velocidad", "", "Acelera o ralentiza video y audio manteniendo el tono de la voz.",
         [F("input", "file", "Archivo"), F("factor", "float", "Factor de velocidad", 1.5, minimum=0.1, maximum=10, step=0.25,
                                            suffix=" ×"),
          F("no_audio", "bool", "Quitar el audio (para videos sin sonido)", False)],
         b_speed, "_velocidad"),
    Tool("Rotar o voltear", "", "Gira el video 90°/180°/270° o lo voltea como un espejo.",
         [F("input", "file", "Video", filt=VIDEO_FILTER),
          F("op", "choice", "Operación", "90", [("Girar 90° a la derecha", "90"), ("Girar 90° a la izquierda", "270"),
                                                ("Girar 180°", "180"), ("Voltear horizontal (espejo)", "hflip"),
                                                ("Voltear vertical", "vflip")])],
         b_rotate, "_rotado"),
    Tool("Recortar encuadre / redimensionar", "", "Cambia la relación de aspecto (p. ej. horizontal → vertical 9:16 "
                                                        "para Reels/TikTok) o la resolución.",
         [F("input", "file", "Video", filt=VIDEO_FILTER),
          F("crop", "choice", "Recortar a", "", [("No recortar", ""), ("16:9 (horizontal)", "16:9"), ("9:16 (vertical)", "9:16"),
                                                ("1:1 (cuadrado)", "1:1"), ("4:3", "4:3")]),
          F("height", "choice", "Altura final", "", [("Sin cambiar", ""), ("2160", "2160"), ("1920", "1920"), ("1080", "1080"),
                                                     ("720", "720"), ("480", "480")])],
         b_crop_scale, "_encuadre"),
    Tool("Capturas de fotogramas", "", "Guarda una imagen de un instante, una cada N segundos, o un mosaico de miniaturas.",
         [F("input", "file", "Video", filt=VIDEO_FILTER),
          F("mode", "choice", "Modo", "single", [("Un solo fotograma", "single"), ("Uno cada N segundos", "every"),
                                                 ("Mosaico 4×4 de todo el video", "mosaic")]),
          F("time", "text", "Instante (modo un fotograma)", "0:05"),
          F("every", "float", "Cada (segundos)", 10, minimum=0.1, maximum=3600),
          F("img", "choice", "Formato", "jpg", [("JPG", "jpg"), ("PNG", "png"), ("WebP", "webp")])],
         b_frames, out_kind="dir"),
    Tool("Subtítulos", "", "Añade un archivo de subtítulos como pista seleccionable o los «quema» en la imagen.",
         [F("input", "file", "Video", filt=VIDEO_FILTER), F("subs", "file", "Subtítulos", filt=SUB_FILTER),
          F("mode", "choice", "Modo", "soft", [("Pista seleccionable (sin recodificar)", "soft"),
                                               ("Quemar en la imagen (siempre visibles)", "hard")]),
          F("lang", "text", "Idioma (código ISO, pista seleccionable)", "spa"),
          F("size", "int", "Tamaño de letra (quemados, 0 = automático)", 0, minimum=0, maximum=100)],
         b_subs, "_subs"),
    Tool("Metadatos y carátula", "", "Edita título, artista, álbum, año, género y añade o cambia la carátula "
                                          "de canciones y videos.",
         [F("input", "file", "Archivo")] + [F(k, "text", t, "") for k, t in META_KEYS] +
         [F("cover", "file", "Carátula (opcional)", filt=IMAGE_FILTER),
          F("clear", "bool", "Borrar primero todos los metadatos existentes", False)],
         b_metadata, "_tags"),
    Tool("Imagen + audio → video", "", "Crea un video con una imagen fija y una canción (para subir música a YouTube).",
         [F("image", "file", "Imagen", filt=IMAGE_FILTER), F("audio", "file", "Audio", filt=AUDIO_FILTER),
          F("height", "choice", "Resolución", "1080", [("1080p", "1080"), ("720p", "720"), ("2160p", "2160")])],
         b_still, "_video", "mp4", input_key="audio"),
    Tool("Marca de agua", "", "Superpone un logo o imagen sobre el video.",
         [F("input", "file", "Video", filt=VIDEO_FILTER), F("logo", "file", "Logo (PNG con transparencia)", filt=IMAGE_FILTER),
          F("pos", "choice", "Posición", "br", [("Abajo a la derecha", "br"), ("Abajo a la izquierda", "bl"),
                                                ("Arriba a la derecha", "tr"), ("Arriba a la izquierda", "tl"), ("Centro", "c")]),
          F("scale", "int", "Tamaño (alto respecto al video)", 12, minimum=1, maximum=100, suffix=" %"),
          F("opacity", "int", "Opacidad", 80, minimum=1, maximum=100, suffix=" %")],
         b_watermark, "_marca"),
    Tool("Fundido de entrada y salida", "", "Aplica fade-in y fade-out al audio (y a la imagen si es video).",
         [F("input", "file", "Archivo"), F("fin", "float", "Fundido de entrada", 2, minimum=0, maximum=60, suffix=" s"),
          F("fout", "float", "Fundido de salida", 3, minimum=0, maximum=60, suffix=" s")],
         b_fade, "_fade"),
    Tool("Dividir en partes", "", "Corta un archivo largo en trozos de igual duración, sin recodificar.",
         [F("input", "file", "Archivo"), F("length", "text", "Duración de cada parte", "10:00")],
         b_segment, out_kind="dir"),
    Tool("Eliminar silencios", "", "Quita los silencios de un audio (útil para clases, podcasts o notas de voz).",
         [F("input", "file", "Archivo"), F("threshold", "int", "Umbral de silencio", -45, minimum=-90, maximum=-10, suffix=" dB"),
          F("min_len", "float", "Silencio mínimo a quitar", 0.7, minimum=0.1, maximum=10, suffix=" s")],
         b_silence, "_sin_silencios", lambda v: "m4a" if v.get("input") and not is_audio_file(v["input"]) else None),
    Tool("Invertir (reproducir al revés)", "", "Invierte el video y/o el audio. Usa archivos cortos: consume mucha memoria.",
         [F("input", "file", "Archivo")], b_reverse, "_invertido"),
    Tool("Comando personalizado", "", "Escribe tus propios argumentos de FFmpeg. Usa {entrada} y {salida} como marcadores.",
         [F("input", "file", "Archivo de entrada (opcional)"),
          F("args", "text", "Argumentos", '-i "{entrada}" -vf "hue=s=0" "{salida}"',
            hint="Ejemplo: -i \"{entrada}\" -vf \"hue=s=0\" \"{salida}\"  (blanco y negro)")],
         b_custom, "_custom"),
]


# ---------------------------------------------------------------------------
#  Interfaz
# ---------------------------------------------------------------------------
class ToolForm(QWidget):
    def __init__(self, tool, page):
        super().__init__()
        self.tool = tool
        self.page = page
        self.w = {}
        self._out_edited = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 14, 0)
        lay.setSpacing(12)
        c, cl = card(tool.name, tool.desc)
        for f in tool.fields:
            widget = self._make(f)
            self.w[f.key] = widget
            if f.kind == "bool":
                cl.addWidget(widget)
            else:
                cl.addWidget(field(f.caption, widget, f.hint))
        lay.addWidget(c)
        c2, cl2 = card("Salida")
        if tool.out_kind == "dir":
            self.out = PathPicker("dir", "")
        else:
            self.out = PathPicker("save", "", MEDIA_FILTER)
            self.out.edit.textEdited.connect(lambda *_: setattr(self, "_out_edited", True))
        cl2.addWidget(self.out)
        lay.addWidget(c2)
        lay.addWidget(row(None, button("Ejecutar", self.run, primary=True)))
        lay.addStretch(1)
        inp = self.w.get(tool.input_key)
        if isinstance(inp, PathPicker):
            inp.changed.connect(self._suggest_output)
        elif isinstance(inp, FileList):
            inp.changed.connect(self._suggest_output)
        for k, wd in self.w.items():
            if hasattr(wd, "currentIndexChanged") and k in ("format",):
                wd.currentIndexChanged.connect(lambda *_: self._suggest_output(force=True))

    def _make(self, f):
        if f.kind == "file":
            return PathPicker("open", "", f.filt)
        if f.kind == "files":
            fl = FileList(f.filt, reorder=True)
            fl.setMinimumHeight(180)
            return fl
        if f.kind == "text":
            e = QLineEdit("" if f.default is None else str(f.default))
            return e
        if f.kind == "int":
            s = QSpinBox()
            s.setRange(int(f.minimum), int(f.maximum))
            s.setValue(int(f.default or 0))
            s.setSuffix(f.suffix)
            return s
        if f.kind == "float":
            s = QDoubleSpinBox()
            s.setRange(f.minimum, f.maximum)
            s.setDecimals(f.decimals)
            s.setSingleStep(f.step)
            s.setValue(float(f.default or 0))
            s.setSuffix(f.suffix)
            return s
        if f.kind == "choice":
            return combo(f.options, f.default)
        if f.kind == "bool":
            cb = QCheckBox(f.caption)
            cb.setChecked(bool(f.default))
            return cb
        raise ValueError(f.kind)

    def values(self):
        v = {}
        for f in self.tool.fields:
            wd = self.w[f.key]
            if f.kind == "file":
                v[f.key] = wd.path()
            elif f.kind == "files":
                v[f.key] = wd.files()
            elif f.kind == "text":
                v[f.key] = wd.text().strip()
            elif f.kind in ("int", "float"):
                v[f.key] = wd.value()
            elif f.kind == "choice":
                v[f.key] = wd.currentData()
            elif f.kind == "bool":
                v[f.key] = wd.isChecked()
        return v

    def _primary_input(self):
        v = self.values()
        x = v.get(self.tool.input_key)
        if isinstance(x, list):
            return x[0] if x else ""
        return x or ""

    def _suggest_output(self, *_, force=False):
        src = self._primary_input()
        if not src or not os.path.isfile(src):
            return
        if self.tool.out_kind == "dir":
            if not self.out.path() or force:
                self.out.set_path(os.path.dirname(src))
            return
        if self._out_edited and not force:
            return
        ext = self.tool.out_ext
        if callable(ext):
            ext = ext(self.values())
        self.out.set_path(derive_output(src, self.tool.out_suffix or "_editado", ext))

    def run(self):
        out = self.out.path()
        if not out:
            self._suggest_output(force=True)
            out = self.out.path()
        if not out:
            QMessageBox.warning(self, "Salida", "Indica dónde guardar el resultado.")
            return
        v = self.values()
        src = self._primary_input()
        if src and self.tool.out_kind == "file" and os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(src)):
            QMessageBox.warning(self, "Salida", "La salida no puede ser el mismo archivo que la entrada.")
            return
        try:
            job = self.tool.build(v, out)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, self.tool.name, str(e))
            return
        name = os.path.basename(src) if src else self.tool.name
        t = FFmpegTask(f"{self.tool.name}: {name}", job["commands"], output=job.get("output", out),
                       duration=job.get("duration"), probe=job.get("probe"), cwd=job.get("cwd"),
                       cleanup=job.get("cleanup", ()), label=self.tool.name)
        if job.get("on_probe"):
            t.on_probe = job["on_probe"]
        self.page.manager.add(t)
        self._out_edited = False
        if self.tool.out_kind == "file":
            self.out.set_path("")
            self._suggest_output(force=True)
        self.page.go_queue()


class ToolsPage(QWidget):
    def __init__(self, manager, go_queue):
        super().__init__()
        self.setObjectName("Page")
        self.manager = manager
        self.go_queue = go_queue
        from .widgets import Page
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        header = Page("Herramientas", "Utilidades de FFmpeg para editar video y audio sin programas extra.", scroll=False)
        header.body.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(header, 0)
        content = QHBoxLayout()
        content.setContentsMargins(20, 0, 28, 20)
        content.setSpacing(14)
        self.list = QListWidget()
        self.list.setObjectName("ToolList")
        self.list.setFixedWidth(260)
        from .theme import icon_font
        self.stack = QStackedWidget()
        from PySide6.QtWidgets import QScrollArea, QFrame
        for tool in TOOLS:
            it = QListWidgetItem(tool.name)
            it.setToolTip(tool.desc)
            self.list.addItem(it)
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            sa.setWidget(ToolForm(tool, self))
            self.stack.addWidget(sa)
        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.list.setCurrentRow(0)
        content.addWidget(self.list)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)
