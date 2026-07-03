import pytest

from app.game_engine import GameError, GameStore, RESOURCE_TYPES
from app.maps import generate_map, generate_standard_map, has_adjacent_same_resources, has_adjacent_red_numbers


def join_players(store, game, count=2):
    players = []
    colors = ["red", "blue", "green", "orange"]
    for index in range(count):
        _, player = store.join_game(game.id, f"P{index + 1}", colors[index])
        players.append(player)
    return players


def test_standard_map_distribution_and_red_numbers_not_adjacent():
    board = generate_standard_map(seed="rules")
    terrains = [hex_tile["terrain"] for hex_tile in board["hexes"]]
    assert len(board["hexes"]) == 19
    assert terrains.count("forest") == 4
    assert terrains.count("pasture") == 4
    assert terrains.count("field") == 4
    assert terrains.count("hill") == 3
    assert terrains.count("mountain") == 3
    assert terrains.count("desert") == 1
    assert sorted(hex_tile["number"] for hex_tile in board["hexes"] if hex_tile["number"]) == [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
    assert not has_adjacent_red_numbers(board["hexes"])
    assert not has_adjacent_same_resources(board["hexes"])


def test_map_presets_include_crescent_and_seafarers_gold():
    crescent = generate_map("crescent", seed="crescent")
    seafarers = generate_map("seafarers_gold", seed="sea")
    assert crescent["id"] == "crescent"
    assert seafarers["id"] == "seafarers_gold"
    assert any(hex_tile["terrain"] == "gold" for hex_tile in seafarers["hexes"])
    assert any(hex_tile["terrain"] == "sea" for hex_tile in seafarers["hexes"])
    assert not has_adjacent_red_numbers(crescent["hexes"])
    assert not has_adjacent_red_numbers(seafarers["hexes"])


def test_settlement_distance_rule_blocks_adjacent_intersection():
    store = GameStore()
    game = store.create_game({"map_seed": "distance"})
    p1, p2 = join_players(store, game, 2)
    game.start(p1.id)
    first_vertex = game.board["vertices"][0]["id"]
    game.build(p1.id, "settlement", first_vertex)
    adjacent = game.board["vertex_neighbors"][first_vertex][0]
    with pytest.raises(GameError):
        game.validate_settlement(p2.id, adjacent, setup=True)


def test_second_setup_settlement_grants_starting_resources():
    store = GameStore()
    game = store.create_game({"map_seed": "initial"})
    p1, p2 = join_players(store, game, 2)
    game.start(p1.id)
    complete_setup_slot(game, p1.id)
    complete_setup_slot(game, p2.id)
    complete_setup_slot(game, p2.id)
    before = sum(p2.resources.values())
    assert before > 0


def test_gold_tile_requires_resource_choice():
    store = GameStore()
    game = store.create_game({"map_preset": "seafarers_gold", "map_seed": "gold"})
    p1, _ = join_players(store, game, 2)
    hex_tile = next(hex_tile for hex_tile in game.board["hexes"] if hex_tile["terrain"] == "gold" and hex_tile["number"])
    game.buildings[hex_tile["vertices"][0]] = {"player_id": p1.id, "type": "settlement"}
    game.distribute_resources(hex_tile["number"])
    assert game.pending_gold[p1.id] == 1
    game.turn_stage = "gold_choice"
    game.choose_gold_resources(p1.id, {"ore": 1})
    assert game.pending_gold == {}
    assert p1.resources["ore"] == 1


def test_production_skips_robber_tile():
    store = GameStore()
    game = store.create_game({"map_seed": "production"})
    p1, _ = join_players(store, game, 2)
    hex_tile = next(hex_tile for hex_tile in game.board["hexes"] if hex_tile["number"] and hex_tile["terrain"] != "desert")
    vertex = hex_tile["vertices"][0]
    game.buildings[vertex] = {"player_id": p1.id, "type": "settlement"}
    game.robber_hex_id = hex_tile["id"]
    game.distribute_resources(hex_tile["number"])
    assert sum(p1.resources.values()) == 0
    game.robber_hex_id = next(item["id"] for item in game.board["hexes"] if item["terrain"] == "desert")
    game.distribute_resources(hex_tile["number"])
    assert sum(p1.resources.values()) == 1


def test_longest_road_awarded_at_five_edges():
    store = GameStore()
    game = store.create_game({"map_seed": "road"})
    p1, _ = join_players(store, game, 2)
    path_edges = find_path_edges(game, 5)
    for edge in path_edges:
        game.roads[edge] = p1.id
    game.update_longest_road()
    assert game.longest_road_holder == p1.id
    assert game.longest_road_size >= 5


def complete_setup_slot(game, player_id):
    vertex = next(vertex["id"] for vertex in game.board["vertices"] if vertex["id"] not in game.buildings and not any(neighbor in game.buildings for neighbor in game.board["vertex_neighbors"][vertex["id"]]))
    game.build(player_id, "settlement", vertex)
    edge = next(edge_id for edge_id in game.board["vertex_edges"][vertex] if edge_id not in game.roads)
    game.build(player_id, "road", edge)


def find_path_edges(game, length):
    edges_by_vertex = game.board["vertex_edges"]
    edges_by_id = game.board["edges_by_id"]

    def dfs(vertex, used, path):
        if len(path) == length:
            return path
        for edge_id in edges_by_vertex[vertex]:
            if edge_id in used:
                continue
            a, b = edges_by_id[edge_id]["vertices"]
            result = dfs(b if a == vertex else a, used | {edge_id}, path + [edge_id])
            if result:
                return result
        return None

    for vertex in game.board["vertices_by_id"]:
        result = dfs(vertex, set(), [])
        if result:
            return result
    raise AssertionError("No path found")
