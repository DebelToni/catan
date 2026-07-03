from __future__ import annotations

import random
import string
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .maps import generate_map, list_map_presets

RESOURCE_TYPES = ["lumber", "brick", "wool", "grain", "ore"]
TERRAIN_TO_RESOURCE = {
    "forest": "lumber",
    "hill": "brick",
    "pasture": "wool",
    "field": "grain",
    "mountain": "ore",
}
BUILD_COSTS = {
    "road": {"lumber": 1, "brick": 1},
    "ship": {"lumber": 1, "wool": 1},
    "settlement": {"lumber": 1, "brick": 1, "wool": 1, "grain": 1},
    "city": {"grain": 2, "ore": 3},
    "development": {"wool": 1, "grain": 1, "ore": 1},
}
PLAYER_COLORS = [
    {"id": "red", "name": "Red", "hex": "#e63946"},
    {"id": "blue", "name": "Blue", "hex": "#277da1"},
    {"id": "orange", "name": "Orange", "hex": "#f3722c"},
    {"id": "white", "name": "White", "hex": "#f8f9fa"},
    {"id": "green", "name": "Green", "hex": "#43aa8b"},
    {"id": "purple", "name": "Purple", "hex": "#9b5de5"},
    {"id": "black", "name": "Black", "hex": "#242423"},
    {"id": "pink", "name": "Pink", "hex": "#ff70a6"},
    {"id": "yellow", "name": "Yellow", "hex": "#f9c74f"},
    {"id": "teal", "name": "Teal", "hex": "#00b4d8"},
]
DEFAULT_SETTINGS = {
    "points_to_win": 10,
    "hand_limit": 7,
    "turn_timer_seconds": 0,
    "friendly_robber": False,
    "random_map": True,
    "map_seed": "",
    "allow_spectators": True,
    "map_preset": "standard",
}
DEV_DECK_TEMPLATE = (
    ["knight"] * 14
    + ["road_building"] * 2
    + ["year_of_plenty"] * 2
    + ["monopoly"] * 2
    + ["victory_point"] * 5
)


class GameError(Exception):
    pass


def empty_resources() -> dict[str, int]:
    return {resource: 0 for resource in RESOURCE_TYPES}


def resource_total(resources: dict[str, int]) -> int:
    return sum(int(resources.get(resource, 0)) for resource in RESOURCE_TYPES)


def short_id(length: int = 5) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def public_color(color_id: str) -> str:
    return next((color["hex"] for color in PLAYER_COLORS if color["id"] == color_id), "#888888")


@dataclass
class Player:
    id: str
    name: str
    color: str
    order: int
    host: bool = False
    connected: bool = True
    resources: dict[str, int] = field(default_factory=empty_resources)
    dev_cards: list[dict[str, Any]] = field(default_factory=list)
    knights_played: int = 0
    dev_played_turn: int | None = None
    joined_at: float = field(default_factory=time.time)


@dataclass
class Game:
    id: str
    settings: dict[str, Any]
    board: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    players: dict[str, Player] = field(default_factory=dict)
    phase: str = "lobby"
    turn_stage: str = "lobby"
    setup_steps: list[dict[str, Any]] = field(default_factory=list)
    setup_index: int = 0
    setup_action: str = "settlement"
    setup_last_vertex: str | None = None
    current_player_id: str | None = None
    turn_number: int = 0
    roads: dict[str, str] = field(default_factory=dict)
    buildings: dict[str, dict[str, str]] = field(default_factory=dict)
    bank: dict[str, int] = field(default_factory=lambda: {resource: 19 for resource in RESOURCE_TYPES})
    dev_deck: list[dict[str, Any]] = field(default_factory=list)
    robber_hex_id: str = ""
    dice_history: list[dict[str, Any]] = field(default_factory=list)
    last_roll: dict[str, Any] | None = None
    pending_discards: dict[str, int] = field(default_factory=dict)
    pending_robber: dict[str, Any] | None = None
    pending_gold: dict[str, int] = field(default_factory=dict)
    free_roads_remaining: int = 0
    largest_army_holder: str | None = None
    largest_army_size: int = 0
    longest_road_holder: str | None = None
    longest_road_size: int = 0
    trade_offers: list[dict[str, Any]] = field(default_factory=list)
    chat: list[dict[str, Any]] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    winner: str | None = None

    @property
    def ordered_players(self) -> list[Player]:
        return sorted(self.players.values(), key=lambda player: player.order)

    @property
    def active_player(self) -> Player:
        if not self.current_player_id or self.current_player_id not in self.players:
            raise GameError("No active player.")
        return self.players[self.current_player_id]

    def add_log(self, text: str) -> None:
        self.log.append(text)
        self.log = self.log[-120:]

    def get_player(self, player_id: str) -> Player:
        if player_id not in self.players:
            raise GameError("Player is not in this game.")
        return self.players[player_id]

    def require_active(self, player_id: str) -> Player:
        if self.winner:
            raise GameError("The game is already over.")
        if player_id != self.current_player_id:
            raise GameError("It is not your turn.")
        return self.get_player(player_id)

    def start(self, player_id: str) -> None:
        if self.phase != "lobby":
            raise GameError("Game has already started.")
        starter = self.get_player(player_id)
        if not starter.host:
            raise GameError("Only the host can start the game.")
        if len(self.players) < 2:
            raise GameError("At least 2 players are required.")
        ordered = self.ordered_players
        self.setup_steps = [
            {"player_id": player.id, "round": 1} for player in ordered
        ] + [
            {"player_id": player.id, "round": 2} for player in reversed(ordered)
        ]
        self.setup_index = 0
        self.setup_action = "settlement"
        self.setup_last_vertex = None
        self.phase = "setup"
        self.turn_stage = "setup"
        self.current_player_id = self.setup_steps[0]["player_id"]
        self.add_log("Setup started: place settlements and roads in snake order.")

    def roll_dice(self, player_id: str) -> dict[str, Any]:
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage != "must_roll":
            raise GameError("Roll at the start of your turn.")
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        roll = {"die1": die1, "die2": die2, "total": total, "turn": self.turn_number}
        self.last_roll = roll
        self.dice_history.append(roll)
        self.dice_history = self.dice_history[-30:]
        self.add_log(f"{player.name} rolled {die1}+{die2}={total}.")
        if total == 7:
            self.pending_discards = {}
            limit = int(self.settings.get("hand_limit", 7))
            for other in self.ordered_players:
                count = resource_total(other.resources)
                if count > limit:
                    self.pending_discards[other.id] = count // 2
            if self.pending_discards:
                self.turn_stage = "discard"
                self.add_log("Players over the hand limit must discard half their cards.")
            else:
                self.turn_stage = "move_robber"
                self.pending_robber = {"player_id": player.id, "reason": "roll_7"}
                self.add_log(f"{player.name} must move the robber.")
        else:
            self.distribute_resources(total)
            self.turn_stage = "gold_choice" if self.pending_gold else "main"
        return roll

    def distribute_resources(self, number: int) -> None:
        produced: list[str] = []
        for hex_tile in self.board["hexes"]:
            if hex_tile.get("number") != number or hex_tile["id"] == self.robber_hex_id:
                continue
            resource = TERRAIN_TO_RESOURCE.get(hex_tile["terrain"])
            if not resource and hex_tile["terrain"] != "gold":
                continue
            for vertex_id in hex_tile["vertices"]:
                building = self.buildings.get(vertex_id)
                if not building:
                    continue
                player = self.players[building["player_id"]]
                amount = 2 if building["type"] == "city" else 1
                if hex_tile["terrain"] == "gold":
                    self.pending_gold[player.id] = self.pending_gold.get(player.id, 0) + amount
                    produced.append(f"{player.name} chooses {amount} gold resource")
                    continue
                available = self.bank.get(resource, 0)
                if available <= 0:
                    continue
                amount = min(amount, available)
                player.resources[resource] += amount
                self.bank[resource] -= amount
                produced.append(f"{player.name} +{amount} {resource}")
        self.add_log("Production: " + (", ".join(produced) if produced else "nothing produced."))

    def choose_gold_resources(self, player_id: str, resources: dict[str, int]) -> None:
        if self.turn_stage != "gold_choice" or player_id not in self.pending_gold:
            raise GameError("You do not need to choose gold resources right now.")
        player = self.get_player(player_id)
        clean = clean_resource_dict(resources)
        required = self.pending_gold[player_id]
        if resource_total(clean) != required:
            raise GameError(f"Choose exactly {required} resources for gold production.")
        for resource, amount in clean.items():
            if self.bank.get(resource, 0) < amount:
                raise GameError(f"The bank does not have enough {resource}.")
        for resource, amount in clean.items():
            player.resources[resource] += amount
            self.bank[resource] -= amount
        del self.pending_gold[player_id]
        self.add_log(f"{player.name} chose {required} gold resources.")
        if not self.pending_gold:
            self.turn_stage = "main"

    def discard(self, player_id: str, resources: dict[str, int]) -> None:
        if self.turn_stage != "discard" or player_id not in self.pending_discards:
            raise GameError("You do not need to discard right now.")
        player = self.get_player(player_id)
        clean = clean_resource_dict(resources)
        required = self.pending_discards[player_id]
        if resource_total(clean) != required:
            raise GameError(f"Discard exactly {required} cards.")
        ensure_has(player, clean)
        pay_to_bank(self, player, clean)
        del self.pending_discards[player_id]
        self.add_log(f"{player.name} discarded {required} cards.")
        if not self.pending_discards:
            self.turn_stage = "move_robber"
            self.pending_robber = {"player_id": self.current_player_id, "reason": "roll_7"}
            self.add_log(f"{self.active_player.name} must move the robber.")

    def move_robber(self, player_id: str, hex_id: str, victim_id: str | None = None) -> None:
        if self.turn_stage != "move_robber" or not self.pending_robber:
            raise GameError("The robber is not being moved right now.")
        if self.pending_robber["player_id"] != player_id:
            raise GameError("Only the robber mover can choose the tile.")
        if hex_id == self.robber_hex_id:
            raise GameError("Move the robber to a different tile.")
        hex_tile = self.hex_by_id(hex_id)
        if hex_tile["terrain"] == "sea":
            raise GameError("Move the robber to a land tile.")
        adjacent_player_ids = self.players_on_hex(hex_id)
        possible_victims = [pid for pid in adjacent_player_ids if pid != player_id and resource_total(self.players[pid].resources) > 0]
        if self.settings.get("friendly_robber"):
            possible_victims = [pid for pid in possible_victims if self.victory_points(pid, public_only=True) > 2]
        if victim_id:
            if victim_id not in possible_victims:
                raise GameError("That player cannot be robbed from this tile.")
        elif possible_victims:
            victim_id = random.choice(possible_victims)
        self.robber_hex_id = hex_id
        mover = self.get_player(player_id)
        if victim_id:
            victim = self.get_player(victim_id)
            stolen = steal_random_resource(victim)
            if stolen:
                mover.resources[stolen] += 1
                self.add_log(f"{mover.name} moved the robber to {hex_tile['terrain']} and stole from {victim.name}.")
            else:
                self.add_log(f"{mover.name} moved the robber to {hex_tile['terrain']}.")
        else:
            self.add_log(f"{mover.name} moved the robber to {hex_tile['terrain']}.")
        self.pending_robber = None
        self.turn_stage = "main"
        self.check_winner(player_id)

    def build(self, player_id: str, build_type: str, target_id: str) -> None:
        if build_type not in {"road", "settlement", "city"}:
            raise GameError("Unknown build type.")
        if self.phase == "setup":
            self.setup_build(player_id, build_type, target_id)
            return
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage not in {"main", "road_building"}:
            raise GameError("You cannot build right now.")
        if build_type != "road" and self.turn_stage == "road_building":
            raise GameError("Place the free roads before doing anything else.")
        free_road = self.turn_stage == "road_building" and build_type == "road"
        if build_type == "road":
            self.validate_road(player_id, target_id)
            if not free_road:
                cost = BUILD_COSTS["ship"] if self.edge_touches_sea(target_id) else BUILD_COSTS["road"]
                ensure_has(player, cost)
                pay_to_bank(self, player, cost)
            self.roads[target_id] = player_id
            self.add_log(f"{player.name} built a {'ship' if self.edge_touches_sea(target_id) else 'road'}.")
            if free_road:
                self.free_roads_remaining -= 1
                if self.free_roads_remaining <= 0:
                    self.turn_stage = "main"
            self.update_longest_road()
        elif build_type == "settlement":
            self.validate_settlement(player_id, target_id, setup=False)
            ensure_has(player, BUILD_COSTS["settlement"])
            pay_to_bank(self, player, BUILD_COSTS["settlement"])
            self.buildings[target_id] = {"player_id": player_id, "type": "settlement"}
            self.add_log(f"{player.name} built a settlement.")
            self.update_longest_road()
        else:
            building = self.buildings.get(target_id)
            if not building or building["player_id"] != player_id or building["type"] != "settlement":
                raise GameError("Select one of your settlements to upgrade.")
            ensure_has(player, BUILD_COSTS["city"])
            pay_to_bank(self, player, BUILD_COSTS["city"])
            building["type"] = "city"
            self.add_log(f"{player.name} upgraded to a city.")
        self.check_winner(player_id)

    def setup_build(self, player_id: str, build_type: str, target_id: str) -> None:
        if self.phase != "setup" or self.current_player_id != player_id:
            raise GameError("It is not your setup placement.")
        step = self.setup_steps[self.setup_index]
        player = self.get_player(player_id)
        if self.setup_action == "settlement":
            if build_type != "settlement":
                raise GameError("Place a settlement first.")
            self.validate_settlement(player_id, target_id, setup=True)
            self.buildings[target_id] = {"player_id": player_id, "type": "settlement"}
            self.setup_last_vertex = target_id
            self.setup_action = "road"
            if step["round"] == 2:
                self.grant_initial_resources(player, target_id)
            self.add_log(f"{player.name} placed a setup settlement.")
        else:
            if build_type != "road":
                raise GameError("Place a road from your new settlement.")
            self.validate_setup_road(player_id, target_id)
            self.roads[target_id] = player_id
            self.add_log(f"{player.name} placed a setup road.")
            self.update_longest_road()
            self.setup_index += 1
            self.setup_action = "settlement"
            self.setup_last_vertex = None
            if self.setup_index >= len(self.setup_steps):
                self.phase = "playing"
                self.turn_stage = "must_roll"
                self.current_player_id = self.ordered_players[0].id
                self.turn_number = 1
                self.add_log(f"Setup complete. {self.active_player.name} starts.")
            else:
                self.current_player_id = self.setup_steps[self.setup_index]["player_id"]

    def grant_initial_resources(self, player: Player, vertex_id: str) -> None:
        gained: list[str] = []
        vertex = self.board["vertices_by_id"][vertex_id]
        for hex_id in vertex["hexes"]:
            hex_tile = self.hex_by_id(hex_id)
            resource = TERRAIN_TO_RESOURCE.get(hex_tile["terrain"])
            if resource and self.bank[resource] > 0:
                player.resources[resource] += 1
                self.bank[resource] -= 1
                gained.append(resource)
        if gained:
            self.add_log(f"{player.name} took starting resources: {', '.join(gained)}.")

    def validate_settlement(self, player_id: str, vertex_id: str, setup: bool) -> None:
        if vertex_id not in self.board["vertices_by_id"]:
            raise GameError("Unknown intersection.")
        if not self.vertex_touches_land(vertex_id):
            raise GameError("Settlements must touch land.")
        if vertex_id in self.buildings:
            raise GameError("That intersection is occupied.")
        for neighbor in self.board["vertex_neighbors"].get(vertex_id, []):
            if neighbor in self.buildings:
                raise GameError("Settlements must be at least two roads apart.")
        if not setup:
            if not any(self.roads.get(edge_id) == player_id for edge_id in self.board["vertex_edges"].get(vertex_id, [])):
                raise GameError("A new settlement must connect to your road.")

    def validate_setup_road(self, player_id: str, edge_id: str) -> None:
        if edge_id not in self.board["edges_by_id"]:
            raise GameError("Unknown road edge.")
        if edge_id in self.roads:
            raise GameError("That edge already has a road.")
        vertices = self.board["edges_by_id"][edge_id]["vertices"]
        if self.setup_last_vertex not in vertices:
            raise GameError("Setup roads must touch the settlement just placed.")

    def validate_road(self, player_id: str, edge_id: str) -> None:
        if edge_id not in self.board["edges_by_id"]:
            raise GameError("Unknown road edge.")
        if edge_id in self.roads:
            raise GameError("That edge already has a road.")
        edge = self.board["edges_by_id"][edge_id]
        if not any(self.can_connect_road_from_vertex(player_id, vertex_id, edge_id) for vertex_id in edge["vertices"]):
            raise GameError("Roads must connect to your road network or building.")

    def can_connect_road_from_vertex(self, player_id: str, vertex_id: str, ignored_edge: str) -> bool:
        building = self.buildings.get(vertex_id)
        if building and building["player_id"] != player_id:
            return False
        if building and building["player_id"] == player_id:
            return True
        return any(
            edge_id != ignored_edge and self.roads.get(edge_id) == player_id
            for edge_id in self.board["vertex_edges"].get(vertex_id, [])
        )

    def buy_development_card(self, player_id: str) -> None:
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Buy development cards during your main turn.")
        if not self.dev_deck:
            raise GameError("The development deck is empty.")
        ensure_has(player, BUILD_COSTS["development"])
        pay_to_bank(self, player, BUILD_COSTS["development"])
        card = self.dev_deck.pop()
        card = {**card, "bought_turn": self.turn_number}
        player.dev_cards.append(card)
        self.add_log(f"{player.name} bought a development card.")
        self.check_winner(player_id)

    def play_development_card(self, player_id: str, card_id: str, payload: dict[str, Any] | None = None) -> None:
        player = self.require_active(player_id)
        payload = payload or {}
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Play development cards during your main turn.")
        card = next((card for card in player.dev_cards if card["id"] == card_id), None)
        if not card:
            raise GameError("You do not have that development card.")
        if card["type"] == "victory_point":
            raise GameError("Victory point cards score automatically and stay hidden.")
        if card.get("bought_turn") == self.turn_number:
            raise GameError("You cannot play a development card on the turn you bought it.")
        if player.dev_played_turn == self.turn_number:
            raise GameError("You can play only one development card per turn.")
        card_type = card["type"]
        resources = None
        monopoly_resource = None
        if card_type == "year_of_plenty":
            resources = clean_resource_dict(payload.get("resources", {}))
            if resource_total(resources) != 2:
                raise GameError("Year of Plenty takes exactly two resources.")
        elif card_type == "monopoly":
            monopoly_resource = payload.get("resource")
            if monopoly_resource not in RESOURCE_TYPES:
                raise GameError("Choose a resource for Monopoly.")
        elif card_type not in {"knight", "road_building"}:
            raise GameError("Unknown development card.")

        player.dev_cards.remove(card)
        player.dev_played_turn = self.turn_number
        if card_type == "knight":
            player.knights_played += 1
            self.update_largest_army(player_id)
            self.turn_stage = "move_robber"
            self.pending_robber = {"player_id": player_id, "reason": "knight"}
            self.add_log(f"{player.name} played a Knight.")
        elif card_type == "road_building":
            self.free_roads_remaining = 2
            self.turn_stage = "road_building"
            self.add_log(f"{player.name} played Road Building.")
        elif card_type == "year_of_plenty":
            assert resources is not None
            for resource, amount in resources.items():
                amount = min(amount, self.bank.get(resource, 0))
                player.resources[resource] += amount
                self.bank[resource] -= amount
            self.add_log(f"{player.name} played Year of Plenty.")
        elif card_type == "monopoly":
            assert monopoly_resource is not None
            total = 0
            for other in self.ordered_players:
                if other.id == player_id:
                    continue
                amount = other.resources[monopoly_resource]
                other.resources[monopoly_resource] = 0
                total += amount
            player.resources[monopoly_resource] += total
            self.add_log(f"{player.name} monopolized {total} {monopoly_resource}.")
        self.check_winner(player_id)

    def bank_trade(self, player_id: str, give: str, receive: str) -> None:
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Trade with the bank during your main turn.")
        if give not in RESOURCE_TYPES or receive not in RESOURCE_TYPES or give == receive:
            raise GameError("Choose two different resources.")
        rate = self.bank_trade_rate(player_id, give)
        if player.resources[give] < rate:
            raise GameError(f"You need {rate} {give} for that bank trade.")
        if self.bank[receive] <= 0:
            raise GameError("The bank is out of that resource.")
        player.resources[give] -= rate
        self.bank[give] += rate
        player.resources[receive] += 1
        self.bank[receive] -= 1
        self.add_log(f"{player.name} traded {rate} {give} with the bank for 1 {receive}.")

    def bank_trade_rate(self, player_id: str, resource: str) -> int:
        rate = 4
        for port in self.board.get("ports", []):
            vertices = self.board["edges_by_id"][port["edge_id"]]["vertices"]
            owns_port = any(
                self.buildings.get(vertex_id, {}).get("player_id") == player_id
                for vertex_id in vertices
            )
            if not owns_port:
                continue
            if port["kind"] == "3:1":
                rate = min(rate, 3)
            elif port["kind"] == resource:
                rate = min(rate, 2)
        return rate

    def create_trade_offer(self, player_id: str, give: dict[str, int], receive: dict[str, int]) -> None:
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Create trades during your main turn.")
        give = clean_resource_dict(give)
        receive = clean_resource_dict(receive)
        if resource_total(give) <= 0 or resource_total(receive) <= 0:
            raise GameError("Trade offers need cards on both sides.")
        ensure_has(player, give)
        offer = {
            "id": short_id(6),
            "from_player_id": player_id,
            "give": give,
            "receive": receive,
            "created_at": time.time(),
        }
        self.trade_offers.append(offer)
        self.add_log(f"{player.name} offered a trade.")

    def accept_trade_offer(self, player_id: str, offer_id: str) -> None:
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Trades resolve during the active player's main turn.")
        offer = next((offer for offer in self.trade_offers if offer["id"] == offer_id), None)
        if not offer:
            raise GameError("Trade offer not found.")
        if player_id == offer["from_player_id"]:
            raise GameError("You cannot accept your own offer.")
        proposer = self.get_player(offer["from_player_id"])
        accepter = self.get_player(player_id)
        ensure_has(proposer, offer["give"])
        ensure_has(accepter, offer["receive"])
        transfer(proposer.resources, accepter.resources, offer["give"])
        transfer(accepter.resources, proposer.resources, offer["receive"])
        self.trade_offers = [item for item in self.trade_offers if item["id"] != offer_id]
        self.add_log(f"{accepter.name} accepted {proposer.name}'s trade.")

    def cancel_trade_offer(self, player_id: str, offer_id: str) -> None:
        before = len(self.trade_offers)
        self.trade_offers = [
            offer for offer in self.trade_offers
            if not (offer["id"] == offer_id and offer["from_player_id"] == player_id)
        ]
        if len(self.trade_offers) == before:
            raise GameError("Trade offer not found.")

    def end_turn(self, player_id: str) -> None:
        player = self.require_active(player_id)
        if self.phase != "playing" or self.turn_stage != "main":
            raise GameError("Finish pending actions before ending your turn.")
        self.trade_offers = [offer for offer in self.trade_offers if offer["from_player_id"] != player_id]
        ordered = self.ordered_players
        current_index = next(index for index, other in enumerate(ordered) if other.id == player_id)
        next_player = ordered[(current_index + 1) % len(ordered)]
        self.current_player_id = next_player.id
        self.turn_stage = "must_roll"
        self.turn_number += 1
        self.last_roll = None
        self.add_log(f"{player.name} ended turn. {next_player.name} is up.")

    def add_chat(self, player_id: str, text: str) -> None:
        player = self.get_player(player_id)
        text = str(text).strip()[:300]
        if not text:
            return
        self.chat.append({"player_id": player_id, "name": player.name, "text": text, "time": time.time()})
        self.chat = self.chat[-80:]

    def hex_by_id(self, hex_id: str) -> dict[str, Any]:
        try:
            return self.board["hexes_by_id"][hex_id]
        except KeyError as exc:
            raise GameError("Unknown tile.") from exc

    def vertex_touches_land(self, vertex_id: str) -> bool:
        vertex = self.board["vertices_by_id"][vertex_id]
        return any(self.hex_by_id(hex_id)["terrain"] != "sea" for hex_id in vertex["hexes"])

    def edge_touches_sea(self, edge_id: str) -> bool:
        edge = self.board["edges_by_id"][edge_id]
        return any(self.hex_by_id(hex_id)["terrain"] == "sea" for hex_id in edge["hexes"])

    def players_on_hex(self, hex_id: str) -> list[str]:
        hex_tile = self.hex_by_id(hex_id)
        player_ids = []
        for vertex_id in hex_tile["vertices"]:
            building = self.buildings.get(vertex_id)
            if building and building["player_id"] not in player_ids:
                player_ids.append(building["player_id"])
        return player_ids

    def update_largest_army(self, player_id: str) -> None:
        player = self.get_player(player_id)
        if player.knights_played >= 3 and player.knights_played > self.largest_army_size:
            self.largest_army_holder = player_id
            self.largest_army_size = player.knights_played
            self.add_log(f"{player.name} claimed Largest Army.")

    def update_longest_road(self) -> None:
        lengths = {player.id: self.longest_road_for(player.id) for player in self.ordered_players}
        self.longest_road_size = lengths.get(self.longest_road_holder or "", 0)
        max_length = max(lengths.values(), default=0)
        contenders = [pid for pid, length in lengths.items() if length == max_length and length >= 5]
        if not contenders:
            self.longest_road_holder = None
            self.longest_road_size = 0
            return
        if self.longest_road_holder in contenders:
            self.longest_road_size = max_length
            return
        if len(contenders) == 1:
            self.longest_road_holder = contenders[0]
            self.longest_road_size = max_length
            self.add_log(f"{self.players[contenders[0]].name} claimed Longest Road ({max_length}).")

    def longest_road_for(self, player_id: str) -> int:
        owned_edges = {edge_id for edge_id, owner in self.roads.items() if owner == player_id}
        if not owned_edges:
            return 0
        edge_vertices = {edge_id: self.board["edges_by_id"][edge_id]["vertices"] for edge_id in owned_edges}
        vertex_edges: dict[str, list[str]] = {}
        for edge_id, vertices in edge_vertices.items():
            for vertex_id in vertices:
                vertex_edges.setdefault(vertex_id, []).append(edge_id)

        def blocked(vertex_id: str) -> bool:
            building = self.buildings.get(vertex_id)
            return bool(building and building["player_id"] != player_id)

        def dfs(vertex_id: str, used_edges: set[str]) -> int:
            if used_edges and blocked(vertex_id):
                return 0
            best = 0
            for edge_id in vertex_edges.get(vertex_id, []):
                if edge_id in used_edges:
                    continue
                a, b = edge_vertices[edge_id]
                next_vertex = b if a == vertex_id else a
                best = max(best, 1 + dfs(next_vertex, used_edges | {edge_id}))
            return best

        return max(dfs(vertex_id, set()) for vertex_id in vertex_edges)

    def victory_points(self, player_id: str, public_only: bool = False) -> int:
        points = 0
        for building in self.buildings.values():
            if building["player_id"] == player_id:
                points += 2 if building["type"] == "city" else 1
        if self.longest_road_holder == player_id:
            points += 2
        if self.largest_army_holder == player_id:
            points += 2
        if not public_only:
            player = self.get_player(player_id)
            points += sum(1 for card in player.dev_cards if card["type"] == "victory_point")
        return points

    def check_winner(self, player_id: str) -> None:
        if self.phase == "playing" and self.victory_points(player_id) >= int(self.settings.get("points_to_win", 10)):
            self.winner = player_id
            self.phase = "game_over"
            self.turn_stage = "game_over"
            self.add_log(f"{self.players[player_id].name} wins!")

    def serialize(self, viewer_id: str | None = None) -> dict[str, Any]:
        players = []
        for player in self.ordered_players:
            players.append({
                "id": player.id,
                "name": player.name,
                "color": player.color,
                "color_hex": public_color(player.color),
                "order": player.order,
                "host": player.host,
                "connected": player.connected,
                "resource_count": resource_total(player.resources),
                "dev_count": len(player.dev_cards),
                "knights_played": player.knights_played,
                "public_vp": self.victory_points(player.id, public_only=True),
                "total_vp": self.victory_points(player.id) if player.id == viewer_id or self.winner else None,
                "longest_road": self.longest_road_for(player.id),
            })
        you = None
        if viewer_id in self.players:
            viewer = self.players[viewer_id]
            you = {
                "id": viewer.id,
                "resources": deepcopy(viewer.resources),
                "dev_cards": [deepcopy(card) for card in viewer.dev_cards],
                "bank_rates": {resource: self.bank_trade_rate(viewer.id, resource) for resource in RESOURCE_TYPES},
            }
        setup = None
        if self.phase == "setup" and self.setup_steps:
            setup = {
                "player_id": self.current_player_id,
                "action": self.setup_action,
                "round": self.setup_steps[self.setup_index]["round"],
                "last_vertex": self.setup_last_vertex,
            }
        return {
            "game_id": self.id,
            "settings": deepcopy(self.settings),
            "phase": self.phase,
            "turn_stage": self.turn_stage,
            "setup": setup,
            "current_player_id": self.current_player_id,
            "turn_number": self.turn_number,
            "players": players,
            "you": you,
            "board": self.public_board(),
            "pieces": {"roads": deepcopy(self.roads), "buildings": deepcopy(self.buildings)},
            "robber_hex_id": self.robber_hex_id,
            "dice_history": deepcopy(self.dice_history),
            "last_roll": deepcopy(self.last_roll),
            "pending_discards": deepcopy(self.pending_discards),
            "pending_robber": deepcopy(self.pending_robber),
            "pending_gold": deepcopy(self.pending_gold),
            "free_roads_remaining": self.free_roads_remaining,
            "largest_army_holder": self.largest_army_holder,
            "largest_army_size": self.largest_army_size,
            "longest_road_holder": self.longest_road_holder,
            "longest_road_size": self.longest_road_size,
            "trade_offers": deepcopy(self.trade_offers),
            "chat": deepcopy(self.chat),
            "log": self.log[-80:],
            "winner": self.winner,
            "colors": PLAYER_COLORS,
            "map_presets": list_map_presets(),
        }

    def public_board(self) -> dict[str, Any]:
        return {
            "id": self.board["id"],
            "name": self.board["name"],
            "hexes": self.board["hexes"],
            "vertices": self.board["vertices"],
            "edges": self.board["edges"],
            "ports": self.board.get("ports", []),
            "uses_ships": self.board.get("uses_ships", False),
            "uses_gold": self.board.get("uses_gold", False),
        }


def clean_resource_dict(resources: dict[str, Any]) -> dict[str, int]:
    clean = empty_resources()
    for resource in RESOURCE_TYPES:
        try:
            clean[resource] = max(0, int(resources.get(resource, 0)))
        except (TypeError, ValueError):
            clean[resource] = 0
    return clean


def ensure_has(player: Player, cost: dict[str, int]) -> None:
    for resource, amount in cost.items():
        if player.resources.get(resource, 0) < amount:
            raise GameError(f"Not enough {resource}.")


def pay_to_bank(game: Game, player: Player, cost: dict[str, int]) -> None:
    for resource, amount in cost.items():
        player.resources[resource] -= amount
        game.bank[resource] += amount


def transfer(source: dict[str, int], target: dict[str, int], resources: dict[str, int]) -> None:
    for resource, amount in resources.items():
        source[resource] -= amount
        target[resource] += amount


def steal_random_resource(victim: Player) -> str | None:
    cards = [resource for resource, amount in victim.resources.items() for _ in range(amount)]
    if not cards:
        return None
    resource = random.choice(cards)
    victim.resources[resource] -= 1
    return resource


class GameStore:
    def __init__(self) -> None:
        self.games: dict[str, Game] = {}

    def create_game(self, settings: dict[str, Any] | None = None) -> Game:
        merged = {**DEFAULT_SETTINGS, **(settings or {})}
        merged["points_to_win"] = clamp_int(merged.get("points_to_win"), 1, 30, 10)
        merged["hand_limit"] = clamp_int(merged.get("hand_limit"), 1, 30, 7)
        merged["turn_timer_seconds"] = clamp_int(merged.get("turn_timer_seconds"), 0, 600, 0)
        merged["friendly_robber"] = bool(merged.get("friendly_robber"))
        merged["random_map"] = bool(merged.get("random_map", True))
        merged["allow_spectators"] = bool(merged.get("allow_spectators", True))
        preset_ids = {preset["id"] for preset in list_map_presets()}
        if merged.get("map_preset") not in preset_ids:
            merged["map_preset"] = "standard"
        seed = str(merged.get("map_seed") or "").strip()
        if not seed and merged["random_map"]:
            seed = short_id(8)
        merged["map_seed"] = seed
        board = generate_map(merged["map_preset"], seed=seed or merged["map_preset"])
        game_id = short_id()
        while game_id in self.games:
            game_id = short_id()
        dev_deck = [{"id": short_id(8), "type": card_type} for card_type in DEV_DECK_TEMPLATE]
        random.Random(seed or game_id).shuffle(dev_deck)
        game = Game(id=game_id, settings=merged, board=board, dev_deck=dev_deck)
        desert = next(hex_tile for hex_tile in board["hexes"] if hex_tile["terrain"] == "desert")
        game.robber_hex_id = desert["id"]
        self.games[game_id] = game
        return game

    def get(self, game_id: str) -> Game:
        game_id = str(game_id).upper().strip()
        if game_id not in self.games:
            raise GameError("Game not found.")
        return self.games[game_id]

    def list_games(self) -> list[dict[str, Any]]:
        result = []
        for game in self.games.values():
            result.append({
                "id": game.id,
                "phase": game.phase,
                "players": len(game.players),
                "created_at": game.created_at,
                "settings": game.settings,
            })
        return sorted(result, key=lambda item: item["created_at"], reverse=True)

    def join_game(self, game_id: str, name: str, color: str, player_id: str | None = None) -> tuple[Game, Player]:
        game = self.get(game_id)
        name = str(name or "").strip()[:24] or "Player"
        if player_id and player_id in game.players:
            player = game.players[player_id]
            player.name = name
            player.connected = True
            return game, player
        if game.phase != "lobby":
            if not game.settings.get("allow_spectators"):
                raise GameError("This game has already started.")
            raise GameError("Spectating is not implemented yet; join before the host starts.")
        color_ids = {item["id"] for item in PLAYER_COLORS}
        used_colors = {player.color for player in game.players.values()}
        if color not in color_ids:
            available = [item["id"] for item in PLAYER_COLORS if item["id"] not in used_colors]
            if not available:
                raise GameError("All preset colors are taken.")
            color = available[0]
        if color in used_colors:
            raise GameError("That color is already taken.")
        player_id = short_id(10)
        while player_id in game.players:
            player_id = short_id(10)
        player = Player(
            id=player_id,
            name=name,
            color=color,
            order=len(game.players),
            host=not game.players,
        )
        game.players[player_id] = player
        game.add_log(f"{name} joined as {color}.")
        return game, player


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))
