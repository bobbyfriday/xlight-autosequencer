# x-onset Quick Start Tutorial

A step-by-step walkthrough of the web UI — from uploading your first song to generating an xLights sequence file.

---

## Prerequisites

Before you begin, make sure you have:

- Python 3.11+ with dependencies installed (`pip install vamp librosa madmom click demucs flask mutagen questionary rich`)
- ffmpeg installed (`brew install ffmpeg` on macOS)
- Vamp plugin packs from [vamp-plugins.org](https://www.vamp-plugins.org/)
- An MP3 file to work with
- An xLights layout file (`.xlights_rgbeffects.xml`) for your display

---

## 1. Launch the Dashboard

Start the web UI from your terminal:

```bash
xlight-analyze review
```

Your browser opens to `http://localhost:5173` — the **x-onset** dashboard. The top navbar has three main pages:

| Nav Link | What It Does |
|----------|-------------|
| **Song Library** | Upload, analyze, and manage songs |
| **Theme Editor** | Browse and customize visual themes |
| **Layout Grouping** | Organize your xLights props into power groups |

If this is your first time, you'll see an empty state with an **Upload Your First Song** button.

> ![Screenshot placeholder: The x-onset dashboard showing the dark-themed navbar with "x-onset" branding and three nav links (Song Library, Theme Editor, Layout Grouping). Below is the empty state with a music note icon, "No songs analyzed yet" heading, and a blue "Upload Your First Song" button.](screenshots/01-dashboard-empty.png)

---

## 2. Upload and Analyze a Song

Click **+ Upload & Analyze New Song** to expand the upload panel.

### Drop Your File

Drag your MP3 onto the drop zone, or click **browse files** to select one. The filename appears below the drop zone once loaded.

### Choose Analysis Options

Below the drop zone you'll see checkboxes for each analysis module:

| Option | What It Does | Recommended |
|--------|-------------|-------------|
| **Vamp plugins** | Beat, onset, pitch, chord, and structure detection | Yes |
| **madmom** | Neural network beat/downbeat tracking | Yes |
| **Stem separation** | Splits audio into drums, bass, vocals, guitar, piano, other | Yes |
| **Phonemes** | Extracts word timing from vocals (needs lyrics) | Optional |
| **Song structure** | Detects verse/chorus/bridge/intro/outro boundaries | Yes |
| **Build story** | Automatically creates a song story interpretation | Yes |

> ![Screenshot placeholder: The upload panel expanded, showing a drop zone with an MP3 filename displayed, six checkboxes (Vamp, madmom, Stems, Phonemes, Structure, Story), and a blue "Analyze" button.](screenshots/02-upload-panel.png)

### Watch the Progress

Click **Analyze**. A progress panel replaces the upload area, showing:

- A progress bar filling as each step completes
- A step list with checkmarks for finished steps and a spinner for the current step
- If you enabled Phonemes, a prompt may appear asking for artist/title for Genius lyric lookup — fill it in or click **Skip**

> ![Screenshot placeholder: The progress section showing a bar at about 65%, with completed steps (Loading audio, Stem separation, Vamp beats) and the current step (madmom beats) with a spinner.](screenshots/03-analysis-progress.png)

### View the Result

When analysis finishes, the progress panel shows **"Analysis complete!"** with a **View Result** button. Click it — if you had "Build story" checked, you'll land on the **Story Review** page. Otherwise you'll go to the **Timeline**.

The song also appears in the **Song Library** table below with its title, artist, BPM, duration, and quality score.

---

## 3. Explore the Song Library

The library table shows all your analyzed songs. Each row displays metadata pulled from the MP3's ID3 tags plus analysis results.

### Song Detail Panel

Click any row to expand a **detail panel** below it with:

- **Quality Score** — a visual bar showing overall analysis quality
- **Details** — duration, BPM, key, stem status, structure info
- **Action buttons:**

| Button | Where It Goes |
|--------|--------------|
| **Review Timeline** | Raw timing track visualization |
| **Story Review** | Section structure editor with theme assignment |
| **Phonemes** | Lyric/word timing editor (if phoneme data exists) |
| **Re-analyze** | Opens the upload panel to re-run analysis |
| **Delete** | Removes the song from the library |

> ![Screenshot placeholder: The song library table with one row expanded showing the detail panel. The quality score bar is at 78%, details show "3:42 · 128 BPM · E minor", and five action buttons are visible.](screenshots/04-song-detail.png)

---

## 4. Review the Timeline

Click **Review Timeline** from the detail panel.

The **Timeline** page shows every detected timing track laid out against the audio:

- **Left panel** — track list showing each algorithm's output (beats, onsets, drums, bass, vocal onsets, etc.) with quality scores and stem badges
- **Canvas** — horizontal timeline with colored marks for every detected event
- **Toolbar** — Play/Pause, Prev/Next navigation, zoom controls, focus mode

### Key Interactions

| Action | How |
|--------|-----|
| Focus a single track | Click its name in the left panel |
| Jump between marks | **Prev** / **Next** buttons (navigates the focused track) |
| Zoom in/out | **+** / **-** buttons, or Ctrl+scroll |
| Clear focus | **Clear Focus** button |
| Play with audio | **Play** button (audio syncs to the playhead) |

This page is for inspecting the raw analysis quality. Once you're satisfied, go back to the library and open **Story Review** to work with the musical structure.

> ![Screenshot placeholder: The Timeline page showing about 15 colored timing tracks (beats, onsets, drums energy, bass energy, vocal onsets, chord changes, etc.) overlaid as horizontal rows of dots and lines on a dark background. The left panel shows track names with quality scores. A playhead line marks the current position.](screenshots/05-timeline.png)

---

## 5. Edit the Song Story

Click **Story Review** from the library detail panel (or click **View Result** right after analysis).

This is the core editing page where you shape the song's structure before generating a light show.

### The Timeline

The main area shows a horizontal bar chart of **sections** — each block represents a section like "intro", "verse_1", "chorus_1", "bridge", etc. Blocks are color-coded by role.

Below the section bars, **stem accent tracks** show musical intensity as dot patterns for drums, bass, and vocals — these help you see where the energy is.

### Playback

Use the toolbar to play the song synced to the timeline:
- **Play** button starts/pauses
- Time display shows current position
- The playhead moves across the timeline as the song plays
- **Zoom** in/out with the +/- buttons or Ctrl+scroll, **Fit** resets zoom

### The Flyout Panel

Click any section block to open a **flyout panel** on the right with three tabs:

#### Details Tab
Shows the section's time range, role, energy profile, and character tags. Edit actions include:

| Action | What It Does |
|--------|-------------|
| **Reprofile** | Change the section's role (e.g. verse → bridge) |
| **Split** | Split a section into two at a time point |
| **Merge** | Combine with an adjacent section |
| **Boundary adjust** | Drag section edges to change start/end times |

> ![Screenshot placeholder: The Story Review page with a timeline of colored section blocks (intro, verse_1, chorus_1, verse_2, chorus_2, bridge, chorus_3, outro). The flyout panel is open on the right showing the Details tab for "chorus_1" with its time range, energy info, and Reprofile/Split/Merge buttons.](screenshots/06-story-details-tab.png)

#### Moments Tab
Shows key musical moments detected within the selected section — impacts, builds, drops, and transitions. Each moment has a rank and intensity score.

#### Themes Tab
This is where you assign visual themes to sections. See **Step 7** for the full walkthrough.

### The Preferences Panel

Click the **⚙ Prefs** button in the toolbar to open song-level preferences:

| Setting | What It Controls |
|---------|-----------------|
| **Mood** | Overall mood filter for theme selection (ethereal, aggressive, dark, structural, or auto) |
| **Occasion** | christmas, halloween, or general — filters themes to match |
| **Focus stem** | Which instrument stem to prioritize |
| **Intensity** | Slider from 0 to 2 controlling effect density and brightness |
| **Theme lock** | Force a specific theme for the entire song (overrides per-section) |

Click **Apply preferences** to save. A pencil icon (✎) next to the theme lock field opens that theme directly in the Theme Editor.

> ![Screenshot placeholder: The Preferences panel showing dropdown selectors for Mood (set to "aggressive"), Occasion (set to "christmas"), Focus stem (set to "auto"), an Intensity slider at 1.25, a Theme lock text field, and an "Apply preferences" button.](screenshots/07-story-preferences.png)

### Save and Export

- **Save** — saves your edits as a `_story_reviewed.json` file (preserves your work for future sessions)
- **Export** — exports the finalized story, ready for sequence generation

---

## 6. Set Up Layout Groups

Navigate to **Layout Grouping** in the navbar.

This page organizes your xLights props into 8 tiers of **power groups**. The generator uses these tiers to decide which props get which effects — background washes go to tier 1, beat-synced chases to tier 4, hero spotlights to tier 8, and so on.

### Load Your Layout

Launch with your layout file from the terminal:

```bash
xlight-analyze grouper-edit your_layout.xlights_rgbeffects
```

The page shows your props organized across 8 tier tabs:

| Tier | Tab Name | Purpose |
|------|----------|---------|
| 1 | **Canvas** | Whole-display background wash |
| 2 | **Spatial** | Geographic zones (left, right, top, bottom) |
| 3 | **Architecture** | Structural groupings (roofline, arches, windows) |
| 4 | **Rhythm** | Beat-synced chase sequences |
| 5 | **Fidelity** | High-resolution detail props |
| 6 | **Prop Type** | Grouped by kind (all mini-trees, all candy canes) |
| 7 | **Compound** | Multi-prop coordinated effects |
| 8 | **Heroes** | Spotlight props for dramatic moments |

### Organize Props

- Click a **tier tab** to switch tiers
- **Drag props** from the "Ungrouped" section at the bottom into named groups
- Click **+ New Group** to create a group — name it with the tier convention (e.g. `01_BASE_Roof`)
- Reorder props by dragging within groups

### Save and Export

- **Save** — persists your groupings
- **Reset to Original** — reverts all changes
- **Export** — writes the power group layout for the generator

> ![Screenshot placeholder: The Layout Group Editor showing the "Canvas" tier tab selected. Two groups are visible: "01_BASE_Roof" with 4 props listed inside, and "01_BASE_Outline" with 6 props. Below is the "Ungrouped" section with remaining props. The header shows Save, Reset, and Export buttons.](screenshots/08-layout-grouper.png)

---

## 7. Assign Themes to Sections

Go back to **Story Review** (click a song in the library → **Story Review**). Click a section, then open the **Themes** tab in the flyout panel.

### Theme Recommendations

The Themes tab shows two sections:

1. **Recommended** — themes automatically scored based on the section's energy, mood, and occasion settings. Each card shows a reason like "matches christmas occasion" or "aggressive mood, fits high energy".

2. **All Themes** — the full list, filterable by mood and occasion dropdowns at the top.

### Theme Cards

Each theme card displays:
- **Theme name** and mood tag
- **Palette strip** — the theme's color scheme as colored dots
- **Intent** — a short description of the visual feel
- An **Assign** button

> ![Screenshot placeholder: The Themes tab in the flyout panel. At top are two filter dropdowns (mood, occasion). Below is a "Recommended" section with 3 theme cards showing palette dots and "Assign" buttons. One card ("Midnight Frost") shows "ethereal mood — cool blue shimmer wash". Below that is "All Themes" with more cards.](screenshots/09-themes-tab.png)

### Assigning a Theme

- Click **Assign** on any theme card to assign it to the selected section
- The section block on the timeline updates to show a **palette strip** at its bottom edge
- You can also **drag** a theme card and drop it onto a section block
- To remove an assignment, the "Assigned" label at the top of the tab shows the current theme with a **Remove** button
- Click **Apply recommended to unassigned** at the bottom to auto-assign the top recommendation to every section that doesn't have a theme yet

### Per-Section vs Global

You can assign themes individually per section, or use the **⚙ Prefs** panel's **Theme lock** field to force one theme for the whole song. Per-section assignments override the global lock.

---

## 8. Browse and Customize Themes

Navigate to **Theme Editor** in the navbar for deeper theme editing.

### Left Panel — Theme List

- **Search bar** — type to filter by name
- **Filter dropdowns** — mood, occasion, genre
- **Clear filters** — resets all filters
- Theme cards show name, mood, and palette preview

### Right Panel — Theme Detail

Click a theme to see its full definition:

- **Metadata** — name, mood, occasion, genre, intent
- **Palette** — primary and accent colors
- **Layers** — the effect stack from bottom (background) to top (foreground)

Each layer shows:
- **Effect dropdown** — the xLights effect (Color Wash, Twinkle, Meteors, etc.)
- **Blend mode dropdown** — how this layer composites (Normal, Additive, Layered, etc.)
- **Parameter overrides** — specific knob values for this effect
- **Reorder/Remove** buttons — drag to reorder, × to delete a layer

> ![Screenshot placeholder: The Theme Editor with the left panel showing a filtered list of themes. The right panel shows "Midnight Frost" selected, with palette swatches, metadata fields, and a layer editor showing 3 layers: Color Wash (Normal), Twinkle (Additive), and Meteors (Layered). Each layer has an effect dropdown and blend mode dropdown.](screenshots/10-theme-editor.png)

### Creating a Custom Theme

1. Click **+ New Theme** in the toolbar
2. Fill in name, mood, occasion, genre, intent
3. Set your palette colors
4. Add layers — pick effects from the dropdown, choose blend modes
5. Adjust parameter overrides per layer
6. Click **Save**

Custom themes are stored in `~/.xlight/custom_themes/` and appear alongside the 21 built-in themes everywhere in the app.

---

## 9. Work with Effect Variants

Effect **variants** are named parameter presets for effects. Think of them as "flavors" — the Twinkle effect might have a `twinkle_gentle_shimmer` variant (slow, subtle) and a `twinkle_rapid_sparkle` variant (fast, energetic).

### Browse Variants

Open the variant browser at `http://localhost:5173/variants`.

The page shows all available variants with filtering:

| Filter | Options |
|--------|---------|
| **Effect** | Filter by base effect name |
| **Energy** | low, medium, high |
| **Tier** | background, mid, foreground, hero |
| **Scope** | single-prop, group |

Each variant card shows:
- Name and base effect
- Parameter overrides (the specific knob values)
- Tags (energy, tier affinity, section roles)
- Whether it's built-in or custom

> ![Screenshot placeholder: The variant browser page showing a filtered list of variants. Each card shows the variant name (e.g. "twinkle_gentle_shimmer"), base effect ("Twinkle"), energy tag ("low"), tier affinity ("background"), and a summary of parameter overrides.](screenshots/11-variant-browser.png)

### How Variants Connect to Themes

In the **Theme Editor**, each layer can optionally reference a variant. When the generator places that layer's effect, parameters resolve in this order:

```
Effect defaults  →  Variant overrides  →  Layer parameter overrides
```

The variant sets the baseline character. The theme layer can fine-tune on top. For example, a theme might say "use the `twinkle_gentle_shimmer` variant but increase speed to 20."

### Variant Tags Drive Smart Selection

Each variant carries tags that the generator uses when auto-selecting:
- **tier_affinity** — which tier level it suits (background, mid, foreground, hero)
- **energy_level** — should match the section's energy
- **section_roles** — verse, chorus, bridge, build, drop, etc.
- **direction_cycle** — alternates direction across repeated placements

---

## 10. Generate the Sequence

With your song story edited, themes assigned, and layout groups configured, generate the xLights `.xsq` file. This step uses the CLI:

```bash
xlight-analyze generate song.mp3 layout.xlights_rgbeffects
```

The generator automatically picks up your `_story_reviewed.json` if it exists alongside the audio file. To be explicit:

```bash
xlight-analyze generate song.mp3 layout.xlights_rgbeffects \
  --story song_story_reviewed.json
```

### What Happens

1. Loads your analysis, song story, layout groups, themes, and variants
2. Selects themes per section (using your assignments, or auto-selecting based on mood/energy/occasion)
3. Places effects across all 8 tiers — mapping theme layers to power groups, resolving variants, aligning to beats and bars
4. Blends palettes with chord-derived colors from the harmonic analysis
5. Writes the `.xsq` file

### Useful Options

| Flag | What It Does |
|------|-------------|
| `--theme-override chorus=Inferno` | Force a theme for a section type (repeatable) |
| `--tiers base,beat,hero` | Only generate specific tiers |
| `--occasion christmas` | Set occasion for auto theme selection |
| `--fresh` | Skip cache, re-run analysis |
| `-o /path/to/output/` | Set output directory |

Or use the interactive wizard for a guided experience:

```bash
xlight-analyze generate-wizard song.mp3
```

> ![Screenshot placeholder: Terminal showing the generate command output with a summary: "Generated song.xsq — 12 sections, 6 themes, 847 effect placements across 32 groups, 8 tiers."](screenshots/12-generate-output.png)

---

## 11. Open in xLights

1. Open xLights and load your show folder
2. **File → Open Sequence** → select the generated `.xsq` file
3. The sequence appears with all effect placements on your models and groups
4. Press Play to preview synced to the music

> ![Screenshot placeholder: The xLights sequencer with the imported sequence showing colored effect blocks across model groups on the timeline, and the 2D layout preview showing lit props.](screenshots/13-xlights-result.png)

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  Song Library: Upload MP3 → Analyze                         │
│       ↓                                                     │
│  Timeline: Review raw timing tracks and quality scores      │
│       ↓                                                     │
│  Story Review: Edit sections, set preferences               │
│       ↓                                                     │
│  Story Review → Themes Tab: Assign themes to sections       │
│       ↓                                                     │
│  Theme Editor: Customize themes, add layers, set effects    │
│       ↓                                                     │
│  Variant Browser: Browse/create effect parameter presets    │
│       ↓                                                     │
│  Layout Grouping: Organize props into 8-tier power groups   │
│       ↓                                                     │
│  CLI: xlight-analyze generate song.mp3 layout.xlights       │
│       ↓                                                     │
│  xLights: Open .xsq → preview → render                     │
└─────────────────────────────────────────────────────────────┘
```

All of the above except the final generate step and xLights import happens in the web UI at `http://localhost:5173`.
