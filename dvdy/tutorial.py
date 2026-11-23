"""Tutorial de primer inicio: cinco pasos cortos con escenas animadas dibujadas a mano.

Se ve una sola vez (después de instalar los componentes y antes del aviso de actualización),
así que admite más movimiento que el resto de la app (ux-motion: la frecuencia manda).
Reglas que sigue:
- Cada escena es una línea de tiempo: los elementos entran en cascada de 40 ms con ease-out.
- El desplazamiento entre lugares usa ease-in-out; el salto del punto de banda va en arco.
- El progreso de la descarga de ejemplo es lineal (es una barra de progreso).
- El cambio de paso tiene dirección: Siguiente entra desde la derecha, Atrás desde la izquierda.
  Entra en 300 ms y sale en 150 ms. Se puede interrumpir pulsando varias veces.
- Con las animaciones desactivadas, cada escena muestra directamente su cuadro final.
"""
import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from . import motion
from .config import cfg
from .theme import current, label_font
from .widgets import button

_OUT = motion.ease_out()
_INOUT = motion.ease_in_out()
_SPRING = motion.spring_out()


def seg(t, start, dur, curve=_OUT):
    """Avance (0-1) de un tramo de la línea de tiempo que empieza en `start` y dura `dur` ms."""
    if t <= start:
        return 0.0
    if t >= start + dur:
        return 1.0
    x = (t - start) / dur
    return curve.valueForProgress(x) if curve is not None else x


def col(key, alpha=1.0):
    c = QColor(current[key])
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def lerp(a, b, k):
    return a + (b - a) * k


# ---------------------------------------------------------------------------
class Scene(QWidget):
    """Ilustración animada. Subclases: DURATION (ms) y draw(p, t)."""
    DURATION = 1500

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(220)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Clic para repetir la animación")
        self._t = float(self.DURATION)
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(self.DURATION))
        self._anim.setDuration(self.DURATION)
        self._anim.setEasingCurve(QEasingCurve.Linear)  # el reloj es lineal; cada tramo usa su curva
        self._anim.valueChanged.connect(self._tick)

    def play(self, delay_ms=0):
        self._anim.stop()
        if not motion.enabled():
            self._t = float(self.DURATION)
            self.update()
            return
        self._t = 0.0
        self.update()
        if delay_ms:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(delay_ms, self._anim.start)
        else:
            self._anim.start()

    def _tick(self, v):
        self._t = float(v)
        self.update()

    def mousePressEvent(self, e):
        self.play()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        # Lienzo: rectángulo redondeado del color de los paneles
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(col("line"), 1))
        p.setBrush(col("panel"))
        p.drawRoundedRect(r, 12, 12)
        p.setClipRect(r.adjusted(1, 1, -1, -1))
        self.draw(p, self._t)
        p.end()

    def draw(self, p, t):
        pass

    # --- piezas comunes ---
    def text(self, p, x, y, s, size=10.5, weight=QFont.Normal, color="text", alpha=1.0, align=Qt.AlignLeft,
             font=None, w=400):
        f = font or QFont("Archivo")
        if font is None:
            f.setPointSizeF(size)
            f.setWeight(weight)
        p.setFont(f)
        p.setPen(col(color, alpha))
        rx = x if align == Qt.AlignLeft else (x - w / 2 if align == Qt.AlignHCenter else x - w)
        p.drawText(QRectF(rx, y - 14, w, 28), align | Qt.AlignVCenter, s)

    def dial(self, p, left, right, base, value, on=True, alpha=1.0, labels=True):
        """Escala de dial como la de la app, con la aguja en `value` (0-100)."""
        span = right - left
        p.setPen(QPen(col("line", alpha), 1))
        p.drawLine(QPointF(left, base), QPointF(right, base))
        for i in range(41):
            x = left + span * i / 40
            major = i % 10 == 0
            p.setPen(QPen(col("muted" if major else "line2", alpha), 1))
            p.drawLine(QPointF(x, base - (16 if major else 10 if i % 5 == 0 else 6)), QPointF(x, base))
        if labels:
            p.setFont(label_font(8, spacing=110))
            p.setPen(col("muted", alpha))
            for i, lab in enumerate(("0", "25", "50", "75", "100")):
                x = left + span * i / 4
                p.drawText(QRectF(x - 20, base + 3, 40, 14), Qt.AlignHCenter | Qt.AlignTop, lab)
        x = left + span * value / 100
        c = col("amber" if on else "faint", alpha)
        p.setPen(QPen(c, 2))
        p.drawLine(QPointF(x, base - 36), QPointF(x, base + 1))
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(QPointF(x, base - 35), 3, 3)

    def check(self, p, cx, cy, k, scale=1.0, alpha=1.0):
        """Tilde dentro de un círculo marfil; k = cuánto del trazo está dibujado (0-1)."""
        if k <= 0:
            return
        p.save()
        p.translate(cx, cy)
        p.scale(scale, scale)
        p.setPen(Qt.NoPen)
        p.setBrush(col("text", alpha))
        p.drawEllipse(QPointF(0, 0), 11, 11)
        path = QPainterPath(QPointF(-5, 0.3))
        path.lineTo(-1.4, 3.8)
        path.lineTo(5.2, -3.8)
        part = QPainterPath(path.pointAtPercent(0))
        L = path.length()
        for i in range(1, 25):
            part.lineTo(path.pointAtPercent(path.percentAtLength(L * k * i / 24)))
        pen = QPen(col("bg", alpha), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(part)
        p.restore()

    def chip(self, p, x, y, w, s, primary, alpha):
        r = QRectF(x, y, w, 26)
        p.setPen(QPen(col("text" if primary else "line2", alpha), 1))
        p.setBrush(col("text", alpha) if primary else Qt.NoBrush)
        p.drawRoundedRect(r, 6, 6)
        f = QFont("Archivo")
        f.setPointSizeF(9)
        f.setWeight(QFont.Bold if primary else QFont.Normal)
        p.setFont(f)
        p.setPen(col("on_text" if primary else "text", alpha))
        p.drawText(r, Qt.AlignCenter, s)

    def cover(self, p, r, alpha=1.0, music=False):
        """Tapa de ejemplo: degradado sobrio con un triángulo de reproducción o una nota."""
        from PySide6.QtGui import QLinearGradient
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, col("raised", alpha))
        g.setColorAt(1, col("line2", alpha))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 8, 8)
        c = r.center()
        p.setBrush(col("text", 0.85 * alpha))
        if music:
            p.drawEllipse(QPointF(c.x() - 5, c.y() + 7), 6, 5)
            p.drawRect(QRectF(c.x(), c.y() - 12, 2, 19))
            p.drawRect(QRectF(c.x(), c.y() - 12, 9, 3))
        else:
            s = min(r.width(), r.height()) * 0.16
            tri = QPainterPath(QPointF(c.x() - s * 0.6, c.y() - s))
            tri.lineTo(c.x() + s, c.y())
            tri.lineTo(c.x() - s * 0.6, c.y() + s)
            tri.closeSubpath()
            p.drawPath(tri)


# ---------------------------------------------------------------------------
class WelcomeScene(Scene):
    """El nombre aparece y la aguja recorre el dial como quien busca una emisora."""
    DURATION = 1900

    def draw(self, p, t):
        w, h = self.width(), self.height()
        cx = w / 2
        # Marca: sube 10 px y aparece (0-350 ms)
        k = seg(t, 0, 350)
        f = QFont("Archivo Narrow")
        f.setPointSizeF(26)
        f.setWeight(QFont.Bold)
        f.setLetterSpacing(QFont.PercentageSpacing, 112)
        self.text(p, cx, 62 + 10 * (1 - k), "DVDY STUDIO", font=f, alpha=k, align=Qt.AlignHCenter, w=w)
        # Bajada (cascada: 60 ms después)
        k2 = seg(t, 60, 300)
        self.text(p, cx, 96 + 8 * (1 - k2), "Videos y música, sin consola", size=10.5, color="muted",
                  alpha=k2, align=Qt.AlignHCenter, w=w)
        # Dial: aparece (250 ms) y la aguja sintoniza: viaja, se pasa un poco y se asienta
        k3 = seg(t, 250, 300)
        sweep = seg(t, 450, 900, _INOUT)
        settle = seg(t, 1350, 450, _SPRING)
        value = lerp(0, 82, sweep) + lerp(0, -10, settle)
        self.dial(p, 70, w - 70, 176, value, on=t > 450, alpha=k3)


class PasteScene(Scene):
    """El enlace se escribe solo en el campo y aparece la tapa del video."""
    URL = "https://youtu.be/dQw4w9WgXcQ"
    TYPE_START, CHAR_MS = 250, 28
    DURATION = 250 + 28 * 28 + 900

    def draw(self, p, t):
        w = self.width()
        field = QRectF(40, 26, w - 80, 40)
        k = seg(t, 0, 250)
        typed_end = self.TYPE_START + len(self.URL) * self.CHAR_MS
        focused = self.TYPE_START <= t
        p.setPen(QPen(col("amber" if focused and t < typed_end + 250 else "line2", k), 1.2))
        p.setBrush(col("bg", k))
        p.drawRoundedRect(field, 9, 9)
        n = int(max(0, min(len(self.URL), (t - self.TYPE_START) / self.CHAR_MS)))
        shown = self.URL[:n]
        f = QFont("Archivo")
        f.setPointSizeF(10.5)
        p.setFont(f)
        if n == 0:
            p.setPen(col("faint", k))
            p.drawText(field.adjusted(14, 0, -14, 0), Qt.AlignVCenter | Qt.AlignLeft, "Pega aquí un enlace…")
        else:
            p.setPen(col("text"))
            p.drawText(field.adjusted(14, 0, -14, 0), Qt.AlignVCenter | Qt.AlignLeft, shown)
        # Cursor: parpadea mientras escribe y un rato después
        if focused and int(t / 450) % 2 == 0 or self.TYPE_START <= t < typed_end:
            cx = field.left() + 14 + p.fontMetrics().horizontalAdvance(shown) + 1
            p.setPen(QPen(col("text", k), 1.2))
            p.drawLine(QPointF(cx, field.center().y() - 9), QPointF(cx, field.center().y() + 9))
        # Tapa: aparece creciendo 0.94 → 1 con ease-out; luego título y datos en cascada
        start = typed_end + 120
        kc = seg(t, start, 320)
        cw, ch = 176, 99
        s = lerp(0.94, 1.0, kc)
        rect = QRectF(40, 88, cw, ch)
        p.save()
        p.translate(rect.center())
        p.scale(s, s)
        p.translate(-rect.center())
        if kc > 0:
            self.cover(p, rect, kc)
        p.restore()
        x = rect.right() + 22
        for i, (txt, size, weight, color) in enumerate((
                ("Mi canción favorita (video oficial)", 11.5, QFont.Bold, "text"),
                ("Artista  ·  3:33  ·  1,2 M vistas", 9.5, QFont.Normal, "muted"))):
            ki = seg(t, start + 120 + 40 * i, 260)
            self.text(p, x + 8 * (1 - ki), 112 + 26 * i, txt, size=size, weight=weight, color=color, alpha=ki,
                      w=w - x - 30)
        kb = seg(t, start + 220, 260)
        p.setPen(Qt.NoPen)
        p.setBrush(col("line", kb))
        p.drawRoundedRect(QRectF(x + 8 * (1 - kb), 166, 120, 6), 3, 3)


class BandScene(Scene):
    """El punto ámbar salta en arco de VIDEO a MÚSICA y cambia lo que se va a bajar."""
    DURATION = 2000
    BANDS = ("Video", "Música", "Solo video", "Formato manual")
    HOP_AT, HOP_MS = 650, 420

    def _positions(self, p):
        p.setFont(label_font(10.5, weight=700, spacing=118))
        fm = p.fontMetrics()
        widths = [fm.horizontalAdvance(b.upper()) + 22 for b in self.BANDS]
        gap = 26
        total = sum(widths) + gap * (len(widths) - 1)
        x = (self.width() - total) / 2
        out = []
        for wd in widths:
            out.append(x)
            x += wd + gap
        return out, widths

    def draw(self, p, t):
        xs, widths = self._positions(p)
        y = 70
        k = seg(t, 0, 300)
        hop = seg(t, self.HOP_AT, self.HOP_MS, None)
        landed = t >= self.HOP_AT + self.HOP_MS
        sel = 1 if landed else 0
        for i, (b, x) in enumerate(zip(self.BANDS, xs)):
            ki = seg(t, 40 * i, 260)
            yy = y + 6 * (1 - ki)
            p.setPen(QPen(col("muted", ki), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x + 7, yy), 5, 5)
            on = i == sel
            p.setFont(label_font(10.5, weight=700 if on else 600, spacing=118))
            p.setPen(col("text" if on else "muted", ki))
            p.drawText(QRectF(x + 22, yy - 14, 200, 28), Qt.AlignVCenter | Qt.AlignLeft, b.upper())
        # El punto: x con ease-in-out, y en parábola (arco), aterriza con un latido
        x0, x1 = xs[0] + 7, xs[1] + 7
        kx = _INOUT.valueForProgress(hop)
        px = lerp(x0, x1, kx)
        py = y - 22 * math.sin(math.pi * hop)
        pop = seg(t, self.HOP_AT + self.HOP_MS, 160)
        r = 5 * (lerp(1.45, 1.0, pop) if landed else lerp(1.0, 0.85, math.sin(math.pi * hop)))
        if landed and pop < 1:  # squash: al tocar se aplasta un poco y recupera
            rx, ry = r * lerp(1.25, 1.0, pop), r * lerp(0.8, 1.0, pop)
        else:
            rx = ry = r
        p.setPen(Qt.NoPen)
        p.setBrush(col("amber", k))
        p.drawEllipse(QPointF(px, py), rx, ry)
        # Casillas de abajo: cambian a lo de Música (cruce rápido)
        change = seg(t, self.HOP_AT + self.HOP_MS + 60, 260)
        tiles = (("Calidad", "1080p", "Mejor (320 kbps)"), ("Formato", "MP4", "MP3"),
                 ("Carpeta", "Descargas", "Música"))
        tw, gap = 150, 12
        x = (self.width() - (3 * tw + 2 * gap)) / 2
        for i, (cap, a, b) in enumerate(tiles):
            ki = seg(t, 120 + 40 * i, 280)
            r = QRectF(x + i * (tw + gap), 122 + 8 * (1 - ki), tw, 54)
            p.setPen(QPen(col("line", ki), 1))
            p.setBrush(col("bg", ki))
            p.drawRoundedRect(r, 8, 8)
            p.setFont(label_font(8, spacing=112))
            p.setPen(col("muted", ki))
            p.drawText(r.adjusted(12, 8, -8, 0), Qt.AlignTop | Qt.AlignLeft, cap.upper())
            f = QFont("Archivo")
            f.setPointSizeF(10.5)
            p.setFont(f)
            out_a = 1 - min(1, change * 2)
            in_b = max(0, change * 2 - 1)
            p.setPen(col("text", ki * out_a))
            p.drawText(r.adjusted(12, 26 - 4 * change, -8, 0), Qt.AlignTop | Qt.AlignLeft, a)
            p.setPen(col("text", ki * in_b))
            p.drawText(r.adjusted(12, 26 + 4 * (1 - in_b), -8, 0), Qt.AlignTop | Qt.AlignLeft, b)


class DialScene(Scene):
    """La descarga avanza en el dial y termina con la tilde y los botones Abrir."""
    RUN_AT, RUN_MS = 400, 1700
    DURATION = 400 + 1700 + 900

    def draw(self, p, t):
        w = self.width()
        k = seg(t, 0, 300)
        prog = seg(t, self.RUN_AT, self.RUN_MS, None)  # lineal: es progreso
        prog = math.floor(prog * 40) / 40  # llega a saltitos, como los datos de una descarga
        done = t >= self.RUN_AT + self.RUN_MS + 80
        p.setFont(label_font(8.5, spacing=116))
        p.setPen(col("muted", k))
        p.drawText(QRectF(40, 14, 200, 20), Qt.AlignLeft | Qt.AlignVCenter, "EN EL DIAL")
        self.dial(p, 50, w - 50, 80, 100 * prog if not done else 100, on=not done, alpha=k)
        # Fila de la tarea
        kr = seg(t, 80, 300)
        y = 112 + 8 * (1 - kr)
        cov = QRectF(40, y, 56, 56)
        self.cover(p, cov, kr, music=True)
        x = cov.right() + 14
        self.text(p, x, y + 10, "Mi canción favorita.mp3", size=11, weight=QFont.Bold, alpha=kr, w=w - x - 40)
        if not done:
            status = f"Bajando {int(prog * 100)} %  ·  2,4 MB/s" if t >= self.RUN_AT else "En espera"
            self.text(p, x, y + 30, status, size=9.5, color="amber_text" if t >= self.RUN_AT else "muted",
                      alpha=kr, w=w - x - 40)
            bar = QRectF(x, y + 46, w - x - 40, 3)
            p.setPen(Qt.NoPen)
            p.setBrush(col("line", kr))
            p.drawRoundedRect(bar, 1.5, 1.5)
            p.setBrush(col("amber", kr))
            p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * prog, 3), 1.5, 1.5)
        else:
            end = self.RUN_AT + self.RUN_MS + 80
            self.text(p, x, y + 30, "Listo  ·  en tu carpeta Música", size=9.5, color="muted", w=w - x - 40)
            # Final del recorrido (peak-end): la tilde aparece con un rebote y se dibuja
            self.check(p, cov.right() - 4, cov.bottom() - 4, seg(t, end, 300),
                       scale=lerp(0.4, 1.0, seg(t, end, 260, _SPRING)))
            for i, (s, prim, cw) in enumerate((("Abrir", True, 70), ("Mostrar en la carpeta", False, 150))):
                ki = seg(t, end + 160 + 40 * i, 240)
                self.chip(p, x + (0 if i == 0 else 78) + 6 * (1 - ki), y + 50, cw, s, prim, ki)


class ModeScene(Scene):
    """El interruptor pasa de Simple a Avanzado y aparecen más secciones."""
    FLIP_AT, FLIP_MS = 600, 260
    DURATION = 2000
    BASIC = ("Descargar",)
    EXTRA = ("Playlists", "Buscar", "Convertir", "Herramientas")

    def draw(self, p, t):
        w = self.width()
        k = seg(t, 0, 300)
        pos = seg(t, self.FLIP_AT, self.FLIP_MS, _INOUT)
        on = pos > 0.5
        f = QFont("Archivo")
        f.setPointSizeF(10.5)
        # «Simple [interruptor] Avanzado», centrado
        sw, sh = 44, 24
        cx = w / 2
        sx = cx - sw / 2
        sy = 40
        p.setFont(f)
        fm = p.fontMetrics()
        for label_, active, right in (("Simple", not on, False), ("Avanzado", on, True)):
            f.setWeight(QFont.Bold if active else QFont.Normal)
            p.setFont(f)
            p.setPen(col("text" if active else "muted", k))
            if right:
                p.drawText(QRectF(sx + sw + 10, sy - 2, 140, sh + 4), Qt.AlignVCenter | Qt.AlignLeft, label_)
            else:
                p.drawText(QRectF(sx - 150, sy - 2, 140, sh + 4), Qt.AlignVCenter | Qt.AlignRight, label_)
        track = QColor(col("line2", k))
        on_c = col("text", k)
        track = QColor(int(lerp(track.red(), on_c.red(), pos)), int(lerp(track.green(), on_c.green(), pos)),
                       int(lerp(track.blue(), on_c.blue(), pos)), int(255 * k))
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(sx, sy, sw, sh), sh / 2, sh / 2)
        d = sh - 6
        kx = sx + 3 + (sw - d - 6) * pos
        stretch = 4 * pos * (1 - pos) * 8  # squash & stretch a mitad de camino
        p.setBrush(col("bg" if on else "text", k))
        p.drawRoundedRect(QRectF(kx - stretch / 2, sy + 3 + stretch / 10, d + stretch, d - stretch / 5), d / 2, d / 2)
        # Pestañas de la barra superior: con Avanzado entran las demás en cascada de 40 ms
        items = list(self.BASIC) + list(self.EXTRA)
        p.setFont(f)
        f.setWeight(QFont.Normal)
        p.setFont(f)
        fm = p.fontMetrics()
        widths = [fm.horizontalAdvance(s) + 28 for s in items]
        total = sum(widths)
        x = (w - total) / 2
        base_y = 130
        p.setPen(QPen(col("line", k), 1))
        p.drawLine(QPointF(40, base_y + 22), QPointF(w - 40, base_y + 22))
        for i, (s, wd) in enumerate(zip(items, widths)):
            if i == 0:
                ki = k
            else:
                ki = seg(t, self.FLIP_AT + self.FLIP_MS - 60 + 40 * (i - 1), 280)
            p.setPen(col("text" if i == 0 else "muted", ki))
            p.drawText(QRectF(x, base_y - 8 + 8 * (1 - ki), wd, 26), Qt.AlignCenter, s)
            if i == 0:
                p.setPen(QPen(col("text", ki), 2))
                p.drawLine(QPointF(x + 12, base_y + 21), QPointF(x + wd - 12, base_y + 21))
            x += wd
        ks = seg(t, self.FLIP_AT + self.FLIP_MS + 160, 300)
        self.text(p, w / 2, 186, "Simple también descarga todo: solo esconde lo que no usas a diario.",
                  size=9.5, color="muted", alpha=ks, align=Qt.AlignHCenter, w=w - 60)


STEPS = (
    (WelcomeScene, "Te damos la bienvenida",
     "DVDY Studio descarga videos y música de YouTube y de más de 1800 sitios, y convierte tus archivos. "
     "Te muestro lo básico en cuatro pasos."),
    (PasteScene, "Pega un enlace",
     "Copia el enlace del video o la canción y pégalo arriba, en Descargar. La app lo lee sola y te muestra "
     "la tapa y el título."),
    (BandScene, "Elige qué quieres bajar",
     "Video, Música (MP3 con carátula y datos), solo video o un formato a mano. Las casillas de abajo "
     "ajustan la calidad y la carpeta."),
    (DialScene, "Síguelo en el dial",
     "Presiona Descargar y mira el avance en el dial de la derecha. Cuando termina, la abres o la ves en "
     "su carpeta con un clic."),
    (ModeScene, "Simple o Avanzado",
     "Arriba a la derecha cambias de modo. Avanzado suma playlists, búsqueda, conversión y herramientas. "
     "Puedes volver a ver este tutorial desde Ajustes."),
)


# ---------------------------------------------------------------------------
class StepDots(QWidget):
    """Puntos de progreso; el actual es una píldora ámbar que se estira hacia el nuevo paso."""

    def __init__(self, n):
        super().__init__()
        self.n = n
        self._pos = 0.0
        self.setFixedSize(n * 14 + 16, 16)

    def set_index(self, i):
        motion.animate(self, "dots", self._pos, float(i), motion.UI, motion.ease_in_out(), self._set)
        self.setAccessibleDescription(f"Paso {i + 1} de {self.n}")

    def _set(self, v):
        self._pos = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        cy = self.height() / 2
        for i in range(self.n):
            p.setBrush(col("line2"))
            p.drawEllipse(QPointF(7 + i * 14, cy), 3, 3)
        # Píldora: el borde de adelante va primero y el de atrás lo alcanza (estirar y recoger)
        a = 7 + math.floor(self._pos) * 14
        b = 7 + math.ceil(self._pos) * 14
        frac = self._pos - math.floor(self._pos)
        left = lerp(a, b, max(0.0, frac * 2 - 1)) - 4
        right = lerp(a, b, min(1.0, frac * 2)) + 4
        p.setBrush(col("amber"))
        p.drawRoundedRect(QRectF(left, cy - 3.5, right - left, 7), 3.5, 3.5)
        p.end()


class _Step(QWidget):
    def __init__(self, scene_cls, title, body):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.scene = scene_cls()
        lay.addWidget(self.scene)
        lay.addSpacing(8)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        lay.addWidget(t)
        b = QLabel(body)
        b.setObjectName("Muted")
        b.setWordWrap(True)
        lay.addWidget(b)
        lay.addStretch(1)


GAP = 110  # ms entre que empieza a salir un paso y empieza a entrar el siguiente


class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cómo se usa DVDY Studio")
        self.setModal(True)
        self.setFixedSize(640, 470)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        self.counter = QLabel()
        self.counter.setObjectName("Label")
        root.addWidget(self.counter)

        # Escenario de los pasos: sin layout, los pasos se mueven a mano para la transición
        self.viewport = QWidget()
        self.viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.viewport, 1)
        self.steps = []
        for cls, title, body in STEPS:
            s = _Step(cls, title, body)
            s.setParent(self.viewport)
            s.hide()
            self.steps.append(s)

        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.skip_btn = button("Saltar tutorial", self.reject, flat=True)
        foot.addWidget(self.skip_btn)
        foot.addStretch(1)
        self.dots = StepDots(len(STEPS))
        foot.addWidget(self.dots, 0, Qt.AlignVCenter)
        foot.addStretch(1)
        self.back_btn = button("Atrás", lambda: self.go(self.index - 1))
        foot.addWidget(self.back_btn)
        self.next_btn = button("Siguiente", self._next, primary=True)
        self.next_btn.setDefault(True)
        foot.addWidget(self.next_btn)
        root.addLayout(foot)

        self.index = -1
        self._closing = False
        self.go(0, animate=False)

    # --- navegación ---
    def _next(self):
        if self.index >= len(self.steps) - 1:
            self.accept()
        else:
            self.go(self.index + 1)

    def go(self, i, animate=True):
        if not 0 <= i < len(self.steps) or i == self.index:
            return
        d = 1 if i > self.index else -1
        old = self.steps[self.index] if self.index >= 0 else None
        new = self.steps[i]
        self.index = i
        last = i == len(self.steps) - 1
        self.counter.setText(f"CÓMO SE USA  ·  {i + 1} DE {len(self.steps)}")
        self.back_btn.setVisible(i > 0)
        self.next_btn.setText("Empezar" if last else "Siguiente")
        self.skip_btn.setVisible(not last)
        self.dots.set_index(i)
        self.next_btn.setFocus()

        vw = self.viewport.rect()
        # Interrumpible: cualquier paso que no sea el que sale ni el que entra se esconde al instante
        for s in self.steps:
            if s is not old and s is not new:
                motion.stop(s, "slide")
                s.hide()
                s.setGraphicsEffect(None)
        new.setGeometry(vw)
        new.show()
        new.raise_()
        new.scene.play(delay_ms=GAP + 100 if animate and motion.enabled() and old else 0)
        if not animate or not motion.enabled():
            if old:
                old.hide()
            new.move(0, 0)
            new.setGraphicsEffect(None)
            return
        SHIFT = 28
        # Entrada: 300 ms ease-out desde el lado de la dirección
        eff_new = QGraphicsOpacityEffect(new)
        eff_new.setOpacity(0.0)
        new.setGraphicsEffect(eff_new)

        def enter(v, new=new, eff=eff_new):
            new.move(int(round(SHIFT * d * (1 - v))), 0)
            eff.setOpacity(v)

        def entered(new=new):
            new.move(0, 0)
            new.setGraphicsEffect(None)
        def start_enter(new=new):
            # Interrumpible: si mientras tanto se pidió otro paso, este ya no entra
            if self.steps[self.index] is new:
                motion.animate(new, "slide", 0.0, 1.0, motion.ENTER, motion.ease_out(), enter, entered)
        # Sin solapar textos: el paso nuevo entra cuando el anterior ya casi salió
        if old:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(GAP, start_enter)
        else:
            start_enter()

        # Salida: 150 ms ease-in hacia el lado contrario, desde donde esté
        if old:
            start_x = old.x()
            eff_old = old.graphicsEffect()
            if not isinstance(eff_old, QGraphicsOpacityEffect):
                eff_old = QGraphicsOpacityEffect(old)
                eff_old.setOpacity(1.0)
                old.setGraphicsEffect(eff_old)
            start_op = eff_old.opacity()

            def leave(v, old=old, eff=eff_old):
                old.move(int(round(lerp(start_x, -SHIFT * d, v))), 0)
                eff.setOpacity(start_op * (1 - v))

            def left(old=old):
                old.hide()
                old.setGraphicsEffect(None)
                old.move(0, 0)
            motion.animate(old, "slide", 0.0, 1.0, motion.EXIT_UI, motion.ease_in(), leave, left)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Right, Qt.Key_PageDown):
            self._next()
        elif e.key() in (Qt.Key_Left, Qt.Key_PageUp):
            self.go(self.index - 1)
        else:
            super().keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if 0 <= self.index < len(self.steps):
            self.steps[self.index].setGeometry(self.viewport.rect())

    def showEvent(self, e):
        super().showEvent(e)
        self.steps[self.index].setGeometry(self.viewport.rect())
        if not getattr(self, "_shown_once", False):
            self._shown_once = True
            motion.window_in(self, motion.ENTER)
            self.steps[self.index].scene.play(delay_ms=200 if motion.enabled() else 0)

    def done(self, r):
        """Al cerrar queda marcado como visto; la ventana sale con un fundido corto (120 ms)."""
        cfg["tutorial_done"] = True
        cfg.save()
        if self._closing or not motion.enabled():
            return super().done(r)
        self._closing = True
        motion.animate(self, "close", self.windowOpacity(), 0.0, motion.EXIT, motion.ease_in(),
                       self.setWindowOpacity, lambda: QDialog.done(self, r))


def show_tutorial(parent=None):
    TutorialDialog(parent).exec()
