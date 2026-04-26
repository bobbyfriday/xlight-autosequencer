"""xLights layout parser.

Reads xlights_rgbeffects.xml (models) + xlights_networks.xml (controllers) and
returns Models with their per-pixel positions in canonical local coords plus
the world-space transform parameters (Scale / Rotate / Translate).

The Renderer takes these and produces the final 2D screen positions.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Controller:
    name: str
    start: int   # absolute 0-based start channel in the FSEQ
    length: int


@dataclass
class Model:
    name: str
    display_as: str
    start_channel: int   # absolute, 0-based
    n_pixels: int
    parm1: int
    parm2: int
    parm3: int
    world_x: float
    world_y: float
    world_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    rotate_x: float   # degrees
    rotate_y: float
    rotate_z: float
    # ThreePointScreenLocation / TwoPointScreenLocation models use these
    # to define endpoint geometry directly (Arches, Single Line).
    x2: float = 0.0
    y2: float = 0.0
    z2: float = 0.0
    height: float = 1.0  # Arches: peak height multiplier
    custom_grid: list[list[int]] = field(default_factory=list)
    custom_w: int = 0
    custom_h: int = 0


def parse_controllers(networks_path: Path) -> dict[str, Controller]:
    """Walk xlights_networks.xml, sort by Id, accumulate channel ranges."""
    tree = ET.parse(networks_path)
    root = tree.getroot()
    items = []
    for c in root.findall("Controller"):
        idn = int(c.attrib.get("Id", 0))
        name = c.attrib["Name"]
        max_ch = 0
        net = c.find("network")
        if net is not None:
            max_ch = int(net.attrib.get("MaxChannels", 0))
        protocol = c.attrib.get("Protocol", "")
        items.append((idn, name, max_ch, protocol))
    items.sort()
    out = {}
    cursor = 0
    for _, name, max_ch, proto in items:
        if proto == "Player Only" or max_ch == 0:
            out[name] = Controller(name=name, start=cursor, length=0)
            continue
        out[name] = Controller(name=name, start=cursor, length=max_ch)
        cursor += max_ch
    return out


_START_PAT = re.compile(r"!([^:]+):(\d+)")


def resolve_start_channel(start_str: str, controllers: dict[str, Controller]) -> int | None:
    """Resolve `!Controller:N` to absolute 0-based channel; or parse a plain int."""
    m = _START_PAT.match(start_str.strip())
    if not m:
        try:
            return int(start_str) - 1
        except ValueError:
            return None
    name, ch = m.group(1), int(m.group(2))
    ctl = controllers.get(name)
    if ctl is None:
        return None
    return ctl.start + ch - 1


def _parse_custom_model(s: str) -> tuple[list[list[int]], int, int]:
    """xLights CustomModel string: rows separated by ;, cells by ,. Empty cell = no pixel."""
    rows = []
    width = 0
    for raw_row in s.split(";"):
        cells = []
        for c in raw_row.split(","):
            c = c.strip()
            if not c:
                cells.append(0)
            else:
                try:
                    cells.append(int(c))
                except ValueError:
                    cells.append(0)
        rows.append(cells)
        width = max(width, len(cells))
    for r in rows:
        while len(r) < width:
            r.append(0)
    return rows, width, len(rows)


def parse_models(rgbeffects_path: Path, controllers: dict[str, Controller]) -> list[Model]:
    """Walk xlights_rgbeffects.xml and return one Model per top-level <model>."""
    tree = ET.parse(rgbeffects_path)
    root = tree.getroot()
    out = []
    for m in root.find("models").findall("model"):
        sc = resolve_start_channel(m.attrib.get("StartChannel", "1"), controllers)
        if sc is None:
            continue
        try:
            p1 = int(m.attrib.get("parm1", 1))
            p2 = int(m.attrib.get("parm2", 1))
            p3 = int(m.attrib.get("parm3", 1))
        except ValueError:
            continue

        display_as = m.attrib.get("DisplayAs", "Single Line")
        if display_as == "Custom":
            grid_str = m.attrib.get("CustomModel", "")
            grid, gw, gh = _parse_custom_model(grid_str) if grid_str else ([], 0, 0)
            n_pix = max((max(row) for row in grid if row), default=0)
        elif display_as == "Cube":
            n_pix = p1 * p2 * p3
            grid, gw, gh = [], 0, 0
        else:
            n_pix = p1 * p2
            grid, gw, gh = [], 0, 0

        try:
            wx = float(m.attrib.get("WorldPosX", 0))
            wy = float(m.attrib.get("WorldPosY", 0))
            wz = float(m.attrib.get("WorldPosZ", 0))
            sx = float(m.attrib.get("ScaleX", 1))
            sy = float(m.attrib.get("ScaleY", 1))
            sz = float(m.attrib.get("ScaleZ", 1))
            rx = float(m.attrib.get("RotateX", 0))
            ry = float(m.attrib.get("RotateY", 0))
            rz = float(m.attrib.get("RotateZ", 0))
            x2 = float(m.attrib.get("X2", 0))
            y2 = float(m.attrib.get("Y2", 0))
            z2 = float(m.attrib.get("Z2", 0))
            height = float(m.attrib.get("Height", 1))
        except ValueError:
            continue

        out.append(Model(
            name=m.attrib.get("name", "?"),
            display_as=display_as, start_channel=sc, n_pixels=n_pix,
            parm1=p1, parm2=p2, parm3=p3,
            world_x=wx, world_y=wy, world_z=wz,
            scale_x=sx, scale_y=sy, scale_z=sz,
            rotate_x=rx, rotate_y=ry, rotate_z=rz,
            x2=x2, y2=y2, z2=z2, height=height,
            custom_grid=grid, custom_w=gw, custom_h=gh,
        ))
    return out


# ---- Per-model pixel placement in WORLD coordinates ----
#
# xLights uses three different geometry conventions, picked by DisplayAs:
#
# 1. ThreePointScreenLocation (Arches): WorldPos = first endpoint, X2/Y2/Z2 =
#    vector to second endpoint, Height = arch peak multiplier. Curve is a half-
#    sine from pt1 → pt2 with peak at Height × |pt2-pt1| above the chord.
# 2. TwoPointScreenLocation (Single Line): WorldPos = first endpoint, X2/Y2/Z2
#    = vector to second endpoint. Pixels distributed evenly along the line.
# 3. BoxedScreenLocation (Cube, Star, Tree): canonical [-0.5, 0.5]³ box,
#    Scale = half-extent in each axis (full world dim = 2 × Scale), then
#    rotate/translate.
# 4. Parm-relative (Custom, Matrix): canonical [0..parm], Scale = world units
#    per pixel; full world dim = parm × Scale.
#
# The first two encode the world geometry directly via their endpoint pairs
# and bypass the model_to_world transform entirely. The latter two go through
# the centering + scale + rotate + translate pipeline.

def _rot_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    """Z-Y-X intrinsic Tait-Bryan order (matches xLights)."""
    rx, ry, rz = np.deg2rad([rx_deg, ry_deg, rz_deg])
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float32)
    return Rz @ Ry @ Rx


def _arches_world(model: Model) -> np.ndarray:
    """Place pixels along an arch curve from pt1 to pt2 with a half-sine peak."""
    n = model.n_pixels
    positions = np.zeros((n, 3), dtype=np.float32)
    arches = max(model.parm1, 1)
    per_arch = max(model.parm2, 1)

    p1 = np.array([model.world_x, model.world_y, model.world_z], dtype=np.float32)
    chord = np.array([model.x2, model.y2, model.z2], dtype=np.float32)
    span = float(np.linalg.norm(chord))
    # Peak vector: perpendicular to the chord, in the world's +Y plane.
    # For most arches the chord lies in XZ → peak goes +Y. Cross with up vector.
    if span < 1e-3:
        return positions
    peak_dir = np.array([0, 1, 0], dtype=np.float32)
    peak_height = model.height * span * 0.5  # arch rises ~half the span by default

    # Multiple arches share the same model? In practice each arch is a separate
    # model (parm1=1 per model in this user's layout), but support parm1>1 by
    # tiling along the chord direction.
    for ai in range(arches):
        arch_p1 = p1 + (ai / arches) * chord
        arch_chord = chord / arches
        for j in range(per_arch):
            idx = ai * per_arch + j
            if idx >= n:
                break
            t = j / max(per_arch - 1, 1)  # 0..1 along chord
            angle = np.pi * t  # 0..π for a half-sine arc
            base = arch_p1 + arch_chord * t
            peak_offset = peak_dir * peak_height * np.sin(angle)
            positions[idx] = base + peak_offset
    return positions


def _line_world(model: Model) -> np.ndarray:
    """Pixels distributed evenly along a straight line from pt1 to pt2."""
    n = model.n_pixels
    positions = np.zeros((n, 3), dtype=np.float32)
    p1 = np.array([model.world_x, model.world_y, model.world_z], dtype=np.float32)
    chord = np.array([model.x2, model.y2, model.z2], dtype=np.float32)
    if np.linalg.norm(chord) < 1e-3:
        # Fall back to a small unit-X strip if X2/Y2/Z2 missing
        chord = np.array([max(n - 1, 1), 0, 0], dtype=np.float32)
    for i in range(n):
        t = i / max(n - 1, 1)
        positions[i] = p1 + chord * t
    return positions


def _boxed_world(model: Model, local: np.ndarray) -> np.ndarray:
    """Canonical [-0.5, 0.5]³ → world via Scale × 2 (full extent), Rotate, Translate."""
    pts = local.copy()
    pts[:, 0] *= model.scale_x * 2.0
    pts[:, 1] *= model.scale_y * 2.0
    pts[:, 2] *= model.scale_z * 2.0
    if abs(model.rotate_x) + abs(model.rotate_y) + abs(model.rotate_z) > 0.01:
        pts = pts @ _rot_matrix(model.rotate_x, model.rotate_y, model.rotate_z).T
    pts[:, 0] += model.world_x
    pts[:, 1] += model.world_y
    pts[:, 2] += model.world_z
    return pts


def _parm_world(model: Model, local: np.ndarray, default_size: tuple[float, float, float]) -> np.ndarray:
    """Canonical [0..parm] → world via center, Scale (per-pixel multiplier), Rotate, Translate."""
    w, h, d = default_size
    pts = local.copy()
    pts[:, 0] -= w / 2
    pts[:, 1] -= h / 2
    pts[:, 2] -= d / 2
    pts[:, 0] *= model.scale_x
    pts[:, 1] *= model.scale_y
    pts[:, 2] *= model.scale_z
    if abs(model.rotate_x) + abs(model.rotate_y) + abs(model.rotate_z) > 0.01:
        pts = pts @ _rot_matrix(model.rotate_x, model.rotate_y, model.rotate_z).T
    pts[:, 0] += model.world_x
    pts[:, 1] += model.world_y
    pts[:, 2] += model.world_z
    return pts


def model_world_pixels(model: Model) -> np.ndarray:
    """Return Nx3 WORLD-coordinate positions for every pixel of this model."""
    n = model.n_pixels
    if n <= 0:
        return np.zeros((0, 3), dtype=np.float32)

    da = model.display_as

    if da == "Arches":
        return _arches_world(model)

    if da == "Single Line":
        return _line_world(model)

    if da == "Custom" and model.custom_grid:
        # Parm-relative: canonical = grid coords, Scale = world units per pixel.
        local = np.zeros((n, 3), dtype=np.float32)
        for r, row in enumerate(model.custom_grid):
            for c, pix in enumerate(row):
                if 0 < pix <= n:
                    local[pix - 1] = (c, model.custom_h - 1 - r, 0)
        return _parm_world(model, local, (model.custom_w, model.custom_h, 1))

    if da in ("Horiz Matrix", "Vert Matrix"):
        strings = max(model.parm1, 1)
        per_string = max(model.parm2, 1)
        strands = max(model.parm3, 1)
        per_strand = max(per_string // strands, 1)
        local = np.zeros((n, 3), dtype=np.float32)
        if da == "Vert Matrix":
            cols = strings * strands
            rows = per_strand
            for i in range(n):
                string = i // per_string
                in_string = i % per_string
                strand = in_string // per_strand
                in_strand = in_string % per_strand
                col = string * strands + strand
                row = in_strand if strand % 2 == 0 else (per_strand - 1 - in_strand)
                local[i] = (col, rows - 1 - row, 0)
        else:  # Horiz Matrix
            cols = per_strand
            rows = strings * strands
            for i in range(n):
                string = i // per_string
                in_string = i % per_string
                strand = in_string // per_strand
                in_strand = in_string % per_strand
                row = string * strands + strand
                col = in_strand if strand % 2 == 0 else (per_strand - 1 - in_strand)
                local[i] = (col, rows - 1 - row, 0)
        return _parm_world(model, local, (cols, rows, 1))

    if da == "Cube":
        # BoxedScreenLocation: each axis is parm[1,2,3] nodes, full world span = 2×Scale.
        w, h, d = max(model.parm1, 1), max(model.parm2, 1), max(model.parm3, 1)
        per_face = w * h
        local = np.zeros((n, 3), dtype=np.float32)
        for i in range(n):
            slab = i // per_face
            within = i % per_face
            r = within // w
            c = within % w
            # Normalize to [-0.5, 0.5] in each axis
            local[i] = (
                (c + 0.5) / w - 0.5,
                0.5 - (r + 0.5) / h,
                (slab + 0.5) / d - 0.5,
            )
        return _boxed_world(model, local)

    if da == "Star":
        # Concentric rings in XY plane; each ring has parm2 lights, parm1 rings total.
        local = np.zeros((n, 3), dtype=np.float32)
        for i in range(n):
            ring = i // max(model.parm2, 1)
            within = i % max(model.parm2, 1)
            ratio = (ring + 1) / max(model.parm1, 1)
            radius = 0.5 * ratio
            angle = 2 * np.pi * within / max(model.parm2, 1) - np.pi / 2
            local[i] = (radius * np.cos(angle), radius * np.sin(angle), 0)
        return _boxed_world(model, local)

    if da.startswith("Tree"):
        # Half-cone: spirals from base (Y=-0.5) up to top (Y=+0.5).
        local = np.zeros((n, 3), dtype=np.float32)
        strings = max(model.parm1, 1)
        per = max(model.parm2, 1)
        for s in range(strings):
            base_angle = 2 * np.pi * s / strings
            for j in range(per):
                idx = s * per + j
                if idx >= n:
                    break
                t = j / max(per - 1, 1)  # 0..1 base→top
                radius = 0.5 * (1 - t)
                angle = base_angle + t * np.pi
                local[idx] = (
                    radius * np.cos(angle),
                    t - 0.5,
                    radius * np.sin(angle),
                )
        return _boxed_world(model, local)

    # Fallback: parm-style strip along +X
    local = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        local[i] = (i / max(n - 1, 1), 0, 0)
    return _parm_world(model, local, (max(n, 1), 1, 1))
