"""Pantalla «Descargar»: el panel de descarga a la izquierda y el dial (la cola) a la derecha.

Flujo: pegar el enlace (se analiza solo), elegir Video o Música, revisar las cuatro casillas
y presionar Descargar (o Enter). En modo Avanzado se suman la tabla de formatos y las
acciones especiales (solo miniatura, solo subtítulos, guardar información).
"""
import json
import os
import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox,
    QPlainTextEdit, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .errors import friendly
from .options_panel import OptionsPanel
from .page_queue import DialPanel
from .tasks import DownloadTask
from .utils import best_thumbnail_url, fmt_count, fmt_size, fmt_time
from .widgets import button, label, load_thumbnail, row, run_async, thumb_label
from .ytopts import build_opts

URL_RE = re.compile(r"^https?://\S+$", re.I)


def _extract_info(url):
    from .ytopts import extract_info
    return extract_info(url, noplaylist=True)


class _NumItem(QTableWidgetItem):
    def __init__(self, text, value):
        super().__init__(text)
        self.value = value if value is not None else -1

    def __lt__(self, other):
        if isinstance(other, _NumItem):
            return self.value < other.value
        return super().__lt__(other)


class UrlBox(QPlainTextEdit):
    """Campo de enlaces: Enter descarga, Mayús+Enter agrega otra línea."""
    submit = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.submit.emit()
            return
        super().keyPressEvent(e)


class DownloadPage(QWidget):
    open_playlist = Signal(str)

    def __init__(self, manager, go_queue, on_action):
        super().__init__()
        self.setObjectName("Page")
        self.manager = manager
        self.go_queue = go_queue
        self.info = None
        self._analyzed = ""
        self._pending = ""
        self.simple = False

        outer = QHBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(22)

        # ================= Columna izquierda =================
        # Un solo panel: arriba el contenido que se desplaza, abajo el pie fijo con Descargar,
        # que queda siempre a la vista aunque se despliegue todo lo de arriba.
        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        lp = QVBoxLayout(left_panel)
        lp.setContentsMargins(24, 22, 14, 18)
        lp.setSpacing(0)
        outer.addWidget(left_panel, 3)

        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("Page")
        inner.setStyleSheet("QWidget#Page { background: transparent; }")
        pl = QVBoxLayout(inner)
        pl.setContentsMargins(0, 0, 10, 8)
        pl.setSpacing(16)
        sa.setWidget(inner)
        lp.addWidget(sa, 1)

        self.urls = UrlBox()
        self.urls.setObjectName("UrlInput")
        self.urls.setPlaceholderText("Pega el enlace de un video, una canción o una playlist…")
        self.urls.setAccessibleName("Enlace para descargar")
        self.urls.setFixedHeight(54)
        self.urls.setTabChangesFocus(True)
        self.urls.submit.connect(self.enqueue)
        self.urls.textChanged.connect(self._schedule_analyze)
        paste = button("Pegar", self.paste)
        paste.setAccessibleName("Pegar el enlace copiado")
        url_row = QHBoxLayout()
        url_row.setSpacing(10)
        url_row.addWidget(self.urls, 1)
        url_row.addWidget(paste)
        pl.addLayout(url_row)

        self.status = label("", "Hint", wrap=True)
        self.playlist_link = button("Es una playlist: elegir canciones en Playlists", flat=True)
        self.playlist_link.clicked.connect(lambda: self.open_playlist.emit(self.first_url()))
        self.playlist_link.hide()
        self.status_row = row(self.status, self.playlist_link, None)
        self.status_row.hide()
        pl.addWidget(self.status_row)

        self.options = OptionsPanel(playlist=False)
        self.options.changed.connect(self._update_summary)
        pl.addWidget(self.options, 1)

        # Vista previa + Descargar (dentro del panel de opciones, encima de «Más opciones»)
        # Escenario: la tapa del enlace pegado, grande, en el espacio libre del panel
        stage = QFrame()
        stage.setObjectName("Stage")
        sl = QVBoxLayout(stage)
        sl.setContentsMargins(0, 10, 0, 6)
        sl.setSpacing(6)
        sl.addStretch(1)
        self.thumb = thumb_label(400, 225)
        self.thumb.setObjectName("Cover")
        self.thumb.setWordWrap(True)
        self.thumb.hide()  # sin enlace no hay tapa: el escenario muestra solo el texto
        sl.addWidget(self.thumb, 0, Qt.AlignHCenter)
        sl.addSpacing(8)
        self.title_lbl = QLabel("Todavía no pegaste ningún enlace")
        self.title_lbl.setObjectName("SectionTitle")
        self.title_lbl.setAlignment(Qt.AlignHCenter)
        self.title_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.meta_lbl = label("YouTube, YouTube Music, TikTok, Instagram, SoundCloud y más de 1800 sitios", "Hint")
        self.meta_lbl.setAlignment(Qt.AlignHCenter)
        self.meta_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sl.addWidget(self.title_lbl)
        sl.addWidget(self.meta_lbl)
        sl.addStretch(1)
        self.options.action_slot.addWidget(stage, 1)

        # Pie del panel: resumen de lo elegido y Descargar
        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        self.summary_lbl = label("", "Hint")
        self.summary_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        bottom.addWidget(self.summary_lbl, 1)

        self.more_actions = QToolButton()
        self.more_actions.setText("Más acciones")
        self.more_actions.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(self.more_actions)
        m.addAction("Bajar solo la miniatura", self.download_thumbnail_only)
        m.addAction("Bajar solo los subtítulos", self.download_subs_only)
        m.addAction("Guardar la información técnica (JSON)…", self.save_info_json)
        m.addAction("Copiar el título", lambda: self.info and QGuiApplication.clipboard().setText(self.info.get("title", "")))
        self.more_actions.setMenu(m)
        bottom.addWidget(self.more_actions, 0, Qt.AlignVCenter)
        self.dl_btn = button("Descargar", self.enqueue, primary=True)
        self.dl_btn.setToolTip("Descargar (Enter)")
        bottom.addWidget(self.dl_btn, 0, Qt.AlignVCenter)
        holder = QFrame()
        holder.setObjectName("PreviewRow")
        holder.setLayout(bottom)
        bottom.setContentsMargins(0, 14, 10, 0)
        lp.addWidget(holder)

        # Tabla de formatos (modo Avanzado)
        self.formats_box = QFrame()
        self.formats_box.setObjectName("PreviewRow")
        fl = QVBoxLayout(self.formats_box)
        fl.setContentsMargins(0, 16, 0, 4)
        fl.setSpacing(10)
        fl.addWidget(label("FORMATOS DISPONIBLES", "Label"))
        fl.addWidget(label("Elige un formato de video y uno de audio (Ctrl+clic) y pulsa «Usar selección». "
                           "Haz clic en los encabezados para ordenar.", "Hint", wrap=True))
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["ID", "Ext.", "Resolución", "FPS", "Video", "Audio", "Tamaño", "Kbps", "Nota"])
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
                                tooltip="Copia la dirección del archivo del formato elegido"), None))
        self.formats_box.hide()
        pl.addWidget(self.formats_box)

        # ================= Columna derecha: el dial =================
        self.dial = DialPanel(manager, on_action)
        self.dial.setMinimumWidth(380)
        self.dial.setMaximumWidth(460)
        outer.addWidget(self.dial, 2)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(600)
        self._timer.timeout.connect(self._auto_analyze)
        self._update_summary()

    # ------------------------------------------------------------------
    def set_simple(self, simple):
        self.simple = simple
        self.options.set_simple(simple)
        self.more_actions.setVisible(not simple)
        self.formats_box.setVisible(not simple and self.table.rowCount() > 0)
        self._update_summary()

    def _update_summary(self, *_):
        folder = os.path.basename(os.path.normpath(self.options.output_dir.path())) or self.options.output_dir.path()
        self.summary_lbl.setText(f"{self.options.summary()}  ·  se guarda en {folder}")

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
            self.urls.setFocus()
            self.analyze()

    # --- análisis automático ---
    def _schedule_analyze(self):
        url = self.first_url()
        if URL_RE.match(url) and url != self._analyzed:
            self._timer.start()
        elif not url:
            self._reset_preview()

    def _auto_analyze(self):
        url = self.first_url()
        if URL_RE.match(url) and url != self._analyzed:
            self.analyze()

    def _reset_preview(self):
        self.info = None
        self._analyzed = ""
        self.thumb.clear()
        self.thumb.hide()
        self.title_lbl.setText("Todavía no pegaste ningún enlace")
        self.meta_lbl.setText("YouTube, YouTube Music, TikTok, Instagram, SoundCloud y más de 1800 sitios")
        self.playlist_link.hide()
        self._say("")
        self.table.setRowCount(0)
        self.formats_box.hide()

    def analyze(self):
        url = self.first_url()
        if not url:
            return
        self._analyzed = url
        self._pending = url
        self.status.setObjectName("Hint")
        self._say("Buscando el video…")
        self._repolish(self.status)
        self.title_lbl.setText("Buscando…")
        self.meta_lbl.setText("")
        self.thumb.clear()
        self.thumb.hide()
        self.playlist_link.setVisible("list=" in url or "/playlist" in url)
        self.status_row.show()
        run_async(_extract_info, url, on_done=lambda info, u=url: self._on_info(u, info),
                  on_error=lambda msg, u=url: self._on_error(u, msg))

    def _say(self, text):
        self.status.setText(text)
        self.status_row.setVisible(bool(text) or self.playlist_link.isVisible())

    def _repolish(self, w):
        w.style().unpolish(w)
        w.style().polish(w)

    def _on_error(self, url, msg):
        if url != self._pending:
            return
        text, _ = friendly(msg)
        self.status.setObjectName("ErrText")
        self._say(text)
        self.status.setToolTip(msg)
        self._repolish(self.status)
        self.title_lbl.setText("No se pudo leer este enlace")
        self.meta_lbl.setText("Revisa el enlace o intenta de nuevo.")

    def _on_info(self, url, info):
        if url != self._pending:
            return
        self.info = info
        if info.get("_type") == "playlist":
            self._say("Es una playlist: la abro en Playlists para que elijas las canciones.")
            self.open_playlist.emit(url)
            return
        self._say("")
        self.status.setToolTip("")
        self.title_lbl.setText(info.get("title") or "")
        self.title_lbl.setToolTip(info.get("title") or "")
        parts = [info.get("uploader") or info.get("channel") or "", fmt_time(info.get("duration"))]
        if info.get("view_count"):
            parts.append(f"{fmt_count(info['view_count'])} vistas")
        if info.get("chapters"):
            parts.append(f"{len(info['chapters'])} capítulos")
        self.meta_lbl.setText("  ·  ".join(p for p in parts if p))
        self.thumb.clear()
        self.thumb.show()
        load_thumbnail(best_thumbnail_url(info), self.thumb, (400, 225))
        self.urls.setFocus()
        self._fill_formats(info.get("formats") or [])
        self.formats_box.setVisible(not self.simple and self.table.rowCount() > 0)

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
        self.options.set_format_string("+".join(str(f["format_id"]) for f in videos + audios))

    def copy_stream_url(self):
        fmts = self._selected_formats()
        if fmts and fmts[0].get("url"):
            QGuiApplication.clipboard().setText(fmts[0]["url"])
            self._say("Enlace directo copiado.")

    # ------------------------------------------------------------------
    def _make_task(self, url, choices, label_kind):
        opts = build_opts(choices)
        title, thumb = None, ""
        if self.info and url == self._analyzed:
            title = self.info.get("title")
            thumb = best_thumbnail_url(self.info) or ""
        return DownloadTask(url, opts, title=title, label=label_kind, thumb=thumb)

    def enqueue(self):
        urls = self.urls_list()
        if not urls:
            self.status.setObjectName("ErrText")
            self._say("Primero pega un enlace.")
            self._repolish(self.status)
            self.urls.setFocus()
            return
        try:
            choices = self.options.values()
            if choices["mode"] == "custom" and not choices["format_string"]:
                raise ValueError("Escribe un código de formato o elígelo en la tabla de formatos.")
            build_opts(choices)
        except ValueError as e:
            QMessageBox.warning(self, "Revisa las opciones", str(e))
            return
        kind = {"audio": "Música", "video": "Video sin sonido"}.get(choices["mode"], "Video")
        for u in urls:
            self.manager.add(self._make_task(u, choices, kind))
        self.status.setObjectName("Hint")
        self._say(f"Agregado al dial. Puedes pegar otro enlace." if len(urls) == 1
                            else f"{len(urls)} enlaces agregados al dial.")
        self._repolish(self.status)
        self.urls.clear()
        self._analyzed = ""
        self.urls.setFocus()

    def download_thumbnail_only(self):
        self._special({"embed_thumbnail": False, "write_thumbnail": True, "skip_download": True,
                       "embed_metadata": False, "subs": False}, "Miniatura")

    def download_subs_only(self):
        self._special({"subs": True, "sub_langs": self.options.values()["sub_langs"] or "es.*,es,en.*,en",
                       "embed_subs": False, "skip_download": True, "embed_thumbnail": False,
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

    def save_info_json(self):
        if not self.info:
            QMessageBox.information(self, "Falta el enlace", "Pega un enlace primero.")
            return
        name = "".join(ch for ch in (self.info.get("title") or "info") if ch not in '\\/:*?"<>|')[:120]
        path, _ = QFileDialog.getSaveFileName(self, "Guardar información",
                                              os.path.join(self.options.output_dir.path(), name + ".info.json"),
                                              "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.info, f, ensure_ascii=False, indent=2)
            self._say("Información guardada.")
