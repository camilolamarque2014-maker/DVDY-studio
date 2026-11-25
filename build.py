"""Compila DVDY Studio (no necesita Python instalado) y arma el paquete para compartir.

Uso:
    pip install -r requirements.txt pyinstaller
    python build.py

Resultado en Windows:
    compilacion/dist/DVDY Studio/DVDY Studio.exe            (carpeta del programa)
    compilacion/dist/DVDY_Studio-vX.Y.Z-windows-x64.zip     (para GitHub Releases)

Resultado en Linux (Ubuntu):
    compilacion/dist/dvdy-studio/dvdy-studio                (carpeta del programa)
    compilacion/dist/dvdy-studio_X.Y.Z_amd64.deb            (para GitHub Releases)
    El .deb instala el programa en /opt/dvdy-studio, el comando /usr/bin/dvdy-studio, el
    acceso en el menú de aplicaciones y el ícono. Su campo Version sale de APP_VERSION
    (dvdy/config.py), así apt lo reconoce como actualización en cada release.

compilacion/build/ guarda los archivos temporales de PyInstaller.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "compilacion")  # todo lo que genera PyInstaller va aquí
sys.path.insert(0, ROOT)

from dvdy.config import APP_VERSION  # noqa: E402
from dvdy.system import APP_ID, IS_WINDOWS, LINUX_INSTALL_DIR  # noqa: E402

APP = "DVDY Studio" if IS_WINDOWS else APP_ID   # en Linux, un nombre de ejecutable sin espacios
HOMEPAGE = "https://camilolamarque2014-maker.github.io/DVDY-studio/"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)

# Librerías del sistema que Qt necesita en Ubuntu y que PyInstaller no incluye (X11 y Wayland).
DEB_DEPENDS = [
    "libc6 (>= 2.35)", "libegl1", "libgl1", "libfontconfig1", "libfreetype6", "libdbus-1-3",
    "libxkbcommon0", "libxkbcommon-x11-0", "libxcb-cursor0", "libxcb-icccm4", "libxcb-keysyms1",
    "libxcb-shape0", "libxcb-randr0", "libxcb-render-util0", "libxcb-image0", "libxcb-xkb1",
    "libx11-xcb1", "libwayland-client0", "libwayland-cursor0", "libwayland-egl1",
    "xdg-utils", "pkexec | policykit-1",
]

DESKTOP_ENTRY = f"""[Desktop Entry]
Type=Application
Name=DVDY Studio
GenericName=Descargador de videos y música
Comment=Descarga videos, música y playlists, y convierte audio y video
Exec={APP_ID}
Icon={APP_ID}
Terminal=false
Categories=AudioVideo;Video;Audio;Network;
Keywords=youtube;yt-dlp;ffmpeg;descargar;video;música;mp3;playlist;convertir;
StartupWMClass={APP_ID}
StartupNotify=true
"""


def _qt_app():
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication(sys.argv[:1])


def make_icon(path):
    """Dibuja el ícono de la app y lo guarda como .ico con varios tamaños (Windows)."""
    from PySide6.QtGui import QImageWriter
    _app = _qt_app()  # noqa: F841
    from dvdy.theme import app_icon
    icon = app_icon()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = QImageWriter(path, b"ico")
    if not w.canWrite():
        # Sin plugin ICO: guardar PNG y convertir con Pillow si está disponible
        png = path[:-4] + ".png"
        icon.pixmap(256, 256).save(png)
        from PIL import Image
        Image.open(png).save(path, sizes=[(s, s) for s in ICON_SIZES])
        return
    w.write(icon.pixmap(256, 256).toImage())


def make_png_icons(share_dir):
    """Íconos PNG para el tema hicolor de Linux: usr/share/icons/hicolor/NxN/apps/dvdy-studio.png."""
    _app = _qt_app()  # noqa: F841
    from dvdy.theme import app_icon
    icon = app_icon()
    for s in ICON_SIZES:
        d = os.path.join(share_dir, "icons", "hicolor", f"{s}x{s}", "apps")
        os.makedirs(d, exist_ok=True)
        icon.pixmap(s, s).save(os.path.join(d, f"{APP_ID}.png"))


def run_pyinstaller(icon=None):
    import PyInstaller.__main__
    for d in ("build", os.path.join("dist", APP)):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)
    PyInstaller.__main__.run([
        os.path.join(ROOT, "DVDY_Studio.pyw"),
        "--name", APP,
        "--windowed",            # sin ventana de consola
        "--onedir",              # carpeta: arranca mucho más rápido que --onefile
        "--noconfirm",
        "--clean",
        *(["--icon", icon] if icon else []),
        "--paths", ROOT,
        "--collect-submodules", "dvdy",
        "--add-data", os.path.join(ROOT, "dvdy", "assets") + os.pathsep + os.path.join("dvdy", "assets"),  # tipografías (OFL)
        "--collect-submodules", "yt_dlp",
        "--collect-all", "yt_dlp_ejs",
        "--collect-submodules", "mutagen",
        "--hidden-import", "websockets",
        "--collect-data", "certifi",   # cacert.pem: certificados para HTTPS en Windows sin actualizar
        "--hidden-import", "brotli",
        "--hidden-import", "Cryptodome",
        # Módulos de Qt que no se usan (reduce bastante el tamaño)
        *[a for m in ("PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
                      "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
                      "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtBluetooth",
                      "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "tkinter")
          for a in ("--exclude-module", m)],
        "--distpath", os.path.join(OUT, "dist"),
        "--workpath", os.path.join(OUT, "build"),
        "--specpath", os.path.join(OUT, "build"),
    ])
    out_dir = os.path.join(OUT, "dist", APP)
    shutil.copy(os.path.join(ROOT, "README.md"), os.path.join(out_dir, "LEEME.md"))
    return out_dir


def build_windows():
    icon = os.path.join(ROOT, "assets", "icon.ico")
    make_icon(icon)
    out_dir = run_pyinstaller(icon)
    zip_base = os.path.join(OUT, "dist", f"DVDY_Studio-v{APP_VERSION}-windows-x64")
    shutil.make_archive(zip_base, "zip", os.path.join(OUT, "dist"), APP)
    size = os.path.getsize(zip_base + ".zip") / 1e6
    print(f"\nListo:\n  {out_dir}\\{APP}.exe\n  {zip_base}.zip  ({size:.0f} MB)")


def _normalize_permissions(root):
    """Carpetas 755 y archivos 644, salvo los ejecutables (755): lo que espera dpkg."""
    for d, dirs, files in os.walk(root):
        for name in dirs:
            p = os.path.join(d, name)
            if not os.path.islink(p):
                os.chmod(p, 0o755)
        for name in files:
            p = os.path.join(d, name)
            if not os.path.islink(p):
                os.chmod(p, 0o755 if os.stat(p).st_mode & 0o111 else 0o644)


def _dir_size_kb(root):
    total = 0
    for d, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(d, name)
            if not os.path.islink(p):
                total += os.path.getsize(p)
    return (total + 1023) // 1024


def build_deb(out_dir, arch=None):
    """Arma el paquete .deb a partir de la carpeta que generó PyInstaller."""
    from dvdy.updater import deb_arch
    arch = arch or deb_arch()
    stage = os.path.join(OUT, "deb", f"{APP_ID}_{APP_VERSION}_{arch}")
    shutil.rmtree(stage, ignore_errors=True)
    opt = os.path.join(stage, LINUX_INSTALL_DIR.lstrip("/"))
    shutil.copytree(out_dir, opt, symlinks=True)
    usr = os.path.join(stage, "usr")
    os.makedirs(os.path.join(usr, "bin"))
    os.symlink(os.path.join(LINUX_INSTALL_DIR, APP_ID), os.path.join(usr, "bin", APP_ID))
    share = os.path.join(usr, "share")
    os.makedirs(os.path.join(share, "applications"))
    with open(os.path.join(share, "applications", f"{APP_ID}.desktop"), "w", encoding="utf-8") as f:
        f.write(DESKTOP_ENTRY)
    make_png_icons(share)
    doc = os.path.join(share, "doc", APP_ID)
    os.makedirs(doc)
    with open(os.path.join(doc, "copyright"), "w", encoding="utf-8") as f:
        f.write("DVDY Studio\nhttps://github.com/camilolamarque2014-maker/DVDY-studio\n\n"
                "Incluye yt-dlp (Unlicense), Qt / PySide6 (LGPL) y mutagen (GPL-2.0+).\n"
                "Las tipografías Archivo y Archivo Narrow tienen licencia SIL OFL 1.1.\n")
    _normalize_permissions(stage)

    debian = os.path.join(stage, "DEBIAN")
    os.makedirs(debian)
    control = "\n".join([
        f"Package: {APP_ID}",
        f"Version: {APP_VERSION}",          # cambia en cada release: apt lo ve como actualización
        "Section: video",
        "Priority: optional",
        f"Architecture: {arch}",
        "Maintainer: DVDY Studio <camilolamarque2014-maker@users.noreply.github.com>",
        f"Installed-Size: {_dir_size_kb(stage)}",
        "Depends: " + ", ".join(DEB_DEPENDS),
        "Recommends: ffmpeg",
        f"Homepage: {HOMEPAGE}",
        "Description: Descarga videos, música y playlists sin usar la consola",
        " Interfaz gráfica para yt-dlp y FFmpeg: descarga videos, música y playlists de",
        " YouTube y más de 1800 sitios en la calidad que elijas, con metadatos y carátulas.",
        " También convierte y edita audio y video (MP4 a MP3, recortar, comprimir, GIF).",
        "",
    ])
    with open(os.path.join(debian, "control"), "w", encoding="utf-8") as f:
        f.write(control)
    os.chmod(debian, 0o755)
    os.chmod(os.path.join(debian, "control"), 0o644)

    deb = os.path.join(OUT, "dist", f"{APP_ID}_{APP_VERSION}_{arch}.deb")
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", "-Zxz", stage, deb], check=True)
    return deb


def build_linux():
    out_dir = run_pyinstaller()
    deb = build_deb(out_dir)
    size = os.path.getsize(deb) / 1e6
    print(f"\nListo:\n  {out_dir}/{APP}\n  {deb}  ({size:.0f} MB)")


def main():
    if IS_WINDOWS:
        build_windows()
    else:
        build_linux()


if __name__ == "__main__":
    main()
