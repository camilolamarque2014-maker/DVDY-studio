"""Cola de tareas: descargas con yt-dlp y procesos de FFmpeg ejecutados en segundo plano."""
import itertools
import os
import re
import subprocess
import threading
import time

from PySide6.QtCore import QObject, Signal

from .config import cfg, history
from .utils import CREATE_NO_WINDOW, find_ffmpeg, fmt_size, fmt_time, media_duration

QUEUED, RUNNING, PAUSED, DONE, ERROR, CANCELED = "queued", "running", "paused", "done", "error", "canceled"
STATUS_TEXT = {
    QUEUED: "En cola", RUNNING: "En curso", PAUSED: "Pausado",
    DONE: "Completado", ERROR: "Error", CANCELED: "Cancelado",
}
_ids = itertools.count(1)


class StopTask(Exception):
    pass


class Task:
    kind = "task"
    can_pause = False

    def __init__(self, title):
        self.id = next(_ids)
        self.title = title
        self.status = QUEUED
        self.progress = -1.0  # -1 = indeterminado
        self.detail = ""
        self.speed = ""
        self.eta = ""
        self.output = ""
        self.error = ""
        self.warnings = 0
        self.manager = None
        self._stop = threading.Event()
        self._pause = False
        self._last_emit = 0.0

    # --- comunicación con la interfaz ---
    def emit(self, force=False):
        now = time.monotonic()
        if force or now - self._last_emit > 0.15:
            self._last_emit = now
            if self.manager:
                self.manager.task_updated.emit(self)

    def log(self, level, msg):
        if self.manager:
            self.manager.log.emit(level, f"[#{self.id}] {msg}")

    # --- control ---
    def request_stop(self, pause=False):
        self._pause = pause
        self._stop.set()

    def reset_for_run(self):
        self._stop.clear()
        self._pause = False
        self.error = ""
        self.warnings = 0

    @property
    def stopped(self):
        return self._stop.is_set()

    def run(self):
        raise NotImplementedError

    def history_kind(self):
        return self.kind


class TaskManager(QObject):
    task_added = Signal(object)
    task_updated = Signal(object)
    task_removed = Signal(object)
    task_finished = Signal(object)
    log = Signal(str, str)
    counts_changed = Signal(int, int)  # activas, total

    def __init__(self):
        super().__init__()
        self.tasks = []
        self._done_signal_relay = _Relay()
        self._done_signal_relay.done.connect(self._on_thread_done)

    @property
    def max_concurrent(self):
        return max(1, int(cfg["max_concurrent"] or 1))

    def add(self, task, start=True):
        task.manager = self
        self.tasks.append(task)
        self.task_added.emit(task)
        if start:
            self.schedule()
        self._emit_counts()
        return task

    def remove(self, task):
        if task.status == RUNNING:
            task.request_stop()
        if task in self.tasks:
            self.tasks.remove(task)
            self.task_removed.emit(task)
        self._emit_counts()

    def pause(self, task):
        if task.status == RUNNING and task.can_pause:
            task.request_stop(pause=True)
        elif task.status == QUEUED:
            task.status = PAUSED
            task.emit(True)
            self._emit_counts()

    def resume(self, task):
        if task.status in (PAUSED, ERROR, CANCELED):
            task.status = QUEUED
            task.detail = ""
            task.emit(True)
            self.schedule()

    def cancel(self, task):
        if task.status == RUNNING:
            task.request_stop()
        elif task.status in (QUEUED, PAUSED):
            task.status = CANCELED
            task.emit(True)
        self._emit_counts()

    def pause_all(self):
        for t in list(self.tasks):
            if t.status in (RUNNING, QUEUED):
                self.pause(t)

    def resume_all(self):
        for t in list(self.tasks):
            if t.status == PAUSED:
                self.resume(t)

    def cancel_all(self):
        for t in list(self.tasks):
            if t.status in (RUNNING, QUEUED, PAUSED):
                self.cancel(t)

    def clear_finished(self):
        for t in list(self.tasks):
            if t.status in (DONE, CANCELED, ERROR):
                self.remove(t)

    def active_count(self):
        return sum(1 for t in self.tasks if t.status in (RUNNING, QUEUED))

    def _emit_counts(self):
        self.counts_changed.emit(self.active_count(), len(self.tasks))

    def schedule(self):
        running = sum(1 for t in self.tasks if t.status == RUNNING)
        for t in self.tasks:
            if running >= self.max_concurrent:
                break
            if t.status == QUEUED:
                running += 1
                self._start(t)
        self._emit_counts()

    def _start(self, task):
        # Se ejecuta en el hilo principal: resolver lazy imports pendientes antes del hilo de trabajo
        from .compat import resolve_lazy_imports
        resolve_lazy_imports()
        task.reset_for_run()
        task.status = RUNNING
        task.progress = -1
        task.emit(True)
        threading.Thread(target=self._worker, args=(task,), daemon=True).start()

    def _worker(self, task):
        try:
            task.run()
            if task.stopped:
                task.status = PAUSED if task._pause else CANCELED
            else:
                task.status = DONE
                task.progress = 100
        except StopTask:
            task.status = PAUSED if task._pause else CANCELED
        except Exception as e:  # noqa: BLE001
            if task.stopped:
                task.status = PAUSED if task._pause else CANCELED
            else:
                task.status = ERROR
                task.error = _clean_error(str(e))
                task.log("error", task.error)
        task.speed = task.eta = ""
        if task.status == PAUSED:
            task.detail = "Pausado — se reanudará donde quedó"
        elif task.status == CANCELED:
            task.detail = "Cancelado"
        elif task.status == ERROR:
            task.detail = task.error
        elif task.status == DONE:
            task.detail = "Completado" + (f" con {task.warnings} aviso(s)" if task.warnings else "")
            try:
                if task.kind != "other":
                    history.add(task.title, task.history_kind(), task.output, getattr(task, "url", ""))
            except OSError:
                pass
        task.emit(True)
        self._done_signal_relay.done.emit(task)

    def _on_thread_done(self, task):
        self.task_finished.emit(task)
        self.schedule()


class _Relay(QObject):
    done = Signal(object)


def _clean_error(msg):
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    return msg.replace("ERROR: ", "").strip()


# ---------------------------------------------------------------------------
#  Descarga con yt-dlp
# ---------------------------------------------------------------------------
class _YDLLogger:
    def __init__(self, task):
        self.task = task

    def debug(self, msg):
        if msg.startswith("[debug] "):
            return
        self.info(msg)

    def info(self, msg):
        self.task.log("info", msg)
        m = re.match(r"\[(\w+)\]", msg)
        if m and m.group(1) not in ("download",) and self.task.status == RUNNING:
            stage = m.group(1)
            if stage in ("Merger", "ExtractAudio", "VideoRemuxer", "EmbedThumbnail", "Metadata",
                         "FFmpegMetadata", "SponsorBlock", "ModifyChapters", "SplitChapters",
                         "EmbedSubtitle", "ThumbnailsConvertor", "VideoConvertor", "FixupM3u8"):
                self.task.detail = f"Procesando ({stage})…"
                self.task.emit()

    def warning(self, msg):
        self.task.warnings += 1
        self.task.log("warning", _clean_error(msg))

    def error(self, msg):
        self.task.log("error", _clean_error(msg))


class DownloadTask(Task):
    kind = "download"
    can_pause = True

    def __init__(self, url, opts, title=None, label="Video"):
        super().__init__(title or url)
        self.url = url
        self.opts = opts
        self.label = label
        self._title_known = bool(title)
        self._files = []

    def history_kind(self):
        return self.label

    def _hook(self, d):
        if self.stopped:
            import yt_dlp
            raise yt_dlp.utils.DownloadCancelled("Detenido por el usuario")
        info = d.get("info_dict") or {}
        if not self._title_known and info.get("title"):
            if not info.get("playlist_index"):
                self.title = info["title"]
        prefix = ""
        idx, n = info.get("playlist_index"), info.get("n_entries") or info.get("playlist_count")
        if idx and n:
            prefix = f"[{idx}/{n}] "
            if info.get("playlist_title") and not self._title_known:
                self.title = info["playlist_title"]
        name = info.get("title") or os.path.basename(d.get("filename") or "")
        status = d.get("status")
        if status == "downloading":
            done = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                self.progress = min(100.0, done * 100.0 / total)
            elif d.get("fragment_count"):
                self.progress = (d.get("fragment_index") or 0) * 100.0 / d["fragment_count"]
            else:
                self.progress = -1
            sp = d.get("speed")
            self.speed = f"{fmt_size(sp)}/s" if sp else ""
            self.eta = fmt_time(d.get("eta")) if d.get("eta") is not None else ""
            size = f"{fmt_size(done)} de {fmt_size(total)}" if total else fmt_size(done)
            self.detail = f"{prefix}{name} · {size}"
            self.emit()
        elif status == "finished":
            self.detail = f"{prefix}Descarga terminada, procesando…"
            self.speed = self.eta = ""
            self.emit(True)

    def _pp_hook(self, d):
        if self.stopped:
            import yt_dlp
            raise yt_dlp.utils.DownloadCancelled("Detenido por el usuario")
        if d.get("status") == "started":
            self.detail = f"Procesando ({d.get('postprocessor')})…"
            self.progress = -1
            self.emit(True)

    def _post_hook(self, filepath):
        self._files.append(filepath)
        self.output = filepath

    def run(self):
        import yt_dlp
        opts = dict(self.opts)
        opts["logger"] = _YDLLogger(self)
        opts["progress_hooks"] = [self._hook]
        opts["postprocessor_hooks"] = [self._pp_hook]
        opts["post_hooks"] = [self._post_hook]
        opts["quiet"] = True
        opts["noprogress"] = True
        self.detail = "Obteniendo información…"
        self.emit(True)
        self.log("info", f"Iniciando: {self.url}")
        with yt_dlp.YoutubeDL(opts) as ydl:
            code = ydl.download([self.url])
        if self.stopped:
            return
        if not self.output and opts.get("paths", {}).get("home"):
            self.output = opts["paths"]["home"]
        if len(self._files) > 1:
            self.output = os.path.dirname(self._files[-1])
        if code != 0 and not self._files:
            if opts.get("skip_download"):
                return
            raise RuntimeError("La descarga falló. Revisa el Registro para más detalles.")


# ---------------------------------------------------------------------------
#  Procesos de FFmpeg
# ---------------------------------------------------------------------------
class FFmpegTask(Task):
    """Ejecuta uno o varios comandos de FFmpeg (p. ej. codificación en dos pasadas).

    Cada comando es la lista de argumentos SIN el ejecutable (se añade automáticamente).
    """
    kind = "ffmpeg"

    def __init__(self, title, commands, output="", duration=None, probe=None, cwd=None,
                 cleanup=(), label="FFmpeg", on_done=None):
        super().__init__(title)
        self.commands = commands
        self.output = output
        self.duration = duration
        self.probe = probe
        self.cwd = cwd
        self.cleanup = list(cleanup)
        self.label = label
        self.on_done = on_done
        self.on_probe = None  # función opcional para ajustar la duración detectada
        self._proc = None

    def history_kind(self):
        return self.label

    def request_stop(self, pause=False):
        super().request_stop(pause)
        p = self._proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def run(self):
        ff = find_ffmpeg()
        if not ff:
            raise RuntimeError("No se encontró FFmpeg. Configura su ruta en Ajustes.")
        if self.duration is None and self.probe:
            self.detail = "Analizando archivo…"
            self.emit(True)
            self.duration = media_duration(self.probe)
            if self.duration and self.on_probe:
                self.duration = self.on_probe(self.duration)
        n = len(self.commands)
        try:
            for i, args in enumerate(self.commands):
                if self.stopped:
                    raise StopTask()
                self._run_one(ff, args, i, n)
        finally:
            for f in self.cleanup:
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                except OSError:
                    pass
        if self.on_done and not self.stopped:
            self.on_done(self)

    def _run_one(self, ff, args, index, total_cmds):
        cmd = [ff, "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1", "-nostats", *args]
        self.log("info", "ffmpeg " + " ".join(_quote(a) for a in cmd[1:]))
        pass_txt = f" (pasada {index + 1}/{total_cmds})" if total_cmds > 1 else ""
        self.detail = "Procesando" + pass_txt
        self.emit(True)
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.cwd,
            text=True, encoding="utf-8", errors="replace", creationflags=CREATE_NO_WINDOW)
        err_lines = []

        def read_err():
            for line in self._proc.stderr:
                line = line.rstrip()
                if line:
                    err_lines.append(line)
                    del err_lines[:-40]

        t = threading.Thread(target=read_err, daemon=True)
        t.start()
        out_time = 0.0
        speed = ""
        for line in self._proc.stdout:
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms"):
                try:
                    out_time = int(val) / 1_000_000
                except ValueError:
                    continue
            elif key == "speed":
                speed = val.strip()
            elif key == "total_size":
                try:
                    size = int(val)
                except ValueError:
                    size = None
            elif key == "progress":
                if self.duration:
                    frac = min(1.0, out_time / self.duration)
                    self.progress = (index + frac) * 100.0 / total_cmds
                    remaining = (self.duration - out_time)
                    try:
                        sp = float(speed.rstrip("x"))
                        self.eta = fmt_time(remaining / sp) if sp > 0 else ""
                    except ValueError:
                        self.eta = ""
                else:
                    self.progress = -1
                self.speed = speed if speed and speed != "N/A" else ""
                self.detail = f"Procesando{pass_txt} · {fmt_time(out_time)}" + (
                    f" de {fmt_time(self.duration)}" if self.duration else "")
                self.emit()
        self._proc.wait()
        t.join(timeout=2)
        code = self._proc.returncode
        self._proc = None
        if self.stopped:
            raise StopTask()
        if code != 0:
            for l in err_lines[-15:]:
                self.log("error", l)
            msg = next((l for l in reversed(err_lines) if "rror" in l or "nvalid" in l), None)
            raise RuntimeError(msg or (err_lines[-1] if err_lines else f"FFmpeg terminó con código {code}"))


class CallableTask(Task):
    """Tarea genérica que ejecuta una función Python (p. ej. actualizar yt-dlp)."""
    kind = "other"

    def __init__(self, title, func, label="Tarea"):
        super().__init__(title)
        self.func = func
        self.label = label

    def history_kind(self):
        return self.label

    def run(self):
        self.detail = "Ejecutando…"
        self.emit(True)
        self.func(self)


def _quote(a):
    return f'"{a}"' if (" " in a or not a) else a
