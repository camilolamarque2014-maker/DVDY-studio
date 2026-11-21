# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop

Native Windows desktop app (Windows 10/11, 64-bit) built with Python and PySide6 (Qt Widgets). Not a web app: there is no browser surface, URL, or dev server.

## Users

Primary: non-technical people — the author's friends and acquaintances, and anyone who finds the project on GitHub — who just want to download music or videos (often from YouTube) without dealing with the command line, codecs, or installing developer tools. They open the app, paste a link, pick "video" or "audio", and expect the file to appear in their Downloads or Music folder.

Secondary: people who want more control (format codes, subtitles, SponsorBlock, FFmpeg editing). They are served by the Advanced mode, but they are not who the product is designed around.

## Product Purpose

DVDY Studio is a graphical front end for yt-dlp and FFmpeg. It lets someone download videos, music, and whole playlists from YouTube and 1800+ other sites in the quality they choose, with metadata and cover art, and convert or edit audio and video — all without a terminal.

Success means a non-technical person can install it, get a working download on the first try, and never need to know that yt-dlp, FFmpeg, or Deno exist.

## Positioning

- **All in one:** downloading, playlists and music, search, a download queue, batch conversion, and 22 FFmpeg editing tools live in a single app, instead of separate downloaders and converters.
- **Free and open:** public source on GitHub, no ads, no accounts, no paid tier.

## Operating Context

- Distributed as a zip on GitHub Releases (`DVDY_Studio-vX.Y.Z-windows-x64.zip`) containing `DVDY Studio.exe` plus its `_internal` folder; users unzip and run it. No installer, no admin rights.
- On first launch, if FFmpeg or Deno are missing, the app offers to download them automatically from their official GitHub releases into `%LOCALAPPDATA%\DVDY Studio\bin`. yt-dlp ships inside the exe and can be updated from Settings.
- Unsigned executable: Windows SmartScreen warns on first run ("More info → Run anyway").
- Settings and history live in `%APPDATA%\DVDY Studio`.
- Users may run it on fresh or locked-down Windows installs (e.g. Windows Sandbox) where root certificates and tools are missing; the app must cope.
- Can also run from source (`DVDY_Studio.pyw`) on a machine with Python; it offers to pip-install missing libraries.

## Capabilities and Constraints

Sections (sidebar): Descargar, Playlists y música, Buscar, Cola, Convertir, Herramientas, Inspector, Historial, Registro, Ajustes.

- **Simple / Advanced switch:** Simple mode hides Herramientas, Inspector, Registro, the format table, and advanced options; hidden options fall back to defaults rather than silently applying. Simple mode is the primary experience.
- Downloads: video+audio, audio only, video only, manual format code; quality 144p–8K, container, codec, FPS; subtitles, SponsorBlock, chapters, sections, thumbnail/subtitle-only, info JSON.
- Playlists: track selection, filters, metadata, square cover art, track numbers, album, download archive.
- Search: YouTube, YouTube Music, SoundCloud.
- Queue: parallel tasks, pause/resume, retry, cancel.
- Convert: batch FFmpeg conversion with quick presets; Tools: 22 FFmpeg utilities.
- UI language is Spanish only. No i18n layer exists.
- Depends on third-party behaviour that changes often (YouTube); errors must be explainable and recoverable (update yt-dlp, retry, view log).
- Built with PyInstaller (`build.py`, output in `compilacion/`).
- **Open decision:** project license is not chosen yet (GPL-3.0 vs MIT was discussed; MIT would require dropping the bundled mutagen).

## Brand Commitments

- Name: **DVDY Studio**. Current version 2.0.1 (the original single-file script was v1).
- Voice: Spanish addressed with **"tú"** (neutral Spanish: "Pega", "Elige", "Descarga"), plain and friendly, no jargon in the primary flow. Technical terms (codecs, CRF, LUFS) appear only in Advanced surfaces and always with a plain explanation.
- GitHub description: "Interfaz gráfica para yt-dlp y FFmpeg: descarga videos, música y playlists de YouTube y +1800 sitios en la calidad que elijas, con metadatos y carátulas. Convierte y edita audio y video (MP4→MP3, recortar, comprimir, GIF). Modo simple/avanzado, cola de descargas e instalación automática de FFmpeg. Ejecutable para Windows, sin Python."

## Evidence on Hand

- Repository: https://github.com/camilolamarque2014-maker/DVDY-studio
- Releases: v2.0.0 and v2.0.1 (latest) on GitHub Releases.
- `README.md` documents installation, features, building, and credits (yt-dlp, FFmpeg, Deno, Qt/PySide6).
- No user counts, testimonials, reviews, press, or download statistics exist. Do not fabricate any.

## Product Principles

1. **First download must just work.** Defaults, automatic dependency install, and plain language exist so a non-technical user succeeds without help.
2. **Simple first, power on request.** Every capability may exist, but the Simple mode shows only what a casual user needs; complexity lives behind the Advanced switch, never in their way.
3. **Nothing hidden applies silently.** What the user cannot see falls back to safe defaults; settings never surprise.
4. **Failures explain themselves.** When yt-dlp, FFmpeg, or the network fails, the app says what happened in plain Spanish and offers the fix (update, retry, install, open log).
5. **Free, open, no strings.** No ads, accounts, telemetry, or upsells.

## Accessibility & Inclusion

No formal standard has been committed to. Users are non-technical, so plain language and forgiving flows are a requirement; keyboard and screen-reader support beyond Qt defaults is undecided.
