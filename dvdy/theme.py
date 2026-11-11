"""Tema visual (QSS) e íconos de DVDY Studio."""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap

PALETTES = {
    "dark": {
        "bg": "#0e1016", "side": "#12141c", "surface": "#171a23", "surface2": "#1e2230",
        "surface3": "#262b3b", "border": "#2a2f3f", "text": "#e7e9f0", "muted": "#8a90a3",
        "input": "#11131a", "console_bg": "#0b0d12", "ok": "#3ecf8e", "warn": "#f5b74e", "err": "#ff5d6c",
    },
    "light": {
        "bg": "#f3f4f8", "side": "#ffffff", "surface": "#ffffff", "surface2": "#f0f1f6",
        "surface3": "#e4e6ef", "border": "#dcdfe8", "text": "#1b1d26", "muted": "#6b7184",
        "input": "#ffffff", "console_bg": "#fafbfd", "ok": "#1f9d68", "warn": "#c98a12", "err": "#d93848",
    },
}

ICON = {
    "download": "", "music": "", "search": "", "queue": "",
    "convert": "", "tools": "", "info": "", "history": "",
    "log": "", "settings": "", "pause": "", "play": "",
    "cancel": "", "folder": "", "delete": "", "video": "",
    "refresh": "", "paste": "", "link": "", "add": "",
    "check": "", "file": "", "clear": "", "up": "", "down": "",
    "open": "", "copy": "", "save": "", "image": "",
}

_icon_family = None


def icon_family():
    global _icon_family
    if _icon_family is None:
        fams = set(QFontDatabase.families())
        _icon_family = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in fams), "Segoe UI Symbol")
    return _icon_family


def icon_font(size=12):
    f = QFont(icon_family())
    f.setPixelSize(size)
    return f


def glyph_icon(name, color="#e7e9f0", size=32):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(color))
    p.setFont(icon_font(int(size * 0.62)))
    p.drawText(pm.rect(), Qt.AlignCenter, ICON.get(name, name))
    p.end()
    return QIcon(pm)


def app_icon(accent="#7c5cff"):
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, size, size)
        c = QColor(accent)
        grad.setColorAt(0, c.lighter(130))
        grad.setColorAt(1, c.darker(140))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        r = size * 0.22
        p.drawRoundedRect(QRectF(0, 0, size, size), r, r)
        path = QPainterPath()
        s = size
        path.moveTo(QPointF(s * 0.38, s * 0.26))
        path.lineTo(QPointF(s * 0.38, s * 0.62))
        path.lineTo(QPointF(s * 0.70, s * 0.44))
        path.closeSubpath()
        p.setBrush(QColor("white"))
        p.drawPath(path)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawRoundedRect(QRectF(s * 0.26, s * 0.72, s * 0.48, s * 0.07), s * 0.03, s * 0.03)
        p.end()
        icon.addPixmap(pm)
    return icon


def build_qss(theme="dark", accent="#7c5cff"):
    c = dict(PALETTES.get(theme, PALETTES["dark"]))
    a = QColor(accent)
    c["accent"] = a.name()
    c["accent_hover"] = a.lighter(115).name()
    c["accent_press"] = a.darker(115).name()
    c["accent_soft"] = f"rgba({a.red()},{a.green()},{a.blue()},40)"
    c["accent_soft2"] = f"rgba({a.red()},{a.green()},{a.blue()},70)"
    c["icon_font"] = icon_family()
    return QSS_TEMPLATE % c


QSS_TEMPLATE = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 10pt; color: %(text)s; }
QMainWindow, #Root, QDialog { background: %(bg)s; }
QWidget#Page { background: %(bg)s; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QToolTip { background: %(surface2)s; color: %(text)s; border: 1px solid %(border)s; padding: 6px; border-radius: 6px; }

/* ---------- Barra lateral ---------- */
#Sidebar { background: %(side)s; border-right: 1px solid %(border)s; }
#AppTitle { font-size: 15pt; font-weight: 700; }
#AppSubtitle { color: %(muted)s; font-size: 8.5pt; }
#NavButton { text-align: left; padding: 9px 12px; border: none; border-radius: 8px; background: transparent;
             color: %(muted)s; font-size: 10pt; }
#NavButton:hover { background: %(surface2)s; color: %(text)s; }
#NavButton:checked { background: %(accent_soft)s; color: %(text)s; font-weight: 600; }
#NavIcon { font-family: "%(icon_font)s"; font-size: 13pt; color: %(text)s; background: transparent; }
#NavText { color: %(text)s; background: transparent; }
#NavText[active="true"] { font-weight: 700; }
#ModeOn { color: %(text)s; font-weight: 700; font-size: 9pt; background: transparent; }
#ModeOff { color: %(muted)s; font-size: 9pt; background: transparent; }
#ModeBox { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 10px; }
#NavBadge { background: %(accent)s; color: white; border-radius: 9px; padding: 1px 7px; font-size: 8pt; font-weight: 700; }
#SideFooter { color: %(muted)s; font-size: 8.5pt; }

/* ---------- Encabezados ---------- */
#PageTitle { font-size: 19pt; font-weight: 700; }
#PageSubtitle { color: %(muted)s; font-size: 10pt; }
#SectionTitle { font-size: 11pt; font-weight: 600; }
#Muted { color: %(muted)s; }
#Hint { color: %(muted)s; font-size: 9pt; }
#Big { font-size: 13pt; font-weight: 600; }
#OkText { color: %(ok)s; } #WarnText { color: %(warn)s; } #ErrText { color: %(err)s; }

/* ---------- Tarjetas ---------- */
#Card { background: %(surface)s; border: 1px solid %(border)s; border-radius: 12px; }
#Banner { background: %(accent_soft)s; border: 1px solid %(accent)s; border-radius: 10px; }
#Thumb { background: %(surface2)s; border-radius: 8px; }

/* ---------- Entradas ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
    background: %(input)s; border: 1px solid %(border)s; border-radius: 8px; padding: 6px 9px;
    selection-background-color: %(accent)s; selection-color: white; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid %(accent)s; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: %(muted)s; background: %(surface2)s; }
#UrlInput { font-size: 11pt; padding: 10px 12px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; width: 0; }
QComboBox QAbstractItemView { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 8px;
    selection-background-color: %(accent_soft2)s; selection-color: %(text)s; outline: none; padding: 4px; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; border: none; }

/* ---------- Botones ---------- */
QPushButton, QToolButton { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 8px;
    padding: 7px 14px; }
QPushButton:hover, QToolButton:hover { background: %(surface3)s; }
QPushButton:pressed, QToolButton:pressed { background: %(border)s; }
QPushButton:disabled, QToolButton:disabled { color: %(muted)s; background: %(surface)s; }
QPushButton#Primary { background: %(accent)s; border: 1px solid %(accent)s; color: white; font-weight: 600; padding: 9px 18px; }
QPushButton#Primary:hover { background: %(accent_hover)s; }
QPushButton#Primary:pressed { background: %(accent_press)s; }
QPushButton#Primary:disabled { background: %(surface3)s; border-color: %(border)s; color: %(muted)s; }
QPushButton#Flat, QToolButton#Flat { background: transparent; border: none; padding: 5px 8px; }
QPushButton#Flat:hover, QToolButton#Flat:hover { background: %(surface2)s; }
QToolButton#IconBtn { font-family: "%(icon_font)s"; font-size: 11pt; background: transparent; border: none;
    border-radius: 6px; padding: 5px; min-width: 26px; min-height: 26px; }
QToolButton#IconBtn:hover { background: %(surface3)s; }
QToolButton::menu-indicator { image: none; width: 0; }
#Segment QPushButton { border-radius: 0; border-right: none; padding: 8px 14px; }
#Segment QPushButton:first-child { border-top-left-radius: 8px; border-bottom-left-radius: 8px; }
#Segment QPushButton[last="true"] { border-top-right-radius: 8px; border-bottom-right-radius: 8px; border-right: 1px solid %(border)s; }
#Segment QPushButton:checked { background: %(accent)s; border-color: %(accent)s; color: white; font-weight: 600; }

/* ---------- Casillas / radios ---------- */
QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid %(muted)s; background: %(input)s; }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 9px; }
QCheckBox::indicator:checked { background: %(accent)s; border-color: %(accent)s; image: none; }
QRadioButton::indicator:checked { background: %(accent)s; border: 1px solid %(accent)s; }
QCheckBox:disabled, QRadioButton:disabled { color: %(muted)s; }

/* ---------- Pestañas ---------- */
QTabWidget::pane { border: 1px solid %(border)s; border-radius: 10px; background: %(surface)s; top: -1px; }
QTabBar::tab { background: transparent; color: %(muted)s; padding: 8px 14px; border: none; margin-right: 2px;
    border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(text)s; border-bottom: 2px solid %(accent)s; font-weight: 600; }
QTabBar::tab:hover { color: %(text)s; }

/* ---------- Tablas y listas ---------- */
QTableWidget, QTableView, QTreeWidget, QListWidget { background: %(input)s; border: 1px solid %(border)s; border-radius: 10px;
    gridline-color: transparent; alternate-background-color: %(surface)s; outline: none;
    selection-background-color: %(accent_soft2)s; selection-color: %(text)s; }
QTableWidget::item, QTreeWidget::item, QListWidget::item { padding: 4px 6px; border: none; }
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected { background: %(accent_soft2)s; }
QHeaderView { background: transparent; }
QHeaderView::section { background: %(surface2)s; color: %(muted)s; border: none; border-bottom: 1px solid %(border)s;
    padding: 7px 8px; font-weight: 600; }
QTableCornerButton::section { background: %(surface2)s; border: none; }
#NavList, #ToolList { background: transparent; border: none; }
#ToolList::item { padding: 9px 10px; border-radius: 8px; margin: 1px 0; color: %(muted)s; }
#ToolList::item:hover { background: %(surface2)s; color: %(text)s; }
#ToolList::item:selected { background: %(accent_soft)s; color: %(text)s; }

/* ---------- Progreso ---------- */
QProgressBar { background: %(surface3)s; border: none; border-radius: 4px; height: 8px; text-align: center; color: transparent; }
QProgressBar::chunk { background: %(accent)s; border-radius: 4px; }
QProgressBar#Done::chunk { background: %(ok)s; }
QProgressBar#Failed::chunk { background: %(err)s; }
QProgressBar#Paused::chunk { background: %(warn)s; }
QSlider::groove:horizontal { height: 4px; background: %(surface3)s; border-radius: 2px; }
QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 2px; }
QSlider::handle:horizontal { background: white; border: 2px solid %(accent)s; width: 12px; height: 12px; margin: -6px 0; border-radius: 8px; }

/* ---------- Consola ---------- */
#Console { background: %(console_bg)s; font-family: "Cascadia Mono", "Consolas", monospace; font-size: 9pt; border-radius: 10px; }

/* ---------- Barras de desplazamiento ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(surface3)s; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(surface3)s; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QGroupBox { border: 1px solid %(border)s; border-radius: 10px; margin-top: 14px; padding: 12px 10px 10px 10px; background: transparent; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: %(muted)s; font-weight: 600; }
QMenu { background: %(surface2)s; border: 1px solid %(border)s; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 7px 22px 7px 14px; border-radius: 6px; }
QMenu::item:selected { background: %(accent_soft2)s; }
QMenu::separator { height: 1px; background: %(border)s; margin: 4px 8px; }
QMessageBox { background: %(surface)s; }
QSplitter::handle { background: transparent; }
"""
