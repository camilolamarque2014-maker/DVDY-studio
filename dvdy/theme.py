"""Identidad visual de DVDY Studio: «Radio de Madrugada».

Grafito oscuro, texto marfil y una sola luz ámbar reservada para lo que está activo
(la descarga en curso, la aguja del dial, la banda elegida). El color vive solo en las
tapas y en esa luz. Existe una versión clara de la misma identidad, que se usa cuando
el sistema (Windows o Ubuntu) está en modo claro (o si el usuario la elige en Ajustes).
"""
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPainter, QPainterPath, QPixmap

FONT_TEXT = "Archivo"
FONT_LABEL = "Archivo Narrow"

# Tres tamaños de letra en toda la app (pt): pequeño, cuerpo y título.
SIZE_SMALL = 9
SIZE_BODY = 10.5
SIZE_TITLE = 17

PALETTES = {
    "dark": {
        "bg": "#131315", "panel": "#1d1d21", "raised": "#24242a", "line": "#2a2a30", "line2": "#3a3a42",
        "text": "#f4ede0", "muted": "#8c8a86", "faint": "#5f5d5a",
        "amber": "#e9a23b", "amber_text": "#e9a23b", "err": "#c8553d", "err_text": "#e07a63",
        "on_text": "#131315", "console": "#0f0f11",
    },
    "light": {
        "bg": "#ecebe7", "panel": "#f8f7f4", "raised": "#f1f0ec", "line": "#dddad3", "line2": "#c4c0b7",
        "text": "#18181a", "muted": "#64615b", "faint": "#9a968e",
        "amber": "#c9821c", "amber_text": "#8f5508", "err": "#a8402c", "err_text": "#a8402c",
        "on_text": "#f8f7f4", "console": "#f4f3ef",
    },
}

# Paleta en uso (la actualiza build_qss); los widgets pintados a mano la leen de aquí.
current = dict(PALETTES["dark"])

ICON = {
    "download": "", "music": "", "search": "", "queue": "",
    "convert": "", "tools": "", "info": "", "history": "",
    "log": "", "settings": "", "pause": "", "play": "",
    "cancel": "", "folder": "", "delete": "", "video": "",
    "refresh": "", "paste": "", "link": "", "add": "",
    "check": "", "file": "", "clear": "", "up": "", "down": "",
    "open": "", "copy": "", "save": "", "image": "",
    "more": "", "chevdown": "", "chevup": "", "warning": "",
    "playlist": "", "sync": "",
}

# Linux no trae las fuentes de íconos de Windows (Segoe): se usan símbolos Unicode que están en
# las fuentes comunes (DejaVu, Noto). Solo hacen falta los íconos que la interfaz muestra.
UNICODE_ICON = {
    "cancel": "✕", "more": "⋯", "up": "↑", "down": "↓", "download": "↓", "convert": "⇄",
    "sync": "⟳", "file": "▢", "music": "♪", "video": "▶", "play": "▶", "pause": "⏸",
    "check": "✓", "add": "+", "clear": "✕", "delete": "✕", "chevdown": "⌄", "chevup": "⌃",
    "warning": "⚠", "refresh": "⟳", "search": "⌕", "folder": "▤", "settings": "⚙",
}

_icon_family = None
_fonts_loaded = False


def load_fonts():
    """Registra las tipografías incluidas en la app (licencia OFL, ver assets/fonts/OFL.txt)."""
    global _fonts_loaded
    if _fonts_loaded:
        return
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    for name in ("Archivo-Variable.ttf", "ArchivoNarrow-Variable.ttf"):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)
    _fonts_loaded = True


def icon_family():
    global _icon_family
    if _icon_family is None:
        fams = set(QFontDatabase.families())
        segoe = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in fams), None)
        if segoe:
            _icon_family = segoe
        elif "Segoe UI Symbol" in fams:
            _icon_family = "Segoe UI Symbol"
        else:
            # Sin fuentes de Windows: símbolos Unicode con una fuente que los tenga
            ICON.update(UNICODE_ICON)
            _icon_family = next((f for f in ("DejaVu Sans", "Noto Sans Symbols 2", "Noto Sans Symbols",
                                             "Noto Sans") if f in fams), FONT_TEXT)
    return _icon_family


def icon_font(size=12):
    f = QFont(icon_family())
    f.setPixelSize(size)
    return f


def label_font(size=SIZE_SMALL, weight=QFont.DemiBold, spacing=116):
    f = QFont(FONT_LABEL)
    f.setPointSizeF(size)
    f.setWeight(weight if isinstance(weight, QFont.Weight) else QFont.Weight(int(weight)))
    f.setLetterSpacing(QFont.PercentageSpacing, spacing)
    f.setCapitalization(QFont.AllUppercase)
    return f


def resolve_theme(choice):
    """'auto' sigue al sistema (Windows o el modo claro/oscuro de Ubuntu); 'dark' y 'light' fuerzan uno."""
    if choice in ("dark", "light"):
        return choice
    from .system import IS_WINDOWS, linux_color_scheme
    if not IS_WINDOWS:
        scheme = linux_color_scheme()
        if scheme:
            return scheme
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass
    return "dark"


def app_icon():
    """Ícono: placa de grafito con el triángulo de reproducción marfil y la aguja ámbar del dial."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        s = float(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1d1d21"))
        p.drawRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)
        path = QPainterPath()
        path.moveTo(QPointF(s * 0.36, s * 0.24))
        path.lineTo(QPointF(s * 0.36, s * 0.60))
        path.lineTo(QPointF(s * 0.68, s * 0.42))
        path.closeSubpath()
        p.setBrush(QColor("#f4ede0"))
        p.drawPath(path)
        p.setBrush(QColor("#3a3a42"))
        p.drawRoundedRect(QRectF(s * 0.20, s * 0.74, s * 0.60, s * 0.06), s * 0.03, s * 0.03)
        p.setBrush(QColor("#e9a23b"))
        p.drawRoundedRect(QRectF(s * 0.52, s * 0.68, max(1.5, s * 0.05), s * 0.18), s * 0.02, s * 0.02)
        p.end()
        icon.addPixmap(pm)
    return icon


def apply_palette(app, theme="dark"):
    """Ajusta la paleta de Qt a la identidad (sin el azul de selección por defecto del sistema)."""
    from PySide6.QtGui import QPalette
    c = PALETTES.get(theme, PALETTES["dark"])
    pal = app.palette()
    roles = {
        QPalette.Window: c["bg"], QPalette.Base: c["bg"], QPalette.AlternateBase: c["panel"],
        QPalette.Text: c["text"], QPalette.WindowText: c["text"], QPalette.ButtonText: c["text"],
        QPalette.Button: c["panel"], QPalette.ToolTipBase: c["panel"], QPalette.ToolTipText: c["text"],
        QPalette.PlaceholderText: c["muted"], QPalette.Highlight: c["line2"], QPalette.HighlightedText: c["text"],
        QPalette.Link: c["text"], QPalette.BrightText: c["text"],
    }
    for role, col in roles.items():
        pal.setColor(role, QColor(col))
    app.setPalette(pal)


def build_qss(theme="dark"):
    c = dict(PALETTES.get(theme, PALETTES["dark"]))
    current.clear()
    current.update(c)
    current["name"] = theme
    a = QColor(c["amber"])
    c["amber_soft"] = f"rgba({a.red()},{a.green()},{a.blue()},34)"
    t = QColor(c["text"])
    c["text_soft"] = f"rgba({t.red()},{t.green()},{t.blue()},18)"
    c["text_soft2"] = f"rgba({t.red()},{t.green()},{t.blue()},30)"
    c["icon_font"] = icon_family()
    c["ft"], c["fl"] = FONT_TEXT, FONT_LABEL
    c["s_small"], c["s_body"], c["s_title"] = SIZE_SMALL, SIZE_BODY, SIZE_TITLE
    ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui").replace("\\", "/")
    c["check"] = f"{ui}/check_{theme}.svg"
    c["chev"] = f"{ui}/chevron_{theme}.svg"
    c["chev_hover"] = f"{ui}/chevron_hover_{theme}.svg"
    return QSS_TEMPLATE % c


QSS_TEMPLATE = """
* { font-family: "%(ft)s", "Segoe UI", sans-serif; font-size: %(s_body)spt; color: %(text)s; }
QMainWindow, #Root, QDialog { background: %(bg)s; }
QWidget#Page { background: %(bg)s; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QToolTip { background: %(panel)s; color: %(text)s; border: 1px solid %(line2)s; padding: 6px 8px; border-radius: 6px; }
QLineEdit, QPlainTextEdit, QTextEdit { selection-background-color: %(text)s; selection-color: %(on_text)s; }

/* ---------- Barra superior ---------- */
#TopBar { background: %(bg)s; border-bottom: 1px solid %(line)s; }
#Wordmark { font-family: "%(fl)s"; font-weight: 700; font-size: %(s_title)spt; letter-spacing: 1px; }
#TopNav { background: transparent; border: none; border-radius: 6px; padding: 7px 12px; color: %(muted)s; font-weight: 500; }
#TopNav:hover { color: %(text)s; background: %(text_soft)s; }
#TopNav:checked { color: %(text)s; font-weight: 700; border-bottom: 2px solid %(text)s; border-radius: 0; }
#TopNav:focus { color: %(text)s; border: 1px dashed %(muted)s; border-radius: 6px; }
#TopNav:checked:focus { border: 1px dashed %(muted)s; border-bottom: 2px solid %(text)s; border-radius: 0; }
#NavDot { background: %(amber)s; border-radius: 3px; }
#ModeBox { background: transparent; }
#ModeOn { color: %(text)s; font-family: "%(fl)s"; font-weight: 700; font-size: %(s_small)spt; letter-spacing: 1px; background: transparent; }
#ModeOff { color: %(muted)s; font-family: "%(fl)s"; font-weight: 600; font-size: %(s_small)spt; letter-spacing: 1px; background: transparent; }

/* ---------- Texto ---------- */
#PageTitle { font-size: %(s_title)spt; font-weight: 700; }
#PageSubtitle, #Muted { color: %(muted)s; }
#Hint { color: %(muted)s; font-size: %(s_small)spt; }
#Label { font-family: "%(fl)s"; font-weight: 600; font-size: %(s_small)spt; letter-spacing: 1px; color: %(muted)s; }
#SectionTitle { font-weight: 700; }
#Big { font-weight: 700; }
#AmberText { color: %(amber_text)s; } #ErrText { color: %(err_text)s; } #OkText { color: %(text)s; } #WarnText { color: %(amber_text)s; }

/* ---------- Paneles ---------- */
#Card, #Panel { background: %(panel)s; border: 1px solid %(line)s; border-radius: 12px; }
#Tile { background: transparent; border: 1px solid %(line)s; border-radius: 9px; }
#Tile:hover { border-color: %(line2)s; }
#Tile[focused="true"] { border: 1px solid %(text)s; }
#Banner { background: %(panel)s; border: 1px solid %(line2)s; border-radius: 10px; }
#Thumb { background: %(raised)s; border-radius: 6px; }
#TaskRow { background: transparent; border: none; }
#Sep { background: %(line)s; border: none; }
#PreviewRow { background: transparent; border: none; border-top: 1px solid %(line)s; }
#Empty { color: %(muted)s; }

/* ---------- Entradas ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
    background: %(bg)s; border: 1px solid %(line2)s; border-radius: 8px; padding: 6px 10px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid %(text)s; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: %(faint)s; border-color: %(line)s; }
#UrlInput { padding: 14px 16px; border-radius: 10px; }
#Tile QComboBox, #Tile QPushButton#TileButton { background: transparent; border: none; padding: 2px 0; font-weight: 600; text-align: left; }
#Tile QComboBox:focus, #Tile QPushButton#TileButton:focus { border: none; color: %(text)s; text-decoration: underline; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down { border: none; width: 24px; subcontrol-position: center right; }
QComboBox::down-arrow { image: url(%(chev)s); width: 11px; height: 11px; }
QComboBox::down-arrow:hover, QComboBox::down-arrow:focus, QComboBox::down-arrow:on { image: url(%(chev_hover)s); }
#Tile QComboBox { padding-right: 22px; }
QComboBox QAbstractItemView { background: %(panel)s; border: 1px solid %(line2)s; border-radius: 8px;
    selection-background-color: %(text_soft2)s; selection-color: %(text)s; outline: none; padding: 4px; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; border: none; }

/* ---------- Botones ---------- */
QPushButton, QToolButton { background: transparent; border: 1px solid %(line2)s; border-radius: 8px; padding: 7px 14px; font-weight: 600; }
QPushButton:hover, QToolButton:hover { background: %(text_soft)s; }
QPushButton:pressed, QToolButton:pressed { background: %(text_soft2)s; }
QPushButton:focus, QToolButton:focus { border: 1px solid %(text)s; }
QPushButton:disabled, QToolButton:disabled { color: %(faint)s; border-color: %(line)s; }
QPushButton#Primary { background: %(text)s; border: 1px solid %(text)s; color: %(on_text)s; font-weight: 700; padding: 11px 30px; border-radius: 10px; }
QPushButton#Primary:hover { background: %(muted)s; border-color: %(muted)s; }
QPushButton#Primary:focus { border: 2px solid %(on_text)s; padding: 10px 29px; }
QPushButton#Primary:disabled { background: %(line)s; border-color: %(line)s; color: %(faint)s; }
QPushButton#Flat, QToolButton#Flat { border: none; padding: 5px 8px; color: %(muted)s; }
QPushButton#Flat:hover, QToolButton#Flat:hover { color: %(text)s; background: %(text_soft)s; }
QPushButton#Small { padding: 4px 10px; border-radius: 6px; font-size: %(s_small)spt; }
QPushButton#SmallPrimary { padding: 4px 12px; border-radius: 6px; font-size: %(s_small)spt; background: %(text)s; color: %(on_text)s; border-color: %(text)s; }
QPushButton#SmallPrimary:hover { background: %(muted)s; border-color: %(muted)s; }
QToolButton#IconBtn { font-family: "%(icon_font)s"; font-size: 11pt; border: none; border-radius: 6px; padding: 5px; min-width: 26px; min-height: 26px; color: %(muted)s; }
QToolButton#IconBtn:hover { background: %(text_soft)s; color: %(text)s; }
QToolButton#IconBtn:focus { border: 1px solid %(text)s; }
QToolButton::menu-indicator { image: none; width: 0; }
#Segment QPushButton { border-radius: 0; border-right: none; padding: 8px 14px; color: %(muted)s; }
#Segment QPushButton:first-child { border-top-left-radius: 8px; border-bottom-left-radius: 8px; }
#Segment QPushButton[last="true"] { border-top-right-radius: 8px; border-bottom-right-radius: 8px; border-right: 1px solid %(line2)s; }
#Segment QPushButton:checked { background: %(text)s; border-color: %(text)s; color: %(on_text)s; font-weight: 700; }

/* ---------- Casillas ---------- */
QCheckBox, QRadioButton { spacing: 9px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator { width: 15px; height: 15px; border: 1px solid %(muted)s; background: transparent; }
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked { background: %(text)s; border-color: %(text)s; image: url(%(check)s); }
QCheckBox::indicator:checked:disabled { background: %(faint)s; border-color: %(faint)s; }
QCheckBox::indicator:disabled { border-color: %(line2)s; }
QCheckBox:focus, QRadioButton:focus { color: %(text)s; text-decoration: underline; }
QRadioButton::indicator:checked { background: %(text)s; border-color: %(text)s; }
QCheckBox:disabled, QRadioButton:disabled { color: %(faint)s; }

/* ---------- Pestañas ---------- */
QTabWidget::pane { border: none; border-top: 1px solid %(line)s; background: transparent; top: -1px; padding-top: 4px; }
QTabBar::tab { background: transparent; color: %(muted)s; padding: 8px 14px; border: none; margin-right: 2px;
    border-bottom: 2px solid transparent; font-family: "%(fl)s"; font-weight: 600; font-size: %(s_small)spt; letter-spacing: 1px; text-transform: uppercase; }
QTabBar::tab:selected { color: %(text)s; border-bottom: 2px solid %(text)s; }
QTabBar::tab:hover { color: %(text)s; }
QTabBar::tab:focus { color: %(text)s; }

/* ---------- Tablas y listas ---------- */
QTableWidget, QTableView, QTreeWidget, QListWidget { background: transparent; border: 1px solid %(line)s; border-radius: 10px;
    gridline-color: transparent; alternate-background-color: %(text_soft)s; outline: none;
    selection-background-color: %(text_soft2)s; selection-color: %(text)s; }
QTableWidget::item, QTreeWidget::item, QListWidget::item { padding: 4px 6px; border: none; }
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: %(text_soft2)s; color: %(text)s; }
QTableWidget:focus, QTreeWidget:focus, QListWidget:focus { border-color: %(line2)s; }
QHeaderView { background: transparent; }
QHeaderView::section { background: transparent; color: %(muted)s; border: none; border-bottom: 1px solid %(line)s;
    padding: 7px 8px; font-family: "%(fl)s"; font-weight: 600; font-size: %(s_small)spt; letter-spacing: 1px; text-transform: uppercase; }
QTableCornerButton::section { background: transparent; border: none; }
#ToolList { background: transparent; border: none; }
#ToolHeader { color: %(muted)s; }
#DropZone { background: %(raised)s; border: none; border-radius: 10px; }
#DropZone:focus { border-color: %(text)s; }
#Grid { background: transparent; border: none; }
#Grid::item { border: none; border-radius: 8px; padding: 6px; color: %(muted)s; background: transparent; }
#Grid::item:hover { color: %(text)s; }
#Grid::item:selected { background: %(text)s; color: %(on_text)s; }
#Grid::item:selected:hover { background: %(muted)s; color: %(on_text)s; }
#Stage { background: transparent; border: none; }
#Notes { background: %(raised)s; border: none; border-radius: 10px; padding: 10px 14px; }
#Cover { background: %(raised)s; border-radius: 8px; color: %(muted)s; }
#ToolList::item { padding: 8px 10px; border-radius: 7px; margin: 1px 0; color: %(muted)s; }
#ToolList::item:hover { background: %(text_soft)s; color: %(text)s; }
#ToolList::item:selected { background: transparent; color: %(text)s; font-weight: 700; }
#ToolList::item:focus { border: 1px dashed %(muted)s; }

/* ---------- Progreso ---------- */
QProgressBar { background: %(line)s; border: none; border-radius: 2px; text-align: center; color: transparent; }
QProgressBar::chunk { background: %(amber)s; border-radius: 2px; }
QProgressBar#Done::chunk { background: %(muted)s; }
QProgressBar#Failed::chunk { background: %(err)s; }
QProgressBar#Paused::chunk { background: %(muted)s; }
QSlider::groove:horizontal { height: 3px; background: %(line2)s; border-radius: 1px; }
QSlider::sub-page:horizontal { background: %(text)s; border-radius: 1px; }
QSlider::handle:horizontal { background: %(text)s; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }
QSlider:focus { border: none; }

/* ---------- Consola ---------- */
#Console { background: %(console)s; font-family: "Cascadia Mono", "Consolas", monospace; font-size: %(s_small)spt; border-radius: 10px; }

/* ---------- Barras de desplazamiento ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(line2)s; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(muted)s; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(line2)s; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QGroupBox { border: 1px solid %(line)s; border-radius: 10px; margin-top: 14px; padding: 12px 10px 10px 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; color: %(muted)s; }
QMenu { background: %(panel)s; border: 1px solid %(line2)s; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 7px 22px 7px 14px; border-radius: 6px; }
QMenu::item:selected { background: %(text_soft2)s; }
QMenu::separator { height: 1px; background: %(line)s; margin: 4px 8px; }
QMessageBox { background: %(panel)s; }
QSplitter::handle { background: transparent; }
"""
