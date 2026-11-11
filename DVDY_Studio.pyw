"""DVDY Studio — interfaz gráfica para yt-dlp y FFmpeg.

Se puede ejecutar de dos formas:
  * Como programa (DVDY Studio.exe), generado con build.py: no necesita Python.
  * Desde el código: doble clic en este archivo. Si faltan librerías de Python, ofrece instalarlas.

FFmpeg y Deno se descargan desde la propia app si no están en el equipo.
"""
import os
import subprocess
import sys
import traceback

FROZEN = bool(getattr(sys, "frozen", False))
if not FROZEN:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Sin consola (pythonw.exe o .exe con ventana) stdout/stderr son None y yt-dlp fallaría al escribir.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

PY_PACKAGES = [("PySide6", "PySide6"), ("yt_dlp", "yt-dlp[default]"), ("mutagen", "mutagen")]


def _msgbox(text, title="DVDY Studio", flags=0x40):
    import ctypes
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags)


def _ensure_python_packages():
    """Solo al ejecutar desde el código: instala con pip las librerías que falten."""
    missing = []
    for mod, pkg in PY_PACKAGES:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if not missing:
        return True
    ans = _msgbox("Faltan estas librerías de Python:\n\n    " + "\n    ".join(missing) +
                  "\n\n¿Quieres instalarlas automáticamente ahora? (necesita Internet, tarda uno o dos minutos)",
                  flags=0x24)  # Sí / No + icono de pregunta
    if ans != 6:  # IDYES
        return False
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        exe = exe[:-len("pythonw.exe")] + "python.exe"
    # Consola visible para que se vea el progreso de pip
    code = subprocess.call([exe, "-m", "pip", "install", "--upgrade", *missing],
                           creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    if code != 0:
        _msgbox("No se pudieron instalar las librerías. Prueba manualmente con:\n\npip install " +
                " ".join(f'"{m}"' for m in missing), flags=0x10)
        return False
    import importlib
    importlib.invalidate_caches()
    return True


def _excepthook(etype, value, tb):
    msg = "".join(traceback.format_exception(etype, value, tb))
    try:
        from dvdy.config import CONFIG_DIR
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(os.path.join(CONFIG_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Error inesperado", msg[-3000:])
    except Exception:
        pass


def main():
    if not FROZEN and not _ensure_python_packages():
        return
    sys.excepthook = _excepthook

    # Python 3.15: resolver los «lazy imports» antes de crear hilos de descarga
    from dvdy.compat import resolve_lazy_imports
    resolve_lazy_imports()

    # Si se descargó un yt-dlp más nuevo desde la app, usarlo (antes de importar yt_dlp)
    from dvdy.deps import activate_ytdlp_override
    activate_ytdlp_override()

    if os.name == "nt":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dvdy.studio.2")
        except Exception:
            pass

    from PySide6.QtWidgets import QApplication
    from dvdy.config import APP_NAME, cfg
    from dvdy.main_window import MainWindow
    from dvdy.theme import build_qss

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(build_qss(cfg["theme"], cfg["accent"]))
    if "--selftest" in sys.argv:
        return _selftest(sys.argv[sys.argv.index("--selftest") + 1])
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


def _selftest(out_dir):
    """Prueba interna para verificar una compilación: DVDY Studio.exe --selftest CARPETA."""
    os.makedirs(out_dir, exist_ok=True)
    report = open(os.path.join(out_dir, "selftest.txt"), "w", encoding="utf-8")

    def log(*a):
        report.write(" ".join(str(x) for x in a) + "\n")
        report.flush()

    try:
        import yt_dlp
        from dvdy import deps
        from dvdy.setup_dialog import SetupDialog
        from dvdy.tasks import DownloadTask, FFmpegTask
        from dvdy.utils import find_ffmpeg, find_js_runtime
        from dvdy.ytopts import build_opts, default_choices
        log("frozen:", FROZEN, "yt-dlp:", yt_dlp.version.__version__, "ffmpeg:", find_ffmpeg(),
            "js:", find_js_runtime(), "faltan:", deps.missing_components())
        dlg = SetupDialog(None, components=("ffmpeg", "deno", "yt-dlp"), preselect=("ffmpeg", "deno"))
        dlg.show()
        dlg.grab().save(os.path.join(out_dir, "setup_dialog.png"))
        dlg.close()
        # HTTPS solo con los certificados de certifi (simula un Windows sin certificados raíz)
        import ssl
        import certifi
        import urllib.request
        only = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        only.load_verify_locations(cafile=certifi.where())
        with urllib.request.urlopen(deps.URLS["yt-dlp"], timeout=60, context=only) as r:
            r.read(1024)
        log("https solo con certifi: OK", os.path.isfile(certifi.where()))
        deps._ssl_ctx = only  # el instalador también usará solo certifi, como en Windows Sandbox
        if "--install" in sys.argv:
            for key in deps.missing_components():
                deps.install(key, status=lambda s: log("  ", s))
            log("tras instalar, faltan:", deps.missing_components(), "ffmpeg:", find_ffmpeg(), "js:", find_js_runtime())
        url ="https://www.youtube.com/watch?v=jNQXAC9IVRw"
        import concurrent.futures as cf
        log("ThreadPoolExecutor en el módulo:", type(cf.__dict__.get("ThreadPoolExecutor")).__name__)
        # audio, video y video por fragmentos HLS (usa ThreadPoolExecutor en paralelo)
        for kind, fmt in (("audio", None), ("video", None), ("hls", "bv*[protocol^=m3u8]+ba/b")):
            c = default_choices(kind == "audio")
            c["output_dir"] = out_dir
            c["quality"] = "360"
            c["template"] = f"%(title)s [{kind}].%(ext)s"
            opts = build_opts(c)
            if fmt:
                opts["format"] = fmt
            t = DownloadTask(url, opts)
            # En un hilo aparte, igual que en la app
            import threading
            err = []

            def _run(task=t):
                try:
                    task.run()
                except Exception:
                    err.append(traceback.format_exc())

            th = threading.Thread(target=_run)
            th.start()
            th.join()
            if err:
                raise RuntimeError(err[0])
            log("descarga", kind, "->", t.output, "avisos:", t.warnings)
            if kind == "video":
                src = t.output
        dst = os.path.join(out_dir, "convertido.mp3")
        f = FFmpegTask("conv", [["-i", src, "-vn", "-b:a", "192k", dst]], output=dst, probe=src)
        f.run()
        log("ffmpeg ->", dst, os.path.getsize(dst), "bytes")
        log("OK")
    except Exception:
        log("FALLO:\n" + traceback.format_exc())
    report.close()


if __name__ == "__main__":
    main()
