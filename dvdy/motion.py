"""Movimiento de la interfaz, según los principios de ux-motion.

- Entrar con ease-out, salir con ease-in, desplazarse con ease-in-out. Lineal solo en progreso.
- Tiempos: respuesta 100-150 ms, transiciones 150-300 ms, paneles grandes hasta ~400 ms.
- Cerrar más rápido que abrir (la salida dura la mitad o un tercio de la entrada).
- Lo que se usa mucho apenas se anima; lo de una sola vez (el tutorial) puede lucirse más.
- Todo se puede interrumpir: cada animación arranca desde el valor actual.
- Si el sistema (Windows o GNOME) tiene las animaciones desactivadas (o el usuario las apaga en Ajustes), no hay movimiento.
"""
import ctypes

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

# Duraciones (ms)
PRESS = 100
HOVER = 120
UI = 200
ENTER = 300
PANEL = 380
EXIT = 120     # salidas: rápidas
EXIT_UI = 150


def _bezier(x1, y1, x2, y2):
    c = QEasingCurve(QEasingCurve.BezierSpline)
    c.addCubicBezierSegment(QPointF(x1, y1), QPointF(x2, y2), QPointF(1, 1))
    return c


def ease_out():
    return _bezier(0.16, 1, 0.3, 1)


def ease_in():
    return _bezier(0.7, 0, 0.84, 0)


def ease_in_out():
    return _bezier(0.65, 0, 0.35, 1)


def spring_out():
    """Ease-out con un pequeño rebote (follow through, amortiguación ~0.75)."""
    c = QEasingCurve(QEasingCurve.OutBack)
    c.setOvershoot(1.2)
    return c


_windows_motion = None


def _windows_allows_motion():
    """Lee «Mostrar animaciones en Windows» (SPI_GETCLIENTAREAANIMATION) o, en Linux, la opción de GNOME."""
    global _windows_motion
    if _windows_motion is None:
        from .system import IS_WINDOWS, gnome_animations_enabled
        if not IS_WINDOWS:
            _windows_motion = gnome_animations_enabled()
            return _windows_motion
        try:
            value = ctypes.c_int(1)
            ok = ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(value), 0)
            _windows_motion = bool(value.value) if ok else True
        except Exception:
            _windows_motion = True
    return _windows_motion


def enabled():
    from .config import cfg
    return bool(cfg["animations"]) and _windows_allows_motion()


# Las animaciones en curso se guardan aquí para que no las recolecte Python a mitad de camino
_running = {}


def _keep(owner, key, anim):
    old = _running.pop((id(owner), key), None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass  # ya destruida junto con su widget
    k = (id(owner), key)
    _running[k] = anim
    anim.finished.connect(lambda: _running.get(k) is anim and _running.pop(k, None))
    anim.destroyed.connect(lambda *_: _running.get(k) is anim and _running.pop(k, None))


def stop(owner, key):
    old = _running.pop((id(owner), key), None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass  # ya destruida junto con su widget


def animate(owner, key, start, end, ms, curve, on_value, on_done=None):
    """Interpola entre start y end llamando a on_value. Interrumpible: una nueva llamada con la
    misma clave detiene la anterior (llámala con el valor actual como start)."""
    if not enabled() or ms <= 0:
        on_value(end)
        if on_done:
            on_done()
        return None
    a = QVariantAnimation(owner)
    a.setStartValue(start)
    a.setEndValue(end)
    a.setDuration(ms)
    a.setEasingCurve(curve)
    a.valueChanged.connect(on_value)
    if on_done:
        a.finished.connect(on_done)
    _keep(owner, key, a)
    a.start()
    return a


def fade(widget, start, end, ms, curve=None, on_done=None, key="fade"):
    """Fundido con un efecto de opacidad que se quita al terminar (no deja costo de dibujo)."""
    if not enabled():
        widget.setGraphicsEffect(None)
        if on_done:
            on_done()
        return None
    eff = widget.graphicsEffect()
    if not isinstance(eff, QGraphicsOpacityEffect):
        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(start)
        widget.setGraphicsEffect(eff)
    else:
        start = eff.opacity()  # desde el valor actual: interrumpible

    def done():
        if end >= 1.0:
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                pass
        if on_done:
            on_done()

    a = QPropertyAnimation(eff, b"opacity", widget)
    a.setStartValue(start)
    a.setEndValue(end)
    a.setDuration(ms)
    a.setEasingCurve(curve or (ease_out() if end > start else ease_in()))
    a.finished.connect(done)
    _keep(widget, key, a)
    a.start()
    return a


def fade_in(widget, ms=UI, on_done=None):
    return fade(widget, 0.0, 1.0, ms, ease_out(), on_done)


def fade_out(widget, ms=EXIT, on_done=None):
    return fade(widget, 1.0, 0.0, ms, ease_in(), on_done)


def stagger_in(widgets, step=40, ms=UI, cap=6, first_delay=0):
    """Hace entrar varios widgets en cascada (step ms entre cada uno; pasados `cap`, entran juntos)."""
    from PySide6.QtCore import QTimer
    from shiboken6 import isValid
    if not enabled():
        return
    for i, w in enumerate(widgets):
        eff = QGraphicsOpacityEffect(w)
        eff.setOpacity(0.0)
        w.setGraphicsEffect(eff)

        def go(w=w):
            if isValid(w):
                fade(w, 0.0, 1.0, ms, ease_out())
        QTimer.singleShot(first_delay + step * min(i, cap), go)


def window_in(win, ms=UI):
    """Aparición de una ventana: fundido de la ventana entera."""
    if not enabled():
        return
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.platformName() == "wayland":
        return  # Wayland no permite cambiar la opacidad de una ventana
    win.setWindowOpacity(0.0)
    a = QPropertyAnimation(win, b"windowOpacity", win)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setDuration(ms)
    a.setEasingCurve(ease_out())
    _keep(win, "window", a)
    a.start()


def shake(widget, distance=6, ms=300):
    """Sacudón corto de error: tres idas y vueltas en ~300 ms (feedback exagerado, ux-motion §9)."""
    if not enabled():
        return
    base = widget.pos()
    a = QVariantAnimation(widget)
    a.setStartValue(0.0)
    a.setEndValue(1.0)
    a.setDuration(ms)

    def step(t):
        import math
        # seno amortiguado: 3 oscilaciones que se apagan
        dx = distance * math.sin(t * math.pi * 6) * (1 - t)
        widget.move(base.x() + int(round(dx)), base.y())

    a.valueChanged.connect(step)
    a.finished.connect(lambda: widget.move(base))
    _keep(widget, "shake", a)
    a.start()
