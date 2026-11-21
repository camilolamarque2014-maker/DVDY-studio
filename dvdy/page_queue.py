"""Panel «En el dial»: la cola de descargas y conversiones.

Arriba, la escala del dial con la aguja ámbar en el progreso de la descarga activa.
Debajo, cada tarea con su tapa, su estado en español y acciones con texto.
"""
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QToolButton,
    QVBoxLayout, QWidget,
)

from .errors import ACTION_LABELS, NO_RETRY
from .tasks import CANCELED, DONE, ERROR, PAUSED, QUEUED, RUNNING
from .theme import ICON, icon_font
from .utils import open_path, reveal_path
from .widgets import DialStrip, icon_button, label, load_thumbnail, plural, thumb_label

KIND_ICON = {"download": "download", "ffmpeg": "convert", "other": "sync"}


def _small(text, cb, primary=False):
    b = QPushButton(text)
    b.setObjectName("SmallPrimary" if primary else "Small")
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(cb)
    return b


class TaskRow(QWidget):
    def __init__(self, task, manager, on_action):
        super().__init__()
        self.task = task
        self.manager = manager
        self.on_action = on_action
        self.setObjectName("TaskRow")
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.setSpacing(0)
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 12, 0, 12)
        lay.setSpacing(14)
        wrap.addLayout(lay)
        sep = QFrame()
        sep.setObjectName("Sep")
        sep.setFixedHeight(1)
        wrap.addWidget(sep)

        self.cover = thumb_label(56, 56)
        self.cover.setFont(icon_font(20))
        self.cover.setText(ICON[KIND_ICON.get(task.kind, "file")])
        self._thumb_url = None
        lay.addWidget(self.cover, 0, Qt.AlignTop)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        self.title = QLabel()
        self.title.setObjectName("SectionTitle")
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        mid.addWidget(self.title)
        self.status = QLabel()
        self.status.setObjectName("Hint")
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status.setWordWrap(True)
        mid.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(3)
        self.bar.setRange(0, 1000)
        self.bar.setAccessibleName("Progreso")
        mid.addWidget(self.bar)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        self.actions.setContentsMargins(0, 4, 0, 0)
        mid.addLayout(self.actions)
        lay.addLayout(mid, 1)

        self.remove_btn = icon_button("cancel", "Quitar de la lista", lambda: manager.remove(task))
        self.remove_btn.setAccessibleName("Quitar de la lista")
        lay.addWidget(self.remove_btn, 0, Qt.AlignTop)
        self._last_state = None
        self.refresh()

    # --- acciones ---
    def _open(self):
        out = self.task.output
        if out and os.path.isfile(out):
            open_path(out)
        else:
            reveal_path(out)

    def _set_actions(self, items):
        while self.actions.count():
            w = self.actions.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for text, cb, primary in items:
            self.actions.addWidget(_small(text, cb, primary))
        self.actions.addStretch(1)

    def refresh(self):
        t = self.task
        if t.thumb and t.thumb != self._thumb_url:
            self._thumb_url = t.thumb
            self.cover.setText("")
            load_thumbnail(t.thumb, self.cover, (56, 56))
        self._set_title()

        # Estado en una línea
        if t.status == RUNNING:
            bits = []
            if t.progress >= 0:
                bits.append(f"Bajando {t.progress:.0f} %" if t.kind == "download" else f"Procesando {t.progress:.0f} %")
            if t.speed and t.kind == "download":
                bits.append(t.speed)
            if t.eta:
                bits.append(f"quedan {t.eta}")
            if not bits or t.progress < 0:
                bits = [t.detail or "Preparando…"]
            text, style = "  ·  ".join(bits), "AmberText"
        elif t.status == QUEUED:
            text, style = "En espera", "Hint"
        elif t.status == PAUSED:
            text, style = "En pausa · sigue donde quedó", "Hint"
        elif t.status == CANCELED:
            text, style = "Cancelada", "Hint"
        elif t.status == DONE:
            name = os.path.basename(t.output) if t.output and os.path.isfile(t.output) else (t.output or "")
            text = (t.note or "Listo") + (f"  ·  {name}" if name else "")
            style = "Hint"
        else:
            text, style = t.error or "No se pudo completar.", "ErrText"
        self.status.setText(text)
        self.status.setToolTip(t.error_raw if t.status == ERROR and t.error_raw else text)
        if self.status.objectName() != style:
            self.status.setObjectName(style)
            self.status.style().unpolish(self.status)
            self.status.style().polish(self.status)

        # Barra solo mientras está activa o en pausa
        # Sin porcentaje todavía (preparando, uniendo, convirtiendo): sin barra, el estado ámbar lo dice
        self.bar.setVisible(t.status == PAUSED or (t.status == RUNNING and t.progress >= 0))
        self.bar.setRange(0, 1000)
        self.bar.setValue(int(max(0, t.progress) * 10))
        bar_name = "Paused" if t.status == PAUSED else ""
        if self.bar.objectName() != bar_name:
            self.bar.setObjectName(bar_name)
            self.bar.style().unpolish(self.bar)
            self.bar.style().polish(self.bar)

        state = (t.status, t.error_action, bool(t.output))
        if state != self._last_state:
            self._last_state = state
            m = self.manager
            if t.status == RUNNING:
                items = [("Pausar", lambda: m.pause(t), False)] if t.can_pause else []
                items.append(("Cancelar", lambda: m.cancel(t), False))
            elif t.status == QUEUED:
                items = [("Cancelar", lambda: m.cancel(t), False)]
            elif t.status == PAUSED:
                items = [("Reanudar", lambda: m.resume(t), True), ("Cancelar", lambda: m.cancel(t), False)]
            elif t.status == DONE:
                is_file = bool(t.output) and os.path.isfile(t.output)
                items = [("Abrir" if is_file else "Abrir carpeta", self._open, True)]
                if is_file:
                    items.append(("Mostrar en la carpeta", lambda: reveal_path(t.output), False))
            elif t.status == CANCELED:
                items = [("Reintentar", lambda: m.resume(t), False)]
            else:
                act = t.error_action
                items = []
                if act and act != "retry":
                    items.append((ACTION_LABELS[act], lambda a=act: self.on_action(t, a), True))
                if act not in NO_RETRY:
                    items.append(("Reintentar", lambda: m.resume(t), not items))
            self._set_actions(items)
        self.remove_btn.setVisible(t.status != RUNNING)

    def _set_title(self):
        title = self.task.title or ""
        if title.startswith(("http://", "https://")):
            title = re.sub(r"^https?://(www\.|m\.)?", "", title)
        fm = self.title.fontMetrics()
        self.title.setText(fm.elidedText(title, Qt.ElideRight, max(120, self.title.width())))
        self.title.setToolTip(self.task.title)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._set_title()


class DialPanel(QFrame):
    def __init__(self, manager, on_action):
        super().__init__()
        self.setObjectName("Panel")
        self.manager = manager
        self.on_action = on_action
        self.rows = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 10)
        lay.setSpacing(10)

        head = QHBoxLayout()
        t = label("EN EL DIAL", "Label")
        head.addWidget(t)
        self.count = label("", "Hint")
        head.addWidget(self.count)
        head.addStretch(1)
        more = QToolButton()
        more.setObjectName("IconBtn")
        more.setText(ICON["more"])
        more.setToolTip("Más acciones")
        more.setAccessibleName("Más acciones de la cola")
        more.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(more)
        m.addAction("Pausar todo", manager.pause_all)
        m.addAction("Reanudar todo", manager.resume_all)
        m.addAction("Cancelar todo", manager.cancel_all)
        m.addSeparator()
        m.addAction("Quitar las terminadas", manager.clear_finished)
        more.setMenu(m)
        head.addWidget(more)
        lay.addLayout(head)

        self.dial = DialStrip()
        lay.addWidget(self.dial)

        self.empty = QLabel("Todavía no hay descargas.\nPega un enlace y presiona Descargar:\nlo vas a ver acá con su avance.")
        self.empty.setObjectName("Empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(160)
        lay.addWidget(self.empty)

        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        self.list_lay = QVBoxLayout(body)
        self.list_lay.setContentsMargins(0, 0, 4, 0)
        self.list_lay.setSpacing(0)
        self.list_lay.addStretch(1)
        sa.setWidget(body)
        lay.addWidget(sa, 1)

        manager.task_added.connect(self._added)
        manager.task_updated.connect(self._updated)
        manager.task_removed.connect(self._removed)
        self._refresh_head()

    def _added(self, task):
        r = TaskRow(task, self.manager, self.on_action)
        self.rows[task.id] = r
        self.list_lay.insertWidget(0, r)
        self._refresh_head()

    def _updated(self, task):
        r = self.rows.get(task.id)
        if r:
            r.refresh()
        self._refresh_head()

    def _removed(self, task):
        r = self.rows.pop(task.id, None)
        if r:
            r.setParent(None)
            r.deleteLater()
        self._refresh_head()

    def _refresh_head(self):
        tasks = list(self.manager.tasks)
        self.empty.setVisible(not tasks)
        active = [t for t in tasks if t.status == RUNNING]
        waiting = sum(1 for t in tasks if t.status == QUEUED)
        done = sum(1 for t in tasks if t.status == DONE)
        bits = []
        if active:
            bits.append(plural(len(active), "bajando", "bajando"))
        if waiting:
            bits.append(plural(waiting, "en espera", "en espera"))
        if done:
            bits.append(plural(done, "lista", "listas"))
        failed = sum(1 for t in tasks if t.status == ERROR)
        if failed:
            bits.append(plural(failed, "con problema", "con problemas"))
        self.count.setText("  ·  ".join(bits))
        live = next((t for t in active if t.progress >= 0), None)
        if live:
            self._last_needle = live.progress
            self.dial.set_value(live.progress, busy=False)
        elif active:
            # Activa pero sin porcentaje: la aguja sigue encendida en la última posición y late suave
            self.dial.set_value(getattr(self, "_last_needle", 0.0), busy=True)
        else:
            self._last_needle = 0.0
            self.dial.set_value(None)
