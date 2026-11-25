# DVDY Studio

Interfaz gráfica para **yt-dlp** y **FFmpeg**. Sirve para descargar videos, música y playlists de YouTube y de más de 1800 sitios, y para convertir y editar video y audio. No hace falta usar la consola. Funciona en **Windows 10 y 11** y en **Ubuntu 22.04 o posterior** (64 bits).

**Sitio web y descarga:** https://camilolamarque2014-maker.github.io/DVDY-studio/

## Instalación en Windows (sin Python)

1. Descarga el zip de la versión más reciente (`DVDY_Studio-vX.Y.Z-windows-x64.zip`) desde el [sitio web](https://camilolamarque2014-maker.github.io/DVDY-studio/) o la sección **Releases**.
2. Descomprímelo donde quieras y abre **`DVDY Studio.exe`**.
3. La primera vez, si no tienes **FFmpeg** o **Deno**, la app ofrece descargarlos e instalarlos automáticamente con un clic. Pesan unos 250 MB en total y no hace falta ser administrador.

> Windows SmartScreen puede avisar de que la app es «desconocida» porque no está firmada. Pulsa **Más información → Ejecutar de todas formas**.

Los componentes descargados se guardan en `%LOCALAPPDATA%\DVDY Studio\bin`. La configuración y el historial se guardan en `%APPDATA%\DVDY Studio`.

## Instalación en Ubuntu

1. Descarga el paquete de la versión más reciente (`dvdy-studio_X.Y.Z_amd64.deb`) desde el [sitio web](https://camilolamarque2014-maker.github.io/DVDY-studio/) o la sección **Releases**.
2. Ábrelo con doble clic e instálalo desde el Centro de aplicaciones, o desde una terminal:

```
sudo apt install ./dvdy-studio_X.Y.Z_amd64.deb
```

3. Búscalo como **DVDY Studio** en tus aplicaciones, o escribe `dvdy-studio` en una terminal. Si falta **Deno**, la app ofrece bajarlo. **FFmpeg** se instala junto con el paquete.

Funciona en Ubuntu 22.04 o posterior y en sistemas basados en Ubuntu (Linux Mint, Pop!_OS, Zorin…). El programa queda en `/opt/dvdy-studio`. Los componentes descargados se guardan en `~/.local/share/dvdy-studio/bin`. La configuración y el historial se guardan en `~/.config/dvdy-studio`.

Cuando hay una versión nueva, el botón **Actualizar** del aviso baja el `.deb`, cierra la app, la instala (Ubuntu te pide tu contraseña) y la vuelve a abrir. Para desinstalarla: `sudo apt remove dvdy-studio`.

## Funciones

Arriba del menú lateral hay un interruptor **Simple / Avanzado**. El modo Simple muestra solo lo esencial y el Avanzado muestra todas las opciones.

La primera vez que abres la app aparece un tutorial corto de cinco pasos. Puedes volver a verlo desde **Ajustes → Ver el tutorial de nuevo**.

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

En Windows:

```
pip install -r requirements.txt
pythonw DVDY_Studio.pyw
```

Si faltan librerías, el propio `DVDY_Studio.pyw` ofrece instalarlas.

En Ubuntu, dentro de un entorno virtual (Ubuntu no deja instalar con pip fuera de uno):

```
sudo apt install python3-venv libxcb-cursor0
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python DVDY_Studio.pyw
```

## Compilar el programa

```
pip install -r requirements.txt pyinstaller
python build.py
```

Todo lo que genera PyInstaller queda en la carpeta `compilacion/`, que no se guarda en git. `build.py` hace el paquete del sistema donde se ejecuta:

- **Windows:** `compilacion/dist/DVDY Studio/DVDY Studio.exe` y `compilacion/dist/DVDY_Studio-vX.Y.Z-windows-x64.zip`.
- **Ubuntu:** `compilacion/dist/dvdy-studio/dvdy-studio` y `compilacion/dist/dvdy-studio_X.Y.Z_amd64.deb`. Necesita `dpkg-deb` (viene con Ubuntu). El campo `Version` del paquete sale de `APP_VERSION`, así apt reconoce cada versión nueva como actualización.

## Publicar una versión

1. Cambia `APP_VERSION` en `dvdy/config.py` y escribe las notas en `.github/release-notes.md`.
2. Haz commit, crea la etiqueta y súbela:

```
git tag vX.Y.Z
git push origin main vX.Y.Z
```

GitHub Actions (`.github/workflows/release.yml`) corre las pruebas y compila en Windows y en Ubuntu 22.04. En Ubuntu también instala el `.deb`. En los dos sistemas prueba el programa con `--selftest`. Si todo sale bien, publica el release con el zip y el `.deb`.

## Pruebas

```
python -m unittest discover -s tests -t . -v
```

Las pruebas que necesitan yt-dlp se saltan si no está instalado.

## Créditos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense)
- [FFmpeg](https://ffmpeg.org) (GPL, compilación de [yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds))
- [Deno](https://deno.com) (MIT)
- [Qt / PySide6](https://www.qt.io/qt-for-python) (LGPL)

## Testers

-[pablolamarque-droid](https://github.com/pablolamarque-droid)


Usa esta herramienta solo con contenido que tengas derecho a descargar.
