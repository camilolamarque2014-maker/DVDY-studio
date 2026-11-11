"""Panel de opciones de descarga compartido por las páginas Descargar y Playlists."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .config import cfg
from .widgets import PathPicker, Segmented, combo, field, label, row
from .ytopts import (
    AUDIO_FORMATS, AUDIO_QUALITIES, CONTAINERS, FPS_OPTIONS, SPONSOR_CATEGORIES, SUB_FORMATS,
    TEMPLATE_PRESETS, VIDEO_CODECS, VIDEO_QUALITIES,
)

MODES = [("Video + audio", "av"), ("Solo audio", "audio"), ("Solo video (sin sonido)", "video"),
         ("Formato manual", "custom")]


def _tab():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    return w, lay


class OptionsPanel(QWidget):
    def __init__(self, playlist=False):
        super().__init__()
        self.playlist = playlist
        self.adv = []  # controles que solo se muestran en modo avanzado
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # ---- Modo ----
        self.mode = Segmented(MODES, "audio" if playlist else "av")
        self.mode.changed.connect(self._update_enabled)
        outer.addWidget(self.mode)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)

        # ================= Formato =================
        w, lay = _tab()
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        self.quality = combo(VIDEO_QUALITIES, cfg["default_video_quality"])
        self.container = combo(CONTAINERS, cfg["default_container"])
        self.vcodec = combo(VIDEO_CODECS, "any")
        self.fps = combo(FPS_OPTIONS, "any")
        self.audio_format = combo(AUDIO_FORMATS, cfg["default_audio_format"])
        self.audio_quality = combo(AUDIO_QUALITIES, cfg["default_audio_quality"])
        self.format_string = QLineEdit()
        self.format_string.setPlaceholderText("Ej.: 137+140, bv*[height<=720]+ba/b … (selecciona filas en la tabla de formatos)")
        grid.addWidget(field("Calidad de video", self.quality), 0, 0)
        grid.addWidget(field("Contenedor", self.container), 0, 1)
        self.adv.append(field("Códec de video preferido", self.vcodec))
        self.adv.append(field("Cuadros por segundo", self.fps))
        grid.addWidget(self.adv[-2], 1, 0)
        grid.addWidget(self.adv[-1], 1, 1)
        grid.addWidget(field("Formato de audio", self.audio_format), 2, 0)
        grid.addWidget(field("Calidad de audio", self.audio_quality), 2, 1)
        lay.addLayout(grid)
        self.custom_field = field("Código de formato (yt-dlp -f)", self.format_string,
                                  "Admite toda la sintaxis de selección de yt-dlp. Une video y audio con «+».")
        lay.addWidget(self.custom_field)
        self.keep_video = QCheckBox("Conservar los archivos originales tras convertir/unir")
        lay.addWidget(self.keep_video)
        self.adv.append(self.keep_video)
        lay.addStretch(1)
        self.tabs.addTab(w, "Formato")

        # ================= Metadatos =================
        w, lay = _tab()
        self.embed_metadata = QCheckBox("Incrustar metadatos (título, artista, fecha, descripción…)")
        self.embed_metadata.setChecked(cfg["embed_metadata"])
        self.embed_thumbnail = QCheckBox("Incrustar carátula / miniatura en el archivo")
        self.embed_thumbnail.setChecked(cfg["embed_thumbnail"])
        self.square_thumbnail = QCheckBox("Recortar la carátula a cuadrado (estilo álbum)")
        self.square_thumbnail.setChecked(playlist)
        self.write_thumbnail = QCheckBox("Guardar la miniatura como imagen aparte (.jpg)")
        self.parse_artist_title = QCheckBox("Detectar «Artista - Título» en el nombre y limpiar «(Official Video)»")
        self.parse_artist_title.setChecked(playlist)
        self.write_description = QCheckBox("Guardar la descripción (.description)")
        self.write_info_json = QCheckBox("Guardar toda la información en JSON (.info.json)")
        self.write_comments = QCheckBox("Descargar los comentarios (dentro del .info.json, puede tardar)")
        for cb in (self.embed_metadata, self.embed_thumbnail, self.square_thumbnail, self.write_thumbnail,
                   self.parse_artist_title, self.write_description, self.write_info_json, self.write_comments):
            lay.addWidget(cb)
        self.album_from_playlist = QCheckBox("Usar el nombre de la playlist como álbum y su posición como nº de pista")
        self.album_from_playlist.setChecked(playlist)
        self.album_from_playlist.setVisible(playlist)
        lay.addWidget(self.album_from_playlist)
        self.embed_thumbnail.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Metadatos y carátula")

        # ================= Subtítulos =================
        w, lay = _tab()
        self.subs = QCheckBox("Descargar subtítulos")
        lay.addWidget(self.subs)
        self.sub_langs = QLineEdit("es,en")
        self.sub_langs.setPlaceholderText("es,en  ·  es.*  ·  all")
        self.sub_format = combo(SUB_FORMATS, "srt")
        lay.addWidget(row(field("Idiomas (separados por coma, admite regex)", self.sub_langs),
                          field("Formato", self.sub_format)))
        self.auto_subs = QCheckBox("Incluir subtítulos generados automáticamente")
        self.embed_subs = QCheckBox("Incrustar los subtítulos dentro del video")
        self.embed_subs.setChecked(True)
        self.keep_sub_files = QCheckBox("Conservar también los archivos de subtítulos")
        for cb in (self.auto_subs, self.embed_subs, self.keep_sub_files):
            lay.addWidget(cb)
        self.subs.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Subtítulos")

        # ================= Capítulos / SponsorBlock / Fragmento =================
        w, lay = _tab()
        self.embed_chapters = QCheckBox("Incrustar capítulos")
        self.embed_chapters.setChecked(True)
        self.split_chapters = QCheckBox("Dividir en un archivo por capítulo (ideal para álbumes completos)")
        lay.addWidget(self.embed_chapters)
        lay.addWidget(self.split_chapters)
        lay.addWidget(label("SponsorBlock", "SectionTitle"))
        self.sponsorblock = Segmented([("Desactivado", "none"), ("Marcar como capítulos", "mark"),
                                       ("Eliminar segmentos", "remove")], "none")
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
        if not playlist:
            lay.addWidget(label("Descargar solo un fragmento", "SectionTitle"))
            self.section = QCheckBox("Descargar solo una parte del video")
            self.section_start = QLineEdit()
            self.section_start.setPlaceholderText("Inicio: 0:30")
            self.section_end = QLineEdit()
            self.section_end.setPlaceholderText("Fin: 2:15 (vacío = hasta el final)")
            self.precise_cut = QCheckBox("Corte preciso (recodifica en los puntos de corte, más lento)")
            lay.addWidget(self.section)
            lay.addWidget(row(self.section_start, self.section_end))
            lay.addWidget(self.precise_cut)
            self.section.toggled.connect(self._update_enabled)
        lay.addStretch(1)
        self.tabs.addTab(w, "Capítulos y SponsorBlock")

        # ================= Salida / Avanzado =================
        w, lay = _tab()
        self.output_dir = PathPicker("dir", cfg["music_dir"] if playlist else cfg["output_dir"])
        lay.addWidget(field("Carpeta de destino", self.output_dir))
        self.template = QComboBox()
        self.template.setEditable(True)
        for text, t in TEMPLATE_PRESETS:
            self.template.addItem(f"{text}   ·   {t}", t)
        default_t = cfg["playlist_template"] if playlist else cfg["filename_template"]
        self.template.setEditText(default_t)
        self.template.activated.connect(lambda i: self.template.setEditText(self.template.itemData(i)))
        self.adv_template = field("Plantilla de nombre de archivo", self.template,
                            "Variables: %(title)s, %(uploader)s, %(upload_date)s, %(id)s, %(playlist_title)s, "
                            "%(playlist_index)02d, %(artist)s, %(album)s, %(resolution)s, %(ext)s… "
                            "Usa «/» para crear subcarpetas.")
        lay.addWidget(self.adv_template)
        self.adv.append(self.adv_template)
        self.restrict_filenames = QCheckBox("Nombres de archivo simples (sin espacios ni caracteres especiales)")
        self.restrict_filenames.setChecked(cfg["restrict_filenames"])
        self.no_overwrite = QCheckBox("No sobrescribir archivos existentes")
        self.no_overwrite.setChecked(True)
        lay.addWidget(self.restrict_filenames)
        lay.addWidget(self.no_overwrite)
        self.adv += [self.restrict_filenames, self.no_overwrite]
        if playlist:
            self.use_archive = QCheckBox("Recordar lo descargado y saltarlo la próxima vez (ideal para sincronizar playlists)")
            self.use_archive.setChecked(cfg["use_archive"])
            self.playlist_reverse = QCheckBox("Descargar en orden inverso")
            lay.addWidget(self.use_archive)
            lay.addWidget(self.playlist_reverse)
            filt_lbl = label("Filtros", "SectionTitle")
            lay.addWidget(filt_lbl)
            self.min_duration = QLineEdit()
            self.min_duration.setPlaceholderText("Duración mínima (ej. 1:00)")
            self.max_duration = QLineEdit()
            self.max_duration.setPlaceholderText("Duración máxima (ej. 10:00)")
            self.title_filter = QLineEdit()
            self.title_filter.setPlaceholderText("Solo títulos que contengan… (regex)")
            dur_row = row(self.min_duration, self.max_duration)
            lay.addWidget(dur_row)
            lay.addWidget(self.title_filter)
            self.adv += [self.playlist_reverse, filt_lbl, dur_row, self.title_filter]
        else:
            self.noplaylist = QCheckBox("Si el enlace incluye una playlist, descargar solo este video")
            self.noplaylist.setChecked(True)
            lay.addWidget(self.noplaylist)
            self.adv.append(self.noplaylist)
        lay.addStretch(1)
        self.tabs.addTab(w, "Salida y avanzado")

        self._update_enabled()

    # ------------------------------------------------------------------
    def _update_enabled(self, *_):
        mode = self.mode.value()
        video = mode in ("av", "video", "custom")
        self.quality.setEnabled(mode in ("av", "video"))
        self.vcodec.setEnabled(mode in ("av", "video"))
        self.fps.setEnabled(mode in ("av", "video"))
        self.container.setEnabled(video)
        self.audio_format.setEnabled(mode == "audio")
        self.audio_quality.setEnabled(mode == "audio")
        self.custom_field.setVisible(mode == "custom")
        self.square_thumbnail.setEnabled(self.embed_thumbnail.isChecked() or self.write_thumbnail.isChecked())
        subs = self.subs.isChecked()
        for wdg in (self.sub_langs, self.sub_format, self.auto_subs, self.embed_subs, self.keep_sub_files):
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

    def set_simple(self, simple):
        """Modo simple: solo calidad, formato y carpeta. Lo oculto conserva sus valores por defecto."""
        for w in self.adv:
            w.setVisible(not simple)
        self.simple = simple
        for key in ("video", "custom"):
            self.mode.set_key_visible(key, not simple)
        if simple and self.mode.value() in ("video", "custom"):
            self.set_mode("av")
        # Pestañas: 0 Formato, 1 Metadatos, 2 Subtítulos, 3 Capítulos, 4 Salida
        for i in (1, 2, 3):
            self.tabs.setTabVisible(i, not simple)
        self.tabs.setTabText(4, "Carpeta de destino" if simple else "Salida y avanzado")
        self.tabs.setMaximumHeight(240 if simple else 16777215)
        if simple and self.tabs.currentIndex() in (1, 2, 3):
            self.tabs.setCurrentIndex(0)

    def set_mode(self, mode):
        self.mode.set_value(mode)
        self._update_enabled()

    def set_format_string(self, s):
        self.format_string.setText(s)
        self.set_mode("custom")
        self.tabs.setCurrentIndex(0)

    def values(self):
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
            "subs": self.subs.isChecked(),
            "sub_langs": self.sub_langs.text(),
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
        if getattr(self, "simple", False):
            # En modo simple, lo que no se ve no se aplica: se usan los valores predeterminados.
            v.update({
                "vcodec": "any", "fps": "any", "keep_video": False,
                "embed_metadata": cfg["embed_metadata"], "embed_thumbnail": cfg["embed_thumbnail"],
                "square_thumbnail": self.playlist, "parse_artist_title": self.playlist,
                "album_from_playlist": self.playlist, "write_thumbnail": False,
                "write_description": False, "write_info_json": False, "write_comments": False,
                "subs": False, "split_chapters": False, "embed_chapters": True, "sponsorblock": "none",
                "template": cfg["playlist_template"] if self.playlist else cfg["filename_template"],
                "restrict_filenames": cfg["restrict_filenames"], "no_overwrite": True,
            })
            if self.playlist:
                v.update({"playlist_reverse": False, "min_duration": "", "max_duration": "", "title_filter": "",
                          "use_archive": self.use_archive.isChecked()})
            else:
                v.update({"noplaylist": True, "section": False})
        return v

    def summary(self):
        v = self.values()
        if v["mode"] == "audio":
            return f"Audio {self.audio_format.currentText()} · {self.audio_quality.currentText()}"
        if v["mode"] == "custom":
            return f"Formato {v['format_string'] or '—'}"
        q = self.quality.currentText().split(" (")[0]
        return f"{'Video' if v['mode'] == 'video' else 'Video + audio'} {q} · {v['container'].upper()}"
