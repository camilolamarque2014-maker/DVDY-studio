"""Traduce errores técnicos de yt-dlp y FFmpeg a español simple, con una acción sugerida.

Cada regla devuelve (mensaje, acción). Acciones posibles:
  "retry"     reintentar tal cual
  "nocookies" reintentar sin las cookies del navegador
  "ffmpeg"    instalar FFmpeg
  "update"    actualizar yt-dlp
  "browser"   abrir el enlace en el navegador (el contenido no se puede bajar; reintentar no sirve)
  None        no hay una acción automática
El texto técnico original se conserva aparte para «Ver detalles» y el Registro.
"""
import re

COOKIE_ERROR = re.compile(r"cookie|keyring|DPAPI|decrypt", re.I)

_RULES = [
    (re.compile(r"(could not copy|failed to (read|load|decrypt)|database is locked|permission denied).*cookie"
                r"|cookie.*(could not|failed|locked|decrypt)|dpapi|keyring|app.bound encryption", re.I),
     "No se pudieron leer las cookies del navegador (suele pasar si está abierto). Se puede reintentar sin ellas.",
     "nocookies"),
    (re.compile(r"sign in to confirm (your|you.re) age|age.restricted|inappropriate for some users", re.I),
     "Este video tiene restricción de edad. Para bajarlo hay que usar las cookies de un navegador con sesión iniciada (Ajustes, modo Avanzado).",
     "browser"),
    (re.compile(r"not a bot|confirm you.re not a bot", re.I),
     "YouTube pidió confirmar que no eres un robot. Espera unos minutos y reintenta, o usa las cookies del navegador.",
     "retry"),
    (re.compile(r"private video|video is private", re.I),
     "Este video es privado: solo puede verlo quien lo subió o quien tenga permiso.",
     "browser"),
    (re.compile(r"members.only|join this channel", re.I),
     "Este video es solo para miembros del canal.",
     "browser"),
    (re.compile(r"video (is )?unavailable|this video is not available|has been removed|no longer available|account .* terminated", re.I),
     "Este video no está disponible: puede haber sido eliminado o estar bloqueado en tu país.",
     "browser"),
    (re.compile(r"unsupported url|no suitable extractor|is not a valid url", re.I),
     "Este enlace no es compatible. Revisa que sea el enlace de un video, una canción o una playlist.",
     None),
    (re.compile(r"ffmpeg|ffprobe", re.I),
     "Falta FFmpeg para terminar el archivo (unir video y audio o convertirlo).",
     "ffmpeg"),
    (re.compile(r"requested format is not available|nsig|signature|js challenge|jsc|http error 403|precondition|po token", re.I),
     "El sitio cambió algo y hay que actualizar el motor de descargas (yt-dlp).",
     "update"),
    (re.compile(r"getaddrinfo|unable to download webpage|timed out|connection (reset|refused|aborted)|network is unreachable|name or service not known|urlopen error", re.I),
     "No hay conexión o el sitio no responde. Revisa tu internet y reintenta.",
     "retry"),
    (re.compile(r"http error 429|too many requests", re.I),
     "El sitio recibió demasiados pedidos seguidos. Espera unos minutos y reintenta.",
     "retry"),
    (re.compile(r"no space left|disk full", re.I),
     "No queda espacio en el disco. Libera espacio o elige otra carpeta.",
     None),
    (re.compile(r"permission denied|access is denied|errno 13", re.I),
     "No se puede guardar en la carpeta elegida. Elige otra carpeta.",
     None),
    (re.compile(r"invalid data found|moov atom not found|could not find codec|unknown encoder", re.I),
     "El archivo está dañado o su formato no es compatible con esta conversión.",
     None),
    (re.compile(r"geo.?restrict|not available in your country", re.I),
     "Este contenido no está disponible en tu país.",
     "browser"),
]


def friendly(raw):
    """Devuelve (mensaje_en_español, acción) para un error técnico."""
    text = (raw or "").strip()
    for pattern, message, action in _RULES:
        if pattern.search(text):
            return message, action
    return "No se pudo completar. Puedes reintentar o ver los detalles técnicos.", "retry"


def is_cookie_error(raw):
    text = raw or ""
    return bool(COOKIE_ERROR.search(text)) and friendly(text)[1] == "nocookies"


ACTION_LABELS = {
    "retry": "Reintentar",
    "nocookies": "Reintentar sin cookies",
    "ffmpeg": "Instalar FFmpeg",
    "update": "Actualizar yt-dlp",
    "browser": "Abrir en el navegador",
}

# Acciones con las que reintentar no tiene sentido
NO_RETRY = {"browser"}
