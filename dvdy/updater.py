"""Avisos de versión nueva y actualización automática.

Al abrir la app se consulta el último release publicado en GitHub. Si es más nuevo que la
versión instalada, se muestra una ventana (ver update_dialog.py). No se envía ningún dato
del usuario: solo se pide la información pública del release.

La actualización (solo en el .exe): se descarga el zip del release, se descomprime en una
carpeta temporal y un pequeño script espera a que la app se cierre, copia los archivos
nuevos sobre la carpeta del programa y vuelve a abrirlo.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from .config import APP_VERSION

REPO = "camilolamarque2014-maker/DVDY-studio"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
EXE_NAME = "DVDY Studio.exe"


def parse_version(text):
    """'v2.1.0' -> (2, 1, 0). Devuelve None si no es una versión."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not m:
        return None
    return tuple(int(x or 0) for x in m.groups())


def fetch_latest(timeout=10):
    """Información pública del último release, o None si no se pudo consultar."""
    from .deps import ssl_context
    req = urllib.request.Request(API_LATEST, headers={
        "User-Agent": "DVDY-Studio", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
        data = json.loads(r.read().decode("utf-8"))
    zip_url = ""
    zip_size = 0
    for a in data.get("assets") or []:
        if a.get("name", "").lower().endswith(".zip"):
            zip_url = a.get("browser_download_url", "")
            zip_size = a.get("size") or 0
            break
    return {
        "tag": data.get("tag_name") or "",
        "version": parse_version(data.get("tag_name")),
        "name": data.get("name") or data.get("tag_name") or "",
        "notes": data.get("body") or "",
        "url": data.get("html_url") or f"https://github.com/{REPO}/releases/latest",
        "zip_url": zip_url,
        "zip_size": zip_size,
    }


def newer_release(skip_tag=""):
    """El release más nuevo que la versión instalada (y no omitido), o None."""
    info = fetch_latest()
    current = parse_version(APP_VERSION)
    if not info or not info["version"] or not current:
        return None
    if info["version"] <= current or info["tag"] == skip_tag:
        return None
    return info


def brief_notes(markdown, max_chars=900):
    """Lo esencial de las notas del release: todo antes de «Instalación», recortado."""
    text = markdown or ""
    cut = re.search(r"^#+\s*Instalaci[oó]n", text, re.M | re.I)
    if cut:
        text = text[:cut.start()]
    # Los títulos de las notas van en negrita dentro de la ventana (sin tamaños de encabezado)
    text = re.sub(r"^#+\s*(.+?)\s*$", r"**\1**", text, flags=re.M).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0].rstrip() + "\n\n…"
    return text


# ---------------------------------------------------------------------------
#  Actualización automática (solo en la versión .exe)
# ---------------------------------------------------------------------------
def can_self_update():
    """Solo el .exe se reemplaza solo; desde el código se abre la página del release."""
    if not getattr(sys, "frozen", False):
        return False, "Desde el código fuente no se actualiza solo."
    folder = install_dir()
    probe = os.path.join(folder, ".dvdy_write_test")
    try:
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
    except OSError:
        return False, "No hay permiso para escribir en la carpeta del programa."
    return True, ""


def install_dir():
    return os.path.dirname(os.path.abspath(sys.executable))


def download_and_prepare(zip_url, progress=None, cancel=None, status=None):
    """Descarga el zip y lo descomprime. Devuelve la carpeta que contiene el nuevo .exe."""
    from .deps import download
    status = status or (lambda s: None)
    work = tempfile.mkdtemp(prefix="dvdy_update_")
    zip_path = os.path.join(work, "update.zip")
    status("Descargando la versión nueva…")
    download(zip_url, zip_path, progress, cancel)
    status("Preparando los archivos…")
    extract_to = os.path.join(work, "new")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_to)
    os.remove(zip_path)
    for root, _dirs, files in os.walk(extract_to):
        if EXE_NAME in files:
            return work, root
    raise RuntimeError("El paquete descargado no contiene el programa.")


def launch_replacer(work_dir, new_dir, target_dir, wait_pid):
    """Crea y lanza el script que reemplaza el programa cuando la app se cierra."""
    bat = os.path.join(work_dir, "actualizar.bat")
    log = os.path.join(work_dir, "actualizar.log")
    script = f"""@echo off
chcp 65001 >nul
:esperar
tasklist /FI "PID eq {wait_pid}" 2>nul | find "{wait_pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto esperar
)
robocopy "{new_dir}" "{target_dir}" /E /R:5 /W:1 /NFL /NDL /NJH /NJS /NP > "{log}"
if errorlevel 8 (
    start "" "{os.path.join(target_dir, EXE_NAME)}"
    exit /b 1
)
start "" "{os.path.join(target_dir, EXE_NAME)}"
cd /d "%TEMP%"
rmdir /s /q "{work_dir}"
"""
    with open(bat, "w", encoding="utf-8") as f:
        f.write(script)
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True)
    return bat
