"""Ventana «Hay una versión nueva»: versión instalada y nueva, novedades y tres opciones.

- Actualizar (botón principal): en el .exe descarga la versión nueva, cierra la app, reemplaza
  los archivos y la vuelve a abrir. Desde el código fuente abre la página del release.
- Recordarme después: cierra la ventana; vuelve a aparecer la próxima vez que se abra la app.
- Saltar esta versión: no vuelve a avisar hasta que salga una versión más nueva que esta.
"""
import os
import threading

from PySide6.QtCore import QObject, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QTextBrowser, QVBoxLayout,
)

from . import updater
from .config import APP_VERSION, cfg
from .utils import fmt_size
from .widgets import button

REMIND, SKIP, UPDATE = "remind", "skip", "update"


class _Signals(QObject):
    progress = Signal(int, int)
    status = Signal(str)
    ready = Signal(str, str)   # carpeta de trabajo, carpeta con el programa nuevo
    failed = Signal(str)


class UpdateDialog(QDialog):
    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_shown_once", False):
            self._shown_once = True
            from . import motion
            motion.window_in(self, motion.UI)  # aparece con un fundido de 200 ms

    def __init__(self, info, manager=None, parent=None):
        super().__init__(parent)
        self.info = info
        self.manager = manager
        self.choice = REMIND
        self._busy = False
        self._cancel = threading.Event()
        self.setWindowTitle("Hay una versión nueva")
        self.setModal(True)
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 22)
        lay.setSpacing(14)

        title = QLabel("Hay una versión nueva de DVDY Studio")
        title.setObjectName("PageTitle")
        title.setWordWrap(True)
        lay.addWidget(title)

        new_tag = info["tag"].lstrip("vV")
        versions = QLabel(f"Tienes la versión <b>{APP_VERSION}</b> y ya está disponible la <b>{new_tag}</b>.")
        versions.setObjectName("Muted")
        versions.setTextFormat(Qt.RichText)
        versions.setWordWrap(True)
        lay.addWidget(versions)

        what = QLabel("QUÉ CAMBIA")
        what.setObjectName("Label")
        lay.addWidget(what)
        notes = QTextBrowser()
        notes.setObjectName("Notes")
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(updater.brief_notes(info["notes"]) or "Mejoras y correcciones.")
        notes.setMinimumHeight(170)
        notes.setMaximumHeight(300)
        notes.setAccessibleName("Novedades de la versión nueva")
        lay.addWidget(notes, 1)

        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setRange(0, 1000)
        self.bar.hide()
        lay.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        self.status.hide()
        lay.addWidget(self.status)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.update_btn = button("Actualizar", self._update, primary=True)
        self.update_btn.setDefault(True)
        size = f" ({fmt_size(info['zip_size'])})" if info.get("zip_size") else ""
        self.update_btn.setToolTip(f"Descarga la versión nueva{size} y reinicia el programa")
        self.later_btn = button("Recordarme después", self._later)
        self.later_btn.setToolTip("Vuelve a avisar la próxima vez que abras el programa")
        self.skip_btn = button("Saltar esta versión", self._skip)
        self.skip_btn.setToolTip("No avisa de nuevo hasta que salga una versión más nueva")
        row.addWidget(self.update_btn)
        row.addWidget(self.later_btn)
        row.addWidget(self.skip_btn)
        row.addStretch(1)
        lay.addLayout(row)

        self.sig = _Signals()
        self.sig.progress.connect(self._on_progress)
        self.sig.status.connect(self._say)
        self.sig.ready.connect(self._on_ready)
        self.sig.failed.connect(self._on_failed)

    # ------------------------------------------------------------------
    def _say(self, text):
        self.status.setText(text)
        self.status.setVisible(bool(text))

    def _later(self):
        if self._busy:
            self._cancel.set()
            self._say("Cancelando…")
            return
        self.choice = REMIND
        self.reject()

    def _skip(self):
        cfg["skip_update_version"] = self.info["tag"]
        cfg.save()
        self.choice = SKIP
        self.reject()

    def closeEvent(self, e):
        if self._busy:
            self._cancel.set()
            e.ignore()
            return
        super().closeEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._busy:
            self._cancel.set()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------------
    def _update(self):
        ok, reason = updater.can_self_update()
        if not ok or not self.info.get("zip_url"):
            # Sin actualización automática: abrir la página del release para bajarlo a mano
            QDesktopServices.openUrl(QUrl(self.info["url"]))
            self._say(f"{reason} Se abrió la página de descarga en el navegador." if reason else
                      "Se abrió la página de descarga en el navegador.")
            self.choice = REMIND
            return
        if self.manager is not None and self.manager.active_count():
            r = QMessageBox.question(self, "Hay descargas en curso",
                                     "Para actualizar, el programa se va a cerrar y las descargas en curso se van a "
                                     "detener (las pausadas pueden seguir después). ¿Actualizar ahora?")
            if r != QMessageBox.Yes:
                return
        self._busy = True
        self._cancel.clear()
        self.update_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.later_btn.setText("Cancelar")
        self.bar.show()
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            work, new_dir = updater.download_and_prepare(
                self.info["zip_url"],
                progress=lambda d, t: self.sig.progress.emit(d, t),
                cancel=self._cancel,
                status=lambda s: self.sig.status.emit(s))
            self.sig.ready.emit(work, new_dir)
        except Exception as e:  # noqa: BLE001
            from .deps import Cancelled
            self.sig.failed.emit("" if isinstance(e, Cancelled) else str(e))

    def _on_progress(self, done, total):
        if total:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(done * 1000 / total))
            self._say(f"Descargando la versión nueva… {fmt_size(done)} de {fmt_size(total)}")
        else:
            self.bar.setRange(0, 0)

    def _on_failed(self, msg):
        self._busy = False
        self.bar.hide()
        self.update_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.later_btn.setText("Recordarme después")
        if msg:
            from .errors import friendly
            self._say("No se pudo actualizar: " + friendly(msg)[0])
            self.status.setToolTip(msg)
        else:
            self._say("Actualización cancelada.")

    def _on_ready(self, work, new_dir):
        self._say("Listo. El programa se va a cerrar, se actualiza y se vuelve a abrir solo.")
        self.bar.setValue(1000)
        QApplication.processEvents()
        updater.launch_replacer(work, new_dir, updater.install_dir(), os.getpid())
        self.choice = UPDATE
        self._busy = False
        if self.manager is not None:
            self.manager.cancel_all()
        app = QApplication.instance()
        for w in app.topLevelWidgets():
            if hasattr(w, "skip_close_prompt"):
                w.skip_close_prompt = True
        self.accept()
        app.quit()
