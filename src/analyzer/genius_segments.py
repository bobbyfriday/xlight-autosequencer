"""Genius lyric segment timing: fetch, parse, and align section headers to audio."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class LyricSegment:
    """An intermediate section parsed from Genius lyrics (not persisted)."""

    label: str            # header text without brackets, e.g. "Chorus", "Verse 1"
    text: str             # lyric body for this section (stripped)
    occurrence_index: int # 0-based index of this label's repetition


@dataclass
class GeniusMatch:
    """Result of a successful Genius API lookup (transient audit record)."""

    genius_id: int
    title: str
    artist: str
    raw_lyrics: str


# ── Title sanitisation ────────────────────────────────────────────────────────

def sanitize_title(raw_title: str) -> str:
    """
    Strip common suffixes from a song title before Genius search.

    Removes:
    - "Remastered YYYY", "Live at ...", "Radio Edit", "Acoustic", etc.
    - Parenthetical qualifiers: (Remastered), [Live]
    - "feat. / ft. / featuring / with ..." phrases
    - Trailing " - ..." patterns (e.g. "Song - 2024 Version")
    """
    title = raw_title.strip()

    # Remove standalone parenthetical/bracket qualifiers at end
    title = re.sub(r"\s*[\(\[].*?[\)\]]\s*$", "", title)

    # Remove common descriptor suffixes (case-insensitive).
    # Use (?=\s|$) instead of \b so terms ending in '.' (feat., ft.) match correctly.
    title = re.sub(
        r"\s*(feat\.|ft\.|featuring|with|live|acoustic|radio edit|"
        r"explicit|demo|single|remastered|version|mix)(?=\s|$).*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # Remove trailing " - anything" if result would still be non-empty
    candidate = re.sub(r"\s+-\s+.+$", "", title).strip()
    if candidate:
        title = candidate

    return title.strip()


# ── Boilerplate stripping ─────────────────────────────────────────────────────

def strip_boilerplate(raw_lyrics: str) -> str:
    """
    Remove Genius-specific boilerplate from raw lyrics.

    Strips:
    - Leading contributor count line: "N Contributors to 'Song' Lyrics"
    - Trailing "Embed" token (sometimes with a number prefix like "42Embed")
    """
    lines = raw_lyrics.splitlines()

    # Drop first line if it looks like "N Contributors to ... Lyrics"
    if lines and re.match(r"^\d+\s+Contributor", lines[0], re.IGNORECASE):
        lines = lines[1:]

    text = "\n".join(lines)

    # Strip trailing "Embed" or "NNEmbed"
    text = re.sub(r"\d*Embed\s*$", "", text.rstrip()).rstrip()

    return text


# ── Section parsing ───────────────────────────────────────────────────────────

def parse_sections(lyrics: str) -> list[LyricSegment]:
    """
    Split lyrics into sections using bracketed headers as boundaries.

    Returns a list of LyricSegment, one per [Header] found.
    Sections with empty text bodies are included (callers may skip them).

    Occurrence index tracks how many times each label has appeared so far
    (0-based), so the first [Chorus] gets index 0, the second gets 1, etc.
    """
    # Split on [anything], keeping the headers
    parts = re.split(r"(\[.*?\])", lyrics)

    segments: list[LyricSegment] = []
    label_counts: dict[str, int] = {}

    i = 1  # parts[0] is text before the first header (often empty/boilerplate)
    while i < len(parts):
        header_raw = parts[i]
        text_body = parts[i + 1].strip() if i + 1 < len(parts) else ""

        label = header_raw.strip("[]").strip()
        if not label:
            i += 2
            continue

        idx = label_counts.get(label, 0)
        label_counts[label] = idx + 1

        segments.append(LyricSegment(label=label, text=text_body, occurrence_index=idx))
        i += 2

    return segments


# ── ID3 tag reading ───────────────────────────────────────────────────────────

def read_id3_tags(audio_path: str) -> tuple[str, str]:
    """
    Read Artist and Title from ID3 tags via mutagen EasyID3.

    Returns (artist, title).
    Raises ValueError if tags are missing or unreadable.
    """
    try:
        from mutagen.easyid3 import EasyID3
        tags = EasyID3(audio_path)
        artist = tags["artist"][0]
        title = tags["title"][0]
        return artist, title
    except Exception as exc:
        raise ValueError(
            f"Missing or unreadable ID3 tags in {audio_path!r}: {exc}. "
            "Artist and Title tags are required for Genius lookup."
        ) from exc


# ── Genius API fetch ──────────────────────────────────────────────────────────

def fetch_genius_lyrics(title: str, artist: str, token: str) -> Optional[GeniusMatch]:
    """
    Search Genius for the song and return a GeniusMatch, or None when no song
    is found.

    Uses remove_section_headers=False to preserve [Chorus] / [Verse] markers.

    Raises:
        ImportError: if lyricsgenius is not installed.
        Exception: on network/API errors (propagated so callers can log details).
    """
    import lyricsgenius  # let ImportError propagate with a clear message
    genius = lyricsgenius.Genius(
        token,
        verbose=False,
        remove_section_headers=False,
    )
    song = genius.search_song(title, artist)
    if song is None:
        return None
    return GeniusMatch(
        genius_id=song._body.get("id", 0) if hasattr(song, "_body") else 0,
        title=song.title,
        artist=song.artist,
        raw_lyrics=song.lyrics,
    )


# ── WhisperX alignment ────────────────────────────────────────────────────────

def align_sections(
    sections: list[LyricSegment],
    audio_path: str,
    duration_s: float,
    vocals_path: Optional[str] = None,
    device: str = "cpu",
) -> list[tuple[LyricSegment, int]]:
    """
    Force-align each section's text to the audio and return (section, start_ms) pairs.

    Uses the vocals stem when available; falls back to full mix.
    Sections whose alignment yields no words are skipped (per-section warning
    is appended to align_sections.warnings on the returned list attribute).

    Returns a list of (LyricSegment, start_ms_int) for successfully aligned sections.
    The returned list has a .warnings attribute (list[str]) with per-section messages.
    """
    warnings: list[str] = []
    results: list[tuple[LyricSegment, int]] = []

    align_audio_path = vocals_path if vocals_path and Path(vocals_path).exists() else audio_path

    try:
        import whisperx

        audio = whisperx.load_audio(align_audio_path)

        # Detect language via a quick transcription pass
        try:
            _model = whisperx.load_model("base", device, compute_type="float32")
            quick = _model.transcribe(audio, batch_size=4)
            language = quick.get("language", "en")
        except Exception:
            language = "en"

        align_model, metadata = whisperx.load_align_model(
            language_code=language, device=device
        )

        for section in sections:
            if not section.text:
                warnings.append(
                    f"Section [{section.label}] (occurrence {section.occurrence_index}) "
                    "has no lyric text — skipping alignment."
                )
                continue

            try:
                aligned = whisperx.align(
                    [{"text": section.text, "start": 0.0, "end": duration_s}],
                    align_model,
                    metadata,
                    audio,
                    device,
                )
                word_segments = aligned.get("word_segments", [])
                start_s = next(
                    (ws["start"] for ws in word_segments if ws.get("start") is not None),
                    None,
                )
                if start_s is None:
                    warnings.append(
                        f"Section [{section.label}] (occurrence {section.occurrence_index}): "
                        "no words could be aligned — skipping."
                    )
                    continue
                results.append((section, int(round(start_s * 1000))))

            except Exception as exc:
                warnings.append(
                    f"Section [{section.label}] (occurrence {section.occurrence_index}): "
                    f"alignment error — {exc}. Skipping."
                )

    except ImportError:
        warnings.append(
            "whisperx is not installed — cannot align Genius sections. "
            "Install with: pip install whisperx"
        )

    results_with_warnings = _AnnotatedList(results)
    results_with_warnings.warnings = warnings
    results_with_warnings.word_marks = []  # word timing now handled by PhonemeAnalyzer
    return results_with_warnings


class _AnnotatedList(list):
    """list subclass that carries .warnings and .word_marks attributes."""
    warnings: list[str]
    word_marks: list[tuple[str, int, int]]  # (word, start_ms, end_ms)


# ── GeniusSegmentAnalyzer ─────────────────────────────────────────────────────

class GeniusSegmentAnalyzer:
    """
    Orchestrates the full Genius lyric segment pipeline.

    Usage::

        analyzer = GeniusSegmentAnalyzer()
        structure, warnings = analyzer.run(
            audio_path="song.mp3",
            token=os.environ["GENIUS_API_TOKEN"],
            stem_dir=Path("stems/"),
            duration_ms=210_000,
        )
    """

    def run(
        self,
        audio_path: str,
        token: str,
        stem_dir: Optional[Path] = None,
        duration_ms: int = 0,
        device: str = "cpu",
    ) -> tuple[Optional["SongStructure"], Optional["PhonemeResult"], list[str]]:  # noqa: F821
        """
        Run the full pipeline: ID3 → sanitize → Genius fetch → parse → align → emit.

        Returns (SongStructure, PhonemeResult, warnings).
        - SongStructure holds section-level segment boundaries (chorus/verse/etc.).
        - PhonemeResult holds word-level timing from WhisperX forced alignment of the
          Genius lyrics — verified text with accurate timestamps (lyrics_source="genius").
        Both are None on failure. Warnings are always returned.
        """
        from src.analyzer.structure import SongStructure, StructureSegment

        warnings: list[str] = []

        # ── Validate token ────────────────────────────────────────────────────
        if not token:
            warnings.append(
                "GENIUS_API_TOKEN is not set. Obtain a token at genius.com/api-clients "
                "and set: export GENIUS_API_TOKEN=\"<your-token>\""
            )
            return None, None, warnings

        # ── Read ID3 tags ─────────────────────────────────────────────────────
        try:
            artist, title = read_id3_tags(audio_path)
        except ValueError as exc:
            warnings.append(str(exc))
            return None, None, warnings

        # ── Sanitize title ────────────────────────────────────────────────────
        clean_title = sanitize_title(title)

        # ── Fetch lyrics from Genius ──────────────────────────────────────────
        try:
            match = fetch_genius_lyrics(clean_title, artist, token)
        except ImportError:
            warnings.append(
                "lyricsgenius is not installed. "
                "Install with: pip install lyricsgenius"
            )
            return None, None, warnings
        except Exception as exc:
            warnings.append(
                f"Genius API error for '{clean_title}' by '{artist}': {exc}. "
                "Check your GENIUS_API_TOKEN and network connection."
            )
            return None, None, warnings

        if match is None:
            warnings.append(
                f"No Genius match found for '{clean_title}' by '{artist}'. "
                "Skipping segment detection."
            )
            return None, None, warnings

        # ── Strip boilerplate and parse sections ──────────────────────────────
        clean_lyrics = strip_boilerplate(match.raw_lyrics)
        sections = parse_sections(clean_lyrics)

        if not sections:
            warnings.append(
                f"No section headers found in Genius lyrics for '{clean_title}' "
                "by '{artist}'. Skipping segment detection."
            )
            return None, None, warnings

        # ── Discover vocals stem ──────────────────────────────────────────────
        vocals_path: Optional[str] = None
        if stem_dir is not None:
            for candidate in [
                stem_dir / "vocals.mp3",
                stem_dir / "vocals.wav",
            ]:
                if candidate.exists():
                    vocals_path = str(candidate)
                    break

        if vocals_path is None:
            audio_p = Path(audio_path)
            for stem_subdir in [audio_p.parent / "stems", audio_p.parent / ".stems"]:
                for ext in ["mp3", "wav"]:
                    candidate = stem_subdir / f"vocals.{ext}"
                    if candidate.exists():
                        vocals_path = str(candidate)
                        break
                if vocals_path:
                    break

        if vocals_path is None:
            warnings.append(
                "Vocals stem not found — using full mix for alignment. "
                "Run with --stems for better accuracy."
            )

        # ── Align sections ────────────────────────────────────────────────────
        duration_s = duration_ms / 1000.0 if duration_ms > 0 else 0.0
        # Estimate duration from audio if not provided
        if duration_s <= 0:
            try:
                import librosa
                duration_s = float(librosa.get_duration(path=audio_path))
            except Exception:
                duration_s = 300.0  # 5-minute fallback

        aligned = align_sections(sections, audio_path, duration_s, vocals_path, device)
        warnings.extend(getattr(aligned, "warnings", []))

        if not aligned:
            warnings.append(
                "No sections could be aligned. No song_structure will be written."
            )
            return None, None, warnings

        # ── Compute boundaries: end_ms of section N = start_ms of section N+1 ─
        song_duration_ms = duration_ms if duration_ms > 0 else int(duration_s * 1000)
        aligned_sorted = sorted(aligned, key=lambda pair: pair[1])

        segments: list[StructureSegment] = []
        for i, (section, start_ms) in enumerate(aligned_sorted):
            if i + 1 < len(aligned_sorted):
                end_ms = aligned_sorted[i + 1][1]
            else:
                end_ms = song_duration_ms
            segments.append(
                StructureSegment(
                    label=section.label,
                    start_ms=start_ms,
                    end_ms=max(end_ms, start_ms + 1),
                )
            )

        song_structure = SongStructure(segments=segments, source="genius")

        # ── Build word-level PhonemeResult using PhonemeAnalyzer ─────────────
        # Concatenate all section texts into one lyrics block and force-align
        # against the audio in a single pass (the same path as --phonemes --lyrics).
        # This gives WhisperX full-song context so every word gets a timestamp.
        phoneme_result: Optional["PhonemeResult"] = None
        full_lyrics_text = "\n".join(s.text for s in sections if s.text)
        if full_lyrics_text.strip():
            import os
            import tempfile
            tmp_path: Optional[str] = None
            try:
                from src.analyzer.phonemes import PhonemeAnalyzer
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, encoding="utf-8"
                ) as tf:
                    tf.write(full_lyrics_text)
                    tmp_path = tf.name

                align_audio = vocals_path if vocals_path else audio_path
                phoneme_analyzer = PhonemeAnalyzer(device=device)
                phoneme_result = phoneme_analyzer.analyze(
                    audio_path=align_audio,
                    source_file=audio_path,
                    lyrics_path=tmp_path,
                )
                if phoneme_result is not None:
                    phoneme_result.word_track.lyrics_source = "genius"
                    phoneme_result.word_track.name = "genius-words"
                warnings.extend(getattr(phoneme_analyzer, "warnings", []))
            except Exception as exc:
                warnings.append(f"Genius word alignment failed: {exc}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return song_structure, phoneme_result, warnings
