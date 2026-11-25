"""Avisos de versión nueva y actualización automática.

Al abrir la app se consulta el último release publicado en GitHub. Si es más nuevo que la
versión instalada, se muestra una ventana (ver update_dialog.py). No se envía ningún dato
del usuario: solo se pide la información pública del release.

La actualización (solo en el programa compilado, no desde el código):
  Windows: se descarga el zip del release, se descomprime en una carpeta temporal y un
           pequeño script espera a que la app se cierre, copia los archivos nuevos sobre la
           carpeta del programa y vuelve a abrirlo.
  Ubuntu:  se descarga el .deb a /tmp y un script espera a que la app se cierre, lo instala
           con «pkexec apt install -y --reinstall» (Ubuntu pide la contraseña) y vuelve a
           abrir la app como el usuario actual.
"""
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from .config import APP_VERSION
from .system import APP_ID, IS_WINDOWS, LINUX_INSTALL_DIR

REPO = "camilolamarque2014-maker/DVDY-studio"
# DVDY_UPDATE_API: solo para probar la actualización con un servidor local
API_LATEST = os.environ.get("DVDY_UPDATE_API") or f"https://api.github.com/repos/{REPO}/releases/latest"
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
    deb = pick_deb(data.get("assets") or [])
    asset_url, asset_size = (zip_url, zip_size) if IS_WINDOWS else (
        (deb.get("browser_download_url", ""), deb.get("size") or 0) if deb else ("", 0))
    return {
        "tag": data.get("tag_name") or "",
        "version": parse_version(data.get("tag_name")),
        "name": data.get("name") or data.get("tag_name") or "",
        "notes": data.get("body") or "",
        "url": data.get("html_url") or f"https://github.com/{REPO}/releases/latest",
        "zip_url": zip_url,
        "zip_size": zip_size,
        "asset_url": asset_url,    # el paquete para este sistema (zip en Windows, .deb en Ubuntu)
        "asset_size": asset_size,
    }


def deb_arch():
    return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower(), platform.machine().lower())


def pick_deb(assets):
    """El .deb de esta arquitectura entre los archivos del release (p. ej. dvdy-studio_2.4.0_amd64.deb)."""
    arch = deb_arch()
    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(f"_{arch}.deb"):
            return a
    return None


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
    """Solo el programa compilado se actualiza solo; desde el código se abre la página del release."""
    if not getattr(sys, "frozen", False):
        return False, "Desde el código fuente no se actualiza solo."
    if not IS_WINDOWS:
        if os.path.realpath(install_dir()) != os.path.realpath(LINUX_INSTALL_DIR):
            return False, "Esta copia no se instaló con el paquete .deb."
        if not shutil.which("pkexec") or not os.path.isfile("/usr/bin/apt"):
            return False, "Falta pkexec o apt para instalar la actualización."
        return True, ""
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


def download_and_prepare(url, progress=None, cancel=None, status=None):
    """Descarga la versión nueva y la deja lista para instalar.

    Windows: devuelve (carpeta de trabajo, carpeta con el nuevo .exe).
    Ubuntu:  devuelve (carpeta de trabajo, ruta del .deb).
    """
    if not IS_WINDOWS:
        return _download_deb(url, progress, cancel, status)
    from .deps import download
    status = status or (lambda s: None)
    work = tempfile.mkdtemp(prefix="dvdy_update_")
    zip_path = os.path.join(work, "update.zip")
    status("Descargando la versión nueva…")
    download(url, zip_path, progress, cancel)
    status("Preparando los archivos…")
    extract_to = os.path.join(work, "new")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_to)
    os.remove(zip_path)
    for root, _dirs, files in os.walk(extract_to):
        if EXE_NAME in files:
            return work, root
    raise RuntimeError("El paquete descargado no contiene el programa.")


def deb_fields(deb_path):
    """Package y Version de un .deb, leídos con dpkg-deb."""
    out = subprocess.run(["dpkg-deb", "--field", deb_path, "Package", "Version"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError("El archivo descargado no es un paquete .deb válido.")
    fields = dict(line.split(": ", 1) for line in out.stdout.splitlines() if ": " in line)
    return fields.get("Package", ""), fields.get("Version", "")


def _download_deb(url, progress=None, cancel=None, status=None):
    from .deps import download
    status = status or (lambda s: None)
    # Carpeta propia en /tmp (nombre único, solo el usuario puede escribir en ella): nadie más
    # puede cambiar el paquete entre la descarga y la instalación como administrador.
    work = tempfile.mkdtemp(prefix="dvdy_update_", dir="/tmp")
    os.chmod(work, 0o755)  # apt lee el .deb con su usuario sin privilegios (_apt)
    deb = os.path.join(work, "dvdy-studio-update.deb")
    status("Descargando la versión nueva…")
    download(url, deb, progress, cancel)
    status("Verificando el paquete…")
    package, version = deb_fields(deb)
    if package != APP_ID or not parse_version(version):
        raise RuntimeError("El paquete descargado no es DVDY Studio.")
    return work, deb


def launch_replacer(work_dir, new_dir, target_dir, wait_pid):
    """Crea y lanza el script que reemplaza el programa cuando la app se cierra.

    En Ubuntu `new_dir` es la ruta del .deb y `target_dir` no se usa (apt sabe dónde va).
    """
    if not IS_WINDOWS:
        return _launch_deb_installer(work_dir, new_dir, wait_pid)
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


def _launch_deb_installer(work_dir, deb_path, wait_pid):
    """Script que espera a que la app se cierre, instala el .deb con pkexec y la vuelve a abrir.

    Corre como el usuario actual; solo apt corre como administrador (pkexec muestra la ventana
    de contraseña de Ubuntu). Si la instalación falla o se cancela, vuelve a abrir la versión
    actual y le avisa por la variable DVDY_UPDATE_FAILED (código:ruta del registro).
    """
    sh = os.path.join(work_dir, "actualizar.sh")
    log = os.path.join(work_dir, "actualizar.log")
    app = sys.executable  # /opt/dvdy-studio/dvdy-studio: apt lo reemplaza en el mismo lugar
    q = shlex.quote
    script = f"""#!/bin/sh
# Instala la versión nueva de DVDY Studio y la vuelve a abrir.
while kill -0 {int(wait_pid)} 2>/dev/null; do sleep 0.5; done
pkexec /usr/bin/apt install -y --reinstall -o DPkg::Lock::Timeout=600 {q(deb_path)} > {q(log)} 2>&1
code=$?
if [ "$code" -eq 0 ]; then
    rm -f {q(deb_path)}
    exec {q(app)}
fi
DVDY_UPDATE_FAILED="$code:{log}" exec {q(app)}
"""
    with open(sh, "w", encoding="utf-8") as f:
        f.write(script)
    os.chmod(sh, 0o755)
    subprocess.Popen(["/bin/sh", sh], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
    return sh


def update_failure_message(value):
    """Texto para el aviso que se muestra al volver a abrir la app tras una instalación fallida."""
    code, _, log = (value or "").partition(":")
    if code in ("126", "127"):
        return ("No se instaló la actualización porque no se ingresó la contraseña. "
                "Puedes intentarlo de nuevo desde el aviso de versión nueva.", log)
    if code == "100" and log and _log_mentions_lock(log):
        return ("No se pudo instalar la actualización porque Ubuntu estaba instalando otras actualizaciones. "
                "Espera a que termine e inténtalo de nuevo desde el aviso de versión nueva.", log)
    return ("No se pudo instalar la actualización. Revisa tu conexión a internet e inténtalo de nuevo. "
            "Los detalles están en el registro de la instalación.", log)


def _log_mentions_lock(log):
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return False
    return bool(re.search(r"lock|bloque", text, re.I))
