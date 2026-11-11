"""Página «Descargar»: análisis de un enlace, tabla de formatos y opciones completas."""
import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QMenu, QMessageBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .options_panel import OptionsPanel
from .tasks import DownloadTask
from .utils import best_thumbnail_url, fmt_count, fmt_size, fmt_time
from .widgets import Page, button, card, label, load_thumbnail, row, run_async, thumb_label
from .ytopts import build_opts, info_opts


def _extract_info(url):
    import yt_dlp
    o = info_opts()
    o["noplaylist"] = True
    with yt_dlp.YoutubeDL(o) as ydl:
        return ydl.sanitize_info(ydl.extract_info(url, download=False))


class _NumItem(QTableWidgetItem):
    def __init__(self, text, value):
        super().__init__(text)
        self.value = value if value is not None else -1

    def __lt__(self, other):
        if isinstance(other, _NumItem):
            return self.value < other.value
        return super().__lt__(other)


class DownloadPage(Page):
    open_playlist = Signal(str)

    def __init__(self, manager, go_queue):
        super().__init__("Descargar", "Videos, audio y fragmentos desde YouTube y más de 1800 sitios compatibles.")
        self.manager = manager
        self.go_queue = go_queue
        self.info = None

        # ---- URL ----
        c, lay = card()
        self.urls = QPlainTextEdit()
        self.urls.setObjectName("UrlInput")
        self.urls.setPlaceholderText("Pega uno o varios enlaces (uno por línea)…")
        self.urls.setFixedHeight(72)
        lay.addWidget(self.urls)
        self.analyze_btn = button("Analizar enlace", self.analyze)
        self.status = label("", "Hint")
        lay.addWidget(row(button("Pegar", self.paste), self.analyze_btn, self.status, None,
                          button("Limpiar", self.clear_info, flat=True)))
        self.add(c)

        # ---- Información del video ----
        self.info_card, il = card()
        top = QHBoxLayout()
        top.setSpacing(16)
        self.thumb = thumb_label(256, 144)
        top.addWidget(self.thumb, 0, Qt.AlignTop)
        meta = QVBoxLayout()
        meta.setSpacing(4)
        self.title_lbl = label("", "Big", wrap=True)
        self.meta_lbl = label("", "Muted", wrap=True)
        self.extra_lbl = label("", "Hint", wrap=True)
        self.playlist_hint = button("Este enlace pertenece a una playlist → abrir en Playlists", flat=True)
        self.playlist_hint.clicked.connect(lambda: self.open_playlist.emit(self.first_url()))
        self.playlist_hint.hide()
        meta.addWidget(self.title_lbl)
        meta.addWidget(self.meta_lbl)
        meta.addWidget(self.extra_lbl)
        meta.addWidget(self.playlist_hint, 0, Qt.AlignLeft)
        meta.addStretch(1)
        top.addLayout(meta, 1)
        il.addLayout(top)

        self.formats_box = QWidget()
        fl = QVBoxLayout(self.formats_box)
        fl.setContentsMargins(0, 6, 0, 0)
        fl.setSpacing(10)
        il.addWidget(self.formats_box)
        fl.addWidget(label("Formatos disponibles", "SectionTitle"))
        fl.addWidget(label("Selecciona un formato de video y uno de audio (Ctrl+clic) y pulsa «Usar selección». "
                           "Haz clic en los encabezados para ordenar.", "Hint", wrap=True))
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["ID", "Ext.", "Resolución", "FPS", "Video", "Audio",
                                              "Tamaño", "Kbps", "Nota"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setMinimumHeight(260)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.use_selected_formats)
        fl.addWidget(self.table)
        fl.addWidget(row(button("Usar selección", self.use_selected_formats),
                         button("Copiar enlace directo", self.copy_stream_url,
                                tooltip="Copia la URL del stream del formato seleccionado"),
                         None))
        self.info_card.hide()
        self.add(self.info_card)

        # ---- Opciones ----
        c, lay = card("Opciones")
        self.options = OptionsPanel(playlist=False)
        lay.addWidget(self.options)
        self.add(c)

        # ---- Acciones ----
        more = QToolButton()
        more.setText("Más acciones  ▾")
        more.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(more)
        m.addAction("Descargar solo la miniatura", self.download_thumbnail_only)
        m.addAction("Descargar solo los subtítulos", self.download_subs_only)
        m.addAction("Guardar la información (JSON)…", self.save_info_json)
        m.addAction("Copiar el título", lambda: self.info and QGuiApplication.clipboard().setText(self.info.get("title", "")))
        more.setMenu(m)
        self.more_btn = more
        self.summary_lbl = label("", "Muted")
        self.options.mode.changed.connect(self._update_summary)
        self.options.quality.currentIndexChanged.connect(self._update_summary)
        self.options.audio_format.currentIndexChanged.connect(self._update_summary)
        self.options.container.currentIndexChanged.connect(self._update_summary)
        self.add(row(self.summary_lbl, None, more, button("Añadir a la cola y descargar", self.enqueue, primary=True)))
        self.body.addStretch(1)
        self._update_summary()

    # ------------------------------------------------------------------
    def set_simple(self, simple):
        self.formats_box.setVisible(not simple)
        self.more_btn.setVisible(not simple)
        self.options.set_simple(simple)
        self._update_summary()

    def _update_summary(self, *_):
        self.summary_lbl.setText(self.options.summary())

    def urls_list(self):
        return [u.strip() for u in self.urls.toPlainText().splitlines() if u.strip()]

    def first_url(self):
        l = self.urls_list()
        return l[0] if l else ""

    def set_url(self, url, analyze=True):
        self.urls.setPlainText(url)
        if analyze:
            self.analyze()

    def paste(self):
        t = QGuiApplication.clipboard().text().strip()
        if t:
            self.urls.setPlainText(t)
            self.analyze()

    def clear_info(self):
        self.info = None
        self.info_card.hide()
        self.urls.clear()
        self.status.setText("")

    def analyze(self):
        url = self.first_url()
        if not url:
            self.status.setText("Pega un enlace primero.")
            return
        self.analyze_btn.setEnabled(False)
        self.status.setText("Analizando…")
        self.playlist_hint.setVisible("list=" in url or "/playlist" in url)
        run_async(_extract_info, url, on_done=self._on_info, on_error=self._on_error)

    def _on_error(self, msg):
        self.analyze_btn.setEnabled(True)
        self.status.setText("")
        QMessageBox.warning(self, "No se pudo analizar", msg)

    def _on_info(self, info):
        self.analyze_btn.setEnabled(True)
        self.info = info
        if info.get("_type") == "playlist":
            self.status.setText("Es una playlist")
            self.open_playlist.emit(self.first_url())
            return
        self.status.setText("Listo")
        self.title_lbl.setText(info.get("title") or "")
        parts = [info.get("uploader") or info.get("channel") or "", fmt_time(info.get("duration"))]
        if info.get("view_count"):
            parts.append(f"{fmt_count(info['view_count'])} vistas")
        d = info.get("upload_date")
        if d and len(d) == 8:
            parts.append(f"{d[6:]}/{d[4:6]}/{d[:4]}")
        self.meta_lbl.setText("  ·  ".join(p for p in parts if p))
        extra = []
        if info.get("chapters"):
            extra.append(f"{len(info['chapters'])} capítulos")
        subs = list((info.get("subtitles") or {}).keys())
        if subs:
            extra.append("Subtítulos: " + ", ".join(subs[:12]) + ("…" if len(subs) > 12 else ""))
        if info.get("automatic_captions"):
            extra.append("Subtítulos automáticos disponibles")
        if info.get("extractor_key"):
            extra.append(f"Sitio: {info['extractor_key']}")
        self.extra_lbl.setText("   ·   ".join(extra))
        self.thumb.clear()
        load_thumbnail(best_thumbnail_url(info), self.thumb, (256, 144))
        self._fill_formats(info.get("formats") or [])
        self.info_card.show()

    def _fill_formats(self, formats):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for f in reversed(formats):
            if f.get("format_note") == "storyboard" or f.get("ext") == "mhtml":
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            vc = f.get("vcodec") or ""
            ac = f.get("acodec") or ""
            size = f.get("filesize") or f.get("filesize_approx")
            height = f.get("height") or 0
            res = f.get("resolution") or ("audio" if vc == "none" else "")
            items = [
                QTableWidgetItem(str(f.get("format_id"))),
                QTableWidgetItem(f.get("ext") or ""),
                _NumItem(res, height if vc != "none" else -1),
                _NumItem(str(int(f["fps"])) if f.get("fps") else "", f.get("fps") or 0),
                QTableWidgetItem("—" if vc == "none" else vc.split(".")[0]),
                QTableWidgetItem("—" if ac == "none" else ac.split(".")[0]),
                _NumItem(("~" if not f.get("filesize") and size else "") + fmt_size(size) if size else "", size or 0),
                _NumItem(f"{f['tbr']:.0f}" if f.get("tbr") else "", f.get("tbr") or 0),
                QTableWidgetItem(f.get("format_note") or f.get("format") or ""),
            ]
            items[0].setData(Qt.UserRole, f)
            for col, it in enumerate(items):
                self.table.setItem(r, col, it)
        self.table.setSortingEnabled(True)

    def _selected_formats(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows]

    def use_selected_formats(self, *_):
        fmts = self._selected_formats()
        if not fmts:
            return
        videos = [f for f in fmts if (f.get("vcodec") or "none") != "none"]
        audios = [f for f in fmts if (f.get("vcodec") or "none") == "none"]
        ordered = videos + audios
        self.options.set_format_string("+".join(str(f["format_id"]) for f in ordered))
        self._update_summary()

    def copy_stream_url(self):
        fmts = self._selected_formats()
        if fmts and fmts[0].get("url"):
            QGuiApplication.clipboard().setText(fmts[0]["url"])
            self.status.setText("Enlace directo copiado al portapapeles")

    # ------------------------------------------------------------------
    def _make_task(self, url, choices, label_kind):
        opts = build_opts(choices)
        title = None
        if self.info and url == self.first_url() and self.info.get("title"):
            title = self.info["title"]
        return DownloadTask(url, opts, title=title, label=label_kind)

    def enqueue(self):
        urls = self.urls_list()
        if not urls:
            QMessageBox.information(self, "Falta el enlace", "Pega al menos un enlace para descargar.")
            return
        try:
            choices = self.options.values()
            if choices["mode"] == "custom" and not choices["format_string"]:
                raise ValueError("Escribe un código de formato o selecciónalo en la tabla de formatos.")
            build_opts(choices)  # valida
        except ValueError as e:
            QMessageBox.warning(self, "Opciones no válidas", str(e))
            return
        kind = {"audio": "Audio", "video": "Video (sin audio)"}.get(choices["mode"], "Video")
        for u in urls:
            self.manager.add(self._make_task(u, choices, kind))
        self.go_queue()

    def download_thumbnail_only(self):
        self._special({"embed_thumbnail": False, "write_thumbnail": True, "skip_download": True,
                       "embed_metadata": False, "subs": False}, "Miniatura")

    def download_subs_only(self):
        self._special({"subs": True, "embed_subs": False, "skip_download": True, "embed_thumbnail": False,
                       "embed_metadata": False}, "Subtítulos")

    def _special(self, overrides, kind):
        urls = self.urls_list()
        if not urls:
            return
        choices = self.options.values()
        choices.update(overrides)
        choices["mode"] = "av"
        for u in urls:
            self.manager.add(self._make_task(u, choices, kind))
        self.go_queue()

    def save_info_json(self):
        if not self.info:
            QMessageBox.information(self, "Sin información", "Analiza un enlace primero.")
            return
        name = "".join(ch for ch in (self.info.get("title") or "info") if ch not in '\\/:*?"<>|')[:120]
        path, _ = QFileDialog.getSaveFileName(self, "Guardar información",
                                              os.path.join(self.options.output_dir.path(), name + ".info.json"),
                                              "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.info, f, ensure_ascii=False, indent=2)
            self.status.setText("Información guardada")
