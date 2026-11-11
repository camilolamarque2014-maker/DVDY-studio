"""Ventana principal: barra lateral de navegación + páginas."""
import re

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QSystemTrayIcon,
    QVBoxLayout, QWidget,
)

from .config import APP_NAME, APP_VERSION, cfg
from .page_convert import ConvertPage
from .page_download import DownloadPage
from .page_misc import HistoryPage, InspectPage, LogPage
from .page_playlist import PlaylistPage
from .page_queue import QueuePage
from .page_search import SearchPage
from .page_settings import SettingsPage
from .page_tools import ToolsPage
from .tasks import DONE, ERROR, TaskManager
from .theme import ICON, app_icon, build_qss
from .utils import AUDIO_EXTS, VIDEO_EXTS, ext_of
from .widgets import ModeSwitch, button, label

ADVANCED_ONLY = ("tools", "inspect", "log")  # secciones ocultas en modo simple

URL_RE = re.compile(r"^https?://\S+$")


class NavButton(QPushButton):
    def __init__(self, icon, text):
        super().__init__()
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(12)
        ic = QLabel(ICON[icon])
        ic.setObjectName("NavIcon")
        ic.setAttribute(Qt.WA_TransparentForMouseEvents)
        tx = QLabel(text)
        tx.setAttribute(Qt.WA_TransparentForMouseEvents)
        tx.setObjectName("NavText")
        self.toggled.connect(self._on_toggled)
        self.text_lbl = tx
        self.badge = QLabel("")
        self.badge.setObjectName("NavBadge")
        self.badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.badge.hide()
        lay.addWidget(ic)
        lay.addWidget(tx, 1)
        lay.addWidget(self.badge)
        self.setMinimumHeight(40)

    def _on_toggled(self, on):
        self.text_lbl.setProperty("active", on)
        self.text_lbl.style().unpolish(self.text_lbl)
        self.text_lbl.style().polish(self.text_lbl)

    def set_badge(self, n):
        self.badge.setText(str(n))
        self.badge.setVisible(n > 0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}")
        self.setWindowIcon(app_icon(cfg["accent"]))
        self.resize(1240, 860)
        self.setMinimumSize(980, 640)
        self.setAcceptDrops(True)
        self.manager = TaskManager()

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # ---------- Barra lateral ----------
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 20, 14, 16)
        sl.setSpacing(3)
        logo = QLabel()
        logo.setPixmap(app_icon(cfg["accent"]).pixmap(40, 40))
        self.logo = logo
        title = label(APP_NAME, "AppTitle")
        sub = label("yt-dlp + FFmpeg", "AppSubtitle")
        tv = QVBoxLayout()
        tv.setSpacing(0)
        tv.addWidget(title)
        tv.addWidget(sub)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(logo)
        head.addLayout(tv, 1)
        sl.addLayout(head)
        sl.addSpacing(16)

        # Interruptor Simple / Avanzado
        mode_box = QFrame()
        mode_box.setObjectName("ModeBox")
        ml = QHBoxLayout(mode_box)
        ml.setContentsMargins(12, 8, 12, 8)
        self.mode_switch = ModeSwitch(cfg["ui_mode"] != "simple")
        self.mode_switch.setToolTip("Simple: solo lo esencial.  Avanzado: todas las opciones de yt-dlp y FFmpeg.")
        ml.addWidget(self.mode_switch)
        sl.addWidget(mode_box)
        sl.addSpacing(10)

        self.stack = QStackedWidget()
        self.nav = {}

        go_queue = lambda: self.go("queue")  # noqa: E731
        self.pages = {
            "download": DownloadPage(self.manager, go_queue),
            "playlist": PlaylistPage(self.manager, go_queue),
            "search": SearchPage(self.manager, go_queue),
            "queue": QueuePage(self.manager),
            "convert": ConvertPage(self.manager, go_queue),
            "tools": ToolsPage(self.manager, go_queue),
            "inspect": InspectPage(),
            "history": HistoryPage(self._redownload),
            "log": LogPage(),
            "settings": SettingsPage(self.manager),
        }
        sections = [
            ("DESCARGAR", [("download", "download", "Descargar"), ("playlist", "music", "Playlists y música"),
                           ("search", "search", "Buscar"), ("queue", "queue", "Cola")]),
            ("FFMPEG", [("convert", "convert", "Convertir"), ("tools", "tools", "Herramientas"),
                        ("inspect", "info", "Inspector")]),
            ("GENERAL", [("history", "history", "Historial"), ("log", "log", "Registro"),
                         ("settings", "settings", "Ajustes")]),
        ]
        for sec, items in sections:
            s = label(sec, "AppSubtitle")
            s.setContentsMargins(12, 10, 0, 4)
            sl.addWidget(s)
            for key, icon, text in items:
                b = NavButton(icon, text)
                b.clicked.connect(lambda _=False, k=key: self.go(k))
                self.nav[key] = b
                sl.addWidget(b)
                self.stack.addWidget(self.pages[key])
        sl.addStretch(1)
        self.footer = label("", "SideFooter", wrap=True)
        sl.addWidget(self.footer)
        sl.addWidget(label(f"v{APP_VERSION}", "SideFooter"))
        h.addWidget(side)

        # ---------- Contenido ----------
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        self.banner = self._make_banner()
        right.addWidget(self.banner)
        right.addWidget(self.stack, 1)
        h.addLayout(right, 1)

        # ---------- Conexiones ----------
        self.pages["download"].open_playlist.connect(self._open_playlist)
        self.pages["search"].open_download.connect(lambda u: (self.go("download"), self.pages["download"].set_url(u)))
        self.pages["settings"].theme_changed.connect(self.apply_theme)
        self.manager.log.connect(self.pages["log"].append)
        self.manager.counts_changed.connect(self._counts)
        self.manager.task_finished.connect(self._finished)
        self.manager.task_finished.connect(lambda *_: self.pages["history"].refresh())

        self.tray = QSystemTrayIcon(app_icon(cfg["accent"]), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(lambda *_: (self.showNormal(), self.activateWindow()))
        self.tray.show()

        self._last_clip = QGuiApplication.clipboard().text()
        QGuiApplication.clipboard().dataChanged.connect(self._clipboard)

        geo = cfg["window_geometry"]
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
            except Exception:
                pass
        self.mode_switch.changed.connect(self.set_advanced)
        QTimer.singleShot(500, self.check_components)
        self.go("download")
        self.set_advanced(self.mode_switch.is_advanced(), save=False)
        self._counts(0, 0)

    def check_components(self):
        """Al iniciar: si faltan FFmpeg o Deno, ofrece descargarlos automáticamente."""
        from . import deps
        missing = deps.missing_components()
        if not missing or cfg["skip_component_check"] == ",".join(missing):
            return
        from .setup_dialog import SetupDialog
        dlg = SetupDialog(self, components=missing, intro=(
            "Para funcionar, DVDY Studio necesita estos programas gratuitos y no los encontró en tu equipo. "
            "¿Quieres que los descargue e instale automáticamente? Solo se hace una vez."))
        dlg.exec()
        if dlg.changed:
            self.pages["settings"].check()
        elif deps.missing_components():
            # Si el usuario dice «Ahora no», no volver a preguntar hasta que cambie algo
            cfg["skip_component_check"] = ",".join(missing)
            cfg.save()
            self.tray.showMessage("Faltan componentes", "Puedes instalarlos cuando quieras desde Ajustes.",
                                  QSystemTrayIcon.Warning, 5000)

    def set_advanced(self, advanced, save=True):
        simple = not advanced
        for key in ADVANCED_ONLY:
            self.nav[key].setVisible(advanced)
        for page in self.pages.values():
            if hasattr(page, "set_simple"):
                page.set_simple(simple)
        current = next((k for k, p in self.pages.items() if p is self.stack.currentWidget()), "download")
        if simple and current in ADVANCED_ONLY:
            self.go("download")
        if save:
            cfg["ui_mode"] = "advanced" if advanced else "simple"
            cfg.save()

    # ------------------------------------------------------------------
    def _make_banner(self):
        f = QFrame()
        f.setObjectName("Banner")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(14, 8, 8, 8)
        self.banner_lbl = label("")
        lay.addWidget(self.banner_lbl, 1)
        lay.addWidget(button("Video", lambda: self._banner_act("video")))
        lay.addWidget(button("Audio", lambda: self._banner_act("audio")))
        lay.addWidget(button("Abrir en Descargar", lambda: self._banner_act("open")))
        lay.addWidget(button("Ignorar", lambda: self.banner.hide(), flat=True))
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(28, 12, 28, 0)
        wl.addWidget(f)
        wrap.hide()
        return wrap

    def _clipboard(self):
        if not cfg["clipboard_monitor"]:
            return
        t = QGuiApplication.clipboard().text().strip()
        if t == self._last_clip:
            return
        self._last_clip = t
        if URL_RE.match(t):
            self._banner_url = t
            fm = self.banner_lbl.fontMetrics()
            self.banner_lbl.setText("Enlace detectado: " + fm.elidedText(t, Qt.ElideMiddle, 420))
            self.banner.show()

    def _banner_act(self, what):
        url = getattr(self, "_banner_url", "")
        self.banner.hide()
        if not url:
            return
        if what == "open":
            self.go("download")
            self.pages["download"].set_url(url)
        else:
            self.pages["search"].quick(url, {"title": url}, what == "audio")
            self.go("queue")

    def go(self, key):
        for k, b in self.nav.items():
            b.setChecked(k == key)
        self.stack.setCurrentWidget(self.pages[key])
        if key == "history":
            self.pages["history"].refresh()

    def _open_playlist(self, url):
        self.go("playlist")
        self.pages["playlist"].set_url(url)

    def _redownload(self, url):
        self.go("download")
        self.pages["download"].set_url(url)

    def _counts(self, active, total):
        self.nav["queue"].set_badge(active)
        self.footer.setText(f"{active} tarea(s) activa(s)" if active else "Sin tareas activas")

    def _finished(self, task):
        if not cfg["notify_on_finish"] or task.kind == "other" and task.status == DONE:
            return
        if task.status == DONE:
            self.tray.showMessage("Tarea completada", task.title, QSystemTrayIcon.Information, 4000)
        elif task.status == ERROR:
            self.tray.showMessage("Error", f"{task.title}\n{task.error[:200]}", QSystemTrayIcon.Warning, 6000)

    def apply_theme(self):
        app = QApplication.instance()
        app.setStyleSheet(build_qss(cfg["theme"], cfg["accent"]))
        icon = app_icon(cfg["accent"])
        self.setWindowIcon(icon)
        self.logo.setPixmap(icon.pixmap(40, 40))
        self.tray.setIcon(icon)

    # ---------- Arrastrar y soltar a la ventana ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        if md.hasUrls() and md.urls()[0].isLocalFile():
            files = [u.toLocalFile() for u in md.urls() if u.isLocalFile()]
            media = [f for f in files if ext_of(f) in AUDIO_EXTS | VIDEO_EXTS]
            if media:
                self.go("convert")
                self.pages["convert"].add_files(media)
            return
        text = md.text().strip() if md.hasText() else (md.urls()[0].toString() if md.hasUrls() else "")
        if URL_RE.match(text):
            self.go("download")
            self.pages["download"].set_url(text)

    def closeEvent(self, e):
        cfg["window_geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        cfg.save()
        if self.manager.active_count():
            from PySide6.QtWidgets import QMessageBox
            r = QMessageBox.question(self, "Tareas en curso",
                                     "Hay tareas en curso. Si sales se detendrán (las descargas podrán reanudarse luego). "
                                     "¿Salir de todos modos?")
            if r != QMessageBox.Yes:
                e.ignore()
                return
            self.manager.cancel_all()
        self.tray.hide()
        e.accept()
