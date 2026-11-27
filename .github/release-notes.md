# DVDY Studio v2.4.2: correcciones
## Correcciones
- **Ubuntu: «Como el sistema» ahora sigue el modo oscuro.** La app le pregunta a Ubuntu si está en modo claro u oscuro, en lugar de depender de una configuración que no lograba leer y que siempre daba claro. Si cambias el modo con la app abierta, se actualiza al instante.
- **Las imágenes que giras ya no salen dañadas.** «Rotar o voltear» guardaba las fotos como video con extensión .jpg. Ahora una imagen sale como imagen (JPG, PNG o WebP, según el original). Lo mismo vale para «Recortar encuadre / redimensionar» y «Marca de agua», que también aceptan imágenes.

## Instalación en Windows
1. Descarga **`DVDY_Studio-v2.4.2-windows-x64.zip`** (abajo, en *Assets*).
2. Descomprímelo y abre **`DVDY Studio.exe`**. Si ya tenías el programa, puedes descomprimirlo encima de la carpeta anterior: tu configuración y tu historial se mantienen. También puedes usar el botón **Actualizar** del aviso de versión nueva.
3. Si faltan FFmpeg o Deno, la app ofrece descargarlos automáticamente.

> Windows SmartScreen puede avisar de que la app es «desconocida» porque no está firmada: **Más información → Ejecutar de todas formas**.

Requiere Windows 10 u 11 de 64 bits.

## Instalación en Ubuntu
1. Descarga **`dvdy-studio_2.4.2_amd64.deb`** (abajo, en *Assets*).
2. Ábrelo con doble clic e instálalo, o en una terminal: `sudo apt install ./dvdy-studio_2.4.2_amd64.deb`. Si ya tenías la app, también puedes usar el botón **Actualizar** del aviso de versión nueva.
3. Búscalo como **DVDY Studio** en tus aplicaciones. Si falta Deno, la app ofrece descargarlo.

Requiere Ubuntu 22.04 o posterior de 64 bits.
