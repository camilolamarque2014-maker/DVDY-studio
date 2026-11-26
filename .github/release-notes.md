# DVDY Studio v2.4.1: correcciones
## Correcciones
- **Ubuntu: la app ya no deja el cursor en «cargando» al abrirse.** Al arrancar se creaba por un instante una ventana invisible que se quedaba con el aviso de inicio de GNOME. Ahora la ventana principal lo recibe, el cursor vuelve a la normalidad apenas se abre la app y su ícono aparece enseguida en la barra.
- **Windows:** la misma ventana invisible podía aparecer un instante al abrir el programa; ya no se crea.

## Instalación en Windows
1. Descarga **`DVDY_Studio-v2.4.1-windows-x64.zip`** (abajo, en *Assets*).
2. Descomprímelo y abre **`DVDY Studio.exe`**. Si ya tenías el programa, puedes descomprimirlo encima de la carpeta anterior: tu configuración y tu historial se mantienen. También puedes usar el botón **Actualizar** del aviso de versión nueva.
3. Si faltan FFmpeg o Deno, la app ofrece descargarlos automáticamente.

> Windows SmartScreen puede avisar de que la app es «desconocida» porque no está firmada: **Más información → Ejecutar de todas formas**.

Requiere Windows 10 u 11 de 64 bits.

## Instalación en Ubuntu
1. Descarga **`dvdy-studio_2.4.1_amd64.deb`** (abajo, en *Assets*).
2. Ábrelo con doble clic e instálalo, o en una terminal: `sudo apt install ./dvdy-studio_2.4.1_amd64.deb`. Si ya tenías la app, también puedes usar el botón **Actualizar** del aviso de versión nueva.
3. Búscalo como **DVDY Studio** en tus aplicaciones. Si falta Deno, la app ofrece descargarlo.

Requiere Ubuntu 22.04 o posterior de 64 bits.
