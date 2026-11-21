---
name: DVDY Studio
description: A Windows downloader that looks like a radio left on at night. Graphite, ivory, and one amber light for what is playing now.
colors:
  graphite: "#131315"
  graphite-panel: "#1d1d21"
  graphite-raised: "#24242a"
  hairline: "#2a2a30"
  hairline-strong: "#3a3a42"
  ivory: "#f4ede0"
  ash: "#8c8a86"
  smoke: "#5f5d5a"
  dial-amber: "#e9a23b"
  ember-red: "#c8553d"
  ember-red-text: "#e07a63"
  console-black: "#0f0f11"
  light-ground: "#ecebe7"
  light-panel: "#f8f7f4"
  light-raised: "#f1f0ec"
  light-hairline: "#dddad3"
  light-hairline-strong: "#c4c0b7"
  light-ink: "#18181a"
  light-ash: "#64615b"
  light-smoke: "#9a968e"
  light-amber: "#c9821c"
  light-amber-text: "#8f5508"
  light-ember-red: "#a8402c"
typography:
  title:
    fontFamily: "Archivo, Segoe UI, sans-serif"
    fontSize: "17pt"
    fontWeight: 700
  body:
    fontFamily: "Archivo, Segoe UI, sans-serif"
    fontSize: "10.5pt"
    fontWeight: 400
  body-strong:
    fontFamily: "Archivo, Segoe UI, sans-serif"
    fontSize: "10.5pt"
    fontWeight: 700
  small:
    fontFamily: "Archivo, Segoe UI, sans-serif"
    fontSize: "9pt"
    fontWeight: 400
  label:
    fontFamily: "Archivo Narrow, Archivo, sans-serif"
    fontSize: "9pt"
    fontWeight: 600
    letterSpacing: "1px"
  band:
    fontFamily: "Archivo Narrow, Archivo, sans-serif"
    fontSize: "10.5pt"
    fontWeight: 700
    letterSpacing: "0.18em"
  wordmark:
    fontFamily: "Archivo Narrow, Archivo, sans-serif"
    fontSize: "17pt"
    fontWeight: 700
    letterSpacing: "1px"
rounded:
  hair: "2px"
  check: "4px"
  sm: "6px"
  md: "8px"
  tile: "9px"
  lg: "10px"
  panel: "12px"
  pill: "12px"
spacing:
  xxs: "4px"
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "22px"
  gutter: "28px"
components:
  button-primary:
    backgroundColor: "{colors.ivory}"
    textColor: "{colors.graphite}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.lg}"
    padding: "11px 30px"
  button-primary-hover:
    backgroundColor: "{colors.ash}"
    textColor: "{colors.graphite}"
  button-primary-disabled:
    backgroundColor: "{colors.hairline}"
    textColor: "{colors.smoke}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ivory}"
    rounded: "{rounded.md}"
    padding: "7px 14px"
  button-small:
    backgroundColor: "transparent"
    textColor: "{colors.ivory}"
    typography: "{typography.small}"
    rounded: "{rounded.sm}"
    padding: "4px 10px"
  button-small-primary:
    backgroundColor: "{colors.ivory}"
    textColor: "{colors.graphite}"
    typography: "{typography.small}"
    rounded: "{rounded.sm}"
    padding: "4px 12px"
  button-flat:
    backgroundColor: "transparent"
    textColor: "{colors.ash}"
    padding: "5px 8px"
  input:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.ivory}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "6px 10px"
  input-url:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.ivory}"
    rounded: "{rounded.lg}"
    padding: "14px 16px"
    height: "54px"
  panel:
    backgroundColor: "{colors.graphite-panel}"
    rounded: "{rounded.panel}"
    padding: "22px 24px"
  option-tile:
    backgroundColor: "transparent"
    textColor: "{colors.ivory}"
    rounded: "{rounded.tile}"
    padding: "8px 12px 6px 12px"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ash}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "7px 12px"
  nav-item-active:
    backgroundColor: "transparent"
    textColor: "{colors.ivory}"
    typography: "{typography.body-strong}"
  band-active:
    textColor: "{colors.ivory}"
    typography: "{typography.band}"
    height: "34px"
  cover:
    backgroundColor: "{colors.graphite-raised}"
    rounded: "{rounded.md}"
    size: "400px 225px"
  task-cover:
    backgroundColor: "{colors.graphite-raised}"
    rounded: "{rounded.sm}"
    size: "56px"
  progress-track:
    backgroundColor: "{colors.hairline}"
    rounded: "{rounded.hair}"
    height: "3px"
  progress-active:
    backgroundColor: "{colors.dial-amber}"
  progress-failed:
    backgroundColor: "{colors.ember-red}"
  toggle-switch:
    backgroundColor: "{colors.hairline-strong}"
    rounded: "{rounded.pill}"
    size: "44px 24px"
---

# Design System: DVDY Studio

## Overview

**Creative North Star: "Radio de Madrugada"**

The app is a radio left on at night. Graphite chrome, ivory type, and a single amber light that marks only what is playing now: here, what is downloading. Everything else is quiet. Panels are flat graphite slabs separated by hairlines rather than shadows; labels are set like the printing on a tuner faceplate, narrow, uppercase and tracked; the one moving part is the dial needle sliding across a scale of fine ticks.

Colour has two homes and only two: the cover art of whatever was pasted, shown large and untinted, and the amber light. Interaction uses ivory, not amber: the primary button is an ivory slab, focus is an ivory outline, the selected nav item is ivory text with an ivory underline. That keeps amber legible as a status signal instead of a brand tint. The system refuses the dark developer tool with a neon accent and a sidebar of forms; options live in four bordered tiles on one panel, and advanced controls fold away behind "Más opciones".

Dark is the primary rendition. A light rendition of the same world (warm paper ground, ink type, deeper amber) is used when Windows is in light mode or the user picks "Claro"; it keeps every rule, only the values change.

**Key Characteristics:**
- Graphite ground, graphite panels, hairline borders; no shadows anywhere.
- Ivory is the interaction colour; amber is a status light, never a decoration.
- Archivo for reading, Archivo Narrow uppercase tracked for labels, bands and numerals.
- Three type sizes (9pt, 10.5pt, 17pt).
- Covers shown large, untinted, with gently rounded corners.
- Custom-painted radio pieces: the band selector, the tick dial with amber needle, the toggle switch.

## Colors

A near-monochrome warm graphite-and-ivory palette with one amber status light and one muted red for trouble.

### Primary
- **Dial Amber** (dark `dial-amber`, light `light-amber`): the light of the radio. Reserved for the active download's progress chunk, the dial needle while something is downloading, the filled dot of the selected band (Video / Música), the selected tool's dot in the tools list, the top-bar dot that says downloads are running, and the focus ring of the toggle switch. In light mode, amber text uses the deeper `light-amber-text` so status lines stay readable on paper.

### Secondary
- **Ember Red** (dark `ember-red` for fills, `ember-red-text` for text; light `light-ember-red`): failed progress bars and error copy in queue rows. Muted, never alarm-red.

### Neutral
- **Graphite** (`graphite` / `light-ground`): the window ground, and the fill of input fields (fields read as wells cut into the panel).
- **Graphite Panel** (`graphite-panel` / `light-panel`): panels, cards, menus, tooltips, dialogs.
- **Graphite Raised** (`graphite-raised` / `light-raised`): empty cover stages, thumbnails awaiting art, drop zones.
- **Hairline** (`hairline` / `light-hairline`): panel and tile borders, row separators, progress track.
- **Hairline Strong** (`hairline-strong` / `light-hairline-strong`): button and input borders, scrollbar handles, the toggle switch's off track, minor dial ticks.
- **Ivory** (`ivory` / `light-ink`): all primary text, the primary button fill, focus outlines, checked checkboxes, selected tab underlines.
- **Ash** (`ash` / `light-ash`): secondary text, hints, labels, inactive nav, major dial ticks and scale numerals, and the primary button's hover fill.
- **Smoke** (`smoke` / `light-smoke`): disabled text and the parked (idle) dial needle.
- **Console Black** (`console-black`, light `#f4f3ef`): the log console only.

Translucent ivory overlays (ivory at alpha 18/255 for hover, 30/255 for pressed and selected) are derived at build time rather than stored as tokens.

### Named Rules
**The One Light Rule.** Amber means "on air now". It appears only on something that is actively downloading or currently selected as the band or tool. If nothing is playing, the screen has no amber except the wordmark's interpunct. Never use amber for a button, a link, a hover, or a heading.

**The Wordmark Exception.** The interpunct in DVDY·STUDIO is painted amber permanently: the needle's mark on the faceplate. It is the only standing amber in the app and is not a precedent for any other element.

**The Untinted Cover Rule.** Cover art is shown as is: no overlays, no duotone, no colour wash. It is the only full colour on screen.

## Typography

**Body Font:** Archivo (variable, bundled, OFL), falling back to Segoe UI.
**Label Font:** Archivo Narrow (variable, bundled, OFL).

**Character:** A sober grotesque for reading paired with its condensed sibling for the faceplate printing; together they read as hardware labelling rather than web UI.

### Hierarchy
- **Title** (700, 17pt): page titles and the wordmark (the wordmark in Archivo Narrow, 1px tracking).
- **Body** (400, 10.5pt): default for every widget. Section titles, item titles, nav-active and buttons use 600 to 700 at the same size.
- **Small** (400, 9pt): hints, summaries, metadata lines, small buttons, console.
- **Label** (Archivo Narrow 600, 9pt, uppercase, 1px tracking): tile captions (CALIDAD, FORMATO), panel headings (EN EL DIAL), tab bars, table headers, the Simple / Avanzado switch labels.
- **Band** (Archivo Narrow 600 / 700 when selected, 10.5pt, uppercase, tracked): the VIDEO / MÚSICA band selector.

### Named Rules
**The Three Sizes Rule.** Every piece of text is 9pt, 10.5pt or 17pt. Hierarchy below the title comes from weight, colour (ivory vs ash) and the narrow uppercase label face, never from a new size.

**The Faceplate Rule.** Uppercase is only ever set in Archivo Narrow with tracking; Archivo itself is always sentence case.

## Layout

A fixed top bar (wordmark left, text nav, Simple / Avanzado switch right, hairline below) over a two-column body: the working panel on the left (flex 3) and the dial panel on the right (flex 2, 380 to 460px wide). Outer page margins are 28px horizontally and 22px vertically, with a 22px gap between columns. Panels pad 22 to 24px. Inside the download panel the order is fixed: link field with Pegar, band selector, a row of four option tiles, the cover stage centred in the remaining space, a hairline, then the summary line and the Descargar button anchored at the foot, then "Más opciones".

Spacing steps observed in the build: 4, 6, 10, 14, 16, 18, 22, 24 and 28px. Rows in the queue are 12px top and bottom with a hairline separator, cover-to-text gap 14px. Secondary pages use the shared page shell: 28px side margins, 22px above the title, 14px between blocks. The tools page uses a 260px grouped list beside the active tool.

## Elevation & Depth

The system is completely flat. There are no shadows. Depth is tonal: the ground is darkest, panels sit one step lighter, empty stages and thumbnails one step lighter still, and every container edge is a 1px hairline. Input fields reverse the step (ground colour inside a panel) so they read as recessed wells.

### Named Rules
**The No-Shadow Rule.** Separation comes from a tonal step plus a hairline. Never add a drop shadow, glow, or blur to a panel, menu, or button.

## Shapes

Gently rounded rectangles throughout, with radius growing with the size of the object: 2px on the 3px progress bar, 4px on checkboxes, 6px on small buttons, thumbnails and tooltips, 8px on buttons, inputs, menus and the cover stage, 9px on option tiles, 10px on the link field, primary button, tables and banners, 12px on panels. The toggle switch and radio indicators are full pills and circles; the band selector's dot is a 10px circle, ringed when off, filled amber when on. Selected nav and tab items drop their radius and take a straight 2px underline.

## Components

### Buttons
Quiet outlined controls with one ivory slab.
- **Shape:** gently rounded (8px; the primary 10px; small buttons 6px).
- **Primary (Descargar):** solid ivory fill, graphite text, bold, 11px 30px padding. One per screen, anchored at the foot of the working panel.
- **Hover / Focus:** primary hover shifts the fill to ash. Focus on the primary is a 2px inner ring in the ground colour; on other buttons the border turns ivory. Pressed adds a stronger ivory overlay.
- **Secondary:** transparent, 1px hairline-strong border, ivory text, weight 600, 7px 14px. Hover adds a faint ivory overlay.
- **Flat:** no border, ash text that brightens to ivory on hover ("Más opciones", inline links).
- **Small / Small primary:** the queue row actions (Pausar, Cancelar, Abrir); the primary variant is a small ivory slab.
- **Disabled:** smoke text on a hairline border (primary: hairline fill).

### Inputs / Fields
- **Style:** ground-colour fill, 1px hairline-strong border, 8px radius, 6px 10px padding. The link field is the large variant: 54px tall, 10px radius, 14px 16px padding.
- **Focus:** the border turns ivory. No glow.
- **Dropdowns:** a themed chevron SVG on the right that brightens on hover; popup lists are panel-coloured with an 8px radius and an ivory-overlay selection.
- **Disabled:** smoke text, hairline border.

### Option Tiles
Four bordered cells holding the essential options (Calidad, Formato, Carpeta, Subtítulos). Transparent fill, 1px hairline border at 9px radius, 8px 12px padding; a narrow uppercase label on top and a borderless control underneath in 600 weight. Hover strengthens the border. Focus inside a tile underlines the value instead of drawing a box.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** graphite panel.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px hairline.
- **Internal Padding:** 22 to 24px on the main panels; 14 to 16px on settings cards, which open with a narrow uppercase label.

### Navigation
Text-only top nav. Items are ash at 10.5pt with 7px 12px padding; hover brightens to ivory over a faint overlay; the active item is bold ivory with a straight 2px ivory underline. Keyboard focus is a 1px dashed ash outline. A 6px amber dot appears beside the nav while downloads are running, and the Descargar item carries the active count.

### Band Selector (signature)
The Video / Música choice, painted like the AM/FM band switch on a radio. Each band is a 10px circle and a narrow uppercase tracked label, 26px apart. Off: ash ring, ash label. Selected: filled amber dot, bold ivory label. Hover brightens the label; focus draws a thin ivory rounded outline.

### Dial Strip (signature)
The "EN EL DIAL" scale above the queue: a 54px strip with a hairline baseline, 41 ticks (majors every 10 in ash at 16px, mids every 5 at 10px, minors in hairline-strong at 6px) and the numerals 0 / 25 / 50 / 75 / 100 in the narrow label face. A 2px needle with a 3px knob marks the active download's progress in amber; while a download is preparing without a percentage the needle pulses (opacity 0.45 to 1, 50ms frame); with nothing active it parks at 0 in smoke.

### Queue Row
A 56px rounded cover (or a placeholder on graphite raised), a bold title, a small status line (ash; amber while retrying or active; ember red on error), a 3px progress bar (amber active, ash done or paused, ember red failed), small action buttons, and a remove control at the top right. Rows are separated by hairlines, not cards.

### Toggle Switch
44 by 24px pill. Off: hairline-strong track with an ivory knob. On: ivory track with a ground-colour knob. The track colour interpolates over 160ms with an in-out cubic ease. Focus adds a 1.5px amber ring. Used for the Simple / Avanzado switch with narrow uppercase labels either side (the active side bold ivory, the other ash).

### Checkboxes and Tabs
Checkboxes are 15px squares with a 4px radius and an ash border; checked fills ivory with a themed check SVG. Tabs are narrow uppercase labels in ash with a 2px underline that turns ivory when selected.

## Do's and Don'ts

### Do:
- **Do** keep amber for the thing that is downloading now, the selected band and the selected tool; check the screen with nothing downloading and confirm the only amber left is the wordmark's interpunct.
- **Do** use ivory for every interactive emphasis: the primary button, focus outlines, checked states, active nav and tab underlines.
- **Do** separate surfaces with a one-step tonal change and a 1px hairline.
- **Do** set every label, band name, tab, table header and dial numeral in Archivo Narrow, uppercase, tracked about 1px.
- **Do** stay within 9pt, 10.5pt and 17pt.
- **Do** show cover art large and untinted on graphite raised, rounded 8px (6px at thumbnail size).
- **Do** give the light rendition the same structure and rules, swapping only the values.

### Don't:
- **Don't** use amber on buttons, links, hovers, headings or decorative accents.
- **Don't** add drop shadows, glows or blurs.
- **Don't** introduce a second accent colour or tint cover art.
- **Don't** set Archivo (the reading face) in uppercase, or add a fourth text size.
- **Don't** turn the options into a sidebar of form fields; essential options sit in the four tiles, the rest behind "Más opciones".
