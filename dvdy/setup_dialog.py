"""Diálogo para descargar e instalar los componentes que faltan (FFmpeg, Deno, yt-dlp)."""
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from . import deps
from .utils import find_ffmpeg, find_js_runtime, fmt_size


class _Signals(QObject):
    progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(bool, str)


def component_state(key):
    if key == "ffmpeg":
        p = find_ffmpeg()
        return f"Instalado ({p})" if p else None
    if key == "deno":
        name, p = find_js_runtime()
        return f"Instalado: {name} ({p})" if name else None
    if key == "yt-dlp":
        try:
            import yt_dlp
            return f"Versión {yt_dlp.version.__version__}"
        except Exception:
            return None
    return None


class SetupDialog(QDialog):
    """components: claves a ofrecer. preselect: las que vienen marcadas."""

    def __init__(self, parent=None, components=("ffmpeg", "deno"), preselect=None, intro=None):
        super().__init__(parent)
        self.setWindowTitle("Componentes de DVDY Studio")
        self.setMinimumWidth(600)
        self.setModal(True)
        self.changed = False
        self._cancel = threading.Event()
        self._running = False
        self._prefix = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        t = QLabel("Componentes necesarios")
        t.setObjectName("PageTitle")
        lay.addWidget(t)
        i = QLabel(intro or "DVDY Studio usa estos programas gratuitos. Se pueden descargar e instalar "
                            "automáticamente desde sus páginas oficiales (no necesita permisos de administrador).")
        i.setObjectName("Muted")
        i.setWordWrap(True)
        lay.addWidget(i)

        preselect = set(preselect if preselect is not None else components)
        self.checks = {}
        for key in components:
            info = deps.COMPONENTS[key]
            f = QFrame()
            f.setObjectName("Card")
            fl = QHBoxLayout(f)
            fl.setContentsMargins(14, 10, 14, 10)
            cb = QCheckBox()
            cb.setChecked(key in preselect)
            self.checks[key] = cb
            fl.addWidget(cb, 0, Qt.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(2)
            name = QLabel(f"{info['name']}   <span style='font-weight:400;'>· {info['size']}</span>")
            name.setObjectName("SectionTitle")
            col.addWidget(name)
            d = QLabel(info["desc"])
            d.setObjectName("Hint")
            d.setWordWrap(True)
            col.addWidget(d)
            state = component_state(key)
            s = QLabel(f"✔ {state}" if state else "✖ No encontrado")
            s.setObjectName("OkText" if state else "ErrText")
            s.setWordWrap(True)
            col.addWidget(s)
            fl.addLayout(col, 1)
            lay.addWidget(f)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setFixedHeight(8)
        self.bar.hide()
        lay.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.later = QPushButton("Ahora no")
        self.later.clicked.connect(self._close_or_cancel)
        self.go = QPushButton("Descargar e instalar")
        self.go.setObjectName("Primary")
        self.go.clicked.connect(self.start)
        btns.addWidget(self.later)
        btns.addWidget(self.go)
        lay.addLayout(btns)

        self.sig = _Signals()
        self.sig.progress.connect(self._on_progress)
        self.sig.status.connect(self.status.setText)
        self.sig.finished.connect(self._on_finished)

    def _close_or_cancel(self):
        if self._running:
            self._cancel.set()
            self.status.setText("Cancelando…")
        else:
            self.reject()

    def closeEvent(self, e):
        if self._running:
            self._cancel.set()
            e.ignore()
        else:
            super().closeEvent(e)

    def start(self):
        keys = [k for k, cb in self.checks.items() if cb.isChecked()]
        if not keys:
            self.reject()
            return
        self._running = True
        self._cancel.clear()
        self.go.setEnabled(False)
        for cb in self.checks.values():
            cb.setEnabled(False)
        self.later.setText("Cancelar")
        self.bar.show()
        threading.Thread(target=self._work, args=(keys,), daemon=True).start()

    def _work(self, keys):
        try:
            for n, key in enumerate(keys, 1):
                self._prefix = f"({n}/{len(keys)}) " if len(keys) > 1 else ""
                deps.install(key, progress=lambda d, t: self.sig.progress.emit(d, t),
                             status=lambda s: self.sig.status.emit(self._prefix + s), cancel=self._cancel)
            self.sig.finished.emit(True, "Todo listo.")
        except deps.Cancelled:
            self.sig.finished.emit(False, "Instalación cancelada.")
        except Exception as e:  # noqa: BLE001
            self.sig.finished.emit(False, f"Error: {e}")

    def _on_progress(self, done, total):
        if total:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(done * 1000 / total))
            self.status.setText(f"{self._prefix}Descargando… {fmt_size(done)} de {fmt_size(total)}")
        else:
            self.bar.setRange(0, 0)

    def _on_finished(self, ok, msg):
        self._running = False
        self.changed = True
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000 if ok else 0)
        self.status.setText(msg)
        self.later.setText("Cerrar")
        self.go.setText("Reintentar")
        self.go.setEnabled(not ok)
        for cb in self.checks.values():
            cb.setEnabled(not ok)
        if ok:
            self.later.setObjectName("Primary")
            self.later.style().unpolish(self.later)
            self.later.style().polish(self.later)
