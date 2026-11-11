"""Gestor de componentes externos: descarga e instala FFmpeg, Deno y versiones nuevas de yt-dlp.

Todo se guarda en %LOCALAPPDATA%\\DVDY Studio\\bin, así no hace falta permisos de administrador
ni tocar el PATH del sistema. Las descargas salen de las releases oficiales en GitHub.
"""
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

BIN_DIR = os.environ.get("DVDY_BIN_DIR") or os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "DVDY Studio", "bin")
YTDLP_ZIP = os.path.join(BIN_DIR, "yt-dlp.zip")

FROZEN = bool(getattr(sys, "frozen", False))

URLS = {
    # Compilación de FFmpeg mantenida por el equipo de yt-dlp (incluye ffmpeg.exe y ffprobe.exe)
    "ffmpeg": "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "deno": "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip",
    # Versión «zipimport» oficial de yt-dlp (Python puro): se carga sin reinstalar el programa
    "yt-dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
}

COMPONENTS = {
    "ffmpeg": {
        "name": "FFmpeg",
        "desc": "Necesario para unir video y audio, convertir a MP3, incrustar carátulas y todas las herramientas.",
        "size": "≈ 200 MB",
        "required": True,
    },
    "deno": {
        "name": "Deno",
        "desc": "Intérprete de JavaScript que YouTube exige para ofrecer todos los formatos y calidades.",
        "size": "≈ 45 MB",
        "required": True,
    },
    "yt-dlp": {
        "name": "yt-dlp (última versión)",
        "desc": "El motor de descargas. Actualizarlo soluciona la mayoría de los errores cuando YouTube cambia algo.",
        "size": "≈ 3 MB",
        "required": False,
    },
}


class Cancelled(Exception):
    pass


def bin_path(name):
    return os.path.join(BIN_DIR, name + (".exe" if os.name == "nt" else ""))


def local_ffmpeg():
    p = bin_path("ffmpeg")
    return p if os.path.isfile(p) else None


def local_deno():
    p = bin_path("deno")
    return p if os.path.isfile(p) else None


def missing_components():
    """Componentes imprescindibles que no se encuentran en ningún lado."""
    from .utils import find_ffmpeg, find_ffprobe, find_js_runtime
    missing = []
    if not find_ffmpeg() or not find_ffprobe():
        missing.append("ffmpeg")
    if not find_js_runtime()[0]:
        missing.append("deno")
    return missing


# ---------------------------------------------------------------------------
#  Descarga con progreso
# ---------------------------------------------------------------------------
_ssl_ctx = None


def ssl_context():
    """Contexto HTTPS con los certificados de Windows MÁS los de certifi.

    Un Windows recién instalado (o Windows Sandbox) trae muy pocos certificados raíz:
    Windows los descarga solo cuando un programa propio los pide, pero Python no usa ese
    mecanismo y fallaría con CERTIFICATE_VERIFY_FAILED. Con certifi (incluido en la app)
    la verificación funciona igual, sin desactivar la seguridad.
    """
    global _ssl_ctx
    if _ssl_ctx is None:
        import ssl
        ctx = ssl.create_default_context()  # certificados del sistema
        try:
            import certifi
            ctx.load_verify_locations(cafile=certifi.where())
        except Exception:
            pass
        _ssl_ctx = ctx
    return _ssl_ctx


def urlopen(url, timeout=60, user_agent="DVDY-Studio"):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())


def download(url, dest, progress=None, cancel=None):
    """Descarga url -> dest. progress(hechos, total). cancel: threading.Event."""
    with urlopen(url, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            while True:
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    if total and done < total:
        raise IOError("La descarga quedó incompleta. Revisa tu conexión e inténtalo de nuevo.")


def _extract(zip_path, wanted):
    """Extrae del zip los archivos cuyo nombre base esté en `wanted` hacia BIN_DIR."""
    os.makedirs(BIN_DIR, exist_ok=True)
    found = set()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            base = os.path.basename(info.filename).lower()
            if base in wanted and not info.is_dir():
                target = os.path.join(BIN_DIR, base)
                tmp = target + ".new"
                with z.open(info) as src, open(tmp, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.replace(tmp, target)
                found.add(base)
    missing = set(wanted) - found
    if missing:
        raise RuntimeError("El paquete descargado no contiene: " + ", ".join(sorted(missing)))


def install(component, progress=None, status=None, cancel=None):
    """Descarga e instala un componente. status(texto) informa la etapa."""
    status = status or (lambda s: None)
    os.makedirs(BIN_DIR, exist_ok=True)
    url = URLS[component]
    name = COMPONENTS[component]["name"]
    fd, tmp = tempfile.mkstemp(prefix="dvdy_", suffix=".download")
    os.close(fd)
    try:
        status(f"Descargando {name}…")
        download(url, tmp, progress, cancel)
        if component == "ffmpeg":
            status("Descomprimiendo FFmpeg…")
            _extract(tmp, {"ffmpeg.exe", "ffprobe.exe"})
            from . import utils
            utils._encoders_cache = None
        elif component == "deno":
            status("Descomprimiendo Deno…")
            _extract(tmp, {"deno.exe"})
        elif component == "yt-dlp":
            status("Verificando yt-dlp…")
            with zipfile.ZipFile(tmp) as z:
                if "yt_dlp/__init__.py" not in z.namelist():
                    raise RuntimeError("El archivo descargado no es un paquete válido de yt-dlp.")
            os.replace(tmp, YTDLP_ZIP)
            tmp = None
        status(f"{name} instalado correctamente.")
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------------------
#  yt-dlp actualizado
# ---------------------------------------------------------------------------
def activate_ytdlp_override():
    """Si hay un yt-dlp descargado más nuevo, úsalo en lugar del incluido.

    Debe llamarse ANTES de cualquier `import yt_dlp`. Si el archivo está dañado o no es
    compatible, se descarta y se vuelve a la versión incluida.
    """
    if not os.path.isfile(YTDLP_ZIP):
        return None
    sys.path.insert(0, YTDLP_ZIP)
    try:
        import yt_dlp  # noqa: F401
        from yt_dlp.version import __version__
        bundled = _bundled_version()
        if bundled and _vkey(bundled) > _vkey(__version__):
            raise ImportError("la versión incluida es más nueva")
        return __version__
    except Exception:
        sys.path.remove(YTDLP_ZIP)
        for m in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
            del sys.modules[m]
        return None


def _vkey(v):
    return tuple(int(x) for x in v.replace("-", ".").split(".") if x.isdigit())


def _bundled_version():
    """Versión de yt-dlp incluida en el programa (sin cargarla)."""
    import importlib.util
    for p in sys.path:
        if p == YTDLP_ZIP:
            continue
        cand = os.path.join(p, "yt_dlp", "version.py")
        if os.path.isfile(cand):
            spec = importlib.util.spec_from_file_location("_dvdy_ytv", cand)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                return mod.__version__
            except Exception:
                return None
    return None
