"""Página «Ajustes»."""
import os
import subprocess

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QColorDialog, QGridLayout, QLineEdit, QMessageBox, QSpinBox

from .config import ARCHIVE_FILE, CONFIG_DIR, cfg
from .tasks import CallableTask
from .utils import ffmpeg_version, find_ffmpeg, find_js_runtime
from .widgets import Page, PathPicker, Segmented, button, card, combo, field, label, row, run_async
from .ytopts import AUDIO_FORMATS, AUDIO_QUALITIES, CONTAINERS, VIDEO_QUALITIES

BROWSERS = [("Ninguno", ""), ("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox"), ("Brave", "brave"),
            ("Opera", "opera"), ("Vivaldi", "vivaldi"), ("Chromium", "chromium"), ("Whale", "whale")]
ACCENTS = ["#7c5cff", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"]


def _versions():
    import yt_dlp
    js, jsp = find_js_runtime()
    return {
        "yt-dlp": yt_dlp.version.__version__,
        "ffmpeg": ffmpeg_version(),
        "ffmpeg_path": find_ffmpeg(),
        "js": f"{js} ({jsp})" if js else None,
    }


class SettingsPage(Page):
    theme_changed = Signal()

    def __init__(self, manager):
        super().__init__("Ajustes", "Preferencias generales. Se guardan automáticamente al pulsar «Guardar».")
        self.manager = manager

        # ---- Programas ----
        c, lay = card("Programas")
        self.ver_lbl = label("Comprobando versiones…", "Muted", wrap=True)
        lay.addWidget(self.ver_lbl)
        self.ffmpeg_path = PathPicker("open", cfg["ffmpeg_path"], "ffmpeg.exe (ffmpeg.exe);;Todos (*)",
                                      "Vacío = detectar automáticamente en el PATH")
        lay.addWidget(field("Ruta de FFmpeg", self.ffmpeg_path))
        lay.addWidget(row(button("Instalar / actualizar componentes…", self.open_components, primary=True),
                          button("Actualizar yt-dlp", self.update_ytdlp),
                          button("Comprobar de nuevo", self.check), None))
        lay.addWidget(label("YouTube cambia con frecuencia: si una descarga falla, actualizar yt-dlp suele solucionarlo. "
                            "FFmpeg y Deno se descargan de sus páginas oficiales a "
                            "%LOCALAPPDATA%\\DVDY Studio\\bin.", "Hint", wrap=True))
        self.add(c)

        # ---- Carpetas y nombres ----
        c, lay = card("Carpetas y nombres de archivo")
        self.output_dir = PathPicker("dir", cfg["output_dir"])
        self.music_dir = PathPicker("dir", cfg["music_dir"])
        self.tmpl = QLineEdit(cfg["filename_template"])
        self.pl_tmpl = QLineEdit(cfg["playlist_template"])
        lay.addWidget(field("Carpeta de videos", self.output_dir))
        lay.addWidget(field("Carpeta de música / playlists", self.music_dir))
        lay.addWidget(field("Plantilla para videos", self.tmpl))
        lay.addWidget(field("Plantilla para playlists", self.pl_tmpl,
                            "Ejemplo: %(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"))
        self.restrict = QCheckBox("Nombres de archivo simples (solo ASCII, sin espacios)")
        self.restrict.setChecked(cfg["restrict_filenames"])
        lay.addWidget(self.restrict)
        self.add(c)

        # ---- Predeterminados ----
        c, lay = card("Opciones predeterminadas", "Se usan en las descargas rápidas (Buscar, portapapeles) y al abrir la app.")
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        self.def_quality = combo(VIDEO_QUALITIES, cfg["default_video_quality"])
        self.def_container = combo(CONTAINERS, cfg["default_container"])
        self.def_afmt = combo(AUDIO_FORMATS, cfg["default_audio_format"])
        self.def_aq = combo(AUDIO_QUALITIES, cfg["default_audio_quality"])
        g.addWidget(field("Calidad de video", self.def_quality), 0, 0)
        g.addWidget(field("Contenedor", self.def_container), 0, 1)
        g.addWidget(field("Formato de audio", self.def_afmt), 1, 0)
        g.addWidget(field("Calidad de audio", self.def_aq), 1, 1)
        lay.addLayout(g)
        self.embed_meta = QCheckBox("Incrustar metadatos")
        self.embed_meta.setChecked(cfg["embed_metadata"])
        self.embed_thumb = QCheckBox("Incrustar carátula / miniatura")
        self.embed_thumb.setChecked(cfg["embed_thumbnail"])
        self.use_archive = QCheckBox("En playlists, recordar lo descargado y saltarlo la próxima vez")
        self.use_archive.setChecked(cfg["use_archive"])
        for w in (self.embed_meta, self.embed_thumb, self.use_archive):
            lay.addWidget(w)
        lay.addWidget(row(button("Vaciar registro de descargados", self.clear_archive, flat=True), None))
        self.add(c)

        # ---- Red ----
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
        self.rate.setPlaceholderText("Sin límite (ej. 5M, 500K)")
        self.proxy = QLineEdit(cfg["proxy"])
        self.proxy.setPlaceholderText("http://usuario:clave@host:puerto  o  socks5://…")
        g.addWidget(field("Tareas simultáneas", self.max_conc), 0, 0)
        g.addWidget(field("Fragmentos en paralelo por descarga", self.frags), 0, 1)
        g.addWidget(field("Reintentos", self.retries), 1, 0)
        g.addWidget(field("Límite de velocidad", self.rate), 1, 1)
        lay.addLayout(g)
        lay.addWidget(field("Proxy", self.proxy))
        self.geo = QCheckBox("Intentar evitar restricciones geográficas")
        self.geo.setChecked(cfg["geo_bypass"])
        lay.addWidget(self.geo)
        self.add(c)

        # ---- Cuenta ----
        c, lay = card("Cookies e inicio de sesión",
                      "Para videos privados, con restricción de edad, de miembros o si YouTube pide «confirma que no eres un bot». "
                      "Se leen las cookies del navegador donde tengas la sesión iniciada (ciérralo antes de descargar si falla).")
        self.browser = combo(BROWSERS, cfg["cookies_browser"])
        self.cookie_file = PathPicker("open", cfg["cookies_file"], "Cookies (*.txt);;Todos (*)",
                                      "Opcional: archivo cookies.txt en formato Netscape")
        lay.addWidget(row(field("Usar cookies del navegador", self.browser), None))
        lay.addWidget(field("Archivo de cookies", self.cookie_file))
        self.add(c)

        # ---- Interfaz ----
        c, lay = card("Interfaz")
        self.theme = Segmented([("Oscuro", "dark"), ("Claro", "light")], cfg["theme"])
        lay.addWidget(field("Tema", self.theme))
        self.accent = cfg["accent"]
        sw = []
        for col in ACCENTS:
            b = button("")
            b.setFixedSize(30, 30)
            b.setStyleSheet(f"background:{col}; border-radius:15px; border:2px solid rgba(255,255,255,40);")
            b.clicked.connect(lambda _=False, c=col: self._set_accent(c))
            sw.append(b)
        sw.append(button("Otro…", self._pick_accent, flat=True))
        lay.addWidget(field("Color de acento", row(*sw, None)))
        self.clip = QCheckBox("Detectar enlaces copiados al portapapeles y ofrecer descargarlos")
        self.clip.setChecked(cfg["clipboard_monitor"])
        self.notify = QCheckBox("Notificar al terminar cada tarea")
        self.notify.setChecked(cfg["notify_on_finish"])
        lay.addWidget(self.clip)
        lay.addWidget(self.notify)
        self.add(c)

        self.add(row(button("Abrir carpeta de configuración", lambda: os.startfile(CONFIG_DIR) if os.path.isdir(CONFIG_DIR) else None,
                            flat=True), None, button("Guardar", self.save, primary=True)))
        self.body.addStretch(1)
        self.check()

    # ------------------------------------------------------------------
    def _set_accent(self, col):
        self.accent = col
        self.save(silent=True)

    def _pick_accent(self):
        c = QColorDialog.getColor(QColor(self.accent), self, "Color de acento")
        if c.isValid():
            self._set_accent(c.name())

    def check(self):
        self.ver_lbl.setText("Comprobando versiones…")
        run_async(_versions, on_done=self._show_versions, on_error=lambda m: self.ver_lbl.setText(m))

    def _show_versions(self, v):
        ff = (f"FFmpeg {v['ffmpeg']}  —  {v['ffmpeg_path']}" if v["ffmpeg"]
              else "⚠ FFmpeg NO encontrado: pulsa «Instalar / actualizar componentes»." )
        js = (f"Intérprete JS: {v['js']}" if v["js"]
              else "⚠ Falta Deno (intérprete JS): pulsa «Instalar / actualizar componentes».")
        self.ver_lbl.setText(f"yt-dlp {v['yt-dlp']}\n{ff}\n{js}")

    def open_components(self, keys=("ffmpeg", "deno", "yt-dlp"), preselect=None):
        from . import deps
        from .setup_dialog import SetupDialog
        if preselect is None:
            preselect = deps.missing_components()
        dlg = SetupDialog(self, components=keys, preselect=preselect)
        dlg.exec()
        if dlg.changed:
            self.check()
            if "yt-dlp" in keys and dlg.checks.get("yt-dlp") and dlg.checks["yt-dlp"].isChecked():
                QMessageBox.information(self, "yt-dlp actualizado",
                                        "Reinicia DVDY Studio para usar la nueva versión de yt-dlp.")

    def update_ytdlp(self):
        self.open_components(("yt-dlp",), ["yt-dlp"])

    def clear_archive(self):
        if os.path.isfile(ARCHIVE_FILE):
            os.remove(ARCHIVE_FILE)
        QMessageBox.information(self, "Listo", "Se vació el registro de elementos descargados.")

    def save(self, silent=False):
        old_theme = (cfg["theme"], cfg["accent"])
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
        cfg["accent"] = self.accent
        cfg["clipboard_monitor"] = self.clip.isChecked()
        cfg["notify_on_finish"] = self.notify.isChecked()
        cfg.save()
        self.manager.schedule()
        if old_theme != (cfg["theme"], cfg["accent"]) or not silent:
            self.theme_changed.emit()
        if not silent:
            self.check()
            QMessageBox.information(self, "Ajustes", "Ajustes guardados.")
