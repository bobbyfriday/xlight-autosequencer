"""Import effect variants from .xsq sequence files."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from src.effects.library import EffectLibrary
from src.variants.library import VariantLibrary
from src.variants.models import EffectVariant, VariantTags

# xLights param key names → our effect library names (spacing/casing mismatches)
_EFFECT_NAME_ALIASES: dict[str, str] = {
    "ColorWash": "Color Wash",
    "VUMeter": "VU Meter",
    "SingleStrand": "Single Strand",
}


def _parse_effect_db(root: ET.Element) -> dict[int, dict[str, str]]:
    """Build a ref → parameter dict index from <EffectDB> element.

    Each <Effect> element has comma-separated key=value pairs as text.
    """
    effect_db: dict[int, dict[str, str]] = {}
    db_el = root.find("EffectDB")
    if db_el is None:
        return effect_db

    for idx, effect_el in enumerate(db_el.findall("Effect")):
        ref_str = effect_el.get("ref")
        # Use explicit ref attribute if present, otherwise use index
        if ref_str is not None:
            try:
                ref = int(ref_str)
            except ValueError:
                ref = idx
        else:
            ref = idx

        text = (effect_el.text or "").strip()
        params: dict[str, str] = {}
        if text:
            for token in text.split(","):
                token = token.strip()
                if "=" in token:
                    key, _, value = token.partition("=")
                    params[key.strip()] = value.strip()
        effect_db[ref] = params

    return effect_db


def _extract_effect_name(params: dict[str, str], label: str) -> str | None:
    """Determine the effect name from parameter keys or label.

    Parameter keys follow the pattern E_{type}_{EffectName}_{ParamName}.
    We extract EffectName from the second underscore-delimited segment.
    """
    candidates: dict[str, int] = {}
    for key in params:
        parts = key.split("_")
        if len(parts) >= 3:
            if parts[2] == "Eff" and len(parts) >= 4:
                effect_name = parts[3]
            else:
                effect_name = parts[2]
            candidates[effect_name] = candidates.get(effect_name, 0) + 1

    if candidates:
        # xLights meta-effects (e.g. Single Strand) contain sub-effect params
        # (Chase, Skips) that outvote the parent.  Detect by known marker keys.
        if "SingleStrand" in candidates:
            return "Single Strand"
        name = max(candidates, key=lambda k: candidates[k])
        return _EFFECT_NAME_ALIASES.get(name, name)

    if label:
        first_word = label.split()[0] if label.split() else ""
        if first_word:
            return first_word

    return None


def _make_identity_key(base_effect: str, params: dict) -> str:
    """Compute identity_key for a given (base_effect, params) pair.

    Uses the same format as EffectVariant.identity_key() — "params" key.
    """
    import hashlib
    import json

    normalized: dict[str, int | float | str] = {}
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, bool):
            normalized[k] = int(v)
        else:
            normalized[k] = v

    payload = json.dumps(
        {"base_effect": base_effect, "params": normalized},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _coerce_param_values(params: dict[str, str]) -> dict[str, int | float | str]:
    """Coerce string parameter values to int/float where possible."""
    result: dict[str, int | float | str] = {}
    for k, v in params.items():
        try:
            result[k] = int(v)
            continue
        except ValueError:
            pass
        try:
            result[k] = float(v)
            continue
        except ValueError:
            pass
        result[k] = v
    return result


def extract_variants_from_xsq(
    xsq_path: str | Path,
    effect_library: EffectLibrary,
    skip_duplicates: bool = False,
    existing_library: VariantLibrary | None = None,
    dry_run: bool = False,
    custom_dir: str | Path | None = None,
) -> list[dict]:
    """Extract effect variants from an .xsq sequence file.

    Parses the EffectDB from the .xsq XML, identifies unique effect
    configurations, and returns them as a list of result dicts.

    Args:
        xsq_path: Path to the .xsq file.
        effect_library: Loaded effect library for validation.
        skip_duplicates: If True, exclude duplicate entries from the result.
        existing_library: Existing variant library to check for pre-existing
            duplicates. If None, only in-XSQ deduplication is performed.
        dry_run: If True, do not save any variants to disk.
        custom_dir: Directory to save imported variants. If None, defaults to
            ~/.xlight/custom_variants/.

    Returns:
        List of dicts with keys:
            status: "imported" | "duplicate" | "unknown"
            name: str
            base_effect: str
            parameter_overrides: dict
            identity_key: str
    """
    xsq_path = Path(xsq_path)

    try:
        tree = ET.parse(str(xsq_path))
        root = tree.getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {xsq_path}: {exc}") from exc

    effect_db = _parse_effect_db(root)

    if not effect_db:
        return []

    # Collect labels from ElementEffects
    label_by_ref: dict[int, str] = {}
    element_effects_el = root.find("ElementEffects")
    if element_effects_el is not None:
        for elem_el in element_effects_el:
            for eff_el in elem_el.findall("Effect"):
                ref_str = eff_el.get("ref")
                label = eff_el.get("label", "")
                if ref_str is not None:
                    try:
                        ref = int(ref_str)
                        if ref not in label_by_ref and label:
                            label_by_ref[ref] = label
                    except ValueError:
                        pass

    # Track seen identity keys within this XSQ (for intra-file deduplication)
    seen_identity_keys: set[str] = set()

    # Pre-populate from existing library if provided
    if existing_library is not None:
        for v in existing_library.variants.values():
            seen_identity_keys.add(v.identity_key())

    # Count per effect name for auto-numbering
    effect_name_counter: dict[str, int] = {}

    results: list[dict] = []

    for ref in sorted(effect_db.keys()):
        raw_params = effect_db[ref]
        label = label_by_ref.get(ref, "")

        base_effect = _extract_effect_name(raw_params, label)
        coerced_params = _coerce_param_values(raw_params)

        if base_effect is None or effect_library.get(base_effect) is None:
            identity_key = _make_identity_key(base_effect or "Unknown", coerced_params)
            item = {
                "status": "unknown",
                "name": label or f"Unknown {ref}",
                "base_effect": base_effect or "Unknown",
                "parameter_overrides": coerced_params,
                "identity_key": identity_key,
            }
            results.append(item)
            continue

        identity_key = _make_identity_key(base_effect, coerced_params)

        if identity_key in seen_identity_keys:
            item = {
                "status": "duplicate",
                "name": label or f"{base_effect} (duplicate)",
                "base_effect": base_effect,
                "parameter_overrides": coerced_params,
                "identity_key": identity_key,
            }
            if not skip_duplicates:
                results.append(item)
            continue

        seen_identity_keys.add(identity_key)
        effect_name_counter[base_effect] = effect_name_counter.get(base_effect, 0) + 1
        seq_num = effect_name_counter[base_effect]
        auto_name = f"{base_effect} {seq_num:02d} (imported)"

        item = {
            "status": "imported",
            "name": auto_name,
            "base_effect": base_effect,
            "parameter_overrides": coerced_params,
            "identity_key": identity_key,
        }
        results.append(item)

        if not dry_run:
            variant = EffectVariant(
                name=auto_name,
                base_effect=base_effect,
                parameter_overrides=coerced_params,
                description=f"Imported from {xsq_path.name}",
                tags=VariantTags(),
            )
            if existing_library is not None:
                from src.variants.library import _DEFAULT_CUSTOM_DIR
                save_dir = Path(custom_dir) if custom_dir else _DEFAULT_CUSTOM_DIR
                existing_library.save_custom_variant(variant, custom_dir=save_dir)
            else:
                from src.variants.library import _DEFAULT_CUSTOM_DIR, _slugify
                import json as _json
                save_dir = Path(custom_dir) if custom_dir else _DEFAULT_CUSTOM_DIR
                save_dir.mkdir(parents=True, exist_ok=True)
                slug = _slugify(auto_name)
                out_path = save_dir / f"{slug}.json"
                out_path.write_text(
                    _json.dumps(variant.to_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    return results
