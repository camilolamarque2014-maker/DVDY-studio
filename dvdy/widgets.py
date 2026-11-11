"""Componentes reutilizables de la interfaz."""
import os
import threading
import urllib.request

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from .theme import ICON


# ---------------------------------------------------------------------------
def card(title=None, subtitle=None, spacing=10):
    """Devuelve (frame, layout) de una tarjeta con título opcional."""
    f = QFrame()
    f.setObjectName("Card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(16, 14, 16, 16)
    lay.setSpacing(spacing)
    if title:
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("Hint")
        s.setWordWrap(True)
        lay.addWidget(s)
    return f, lay


def label(text, name=None, wrap=False):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    if wrap:
        l.setWordWrap(True)
    return l


def icon_button(icon, tooltip="", callback=None):
    b = QToolButton()
    b.setObjectName("IconBtn")
    b.setText(ICON.get(icon, icon))
    b.setToolTip(tooltip)
    b.setCursor(Qt.PointingHandCursor)
    if callback:
        b.clicked.connect(callback)
    return b


def button(text, callback=None, primary=False, flat=False, tooltip=""):
    b = QPushButton(text)
    if primary:
        b.setObjectName("Primary")
    elif flat:
        b.setObjectName("Flat")
    b.setCursor(Qt.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    if callback:
        b.clicked.connect(callback)
    return b


def combo(items, current=None):
    """items: lista de (texto, dato)."""
    c = QComboBox()
    for text, data in items:
        c.addItem(text, data)
    if current is not None:
        set_combo(c, current)
    return c


def set_combo(c, data):
    i = c.findData(data)
    if i >= 0:
        c.setCurrentIndex(i)


def hline():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color: rgba(128,128,128,40);")
    return f


def row(*widgets, spacing=8, stretch_last=False, margins=(0, 0, 0, 0)):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for x in widgets:
        if x is None:
            lay.addStretch(1)
        elif isinstance(x, int):
            lay.addSpacing(x)
        else:
            lay.addWidget(x)
    if stretch_last:
        lay.addStretch(1)
    return w


def field(caption, widget, hint=None):
    """Etiqueta encima de un control."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    l = QLabel(caption)
    l.setObjectName("Muted")
    lay.addWidget(l)
    lay.addWidget(widget)
    if hint:
        h = QLabel(hint)
        h.setObjectName("Hint")
        h.setWordWrap(True)
        lay.addWidget(h)
    return w


class Page(QWidget):
    """Página con encabezado y contenido desplazable."""

    def __init__(self, title, subtitle="", scroll=True):
        super().__init__()
        self.setObjectName("Page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(28, 22, 28, 10)
        hl.setSpacing(2)
        self.header_row = QHBoxLayout()
        t = QLabel(title)
        t.setObjectName("PageTitle")
        self.header_row.addWidget(t)
        self.header_row.addStretch(1)
        hl.addLayout(self.header_row)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("PageSubtitle")
            s.setWordWrap(True)
            hl.addWidget(s)
        outer.addWidget(head)
        body = QWidget()
        body.setObjectName("Page")
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(28, 8, 28, 24)
        self.body.setSpacing(14)
        if scroll:
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setWidget(body)
            outer.addWidget(sa, 1)
        else:
            outer.addWidget(body, 1)

    def add(self, w, stretch=0):
        self.body.addWidget(w, stretch)
        return w


class Segmented(QWidget):
    """Selector segmentado (botones exclusivos)."""
    changed = Signal(str)

    def __init__(self, items, current=None):
        super().__init__()
        self.setObjectName("Segment")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for text, key in items:
            b = QPushButton(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            from PySide6.QtGui import QFont, QFontMetrics
            bold = QFont("Segoe UI Variable Text")
            bold.setPointSizeF(10.5)
            bold.setBold(True)
            b.setMinimumWidth(QFontMetrics(bold).horizontalAdvance(text) + 40)
            self.group.addButton(b)
            self.buttons[key] = b
            lay.addWidget(b)
            b.toggled.connect(lambda on, k=key: on and self.changed.emit(k))
        lay.addStretch(1)
        self.set_value(current or items[0][1])
        self.restyle()

    def set_key_visible(self, key, visible):
        self.buttons[key].setVisible(visible)
        self.restyle()

    def restyle(self):
        """Marca el último botón visible para redondear su borde derecho."""
        visible = [b for b in self.buttons.values() if not b.isHidden()]
        for b in self.buttons.values():
            last = bool(visible) and b is visible[-1]
            if b.property("last") != last:
                b.setProperty("last", last)
                b.style().unpolish(b)
                b.style().polish(b)

    def value(self):
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return None

    def set_value(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class PathPicker(QWidget):
    """Campo de texto + botón para elegir carpeta, archivo para abrir o archivo para guardar."""
    changed = Signal(str)

    def __init__(self, mode="dir", path="", file_filter="Todos (*)", placeholder=""):
        super().__init__()
        self.mode = mode
        self.file_filter = file_filter
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit(path)
        self.edit.setPlaceholderText(placeholder or {
            "dir": "Elige una carpeta…", "open": "Elige un archivo…", "save": "Archivo de salida…"}[mode])
        self.edit.textChanged.connect(self.changed.emit)
        self.setAcceptDrops(True)
        lay.addWidget(self.edit, 1)
        lay.addWidget(button("Examinar…", self.browse))

    def browse(self):
        cur = self.edit.text().strip()
        start = cur if cur else os.path.expanduser("~")
        if self.mode == "dir":
            p = QFileDialog.getExistingDirectory(self, "Elegir carpeta", start)
        elif self.mode == "open":
            p, _ = QFileDialog.getOpenFileName(self, "Elegir archivo", os.path.dirname(start) if cur else start,
                                               self.file_filter)
        else:
            p, _ = QFileDialog.getSaveFileName(self, "Guardar como", start, self.file_filter)
        if p:
            self.set_path(os.path.normpath(p))

    def path(self):
        return self.edit.text().strip()

    def set_path(self, p):
        self.edit.setText(p)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.set_path(os.path.normpath(urls[0].toLocalFile()))


class FileList(QWidget):
    """Lista de archivos con arrastrar y soltar."""
    changed = Signal()

    def __init__(self, file_filter="Todos (*)", placeholder="Arrastra archivos aquí o usa «Añadir»", reorder=False):
        super().__init__()
        self.file_filter = file_filter
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.list = _DropList(placeholder)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        if reorder:
            self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.files_dropped.connect(self.add_files)
        lay.addWidget(self.list, 1)
        btns = [button("Añadir…", self.browse), button("Quitar", self.remove_selected), button("Vaciar", self.clear)]
        if reorder:
            btns += [icon_button("up", "Subir", lambda: self.move(-1)), icon_button("down", "Bajar", lambda: self.move(1))]
        self.count_label = label("", "Hint")
        lay.addWidget(row(*btns, None, self.count_label))
        self._update_count()

    def browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Añadir archivos", "", self.file_filter)
        self.add_files(files)

    def add_files(self, files):
        existing = set(self.files())
        for f in files:
            f = os.path.normpath(f)
            if os.path.isfile(f) and f not in existing:
                it = QListWidgetItem(os.path.basename(f))
                it.setToolTip(f)
                it.setData(Qt.UserRole, f)
                self.list.addItem(it)
                existing.add(f)
        self._update_count()

    def remove_selected(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self._update_count()

    def clear(self):
        self.list.clear()
        self._update_count()

    def move(self, d):
        r = self.list.currentRow()
        if r < 0:
            return
        nr = r + d
        if 0 <= nr < self.list.count():
            it = self.list.takeItem(r)
            self.list.insertItem(nr, it)
            self.list.setCurrentRow(nr)
            self.changed.emit()

    def files(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _update_count(self):
        n = self.list.count()
        self.count_label.setText(f"{n} archivo(s)" if n else "")
        self.changed.emit()


class _DropList(QListWidget):
    files_dropped = Signal(list)

    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            files = []
            for u in e.mimeData().urls():
                p = u.toLocalFile()
                if os.path.isdir(p):
                    for name in sorted(os.listdir(p)):
                        full = os.path.join(p, name)
                        if os.path.isfile(full):
                            files.append(full)
                elif p:
                    files.append(p)
            self.files_dropped.emit(files)
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.count() == 0:
            from PySide6.QtGui import QPainter
            p = QPainter(self.viewport())
            p.setPen(self.palette().placeholderText().color())
            p.drawText(self.viewport().rect(), Qt.AlignCenter, self.placeholder)
            p.end()


# ---------------------------------------------------------------------------
class _ThumbRelay(QObject):
    loaded = Signal(object, str, bytes)


_relay = None
_cache = {}


def load_thumbnail(url, target_label, size):
    """Descarga una miniatura en segundo plano y la muestra en target_label."""
    global _relay
    if _relay is None:
        _relay = _ThumbRelay()
        _relay.loaded.connect(_on_thumb)
    target_label._thumb_url = url
    target_label._thumb_size = size
    if not url:
        return
    if url in _cache:
        _on_thumb(target_label, url, _cache[url])
        return

    def work():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            _cache[url] = data
            _relay.loaded.emit(target_label, url, data)
        except Exception:
            pass

    threading.Thread(target=work, daemon=True).start()


def _on_thumb(lbl, url, data):
    try:
        if getattr(lbl, '_thumb_url', None) != url:
            return
        pm = QPixmap()
        if not pm.loadFromData(data):
            return
        w, h = lbl._thumb_size
        pm = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (pm.width() - w) // 2)
        y = max(0, (pm.height() - h) // 2)
        lbl.setPixmap(_rounded(pm.copy(x, y, w, h), 8))
    except RuntimeError:
        pass  # el widget ya fue destruido


def _rounded(pm, radius):
    from PySide6.QtGui import QPainter, QPainterPath
    out = QPixmap(pm.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, pm.width(), pm.height(), radius, radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def thumb_label(w, h):
    l = QLabel()
    l.setObjectName("Thumb")
    l.setFixedSize(w, h)
    l.setAlignment(Qt.AlignCenter)
    l.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return l


# ---------------------------------------------------------------------------
class Worker(QObject):
    """Ejecuta una función en un hilo y devuelve el resultado al hilo de la interfaz."""
    finished = Signal(object)
    failed = Signal(str)

    _alive = set()

    def __init__(self, func, *args):
        super().__init__()
        self.func, self.args = func, args

    def start(self):
        Worker._alive.add(self)
        self.finished.connect(self._cleanup)
        self.failed.connect(self._cleanup)
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        try:
            res = self.func(*self.args)
            self.finished.emit(res)
        except Exception as e:  # noqa: BLE001
            import re
            self.failed.emit(re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", ""))

    def _cleanup(self, *_):
        Worker._alive.discard(self)


def run_async(func, *args, on_done=None, on_error=None):
    w = Worker(func, *args)
    if on_done:
        w.finished.connect(on_done)
    if on_error:
        w.failed.connect(on_error)
    return w.start()


# ---------------------------------------------------------------------------
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QPainter  # noqa: E402
from PySide6.QtWidgets import QAbstractButton  # noqa: E402


class ToggleSwitch(QAbstractButton):
    """Interruptor deslizante animado (apagado = izquierda, encendido = derecha)."""

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate)

    def _get_knob(self):
        return self._pos

    def _set_knob(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, e):
        from .config import cfg
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        accent = QColor(cfg["accent"])
        off = QColor("#3a4052") if cfg["theme"] != "light" else QColor("#c9cdd8")
        track = QColor(
            int(off.red() + (accent.red() - off.red()) * self._pos),
            int(off.green() + (accent.green() - off.green()) * self._pos),
            int(off.blue() + (accent.blue() - off.blue()) * self._pos))
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        r = QRectF(0, 0, self.width(), self.height())
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = self.height() - 6
        x = 3 + (self.width() - d - 6) * self._pos
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()

    def sizeHint(self):
        return self.size()


class ModeSwitch(QWidget):
    """«Simple  [interruptor]  Avanzado»."""
    changed = Signal(bool)  # True = avanzado

    def __init__(self, advanced=True):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.simple_lbl = QLabel("Simple")
        self.adv_lbl = QLabel("Avanzado")
        self.switch = ToggleSwitch(advanced)
        for l, val in ((self.simple_lbl, False), (self.adv_lbl, True)):
            l.setCursor(Qt.PointingHandCursor)
            l.mousePressEvent = lambda _e, v=val: self.switch.setChecked(v)
        lay.addWidget(self.simple_lbl)
        lay.addWidget(self.switch)
        lay.addWidget(self.adv_lbl)
        lay.addStretch(1)
        self.switch.toggled.connect(self._changed)
        self._refresh()

    def _changed(self, on):
        self._refresh()
        self.changed.emit(on)

    def _refresh(self):
        on = self.switch.isChecked()
        for l, active in ((self.simple_lbl, not on), (self.adv_lbl, on)):
            l.setObjectName("ModeOn" if active else "ModeOff")
            l.style().unpolish(l)
            l.style().polish(l)

    def is_advanced(self):
        return self.switch.isChecked()