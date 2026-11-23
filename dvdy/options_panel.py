"""Panel de opciones de descarga compartido por las pantallas Descargar y Playlists.

Arriba, lo esencial siempre a la vista: la banda (Video / Música, y en modo Avanzado también
Solo video y Formato manual) y cuatro casillas: Calidad, Formato, Carpeta y Subtítulos.
Debajo, «Más opciones» despliega todo lo demás. El botón indica cuántas opciones extra están
activas, para que nada oculto se aplique sin que se vea.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from .config import cfg
from .widgets import BandSelector, FolderButton, Segmented, combo, field, label, row, tile
from .ytopts import (
    AUDIO_FORMATS, AUDIO_QUALITIES, CONTAINERS, FPS_OPTIONS, SPONSOR_CATEGORIES, SUB_FORMATS,
    TEMPLATE_PRESETS, VIDEO_CODECS, VIDEO_QUALITIES,
)

MODES = [("Video", "av"), ("Música", "audio"), ("Solo video", "video"), ("Formato manual", "custom")]
SUB_CHOICES = [("Sin subtítulos", ""), ("Español", "es.*,es"), ("Inglés", "en.*,en"),
               ("Español e inglés", "es.*,es,en.*,en"), ("Todos los idiomas", "all")]
AUDIO_FMT_SHORT = [(t.split(" (")[0], d) for t, d in AUDIO_FORMATS]
VIDEO_Q_SHORT = [("La mejor", "best"), ("8K", "4320"), ("4K", "2160"), ("1440p", "1440"), ("1080p", "1080"),
                 ("720p", "720"), ("480p", "480"), ("360p", "360"), ("240p", "240"), ("144p", "144")]


def _tab():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    return w, lay


class OptionsPanel(QWidget):
    changed = Signal()

    def __init__(self, playlist=False):
        super().__init__()
        self.playlist = playlist
        self.simple = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(14)

        # ---------------- Banda ----------------
        self.mode = BandSelector(MODES, "audio" if playlist else "av")
        self.mode.changed.connect(self._update_enabled)
        outer.addWidget(self.mode)

        # ---------------- Casillas esenciales ----------------
        self.quality = combo(VIDEO_Q_SHORT, cfg["default_video_quality"])
        self.audio_quality = combo(AUDIO_QUALITIES, cfg["default_audio_quality"])
        self.container = combo(CONTAINERS, cfg["default_container"])
        self.audio_format = combo(AUDIO_FMT_SHORT, cfg["default_audio_format"])
        self.output_dir = FolderButton(cfg["music_dir"] if playlist else cfg["output_dir"])
        self.sub_choice = combo(SUB_CHOICES, "")
        self.q_box = QWidget()
        ql = QHBoxLayout(self.q_box)
        ql.setContentsMargins(0, 0, 0, 0)
        ql.addWidget(self.quality)
        ql.addWidget(self.audio_quality)
        self.f_box = QWidget()
        fl = QHBoxLayout(self.f_box)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(self.container)
        fl.addWidget(self.audio_format)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.addWidget(tile("Calidad", self.q_box), 0, 0)
        grid.addWidget(tile("Formato", self.f_box), 0, 1)
        grid.addWidget(tile("Carpeta", self.output_dir), 0, 2)
        grid.addWidget(tile("Subtítulos", self.sub_choice), 0, 3)
        for i in range(4):
            grid.setColumnStretch(i, 1)
        outer.addLayout(grid)

        self.format_string = QLineEdit()
        self.format_string.setPlaceholderText("Código de formato, ej.: 137+140 o bv*[height<=720]+ba/b  "
                                              "(también puedes elegirlo en la tabla de formatos)")
        self.custom_field = field("Código de formato (avanzado)", self.format_string,
                                  "Admite toda la sintaxis de selección de yt-dlp. Une video y audio con «+».")
        outer.addWidget(self.custom_field)

        # Espacio para la vista previa y el botón Descargar (lo llena la pantalla que usa el panel),
        # siempre por encima de «Más opciones» para que la acción principal no quede fuera de vista.
        self.action_slot = QVBoxLayout()
        self.action_slot.setContentsMargins(0, 0, 0, 0)

        # ---------------- Más opciones ----------------
        self.more_btn = QPushButton()
        self.more_btn.setObjectName("Flat")
        self.more_btn.setCheckable(True)
        self.more_btn.toggled.connect(self._toggle_more)
        outer.addWidget(row(self.more_btn, None))

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        self._build_tabs()
        self.tabs.currentChanged.connect(self._fit_tabs)
        self._fit_tabs()
        self.tabs.hide()
        # La vista previa y el pie con Descargar van después de las opciones que configuran
        outer.addLayout(self.action_slot, 1)

        for w in (self.quality, self.audio_quality, self.container, self.audio_format, self.sub_choice):
            w.currentIndexChanged.connect(self._update_enabled)
        self._update_enabled()

    # ------------------------------------------------------------------
    def _build_tabs(self):
        playlist = self.playlist

        # ===== Video =====
        w, lay = _tab()
        self.vcodec = combo(VIDEO_CODECS, "any")
        self.fps = combo(FPS_OPTIONS, "any")
        lay.addWidget(row(field("Códec de video preferido", self.vcodec), field("Cuadros por segundo", self.fps)))
        self.keep_video = QCheckBox("Conservar los archivos originales después de unir o convertir")
        lay.addWidget(self.keep_video)
        lay.addStretch(1)
        self.tabs.addTab(w, "Video")

        # ===== Metadatos =====
        w, lay = _tab()
        self.embed_metadata = QCheckBox("Guardar título, artista y fecha dentro del archivo")
        self.embed_metadata.setChecked(cfg["embed_metadata"])
        self.embed_thumbnail = QCheckBox("Poner la carátula o miniatura dentro del archivo")
        self.embed_thumbnail.setChecked(cfg["embed_thumbnail"])
        self.square_thumbnail = QCheckBox("Recortar la carátula a cuadrado, como un disco")
        self.square_thumbnail.setChecked(playlist)
        self.write_thumbnail = QCheckBox("Guardar también la miniatura como imagen aparte")
        self.parse_artist_title = QCheckBox("Separar «Artista - Título» y quitar «(Official Video)» del nombre")
        self.parse_artist_title.setChecked(playlist)
        self.album_from_playlist = QCheckBox("Usar el nombre de la playlist como álbum y su orden como nº de pista")
        self.album_from_playlist.setChecked(playlist)
        self.album_from_playlist.setVisible(playlist)
        self.write_description = QCheckBox("Guardar la descripción en un archivo de texto")
        self.write_info_json = QCheckBox("Guardar toda la información técnica (.info.json)")
        self.write_comments = QCheckBox("Guardar los comentarios (puede tardar)")
        for cb in (self.embed_metadata, self.embed_thumbnail, self.square_thumbnail, self.write_thumbnail,
                   self.parse_artist_title, self.album_from_playlist, self.write_description,
                   self.write_info_json, self.write_comments):
            lay.addWidget(cb)
            cb.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Datos y carátula")

        # ===== Subtítulos =====
        w, lay = _tab()
        self.sub_langs = QLineEdit()
        self.sub_langs.setPlaceholderText("Idiomas personalizados, ej.: es,en,pt  (vacío = lo elegido arriba)")
        self.sub_format = combo(SUB_FORMATS, "srt")
        lay.addWidget(row(field("Otros idiomas", self.sub_langs), field("Formato", self.sub_format)))
        self.auto_subs = QCheckBox("Incluir subtítulos generados automáticamente")
        self.embed_subs = QCheckBox("Ponerlos dentro del video")
        self.embed_subs.setChecked(True)
        self.keep_sub_files = QCheckBox("Guardar también los archivos de subtítulos")
        for cb in (self.auto_subs, self.embed_subs, self.keep_sub_files):
            lay.addWidget(cb)
            cb.toggled.connect(self._update_enabled)
        self.sub_langs.textChanged.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Subtítulos")

        # ===== Capítulos, SponsorBlock y fragmento =====
        w, lay = _tab()
        self.embed_chapters = QCheckBox("Guardar los capítulos dentro del archivo")
        self.embed_chapters.setChecked(True)
        self.split_chapters = QCheckBox("Separar en un archivo por capítulo (ideal para álbumes completos)")
        lay.addWidget(self.embed_chapters)
        lay.addWidget(self.split_chapters)
        lay.addWidget(label("Saltar partes con SponsorBlock", "SectionTitle"))
        self.sponsorblock = Segmented([("No", "none"), ("Marcar como capítulos", "mark"),
                                       ("Quitar del archivo", "remove")], "none")
        self.sponsorblock.changed.connect(self._update_enabled)
        lay.addWidget(self.sponsorblock)
        sg = QGridLayout()
        self.sponsor_checks = {}
        for i, (key, text) in enumerate(SPONSOR_CATEGORIES):
            cb = QCheckBox(text)
            cb.setChecked(key in ("sponsor", "selfpromo", "interaction", "music_offtopic"))
            self.sponsor_checks[key] = cb
            sg.addWidget(cb, i // 2, i % 2)
        lay.addLayout(sg)
        for cb in (self.embed_chapters, self.split_chapters):
            cb.toggled.connect(self._update_enabled)
        if not playlist:
            lay.addWidget(label("Bajar solo una parte", "SectionTitle"))
            self.section = QCheckBox("Bajar solo un fragmento")
            self.section_start = QLineEdit()
            self.section_start.setPlaceholderText("Desde, ej.: 0:30")
            self.section_end = QLineEdit()
            self.section_end.setPlaceholderText("Hasta, ej.: 2:15 (vacío = hasta el final)")
            self.precise_cut = QCheckBox("Corte exacto (más lento)")
            lay.addWidget(self.section)
            lay.addWidget(row(self.section_start, self.section_end))
            lay.addWidget(self.precise_cut)
            self.section.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Capítulos y fragmentos")

        # ===== Nombres y playlists =====
        w, lay = _tab()
        self.template = QComboBox()
        self.template.setEditable(True)
        for text, t in TEMPLATE_PRESETS:
            self.template.addItem(f"{text}   ·   {t}", t)
        self._default_template = cfg["playlist_template"] if playlist else cfg["filename_template"]
        self.template.setEditText(self._default_template)
        self.template.activated.connect(lambda i: self.template.setEditText(self.template.itemData(i)))
        self.template.editTextChanged.connect(self._update_enabled)
        lay.addWidget(field("Nombre de los archivos", self.template,
                            "Ejemplos de variables: %(title)s título, %(uploader)s canal, %(playlist_index)02d número "
                            "en la playlist. Usa «/» para crear subcarpetas."))
        self.restrict_filenames = QCheckBox("Nombres simples (sin acentos, espacios ni símbolos)")
        self.restrict_filenames.setChecked(cfg["restrict_filenames"])
        self.no_overwrite = QCheckBox("No reemplazar archivos que ya existen")
        self.no_overwrite.setChecked(True)
        lay.addWidget(self.restrict_filenames)
        lay.addWidget(self.no_overwrite)
        if playlist:
            self.use_archive = QCheckBox("Recordar lo ya bajado y saltarlo la próxima vez (para mantener playlists al día)")
            self.use_archive.setChecked(cfg["use_archive"])
            self.playlist_reverse = QCheckBox("Bajar en orden inverso")
            lay.addWidget(self.use_archive)
            lay.addWidget(self.playlist_reverse)
            self.min_duration = QLineEdit()
            self.min_duration.setPlaceholderText("Duración mínima, ej.: 1:00")
            self.max_duration = QLineEdit()
            self.max_duration.setPlaceholderText("Duración máxima, ej.: 10:00")
            self.title_filter = QLineEdit()
            self.title_filter.setPlaceholderText("Solo títulos que contengan…")
            lay.addWidget(label("Filtros", "SectionTitle"))
            lay.addWidget(row(self.min_duration, self.max_duration))
            lay.addWidget(self.title_filter)
            for wdg in (self.use_archive, self.playlist_reverse):
                wdg.toggled.connect(self._update_enabled)
            for wdg in (self.min_duration, self.max_duration, self.title_filter):
                wdg.textChanged.connect(self._update_enabled)
        else:
            self.noplaylist = QCheckBox("Si el enlace es de una playlist, bajar solo este video")
            self.noplaylist.setChecked(True)
            lay.addWidget(self.noplaylist)
        for cb in (self.restrict_filenames, self.no_overwrite):
            cb.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Nombres y playlists" if playlist else "Nombres")

    # ------------------------------------------------------------------
    def _fit_tabs(self, *_):
        """Cada pestaña ocupa solo su alto (QTabWidget usa por defecto el de la más alta)."""
        from PySide6.QtWidgets import QSizePolicy
        cur = self.tabs.currentIndex()
        for i in range(self.tabs.count()):
            pol = QSizePolicy.Preferred if i == cur else QSizePolicy.Ignored
            self.tabs.widget(i).setSizePolicy(pol, pol)
        page = self.tabs.widget(cur)
        page.adjustSize()
        self.tabs.setFixedHeight(self.tabs.tabBar().sizeHint().height() + page.sizeHint().height() + 6)

    def _toggle_more(self, on):
        """Abre en 220 ms (ease-out) y cierra en 120 ms (ease-in): cerrar siempre es más rápido."""
        from . import motion
        self._update_more_label()
        start = self.tabs.height() if self.tabs.isVisible() else 0
        if on:
            self.tabs.setVisible(True)
            self._fit_tabs()
            target = self.tabs.height()
            if not motion.enabled():
                return
            self.tabs.setFixedHeight(start)
            motion.fade(self.tabs, 0.0, 1.0, motion.ENTER, motion.ease_out())
            motion.animate(self, "more", start, target, 220, motion.ease_out(),
                           lambda v: self.tabs.setFixedHeight(int(v)), self._fit_tabs)
        else:
            def done():
                self.tabs.setVisible(False)
                self.tabs.setGraphicsEffect(None)
                self._fit_tabs()
            if not motion.enabled():
                done()
                return
            motion.fade(self.tabs, 1.0, 0.0, motion.EXIT, motion.ease_in())
            motion.animate(self, "more", start, 0, motion.EXIT, motion.ease_in(),
                           lambda v: self.tabs.setFixedHeight(int(v)), done)

    def _active_extras(self):
        """Opciones de «Más opciones» que difieren de lo predeterminado."""
        n = 0
        n += self.vcodec.currentData() != "any"
        n += self.fps.currentData() != "any"
        n += self.keep_video.isChecked()
        n += self.embed_metadata.isChecked() != bool(cfg["embed_metadata"])
        n += self.embed_thumbnail.isChecked() != bool(cfg["embed_thumbnail"])
        n += self.write_thumbnail.isChecked()
        n += self.write_description.isChecked()
        n += self.write_info_json.isChecked()
        n += self.write_comments.isChecked()
        n += bool(self.sub_langs.text().strip())
        n += self.auto_subs.isChecked()
        n += self.split_chapters.isChecked()
        n += self.sponsorblock.value() != "none"
        n += self.template.currentText().strip() != self._default_template
        n += self.restrict_filenames.isChecked() != bool(cfg["restrict_filenames"])
        n += not self.no_overwrite.isChecked()
        if self.playlist:
            n += self.playlist_reverse.isChecked()
            n += bool(self.min_duration.text().strip() or self.max_duration.text().strip()
                      or self.title_filter.text().strip())
        else:
            n += self.section.isChecked()
        return n

    def _update_more_label(self):
        import os
        from PySide6.QtCore import QSize, Qt as _Qt
        from PySide6.QtGui import QIcon
        from .theme import current
        n = self._active_extras()
        extra = f"  ·  {n} activa{'s' if n != 1 else ''}" if n else ""
        self.more_btn.setText(f"Más opciones{extra}")
        ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui")
        name = "chevron_up" if self.more_btn.isChecked() else "chevron"
        self.more_btn.setIcon(QIcon(os.path.join(ui, f"{name}_{current.get('name', 'dark')}.svg")))
        self.more_btn.setIconSize(QSize(11, 11))
        self.more_btn.setLayoutDirection(_Qt.RightToLeft)
        self.more_btn.setAccessibleName("Más opciones" + (f", {n} activas" if n else ""))

    def _update_enabled(self, *_):
        mode = self.mode.value()
        audio = mode == "audio"
        video = mode in ("av", "video", "custom")
        self.quality.setVisible(not audio)
        self.audio_quality.setVisible(audio)
        self.container.setVisible(not audio)
        self.audio_format.setVisible(audio)
        self.quality.setEnabled(mode in ("av", "video"))
        self.vcodec.setEnabled(mode in ("av", "video"))
        self.fps.setEnabled(mode in ("av", "video"))
        self.custom_field.setVisible(mode == "custom")
        self.tabs.setTabVisible(0, video)
        self.square_thumbnail.setEnabled(self.embed_thumbnail.isChecked() or self.write_thumbnail.isChecked())
        subs = bool(self.sub_choice.currentData() or self.sub_langs.text().strip())
        for wdg in (self.sub_format, self.auto_subs, self.keep_sub_files):
            wdg.setEnabled(subs)
        self.embed_subs.setEnabled(subs and video)
        sb = self.sponsorblock.value() != "none"
        for cb in self.sponsor_checks.values():
            cb.setEnabled(sb)
        if not self.playlist:
            on = self.section.isChecked()
            self.section_start.setEnabled(on)
            self.section_end.setEnabled(on)
            self.precise_cut.setEnabled(on)
        self._update_more_label()
        self.changed.emit()

    # ------------------------------------------------------------------
    def set_simple(self, simple):
        """Simple: banda de dos opciones y «Más opciones» plegado. Avanzado: todo desplegado."""
        self.simple = simple
        for key in ("video", "custom"):
            self.mode.set_key_visible(key, not simple)
        if simple and self.mode.value() in ("video", "custom"):
            self.set_mode("av")
        self.more_btn.setChecked(not simple)
        self._update_enabled()

    def set_mode(self, mode):
        self.mode.set_value(mode)
        self._update_enabled()

    def set_format_string(self, s):
        self.format_string.setText(s)
        self.set_mode("custom")

    def values(self):
        langs = self.sub_langs.text().strip() or self.sub_choice.currentData()
        v = {
            "mode": self.mode.value(),
            "quality": self.quality.currentData(),
            "container": self.container.currentData(),
            "vcodec": self.vcodec.currentData(),
            "fps": self.fps.currentData(),
            "audio_format": self.audio_format.currentData(),
            "audio_quality": self.audio_quality.currentData(),
            "format_string": self.format_string.text().strip(),
            "keep_video": self.keep_video.isChecked(),
            "embed_metadata": self.embed_metadata.isChecked(),
            "embed_thumbnail": self.embed_thumbnail.isChecked(),
            "square_thumbnail": self.square_thumbnail.isChecked(),
            "write_thumbnail": self.write_thumbnail.isChecked(),
            "parse_artist_title": self.parse_artist_title.isChecked(),
            "write_description": self.write_description.isChecked(),
            "write_info_json": self.write_info_json.isChecked(),
            "write_comments": self.write_comments.isChecked(),
            "album_from_playlist": self.playlist and self.album_from_playlist.isChecked(),
            "subs": bool(langs),
            "sub_langs": langs or "",
            "sub_format": self.sub_format.currentData(),
            "auto_subs": self.auto_subs.isChecked(),
            "embed_subs": self.embed_subs.isChecked(),
            "keep_sub_files": self.keep_sub_files.isChecked(),
            "embed_chapters": self.embed_chapters.isChecked(),
            "split_chapters": self.split_chapters.isChecked(),
            "sponsorblock": self.sponsorblock.value(),
            "sponsor_categories": [k for k, cb in self.sponsor_checks.items() if cb.isChecked()],
            "output_dir": self.output_dir.path(),
            "template": self.template.currentText().strip(),
            "restrict_filenames": self.restrict_filenames.isChecked(),
            "no_overwrite": self.no_overwrite.isChecked(),
        }
        if self.playlist:
            v.update({
                "is_playlist": True,
                "use_archive": self.use_archive.isChecked(),
                "playlist_reverse": self.playlist_reverse.isChecked(),
                "min_duration": self.min_duration.text().strip(),
                "max_duration": self.max_duration.text().strip(),
                "title_filter": self.title_filter.text().strip(),
            })
        else:
            v.update({
                "noplaylist": self.noplaylist.isChecked(),
                "section": self.section.isChecked(),
                "section_start": self.section_start.text(),
                "section_end": self.section_end.text(),
                "precise_cut": self.precise_cut.isChecked(),
            })
        return v

    def summary(self):
        v = self.values()
        if v["mode"] == "audio":
            return f"Música · {self.audio_format.currentText()} · {self.audio_quality.currentText()}"
        if v["mode"] == "custom":
            return f"Formato {v['format_string'] or '—'}"
        q = self.quality.currentText()
        kind = "Solo video" if v["mode"] == "video" else "Video"
        return f"{kind} · {q} · {v['container'].upper()}"
