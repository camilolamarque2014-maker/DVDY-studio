"""Diferencias entre Windows y Linux, reunidas en un solo lugar.

En Windows todo se comporta igual que antes del porte a Linux. En Linux se siguen las
convenciones de freedesktop (XDG): configuración en ~/.config, datos en ~/.local/share y
las carpetas Descargas/Música que el usuario tenga configuradas (con su nombre en español).

Este módulo no importa Qt: lo usan config.py y deps.py antes de crear la ventana.
"""
import os
import shutil
import subprocess
import sys

IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")
FROZEN = bool(getattr(sys, "frozen", False))

APP_ID = "dvdy-studio"             # nombre del paquete .deb, del ejecutable y del .desktop en Linux
LINUX_INSTALL_DIR = "/opt/dvdy-studio"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""


# ---------------------------------------------------------------------------
#  Carpetas
# ---------------------------------------------------------------------------
def config_dir():
    """Configuración e historial."""
    if IS_WINDOWS:
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DVDY Studio")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_ID)


def data_dir():
    """Componentes descargados (FFmpeg, Deno, yt-dlp nuevo)."""
    if IS_WINDOWS:
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "DVDY Studio")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_ID)


def _xdg_user_dir(key):
    """Lee ~/.config/user-dirs.dirs (p. ej. XDG_DOWNLOAD_DIR="$HOME/Descargas")."""
    home = os.path.expanduser("~")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    try:
        with open(os.path.join(base, "user-dirs.dirs"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"XDG_{key}_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    value = value.replace("$HOME", home)
                    if os.path.isabs(value) and os.path.normpath(value) != os.path.normpath(home):
                        return value
    except OSError:
        pass
    return None


def user_dir(kind):
    """Carpeta personal de «download» o «music»; si no existe, la carpeta del usuario."""
    home = os.path.expanduser("~")
    candidates = []
    if IS_LINUX:
        xdg = _xdg_user_dir({"download": "DOWNLOAD", "music": "MUSIC"}[kind])
        if xdg:
            candidates.append(xdg)
    candidates.append(os.path.join(home, {"download": "Downloads", "music": "Music"}[kind]))
    for path in candidates:
        if os.path.isdir(path):
            return path
    return home


# ---------------------------------------------------------------------------
#  Procesos
# ---------------------------------------------------------------------------
def fix_frozen_environment():
    """Linux + PyInstaller: que los programas externos no hereden las librerías empaquetadas.

    El ejecutable de PyInstaller pone su carpeta en LD_LIBRARY_PATH para cargar sus propias
    librerías. Si un programa del sistema (ffmpeg de apt, xdg-open, el gestor de archivos,
    pkexec) lo hereda, puede cargar una versión equivocada y fallar. Este proceso ya cargó sus
    librerías al arrancar, así que restaurar la variable original no lo afecta.
    """
    if not (IS_LINUX and FROZEN):
        return
    for var in ("LD_LIBRARY_PATH",):
        orig = os.environ.get(var + "_ORIG")
        if orig is not None:
            os.environ[var] = orig
        else:
            os.environ.pop(var, None)


def _spawn(cmd):
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError:
        return False


def open_path(path):
    """Abre un archivo o carpeta con el programa predeterminado."""
    if not path or not os.path.exists(path):
        return
    if IS_WINDOWS:
        os.startfile(path)
    elif sys.platform == "darwin":
        _spawn(["open", path])
    else:
        _spawn(["xdg-open", path])


def _show_items_dbus(path):
    """Pide al gestor de archivos (Nautilus, Dolphin, Nemo…) que abra la carpeta con el archivo marcado."""
    if not shutil.which("gdbus"):
        return False
    from urllib.parse import quote
    uri = "file://" + quote(os.path.abspath(path))
    try:
        r = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.freedesktop.FileManager1",
             "--object-path", "/org/freedesktop/FileManager1",
             "--method", "org.freedesktop.FileManager1.ShowItems", f"['{uri}']", ""],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def reveal_path(path):
    """Muestra el archivo en su carpeta (o abre la carpeta)."""
    if not path:
        return
    if IS_WINDOWS:
        if os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif os.path.isdir(path):
            os.startfile(path)
        elif os.path.isdir(os.path.dirname(path)):
            os.startfile(os.path.dirname(path))
        return
    if os.path.isfile(path):
        if not _show_items_dbus(path):
            open_path(os.path.dirname(path))
    elif os.path.isdir(path):
        open_path(path)
    elif os.path.isdir(os.path.dirname(path)):
        open_path(os.path.dirname(path))


def show_error_box(text, title="DVDY Studio", question=False):
    """Mensaje antes de que exista Qt (faltan librerías). Devuelve True si se respondió «Sí»."""
    if IS_WINDOWS:
        import ctypes
        flags = 0x24 if question else 0x10
        return ctypes.windll.user32.MessageBoxW(0, text, title, flags) == 6
    print(f"{title}: {text}", file=sys.__stderr__ or sys.stderr)
    if shutil.which("zenity"):
        kind = "--question" if question else "--error"
        try:
            return subprocess.call(["zenity", kind, "--no-wrap", f"--title={title}", f"--text={text}"]) == 0
        except OSError:
            pass
    return False


def gnome_animations_enabled():
    """Linux: respeta «Animaciones» de GNOME (Configuración → Accesibilidad)."""
    if not shutil.which("gsettings"):
        return True
    try:
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=2)
        return r.stdout.strip() != "false"
    except (OSError, subprocess.SubprocessError):
        return True
