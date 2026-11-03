# Final Fantasy X & X-2 Text & Localization Studio (v2.0.0)

A comprehensive professional localization and text modding suite designed to view, decode, edit, audit, translate, and repack all text and dialogue binary tables from both **Final Fantasy X** and **Final Fantasy X-2 HD Remaster**.

[![Repository](https://img.shields.io/badge/GitHub-FFX__Text__Tool-blue?logo=github)](https://github.com/NfgOdin/FFX_Text_Tool)
[![Version](https://img.shields.io/badge/Version-2.0.0-emerald)](#release-changelog)

---

## Key Pillars & Features

- **Dual-Engine Game Support (FFX & FFX-2)**:
  - Seamlessly toggle between **Final Fantasy X** and **Final Fantasy X-2 HD Remaster** with 1 click.
  - Dynamic game-aware UI theme switching: **Sin Blue** (`#3b82f6`) for FFX vs **Celsius Purple** (`#a855f7`) for FFX-2.
  - Dedicated support for FFX-2 extended kernel tables (`acc.bin`, `accessory.bin`, `dress.bin`, `monmagic.bin`, etc.) and dressphere party equipment slots (Yuna Gunner, Rikku Thief, Paine Warrior, plus creature slots).
- **Interactive Choice Simulator & Live Preview**:
  - Real-time in-game dialogue simulator rendering line-by-line formatting, custom colors, and speaker nameplates.
  - **Interactive Choice Navigation**: Navigate multi-option dialogue prompts (`{CHOICE:XX}`) with keyboard $\uparrow/\downarrow$ arrow keys, simulated auto-indentation, and an animated blinking cursor.
- **Dynamic Translation Memory & Multilingual Canonical Lore Glossary**:
  - Over 137 verified canonical glossary terms indexed across 6 languages (English, Japanese, German, French, Italian, Spanish).
  - Proactive translation suggestion banner above the editor with `Ctrl+T` / 1-click auto-insertion.
  - Searchable Lore Glossary browser and Translation Dashboard.
- **QA Syntax & Crash Prevention Auditor**:
  - Deep-scanning syntax validator detecting unclosed brackets, invalid color codes, missing resets, line overflows ($>43$ chars per line), and 16-bit offset pool overflow risks.
  - **1-Click Safe Auto-Fix**: Automatically repair formatting errors across the current file, category, or entire localization with `.bak` safety backups.
  - **Cutscene VO Timing Estimator**: Calculates display duration, Characters Per Second (CPS), and Words Per Minute (WPM) based on `{TIME:XX}` engine delays to assist cutscene voice dubbing.
- **Reusable Batch Replacement Ruleset Manager**:
  - Create, save, load, and execute JSON regex/text replacement pipelines across single files, categories, or the entire localization tree.
- **1-Click Mod Packager (Spira Mod Manager & Nexus Mods)**:
  - Generate release-ready mod archives (`.zip`) with automatically structured `manifest.json` metadata compatible with Spira Mod Manager and Nexus Mods.
  - Dynamic game path routing (`ffx_ps2/ffx/master` vs `ffx_ps2/ffx2/master`).
- **Visual Side-by-Side Diff Viewer**:
  - Compare edited files directly against original or reference localizations with color-coded additions, deletions, and modifications.
- **Data Safety, Recent Files & Editing Polish**:
  - **Exit & Navigation Protection**: Prompts with `Yes / No / Cancel` on unsaved changes before switching rows, loading files, or exiting (`WM_DELETE_WINDOW`).
  - **Recent Files Menu**: Native `File -> Recent Files` dynamic cascade with universal category path resolution.
  - **Rich Context Menu**: Right-click editing menu (Cut, Copy, Paste, Delete, Select All, Lore TM, and control tag wrapping).
  - **Standalone Bundled Encodings**: Packaged with all official character encoding tables (`us`, `jp`, `ch`, `cn`, `kr`) for zero external dependencies.

---

## Release Changelog

### v2.0.0 (The Studio Edition)
- **Full Dual-Engine Support (FFX & FFX-2)**:
  - Complete support for Final Fantasy X and Final Fantasy X-2 HD Remaster text assets.
  - Adaptive visual themes: *Sin Blue* for FFX and *Celsius Purple* for FFX-2.
  - Added FFX-2 tables (`acc.bin`, `accessory.bin`, `dress.bin`, `monmagic.bin`, etc.) and party equipment mappings.
- **Interactive Choice Simulator**:
  - Live interactive choice box simulator with animated blinking cursor, keyboard navigation ($\uparrow/\downarrow$), and accurate in-game line indentation.
- **Translation Memory & Canonical Lore Glossary**:
  - Proactive Lore TM suggestion engine with `Ctrl+T` insertion.
  - 137 verified canonical terms across English, Japanese, German, French, Italian, and Spanish.
- **QA Syntax & Crash Prevention Auditor**:
  - Complete error detection for unclosed control tags, invalid color codes, and line overflows ($>43$ chars).
  - 1-click batch safe auto-fix for active memory and disk files with automatic `.bak` backups.
  - Cutscene Voice-Over (VO) timing and speech-rate estimator (CPS / WPM).
- **Reusable Batch Replacement Ruleset Manager**:
  - Save, load, and run persistent JSON replacement pipelines across files and localizations.
- **1-Click Mod Packager**:
  - Export structured `.zip` mod packages with Spira Mod Manager `manifest.json` and Nexus Mods compatibility.
- **Visual Side-by-Side Diff Dialog**:
  - Interactive comparison tool with color-coded diffs, filter by changes, and `Alt+Left` / `Alt+Right` entry navigation.
- **Desktop Polish & Data Safety**:
  - `WM_DELETE_WINDOW` unsaved-changes protection on exit, file switch, and row navigation.
  - Native `File -> Recent Files` menu cascade with multi-category path resolution.
  - Right-click context menus with tag wrapping and Lore TM insertion across all text widgets.
  - Bundled character encoding tables into standalone PyInstaller executable.

### v1.2.0 (The Ultimate Text & Dialogue Update)
- **Modern Sleek Slate Dark Theme & Modernized UI**:
  - Restyled entire interface with a modern `#0e1117` / `#161922` / `#1f2432` slate palette, elevated cards, and polished interactive hover states.
  - Alternating zebra-striped rows in the entry treeview for improved readability.
  - Search bar now features an instant match counter badge (e.g. `12 of 1578 matches`) and a 1-click `✕` clear button (`Esc` shortcut).
- **Multi-Line Dialogue Editor with Syntax Highlighting**:
  - Replaced cramped single-line fields with an expansive multi-line text editor featuring full word wrap, line breaks, and keyboard shortcuts (`Ctrl+Enter` to apply edits).
  - Dynamic syntax tag color coding: speakers (cyan), text colors (yellow), flow/pauses (green), choices (orange), and game variables (pink).
- **Interactive Syntax Tag Hover Tooltips**:
  - Hovering your mouse over any control tag (`{PC:00}`, `{MCR:s06l63}`, `{CLR:YELLOW}`, `{PAUSE}`, `{TIME:1E}`, `{CHOICE:00}`, etc.) displays an immediate floating tooltip explaining what the tag means, which character/speaker it represents, or how it functions in-game.
- **Quick-Insert Tag Toolbar**:
  - 1-click toolbar buttons directly above the dialogue editor for fast editing: `🟡 Color ▼`, `👤 Speaker ▼`, `⏸️ Pause`, `⏱️ Time`, `🔘 Choice`, and `↩️ \n`.
- **Live In-Game Dialogue Box Preview**:
  - Real-time simulated FFX dialogue box showing how text appears in-game.
  - Automatically parses line 1 speaker tags (`{PC:XX}` or `{MCR:sXXlYY}`) into dedicated speaker nameplate headers (`[ TIDUS ]`, `[ YUNA ]`, `[ SEYMOUR ]`, etc.) and renders inline text colors (`{CLR:YELLOW}`, `{CLR:RED}`, etc.) live as you type.
- **Universal Text Support Across All Game Assets**:
  - **Monster Arena & Help Tutorials (`.sps2`)**: Added full support for Screen Presentation Script tables (`help/**/*.sps2`), enabling complete editing and translation of `mon_boku.sps2` (Monster Arena boss names, capture requirements, trainer lines) and tutorial scripts.
  - **Story Cutscenes & Dialogue (`event/obj_ps3`)**: Added full support for all 636 localized story cutscene and NPC interaction files across Spira.
  - **In-Battle Voice & Dialogue (`battle/btl`)**: Added full support for all 164 battle tactical dialogue and victory quote tables.
  - **Menu & System Text (`menu`, `cloudsave`)**: Added support for menu tutorials (`menumain.bin`), cloud save dialogues (`cloud.bin`, `cloudv.bin`), and the Al Bhed Primer letter substitution dictionary (`albheddic.bin`).
  - **Equipment & Party Support (`w_name.bin`, `ply_save.bin`, `ply_rom.bin`, `sphere.bin`)**:
    - Full support for `w_name.bin` (covering equipment/armor across all 7 playable characters: Tidus, Yuna, Auron, Kimahri, Wakka, Lulu, Rikku) with specialized suffix/tail pointer preservation.
    - Added support for `ply_save.bin` (default character names and base party configurations).
    - Added support for `ply_rom.bin` (character biography descriptions and switch/summon battle cues) and `sphere.bin` (Sphere Grid node descriptions).
- **Al Bhed Cipher Dictionary (`menu/albheddic.bin`)**:
  - Full decoding, editing, and repacking of the 60-entry letter substitution cipher table used for Al Bhed Primer translations (A-Z and a-z letter-by-letter and primer-by-primer).
- **Universal Pointer Table Compatibility**:
  - Enhanced message file parser to cleanly handle high-word UI flags and choice counts in pointers (e.g., Blitzball tutorials `bltz0000.bin`, cloud saves `cloudv.bin`, and zero-length dummy tables). Verified across all 4,177 localized files with 100% pass rate.
- **Single-Row CSV Placeholder (`{\n}`)**:
  - Export and import automatically encode line feeds as `{\n}` so each entry remains strictly on a single row, optimizing spreadsheet and Power Query/Excel workflows without multiline splits.
- **Built-In Control Tags Cheat Sheet**:
  - Added an interactive "📖 Tags Cheat Sheet" popup window accessible directly from the Dialogue Editor tab and the bottom footer.
  - Complete in-app and README reference guide explaining line breaks, colors, pauses, frame delays, character lookups (`{PC:XX}`), macro speaker nameplates (`{MCR:sXXlYY}`), variables, and choice options.
- **Data Category Switcher & Multi-Scope Search/Replace**:
  - Added category dropdown to switch smoothly between Kernel Tables, Monster Arena & Help, Story Cutscenes, Battle Quotes, and System Menus.
  - Search & Replace now supports Current File, Current Category, and All Files in Localization.
- **Macro & Engine Bytecode Fixes**:
  - Fixed `{MCR:sXXlYY}` macro decoding and parsing: preserves raw hex bytes without negative offset errors. Added full support for choices, pixel spacing, and timed delays.

### v1.1.0
- **Added Monster Support**: Added full support for `monster1.bin`, `monster2.bin`, and `monster3.bin` (covering enemy names, Sensor tips, and full Scan text boxes across all 365 enemy entries).
- **Search & Display Enhancements**: Improved treeview search and list previews to display Sensor/Scan information cleanly for monster tables.
- **Repack & Stability Improvements**: Tested round-trip repacking across all localized monster files.

### v1.0.0
- Initial public release supporting abilities, items, menus, commands, and key item tables with full FFX charset encoding/decoding and CSV batch tools.

---

## In-Game Control Tags Cheat Sheet

FFX text files use special inline control codes enclosed in curly brackets `{...}` to represent formatting, speaker nameplates, variables, pauses, and colors. These tags can be edited freely or preserved in dialogue:

### 1. Formatting & Flow Control
| Tag | Name | Description | Example |
| :--- | :--- | :--- | :--- |
| `\n` or `{\n}` | **Line Break** | Advances dialogue to the next line in the text box. In CSV exports, formatted as `{\n}` to maintain single-row integrity. | `Welcome!\nHow can I help you?` |
| `{PAUSE}` | **Player Input Pause** | Halts text display until the player presses confirm or voice acting finishes. | `Wait...{PAUSE}\nDid you hear that?` |
| `{SPACE:XX}` | **Pixel Spacing** | Adds horizontal spacing in pixels (`XX` = hex 00–FF). Used for indenting or table columns. | `{SPACE:0A}Option A` |
| `{TIME:XX}` | **Timed Delay** | Delays subsequent text by `XX` frames to sync lines with gestures and animations. | `{TIME:1E}Now!` |

### 2. Text Colors (`{CLR:...}`)
| Tag | Hex Code | Purpose & Appearance | Example |
| :--- | :--- | :--- | :--- |
| `{CLR:WHITE}` | `0x41` | Default standard text color. | `{CLR:WHITE}Normal text` |
| `{CLR:YELLOW}` | `0x43` | Highlighted keywords, locations, item names, and battle terms. | `{CLR:YELLOW}Overdrive{CLR:WHITE}` |
| `{CLR:GREY}` | `0x52` | Subdued, inactive, or disabled text/choices. | `{CLR:GREY}(Unavailable)` |
| `{CLR:BLUE}` | `0x88` | Beneficial status effects, positive buffs, and defensive stats. | `{CLR:BLUE}Haste{CLR:WHITE}` |
| `{CLR:RED}` | `0x94` | Debuffs, warnings, boss attacks, and danger status. | `{CLR:RED}Doom{CLR:WHITE}` |
| `{CLR:PINK}` | `0x97` | Special emphasis or unique cues. | `{CLR:PINK}Special{CLR:WHITE}` |
| `{CLR:OL_PURPLE}` | `0xA1` | Outlined purple title text. | `{CLR:OL_PURPLE}Notice` |
| `{CLR:OL_CYAN}` | `0xB1` | Outlined cyan header text. | `{CLR:OL_CYAN}Info` |

### 3. Speakers, Characters & Variables
| Tag | Description | Notes / Values | Example |
| :--- | :--- | :--- | :--- |
| `{PC:XX}` | **Playable Character Name** | `00`=Tidus, `01`=Yuna, `02`=Auron, `03`=Kimahri, `04`=Wakka, `05`=Lulu, `06`=Rikku, `07`=Seymour. Placing this on line 1 of a cutscene dialogue box sets the speaker nameplate. | `{PC:00}\nI am with you!` |
| `{MCR:sXXlYY}` | **Macro String Lookup** | Fetches dynamic strings from engine Section `XX`, Line `YY`. Used for NPC speaker nameplates and consistent location/character names across localizations. | `{MCR:s06l63}\nThat is enough, {MCR:s06l40}.` |
| `{VAR:XX}` | **Dynamic Number** | Live in-game numbers (Gil balance, timer, countdown seconds, score). | `Obtained: {VAR:01} Gil` |
| `{KEY:XX}` | **Key Item Name** | Dynamically looks up and displays the Key Item name for inventory index `XX`. | `Received {KEY:04}!` |

### 4. Interactive Choices & Menus
| Tag | Name | Description | Example |
| :--- | :--- | :--- | :--- |
| `{CHOICE:XX}` | **Choice Option** | Marks a selectable dialogue choice (`00`=First, `01`=Second, etc.). | `{CHOICE:00} Yes\n{CHOICE:01} No{CHOICE-END}` |
| `{CHOICE-END}` | **End Choice Box** | Closes the selectable choice prompt. | `{CHOICE:00} Fight\n{CHOICE:01} Flee{CHOICE-END}` |

---

## Getting Started

### Prerequisites

- **Python 3.8 or higher**
- **Tkinter** (usually included with standard Python installations)

### Running the Application

Simply execute the main script using python:

```bash
python FFX_Text_Tool.py
```

### Packaging into a Executable

You can compile the tool into a standalone Windows executable using PyInstaller with the provided `.spec` configuration:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build the executable:
   ```bash
   pyinstaller FFX_Text_Tool.spec
   ```
3. Find your built executable in the `dist` folder.

---

## Contributing & Repository

For updates, issues, and contributions, visit the repository:
[https://github.com/NfgOdin/FFX_Text_Tool](https://github.com/NfgOdin/FFX_Text_Tool)

Developed by **NfgOdin** (Copyright © 2026).
All rights reserved.
