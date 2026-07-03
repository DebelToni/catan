from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit, join_room

from .game_engine import GameError, GameStore, PLAYER_COLORS, RESOURCE_TYPES
from .maps import list_map_presets

app = Flask(__name__)
app.config["SECRET_KEY"] = "local-catan-dev-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
store = GameStore()
sid_to_player: dict[str, tuple[str, str]] = {}


@app.get("/")
@app.get("/game/<game_id>")
def index(game_id: str | None = None):
    return render_template("index.html", game_id=(game_id or "").upper())


@app.get("/api/games")
def games():
    return jsonify(store.list_games())


@app.get("/api/colors")
def colors():
    return jsonify(PLAYER_COLORS)


@app.get("/health")
def health():
    return {"ok": True}


@socketio.on("connect")
def on_connect():
    emit("server_info", {"colors": PLAYER_COLORS, "resources": RESOURCE_TYPES, "map_presets": list_map_presets()})


@socketio.on("disconnect")
def on_disconnect():
    mapping = sid_to_player.pop(request.sid, None)
    if not mapping:
        return
    game_id, player_id = mapping
    try:
        game = store.get(game_id)
        if player_id in game.players and (game_id, player_id) not in sid_to_player.values():
            game.players[player_id].connected = False
            broadcast_state(game)
    except GameError:
        pass


@socketio.on("create_game")
def on_create_game(data):
    try:
        game = store.create_game((data or {}).get("settings") or {})
        game, player = store.join_game(game.id, (data or {}).get("name"), (data or {}).get("color"))
        bind_player(game.id, player.id)
        emit("game_created", {"game_id": game.id, "player_id": player.id, "url": f"/game/{game.id}"})
        broadcast_state(game)
    except GameError as exc:
        emit_error(str(exc))


@socketio.on("join_game")
def on_join_game(data):
    try:
        data = data or {}
        game, player = store.join_game(data.get("game_id", ""), data.get("name"), data.get("color"), data.get("player_id"))
        bind_player(game.id, player.id)
        emit("joined_game", {"game_id": game.id, "player_id": player.id, "url": f"/game/{game.id}"})
        broadcast_state(game)
    except GameError as exc:
        emit_error(str(exc))


@socketio.on("start_game")
def on_start_game(data):
    with_game_player(data, lambda game, player_id: game.start(player_id))


@socketio.on("roll_dice")
def on_roll_dice(data):
    with_game_player(data, lambda game, player_id: game.roll_dice(player_id))


@socketio.on("build")
def on_build(data):
    def action(game, player_id):
        game.build(player_id, (data or {}).get("type"), (data or {}).get("target_id"))
    with_game_player(data, action)


@socketio.on("discard")
def on_discard(data):
    with_game_player(data, lambda game, player_id: game.discard(player_id, (data or {}).get("resources") or {}))


@socketio.on("choose_gold")
def on_choose_gold(data):
    with_game_player(data, lambda game, player_id: game.choose_gold_resources(player_id, (data or {}).get("resources") or {}))


@socketio.on("move_robber")
def on_move_robber(data):
    def action(game, player_id):
        game.move_robber(player_id, (data or {}).get("hex_id"), (data or {}).get("victim_id") or None)
    with_game_player(data, action)


@socketio.on("buy_dev_card")
def on_buy_dev_card(data):
    with_game_player(data, lambda game, player_id: game.buy_development_card(player_id))


@socketio.on("play_dev_card")
def on_play_dev_card(data):
    def action(game, player_id):
        game.play_development_card(player_id, (data or {}).get("card_id"), (data or {}).get("payload") or {})
    with_game_player(data, action)


@socketio.on("bank_trade")
def on_bank_trade(data):
    def action(game, player_id):
        game.bank_trade(player_id, (data or {}).get("give"), (data or {}).get("receive"))
    with_game_player(data, action)


@socketio.on("create_trade_offer")
def on_create_trade_offer(data):
    def action(game, player_id):
        game.create_trade_offer(player_id, (data or {}).get("give") or {}, (data or {}).get("receive") or {})
    with_game_player(data, action)


@socketio.on("accept_trade_offer")
def on_accept_trade_offer(data):
    def action(game, player_id):
        game.accept_trade_offer(player_id, (data or {}).get("offer_id"))
    with_game_player(data, action)


@socketio.on("cancel_trade_offer")
def on_cancel_trade_offer(data):
    def action(game, player_id):
        game.cancel_trade_offer(player_id, (data or {}).get("offer_id"))
    with_game_player(data, action)


@socketio.on("end_turn")
def on_end_turn(data):
    with_game_player(data, lambda game, player_id: game.end_turn(player_id))


@socketio.on("chat")
def on_chat(data):
    def action(game, player_id):
        game.add_chat(player_id, (data or {}).get("text", ""))
    with_game_player(data, action)


def bind_player(game_id: str, player_id: str) -> None:
    game_id = game_id.upper()
    sid_to_player[request.sid] = (game_id, player_id)
    join_room(game_id)


def with_game_player(data, callback):
    try:
        data = data or {}
        game_id = (data.get("game_id") or "").upper()
        player_id = data.get("player_id")
        game = store.get(game_id)
        if player_id not in game.players:
            raise GameError("Join the game before acting.")
        callback(game, player_id)
        broadcast_state(game)
    except GameError as exc:
        emit_error(str(exc))


def broadcast_state(game) -> None:
    for sid, (game_id, player_id) in list(sid_to_player.items()):
        if game_id == game.id:
            socketio.emit("state", game.serialize(player_id), room=sid)



def emit_error(message: str) -> None:
    emit("error_message", {"message": message})
