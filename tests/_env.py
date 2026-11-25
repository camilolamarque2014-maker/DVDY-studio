"""Aísla las pruebas: configuración e historial en una carpeta temporal, nunca en la real.

Cada archivo de prueba importa este módulo ANTES que `dvdy`.
"""
import os
import tempfile

TMP = tempfile.mkdtemp(prefix="dvdy_tests_")
os.environ["APPDATA"] = TMP
os.environ["LOCALAPPDATA"] = TMP
os.environ["XDG_CONFIG_HOME"] = os.path.join(TMP, "config")  # Linux
os.environ["XDG_DATA_HOME"] = os.path.join(TMP, "data")
os.environ["DVDY_BIN_DIR"] = os.path.join(TMP, "bin")

try:
    import yt_dlp  # noqa: F401
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False
