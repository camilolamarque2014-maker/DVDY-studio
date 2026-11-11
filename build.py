"""Genera «DVDY Studio.exe» (no necesita Python instalado) y un .zip listo para compartir.

Uso:
    pip install -r requirements.txt pyinstaller
    python build.py

Resultado:
    compilacion/dist/DVDY Studio/DVDY Studio.exe   (carpeta del programa)
    compilacion/dist/DVDY_Studio-windows-x64.zip   (para compartir o subir a GitHub Releases)
    compilacion/build/                             (archivos temporales de PyInstaller)
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "compilacion")  # todo lo que genera PyInstaller va aquí
sys.path.insert(0, ROOT)
APP = "DVDY Studio"


def make_icon(path):
    """Dibuja el ícono de la app y lo guarda como .ico con varios tamaños."""
    from PySide6.QtGui import QGuiApplication, QImageWriter
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    from dvdy.theme import app_icon
    icon = app_icon("#7c5cff")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    w = QImageWriter(path, b"ico")
    if not w.canWrite():
        # Sin plugin ICO: guardar PNG y convertir con Pillow si está disponible
        png = path[:-4] + ".png"
        icon.pixmap(256, 256).save(png)
        from PIL import Image
        Image.open(png).save(path, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
        return
    w.write(icon.pixmap(256, 256).toImage())


def main():
    import PyInstaller.__main__

    icon = os.path.join(ROOT, "assets", "icon.ico")
    make_icon(icon)
    for d in ("build", os.path.join("dist", APP)):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)

    PyInstaller.__main__.run([
        os.path.join(ROOT, "DVDY_Studio.pyw"),
        "--name", APP,
        "--windowed",            # sin ventana de consola
        "--onedir",              # carpeta: arranca mucho más rápido que --onefile
        "--noconfirm",
        "--clean",
        "--icon", icon,
        "--paths", ROOT,
        "--collect-submodules", "dvdy",
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
    zip_base = os.path.join(OUT, "dist", "DVDY_Studio-windows-x64")
    shutil.make_archive(zip_base, "zip", os.path.join(OUT, "dist"), APP)
    size = os.path.getsize(zip_base + ".zip") / 1e6
    print(f"\nListo:\n  {out_dir}\\{APP}.exe\n  {zip_base}.zip  ({size:.0f} MB)")


if __name__ == "__main__":
    main()
