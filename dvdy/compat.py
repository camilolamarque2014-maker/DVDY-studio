"""Arreglos de compatibilidad con versiones concretas de Python."""
import sys


def resolve_lazy_imports():
    """Python 3.15 introdujo los «lazy imports» (PEP 810) y la biblioteca estándar los usa.

    Por ejemplo, `concurrent.futures` guarda ThreadPoolExecutor como un objeto pendiente
    (tipo `lazy_import`) hasta su primer uso. En algunas compilaciones de Python ese objeto
    pendiente llega a yt-dlp sin resolver al descargar fragmentos (HLS/DASH) desde un hilo,
    y falla con «'lazy_import' object is not callable».

    Aquí se resuelven desde el hilo principal y se guarda la clase real en el módulo, de
    modo que ningún hilo vuelva a ver el objeto pendiente. En versiones anteriores de
    Python no hace nada.
    """
    if sys.version_info < (3, 15):
        return
    try:
        import concurrent.futures as cf
        from concurrent.futures.thread import ThreadPoolExecutor
        cf.ThreadPoolExecutor = ThreadPoolExecutor
    except Exception:
        pass
    # Por seguridad, resolver cualquier otro objeto pendiente en los módulos ya cargados
    for mod in list(sys.modules.values()):
        d = getattr(mod, "__dict__", None)
        if not isinstance(d, dict):
            continue
        for name, val in list(d.items()):
            if type(val).__name__ == "lazy_import":
                try:
                    setattr(mod, name, getattr(mod, name))
                except Exception:
                    pass
