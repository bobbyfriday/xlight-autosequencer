# Quickstart: Vamp Parameter Sweep

**Branch**: `005-vamp-parameter-tuning`

---

## Typical workflow

### 1. Discover what parameters an algorithm exposes

```bash
xlight-analyze params qm-vamp-plugins:qm-onsetdetector
```

Output shows parameter names, types, ranges, and defaults.

### 2. Get suggested candidate values for a numeric parameter

```bash
xlight-analyze sweep-suggest qm-vamp-plugins:qm-onsetdetector sensitivity --steps 5
```

Prints 5 evenly-spaced values across the valid range — copy into your config.

### 3. Create a sweep config file

`onset_sweep.json`:
```json
{
  "algorithm": "qm_onsets_complex",
  "stems": ["full_mix", "drums"],
  "sweep": {
    "sensitivity": [20, 40, 50, 60, 80]
  },
  "fixed": {
    "dftype": 3
  }
}
```

This produces 2 stems × 5 sensitivity values = **10 permutations**. Omit `"stems"`
to skip the stem dimension and use the algorithm's default stem only.

### 4. Run the sweep

```bash
xlight-analyze sweep song.mp3 --config onset_sweep.json
```

The tool runs stem separation once (or uses the cache if already separated), shows a
permutation count + runtime estimate, then prompts before starting. Results are
printed ranked by quality score with a STEM column when complete.

### 5. Validate finalists in the review UI

The sweep report JSON (`song_sweep_qm_onsets_complex.json`) contains full timing
track data for every permutation. Load it directly in the review UI to listen and
compare visually before committing to a winner.

### 6. Save the winning config

```bash
xlight-analyze sweep-save song_sweep_qm_onsets_complex.json --name tight-onsets
```

Use `--rank 2` to save the second-ranked result instead of the top result.

---

## Notes

- Quality score (density + regularity) is a **coarse filter**, not ground truth.
  Always validate the top 2–3 candidates visually before picking a winner.
- Sweeps are per-algorithm. To tune multiple algorithms, run `sweep` once per algorithm.
- Saved configs live in `~/.xlight/sweep_configs/` and persist across projects.
