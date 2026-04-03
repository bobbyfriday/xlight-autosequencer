# CC0 Music Test Fixtures

Royalty-free, CC0-licensed tracks for end-to-end validation testing.
All tracks are public domain — no attribution required.

## Tracks

| File | Source | Duration | BPM | Character |
|---|---|---|---|---|
| `space_ambience.mp3` | FreePD | 4:36 | ~140 | Ambient pads, minimal melody, low energy |
| `nostalgic_piano.mp3` | FreePD | 3:16 | ~59 | Solo piano, clear melodic phrases |
| `maple_leaf_rag.mp3` | FreePD | 2:59 | ~99 | Ragtime, clear AABB section structure |
| `funshine.mp3` | FreePD | 2:45 | ~96 | Upbeat pop/funk, drums + bass + melody |
| `black_box_legendary.mp3` | Pixabay | 2:58 | ~81 | Electronic/cinematic, heavy beats |

## Source

Downloaded from [SoundSafari/CC0-1.0-Music](https://github.com/SoundSafari/CC0-1.0-Music).

## Usage

These files are NOT committed to git (`.gitignore` excludes `*.mp3`).
To download them:

```bash
cd tests/fixtures/cc0_music/
curl -sL -o space_ambience.mp3 "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freepd.com/Space%20Ambience.mp3"
curl -sL -o nostalgic_piano.mp3 "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freepd.com/Nostalgic%20Piano.mp3"
curl -sL -o maple_leaf_rag.mp3 "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freepd.com/Maple%20Leaf%20Rag.mp3"
curl -sL -o funshine.mp3 "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/freepd.com/Funshine.mp3"
curl -sL -o black_box_legendary.mp3 "https://raw.githubusercontent.com/SoundSafari/CC0-1.0-Music/main/pixbay.com/black-box-legendary-9509.mp3"
```

Or use the download script:

```bash
python -m tests.validation.download_fixtures
```
