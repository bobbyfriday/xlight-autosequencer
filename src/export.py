"""T015: JSON serialisation and deserialisation for AnalysisResult."""
from __future__ import annotations

import json

from src.analyzer.result import AnalysisResult


def write(result: AnalysisResult, path: str) -> None:
    """Serialise an AnalysisResult to a JSON file."""
    data = result.to_dict()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def read(path: str) -> AnalysisResult:
    """Deserialise an AnalysisResult from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return AnalysisResult.from_dict(data)
