<div align="center">

# 📷 instant-film-agent

### Authentic Instant Film Frame & Emulation Engine for AI Agents and CLI

[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg?style=flat-square)](pyproject.toml)
[![Python](https://img.shields.io/badge/python->=3.10-blue.svg?style=flat-square)](pyproject.toml)
[![Engine](https://img.shields.io/badge/engine-NumPy%20%2B%20Pillow%20(Pure)-success.svg?style=flat-square)](src/instant_film_agent/engine/)
[![Latency](https://img.shields.io/badge/latency-~200ms%20(CPU)-brightgreen.svg?style=flat-square)](tests/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Fonts](https://img.shields.io/badge/fonts-OFL%20%2F%20Free-blueviolet.svg?style=flat-square)](src/instant_film_agent/engine/fonts/LICENSE-OFL.txt)

<br />

**[🇺🇸 English](README.md)** | **[🇯🇵 日本語 (Japanese)](README_JA.md)**

<br />

[Why instant-film-agent?](#why-instant-film-agent) • [Key Features](#key-features) • [Preset Gallery](#preset-gallery) • [Agent Integration](#agent-integration-guide) • [CLI Reference](#cli-reference) • [FAQ](#faq)

<br />

*"Not just another flat white border. Millimeter-accurate physical proportions of real-world Polaroid and instax formats, 0-100 optical/chemical film emulation, and authentic margin handwriting physics."*

</div>

---

## 💡 Why instant-film-agent?

When adding an instant film aesthetic to photographs, conventional tools merely slap a generic white rectangle over an image and stamp computer text onto the bottom margin.

Authentic instant photographs (such as Polaroid and instax) embody a distinct physical geometry, chemical behavior, and tactile handwriting:

1. **Millimeter-Accurate Physical Geometry (Reality & Simulacrum)**:
   - **instax mini**: 46×62 mm photo window (≈3:4) set inside a 54×86 mm outer card (credit card golden ratio).
   - **Polaroid 600 / SX-70**: 79×79 mm square window (1:1) within an 88.5×107.5 mm card.
   - **instax WIDE**: 99×62 mm window (≈16:10) within a 108×86 mm card.
   - The iconic proportion—slender borders on three sides and a thick bottom margin housing the chemical reagent pods—provides instantaneous visual recognition.
2. **0–100 Optical & Chemical Emulation Slider**:
   - `0` (Completely non-destructive): Maintains 100% of the input image pixels; only compounds the die-cut frame and handwriting.
   - `1–100` (Continuous chemical development): Adds faded black lifts, highlight roll-off, subtle lens chromatic aberration, roller chemical development streaks, and luminance-weighted dye cloud grain.
3. **Margin Handwriting & Ink Physics**:
   - Emulates oil-based permanent marker bleed, ballpoint pen scratch, glitter pen metallic reflections, and opaque paint pen textures across 20 included open fonts.

### 📊 Comparison with Conventional Approaches

| Aspect | Primitive Borders | General Nodes / Plugins | `instant-film-agent` |
|---|---|---|---|
| **Outer Card Geometry** | Rough approximation | Single square crop | **Millimeter-accurate physical proportions (mini / 600 / SX-70 / WIDE)** |
| **Emulation Strength** | None (Raw image) | Fixed LUT / Filter | **Continuous 0–100 slider (0=zero pixel distortion, 100=rich chemistry)** |
| **Film Tones** | Fixed styles | Manual RGB curves | **Format-linked Smart Defaults + Independent Tones (instax Clear, 70s Amber, 90s Cyan, B&W, etc.)** |
| **Margin Typography** | System default fonts | Monospaced Latin only | **20 Open Handwriting Fonts + Real Ink Physics (Marker bleed, Glitter, Paint)** |
| **EXIF Integration** | Manual entry | System clock only | **Automatic extraction of photo capture timestamp (`DateTimeOriginal`)** |
| **Mask Output** | None | Simple photo crop | **Dual alpha masks for Photo Window (`window_mask`) and Outer Card (`card_mask`)** |
| **Dependencies** | Pillow only | PyTorch / GPU / ComfyUI required | **Pure NumPy + Pillow (No GPU, runs on standard CPU in milliseconds)** |
| **AI Agent Readiness** | Manual UI only | Graph wiring required | **Structured JSON output, machine-readable capabilities catalog, self-diagnostics (`doctor`)** |

---

## 🌟 Key Features

- 📐 **3 Authentic Instant Film Standards**  
  Specifically tailored for modern portrait generations (SDXL / Flux): `Portrait (Vertical)` (instax mini), `Square (Polaroid)` (Polaroid 600 / SX-70), and `Landscape (Wide)` (instax WIDE).
- 🔄 **Adaptive Fit Modes (`Auto Aspect` & `Keep Aspect`)**  
  `Auto Aspect` automatically chooses the optimal film format based on the image's aspect ratio. `Keep Aspect` preserves 100% of the original framing without cropping.
- 🧪 **0 to 100 Continuous Chemical Emulation**  
  From completely neutral (`0`) to rich vintage chemistry (`100`), seamlessly adjust roller development artifacts, organic vignette, and luminance grain.
- 📷 **Automatic EXIF Photo Capture Date Extraction (`--date photo`)**  
  Reads `DateTimeOriginal` from EXIF tags and renders an authentic handwritten date in the margin.
- ✒️ **20 Bundled Handwriting Fonts & Ink Physics**  
  Features casual diary pens, cute round scripts, elegant fountain pens, and bold permanent markers with baseline jitter and visual size normalization.
- 🎭 **Simultaneous Alpha Mask Export (`--save-masks`)**  
  Outputs both window cutouts and outer card masks for downstream image processing workflows.
- ⚡ **Lightweight & High-Performance**  
  Built strictly on pure NumPy and Pillow. Operates in milliseconds on standard CPU without requiring PyTorch, CUDA, or ComfyUI.

---

## 🎨 Preset Gallery

| Preset (`--preset`) | Aliases | Format | Film Tone | Best Suited For |
|---|---|---|---|---|
| **`instax-mini`** *(Default)* | `cheki`, `mini` | Portrait (46×62mm) | Modern Clear (High-key) | Clean skin tones, modern instant portrait, casual diary pen |
| **`polaroid-600`** | `polaroid`, `600` | Square (79×79mm) | Cool Cyan (90s Snap) | 90s cyan black lift, square framing, bold memo script |
| **`polaroid-sx70`** | `sx70`, `70s` | Square (79×79mm) | Warm Amber (70s Vintage) | 70s amber highlights, ivory card, elegant fountain pen |
| **`instax-wide`** | `wide` | Landscape (99×62mm) | Cool Cyan (90s Snap) | Panoramas, group travel photos, blue ballpoint gel ink |
| **`pastel-dream`** | `pastel`, `kawaii` | Portrait | Pastel Muted (Soft Dream) | Dreamy white fade, cute round script, silver glitter ink |
| **`vivid-summer`** | `summer`, `vivid` | Square | Vivid Pop (Summer Punch) | Saturated punchy colors, festival snapshot, red marker |
| **`classic-monochrome`** | `bw`, `monochrome` | Square | Classic B&W (Silver Halide) | Warm-black monochrome gradation, brush calligraphy |
| **`cinematic-night`** | `cinematic` | Landscape | Cinematic Teal (Moody Film) | Matte black frame card, teal shadows, white opaque paint pen |
| **`aged-nostalgia`** | `vintage` | Square | Warm Amber (Aged Vintage) | Aged yellowed paper texture, antique fountain pen ink |
| **`auto-smart`** | `auto` | Auto Aspect | Linked Smart Default | Fully automatic format and tone adaptation |
| **`keep-aspect-clean`** | - | Portrait | Linked Smart Default | 100% no-crop preservation of original image framing |

---

## 🛠️ CLI Reference

### Basic Usage
```bash
# Simplest invocation (Default instax mini portrait)
instant-film-agent apply input.jpg --json

# Custom preset with caption and EXIF date extraction
instant-film-agent apply photo.jpg -p polaroid-600 -c "Summer Memories" -d photo --json

# Save window and card masks as PNG
instant-film-agent apply input.jpg -o out.jpg --save-masks --json

# Zero-distortion mode (No color grading, frame & text only)
instant-film-agent apply input.jpg --emulation 0 --json

# Batch directory processing
instant-film-agent batch ./photos -o ./instant_out -p instax-mini --json
```

### Diagnostics & Management
```bash
# Check runtime integrity and bundled fonts
instant-film-agent doctor --json

# Inspect available capabilities and options in JSON
instant-film-agent capabilities --json

# List available presets
instant-film-agent presets list --json

# Inspect preset details
instant-film-agent presets show polaroid-sx70 --json

# Set default favorite preset
instant-film-agent favorite polaroid-600 --json
```

---

## 🤖 Agent Integration Guide

Designed natively for AI coding and task agents (Antigravity, Gemini, Claude, etc.):

```bash
# 1. Install package in editable mode
pip install -e .

# 2. Verify self-diagnostics
instant-film-agent doctor --json

# 3. Deploy agent skill definition — pick the target by keyword
#    Muse:  ~/workspace/custom-skills/instant-film-agent
#    Gemini CLI / Antigravity: ~/.gemini/config/skills/instant-film-agent (default)
#    An explicit path also works, as does $INSTANT_FILM_SKILL_DEST.
powershell -ExecutionPolicy Bypass -File scripts/install_skill.ps1 muse
# (On Linux / macOS: bash scripts/install_skill.sh muse)
```

---

## 📄 License

- Code: [MIT License](LICENSE)
- Fonts: [SIL Open Font License 1.1 / Free License](src/instant_film_agent/engine/fonts/LICENSE-OFL.txt) (Self-contained and commercially usable)
- Upstream: Based on [`InstantFilmFrame`](https://github.com/treeturtlefall-arch/InstantFilmFrame)
