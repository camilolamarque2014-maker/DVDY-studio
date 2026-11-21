"""Página «Playlists y música»: carga una playlist/canal/álbum, permite elegir pistas y descargarlas."""
import threading

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLineEdit, QListView, QListWidget, QListWidgetItem, QMessageBox, QVBoxLayout,
)

from .options_panel import OptionsPanel
from .tasks import DownloadTask
from .utils import best_thumbnail_url, fmt_time
from .widgets import plural, Page, button, card, label, load_thumbnail, row, run_async, thumb_label
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
    from .ytopts import extract_info
    info = extract_info(url, flat=True)
    # Algunos canales devuelven pestañas (Videos, Shorts…) como sub-playlists
    entries = list(info.get("entries") or [])
    if entries and all(e.get("_type") == "playlist" or "/videos" in (e.get("url") or "") for e in entries[:3]) \
            and info.get("extractor_key") == "YoutubeTab" and len(entries) <= 6:
        sub = extract_info(entries[0]["url"], flat=True)
        sub.setdefault("title", info.get("title"))
        return sub
    return info


COVER_W, COVER_H = 168, 94


def _cover_pixmap(data=None):
    """Tapa redondeada sin teñir; sin datos, un recuadro neutro del tema."""
    from .theme import current
    out = QPixmap(COVER_W, COVER_H)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, COVER_W, COVER_H, 6, 6)
    p.setClipPath(path)
    pm = QPixmap()
    if data and pm.loadFromData(data):
        pm = pm.scaled(COVER_W, COVER_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap(-(pm.width() - COVER_W) // 2, -(pm.height() - COVER_H) // 2, pm)
    else:
        p.fillRect(0, 0, COVER_W, COVER_H, QColor(current.get("raised", "#24242a")))
    p.end()
    return out


def _cover_icon(data=None):
    """Ícono de la tapa con la misma imagen seleccionada o no (sin el tinte de selección de Qt)."""
    pm = _cover_pixmap(data)
    icon = QIcon()
    for mode in (QIcon.Normal, QIcon.Selected, QIcon.Active):
        icon.addPixmap(pm, mode)
    return icon


class _CoverLoader(QObject):
    """Baja las tapas de la grilla de a una, en segundo plano."""
    loaded = Signal(int, int, bytes)  # generación, fila, datos

    def __init__(self):
        super().__init__()
        self.gen = 0

    def start(self, urls):
        self.gen += 1
        gen = self.gen

        def work():
            from .deps import urlopen
            for i, u in enumerate(urls):
                if gen != self.gen:
                    return
                if not u:
                    continue
                try:
                    with urlopen(u, timeout=15, user_agent="Mozilla/5.0") as r:
                        self.loaded.emit(gen, i, r.read())
                except Exception:
                    pass

        threading.Thread(target=work, daemon=True).start()


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
        self.load_btn = button("Cargar lista", self.load)
        lay.addWidget(row(self.url, button("Pegar", self.paste), self.load_btn))
        self.status = label("", "Hint")
        lay.addWidget(self.status)
        self.status.hide()
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
        ll.addWidget(label("Haz clic en una tapa para sumarla o quitarla. Las marcadas en claro son las que se bajan.", "Hint"))
        # Grilla densa de tapas: cada celda es una canción o video; la selección es lo que se baja
        self.grid = QListWidget()
        self.grid.setObjectName("Grid")
        self.grid.setViewMode(QListView.IconMode)
        self.grid.setResizeMode(QListView.Adjust)
        self.grid.setMovement(QListView.Static)
        self.grid.setWrapping(True)
        self.grid.setUniformItemSizes(True)
        self.grid.setWordWrap(True)
        self.grid.setIconSize(QSize(COVER_W, COVER_H))
        self.grid.setGridSize(QSize(COVER_W + 22, COVER_H + 64))
        self.grid.setSpacing(0)
        # Sin barra propia: la página ya se desplaza, así la barra no le roba ancho a las columnas
        self.grid.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid.setSelectionMode(QAbstractItemView.MultiSelection)
        self.grid.setAccessibleName("Canciones de la playlist")
        self.grid.itemSelectionChanged.connect(self._update_sel)
        self.grid.viewport().installEventFilter(self)
        ll.addWidget(self.grid)
        self.covers = _CoverLoader()
        self.covers.loaded.connect(self._on_cover)
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
        self.dl_btn = button("Descargar las elegidas", self.enqueue, primary=True)
        self.add(row(self.summary, None, self.dl_btn))
        self.body.addStretch(1)
        self._update_summary()

    def set_simple(self, simple):
        self.options.set_simple(simple)
        self._update_summary()

    def _say(self, text):
        self.status.setText(text)
        self.status.setVisible(bool(text))

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
        self._say("Cargando la lista… (las playlists grandes pueden tardar)")
        run_async(_extract_playlist, url, on_done=self._on_loaded, on_error=self._on_error)

    def _on_error(self, msg):
        self.load_btn.setEnabled(True)
        self._say("")
        QMessageBox.warning(self, "No se pudo cargar", msg)

    def _on_loaded(self, info):
        self.load_btn.setEnabled(True)
        self.info = info
        if info.get("_type") != "playlist":
            self.entries = [info]
        else:
            self.entries = [e for e in (info.get("entries") or []) if e]
        self._say("")
        self.pl_title.setText(info.get("title") or "Sin título")
        total = sum((e.get("duration") or 0) for e in self.entries)
        meta = [info.get("uploader") or info.get("channel") or "", plural(len(self.entries), "canción o video", "canciones o videos")]
        if total:
            meta.append(f"duración total {fmt_time(total)}")
        self.pl_meta.setText("  ·  ".join(m for m in meta if m))
        self.thumb.clear()
        thumb = best_thumbnail_url(info) or (best_thumbnail_url(self.entries[0]) if self.entries else None)
        load_thumbnail(thumb, self.thumb, (160, 90))
        self.grid.blockSignals(True)
        self.grid.clear()
        blank = _cover_icon()
        urls = []
        for i, e in enumerate(self.entries, 1):
            title = e.get("title") or e.get("id") or "?"
            who = e.get("channel") or e.get("uploader") or ""
            dur = fmt_time(e.get("duration")) if e.get("duration") else ""
            it = QListWidgetItem(blank, f"{i}. {title}" + (f"\n{dur}" if dur else ""))
            it.setData(Qt.UserRole, i)
            it.setData(Qt.UserRole + 1, (title + " " + who).lower())
            it.setToolTip(f"{title}\n{who}  {dur}".strip())
            it.setSizeHint(QSize(COVER_W + 18, COVER_H + 60))
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.grid.addItem(it)
            unavailable = title.startswith("[") and "video" in title.lower()
            it.setSelected(not unavailable)
            urls.append(best_thumbnail_url(e))
        self.grid.blockSignals(False)
        self.covers.start(urls)
        self._update_sel()
        self.list_card.show()
        self._fit_grid()

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.grid.viewport() and ev.type() == QEvent.Resize:
            self._fit_grid()
        return super().eventFilter(obj, ev)

    def _fit_grid(self):
        """Reparte el ancho entre las columnas para que la grilla llene la fila sin hueco a la derecha."""
        w = self.grid.viewport().width() - 2
        cols = max(1, w // (COVER_W + 22))
        cell = (w - 1) // cols
        self.grid.setGridSize(QSize(cell, COVER_H + 64))
        for it in self._items():
            it.setSizeHint(QSize(cell - 4, COVER_H + 60))
        rows = max(1, -(-sum(1 for it in self._items() if not it.isHidden()) // cols))
        self.grid.setFixedHeight(rows * (COVER_H + 64) + 8)

    def _on_cover(self, gen, row, data):
        if gen != self.covers.gen:
            return
        it = self.grid.item(row)
        if it is not None:
            it.setIcon(_cover_icon(data))

    def _items(self):
        return [self.grid.item(i) for i in range(self.grid.count())]

    def _check_all(self, on):
        self.grid.blockSignals(True)
        for it in self._items():
            if not it.isHidden():
                it.setSelected(on)
        self.grid.blockSignals(False)
        self._update_sel()

    def _invert(self):
        self.grid.blockSignals(True)
        for it in self._items():
            if not it.isHidden():
                it.setSelected(not it.isSelected())
        self.grid.blockSignals(False)
        self._update_sel()

    def _apply_filter(self, text):
        text = text.lower().strip()
        for it in self._items():
            it.setHidden(bool(text) and text not in (it.data(Qt.UserRole + 1) or ""))

    def _selected_indices(self):
        return sorted(it.data(Qt.UserRole) for it in self._items() if it.isSelected())

    def _update_sel(self, *_):
        n = len(self._selected_indices())
        self.sel_lbl.setText(f"{n} de {self.grid.count()} elegidas")

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
        kind = "Playlist de música" if choices["mode"] == "audio" else "Playlist de videos"
        thumb = best_thumbnail_url(self.info or {}) or (best_thumbnail_url(self.entries[0]) if self.entries else "")
        self.manager.add(DownloadTask(url, opts, title=title, label=kind, thumb=thumb or ""))
        self.go_queue()
