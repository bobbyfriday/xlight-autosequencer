"""Load and query the xLights effect variant library."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from src.effects.library import EffectLibrary
from src.variants.models import EffectVariant
from src.variants.validator import validate_variant

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtins"
_DEFAULT_CUSTOM_DIR = Path.home() / ".xlight" / "custom_variants"


@dataclass
class VariantLibrary:
    schema_version: str
    variants: dict[str, EffectVariant]
    builtin_names: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.builtin_names is None:
            self.builtin_names = set()

    def get(self, name: str) -> EffectVariant | None:
        """Look up a variant by name (case-insensitive)."""
        if name in self.variants:
            return self.variants[name]
        name_lower = name.lower()
        for key, variant in self.variants.items():
            if key.lower() == name_lower:
                return variant
        return None

    def query(
        self,
        base_effect: str | None = None,
        energy_level: str | None = None,
        tier_affinity: str | None = None,
        scope: str | None = None,
        section_role: str | None = None,
    ) -> list[EffectVariant]:
        """Return variants matching all specified filters (AND logic).

        base_effect comparison is case-insensitive.
        """
        base_effect_lower = base_effect.lower() if base_effect is not None else None
        results = []
        for variant in self.variants.values():
            if base_effect_lower is not None and variant.base_effect.lower() != base_effect_lower:
                continue
            if energy_level is not None and variant.tags.energy_level != energy_level:
                continue
            if tier_affinity is not None and variant.tags.tier_affinity != tier_affinity:
                continue
            if scope is not None and variant.tags.scope != scope:
                continue
            if section_role is not None and section_role not in variant.tags.section_roles:
                continue
            results.append(variant)
        return results

    def save_custom_variant(self, variant: EffectVariant, custom_dir: Path) -> Path:
        """Persist a variant as a JSON file in custom_dir and register it in memory.

        Returns the path to the saved file. Logs a warning if the name matches an
        existing variant (built-in override).
        """
        if variant.name in self.variants:
            logger.warning(
                "save_custom_variant: overriding existing variant '%s'", variant.name
            )
        custom_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(variant.name)
        dest = custom_dir / f"{slug}.json"
        dest.write_text(json.dumps(variant.to_dict(), indent=2), encoding="utf-8")
        self.variants[variant.name] = variant
        return dest

    def delete_custom_variant(self, name: str, custom_dir: Path) -> None:
        """Remove a custom variant file and unregister it from memory.

        Scans custom_dir for a JSON file whose 'name' field matches (case-insensitive)
        rather than assuming a slug-based filename, so externally-created files are
        found regardless of how they were named.

        Raises KeyError if the variant is not in this library instance.
        Raises FileNotFoundError if no matching file exists in custom_dir.
        """
        variant = self.get(name)
        if variant is None:
            raise KeyError(f"Variant '{name}' not found in library")

        target_file = _find_variant_file(variant.name, custom_dir)
        if target_file is None:
            raise FileNotFoundError(
                f"No custom variant file found for '{name}' in {custom_dir}"
            )

        target_file.unlink()
        for key in list(self.variants.keys()):
            if key.lower() == name.lower():
                del self.variants[key]
                break


def _find_variant_file(name: str, custom_dir: Path) -> Path | None:
    """Return the Path of the JSON file in custom_dir whose 'name' matches, or None."""
    if not custom_dir.is_dir():
        return None
    name_lower = name.lower()
    for json_file in sorted(custom_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if isinstance(data.get("name"), str) and data["name"].lower() == name_lower:
                return json_file
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _slugify(name: str) -> str:
    """Convert a variant name to a filesystem-safe ASCII slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "variant"


def _load_variants_from_single_file(
    path: Path,
    effect_library: EffectLibrary | None,
) -> tuple[str, dict[str, EffectVariant]]:
    """Load variants from a single JSON file (legacy format).

    Returns (schema_version, variants_dict).
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    schema_version = raw.get("schema_version", "0.0.0")
    variants: dict[str, EffectVariant] = {}

    for data in raw.get("variants", []):
        if effect_library is not None:
            errors = validate_variant(data, effect_library)
            if errors:
                logger.error(
                    "Built-in variant '%s' has validation errors: %s",
                    data.get("name", "<unknown>"),
                    errors,
                )
                continue
        variant = EffectVariant.from_dict(data)
        variants[variant.name] = variant

    return schema_version, variants


def _load_variants_from_dir(
    builtin_dir: Path,
    effect_library: EffectLibrary | None,
) -> tuple[str, dict[str, EffectVariant]]:
    """Load variants from a per-effect directory of JSON files.

    Returns (schema_version, variants_dict).
    """
    schema_version = "0.0.0"
    manifest_path = builtin_dir / "_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema_version = manifest.get("schema_version", "0.0.0")

    variants: dict[str, EffectVariant] = {}
    for json_file in sorted(builtin_dir.glob("*.json")):
        if json_file.name.startswith("_"):
            continue
        try:
            raw = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Skipping malformed builtin file '%s': %s", json_file.name, exc
            )
            continue
        for data in raw.get("variants", []):
            if effect_library is not None:
                errors = validate_variant(data, effect_library)
                if errors:
                    logger.error(
                        "Built-in variant '%s' has validation errors: %s",
                        data.get("name", "<unknown>"),
                        errors,
                    )
                    continue
            variant = EffectVariant.from_dict(data)
            variants[variant.name] = variant

    return schema_version, variants


def load_variant_library(
    builtin_dir: str | Path | None = None,
    builtin_path: str | Path | None = None,
    custom_dir: str | Path | None = None,
    effect_library: EffectLibrary | None = None,
) -> VariantLibrary:
    """Load the variant library from built-in variants + optional custom overrides.

    Args:
        builtin_dir: Path to the per-effect builtins directory. Defaults to
            the bundled ``builtins/`` directory. Ignored when *builtin_path*
            is provided.
        builtin_path: Legacy single-file mode — path to a monolithic JSON
            catalog. When set, *builtin_dir* is ignored. Useful for test
            fixtures that still ship a single file.
        custom_dir: Path to the custom overrides directory. Defaults to
            ~/.xlight/custom_variants/. If the directory doesn't exist,
            only built-in variants are returned.
        effect_library: EffectLibrary used to validate base_effect references.
            If None, validation is skipped (variants are loaded without checks).

    Raises:
        FileNotFoundError: If the built-in source is missing.
    """
    custom_dir = Path(custom_dir) if custom_dir else _DEFAULT_CUSTOM_DIR

    if builtin_path:
        # Legacy single-file mode (test fixtures)
        builtin_path = Path(builtin_path)
        if not builtin_path.exists():
            raise FileNotFoundError(f"Built-in variant library not found: {builtin_path}")
        schema_version, variants = _load_variants_from_single_file(builtin_path, effect_library)
    else:
        resolved_dir = Path(builtin_dir) if builtin_dir else _BUILTIN_DIR
        if not resolved_dir.is_dir():
            raise FileNotFoundError(f"Built-in variant directory not found: {resolved_dir}")
        schema_version, variants = _load_variants_from_dir(resolved_dir, effect_library)

    builtin_names = set(variants.keys())

    # Load custom overrides / additions
    if custom_dir.is_dir():
        for custom_file in sorted(custom_dir.glob("*.json")):
            try:
                with open(custom_file, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                if effect_library is not None:
                    errors = validate_variant(custom_data, effect_library)
                    if errors:
                        logger.warning(
                            "Skipping invalid custom variant '%s': %s",
                            custom_file.name,
                            errors,
                        )
                        continue
                variant = EffectVariant.from_dict(custom_data)
                variants[variant.name] = variant
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "Skipping malformed custom variant file '%s': %s",
                    custom_file.name,
                    exc,
                )

    return VariantLibrary(schema_version=schema_version, variants=variants, builtin_names=builtin_names)
