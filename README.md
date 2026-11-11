# DVDY Studio

Interfaz gráfica para **yt-dlp** y **FFmpeg**. Sirve para descargar videos, música y playlists de YouTube y de más de 1800 sitios, y para convertir y editar video y audio. No hace falta usar la consola.

## Instalación (sin Python)

1. Descarga `DVDY_Studio-windows-x64.zip` desde la sección **Releases**.
2. Descomprímelo donde quieras y abre **`DVDY Studio.exe`**.
3. La primera vez, si no tienes **FFmpeg** o **Deno**, la app ofrece descargarlos e instalarlos automáticamente con un clic. Pesan unos 250 MB en total y no hace falta ser administrador.

> Windows SmartScreen puede avisar de que la app es «desconocida» porque no está firmada. Pulsa **Más información → Ejecutar de todas formas**.

Los componentes descargados se guardan en `%LOCALAPPDATA%\DVDY Studio\bin`. La configuración y el historial se guardan en `%APPDATA%\DVDY Studio`.

## Funciones

Arriba del menú lateral hay un interruptor **Simple / Avanzado**. El modo Simple muestra solo lo esencial y el Avanzado muestra todas las opciones.

| Sección | Qué hace |
|---|---|
| **Descargar** | Analiza un enlace y muestra miniatura, datos y la tabla de formatos. Descarga video y audio, solo audio o solo video, con calidad de 144p a 8K, eligiendo contenedor, códec y FPS. Incluye subtítulos, SponsorBlock, capítulos, fragmentos, miniatura e info JSON. |
| **Playlists y música** | Playlists, álbumes y canales. Permite elegir las pistas y añade metadatos, carátula cuadrada, número de pista y álbum. Puede recordar lo ya descargado para sincronizar. |
| **Buscar** | Búsqueda en YouTube, YouTube Music y SoundCloud, con descarga en un clic. |
| **Cola** | Descargas en paralelo con pausa y reanudación, reintento y cancelación. |
| **Convertir** | Conversión por lotes, por ejemplo MP4 → MP3. Permite elegir códec (también con la placa de video), calidad, resolución y volumen. |
| **Herramientas** | Recortar, unir, comprimir a X MB, GIF, normalizar volumen, subtítulos, carátulas, marca de agua, cambiar velocidad, rotar y más. |
| **Inspector / Historial / Registro / Ajustes** | Información técnica de los archivos, historial de descargas y conversiones, registro detallado, cookies del navegador, proxy, tema y actualización de componentes. |

Si YouTube cambia algo y las descargas empiezan a fallar, usa **Ajustes → Actualizar yt-dlp**.

## Ejecutar desde el código

Necesitas Python 3.10 o posterior.

```
pip install -r requirements.txt
pythonw DVDY_Studio.pyw
```

Si faltan librerías, el propio `DVDY_Studio.pyw` ofrece instalarlas.

## Generar el .exe

```
pip install -r requirements.txt pyinstaller
python build.py
```

Todo lo que genera PyInstaller queda en la carpeta `compilacion/`. El programa está en `compilacion/dist/DVDY Studio/DVDY Studio.exe`, junto con `compilacion/dist/DVDY_Studio-windows-x64.zip`, que es el archivo para subir a GitHub Releases.

## Créditos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense)
- [FFmpeg](https://ffmpeg.org) (GPL, compilación de [yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds))
- [Deno](https://deno.com) (MIT)
- [Qt / PySide6](https://www.qt.io/qt-for-python) (LGPL)

Usa esta herramienta solo con contenido que tengas derecho a descargar.
