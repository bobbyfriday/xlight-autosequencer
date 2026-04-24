# CC0 Music Test Fixtures

Royalty-free, CC0-licensed tracks used by the `xlight-evaluate gate` acceptance
suite as the default regression corpus. All tracks are public domain — no
attribution required.

## Tracks (4, all CC0 from FreePD)

| File | Duration | BPM | Character |
|---|---|---|---|
| `space_ambience.mp3` | 4:36 | ~140 | Ambient pads, minimal melody, low energy |
| `nostalgic_piano.mp3` | 3:16 | ~59 | Solo piano, clear melodic phrases |
| `maple_leaf_rag.mp3` | 2:59 | ~99 | Ragtime, clear AABB section structure |
| `funshine.mp3` | 2:45 | ~96 | Upbeat pop/funk, drums + bass + melody |

All tracks are sourced from [SoundSafari/CC0-1.0-Music](https://github.com/SoundSafari/CC0-1.0-Music)
(FreePD mirror). A fifth Pixabay-sourced track (`black_box_legendary.mp3`) was
previously listed but removed — Pixabay uses the Pixabay Content License, which
is CC0-like but not actually CC0, and the licensing ambiguity is not worth the
one extra genre it covered.

## Usage

MP3s are **not committed** to the repo — `.gitignore` excludes `*.mp3`.
The `manifest.json` in this directory is committed and records each track's
expected SHA-256 hash. Download via:

```bash
python -m tests.validation.download_fixtures              # download + hash-verify
python -m tests.validation.download_fixtures --force      # re-download all
python -m tests.validation.download_fixtures --update-hashes
    # deliberate rotation — re-download and rewrite manifest hashes
```

A hash mismatch on download means the source URL was silently replaced upstream.
The script deletes the bad file and exits with code **8** (infrastructure
failure), so a drifted MP3 cannot shift the acceptance-gate baseline invisibly.

## Optional local corpus augmentation

For richer local testing against your own music library, create
`~/.xlight/eval_corpus.json`. This file is **never committed** and never
referenced by CI. Songs listed here are added to the default CC0 corpus when
you run the gate locally.

```json
{
  "entries": [
    {
      "slug": "mariah-carey-christmas",
      "path": "/Users/you/Music/ALL I WANT FOR CHRISTMAS IS YOU.mp3",
      "genre": "pop",
      "tempo_bpm": 150,
      "expected_section_count": 6
    },
    {
      "slug": "custom-test",
      "path": "/absolute/path/to/another.mp3"
    }
  ]
}
```

`slug` and `path` are required; other fields are optional. Paths must be
absolute. Local entries are **not** hash-verified (they're your own files).
