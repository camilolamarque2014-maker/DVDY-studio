"""Página «Buscar»: busca en YouTube / YouTube Music / SoundCloud y descarga con un clic."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QSpinBox, QVBoxLayout, QWidget

from .tasks import DownloadTask
from .utils import best_thumbnail_url, fmt_count, fmt_time
from .widgets import Page, button, combo, label, load_thumbnail, row, run_async, thumb_label
from .ytopts import build_opts, default_choices, info_opts

SOURCES = [("YouTube", "ytsearch"), ("YouTube (más recientes)", "ytsearchdate"),
           ("YouTube Music", "ytmusic"), ("SoundCloud", "scsearch")]


def _search(prefix, query, n):
    import yt_dlp
    o = info_opts(flat=True)
    if prefix == "ytmusic":
        from urllib.parse import quote
        url = f"https://music.youtube.com/search?q={quote(query)}#songs"
    else:
        url = f"{prefix}{n}:{query}"
    with yt_dlp.YoutubeDL(o) as ydl:
        info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    return [e for e in (info.get("entries") or []) if e][:n]


class ResultCard(QFrame):
    def __init__(self, entry, page):
        super().__init__()
        self.setObjectName("Card")
        self.entry = entry
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 12, 10)
        lay.setSpacing(14)
        th = thumb_label(160, 90)
        lay.addWidget(th)
        load_thumbnail(best_thumbnail_url(entry), th, (160, 90))
        mid = QVBoxLayout()
        mid.setSpacing(3)
        t = label(entry.get("title") or "?", "SectionTitle", wrap=True)
        mid.addWidget(t)
        meta = [entry.get("channel") or entry.get("uploader") or "", fmt_time(entry.get("duration")) if entry.get("duration") else ""]
        if entry.get("view_count"):
            meta.append(f"{fmt_count(entry['view_count'])} vistas")
        mid.addWidget(label("  ·  ".join(m for m in meta if m), "Muted"))
        mid.addStretch(1)
        url = entry.get("webpage_url") or entry.get("url")
        self.url = url
        mid.addWidget(row(button("Video", lambda: page.quick(url, entry, False)),
                          button("Audio", lambda: page.quick(url, entry, True)),
                          button("Opciones…", lambda: page.open_download.emit(url), flat=True), None))
        lay.addLayout(mid, 1)


class SearchPage(Page):
    open_download = Signal(str)

    def __init__(self, manager, go_queue):
        super().__init__("Buscar", "Busca sin salir de la app y descarga con la configuración predeterminada de Ajustes.")
        self.manager = manager
        self.go_queue = go_queue
        self.query = QLineEdit()
        self.query.setObjectName("UrlInput")
        self.query.setPlaceholderText("¿Qué quieres buscar?")
        self.query.returnPressed.connect(self.search)
        self.source = combo(SOURCES)
        self.count = QSpinBox()
        self.count.setRange(5, 50)
        self.count.setValue(15)
        self.count.setPrefix("Resultados: ")
        self.btn = button("Buscar", self.search, primary=True)
        self.add(row(self.query, self.source, self.count, self.btn))
        self.status = label("", "Hint")
        self.add(self.status)
        self.results = QWidget()
        self.rl = QVBoxLayout(self.results)
        self.rl.setContentsMargins(0, 0, 0, 0)
        self.rl.setSpacing(8)
        self.add(self.results)
        self.body.addStretch(1)

    def search(self):
        q = self.query.text().strip()
        if not q:
            return
        self.btn.setEnabled(False)
        self.status.setText("Buscando…")
        run_async(_search, self.source.currentData(), q, self.count.value(),
                  on_done=self._show, on_error=self._err)

    def _err(self, msg):
        self.btn.setEnabled(True)
        self.status.setText(f"Error: {msg}")

    def _show(self, entries):
        self.btn.setEnabled(True)
        while self.rl.count():
            w = self.rl.takeAt(0).widget()
            if w:
                w.deleteLater()
        for e in entries:
            self.rl.addWidget(ResultCard(e, self))
        self.status.setText(f"{len(entries)} resultados" if entries else "Sin resultados")

    def quick(self, url, entry, audio):
        choices = default_choices(audio)
        self.manager.add(DownloadTask(url, build_opts(choices), title=entry.get("title"),
                                      label="Audio" if audio else "Video"))
        self.status.setText(f"Añadido a la cola: {entry.get('title')}")
