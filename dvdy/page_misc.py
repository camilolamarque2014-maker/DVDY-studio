"""Páginas «Inspector», «Historial» y «Registro»."""
import json
import os
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QGridLayout, QHeaderView, QLineEdit, QMessageBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
)

from .config import history
from .utils import MEDIA_FILTER, ffprobe_json, fmt_size, fmt_time, open_path, reveal_path
from .widgets import Page, PathPicker, button, card, label, row, run_async


# ---------------------------------------------------------------------------
class InspectPage(Page):
    def __init__(self):
        super().__init__("Inspector", "Toda la información técnica de un archivo multimedia (ffprobe): "
                                      "códecs, resolución, bitrate, pistas, capítulos y metadatos.")
        self.data = None
        c, lay = card()
        self.picker = PathPicker("open", "", MEDIA_FILTER, "Arrastra aquí un archivo o pulsa Examinar…")
        self.picker.changed.connect(self._maybe_inspect)
        lay.addWidget(self.picker)
        self.add(c)

        self.summary_card, sl = card("Resumen")
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(30)
        self.grid.setVerticalSpacing(6)
        sl.addLayout(self.grid)
        self.summary_card.hide()
        self.add(self.summary_card)

        self.streams_card, stl = card("Pistas")
        self.streams = QTableWidget(0, 6)
        self.streams.setHorizontalHeaderLabels(["#", "Tipo", "Códec", "Detalles", "Idioma", "Bitrate"])
        self.streams.verticalHeader().hide()
        self.streams.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.streams.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.streams.horizontalHeader().setStretchLastSection(True)
        self.streams.setMinimumHeight(150)
        stl.addWidget(self.streams)
        self.streams_card.hide()
        self.add(self.streams_card)

        self.tree_card, tl = card("Datos completos")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Campo", "Valor"])
        self.tree.setMinimumHeight(320)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tl.addWidget(self.tree)
        tl.addWidget(row(button("Copiar JSON", self.copy_json), button("Abrir archivo", lambda: open_path(self.picker.path())),
                         button("Mostrar en carpeta", lambda: reveal_path(self.picker.path())), None))
        self.tree_card.hide()
        self.add(self.tree_card)
        self.body.addStretch(1)

    def inspect(self, path):
        self.picker.set_path(path)

    def _maybe_inspect(self, path):
        if os.path.isfile(path):
            run_async(ffprobe_json, path, on_done=self._show,
                      on_error=lambda m: QMessageBox.warning(self, "Inspector", m))

    def _show(self, data):
        self.data = data
        fmt = data.get("format", {})
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        items = [
            ("Formato", fmt.get("format_long_name") or fmt.get("format_name")),
            ("Duración", fmt_time(fmt.get("duration"))),
            ("Tamaño", fmt_size(int(fmt["size"])) if fmt.get("size") else "—"),
            ("Bitrate total", f"{int(fmt['bit_rate']) // 1000} kbps" if fmt.get("bit_rate") else "—"),
            ("Pistas", str(fmt.get("nb_streams", ""))),
            ("Capítulos", str(len(data.get("chapters") or []))),
        ]
        tags = fmt.get("tags") or {}
        for k in ("title", "artist", "album", "date", "genre", "encoder"):
            for tk, tv in tags.items():
                if tk.lower() == k:
                    items.append((k.capitalize(), str(tv)))
        for i, (k, v) in enumerate(items):
            self.grid.addWidget(label(k, "Muted"), i // 2, (i % 2) * 2)
            vl = label(v or "—")
            vl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.grid.addWidget(vl, i // 2, (i % 2) * 2 + 1)
        self.streams.setRowCount(0)
        names = {"video": "Video", "audio": "Audio", "subtitle": "Subtítulos", "data": "Datos", "attachment": "Adjunto"}
        for s in data.get("streams", []):
            r = self.streams.rowCount()
            self.streams.insertRow(r)
            t = s.get("codec_type", "")
            if t == "video":
                fr = s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1"
                try:
                    n, d = fr.split("/")
                    fps = f"{float(n) / float(d):.2f} fps" if float(d) else ""
                except ValueError:
                    fps = ""
                det = f"{s.get('width')}×{s.get('height')}  {fps}  {s.get('pix_fmt', '')}"
                if (s.get("disposition") or {}).get("attached_pic"):
                    det += "  (carátula)"
            elif t == "audio":
                det = f"{s.get('sample_rate', '?')} Hz  {s.get('channels', '?')} canales  {s.get('channel_layout', '')}"
            else:
                det = (s.get("tags") or {}).get("title", "")
            br = s.get("bit_rate")
            vals = [str(s.get("index")), names.get(t, t), s.get("codec_long_name") or s.get("codec_name", ""), det,
                    (s.get("tags") or {}).get("language", ""), f"{int(br) // 1000} kbps" if br else ""]
            for col, v in enumerate(vals):
                self.streams.setItem(r, col, QTableWidgetItem(v))
        self.tree.clear()
        self._fill(self.tree.invisibleRootItem(), data)
        self.tree.expandToDepth(0)
        for c in (self.summary_card, self.streams_card, self.tree_card):
            c.show()

    def _fill(self, parent, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                it = QTreeWidgetItem(parent, [str(k), "" if isinstance(v, (dict, list)) else str(v)])
                self._fill(it, v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                name = f"[{i}]"
                if isinstance(v, dict) and "codec_type" in v:
                    name += f" {v['codec_type']}"
                it = QTreeWidgetItem(parent, [name, "" if isinstance(v, (dict, list)) else str(v)])
                self._fill(it, v)

    def copy_json(self):
        if self.data:
            QGuiApplication.clipboard().setText(json.dumps(self.data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
class HistoryPage(Page):
    def __init__(self, on_redownload):
        super().__init__("Historial", "Todo lo que se ha descargado y convertido. Doble clic para abrir.")
        self.on_redownload = on_redownload
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar en el historial…")
        self.search.textChanged.connect(self.refresh)
        self.add(row(self.search, button("Abrir", self.open_sel), button("Mostrar en carpeta", self.reveal_sel),
                     button("Descargar de nuevo", self.redownload), button("Quitar", self.remove_sel),
                     button("Borrar todo", self.clear_all, flat=True)))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Tipo", "Título", "Ubicación"])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Interactive)
        hh.resizeSection(3, 260)
        self.table.setMinimumHeight(480)
        self.table.doubleClicked.connect(self.open_sel)
        self.add(self.table, 1)
        self.refresh()

    def refresh(self, *_):
        q = self.search.text().lower().strip()
        self.table.setRowCount(0)
        for i, h in enumerate(history.items):
            if q and q not in (h.get("title", "") + h.get("path", "") + h.get("kind", "")).lower():
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            exists = os.path.exists(h.get("path") or "")
            vals = [h.get("date", ""), h.get("kind", ""), h.get("title", ""), h.get("path", "")]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setToolTip(v)
                if not exists and c == 3:
                    it.setForeground(QColor("#8a90a3"))
                self.table.setItem(r, c, it)
            self.table.item(r, 0).setData(Qt.UserRole, i)

    def _sel(self):
        r = self.table.currentRow()
        if r < 0:
            return None, None
        i = self.table.item(r, 0).data(Qt.UserRole)
        return i, history.items[i]

    def open_sel(self, *_):
        _, h = self._sel()
        if h:
            if os.path.exists(h["path"]):
                open_path(h["path"])
            else:
                QMessageBox.information(self, "No encontrado", "El archivo ya no existe en esa ubicación.")

    def reveal_sel(self):
        _, h = self._sel()
        if h:
            reveal_path(h["path"])

    def redownload(self):
        _, h = self._sel()
        if h and h.get("url"):
            self.on_redownload(h["url"])

    def remove_sel(self):
        i, h = self._sel()
        if h is not None:
            history.remove(i)
            self.refresh()

    def clear_all(self):
        if QMessageBox.question(self, "Borrar historial", "¿Borrar todo el historial? (los archivos no se eliminan)") \
                == QMessageBox.Yes:
            history.clear()
            self.refresh()


# ---------------------------------------------------------------------------
class LogPage(Page):
    COLORS = {"error": "#ff5d6c", "warning": "#f5b74e"}

    def __init__(self):
        super().__init__("Registro", "Salida detallada de yt-dlp y FFmpeg. Útil para diagnosticar errores.", scroll=False)
        self.only_errors = False
        self.add(row(button("Limpiar", lambda: self.console.clear()), button("Guardar…", self.save),
                     button("Copiar todo", lambda: QGuiApplication.clipboard().setText(self.console.toPlainText())), None))
        self.console = QPlainTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(8000)
        self.add(self.console, 1)

    def append(self, level, msg):
        stamp = time.strftime("%H:%M:%S")
        cur = self.console.textCursor()
        cur.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        if level in self.COLORS:
            fmt.setForeground(QColor(self.COLORS[level]))
        else:
            fmt.setForeground(self.console.palette().text().color())
        cur.insertText(f"{stamp}  {msg}\n", fmt)
        sb = self.console.verticalScrollBar()
        if sb.value() >= sb.maximum() - 40:
            sb.setValue(sb.maximum())

    def save(self):
        p, _ = QFileDialog.getSaveFileName(self, "Guardar registro", "dvdy_registro.txt", "Texto (*.txt)")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.console.toPlainText())
