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
        t = QLabel(title.upper())
        t.setObjectName("Label")
        t.setAccessibleName(title)
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
    f.setObjectName("Sep")
    f.setFixedHeight(1)
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
            bold = QFont("Archivo")
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
        self.setObjectName("DropZone")
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
            from .deps import urlopen
            with urlopen(url, timeout=15, user_agent="Mozilla/5.0") as r:
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
        self._anim.setDuration(200)
        from . import motion
        self._anim.setEasingCurve(motion.ease_in_out())  # se desplaza en pantalla: ease-in-out
        self.toggled.connect(self._animate)

    def _get_knob(self):
        return self._pos

    def _set_knob(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, on):
        from . import motion
        self._anim.stop()
        if not motion.enabled():
            self._set_knob(1.0 if on else 0.0)
            return
        self._anim.setStartValue(self._pos)  # desde donde esté: interrumpible
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, e):
        from .theme import current
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        accent = QColor(current["text"])
        off = QColor(current["line2"])
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
        # Squash & stretch: a mitad de camino la perilla se estira un poco y vuelve a ser redonda al llegar
        stretch = 4 * self._pos * (1 - self._pos) * 7
        p.setBrush(QColor(current["bg"]) if self._pos > 0.5 else QColor(current["text"]))
        p.drawRoundedRect(QRectF(x - stretch / 2, 3 + stretch / 10, d + stretch, d - stretch / 5), d / 2, d / 2)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            from PySide6.QtGui import QPen
            p.setPen(QPen(QColor(current["amber"]), 1.5))
            p.drawRoundedRect(r.adjusted(0.75, 0.75, -0.75, -0.75), r.height() / 2, r.height() / 2)
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
        self.switch.setAccessibleName("Modo avanzado")
        self.switch.setToolTip("Simple: lo esencial a la vista.  Avanzado: todas las secciones y herramientas.")
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

# ---------------------------------------------------------------------------
#  Piezas propias de la identidad «Radio de Madrugada»
# ---------------------------------------------------------------------------
from PySide6.QtCore import QPointF  # noqa: E402


def plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


class BandButton(QAbstractButton):
    """Una banda del selector (como AM / FM): punto indicador y etiqueta en versalitas."""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName(text)
        self._pop = 1.0
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, on):
        # El punto se enciende con un pequeño latido (1.4 → 1 en 150 ms): confirma la elección
        from . import motion
        if on:
            motion.animate(self, "pop", 1.4, 1.0, 150, motion.ease_out(), self._set_pop)

    def _set_pop(self, v):
        self._pop = float(v)
        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        from .theme import label_font
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(label_font(10.5, spacing=118))
        return QSize(fm.horizontalAdvance(self.text().upper()) + 34, 34)

    def paintEvent(self, e):
        from PySide6.QtGui import QPen
        from .theme import current, label_font
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        h = self.height()
        cy = h / 2
        ring = QColor(current["amber"] if on else current["muted"])
        p.setPen(QPen(ring, 1.2))
        p.setBrush(QColor(current["amber"]) if on else Qt.NoBrush)
        r = 5 * (self._pop if on else 1.0)
        p.drawEllipse(QPointF(7, cy), r, r)
        p.setPen(QColor(current["text"] if (on or self.underMouse()) else current["muted"]))
        p.setFont(label_font(10.5, weight=700 if on else 600, spacing=118))
        p.drawText(QRectF(22, 0, self.width() - 22, h), Qt.AlignVCenter | Qt.AlignLeft, self.text().upper())
        if self.hasFocus():
            p.setPen(QPen(QColor(current["text"]), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 2.5, self.width() - 1, h - 5), 5, 5)
        p.end()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class BandSelector(QWidget):
    """Selector de modo de descarga con estética de banda de radio."""
    changed = Signal(str)

    def __init__(self, items, current_key=None):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(26)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for text, key in items:
            b = BandButton(text)
            self.group.addButton(b)
            self.buttons[key] = b
            lay.addWidget(b)
            b.toggled.connect(lambda on, k=key: on and self.changed.emit(k))
        lay.addStretch(1)
        self.set_value(current_key or items[0][1])

    def value(self):
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return None

    def set_value(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def set_key_visible(self, key, visible):
        self.buttons[key].setVisible(visible)


class DialStrip(QWidget):
    """La escala del dial: marcas finas y una aguja ámbar en el progreso de la descarga activa."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(54)
        self.setMaximumHeight(54)
        self._value = None  # None = sin descarga activa (aguja apagada)
        self._shown = 0.0   # posición dibujada de la aguja (se desliza hacia _value)
        self._busy = False
        self._phase = 0.0
        from PySide6.QtCore import QTimer
        self._pulse = QTimer(self)
        self._pulse.setInterval(50)
        self._pulse.timeout.connect(self._tick)
        self.setAccessibleName("Progreso de la descarga activa")

    def set_value(self, v, busy=False):
        """v: 0-100 o None (sin descarga activa). busy: activa pero sin porcentaje (la aguja late)."""
        from . import motion
        was = self._value
        self._value = None if v is None else max(0.0, min(100.0, float(v)))
        target = 0.0 if self._value is None else self._value
        if was is None or self._value is None or abs(target - self._shown) < 0.05:
            motion.stop(self, "needle")  # al encender o apagar el dial, la aguja va directo
            self._shown = target
        else:
            # La aguja se desliza desde donde está (interrumpible): 250 ms ease-in-out
            motion.animate(self, "needle", self._shown, target, 250, motion.ease_in_out(), self._set_shown)
        self._busy = bool(busy) and v is not None
        if self._busy and not self._pulse.isActive():
            self._pulse.start()
        elif not self._busy:
            self._pulse.stop()
        desc = "Sin descargas activas" if v is None else ("Preparando la descarga" if self._busy else f"{self._value:.0f} %")
        self.setAccessibleDescription(desc)
        self.update()

    def _set_shown(self, v):
        self._shown = float(v)
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.05) % 1.0
        self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QPen
        from .theme import current, label_font
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, right = 10.0, w - 10.0
        span = right - left
        base = h - 18.0
        line = QColor(current["line2"])
        p.setPen(QPen(QColor(current["line"]), 1))
        p.drawLine(QPointF(left, base), QPointF(right, base))
        for i in range(0, 41):
            x = left + span * i / 40
            major = i % 10 == 0
            mid = i % 5 == 0
            p.setPen(QPen(QColor(current["muted"]) if major else line, 1))
            top = base - (16 if major else 10 if mid else 6)
            p.drawLine(QPointF(x, top), QPointF(x, base))
        p.setFont(label_font(8, spacing=110))
        p.setPen(QColor(current["muted"]))
        for i, lab in enumerate(("0", "25", "50", "75", "100")):
            x = left + span * i / 4
            p.drawText(QRectF(x - 20, base + 3, 40, 14), Qt.AlignHCenter | Qt.AlignTop, lab)
        if self._value is None:
            x = left
            col = QColor(current["faint"])
        else:
            import math
            x = left + span * self._shown / 100
            col = QColor(current["amber"])
            if self._busy:
                col.setAlphaF(0.45 + 0.55 * (0.5 + 0.5 * math.sin(self._phase * 2 * math.pi)))
        p.setPen(QPen(col, 2))
        p.drawLine(QPointF(x, 2), QPointF(x, base + 1))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(x, 3), 3, 3)
        p.end()


class FolderButton(QPushButton):
    """Botón compacto que muestra el nombre de la carpeta y abre el selector al pulsarlo."""
    changed = Signal(str)

    def __init__(self, path=""):
        super().__init__()
        self.setObjectName("TileButton")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.browse)
        self.set_path(path)

    def path(self):
        return self._path

    def set_path(self, p):
        self._path = p or ""
        name = os.path.basename(os.path.normpath(self._path)) if self._path else "Elegir…"
        self.setText(name or self._path)
        self.setToolTip(self._path)
        self.setAccessibleName(f"Carpeta de destino: {self._path}")
        self.changed.emit(self._path)

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, "Elegir carpeta", self._path or os.path.expanduser("~"))
        if p:
            self.set_path(os.path.normpath(p))


def tile(caption, widget):
    """Casilla de opción: etiqueta en versalitas y el control debajo, sin bordes propios."""
    f = QFrame()
    f.setObjectName("Tile")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 8, 12, 6)
    lay.setSpacing(1)
    l = QLabel(caption.upper())
    l.setObjectName("Label")
    l.setBuddy(widget)
    lay.addWidget(l)
    lay.addWidget(widget)
    widget.setAccessibleName(caption)
    # Foco visible: el borde de la casilla se ilumina cuando cualquiera de sus controles tiene el foco
    flt = _TileFocus(f)
    for w in [widget] + widget.findChildren(QWidget):
        w.installEventFilter(flt)
    f._focus_filter = flt
    return f


class _TileFocus(QObject):
    def __init__(self, frame):
        super().__init__(frame)
        self.frame = frame

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if ev.type() in (QEvent.FocusIn, QEvent.FocusOut):
            on = ev.type() == QEvent.FocusIn
            if self.frame.property("focused") != on:
                self.frame.setProperty("focused", on)
                self.frame.style().unpolish(self.frame)
                self.frame.style().polish(self.frame)
        return False


# ---------------------------------------------------------------------------
class NoWheelOnControls(QObject):
    """La rueda del mouse no cambia listas desplegables, números ni deslizadores: sigue desplazando la página.

    Así, al recorrer las opciones con la rueda, no se cambia un valor sin querer al pasar por encima.
    Las listas abiertas (el desplegable de un QComboBox) siguen respondiendo a la rueda con normalidad.
    """

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSpinBox, QSlider
        if ev.type() != QEvent.Wheel or not isinstance(obj, (QComboBox, QAbstractSpinBox, QSlider)):
            return False
        p = obj.parentWidget()
        while p is not None and not isinstance(p, QAbstractScrollArea):
            p = p.parentWidget()
        if p is not None:
            bar = p.horizontalScrollBar() if ev.angleDelta().x() and not ev.angleDelta().y() else p.verticalScrollBar()
            if bar.isVisible():
                from PySide6.QtWidgets import QApplication
                QApplication.sendEvent(bar, ev)
        return True  # el control no recibe la rueda
