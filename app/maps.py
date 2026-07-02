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
TERRAIN_DISTRIBUTION = [
    "forest", "forest", "forest", "forest",
    "pasture", "pasture", "pasture", "pasture",
    "field", "field", "field", "field",
    "hill", "hill", "hill",
    "mountain", "mountain", "mountain",
    "desert",
]
# Official letter-token order used when placing numbers in a spiral and skipping the desert.
NUMBER_TOKENS = [5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11]
RESOURCE_PORTS = ["lumber", "brick", "wool", "grain", "ore"]
PORT_TYPES = ["3:1", "3:1", "3:1", "3:1", *RESOURCE_PORTS]
HEX_DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
SQRT3 = math.sqrt(3)


def generate_standard_map(seed: str | int | None = None) -> dict[str, Any]:
    rng = random.Random(seed)
    coords = list(STANDARD_COORDS)
    best_hexes = None
    best_score = 10**9

    for _ in range(12000):
        terrains = list(TERRAIN_DISTRIBUTION)
        rng.shuffle(terrains)
        hexes = build_hex_specs(coords, terrains, list(NUMBER_TOKENS))
        score = score_layout(hexes)
        if score < best_score:
            best_hexes = hexes
            best_score = score
        if score <= 20:
            break
    return attach_topology({
        "id": "standard",
        "name": "Balanced Standard 3-4-5-4-3 Island",
        "hexes": best_hexes or build_hex_specs(coords, list(TERRAIN_DISTRIBUTION), list(NUMBER_TOKENS)),
        "ports": build_ports(rng),
    })


def build_hex_specs(coords: list[tuple[int, int]], terrains: list[str], numbers: list[int]) -> list[dict[str, Any]]:
    result = []
    for index, ((q, r), terrain) in enumerate(zip(coords, terrains)):
        x, y = axial_to_pixel(q, r)
        result.append({
            "id": f"h{index}",
            "q": q,
            "r": r,
            "x": x,
            "y": y,
            "terrain": terrain,
            "number": None,
        })
    assign_numbers_in_spiral(result, numbers)
    return result


def assign_numbers_in_spiral(hexes: list[dict[str, Any]], numbers: list[int]) -> None:
    by_coord = {(hex_tile["q"], hex_tile["r"]): hex_tile for hex_tile in hexes}
    number_index = 0
    for coord in spiral_coords(radius=2):
        hex_tile = by_coord[coord]
        if hex_tile["terrain"] == "desert":
            continue
        hex_tile["number"] = numbers[number_index]
        number_index += 1


def spiral_coords(radius: int) -> list[tuple[int, int]]:
    if radius != 2:
        raise ValueError("Only the standard radius-2 island is supported right now.")
    return [
        (0, -2), (1, -2), (2, -2), (2, -1), (2, 0), (1, 1),
        (0, 2), (-1, 2), (-2, 2), (-2, 1), (-2, 0), (-1, -1),
        (0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0),
        (0, 0),
    ]


def score_layout(hexes: list[dict[str, Any]]) -> int:
    red_adjacencies = count_adjacent_pairs(hexes, lambda a, b: a.get("number") in {6, 8} and b.get("number") in {6, 8})
    same_resource_adjacencies = count_adjacent_pairs(
        hexes,
        lambda a, b: a["terrain"] == b["terrain"] and a["terrain"] != "desert",
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
    return count_adjacent_pairs(hexes, lambda a, b: a["terrain"] == b["terrain"] and a["terrain"] != "desert") > 0


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


def build_ports(rng: random.Random) -> list[dict[str, Any]]:
    types = list(PORT_TYPES)
    rng.shuffle(types)
    return [{"kind": kind, "slot": index} for index, kind in enumerate(types)]


def resolve_ports(port_specs: list[dict[str, Any]], edges: list[dict[str, Any]], vertices_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_edges = [edge for edge in edges if len(edge["hexes"]) == 1]
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


def edge_angle(edge: dict[str, Any], vertices_by_id: dict[str, dict[str, Any]]) -> float:
    a, b = edge["vertices"]
    ax, ay = vertices_by_id[a]["x"], vertices_by_id[a]["y"]
    bx, by = vertices_by_id[b]["x"], vertices_by_id[b]["y"]
    return math.atan2((ay + by) / 2, (ax + bx) / 2)
