"""Página «Convertir»: conversión por lotes con FFmpeg (video↔video, video→audio, audio↔audio, GIF)."""
import os
import shlex

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QGridLayout, QLineEdit, QMessageBox, QSlider, QSpinBox,
)

from .tasks import FFmpegTask
from .utils import AUDIO_EXTS, MEDIA_FILTER, derive_output, ffmpeg_encoders, parse_time, ts
from .widgets import FileList, Page, PathPicker, button, card, combo, field, label, row, set_combo

OUT_FORMATS = [
    ("MP4 (video)", "mp4"), ("MKV (video)", "mkv"), ("WebM (video)", "webm"), ("MOV (video)", "mov"),
    ("AVI (video)", "avi"), ("GIF animado", "gif"),
    ("MP3 (audio)", "mp3"), ("M4A / AAC (audio)", "m4a"), ("FLAC (audio sin pérdida)", "flac"),
    ("WAV (audio sin compresión)", "wav"), ("OGG Vorbis (audio)", "ogg"), ("Opus (audio)", "opus"),
    ("AAC crudo (audio)", "aac"),
]
VCODECS = [
    ("Automático según formato", "auto"), ("Copiar sin recodificar (instantáneo)", "copy"),
    ("H.264 (libx264)", "libx264"), ("H.265 / HEVC (libx265)", "libx265"), ("VP9 (libvpx-vp9)", "libvpx-vp9"),
    ("AV1 (SVT-AV1)", "libsvtav1"), ("AV1 (libaom)", "libaom-av1"),
    ("H.264 NVIDIA (h264_nvenc)", "h264_nvenc"), ("HEVC NVIDIA (hevc_nvenc)", "hevc_nvenc"),
    ("H.264 Intel (h264_qsv)", "h264_qsv"), ("HEVC Intel (hevc_qsv)", "hevc_qsv"),
    ("H.264 AMD (h264_amf)", "h264_amf"), ("HEVC AMD (hevc_amf)", "hevc_amf"),
    ("MPEG-4 Part 2 (mpeg4)", "mpeg4"), ("ProRes (prores_ks)", "prores_ks"),
]
ACODECS = [
    ("Automático según formato", "auto"), ("Copiar sin recodificar", "copy"), ("AAC", "aac"),
    ("MP3 (libmp3lame)", "libmp3lame"), ("Opus (libopus)", "libopus"), ("Vorbis (libvorbis)", "libvorbis"),
    ("FLAC", "flac"), ("ALAC", "alac"), ("PCM 16 bits (WAV)", "pcm_s16le"), ("PCM 24 bits", "pcm_s24le"),
    ("AC3 (Dolby Digital)", "ac3"),
]
PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
RESOLUTIONS = [("Original", ""), ("2160p (4K)", "2160"), ("1440p", "1440"), ("1080p", "1080"), ("720p", "720"),
               ("480p", "480"), ("360p", "360"), ("240p", "240")]
FPS = [("Original", ""), ("60", "60"), ("50", "50"), ("30", "30"), ("25", "25"), ("24", "24"), ("15", "15"), ("10", "10")]
BITRATES = [("320 kbps", "320k"), ("256 kbps", "256k"), ("192 kbps", "192k"), ("160 kbps", "160k"),
            ("128 kbps", "128k"), ("96 kbps", "96k"), ("64 kbps", "64k")]
SAMPLE_RATES = [("Original", ""), ("48000 Hz", "48000"), ("44100 Hz", "44100"), ("32000 Hz", "32000"),
                ("22050 Hz", "22050")]
CHANNELS = [("Original", ""), ("Estéreo", "2"), ("Mono", "1"), ("5.1", "6")]

QUICK_PRESETS = [
    ("Personalizado", None),
    ("Video → MP3 320 kbps", {"fmt": "mp3", "ab": "320k"}),
    ("Video → M4A AAC 256 kbps", {"fmt": "m4a", "ab": "256k"}),
    ("Audio → FLAC (sin pérdida)", {"fmt": "flac"}),
    ("Audio → WAV", {"fmt": "wav"}),
    ("Audio → Opus 128 kbps", {"fmt": "opus", "ab": "128k"}),
    ("Video → MP4 compatible (H.264 + AAC)", {"fmt": "mp4", "vc": "libx264", "crf": 21, "preset": "medium", "ac": "aac", "ab": "192k", "yuv": True}),
    ("Video → MP4 pequeño (H.265)", {"fmt": "mp4", "vc": "libx265", "crf": 26, "preset": "medium", "ac": "aac", "ab": "128k"}),
    ("Video → WebM (VP9 + Opus)", {"fmt": "webm", "vc": "libvpx-vp9", "crf": 32, "ac": "libopus", "ab": "128k"}),
    ("Video → 720p para compartir", {"fmt": "mp4", "vc": "libx264", "crf": 23, "res": "720", "ac": "aac", "ab": "128k", "yuv": True}),
    ("Cambiar contenedor a MKV (sin recodificar)", {"fmt": "mkv", "vc": "copy", "ac": "copy"}),
    ("Cambiar contenedor a MP4 (sin recodificar)", {"fmt": "mp4", "vc": "copy", "ac": "copy"}),
    ("Video → GIF (480 px, 12 fps)", {"fmt": "gif", "res": "480", "fps": "12"}),
]

AUTO_ACODEC = {"mp3": "libmp3lame", "m4a": "aac", "aac": "aac", "flac": "flac", "wav": "pcm_s16le",
               "ogg": "libvorbis", "opus": "libopus", "webm": "libopus", "mp4": "aac", "mov": "aac",
               "mkv": "aac", "avi": "libmp3lame"}
AUTO_VCODEC = {"mp4": "libx264", "mov": "libx264", "mkv": "libx264", "webm": "libvpx-vp9", "avi": "mpeg4"}
LOSSLESS_A = {"flac", "alac", "pcm_s16le", "pcm_s24le", "copy"}
SVT_PRESET = {"ultrafast": 12, "superfast": 11, "veryfast": 10, "faster": 9, "fast": 8, "medium": 6,
              "slow": 4, "slower": 3, "veryslow": 2}
NV_PRESET = {"ultrafast": "p1", "superfast": "p2", "veryfast": "p3", "faster": "p3", "fast": "p4",
             "medium": "p5", "slow": "p6", "slower": "p7", "veryslow": "p7"}


def video_quality_args(vc, crf, preset):
    a = ["-c:v", vc]
    if vc in ("libx264", "libx265"):
        a += ["-crf", str(crf), "-preset", preset]
        if vc == "libx265":
            a += ["-tag:v", "hvc1"]
    elif vc == "libvpx-vp9":
        a += ["-crf", str(crf), "-b:v", "0", "-row-mt", "1", "-deadline", "good",
              "-cpu-used", str(min(5, max(0, PRESETS.index(preset) // 2)) if preset in PRESETS else 2)]
    elif vc == "libsvtav1":
        a += ["-crf", str(crf), "-preset", str(SVT_PRESET.get(preset, 6))]
    elif vc == "libaom-av1":
        a += ["-crf", str(crf), "-b:v", "0", "-cpu-used", "6", "-row-mt", "1"]
    elif vc.endswith("_nvenc"):
        a += ["-rc", "vbr", "-cq", str(crf), "-preset", NV_PRESET.get(preset, "p5")]
    elif vc.endswith("_qsv"):
        a += ["-global_quality", str(crf)]
    elif vc.endswith("_amf"):
        a += ["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf)]
    elif vc == "mpeg4":
        a += ["-q:v", str(max(1, min(31, crf // 3)))]
    elif vc == "prores_ks":
        a += ["-profile:v", "3"]
    return a


class ConvertPage(Page):
    def __init__(self, manager, go_queue):
        super().__init__("Convertir", "Convierte archivos por lotes con FFmpeg: MP4 → MP3, cambia formato, códec, "
                                      "resolución, calidad, volumen y más.")
        self.manager = manager
        self.go_queue = go_queue

        c, lay = card("Archivos")
        self.files = FileList(MEDIA_FILTER)
        self.files.setMinimumHeight(170)
        self.files.changed.connect(self._preview)
        lay.addWidget(self.files)
        self.add(c)

        c, lay = card("Formato de salida")
        self.preset = combo(QUICK_PRESETS)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self.fmt = combo(OUT_FORMATS, "mp3")
        self.fmt.currentIndexChanged.connect(self._update_enabled)
        lay.addWidget(row(field("Ajuste rápido", self.preset), field("Formato", self.fmt)))
        self.add(c)

        # ---- Video ----
        self.video_card, lay = card("Video")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        enc = ffmpeg_encoders()
        self.vcodec = combo([(t, d) for t, d in VCODECS if d in ("auto", "copy") or not enc or d in enc], "auto")
        self.vcodec.currentIndexChanged.connect(self._update_enabled)
        self.crf = QSlider(Qt.Horizontal)
        self.crf.setRange(0, 51)
        self.crf.setValue(23)
        self.crf_lbl = label("", "Muted")
        self.crf.valueChanged.connect(lambda v: self.crf_lbl.setText(f"Calidad (CRF/CQ): {v}  —  menor = mejor calidad y más peso"))
        self.crf.valueChanged.connect(self._preview)
        self.crf_lbl.setText("Calidad (CRF/CQ): 23  —  menor = mejor calidad y más peso")
        self.vpreset = combo([(p, p) for p in PRESETS], "medium")
        self.res = combo(RESOLUTIONS, "")
        self.fps = combo(FPS, "")
        self.yuv420 = QCheckBox("Forzar yuv420p (máxima compatibilidad con reproductores)")
        g.addWidget(field("Códec de video", self.vcodec), 0, 0)
        g.addWidget(field("Velocidad de codificación", self.vpreset), 0, 1)
        g.addWidget(field("Resolución (alto)", self.res), 1, 0)
        g.addWidget(field("Cuadros por segundo", self.fps), 1, 1)
        lay.addLayout(g)
        lay.addWidget(self.crf_lbl)
        lay.addWidget(self.crf)
        lay.addWidget(self.yuv420)
        self.add(self.video_card)

        # ---- Audio ----
        self.audio_card, lay = card("Audio")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.acodec = combo([(t, d) for t, d in ACODECS if d in ("auto", "copy") or not enc or d in enc], "auto")
        self.acodec.currentIndexChanged.connect(self._update_enabled)
        self.abitrate = combo(BITRATES, "192k")
        self.arate = combo(SAMPLE_RATES, "")
        self.achannels = combo(CHANNELS, "")
        self.volume = QDoubleSpinBox()
        self.volume.setRange(-30, 30)
        self.volume.setSingleStep(1)
        self.volume.setSuffix(" dB")
        self.no_audio = QCheckBox("Quitar el audio")
        self.no_audio.toggled.connect(self._update_enabled)
        g.addWidget(field("Códec de audio", self.acodec), 0, 0)
        g.addWidget(field("Tasa de bits", self.abitrate), 0, 1)
        g.addWidget(field("Frecuencia de muestreo", self.arate), 1, 0)
        g.addWidget(field("Canales", self.achannels), 1, 1)
        g.addWidget(field("Ajustar volumen", self.volume), 2, 0)
        lay.addLayout(g)
        lay.addWidget(self.no_audio)
        self.add(self.audio_card)

        # ---- Recorte y extras ----
        c, lay = card("Recorte y opciones avanzadas")
        self.start = QLineEdit()
        self.start.setPlaceholderText("Inicio (opcional): 0:30")
        self.end = QLineEdit()
        self.end.setPlaceholderText("Fin (opcional): 1:45")
        lay.addWidget(row(field("Recortar desde", self.start), field("Hasta", self.end)))
        self.keep_meta = QCheckBox("Conservar metadatos del original")
        self.keep_meta.setChecked(True)
        lay.addWidget(self.keep_meta)
        self.extra = QLineEdit()
        self.extra.setPlaceholderText('Argumentos extra de FFmpeg, ej.:  -af "highpass=f=80"  -tune film')
        lay.addWidget(field("Argumentos adicionales (avanzado)", self.extra))
        self.same_folder = QCheckBox("Guardar junto al archivo original")
        self.same_folder.setChecked(True)
        self.out_dir = PathPicker("dir", "")
        self.same_folder.toggled.connect(lambda on: self.out_dir.setEnabled(not on))
        self.out_dir.setEnabled(False)
        self.suffix = QLineEdit("")
        self.suffix.setPlaceholderText("Sufijo del nombre (opcional), ej.: _convertido")
        lay.addWidget(self.same_folder)
        lay.addWidget(row(self.out_dir, self.suffix))
        self.add(c)
        self.adv_card = c

        for w in (self.vpreset, self.res, self.fps, self.abitrate, self.arate, self.achannels):
            w.currentIndexChanged.connect(self._preview)
        for w in (self.start, self.end, self.extra, self.suffix):
            w.textChanged.connect(self._preview)
        self.volume.valueChanged.connect(self._preview)
        self.yuv420.toggled.connect(self._preview)

        c, lay = card("Comando que se ejecutará")
        self.cmd_lbl = label("", "Hint", wrap=True)
        self.cmd_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.cmd_lbl)
        self.add(c)
        self.cmd_card = c
        self.simple = False
        self.add(row(None, button("Convertir", self.convert, primary=True)))
        self.body.addStretch(1)
        self._update_enabled()

    # ------------------------------------------------------------------
    def set_simple(self, simple):
        """Modo simple: solo archivos, ajuste rápido y formato; el resto usa valores automáticos."""
        self.simple = simple
        self.adv_card.setVisible(not simple)
        self.cmd_card.setVisible(not simple)
        if simple:
            # Sin recorte ni extras ocultos que el usuario no pueda ver
            self.start.clear()
            self.end.clear()
            self.extra.clear()
            self.same_folder.setChecked(True)
        self._update_enabled()

    def _apply_preset(self, i):
        p = self.preset.itemData(i)
        if not p:
            return
        set_combo(self.fmt, p["fmt"])
        set_combo(self.vcodec, p.get("vc", "auto"))
        set_combo(self.acodec, p.get("ac", "auto"))
        if "ab" in p:
            set_combo(self.abitrate, p["ab"])
        if "crf" in p:
            self.crf.setValue(p["crf"])
        set_combo(self.vpreset, p.get("preset", "medium"))
        set_combo(self.res, p.get("res", ""))
        set_combo(self.fps, p.get("fps", ""))
        self.yuv420.setChecked(p.get("yuv", False))
        self.no_audio.setChecked(False)
        self._update_enabled()

    def _update_enabled(self, *_):
        fmt = self.fmt.currentData()
        audio_only = fmt in AUDIO_EXTS
        gif = fmt == "gif"
        simple = getattr(self, "simple", False)
        self.video_card.setVisible(not audio_only and not simple)
        self.audio_card.setVisible(not gif and not simple)
        vc = self.vcodec.currentData()
        enc = vc != "copy" and not gif
        self.crf.setEnabled(enc)
        self.vpreset.setEnabled(enc)
        self.vcodec.setEnabled(not gif)
        self.yuv420.setEnabled(enc)
        ac = self.acodec.currentData()
        a_on = not self.no_audio.isChecked() or audio_only
        self.no_audio.setVisible(not audio_only)
        self.acodec.setEnabled(a_on)
        self.abitrate.setEnabled(a_on and ac != "copy" and (ac if ac != "auto" else AUTO_ACODEC.get(fmt, "aac")) not in LOSSLESS_A)
        self.arate.setEnabled(a_on and ac != "copy")
        self.achannels.setEnabled(a_on and ac != "copy")
        self.volume.setEnabled(a_on and ac != "copy")
        self._preview()

    def build_args(self, src, out):
        fmt = self.fmt.currentData()
        audio_only = fmt in AUDIO_EXTS
        start = parse_time(self.start.text())
        end = parse_time(self.end.text())
        if start is not None and end is not None and end <= start:
            raise ValueError("El tiempo final debe ser mayor que el inicial.")
        a = []
        if start:
            a += ["-ss", ts(start)]
        a += ["-i", src]
        if end is not None:
            a += ["-t", ts(end - (start or 0))]
        if self.keep_meta.isChecked():
            a += ["-map_metadata", "0"]
        if fmt == "gif":
            h = self.res.currentData() or "480"
            fps = self.fps.currentData() or "12"
            a += ["-vf", f"fps={fps},scale=-2:{h}:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
                         f"[s1][p]paletteuse=dither=bayer:bayer_scale=4", "-an", "-loop", "0"]
        else:
            if audio_only:
                a += ["-vn"]
            else:
                vc = self.vcodec.currentData()
                if vc == "auto":
                    vc = AUTO_VCODEC.get(fmt, "libx264")
                filters = []
                if self.res.currentData():
                    filters.append(f"scale=-2:{self.res.currentData()}")
                if self.fps.currentData():
                    filters.append(f"fps={self.fps.currentData()}")
                if vc == "copy":
                    if filters:
                        raise ValueError("No se puede cambiar resolución ni FPS copiando el video sin recodificar. "
                                         "Elige un códec de video.")
                    a += ["-map", "0:v?", "-c:v", "copy"]
                else:
                    a += ["-map", "0:v:0?"]
                    a += video_quality_args(vc, self.crf.value(), self.vpreset.currentData())
                    if filters:
                        a += ["-vf", ",".join(filters)]
                    if self.yuv420.isChecked():
                        a += ["-pix_fmt", "yuv420p"]
            if self.no_audio.isChecked() and not audio_only:
                a += ["-an"]
            else:
                ac = self.acodec.currentData()
                if ac == "auto":
                    ac = AUTO_ACODEC.get(fmt, "aac")
                if not audio_only:
                    a += ["-map", "0:a?"]
                a += ["-c:a", ac]
                if ac != "copy":
                    if ac not in LOSSLESS_A:
                        a += ["-b:a", self.abitrate.currentData()]
                    if self.arate.currentData():
                        a += ["-ar", self.arate.currentData()]
                    if self.achannels.currentData():
                        a += ["-ac", self.achannels.currentData()]
                    if self.volume.value():
                        a += ["-af", f"volume={self.volume.value():g}dB"]
                if fmt == "mp3":
                    a += ["-id3v2_version", "3"]
            if fmt in ("mp4", "mov", "m4a"):
                a += ["-movflags", "+faststart"]
            if fmt == "mkv" and not audio_only and self.vcodec.currentData() == "copy":
                a += ["-map", "0:s?", "-c:s", "copy"]
        if self.extra.text().strip():
            a += shlex.split(self.extra.text(), posix=True)
        a += [out]
        return a

    def _out_for(self, src):
        folder = None if self.same_folder.isChecked() else (self.out_dir.path() or None)
        return derive_output(src, self.suffix.text().strip(), self.fmt.currentData(), folder)

    def _preview(self, *_):
        files = self.files.files()
        src = files[0] if files else "entrada.mp4"
        try:
            args = self.build_args(src, self._out_for(src) if files else "salida." + self.fmt.currentData())
            self.cmd_lbl.setText("ffmpeg " + " ".join(f'"{x}"' if " " in x else x for x in args))
        except ValueError as e:
            self.cmd_lbl.setText(f"⚠ {e}")

    def add_files(self, files):
        self.files.add_files(files)

    def convert(self):
        files = self.files.files()
        if not files:
            QMessageBox.information(self, "Sin archivos", "Añade al menos un archivo para convertir.")
            return
        if not self.same_folder.isChecked() and not os.path.isdir(self.out_dir.path()):
            QMessageBox.warning(self, "Carpeta", "Elige una carpeta de destino válida.")
            return
        try:
            jobs = []
            for src in files:
                out = self._out_for(src)
                if os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(src)):
                    raise ValueError("La salida coincidiría con el archivo original. Usa un sufijo u otra carpeta.")
                jobs.append((src, out, self.build_args(src, out)))
        except ValueError as e:
            QMessageBox.warning(self, "Opciones no válidas", str(e))
            return
        start = parse_time(self.start.text())
        end = parse_time(self.end.text())
        for src, out, args in jobs:
            dur = None
            if end is not None:
                dur = end - (start or 0)
            t = FFmpegTask(f"{os.path.basename(src)} → {self.fmt.currentData().upper()}", [args], output=out,
                           duration=dur, probe=src, label="Conversión")
            if start and end is None:
                t.on_probe = lambda d, s=start: max(0.1, d - s)
            self.manager.add(t)
        self.go_queue()
