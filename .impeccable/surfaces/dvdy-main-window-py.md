---
version: 1
slug: "dvdy-main-window-py"
primary_target: "dvdy/main_window.py"
related_targets: ["dvdy/theme.py","dvdy/page_download.py"]
---

# Surface brief: DVDY Studio app shell (all screens)

Mode: Operate. Scope: whole desktop app (PySide6/Qt), Simple and Advanced modes.

## Audience and job
Non-technical people on a Windows laptop at home who want a song, a video or a playlist as files, without knowing formats. Primary task: paste a link, choose Video or Música, download, then open the file.

## Constraints
- Native Qt Widgets + QSS; fonts bundled inside the exe (OFL).
- Spanish, "tú". All current functionality stays; download logic untouched.
- Simple mode = one complete screen (link, Video/Música, quality, format, folder, subtitles visible; "Más opciones" expands everything else; queue beside it). Advanced keeps every section and tool.
- Dark is the primary rendition; a light rendition of the same world activates automatically when Windows is in light mode.
- Fixes from the 2026-11-20 critique: cookie failure, Spanish errors with actions, finished items show file + Abrir, visible keyboard focus, accessible names, Enter downloads.

## Direction contract
THESIS: The app is a radio left on at night: graphite chrome, ivory type, and one amber light that marks only what is playing now, here what is downloading. It refuses the category default of a dark dev tool with a neon accent and a sidebar of forms.

OWN-WORLD: Graphite #131315 ground, #1d1d21 panels, #2a2a30 hairlines; ivory #f4ede0 text, #8c8a86 secondary; amber #e9a23b reserved for the active item, the dial needle and the selected band; muted red #c8553d for errors. Archivo for text, Archivo Narrow uppercase tracked labels and numerals. Three type sizes. Colour lives only in cover art and the amber light; covers untinted, flat, no gradients.

STORY: The visitor pastes a link, sees the item recognised with its cover, picks Video or Música like an AM/FM band, presses Descargar, watches the amber needle move on the dial, and opens the finished file from the same screen.

FIRST VIEWPORT: Top bar: DVDY·STUDIO wordmark, text nav, Simple/Avanzado switch at right. Left panel (about two thirds): link field, VIDEO / MÚSICA band with amber indicator, four option tiles (Calidad, Formato, Carpeta, Subtítulos), "Más opciones" toggle, preview row (cover, title, meta) and the ivory Descargar button. Right panel: EN EL DIAL, a tick-scale dial strip with the amber needle at the active download's progress, then the queue rows with cover, status line and text actions (Pausar, Abrir, Carpeta, Reintentar).

FORM: grounded direction 7 of 7 (Radio de Madrugada), seed:6c49421f31edb19a. Raises: colour only inside covers and the amber light (lexicon); covers untinted, flat colour (zoo map); playlists as a dense whole-cell thumbnail grid with marked selection (doujin catalog); three type sizes, rank by weight and case (timetable).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
