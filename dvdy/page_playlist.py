"""Página «Playlists y música»: carga una playlist/canal/álbum, permite elegir pistas y descargarlas."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .options_panel import OptionsPanel
from .tasks import DownloadTask
from .utils import best_thumbnail_url, fmt_time
from .widgets import Page, button, card, label, load_thumbnail, row, run_async, thumb_label
from .ytopts import build_opts, info_opts


def normalize_playlist_url(url):
    """'watch?v=X&list=Y' -> 'playlist?list=Y' para que se cargue la lista completa."""
    from urllib.parse import parse_qs, urlparse
    u = urlparse(url)
    if "youtube.com" in u.netloc and u.path == "/watch":
        lst = parse_qs(u.query).get("list")
        if lst and not lst[0].startswith("RD"):  # los mixes (RD…) solo funcionan como watch?v=…&list=…
            host = "music.youtube.com" if u.netloc.startswith("music.") else "www.youtube.com"
            return f"https://{host}/playlist?list={lst[0]}"
    return url


def _extract_playlist(url):
    import yt_dlp
    url = normalize_playlist_url(url)
    o = info_opts(flat=True)
    with yt_dlp.YoutubeDL(o) as ydl:
        info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    # Algunos canales devuelven pestañas (Videos, Shorts…) como sub-playlists
    entries = list(info.get("entries") or [])
    if entries and all(e.get("_type") == "playlist" or "/videos" in (e.get("url") or "") for e in entries[:3]) \
            and info.get("extractor_key") == "YoutubeTab" and len(entries) <= 6:
        with yt_dlp.YoutubeDL(o) as ydl:
            sub = ydl.sanitize_info(ydl.extract_info(entries[0]["url"], download=False))
        sub.setdefault("title", info.get("title"))
        return sub
    return info


class PlaylistPage(Page):
    def __init__(self, manager, go_queue):
        super().__init__("Playlists y música",
                         "Descarga playlists, álbumes, canales o mixes completos, eligiendo pistas, metadatos y carátulas.")
        self.manager = manager
        self.go_queue = go_queue
        self.info = None
        self.entries = []

        c, lay = card()
        self.url = QLineEdit()
        self.url.setObjectName("UrlInput")
        self.url.setPlaceholderText("Enlace de playlist, álbum de YouTube Music, canal o mix…")
        self.url.returnPressed.connect(self.load)
        self.load_btn = button("Cargar", self.load, primary=True)
        lay.addWidget(row(self.url, button("Pegar", self.paste), self.load_btn))
        self.status = label("", "Hint")
        lay.addWidget(self.status)
        self.add(c)

        # ---- Contenido de la playlist ----
        self.list_card, ll = card()
        head = QHBoxLayout()
        head.setSpacing(14)
        self.thumb = thumb_label(160, 90)
        head.addWidget(self.thumb, 0, Qt.AlignTop)
        hv = QVBoxLayout()
        self.pl_title = label("", "Big", wrap=True)
        self.pl_meta = label("", "Muted", wrap=True)
        hv.addWidget(self.pl_title)
        hv.addWidget(self.pl_meta)
        hv.addStretch(1)
        head.addLayout(hv, 1)
        ll.addLayout(head)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrar por título…")
        self.filter.textChanged.connect(self._apply_filter)
        self.sel_lbl = label("", "Muted")
        ll.addWidget(row(self.filter, button("Todas", lambda: self._check_all(True)),
                         button("Ninguna", lambda: self._check_all(False)),
                         button("Invertir", self._invert), self.sel_lbl))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Título", "Canal / Artista", "Duración"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self._update_sel)
        ll.addWidget(self.table)
        self.list_card.hide()
        self.add(self.list_card)

        c, lay = card("Opciones")
        self.options = OptionsPanel(playlist=True)
        lay.addWidget(self.options)
        self.add(c)

        self.summary = label("", "Muted")
        self.options.mode.changed.connect(self._update_summary)
        self.options.audio_format.currentIndexChanged.connect(self._update_summary)
        self.options.audio_quality.currentIndexChanged.connect(self._update_summary)
        self.options.quality.currentIndexChanged.connect(self._update_summary)
        self.dl_btn = button("Descargar selección", self.enqueue, primary=True)
        self.add(row(self.summary, None, self.dl_btn))
        self.body.addStretch(1)
        self._update_summary()

    def set_simple(self, simple):
        self.options.set_simple(simple)
        self._update_summary()

    def _update_summary(self, *_):
        self.summary.setText(self.options.summary())

    def paste(self):
        t = QGuiApplication.clipboard().text().strip()
        if t:
            self.url.setText(t)
            self.load()

    def set_url(self, url):
        self.url.setText(url)
        self.load()

    def load(self):
        url = self.url.text().strip()
        if not url:
            return
        self.load_btn.setEnabled(False)
        self.status.setText("Cargando la lista… (las playlists grandes pueden tardar)")
        run_async(_extract_playlist, url, on_done=self._on_loaded, on_error=self._on_error)

    def _on_error(self, msg):
        self.load_btn.setEnabled(True)
        self.status.setText("")
        QMessageBox.warning(self, "No se pudo cargar", msg)

    def _on_loaded(self, info):
        self.load_btn.setEnabled(True)
        self.info = info
        if info.get("_type") != "playlist":
            self.entries = [info]
        else:
            self.entries = [e for e in (info.get("entries") or []) if e]
        self.status.setText(f"{len(self.entries)} elementos cargados")
        self.pl_title.setText(info.get("title") or "Sin título")
        total = sum((e.get("duration") or 0) for e in self.entries)
        meta = [info.get("uploader") or info.get("channel") or "", f"{len(self.entries)} elementos"]
        if total:
            meta.append(f"duración total {fmt_time(total)}")
        self.pl_meta.setText("  ·  ".join(m for m in meta if m))
        self.thumb.clear()
        thumb = best_thumbnail_url(info) or (best_thumbnail_url(self.entries[0]) if self.entries else None)
        load_thumbnail(thumb, self.thumb, (160, 90))
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for i, e in enumerate(self.entries, 1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            num = QTableWidgetItem(str(i))
            num.setFlags(num.flags() | Qt.ItemIsUserCheckable)
            num.setCheckState(Qt.Checked)
            num.setData(Qt.UserRole, i)
            unavailable = (e.get("title") or "").startswith("[") and "video" in (e.get("title") or "").lower()
            self.table.setItem(r, 0, num)
            self.table.setItem(r, 1, QTableWidgetItem(e.get("title") or e.get("id") or "?"))
            self.table.setItem(r, 2, QTableWidgetItem(e.get("channel") or e.get("uploader") or ""))
            self.table.setItem(r, 3, QTableWidgetItem(fmt_time(e.get("duration")) if e.get("duration") else ""))
            if unavailable:
                num.setCheckState(Qt.Unchecked)
        self.table.blockSignals(False)
        self._update_sel()
        self.list_card.show()

    def _rows(self):
        return range(self.table.rowCount())

    def _check_all(self, on):
        self.table.blockSignals(True)
        for r in self._rows():
            if not self.table.isRowHidden(r):
                self.table.item(r, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.table.blockSignals(False)
        self._update_sel()

    def _invert(self):
        self.table.blockSignals(True)
        for r in self._rows():
            if not self.table.isRowHidden(r):
                it = self.table.item(r, 0)
                it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
        self.table.blockSignals(False)
        self._update_sel()

    def _apply_filter(self, text):
        text = text.lower().strip()
        for r in self._rows():
            t = (self.table.item(r, 1).text() + " " + self.table.item(r, 2).text()).lower()
            self.table.setRowHidden(r, bool(text) and text not in t)

    def _selected_indices(self):
        return [self.table.item(r, 0).data(Qt.UserRole) for r in self._rows()
                if self.table.item(r, 0).checkState() == Qt.Checked]

    def _update_sel(self, *_):
        n = len(self._selected_indices())
        self.sel_lbl.setText(f"{n} de {self.table.rowCount()} seleccionadas")

    @staticmethod
    def _compress(indices):
        """[1,2,3,5,7,8] -> '1-3,5,7-8'"""
        out, start, prev = [], None, None
        for i in indices:
            if start is None:
                start = prev = i
            elif i == prev + 1:
                prev = i
            else:
                out.append(f"{start}-{prev}" if start != prev else str(start))
                start = prev = i
        if start is not None:
            out.append(f"{start}-{prev}" if start != prev else str(start))
        return ",".join(out)

    def enqueue(self):
        url = normalize_playlist_url(self.url.text().strip())
        if not url:
            return
        choices = self.options.values()
        if self.entries and self.info and self.info.get("_type") == "playlist":
            idx = self._selected_indices()
            if not idx:
                QMessageBox.information(self, "Nada seleccionado", "Marca al menos una pista.")
                return
            if len(idx) != len(self.entries):
                choices["playlist_items"] = self._compress(idx)
        if choices["mode"] == "custom" and not choices["format_string"]:
            QMessageBox.warning(self, "Falta el formato", "Escribe un código de formato en la pestaña Formato.")
            return
        try:
            opts = build_opts(choices)
        except ValueError as e:
            QMessageBox.warning(self, "Opciones no válidas", str(e))
            return
        title = (self.info or {}).get("title") or url
        kind = "Playlist (audio)" if choices["mode"] == "audio" else "Playlist (video)"
        self.manager.add(DownloadTask(url, opts, title=title, label=kind))
        self.go_queue()
