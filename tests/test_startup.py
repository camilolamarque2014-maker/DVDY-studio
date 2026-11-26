"""Al arrancar solo debe abrirse la ventana principal.

Un control sin contenedor al que se le llama setVisible(True)/show() se vuelve una ventana
propia por un instante. En Ubuntu, GNOME le entrega a esa ventana fugaz el aviso de inicio
de la app y deja el cursor «cargando» hasta agotar la espera.
"""
import os
import unittest

from tests import _env  # noqa: F401

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT and _env.HAS_YTDLP, "PySide6 o yt-dlp no están instalados")
class StartupWindowsTest(unittest.TestCase):
    def test_solo_se_muestra_la_ventana_principal(self):
        from dvdy.config import cfg
        cfg["tutorial_done"] = True
        cfg["check_updates"] = False
        app = QApplication.instance() or QApplication([])
        from dvdy.theme import apply_palette, build_qss, load_fonts
        load_fonts()
        apply_palette(app, "dark")
        app.setStyleSheet(build_qss("dark"))

        shown = []

        class Spy(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == QEvent.Show and obj.isWidgetType() and obj.isWindow():
                    shown.append(f"{type(obj).__name__} {obj.objectName()!r}")
                return False

        spy = Spy()
        app.installEventFilter(spy)
        try:
            from dvdy.main_window import MainWindow
            w = MainWindow()
            w._startup = lambda: None
            self.assertEqual(shown, [], "ventanas abiertas antes de la principal")
            w.show()
            app.processEvents()
            self.assertEqual(len(shown), 1, shown)
            self.assertTrue(shown[0].startswith("MainWindow"), shown)
            w.skip_close_prompt = True
            w.close()
        finally:
            app.removeEventFilter(spy)


if __name__ == "__main__":
    unittest.main()
