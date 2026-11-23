"""Ventana principal: barra superior con la marca, el menú y el interruptor Simple / Avanzado."""
import re

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget,
    QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .config import APP_NAME, APP_VERSION, cfg
from .page_convert import ConvertPage
from .page_download import DownloadPage
from .page_misc import HistoryPage, InspectPage, LogPage
from .page_playlist import PlaylistPage
from .page_search import SearchPage
from .page_settings import SettingsPage
from .page_tools import ToolsPage
from .tasks import DONE, ERROR, TaskManager
from .theme import app_icon, build_qss, current, resolve_theme
from .utils import AUDIO_EXTS, VIDEO_EXTS, ext_of
from .widgets import ModeSwitch, button, label

ADVANCED_ONLY = ("tools", "inspect", "log")  # secciones ocultas en modo Simple
NAV = [("download", "Descargar"), ("playlist", "Playlists"), ("search", "Buscar"), ("convert", "Convertir"),
       ("tools", "Herramientas"), ("inspect", "Inspector"), ("history", "Historial"), ("log", "Registro"),
       ("settings", "Ajustes")]

URL_RE = re.compile(r"^https?://\S+$")


class NavButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("TopNav")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._fit(text)

    def _fit(self, text):
        """Reserva el ancho del texto en negrita para que la sección activa no se corte."""
        from PySide6.QtGui import QFont, QFontMetrics
        from .theme import FONT_TEXT, SIZE_BODY
        f = QFont(FONT_TEXT)
        f.setPointSizeF(SIZE_BODY)
        f.setBold(True)
        self.setMinimumWidth(QFontMetrics(f).horizontalAdvance(text) + 30)

    def setText(self, text):
        super().setText(text)
        self._fit(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1320, 860)
        self.setMinimumSize(1080, 680)
        self.setAcceptDrops(True)
        self.manager = TaskManager()

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ---------- Barra superior ----------
        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(60)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(28, 0, 22, 0)
        tl.setSpacing(4)
        self.wordmark = QLabel()
        self.wordmark.setObjectName("Wordmark")
        self.wordmark.setAccessibleName(APP_NAME)
        tl.addWidget(self.wordmark)
        tl.addSpacing(26)
        self.nav = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, text in NAV:
            b = NavButton(text)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            group.addButton(b)
            self.nav[key] = b
            tl.addWidget(b)
        self.active_dot = QLabel()
        self.active_dot.setObjectName("NavDot")
        self.active_dot.setFixedSize(6, 6)
        self.active_dot.setToolTip("Hay descargas en curso")
        self.active_dot.hide()
        tl.addStretch(1)
        self.mode_switch = ModeSwitch(cfg["ui_mode"] != "simple")
        tl.addWidget(self.mode_switch)
        v.addWidget(top)

        # ---------- Aviso de enlace copiado ----------
        self.banner = self._make_banner()
        v.addWidget(self.banner)

        # ---------- Páginas ----------
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        go_dl = lambda: self.go("download")  # noqa: E731
        self.pages = {
            "download": DownloadPage(self.manager, go_dl, self.task_action),
            "playlist": PlaylistPage(self.manager, go_dl),
            "search": SearchPage(self.manager, go_dl),
            "convert": ConvertPage(self.manager, go_dl),
            "tools": ToolsPage(self.manager, go_dl),
            "inspect": InspectPage(),
            "history": HistoryPage(self._redownload),
            "log": LogPage(),
            "settings": SettingsPage(self.manager),
        }
        for key, _ in NAV:
            self.stack.addWidget(self.pages[key])

        # ---------- Conexiones ----------
        self.pages["download"].open_playlist.connect(self._open_playlist)
        self.pages["search"].open_download.connect(lambda u: (self.go("download"), self.pages["download"].set_url(u)))
        self.pages["settings"].theme_changed.connect(self.apply_theme)
        self.pages["settings"].components_requested.connect(lambda *_: self.open_components())
        self.pages["settings"].tutorial_requested.connect(lambda *_: self.show_tutorial())
        self.manager.log.connect(self.pages["log"].append)
        self.manager.counts_changed.connect(self._counts)
        self.manager.task_finished.connect(self._finished)
        self.manager.task_finished.connect(lambda *_: self.pages["history"].refresh())
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(lambda *_: self.apply_theme())
        except Exception:
            pass

        self.tray = QSystemTrayIcon(app_icon(), self)
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
        self.go("download")
        self.set_advanced(self.mode_switch.is_advanced(), save=False)
        self._paint_wordmark()
        self._counts(0, 0)
        QTimer.singleShot(0, lambda: self.pages["download"].urls.setFocus())
        # Al abrir, una ventana por vez: componentes → tutorial (la primera vez) → aviso de versión nueva
        QTimer.singleShot(500, self._startup)

    # ------------------------------------------------------------------
    def _paint_wordmark(self):
        self.wordmark.setText(f'DVDY<span style="color:{current["amber"]}">·</span>STUDIO')
        self.wordmark.setToolTip(f"{APP_NAME} {APP_VERSION}")

    def _make_banner(self):
        f = QFrame()
        f.setObjectName("Banner")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(14, 8, 8, 8)
        self.banner_lbl = label("")
        lay.addWidget(self.banner_lbl, 1)
        lay.addWidget(button("Video", lambda: self._banner_act("video")))
        lay.addWidget(button("Música", lambda: self._banner_act("audio")))
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
            self.banner_lbl.setText("Copiaste un enlace: " + fm.elidedText(t, Qt.ElideMiddle, 420))
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
            self.go("download")

    def go(self, key):
        if self.nav[key].isHidden() and key in ADVANCED_ONLY:
            key = "download"
        self.nav[key].setChecked(True)
        if isinstance(QApplication.focusWidget(), NavButton):
            self.nav[key].setFocus(Qt.OtherFocusReason)
        page = self.pages[key]
        if self.stack.currentWidget() is not page:
            self.stack.setCurrentWidget(page)
            # Se cambia de sección muy seguido: solo un fundido corto, sin desplazamiento
            from . import motion
            motion.fade(page, 0.0, 1.0, 150, motion.ease_out())
        if key == "history":
            self.pages["history"].refresh()

    def _open_playlist(self, url):
        self.go("playlist")
        self.pages["playlist"].set_url(url)

    def _redownload(self, url):
        self.go("download")
        self.pages["download"].set_url(url)

    def _counts(self, active, total):
        b = self.nav["download"]
        b.setText(f"Descargar  ·  {active}" if active else "Descargar")
        b.setToolTip(f"{active} descargas en curso o en espera" if active else "")

    def _finished(self, task):
        if not cfg["notify_on_finish"] or task.kind == "other" and task.status == DONE:
            return
        if task.status == DONE:
            self.tray.showMessage("Descarga lista" if task.kind == "download" else "Tarea lista",
                                  task.title, QSystemTrayIcon.Information, 4000)
        elif task.status == ERROR:
            self.tray.showMessage("No se pudo completar", f"{task.title}\n{task.error}", QSystemTrayIcon.Warning, 6000)

    # ---------- Acciones sugeridas por un error ----------
    def task_action(self, task, action):
        if action == "nocookies":
            if hasattr(task, "opts"):
                task.opts.pop("cookiesfrombrowser", None)
            self.manager.resume(task)
        elif action == "ffmpeg":
            self.open_components(("ffmpeg",), ["ffmpeg"], then_retry=task)
        elif action == "update":
            self.open_components(("yt-dlp",), ["yt-dlp"])
        elif action == "browser":
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(getattr(task, "url", "")))
        else:
            self.manager.resume(task)

    def open_components(self, keys=("ffmpeg", "deno", "yt-dlp"), preselect=None, then_retry=None):
        from . import deps
        from .setup_dialog import SetupDialog
        if preselect is None:
            preselect = deps.missing_components()
        dlg = SetupDialog(self, components=keys, preselect=preselect)
        dlg.exec()
        if dlg.changed:
            self.pages["settings"].check()
            if then_retry is not None and not deps.missing_components():
                self.manager.resume(then_retry)

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
            cfg["skip_component_check"] = ",".join(missing)
            cfg.save()
            self.tray.showMessage("Faltan componentes", "Puedes instalarlos cuando quieras desde Ajustes.",
                                  QSystemTrayIcon.Warning, 5000)

    def _startup(self):
        self.check_components()  # modal: espera a que se cierre
        if not cfg["tutorial_done"]:
            self.show_tutorial()
        self.check_updates()     # consulta en segundo plano; su ventana sale después

    def show_tutorial(self):
        from .tutorial import TutorialDialog
        TutorialDialog(self).exec()

    def check_updates(self):
        """Consulta en segundo plano si hay una versión nueva publicada en GitHub."""
        if not cfg["check_updates"]:
            return
        from .updater import newer_release
        from .widgets import run_async
        run_async(newer_release, cfg["skip_update_version"], on_done=self._show_update, on_error=lambda *_: None)

    def _show_update(self, info):
        if not info:
            return
        if QApplication.activeModalWidget() is not None:
            # Hay otra ventana abierta (p. ej. componentes): reintentar en un momento
            QTimer.singleShot(3000, lambda: self._show_update(info))
            return
        from .update_dialog import UpdateDialog
        UpdateDialog(info, self.manager, self).exec()

    def set_advanced(self, advanced, save=True):
        simple = not advanced
        for key in ADVANCED_ONLY:
            self.nav[key].setVisible(advanced)
        for page in self.pages.values():
            if hasattr(page, "set_simple"):
                page.set_simple(simple)
        current_key = next((k for k, p in self.pages.items() if p is self.stack.currentWidget()), "download")
        if simple and current_key in ADVANCED_ONLY:
            self.go("download")
        if save:
            cfg["ui_mode"] = "advanced" if advanced else "simple"
            cfg.save()

    def apply_theme(self):
        app = QApplication.instance()
        from .theme import apply_palette
        apply_palette(app, resolve_theme(cfg["theme"]))
        app.setStyleSheet(build_qss(resolve_theme(cfg["theme"])))
        self._paint_wordmark()
        for w in app.allWidgets():
            w.update()

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
        if self.manager.active_count() and not getattr(self, "skip_close_prompt", False):
            from PySide6.QtWidgets import QMessageBox
            r = QMessageBox.question(self, "Hay descargas en curso",
                                     "Si cierras ahora, se detienen. Las descargas pausadas pueden seguir después. "
                                     "¿Cerrar de todos modos?")
            if r != QMessageBox.Yes:
                e.ignore()
                return
            self.manager.cancel_all()
        self.tray.hide()
        e.accept()
