"""Pantalla «Ajustes». Los cambios se guardan solos.

Modo Simple: carpetas, opciones predeterminadas, tema y componentes.
Modo Avanzado: además, nombres de archivo, red, cookies del navegador y rutas de programas.
"""
import os

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLineEdit, QMessageBox, QSpinBox

from .config import ARCHIVE_FILE, CONFIG_DIR, cfg
from .utils import ffmpeg_version, find_ffmpeg, find_js_runtime
from .widgets import Page, PathPicker, Segmented, button, card, combo, field, label, row, run_async
from .ytopts import AUDIO_FORMATS, AUDIO_QUALITIES, CONTAINERS, VIDEO_QUALITIES

BROWSERS = [("No usar", ""), ("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox"), ("Brave", "brave"),
            ("Opera", "opera"), ("Vivaldi", "vivaldi"), ("Chromium", "chromium"), ("Whale", "whale")]


def _versions():
    import yt_dlp
    js, jsp = find_js_runtime()
    return {"yt-dlp": yt_dlp.version.__version__, "ffmpeg": ffmpeg_version(), "ffmpeg_path": find_ffmpeg(),
            "js": js, "js_path": jsp}


class SettingsPage(Page):
    theme_changed = Signal()
    components_requested = Signal()

    def __init__(self, manager):
        super().__init__("Ajustes", "Los cambios se guardan solos.")
        self.manager = manager
        self.adv = []
        self._loading = True
        self.saved_lbl = label("", "Hint")
        self.header_row.addWidget(self.saved_lbl)

        # ---- Componentes ----
        c, lay = card("Componentes")
        self.ver_lbl = label("Comprobando…", "Muted", wrap=True)
        lay.addWidget(self.ver_lbl)
        self.ver_detail = label("", "Hint", wrap=True)
        lay.addWidget(self.ver_detail)
        self.adv.append(self.ver_detail)
        lay.addWidget(row(button("Instalar o actualizar componentes…", lambda: self.components_requested.emit()),
                          button("Comprobar de nuevo", self.check, flat=True), None))
        lay.addWidget(label("Si YouTube cambia algo y las descargas empiezan a fallar, actualizar yt-dlp suele solucionarlo.",
                            "Hint", wrap=True))
        self.ffmpeg_path = PathPicker("open", cfg["ffmpeg_path"], "ffmpeg.exe (ffmpeg.exe);;Todos (*)",
                                      "Vacío = usar el FFmpeg instalado por la app o el del sistema")
        f = field("Ruta de FFmpeg (opcional)", self.ffmpeg_path)
        lay.addWidget(f)
        self.adv.append(f)
        self.add(c)

        # ---- Carpetas ----
        c, lay = card("Carpetas")
        self.output_dir = PathPicker("dir", cfg["output_dir"])
        self.music_dir = PathPicker("dir", cfg["music_dir"])
        lay.addWidget(field("Videos", self.output_dir))
        lay.addWidget(field("Música y playlists", self.music_dir))
        self.add(c)

        # ---- Predeterminados ----
        c, lay = card("Al empezar una descarga", "Lo que viene elegido al abrir la app y en las descargas rápidas de Buscar.")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.def_quality = combo(VIDEO_QUALITIES, cfg["default_video_quality"])
        self.def_container = combo(CONTAINERS, cfg["default_container"])
        self.def_afmt = combo(AUDIO_FORMATS, cfg["default_audio_format"])
        self.def_aq = combo(AUDIO_QUALITIES, cfg["default_audio_quality"])
        g.addWidget(field("Calidad de video", self.def_quality), 0, 0)
        g.addWidget(field("Formato de video", self.def_container), 0, 1)
        g.addWidget(field("Formato de música", self.def_afmt), 1, 0)
        g.addWidget(field("Calidad de música", self.def_aq), 1, 1)
        lay.addLayout(g)
        self.embed_meta = QCheckBox("Guardar título, artista y fecha dentro del archivo")
        self.embed_meta.setChecked(cfg["embed_metadata"])
        self.embed_thumb = QCheckBox("Poner la carátula dentro del archivo")
        self.embed_thumb.setChecked(cfg["embed_thumbnail"])
        self.use_archive = QCheckBox("En playlists, recordar lo ya bajado y saltarlo la próxima vez")
        self.use_archive.setChecked(cfg["use_archive"])
        for w in (self.embed_meta, self.embed_thumb, self.use_archive):
            lay.addWidget(w)
        lay.addWidget(row(button("Olvidar lo ya bajado en playlists", self.clear_archive, flat=True), None))
        self.add(c)

        # ---- Interfaz ----
        c, lay = card("Apariencia y avisos")
        self.theme = Segmented([("Como Windows", "auto"), ("Oscuro", "dark"), ("Claro", "light")], cfg["theme"])
        lay.addWidget(field("Tema", self.theme))
        self.clip = QCheckBox("Ofrecer descargar los enlaces que copio")
        self.clip.setChecked(cfg["clipboard_monitor"])
        self.notify = QCheckBox("Avisarme cuando termina cada descarga")
        self.notify.setChecked(cfg["notify_on_finish"])
        lay.addWidget(self.clip)
        lay.addWidget(self.notify)
        self.add(c)

        # ---- Nombres (Avanzado) ----
        c, lay = card("Nombres de archivo")
        self.tmpl = QLineEdit(cfg["filename_template"])
        self.pl_tmpl = QLineEdit(cfg["playlist_template"])
        lay.addWidget(field("Videos y canciones sueltas", self.tmpl))
        lay.addWidget(field("Playlists", self.pl_tmpl,
                            "Variables: %(title)s título, %(uploader)s canal, %(playlist_title)s nombre de la playlist, "
                            "%(playlist_index)02d número. «/» crea subcarpetas."))
        self.restrict = QCheckBox("Nombres simples (sin acentos, espacios ni símbolos)")
        self.restrict.setChecked(cfg["restrict_filenames"])
        lay.addWidget(self.restrict)
        self.add(c)
        self.adv.append(c)

        # ---- Red (Avanzado) ----
        c, lay = card("Red y descargas")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.max_conc = QSpinBox()
        self.max_conc.setRange(1, 10)
        self.max_conc.setValue(int(cfg["max_concurrent"]))
        self.frags = QSpinBox()
        self.frags.setRange(1, 32)
        self.frags.setValue(int(cfg["concurrent_fragments"]))
        self.retries = QSpinBox()
        self.retries.setRange(0, 100)
        self.retries.setValue(int(cfg["retries"]))
        self.rate = QLineEdit(cfg["rate_limit"])
        self.rate.setPlaceholderText("Sin límite (ej.: 5M, 500K)")
        self.proxy = QLineEdit(cfg["proxy"])
        self.proxy.setPlaceholderText("http://usuario:clave@servidor:puerto  o  socks5://…")
        g.addWidget(field("Descargas a la vez", self.max_conc), 0, 0)
        g.addWidget(field("Partes en paralelo por descarga", self.frags), 0, 1)
        g.addWidget(field("Reintentos", self.retries), 1, 0)
        g.addWidget(field("Límite de velocidad", self.rate), 1, 1)
        lay.addLayout(g)
        lay.addWidget(field("Proxy", self.proxy))
        self.geo = QCheckBox("Intentar evitar bloqueos por país")
        self.geo.setChecked(cfg["geo_bypass"])
        lay.addWidget(self.geo)
        self.add(c)
        self.adv.append(c)

        # ---- Cookies (Avanzado) ----
        c, lay = card("Cookies del navegador",
                      "Sirven para videos con restricción de edad, privados o de miembros. Si el navegador está abierto y no "
                      "se pueden leer, la app descarga igual sin ellas.")
        self.browser = combo(BROWSERS, cfg["cookies_browser"])
        self.cookie_file = PathPicker("open", cfg["cookies_file"], "Cookies (*.txt);;Todos (*)",
                                      "Opcional: archivo cookies.txt")
        lay.addWidget(row(field("Leer cookies de", self.browser), None))
        lay.addWidget(field("Archivo de cookies", self.cookie_file))
        self.add(c)
        self.adv.append(c)

        cfg_btn = button("Abrir la carpeta de configuración",
                         lambda: os.startfile(CONFIG_DIR) if os.path.isdir(CONFIG_DIR) else None, flat=True)
        self.add(row(cfg_btn, None))
        self.adv.append(cfg_btn)
        self.body.addStretch(1)

        # Guardado automático (con una pequeña espera para no escribir en cada tecla)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.save)
        for w in (self.ffmpeg_path, self.output_dir, self.music_dir, self.cookie_file):
            w.changed.connect(self._changed)
        for w in (self.tmpl, self.pl_tmpl, self.rate, self.proxy):
            w.textChanged.connect(self._changed)
        for w in (self.def_quality, self.def_container, self.def_afmt, self.def_aq, self.browser):
            w.currentIndexChanged.connect(self._changed)
        for w in (self.embed_meta, self.embed_thumb, self.use_archive, self.clip, self.notify, self.restrict, self.geo):
            w.toggled.connect(self._changed)
        for w in (self.max_conc, self.frags, self.retries):
            w.valueChanged.connect(self._changed)
        self.theme.changed.connect(self._changed)
        self._loading = False
        self.check()

    # ------------------------------------------------------------------
    def set_simple(self, simple):
        for w in self.adv:
            w.setVisible(not simple)

    def _changed(self, *_):
        if not self._loading:
            self.saved_lbl.setText("")
            self._timer.start()

    def check(self):
        self.ver_lbl.setText("Comprobando…")
        run_async(_versions, on_done=self._show_versions, on_error=lambda m: self.ver_lbl.setText(m))

    def _show_versions(self, v):
        ok_ff = bool(v["ffmpeg"])
        ok_js = bool(v["js"])
        lines = [
            f"Motor de descargas (yt-dlp): versión {v['yt-dlp']}",
            "FFmpeg: instalado" if ok_ff else "FFmpeg: falta. Sin él no se pueden unir videos ni convertir a MP3.",
            "Deno: instalado" if ok_js else "Deno: falta. YouTube ofrece menos calidades sin él.",
        ]
        self.ver_lbl.setText("\n".join(lines))
        self.ver_lbl.setObjectName("Muted" if ok_ff and ok_js else "ErrText")
        self.ver_lbl.style().unpolish(self.ver_lbl)
        self.ver_lbl.style().polish(self.ver_lbl)
        details = []
        if ok_ff:
            details.append(f"FFmpeg {v['ffmpeg']}: {v['ffmpeg_path']}")
        if ok_js:
            details.append(f"{v['js']}: {v['js_path']}")
        self.ver_detail.setText("\n".join(details))

    def clear_archive(self):
        if os.path.isfile(ARCHIVE_FILE):
            os.remove(ARCHIVE_FILE)
        QMessageBox.information(self, "Listo", "La próxima vez se volverán a bajar todas las canciones de tus playlists.")

    def save(self):
        old_theme = cfg["theme"]
        cfg["ffmpeg_path"] = self.ffmpeg_path.path()
        cfg["output_dir"] = self.output_dir.path() or cfg["output_dir"]
        cfg["music_dir"] = self.music_dir.path() or cfg["music_dir"]
        cfg["filename_template"] = self.tmpl.text().strip() or "%(title)s.%(ext)s"
        cfg["playlist_template"] = self.pl_tmpl.text().strip() or cfg["playlist_template"]
        cfg["restrict_filenames"] = self.restrict.isChecked()
        cfg["default_video_quality"] = self.def_quality.currentData()
        cfg["default_container"] = self.def_container.currentData()
        cfg["default_audio_format"] = self.def_afmt.currentData()
        cfg["default_audio_quality"] = self.def_aq.currentData()
        cfg["embed_metadata"] = self.embed_meta.isChecked()
        cfg["embed_thumbnail"] = self.embed_thumb.isChecked()
        cfg["use_archive"] = self.use_archive.isChecked()
        cfg["max_concurrent"] = self.max_conc.value()
        cfg["concurrent_fragments"] = self.frags.value()
        cfg["retries"] = self.retries.value()
        cfg["rate_limit"] = self.rate.text().strip()
        cfg["proxy"] = self.proxy.text().strip()
        cfg["geo_bypass"] = self.geo.isChecked()
        cfg["cookies_browser"] = self.browser.currentData()
        cfg["cookies_file"] = self.cookie_file.path()
        cfg["theme"] = self.theme.value()
        cfg["clipboard_monitor"] = self.clip.isChecked()
        cfg["notify_on_finish"] = self.notify.isChecked()
        cfg.save()
        self.manager.schedule()
        self.saved_lbl.setText("Guardado")
        if old_theme != cfg["theme"]:
            self.theme_changed.emit()
