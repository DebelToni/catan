# Project source of truth

## Product
A browser-based, private-room, Catan-style board game for friends. It runs on a local Flask server and can expose the same local game through a Cloudflare tunnel URL printed in the server stdout.

The implementation uses original placeholder art and does not copy Colonist.io/CATAN branding or assets. The target feel is a fast online hex-board experience: create room, choose color, drag/zoom the board, roll dice with a dice strip animation, build, trade, and play to the configured victory point target.

## Current build
- Local Flask + Socket.IO server with in-memory rooms.
- `run.py` starts the web server and, unless disabled, starts `cloudflared tunnel --url http://localhost:<port>` and prints the public trycloudflare URL when Cloudflare emits it.
- Single-page frontend with room creation, room joining, color selection, map panning/zooming, clickable intersections/edges/tiles, dice strip animation, player list, hand panel, trades, chat, and action log.
- Standard 19-hex base island with randomized resources/numbers from a seed and no adjacent 6/8 numbers.
- Generic board topology generation: hexes, vertices, edges, ports, adjacency, robber tile, roads, settlements, and cities are derived from the map config so custom maps can be added later.
- Generated placeholder PNG assets in `app/static/assets/`. Existing assets are loaded directly by the browser, so redrawing a PNG and restarting/refreshing uses the new art.

## Game settings
- Points to win: default 10, configurable 1-30.
- Max hand limit before robber discard: default 7, configurable 1-30. Players over the limit discard half, rounded down.
- Turn timer seconds: stored in settings; enforcement is not built yet.
- Friendly robber: optional; when enabled, robber steals only from players above 2 public VP.
- Random standard map: enabled by default.
- Map seed: blank creates a random seed; a fixed seed recreates the same map.
- Bank privacy: always private. Bank card counts are never shown as a game setting or public UI.
- Player colors: red, blue, orange, white, green, purple, black, pink, yellow, teal. Each color can be taken once.
- Player count: room can start with 2+ joined players; the engine does not hard-code a 4-player maximum.

## Base rules implemented
- Standard terrain distribution: 4 forest/lumber, 4 pasture/wool, 4 field/grain, 3 hill/brick, 3 mountain/ore, 1 desert.
- Standard number tokens: 2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12. Desert has no number.
- Robber starts on the desert and blocks production on its tile.
- Setup placement uses snake order: first player to last player, then last player to first player.
- Each setup placement is settlement then adjacent road.
- Settlement distance rule: no settlement/city may be on an adjacent intersection.
- Starting resources are granted from tiles adjacent to each player's second setup settlement.
- A normal turn starts with dice roll, then main actions, then end turn.
- Non-7 rolls produce resources for adjacent settlements/cities: settlement = 1, city = 2.
- Rolling 7 triggers hand-limit discards, robber movement, and a random steal from an adjacent victim if chosen/available.
- Roads cost lumber + brick and must connect to the player's network or building.
- Settlements cost lumber + brick + wool + grain and must connect to the player's road after setup.
- Cities cost 2 grain + 3 ore and upgrade an owned settlement.
- Development cards cost wool + grain + ore.
- Development deck: 14 Knights, 2 Road Building, 2 Year of Plenty, 2 Monopoly, 5 Victory Point.
- Development card limits: cannot play a non-VP card on the turn it was bought; one non-VP development card per turn.
- Knight moves robber and counts toward Largest Army.
- Road Building places two free roads.
- Year of Plenty grants exactly two chosen resources from the bank if available.
- Monopoly takes all cards of one chosen resource from opponents.
- Victory Point cards score automatically and stay hidden from other players.
- Largest Army gives 2 VP to the first player with at least 3 played Knights; it transfers only to a strictly larger army.
- Longest Road gives 2 VP for the unique longest continuous road of at least 5 edges; opponent buildings interrupt road continuity.
- Bank trades use 4:1 by default, 3:1 with a generic harbor, and 2:1 with the matching resource harbor.
- Player trade offers can be posted by the active player and accepted by another player during the active player's main turn.

## Screens and buttons
- Home: Create game, Join game, open-game shortcuts.
- Create game: name input, color buttons, points to win, max hand limit, turn timer seconds, map seed, random map toggle, friendly robber toggle, Create room.
- Join game: game code, name input, color buttons, Join room.
- Top bar: game code, phase/stage pill, dice strip, Copy link, Fit board.
- Player panel: color, name, host marker, connection state, public VP, own total VP, resource count, development card count, played Knights, current longest road length.
- Turn panel: Start game, Roll dice, Road, Settlement, City, Buy dev, End turn, contextual setup/robber/free-road help.
- Hand panel: private resource counts and private development cards with Play buttons when legal.
- Robber panel: appears when the player must move robber; click a tile, then choose victim or move only.
- Discard panel: appears only for players required to discard.
- Bank trade panel: give resource, receive resource, Trade button, owned rates.
- Player trades panel: create offer, accept offer, cancel own offer.
- Log/chat panel: game log, chat input, Send.

## Asset files
Terrain: `terrain_forest.png`, `terrain_pasture.png`, `terrain_field.png`, `terrain_hill.png`, `terrain_mountain.png`, `terrain_desert.png`, `terrain_sea.png`.

Resource cards: `resource_lumber.png`, `resource_brick.png`, `resource_wool.png`, `resource_grain.png`, `resource_ore.png`.

Development cards: `dev_knight.png`, `dev_road_building.png`, `dev_year_of_plenty.png`, `dev_monopoly.png`, `dev_victory_point.png`, `card_back_development.png`.

Board/UI pieces: `icon_robber.png`, `piece_settlement.png`, `piece_city.png`, `piece_road.png`, `number_token.png`, `largest_army.png`, `longest_road.png`.

Ports: `port_3to1.png`, `port_lumber.png`, `port_brick.png`, `port_wool.png`, `port_grain.png`, `port_ore.png`.

Dice: `dice_1.png`, `dice_2.png`, `dice_3.png`, `dice_4.png`, `dice_5.png`, `dice_6.png`.

## Known gaps for next passes
- Turn timer is stored but not enforced.
- Spectating after a game starts is intentionally blocked for now.
- Domestic trade negotiation is a simple posted-offer flow, not a full counteroffer table.
- Custom map loading UI is not built yet; the engine topology supports it.
- No bots, expansions, scenarios, accounts, ranking, reconnection conflict UI, or persistent database yet.
