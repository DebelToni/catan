import pytest

from app.game_engine import GameError, GameStore, RESOURCE_TYPES
from app.maps import generate_map, generate_standard_map, has_adjacent_same_resources, has_adjacent_red_numbers


def join_players(store, game, count=2):
    players = []
    colors = ["red", "blue", "green", "orange", "purple", "teal"]
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


def test_map_presets_include_crescent_seafarers_and_5_6_versions():
    expected_sizes = {
        "crescent": 19,
        "seafarers_gold": 31,
        "standard_56": 30,
        "crescent_56": 30,
        "seafarers_gold_56": 47,
    }
    for preset, size in expected_sizes.items():
        board = generate_map(preset, seed=preset)
        assert board["id"] == preset
        assert len(board["hexes"]) == size
        assert not has_adjacent_red_numbers(board["hexes"])
    seafarers = generate_map("seafarers_gold_56", seed="sea")
    assert any(hex_tile["terrain"] == "gold" for hex_tile in seafarers["hexes"])
    assert any(hex_tile["terrain"] == "sea" for hex_tile in seafarers["hexes"])
    assert any(hex_tile.get("hidden") for hex_tile in seafarers["hexes"])
    assert seafarers["players_5_6"] is True


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


def test_pirate_moves_to_sea_and_blocks_ship_placement():
    store = GameStore()
    game = store.create_game({"map_preset": "seafarers_gold", "map_seed": "pirate"})
    p1, p2 = join_players(store, game, 2)
    coastal_edge = next(edge for edge in game.board["edges"] if len(edge["hexes"]) == 1 and game.hex_by_id(edge["hexes"][0])["terrain"] != "sea")
    assert game.edge_touches_sea(coastal_edge["id"])
    sea_hex = next(hex_tile for hex_tile in game.board["hexes"] if hex_tile["terrain"] == "sea" and hex_tile["id"] != game.pirate_hex_id)
    sea_edge = sea_hex["edges"][0]
    game.roads[sea_edge] = p2.id
    p2.resources["ore"] = 1
    game.turn_stage = "move_robber"
    game.current_player_id = p1.id
    game.pending_robber = {"player_id": p1.id, "return_stage": "main"}
    game.move_robber(p1.id, sea_hex["id"], p2.id)
    assert game.pirate_hex_id == sea_hex["id"]
    assert p1.resources["ore"] == 1
    blocked_edge = next(edge_id for edge_id in sea_hex["edges"] if edge_id not in game.roads)
    with pytest.raises(GameError):
        game.validate_road(p1.id, blocked_edge)


def test_knight_returns_to_main_turn_after_robber_move():
    store = GameStore()
    game = store.create_game({"map_seed": "knight"})
    p1, _ = join_players(store, game, 2)
    game.phase = "playing"
    game.turn_stage = "main"
    game.current_player_id = p1.id
    game.turn_number = 2
    card = {"id": "k1", "type": "knight", "bought_turn": 1}
    p1.dev_cards.append(card)
    game.play_development_card(p1.id, card["id"])
    assert game.turn_stage == "move_robber"
    target = next(hex_tile for hex_tile in game.board["hexes"] if hex_tile["id"] != game.robber_hex_id and hex_tile["terrain"] != "sea")
    game.move_robber(p1.id, target["id"])
    assert game.turn_stage == "main"


def test_fog_reveals_when_ship_reaches_it():
    store = GameStore()
    game = store.create_game({"map_preset": "seafarers_gold", "map_seed": "fog"})
    p1, _ = join_players(store, game, 2)
    fog_hex = next(hex_tile for hex_tile in game.board["hexes"] if hex_tile.get("hidden"))
    public_before = next(hex_tile for hex_tile in game.public_board()["hexes"] if hex_tile["id"] == fog_hex["id"])
    assert public_before["terrain"] == "fog"
    assert public_before["number"] is None
    game.buildings[fog_hex["vertices"][0]] = {"player_id": p1.id, "type": "settlement"}
    game.distribute_resources(fog_hex["number"])
    assert sum(p1.resources.values()) == 0
    edge = fog_hex["edges"][0]
    game.reveal_fog_from_edge(edge, p1)
    public_after = next(hex_tile for hex_tile in game.public_board()["hexes"] if hex_tile["id"] == fog_hex["id"])
    assert fog_hex["revealed"] is True
    assert public_after["terrain"] == fog_hex["terrain"]


def test_five_six_uses_paired_player_turn():
    store = GameStore()
    game = store.create_game({"map_preset": "standard_56", "map_seed": "paired"})
    players = join_players(store, game, 6)
    game.phase = "playing"
    game.turn_stage = "main"
    game.current_player_id = players[0].id
    game.paired_primary_player_id = players[0].id
    game.paired_partner_player_id = players[3].id
    game.end_turn(players[0].id)
    assert game.turn_stage == "paired_build"
    assert game.current_player_id == players[3].id
    game.end_turn(players[3].id)
    assert game.turn_stage == "must_roll"
    assert game.current_player_id == players[1].id
    assert game.paired_partner_player_id == players[4].id


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
