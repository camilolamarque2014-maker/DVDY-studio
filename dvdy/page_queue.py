"""Página «Cola»: todas las descargas y conversiones con su progreso."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QSpinBox, QVBoxLayout, QWidget

from .config import cfg
from .tasks import CANCELED, DONE, ERROR, PAUSED, QUEUED, RUNNING, STATUS_TEXT
from .theme import ICON, icon_font
from .utils import reveal_path
from .widgets import Page, button, icon_button, label, row

KIND_ICON = {"download": "download", "ffmpeg": "convert", "other": "settings"}


class TaskCard(QFrame):
    def __init__(self, task, manager):
        super().__init__()
        self.task = task
        self.manager = manager
        self.setObjectName("Card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 10, 10)
        lay.setSpacing(12)
        ic = QLabel(ICON[KIND_ICON.get(task.kind, "file")])
        ic.setFont(icon_font(20))
        ic.setFixedWidth(28)
        ic.setAlignment(Qt.AlignCenter)
        ic.setObjectName("Muted")
        lay.addWidget(ic)
        mid = QVBoxLayout()
        mid.setSpacing(4)
        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("SectionTitle")
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.kind = label(getattr(task, "label", ""), "Hint")
        self.state = label("", "Muted")
        top.addWidget(self.title, 1)
        top.addWidget(self.kind)
        top.addSpacing(10)
        top.addWidget(self.state)
        mid.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setRange(0, 1000)
        mid.addWidget(self.bar)
        self.detail = label("", "Hint")
        self.detail.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        mid.addWidget(self.detail)
        lay.addLayout(mid, 1)

        self.pause_btn = icon_button("pause", "Pausar", self._toggle_pause)
        self.retry_btn = icon_button("refresh", "Reintentar", lambda: manager.resume(task))
        self.cancel_btn = icon_button("cancel", "Cancelar", lambda: manager.cancel(task))
        self.folder_btn = icon_button("folder", "Mostrar en la carpeta", lambda: reveal_path(task.output))
        self.remove_btn = icon_button("delete", "Quitar de la lista", lambda: manager.remove(task))
        for b in (self.pause_btn, self.retry_btn, self.cancel_btn, self.folder_btn, self.remove_btn):
            lay.addWidget(b)
        self.refresh()

    def _toggle_pause(self):
        if self.task.status == PAUSED:
            self.manager.resume(self.task)
        else:
            self.manager.pause(self.task)

    def refresh(self):
        t = self.task
        fm = self.title.fontMetrics()
        self.title.setText(fm.elidedText(t.title, Qt.ElideRight, max(120, self.title.width())))
        self.title.setToolTip(t.title)
        bits = [STATUS_TEXT[t.status]]
        if t.status == RUNNING and t.progress >= 0:
            bits.insert(0, f"{t.progress:.1f}%")
        if t.speed:
            bits.append(t.speed)
        if t.eta:
            bits.append(f"quedan {t.eta}")
        self.state.setText("  ·  ".join(bits))
        dfm = self.detail.fontMetrics()
        self.detail.setText(dfm.elidedText(t.detail or "", Qt.ElideMiddle, max(120, self.detail.width())))
        self.detail.setToolTip(t.detail or "")
        if t.status == RUNNING and t.progress < 0:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int((100 if t.status == DONE else max(0, t.progress)) * 10))
        name = {DONE: "Done", ERROR: "Failed", PAUSED: "Paused", CANCELED: "Failed"}.get(t.status, "")
        if self.bar.objectName() != name:
            self.bar.setObjectName(name)
            self.bar.style().unpolish(self.bar)
            self.bar.style().polish(self.bar)
        self.state.setObjectName({DONE: "OkText", ERROR: "ErrText", PAUSED: "WarnText"}.get(t.status, "Muted"))
        self.state.style().unpolish(self.state)
        self.state.style().polish(self.state)
        self.pause_btn.setVisible(t.can_pause and t.status in (RUNNING, QUEUED, PAUSED))
        self.pause_btn.setText(ICON["play"] if t.status == PAUSED else ICON["pause"])
        self.pause_btn.setToolTip("Reanudar" if t.status == PAUSED else "Pausar")
        self.retry_btn.setVisible(t.status in (ERROR, CANCELED))
        self.cancel_btn.setVisible(t.status in (RUNNING, QUEUED, PAUSED))
        self.folder_btn.setVisible(bool(t.output))
        self.remove_btn.setVisible(t.status not in (RUNNING,))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.refresh()


class QueuePage(Page):
    def __init__(self, manager):
        super().__init__("Cola de tareas", "Descargas y conversiones en curso. Las pausadas se reanudan donde quedaron.")
        self.manager = manager
        self.cards = {}
        self.conc = QSpinBox()
        self.conc.setRange(1, 10)
        self.conc.setValue(int(cfg["max_concurrent"]))
        self.conc.valueChanged.connect(self._set_conc)
        self.add(row(button("Pausar todo", manager.pause_all), button("Reanudar todo", manager.resume_all),
                     button("Cancelar todo", manager.cancel_all), button("Limpiar terminadas", manager.clear_finished),
                     None, label("Tareas simultáneas", "Muted"), self.conc))
        self.empty = label("No hay tareas. Las descargas y conversiones que inicies aparecerán aquí.", "Muted")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(160)
        self.add(self.empty)
        self.list_w = QWidget()
        self.list_lay = QVBoxLayout(self.list_w)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(8)
        self.add(self.list_w)
        self.body.addStretch(1)
        manager.task_added.connect(self._added)
        manager.task_updated.connect(self._updated)
        manager.task_removed.connect(self._removed)

    def _set_conc(self, v):
        cfg["max_concurrent"] = v
        cfg.save()
        self.manager.schedule()

    def _added(self, task):
        c = TaskCard(task, self.manager)
        self.cards[task.id] = c
        self.list_lay.insertWidget(0, c)
        self.empty.hide()

    def _updated(self, task):
        c = self.cards.get(task.id)
        if c:
            c.refresh()

    def _removed(self, task):
        c = self.cards.pop(task.id, None)
        if c:
            c.setParent(None)
            c.deleteLater()
        self.empty.setVisible(not self.cards)
