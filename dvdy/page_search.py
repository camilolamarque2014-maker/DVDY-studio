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
    from .ytopts import extract_info
    info = extract_info(url, flat=True)
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
        self.vbtn = button("Bajar video")
        self.abtn = button("Bajar música")
        self.vbtn.clicked.connect(lambda: self._quick(page, url, entry, False, self.vbtn))
        self.abtn.clicked.connect(lambda: self._quick(page, url, entry, True, self.abtn))
        mid.addWidget(row(self.vbtn, self.abtn,
                          button("Más opciones", lambda: page.open_download.emit(url), flat=True), None))
        lay.addLayout(mid, 1)

    def _quick(self, page, url, entry, audio, btn):
        page.quick(url, entry, audio)
        btn.setText("Agregado al dial")
        btn.setEnabled(False)


class SearchPage(Page):
    open_download = Signal(str)

    def __init__(self, manager, go_queue):
        super().__init__("Buscar", "Busca y baja con un clic, con la calidad elegida en Ajustes.")
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

    def set_simple(self, simple):
        self.count.setVisible(not simple)

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
        from .errors import friendly
        self.status.setText(friendly(msg)[0])

    def _show(self, entries):
        self.btn.setEnabled(True)
        while self.rl.count():
            w = self.rl.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        from . import motion
        cards = []
        for e in entries:
            cards.append(ResultCard(e, self))
            self.rl.addWidget(cards[-1])
        motion.stagger_in(cards)  # cascada de 40 ms; pasados 6 resultados, el resto entra junto
        self.status.setText(f"{len(entries)} resultados" if entries else "No se encontró nada. Prueba con otras palabras.")

    def quick(self, url, entry, audio):
        choices = default_choices(audio)
        self.manager.add(DownloadTask(url, build_opts(choices), title=entry.get("title"),
                                      label="Música" if audio else "Video",
                                      thumb=best_thumbnail_url(entry) or ""))
        self.status.setText(f"Agregado al dial (en Descargar): {entry.get('title')}")
