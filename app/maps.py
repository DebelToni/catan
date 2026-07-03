from __future__ import annotations

import math
import random
from copy import deepcopy
from typing import Any

STANDARD_COORDS = [
    (q, r)
    for r in range(-2, 3)
    for q in range(max(-2, -r - 2), min(2, -r + 2) + 1)
]
CRESCENT_COORDS = [
    (-3, 0), (-3, 1),
    (-2, -1), (-2, 0), (-2, 1), (-2, 2),
    (-1, -2), (-1, -1), (-1, 0), (-1, 2),
    (0, -2), (0, -1), (0, 0), (0, 1),
    (1, -1), (1, 0), (1, 1),
    (2, -1), (2, 0),
]
EXTENDED_COORDS = [
    (q, r)
    for r, start, end in [(-3, 0, 2), (-2, -1, 2), (-1, -2, 2), (0, -3, 2), (1, -3, 1), (2, -3, 0), (3, -3, -1)]
    for q in range(start, end + 1)
]
CRESCENT_56_COORDS = CRESCENT_COORDS + [
    (-4, 1), (-4, 2), (-3, -1), (-3, 2), (-2, -2),
    (-1, -3), (0, -3), (1, -2), (2, -2), (2, 1), (3, -1),
]
SEAFARERS_COORDS = [
    (-4, 0), (-3, -1), (-3, 0), (-3, 1), (-2, -1), (-2, 0), (-2, 1),
    (2, -1), (2, 0), (2, 1), (3, -2), (3, -1), (3, 0), (4, -2),
    (-1, -3), (0, -3), (1, -3), (0, -2),
    (-1, 2), (0, 2), (1, 1), (1, 2),
    (-1, 0), (1, -1), (0, 1),
    (-1, -2), (0, -1), (0, 0), (1, 0), (2, -2), (-2, 2),
]
SEAFARERS_56_COORDS = SEAFARERS_COORDS + [
    (-5, 1), (-4, -1), (4, -3), (4, -1), (2, 3), (-1, 3),
    (-2, -3), (-1, -4), (0, -4), (1, -4), (2, -3), (3, 1), (-3, 2),
    (-4, 1), (3, -3), (2, 2),
]
TERRAIN_DISTRIBUTION = [
    "forest", "forest", "forest", "forest",
    "pasture", "pasture", "pasture", "pasture",
    "field", "field", "field", "field",
    "hill", "hill", "hill",
    "mountain", "mountain", "mountain",
    "desert",
]
EXTENDED_TERRAIN_DISTRIBUTION = [
    "forest", "forest", "forest", "forest", "forest", "forest",
    "pasture", "pasture", "pasture", "pasture", "pasture", "pasture",
    "field", "field", "field", "field", "field", "field",
    "hill", "hill", "hill", "hill", "hill",
    "mountain", "mountain", "mountain", "mountain", "mountain",
    "desert", "desert",
]
SEAFARERS_LAND_DISTRIBUTION = [
    "forest", "forest", "forest", "forest", "forest",
    "pasture", "pasture", "pasture", "pasture", "pasture",
    "field", "field", "field", "field", "field",
    "hill", "hill", "hill", "hill",
    "mountain", "mountain", "mountain",
]
SEAFARERS_56_EXTRA_LAND_DISTRIBUTION = ["forest", "pasture", "field", "field", "hill", "mountain"]
# Official letter-token order used when placing numbers in a spiral and skipping the desert.
NUMBER_TOKENS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
SEAFARERS_NUMBER_TOKENS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11, 3, 4, 5, 6, 9, 10]
EXTENDED_NUMBER_TOKENS = [2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 8, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12]
SEAFARERS_56_NUMBER_TOKENS = EXTENDED_NUMBER_TOKENS + [3, 4, 6, 8]
RESOURCE_PORTS = ["lumber", "brick", "wool", "grain", "ore"]
PORT_TYPES = ["3:1", "3:1", "3:1", "3:1", *RESOURCE_PORTS]
PORT_TYPES_56 = [*PORT_TYPES, "3:1", "wool"]
HEX_DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
SQRT3 = math.sqrt(3)
LAND_TERRAINS = {"forest", "pasture", "field", "hill", "mountain", "desert", "gold"}
MAP_PRESETS = [
    {"id": "standard", "name": "Balanced Standard"},
    {"id": "crescent", "name": "Crescent Bay"},
    {"id": "seafarers_gold", "name": "Seafarers Gold Isles"},
    {"id": "standard_56", "name": "Balanced Standard 5-6"},
    {"id": "crescent_56", "name": "Crescent Bay 5-6"},
    {"id": "seafarers_gold_56", "name": "Seafarers Gold Isles 5-6"},
]


def list_map_presets() -> list[dict[str, str]]:
    return deepcopy(MAP_PRESETS)


def generate_map(preset: str = "standard", seed: str | int | None = None) -> dict[str, Any]:
    if preset == "crescent":
        return generate_balanced_land_map(
            preset="crescent",
            name="Crescent Bay",
            coords=CRESCENT_COORDS,
            terrain_distribution=TERRAIN_DISTRIBUTION,
            number_tokens=NUMBER_TOKENS,
            seed=seed,
        )
    if preset == "seafarers_gold":
        return generate_seafarers_gold_map(seed)
    if preset == "standard_56":
        return generate_extended_standard_map(seed)
    if preset == "crescent_56":
        return generate_balanced_land_map(
            preset="crescent_56",
            name="Crescent Bay 5-6",
            coords=CRESCENT_56_COORDS,
            terrain_distribution=EXTENDED_TERRAIN_DISTRIBUTION,
            number_tokens=EXTENDED_NUMBER_TOKENS,
            seed=seed,
            port_types=PORT_TYPES_56,
            players_5_6=True,
            shuffle_numbers=True,
        )
    if preset == "seafarers_gold_56":
        return generate_seafarers_gold_map(seed, players_5_6=True)
    return generate_standard_map(seed)


def generate_standard_map(seed: str | int | None = None) -> dict[str, Any]:
    return generate_balanced_land_map(
        preset="standard",
        name="Balanced Standard 3-4-5-4-3 Island",
        coords=STANDARD_COORDS,
        terrain_distribution=TERRAIN_DISTRIBUTION,
        number_tokens=NUMBER_TOKENS,
        seed=seed,
        number_order=standard_spiral_coords(),
    )


def generate_extended_standard_map(seed: str | int | None = None) -> dict[str, Any]:
    return generate_balanced_land_map(
        preset="standard_56",
        name="Balanced Standard 5-6 3-4-5-6-5-4-3 Island",
        coords=EXTENDED_COORDS,
        terrain_distribution=EXTENDED_TERRAIN_DISTRIBUTION,
        number_tokens=EXTENDED_NUMBER_TOKENS,
        seed=seed,
        port_types=PORT_TYPES_56,
        players_5_6=True,
        shuffle_numbers=True,
    )


def generate_balanced_land_map(
    preset: str,
    name: str,
    coords: list[tuple[int, int]],
    terrain_distribution: list[str],
    number_tokens: list[int],
    seed: str | int | None,
    number_order: list[tuple[int, int]] | None = None,
    port_types: list[str] | None = None,
    players_5_6: bool = False,
    shuffle_numbers: bool = False,
) -> dict[str, Any]:
    rng = random.Random(seed)
    best_hexes = None
    best_score = 10**9
    order = number_order or number_order_for_shape(coords)
    for _ in range(12000):
        terrains = list(terrain_distribution)
        rng.shuffle(terrains)
        numbers = list(number_tokens)
        if shuffle_numbers:
            rng.shuffle(numbers)
        hexes = build_hex_specs(coords, terrains, numbers, order)
        score = score_layout(hexes)
        if score < best_score:
            best_hexes = hexes
            best_score = score
        if score <= 20:
            break
    return attach_topology({
        "id": preset,
        "name": name,
        "hexes": best_hexes or build_hex_specs(coords, list(terrain_distribution), number_tokens, order),
        "ports": build_ports(rng, port_types or PORT_TYPES),
        "players_5_6": players_5_6,
    })


def generate_seafarers_gold_map(seed: str | int | None = None, players_5_6: bool = False) -> dict[str, Any]:
    rng = random.Random(seed)
    fixed = {
        (-1, 0): "gold",
        (1, -1): "gold",
        (0, 1): "desert",
        (-1, -2): "sea",
        (0, -1): "sea",
        (0, 0): "sea",
        (1, 0): "sea",
        (2, -2): "sea",
        (-2, 2): "sea",
    }
    hidden_coords = {(-1, -3), (0, -3), (1, -3), (0, -2)}
    coords = SEAFARERS_COORDS
    land_distribution = list(SEAFARERS_LAND_DISTRIBUTION)
    number_tokens = list(SEAFARERS_NUMBER_TOKENS)
    port_types = PORT_TYPES
    preset = "seafarers_gold"
    name = "Seafarers Gold Isles"
    if players_5_6:
        fixed.update({
            (-2, -3): "sea",
            (-1, -4): "sea",
            (0, -4): "sea",
            (1, -4): "sea",
            (2, -3): "sea",
            (3, 1): "sea",
            (-3, 2): "sea",
            (-4, 1): "gold",
            (3, -3): "gold",
            (2, 2): "desert",
        })
        hidden_coords.update({(-5, 1), (-4, -1), (4, -3), (4, -1), (2, 3), (-1, 3), (-4, 1), (3, -3)})
        coords = SEAFARERS_56_COORDS
        land_distribution = list(SEAFARERS_LAND_DISTRIBUTION) + list(SEAFARERS_56_EXTRA_LAND_DISTRIBUTION)
        number_tokens = list(SEAFARERS_56_NUMBER_TOKENS)
        port_types = PORT_TYPES_56
        preset = "seafarers_gold_56"
        name = "Seafarers Gold Isles 5-6"
    variable_coords = [coord for coord in coords if coord not in fixed]
    order = number_order_for_shape(coords)
    best_hexes = None
    best_score = 10**9
    for _ in range(16000):
        terrains = list(land_distribution)
        rng.shuffle(terrains)
        numbers = list(number_tokens)
        rng.shuffle(numbers)
        by_coord = dict(fixed)
        by_coord.update(dict(zip(variable_coords, terrains)))
        hexes = build_hex_specs(coords, [by_coord[coord] for coord in coords], numbers, order, hidden_coords)
        score = score_layout(hexes)
        if score < best_score:
            best_hexes = hexes
            best_score = score
        if score <= 20:
            break
    return attach_topology({
        "id": preset,
        "name": name,
        "hexes": best_hexes or [],
        "ports": build_ports(rng, port_types),
        "uses_ships": True,
        "uses_gold": True,
        "uses_pirate": True,
        "uses_fog": True,
        "players_5_6": players_5_6,
    })


def build_hex_specs(
    coords: list[tuple[int, int]],
    terrains: list[str],
    numbers: list[int],
    number_order: list[tuple[int, int]] | None = None,
    hidden_coords: set[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    result = []
    for index, ((q, r), terrain) in enumerate(zip(coords, terrains)):
        x, y = axial_to_pixel(q, r)
        hidden = (hidden_coords is not None and (q, r) in hidden_coords and terrain != "sea")
        result.append({
            "id": f"h{index}",
            "q": q,
            "r": r,
            "x": x,
            "y": y,
            "terrain": terrain,
            "number": None,
            "hidden": hidden,
            "revealed": not hidden,
        })
    assign_numbers(result, numbers, number_order or number_order_for_shape(coords))
    return result


def assign_numbers(hexes: list[dict[str, Any]], numbers: list[int], order: list[tuple[int, int]]) -> None:
    by_coord = {(hex_tile["q"], hex_tile["r"]): hex_tile for hex_tile in hexes}
    number_index = 0
    for coord in order:
        hex_tile = by_coord.get(coord)
        if not hex_tile or hex_tile["terrain"] in {"desert", "sea"}:
            continue
        if number_index >= len(numbers):
            break
        hex_tile["number"] = numbers[number_index]
        number_index += 1


def standard_spiral_coords() -> list[tuple[int, int]]:
    return [
        (0, -2), (1, -2), (2, -2), (2, -1), (2, 0), (1, 1),
        (0, 2), (-1, 2), (-2, 2), (-2, 1), (-2, 0), (-1, -1),
        (0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0),
        (0, 0),
    ]


def number_order_for_shape(coords: list[tuple[int, int]]) -> list[tuple[int, int]]:
    def sort_key(coord: tuple[int, int]) -> tuple[int, float, float]:
        q, r = coord
        ring = max(abs(q), abs(r), abs(-q - r))
        x, y = axial_to_pixel(q, r)
        return (-ring, math.atan2(y, x), math.hypot(x, y))
    return sorted(coords, key=sort_key)


def score_layout(hexes: list[dict[str, Any]]) -> int:
    red_adjacencies = count_adjacent_pairs(hexes, lambda a, b: a.get("number") in {6, 8} and b.get("number") in {6, 8})
    same_resource_adjacencies = count_adjacent_pairs(
        hexes,
        lambda a, b: a["terrain"] == b["terrain"] and a["terrain"] not in {"desert", "sea"},
    )
    red_terrains = [hex_tile["terrain"] for hex_tile in hexes if hex_tile.get("number") in {6, 8}]
    duplicate_red_resources = len(red_terrains) - len(set(red_terrains))
    return red_adjacencies * 10000 + same_resource_adjacencies * 100 + duplicate_red_resources * 10


def count_adjacent_pairs(hexes: list[dict[str, Any]], predicate) -> int:
    by_coord = {(hex_tile["q"], hex_tile["r"]): hex_tile for hex_tile in hexes}
    count = 0
    seen = set()
    for hex_tile in hexes:
        for dq, dr in HEX_DIRECTIONS:
            neighbor = by_coord.get((hex_tile["q"] + dq, hex_tile["r"] + dr))
            if not neighbor:
                continue
            key = tuple(sorted((hex_tile["id"], neighbor["id"])))
            if key in seen:
                continue
            seen.add(key)
            if predicate(hex_tile, neighbor):
                count += 1
    return count


def has_adjacent_red_numbers(hexes: list[dict[str, Any]]) -> bool:
    return count_adjacent_pairs(hexes, lambda a, b: a.get("number") in {6, 8} and b.get("number") in {6, 8}) > 0


def has_adjacent_same_resources(hexes: list[dict[str, Any]]) -> bool:
    return count_adjacent_pairs(hexes, lambda a, b: a["terrain"] == b["terrain"] and a["terrain"] not in {"desert", "sea"}) > 0


def axial_to_pixel(q: int, r: int, size: float = 1.0) -> tuple[float, float]:
    return (size * SQRT3 * (q + r / 2), size * 1.5 * r)


def hex_corners(x: float, y: float, size: float = 1.0) -> list[tuple[float, float]]:
    corners = []
    for index in range(6):
        angle = math.radians(60 * index - 30)
        corners.append((x + size * math.cos(angle), y + size * math.sin(angle)))
    return corners


def attach_topology(map_config: dict[str, Any]) -> dict[str, Any]:
    config = deepcopy(map_config)
    vertices_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    edges_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for hex_tile in config["hexes"]:
        corners = hex_corners(hex_tile["x"], hex_tile["y"])
        vertex_ids = []
        for corner_x, corner_y in corners:
            key = (round(corner_x * 10000), round(corner_y * 10000))
            if key not in vertices_by_key:
                vertices_by_key[key] = {
                    "id": f"v{len(vertices_by_key)}",
                    "x": corner_x,
                    "y": corner_y,
                    "hexes": [],
                }
            vertex = vertices_by_key[key]
            vertex["hexes"].append(hex_tile["id"])
            vertex_ids.append(vertex["id"])
        edge_ids = []
        for index in range(6):
            a = vertex_ids[index]
            b = vertex_ids[(index + 1) % 6]
            key = tuple(sorted((a, b)))
            if key not in edges_by_key:
                edges_by_key[key] = {
                    "id": f"e{len(edges_by_key)}",
                    "vertices": [a, b],
                    "hexes": [],
                }
            edge = edges_by_key[key]
            edge["hexes"].append(hex_tile["id"])
            edge_ids.append(edge["id"])
        hex_tile["vertices"] = vertex_ids
        hex_tile["edges"] = edge_ids

    vertices = sorted(vertices_by_key.values(), key=lambda item: item["id"])
    edges = sorted(edges_by_key.values(), key=lambda item: item["id"])
    vertices_by_id = {vertex["id"]: vertex for vertex in vertices}
    edges_by_id = {edge["id"]: edge for edge in edges}
    vertex_edges: dict[str, list[str]] = {vertex["id"]: [] for vertex in vertices}
    vertex_neighbors: dict[str, list[str]] = {vertex["id"]: [] for vertex in vertices}
    for edge in edges:
        a, b = edge["vertices"]
        vertex_edges[a].append(edge["id"])
        vertex_edges[b].append(edge["id"])
        vertex_neighbors[a].append(b)
        vertex_neighbors[b].append(a)

    ports = resolve_ports(config.get("ports", []), edges, vertices_by_id)
    config["vertices"] = vertices
    config["edges"] = edges
    config["ports"] = ports
    config["hexes_by_id"] = {hex_tile["id"]: hex_tile for hex_tile in config["hexes"]}
    config["vertices_by_id"] = vertices_by_id
    config["edges_by_id"] = edges_by_id
    config["vertex_edges"] = vertex_edges
    config["vertex_neighbors"] = vertex_neighbors
    return config


def build_ports(rng: random.Random, port_types: list[str] | None = None) -> list[dict[str, Any]]:
    types = list(port_types or PORT_TYPES)
    rng.shuffle(types)
    return [{"kind": kind, "slot": index} for index, kind in enumerate(types)]


def resolve_ports(port_specs: list[dict[str, Any]], edges: list[dict[str, Any]], vertices_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_edges = [edge for edge in edges if len(edge["hexes"]) == 1 and not edge_is_all_sea(edge, vertices_by_id)]
    boundary_edges.sort(key=lambda edge: edge_angle(edge, vertices_by_id))
    if not boundary_edges:
        return []
    selected = []
    used_edges = set()
    for spec_index, spec in enumerate(port_specs):
        edge_id = spec.get("edge_id")
        if not edge_id:
            slot = int(spec.get("slot", spec_index))
            target_index = round(slot * len(boundary_edges) / max(1, len(port_specs))) % len(boundary_edges)
            for offset in range(len(boundary_edges)):
                candidate = boundary_edges[(target_index + offset) % len(boundary_edges)]
                if candidate["id"] not in used_edges:
                    edge_id = candidate["id"]
                    break
        if edge_id and edge_id not in used_edges:
            used_edges.add(edge_id)
            selected.append({
                "id": f"p{len(selected)}",
                "edge_id": edge_id,
                "kind": spec.get("kind", "3:1"),
            })
    return selected


def edge_is_all_sea(edge: dict[str, Any], vertices_by_id: dict[str, dict[str, Any]]) -> bool:
    return False


def edge_angle(edge: dict[str, Any], vertices_by_id: dict[str, dict[str, Any]]) -> float:
    a, b = edge["vertices"]
    ax, ay = vertices_by_id[a]["x"], vertices_by_id[a]["y"]
    bx, by = vertices_by_id[b]["x"], vertices_by_id[b]["y"]
    return math.atan2((ay + by) / 2, (ax + bx) / 2)
